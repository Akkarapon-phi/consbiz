# Copyright (c) 2026, Siricons and contributors
# For license information, please see license.txt

"""เงินเดือน (หมวด hr ของแอปออฟฟิศ, หน้า hr-payroll) ครอบ Payroll Entry ของ HRMS ไม่คำนวณเงินเดือนเอง (ตกลง 2026-11-11)

- งวดรายเดือนอย่างเดียว (PAYROLL_FREQUENCY) 1 งวดต่อบริษัทต่อเดือน
- ขั้นตอน: ตรวจการเข้างาน → สร้างสลิป (create_payroll = Payroll Entry Submit → HRMS สร้างสลิปร่าง) → ตรวจสลิป
  (คำนวณใหม่ได้ระหว่างเป็นร่าง) → ยืนยันสลิป (submit_slips = Submit สลิป + HRMS ลงบัญชีเงินเดือนค้างจ่าย)
- ต้องบันทึก Attendance ให้ครบก่อนสร้างและก่อนยืนยันสลิป (attendance_issues): ไม่มีวันรอตัดสิน และวันที่ผ่านมาแล้ว
  บันทึก Attendance ครบ (หน้า hr-attendance) วันที่ยังไม่ถึงนับมาทำงานตาม Payroll Settings
- บันทึกจ่ายเงิน (Bank Entry) เป็นงานบัญชี ทำในระบบเต็ม (โมดูลบัญชีของแอปภายหลัง)
- พนักงานในงวด = ที่มีโครงสร้างเงินเดือน (Salary Structure Assignment) ตามเกณฑ์ของ HRMS (fill_employee_details)
  เกิน 30 คน HRMS ทำในคิว (สถานะ Queued) หน้าจอโหลดใหม่ดูผล
"""

from urllib.parse import quote

import frappe
from frappe import _
from frappe.utils import flt, getdate

from consbiz import hr_attendance

PAYROLL_FREQUENCY = "Monthly"
SLIP_FIELDS = [
	"name",
	"employee",
	"employee_name",
	"designation",
	"department",
	"docstatus",
	"status",
	"payment_days",
	"total_working_days",
	"absent_days",
	"leave_without_pay",
	"gross_pay",
	"total_deduction",
	"net_pay",
	"currency",
]


def can_manage(user=None):
	return hr_attendance.can_manage(user) and bool(frappe.has_permission("Payroll Entry", "create", user=user))


def require_hr():
	if not can_manage():
		frappe.throw(_("เฉพาะฝ่ายบุคคล (HR) ที่ทำเงินเดือนได้เท่านั้น"), frappe.PermissionError)


def payroll_entry_of(company, start, end):
	return frappe.db.get_value(
		"Payroll Entry",
		{
			"company": company,
			"start_date": start,
			"end_date": end,
			"payroll_frequency": PAYROLL_FREQUENCY,
			"docstatus": ("<", 2),
		},
		"name",
		order_by="creation desc",
	)


def salaried_employees(company, start, end):
	"""พนักงานที่มีโครงสร้างเงินเดือน (Submit) ใช้ได้ในงวด"""
	return set(
		frappe.get_all(
			"Salary Structure Assignment",
			filters={"company": company, "docstatus": 1, "from_date": ("<=", end)},
			pluck="employee",
		)
	)


def attendance_issues(company, month, employees=None):
	"""วันที่ยังไม่พร้อมของพนักงานในงวด: {flag: วันรอตัดสิน, unsaved: วันที่ยังไม่บันทึก Attendance, future: วันที่ยังไม่ถึง}"""
	_start, _end, rows = hr_attendance.build(company, month)
	if employees is not None:
		rows = [r for r in rows if r["employee"] in employees]
	out = {"flag": 0, "unsaved": 0, "future": 0, "people": []}
	for row in rows:
		flag = row["totals"]["flag"]
		unsaved = sum(c["s"] in hr_attendance.AUTO_STATUS for c in row["days"].values())
		out["flag"] += flag
		out["unsaved"] += unsaved
		out["future"] += sum(c["s"] == "future" for c in row["days"].values())
		if flag or unsaved:
			out["people"].append({"employee": row["employee"], "employee_name": row["employee_name"], "flag": flag, "unsaved": unsaved})
	return out


def require_attendance(company, month, employees):
	issues = attendance_issues(company, month, employees)
	if issues["flag"] or issues["unsaved"]:
		frappe.throw(
			_("บันทึกการเข้างานให้ครบก่อน: รอตัดสิน {0} วัน, ยังไม่บันทึก Attendance {1} วัน (หน้าสรุปวันทำงาน)").format(
				issues["flag"], issues["unsaved"]
			)
		)


@frappe.whitelist()
def get_payroll(month, company=None):
	require_hr()
	company = hr_attendance.default_company(company)
	start, end = hr_attendance.period_of(month)
	name = payroll_entry_of(company, start, end)
	entry = None
	slips = []
	if name:
		entry = frappe.db.get_value(
			"Payroll Entry",
			name,
			["name", "docstatus", "status", "posting_date", "number_of_employees", "salary_slips_created", "salary_slips_submitted", "error_message"],
			as_dict=True,
		)
		slips = frappe.get_all(
			"Salary Slip",
			filters={"payroll_entry": name, "docstatus": ("<", 2)},
			fields=SLIP_FIELDS,
			order_by="employee_name asc",
			limit_page_length=0,
		)
		employees = set(frappe.get_all("Payroll Employee Detail", filters={"parent": name}, pluck="employee"))
	else:
		employees = salaried_employees(company, start, end)
	salaried = salaried_employees(company, start, end)
	active = frappe.get_all(
		"Employee",
		filters={"company": company, "status": "Active", "date_of_joining": ("<=", end)},
		fields=["name", "employee_name"],
		order_by="employee_name asc",
	)
	return {
		"company": company,
		"start": start,
		"end": end,
		"entry": entry,
		"slips": slips,
		"totals": {
			key: flt(sum(flt(s[key]) for s in slips), 2) for key in ("gross_pay", "total_deduction", "net_pay")
		},
		"attendance": attendance_issues(company, month, employees),
		# พนักงาน Active ที่ไม่มีโครงสร้างเงินเดือน = ไม่ได้อยู่ในงวด
		"no_structure": [e for e in active if e.name not in salaried],
		"currency": frappe.get_cached_value("Company", company, "default_currency"),
		"payroll_payable_account": frappe.get_cached_value("Company", company, "default_payroll_payable_account"),
	}


@frappe.whitelist(methods=["POST"])
def create_payroll(month, company=None):
	"""สร้างงวดเงินเดือน = Payroll Entry (ดึงพนักงาน) แล้ว Submit ให้ HRMS สร้างสลิปร่าง"""
	require_hr()
	company = hr_attendance.default_company(company)
	start, end = hr_attendance.period_of(month)
	if payroll_entry_of(company, start, end):
		frappe.throw(_("เดือนนี้มีงวดเงินเดือนแล้ว"))
	if getdate(start) > getdate():
		frappe.throw(_("ยังไม่ถึงเดือนนี้"))
	require_attendance(company, month, salaried_employees(company, start, end))
	values = frappe.get_cached_value(
		"Company", company, ["default_payroll_payable_account", "cost_center", "default_currency"], as_dict=True
	)
	if not values.default_payroll_payable_account:
		frappe.throw(_("ตั้งบัญชีเงินเดือนค้างจ่าย (Default Payroll Payable Account) ที่บริษัท {0} ก่อน").format(company))
	if frappe.db.get_value("Account", values.default_payroll_payable_account, "account_type") != "Payable":
		frappe.throw(
			_("บัญชีเงินเดือนค้างจ่าย {0} ต้องตั้งประเภทบัญชี (Account Type) เป็น Payable ให้ฝ่ายบัญชีแก้ก่อน").format(
				values.default_payroll_payable_account
			)
		)
	doc = frappe.get_doc(
		{
			"doctype": "Payroll Entry",
			"company": company,
			"posting_date": end,
			"payroll_frequency": PAYROLL_FREQUENCY,
			"start_date": start,
			"end_date": end,
			"currency": values.default_currency,
			"exchange_rate": 1,
			"payroll_payable_account": values.default_payroll_payable_account,
			"cost_center": values.cost_center,
			"salary_slip_based_on_timesheet": 0,
		}
	)
	try:
		doc.fill_employee_details()
	except frappe.ValidationError:
		frappe.clear_messages()
		frappe.throw(
			_("ไม่มีพนักงานที่มีโครงสร้างเงินเดือนรายเดือน (Salary Structure Assignment) ของบริษัท {0} ในงวดนี้").format(company)
		)
	doc.insert()
	doc.submit()
	return {"name": doc.name, "employees": len(doc.employees), "status": doc.status}


def draft_entry(name):
	doc = frappe.get_doc("Payroll Entry", name)
	if doc.docstatus != 1:
		frappe.throw(_("งวดเงินเดือนนี้ยังไม่ได้สร้างสลิปหรือถูกยกเลิกแล้ว"))
	return doc


@frappe.whitelist(methods=["POST"])
def recalculate(payroll_entry):
	"""คำนวณสลิปร่างใหม่ (เช่น แก้ Attendance / Additional Salary หลังสร้างสลิป)"""
	require_hr()
	doc = draft_entry(payroll_entry)
	count = 0
	for name in frappe.get_all("Salary Slip", filters={"payroll_entry": doc.name, "docstatus": 0}, pluck="name"):
		frappe.get_doc("Salary Slip", name).save()
		count += 1
	return {"count": count}


@frappe.whitelist(methods=["POST"])
def submit_slips(payroll_entry):
	"""ยืนยันสลิป = Submit สลิปร่างทั้งงวด (HRMS ลงบัญชีเงินเดือนค้างจ่าย) ตรวจการเข้างานซ้ำก่อน"""
	require_hr()
	doc = draft_entry(payroll_entry)
	month = str(doc.start_date)[:7]
	require_attendance(doc.company, month, {e.employee for e in doc.employees})
	# คำนวณใหม่ก่อนยืนยัน: Attendance/รายการหักที่แก้หลังสร้างสลิปต้องมีผล
	recalculate(payroll_entry)
	doc.reload()
	doc.submit_salary_slips()
	return {"status": frappe.db.get_value("Payroll Entry", doc.name, "status")}


@frappe.whitelist(methods=["POST"])
def cancel_payroll(payroll_entry):
	"""ยกเลิกงวด (เฉพาะที่ยังไม่ได้ยืนยันสลิป) HRMS ลบสลิปร่างให้"""
	require_hr()
	doc = frappe.get_doc("Payroll Entry", payroll_entry)
	if frappe.db.exists("Salary Slip", {"payroll_entry": doc.name, "docstatus": 1}):
		frappe.throw(_("ยืนยันสลิปแล้ว ยกเลิกงวดในแอปไม่ได้ (ต้องยกเลิกบัญชีและสลิปในระบบเต็ม)"))
	if doc.docstatus == 1:
		doc.cancel()
	elif doc.docstatus == 0:
		frappe.delete_doc("Payroll Entry", doc.name)
	return {"name": doc.name}


@frappe.whitelist()
def get_slip(name):
	require_hr()
	slip = frappe.get_doc("Salary Slip", name)
	rows = lambda table: [  # noqa: E731
		{"component": r.salary_component, "abbr": r.abbr, "amount": r.amount}
		for r in slip.get(table)
		if not r.get("statistical_component") and not r.get("do_not_include_in_total")
	]
	return {
		**{f: slip.get(f) for f in SLIP_FIELDS},
		"start_date": slip.start_date,
		"end_date": slip.end_date,
		"salary_structure": slip.salary_structure,
		"earnings": rows("earnings"),
		"deductions": rows("deductions"),
		"rounded_total": slip.rounded_total,
		"pdf": f"/printview?doctype=Salary%20Slip&name={quote(name)}&trigger_print=1",
	}
