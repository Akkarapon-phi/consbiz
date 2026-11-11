# Copyright (c) 2026, Siricons and contributors
# For license information, please see license.txt

"""ตั้งค่า HR (หมวด hr ของแอปออฟฟิศ, หน้า hr-setup) ตรวจความพร้อมของการตั้งค่า HR/เงินเดือนของบริษัท (ตกลง 2026-11-11)

CHECKS = รายการตรวจ แต่ละข้อคืน status ok / warn / error + คำอธิบาย + วิธีแก้:
- fix = แก้อัตโนมัติได้ (apply_fix, เฉพาะ HR Manager / System Manager) ข้อมูลตั้งค่ามาตรฐานของบริษัทไทย
- link = ต้องตัดสินเอง (เช่น เลือกบัญชี) เปิดฟอร์มในระบบเต็ม
ใช้ทั้งไซต์ใหม่และเซิร์ฟเวอร์จริงหลังขึ้นระบบ ทุก fix รันซ้ำได้ (ไม่สร้างซ้ำ)
แก้ข้อมูลที่ Submit แล้ว: สูตร/เงื่อนไขของโครงสร้างเงินเดือนแก้ได้ตามปกติ (Allow on Submit) ส่วน depends_on_payment_days
และช่วงเงินของขั้นภาษีไม่เปิดให้แก้หลัง Submit จึงเขียนตรง (db.set_value) พร้อม Comment บันทึกว่าแก้อะไร
"""

from urllib.parse import quote

import frappe
from frappe import _
from frappe.utils import getdate, nowdate

from consbiz import hr_attendance

# ประกันสังคม 5% ของค่าจ้างจริง (เงินเดือนตามวันทำงาน + OT) ฐานต่ำสุด 1,650 สูงสุด 17,500 (ปี 2569-2571) = ไม่เกิน 875
SSO_FORMULA = "min(rounded(max(base * payment_days / total_working_days + OT, 1650) * 0.05), 875) if total_working_days else 0"
SSO_CONDITION = "payment_days > 0"
UNPAID_COMPONENT = "หักเวลาที่ไม่ได้ทำงาน"
# วันลาขั้นต่ำตาม พ.ร.บ.คุ้มครองแรงงาน (วันทำงาน/ปี)
STATUTORY_LEAVES = {"ลาป่วย": 30, "ลากิจ": 3, "ลาพักร้อน": 6}
LEAVE_POLICY = "วันลาตาม พ.ร.บ.คุ้มครองแรงงาน"
# สิทธิ์ต่อปีที่ไม่คิดตามสัดส่วนเดือนที่เข้างาน (HRMS ลดตามสัดส่วนทุกประเภท) พักร้อนคงตามสัดส่วน (กฎหมายให้หลังทำงานครบ 1 ปี)
FULL_YEAR_LEAVES = ("ลาป่วย", "ลากิจ")
LWP_LEAVE = "ลา (ไม่จ่าย)"
# Salary Component ที่ติดมากับ ERPNext/HRMS (อินเดีย) ไม่ใช้ในไทย
FOREIGN_COMPONENTS = ("Basic", "House Rent Allowance", "Provident Fund", "Professional Tax", "Income Tax", "Arrear", "Leave Encashment")
MANAGER_ROLES = ("HR Manager", "System Manager")


def can_fix(user=None):
	return bool(set(frappe.get_roles(user)) & set(MANAGER_ROLES))


def form(doctype, name=None):
	slug = doctype.lower().replace(" ", "-")
	return f"/app/{slug}/{quote(name)}" if name else f"/app/{slug}"


def result(status, detail, fix=None, link=None, link_label=None):
	return {"status": status, "detail": detail, "fix": fix, "link": link, "link_label": link_label}


def company_value(company, field):
	return frappe.db.get_value("Company", company, field)


def account_type(account):
	return account and frappe.db.get_value("Account", account, "account_type")


def main_structure(company):
	"""โครงสร้างเงินเดือนรายเดือนที่ Submit แล้วของบริษัท (ที่มีคนใช้มากที่สุด)"""
	names = frappe.get_all(
		"Salary Structure",
		filters={"company": company, "docstatus": 1, "is_active": "Yes", "payroll_frequency": "Monthly"},
		pluck="name",
	)
	return names


def structure_rows(structures, parentfield):
	return frappe.get_all(
		"Salary Detail",
		filters={"parenttype": "Salary Structure", "parent": ("in", structures or [""]), "parentfield": parentfield},
		fields=["name", "parent", "salary_component", "abbr", "formula", "condition", "depends_on_payment_days", "amount_based_on_formula"],
	)


# ---------------------------------------------------------------- ตรวจ (company) → result


def check_holiday(company):
	from hrms.utils.holiday_list import get_assigned_holiday_list

	holiday_list = get_assigned_holiday_list(company)
	if not holiday_list:
		return result(
			"error",
			_("ยังไม่ได้กำหนดวันหยุดของบริษัท (Holiday List Assignment) ออกสลิปเงินเดือนไม่ได้"),
			link=form("Holiday List Assignment", "new"),
			link_label=_("กำหนดวันหยุด"),
		)
	to_date = frappe.db.get_value("Holiday List", holiday_list, "to_date")
	weekly = frappe.db.count("Holiday", {"parent": holiday_list, "weekly_off": 1})
	if weekly:
		return result(
			"error",
			_("{0} มีวันหยุดประจำสัปดาห์ {1} วัน (มาจากการลงวันหยุดของพนักงานอยู่แล้ว จะได้หยุดซ้ำ) ใส่เฉพาะวันหยุดนักขัตฤกษ์").format(
				holiday_list, weekly
			),
			link=form("Holiday List", holiday_list),
			link_label=_("แก้วันหยุด"),
		)
	if to_date and getdate(to_date) < getdate():
		return result("error", _("{0} หมดอายุแล้ว ({1}) สร้างของปีนี้แล้วกำหนดใหม่").format(holiday_list, to_date), link=form("Holiday List", "new"))
	return result("ok", _("{0} (วันหยุดนักขัตฤกษ์ {1} วัน)").format(holiday_list, frappe.db.count("Holiday", {"parent": holiday_list})))


def check_payroll_account(company):
	account = company_value(company, "default_payroll_payable_account")
	if not account:
		return result("error", _("ยังไม่ได้ตั้งบัญชีเงินเดือนค้างจ่าย"), link=form("Company", company))
	if account_type(account) != "Payable":
		return result("error", _("{0} ต้องตั้ง Account Type = Payable").format(account), link=form("Account", account))
	return result("ok", account)


def check_advance_account(company):
	account = company_value(company, "default_employee_advance_account")
	if not account:
		return result("error", _("ยังไม่ได้ตั้งบัญชีเงินทดรองจ่ายพนักงาน (ใช้กับเบิกเงินล่วงหน้า/เงินสำรองจ่าย)"), link=form("Company", company))
	if account_type(account) != "Receivable":
		return result("error", _("{0} ต้องตั้ง Account Type = Receivable (HRMS หายอดเบิกตามชนิดบัญชี)").format(account), link=form("Account", account))
	return result("ok", account)


def check_claim_account(company):
	account = company_value(company, "default_expense_claim_payable_account")
	if not account:
		return result(
			"error",
			_("ยังไม่ได้ตั้งบัญชีค้างจ่ายเบิกค่าใช้จ่าย (Default Expense Claim Payable Account) พนักงานเบิกค่าใช้จ่ายคืนไม่ได้"),
			link=form("Company", company),
			link_label=_("เลือกบัญชี (ประเภท Payable)"),
		)
	if account_type(account) != "Payable":
		return result("error", _("{0} ต้องตั้ง Account Type = Payable").format(account), link=form("Account", account))
	return result("ok", account)


def deduction_component(abbr=None, name=None):
	filters = {"type": "Deduction", "disabled": 0}
	if abbr:
		filters["salary_component_abbr"] = abbr
	if name:
		filters["name"] = name
	return frappe.db.get_value("Salary Component", filters, "name")


def check_advance_component(company):
	component = company_value(company, "custom_salary_advance_component")
	if component:
		return result("ok", component)
	found = deduction_component(abbr="SAD") or deduction_component(name="เงินเดือนจ่ายล่วงหน้า")
	return result(
		"error",
		_("ยังไม่ได้เลือกรายการหักคืนเงินเดือนล่วงหน้า (ฟอร์มบริษัท หัวข้อ Self Service: เบิกเงิน)"),
		fix=found and _("ใช้ {0}").format(found),
		link=form("Company", company),
	)


def check_unpaid_component(company):
	component = company_value(company, "custom_unpaid_time_component")
	if component:
		return result("ok", component)
	return result(
		"error",
		_("ยังไม่มีรายการหักเวลาที่ไม่ได้ทำงาน (สาย/กลับก่อน เมื่อ HR สั่งไม่จ่าย)"),
		fix=_("สร้าง \"{0}\" แล้วเลือกให้บริษัท").format(UNPAID_COMPONENT),
	)


def check_payroll_settings(company):
	basis = frappe.db.get_single_value("Payroll Settings", "payroll_based_on")
	if basis != "Attendance":
		return result("error", _("Payroll ยังคิดตาม {0} (ต้องเป็น Attendance วันขาดจึงหักเงินเดือน)").format(basis), fix=_("ตั้งเป็น Attendance"))
	return result("ok", _("คิดตาม Attendance วันที่ยังไม่บันทึกนับมาทำงาน"))


def check_structure(company):
	structures = main_structure(company)
	if not structures:
		return result("error", _("ไม่มีโครงสร้างเงินเดือนรายเดือนที่ Submit แล้ว"), link=form("Salary Structure", "new"))
	return result("ok", ", ".join(structures))


def salary_rows(company):
	return [r for r in structure_rows(main_structure(company), "earnings") if (r.formula or "").strip() == "base"]


def check_salary_proration(company):
	"""เงินเดือน (สูตร base) ต้องคิดตามวันทำงาน ไม่งั้นวันขาด/ลาไม่รับค่าจ้างไม่ถูกหัก"""
	rows = salary_rows(company)
	if not rows:
		return result("warn", _("ไม่พบแถวเงินเดือนที่ใช้สูตร base ในโครงสร้าง"))
	bad = [r for r in rows if not r.depends_on_payment_days]
	component_bad = [
		r.salary_component for r in rows if not frappe.db.get_value("Salary Component", r.salary_component, "depends_on_payment_days")
	]
	if bad or component_bad:
		return result(
			"error",
			_("เงินเดือนใน {0} ไม่ได้คิดตามวันทำงาน: ขาดงาน/ลาไม่รับค่าจ้างจะไม่ถูกหักเงิน").format(
				", ".join(sorted({r.parent for r in bad} | set(component_bad)))
			),
			fix=_("ตั้งให้คิดตามวันทำงาน"),
		)
	return result("ok", _("หักตามวันขาด/ลาไม่รับค่าจ้าง"))


def sso_rows(company):
	return [r for r in structure_rows(main_structure(company), "deductions") if r.abbr == "SSF"]


def check_sso(company):
	rows = sso_rows(company)
	if not rows:
		return result("warn", _("ไม่พบประกันสังคม (ตัวย่อ SSF) ในโครงสร้างเงินเดือน"), link=form("Salary Structure"))
	bad = [r for r in rows if "payment_days" not in (r.formula or "")]
	if bad:
		return result(
			"error",
			_("ประกันสังคมคิดจากเงินเดือนเต็ม เดือนที่ขาด/ลาไม่รับค่าจ้างจะหักเกินค่าจ้างจริง"),
			fix=_("คิดจากค่าจ้างจริง (เงินเดือนตามวันทำงาน + OT) 5% ไม่เกิน 875"),
		)
	return result("ok", _("5% ของค่าจ้างจริง ไม่เกิน 875 บาท"))


def tax_slab_problems(slab):
	rows = frappe.get_all(
		"Taxable Salary Slab", filters={"parent": slab}, fields=["name", "from_amount", "to_amount"], order_by="from_amount asc"
	)
	problems = []
	for i, row in enumerate(rows):
		last = i == len(rows) - 1
		if not last and row.to_amount <= row.from_amount:
			problems.append((row, "to_amount", rows[i + 1].from_amount - 1))
		if i and row.from_amount <= rows[i - 1].to_amount:
			problems.append((row, "from_amount", rows[i - 1].to_amount + 1))
	return problems


def tax_slabs(company):
	return frappe.get_all("Income Tax Slab", filters={"company": company, "docstatus": 1, "disabled": 0}, pluck="name")


def check_tax_slab(company):
	slabs = tax_slabs(company)
	if not slabs:
		return result("warn", _("ไม่มีขั้นภาษีเงินได้ (Income Tax Slab) ระบบจะไม่หักภาษี ณ ที่จ่าย"), link=form("Income Tax Slab", "new"))
	problems = [(slab, p) for slab in slabs for p in tax_slab_problems(slab)]
	if problems:
		text = "; ".join(
			_("{0} แถว {1:,.0f}: {2} ควรเป็น {3:,.0f}").format(slab, row.from_amount, "ถึง" if field == "to_amount" else "เริ่ม", value)
			for slab, (row, field, value) in problems
		)
		return result("error", text, fix=_("แก้ช่วงขั้นภาษีให้ต่อกัน"))
	return result("ok", ", ".join(slabs))


def check_payroll_period(company):
	today = getdate()
	period = frappe.db.get_value(
		"Payroll Period", {"company": company, "start_date": ("<=", today), "end_date": (">=", today)}, "name"
	)
	if not period:
		return result("error", _("ไม่มี Payroll Period ของปีนี้ (ใช้คำนวณภาษีทั้งปี)"), fix=_("สร้างงวดปี {0}").format(today.year))
	return result("ok", period)


def employees_without_structure(company):
	today = nowdate()
	with_ssa = set(
		frappe.get_all("Salary Structure Assignment", filters={"company": company, "docstatus": 1, "from_date": ("<=", today)}, pluck="employee")
	)
	return [
		e
		for e in frappe.get_all("Employee", filters={"company": company, "status": "Active"}, fields=["name", "employee_name"])
		if e.name not in with_ssa
	]


def check_assignments(company):
	missing = employees_without_structure(company)
	if missing:
		return result(
			"error",
			_("ยังไม่มีเงินเดือน {0} คน (ไม่อยู่ในงวดเงินเดือน): {1}").format(len(missing), ", ".join(e.employee_name for e in missing[:8])),
			link=form("Salary Structure Assignment", "new"),
			link_label=_("กำหนดเงินเดือน"),
		)
	return result("ok", _("พนักงานทุกคนมีโครงสร้างเงินเดือน"))


def check_foreign_components(company):
	active = frappe.get_all("Salary Component", filters={"name": ("in", FOREIGN_COMPONENTS), "disabled": 0}, pluck="name")
	if active:
		return result("warn", _("รายการเงินเดือนของอินเดียยังเปิดอยู่ (เลือกผิดได้): {0}").format(", ".join(active)), fix=_("ปิดรายการที่ไม่ได้ใช้"))
	return result("ok", _("ไม่มีรายการที่ไม่ใช้"))


def check_leave_holidays(company):
	bad = frappe.get_all("Leave Type", filters={"is_lwp": 0, "include_holiday": 1}, pluck="name")
	if bad:
		return result(
			"error",
			_("{0} นับวันหยุดเป็นวันลา (กฎหมายนับเป็นวันทำงาน)").format(", ".join(bad)),
			fix=_("ไม่นับวันหยุดในวันลา"),
		)
	return result("ok", _("นับเฉพาะวันทำงาน"))


def current_leave_period(company):
	today = getdate()
	return frappe.db.get_value(
		"Leave Period",
		{"company": company, "is_active": 1, "from_date": ("<=", today), "to_date": (">=", today)},
		["name", "from_date", "to_date"],
		as_dict=True,
	)


def check_leave_policy(company):
	if not current_leave_period(company):
		return result("error", _("ไม่มีรอบวันลา (Leave Period) ของปีนี้"), fix=_("สร้างรอบวันลาปี {0} + นโยบายวันลาตามกฎหมาย").format(getdate().year))
	policy = frappe.db.get_value("Leave Policy", {"docstatus": 1}, "name")
	if not policy:
		return result("error", _("ไม่มีนโยบายวันลา (Leave Policy)"), fix=_("สร้างนโยบาย ลาป่วย 30 ลากิจ 3 ลาพักร้อน 6"))
	return result("ok", _("{0}").format(", ".join(frappe.get_all("Leave Policy", filters={"docstatus": 1}, pluck="title"))))


def employees_without_leave(company):
	period = current_leave_period(company)
	if not period:
		return []
	with_alloc = set(
		frappe.get_all(
			"Leave Allocation",
			filters={"docstatus": 1, "from_date": ("<=", period.to_date), "to_date": (">=", period.from_date)},
			pluck="employee",
		)
	)
	return [
		e
		for e in frappe.get_all("Employee", filters={"company": company, "status": "Active"}, fields=["name", "employee_name"])
		if e.name not in with_alloc
	]


def short_allocations(company):
	"""โควตาลาป่วย/ลากิจของปีนี้ที่ได้น้อยกว่าสิทธิ์ตามกฎหมาย (ถูกลดตามสัดส่วนเดือนที่เข้างาน)"""
	period = current_leave_period(company)
	if not period:
		return []
	employees = frappe.get_all("Employee", filters={"company": company, "status": "Active"}, pluck="name")
	return [
		a
		for a in frappe.get_all(
			"Leave Allocation",
			filters={
				"docstatus": 1,
				"employee": ("in", employees or [""]),
				"leave_type": ("in", FULL_YEAR_LEAVES),
				"from_date": ("<=", period.to_date),
				"to_date": (">=", period.from_date),
			},
			fields=["name", "employee", "employee_name", "leave_type", "new_leaves_allocated"],
		)
		if a.new_leaves_allocated < STATUTORY_LEAVES.get(a.leave_type, 0)
	]


def check_leave_allocations(company):
	if not current_leave_period(company):
		return result("warn", _("สร้างรอบวันลาก่อน"))
	short = short_allocations(company)
	if short:
		return result(
			"error",
			_("ลาป่วย/ลากิจ ได้ไม่ครบสิทธิ์ต่อปี {0} รายการ (ถูกลดตามเดือนที่เข้างาน): {1}").format(
				len(short), ", ".join(sorted({a.employee_name for a in short}))[:200]
			),
			fix=_("เติมให้ครบตามกฎหมาย"),
		)
	missing = employees_without_leave(company)
	if missing:
		return result(
			"error",
			_("ยังไม่ได้รับโควตาวันลา {0} คน (ลาได้แค่ลาไม่รับค่าจ้าง): {1}").format(len(missing), ", ".join(e.employee_name for e in missing[:8])),
			fix=_("ให้โควตาตามนโยบายวันลา"),
		)
	return result("ok", _("พนักงานทุกคนมีโควตาวันลา"))


def check_roles(company):
	from frappe.utils.user import get_users_with_role

	missing = [role for role in ("HR Manager", "Leave Approver", "Expense Approver") if not get_users_with_role(role)]
	if missing:
		return result("error", _("ยังไม่มีผู้ใช้ที่มี Role: {0}").format(", ".join(missing)), link="/app/user", link_label=_("กำหนด Role"))
	return result("ok", _("มีผู้ดูแล HR ผู้อนุมัติการลา และผู้อนุมัติการเบิก"))


def check_employee_users(company):
	rows = frappe.get_all("Employee", filters={"company": company, "status": "Active"}, fields=["name", "employee_name", "user_id", "custom_project"])
	no_user = [r for r in rows if not r.user_id]
	no_project = [r for r in rows if not r.custom_project]
	notes = []
	if no_user:
		notes.append(_("ไม่มีบัญชีผู้ใช้ {0} คน (ใช้ Self Service ไม่ได้)").format(len(no_user)))
	if no_project:
		notes.append(_("ไม่ได้ประจำโครงการ {0} คน (จุดลงเวลา/โควตาวันหยุดใช้ของโครงการ)").format(len(no_project)))
	if notes:
		return result("warn", " · ".join(notes), link="/app/employee?status=Active", link_label=_("ดูพนักงาน"))
	return result("ok", _("ทุกคนมีผู้ใช้และโครงการ"))


CHECKS = [
	("company", "holiday", _("วันหยุดของบริษัท"), check_holiday),
	("company", "payroll_account", _("บัญชีเงินเดือนค้างจ่าย"), check_payroll_account),
	("company", "advance_account", _("บัญชีเงินทดรองจ่ายพนักงาน"), check_advance_account),
	("company", "claim_account", _("บัญชีค้างจ่ายเบิกค่าใช้จ่าย"), check_claim_account),
	("company", "advance_component", _("รายการหักคืนเงินเดือนล่วงหน้า"), check_advance_component),
	("company", "unpaid_component", _("รายการหักเวลาที่ไม่ได้ทำงาน"), check_unpaid_component),
	("payroll", "payroll_settings", _("หลักการคิดเงินเดือน"), check_payroll_settings),
	("payroll", "structure", _("โครงสร้างเงินเดือน"), check_structure),
	("payroll", "salary_proration", _("เงินเดือนคิดตามวันทำงาน"), check_salary_proration),
	("payroll", "sso", _("ประกันสังคม"), check_sso),
	("payroll", "tax_slab", _("ขั้นภาษีเงินได้"), check_tax_slab),
	("payroll", "payroll_period", _("ปีภาษี (Payroll Period)"), check_payroll_period),
	("payroll", "assignments", _("เงินเดือนของพนักงาน"), check_assignments),
	("payroll", "foreign_components", _("รายการเงินเดือนที่ไม่ใช้"), check_foreign_components),
	("leave", "leave_holidays", _("การนับวันลา"), check_leave_holidays),
	("leave", "leave_policy", _("นโยบายและรอบวันลา"), check_leave_policy),
	("leave", "leave_allocations", _("โควตาวันลาของพนักงาน"), check_leave_allocations),
	("people", "roles", _("ผู้ดูแลและผู้อนุมัติ"), check_roles),
	("people", "employees", _("ข้อมูลพนักงาน"), check_employee_users),
]
GROUPS = {"company": _("บริษัทและบัญชี"), "payroll": _("เงินเดือน"), "leave": _("วันลา"), "people": _("ผู้ใช้และพนักงาน")}


@frappe.whitelist()
def get_checks(company=None):
	hr_attendance.require_hr()
	company = hr_attendance.default_company(company)
	rows = []
	for group, key, title, fn in CHECKS:
		try:
			row = fn(company)
		except Exception as error:
			row = result("error", _("ตรวจไม่สำเร็จ: {0}").format(error))
		rows.append({"group": group, "key": key, "title": title, **row})
	return {"company": company, "groups": GROUPS, "checks": rows, "can_fix": can_fix()}


# ---------------------------------------------------------------- แก้ (apply_fix)


def fix_advance_component(company):
	component = deduction_component(abbr="SAD") or deduction_component(name="เงินเดือนจ่ายล่วงหน้า")
	if not component:
		frappe.throw(_("ไม่พบ Salary Component ของเงินเดือนล่วงหน้า"))
	frappe.db.set_value("Company", company, "custom_salary_advance_component", component)


def salary_expense_account(company):
	"""บัญชีค่าใช้จ่ายเงินเดือนของบริษัท (จาก component เงินเดือนในโครงสร้าง)"""
	for row in salary_rows(company):
		account = frappe.db.get_value("Salary Component Account", {"parent": row.salary_component, "company": company}, "account")
		if account:
			return account
	return None


def fix_unpaid_component(company):
	if not frappe.db.exists("Salary Component", UNPAID_COMPONENT):
		doc = frappe.get_doc(
			{
				"doctype": "Salary Component",
				"salary_component": UNPAID_COMPONENT,
				"salary_component_abbr": "UNP",
				"type": "Deduction",
				"depends_on_payment_days": 0,
				"is_tax_applicable": 0,
				"description": _("ไม่จ่ายค่าจ้างของนาทีสาย/กลับก่อน (No Work, No Pay) สร้างจากหน้าสรุปวันทำงาน"),
			}
		)
		doc.insert()
	doc = frappe.get_doc("Salary Component", UNPAID_COMPONENT)
	account = salary_expense_account(company)
	if account and not any(a.company == company for a in doc.accounts):
		# หักค่าจ้างที่ไม่ได้จ่าย = ลดค่าใช้จ่ายเงินเดือน
		doc.append("accounts", {"company": company, "account": account})
		doc.save()
	frappe.db.set_value("Company", company, "custom_unpaid_time_component", UNPAID_COMPONENT)


def fix_payroll_settings(company):
	frappe.db.set_single_value("Payroll Settings", "payroll_based_on", "Attendance")
	if not frappe.db.get_single_value("Payroll Settings", "consider_unmarked_attendance_as"):
		frappe.db.set_single_value("Payroll Settings", "consider_unmarked_attendance_as", "Present")


def comment(doctype, name, text):
	frappe.get_doc(
		{
			"doctype": "Comment",
			"comment_type": "Comment",
			"reference_doctype": doctype,
			"reference_name": name,
			"content": _("ตั้งค่า HR: {0}").format(text),
		}
	).insert(ignore_permissions=True)


def fix_salary_proration(company):
	for row in salary_rows(company):
		frappe.db.set_value("Salary Component", row.salary_component, "depends_on_payment_days", 1)
		if not row.depends_on_payment_days:
			frappe.db.set_value("Salary Detail", row.name, "depends_on_payment_days", 1)
			comment("Salary Structure", row.parent, _("{0} คิดตามวันทำงาน").format(row.salary_component))


def fix_sso(company):
	for row in sso_rows(company):
		doc = frappe.get_doc("Salary Structure", row.parent)
		for d in doc.deductions:
			if d.name == row.name:
				if not d.amount_based_on_formula:
					frappe.db.set_value("Salary Detail", d.name, "amount_based_on_formula", 1)
					d.amount_based_on_formula = 1
				d.formula = SSO_FORMULA
				d.condition = SSO_CONDITION
		doc.save()
		comment("Salary Structure", doc.name, _("ประกันสังคมคิดจากค่าจ้างจริง: {0}").format(SSO_FORMULA))


def fix_tax_slab(company):
	for slab in tax_slabs(company):
		for row, field, value in tax_slab_problems(slab):
			frappe.db.set_value("Taxable Salary Slab", row.name, field, value)
			comment("Income Tax Slab", slab, _("แถว {0:,.0f}: {1} = {2:,.0f}").format(row.from_amount, field, value))


def fix_payroll_period(company):
	year = getdate().year
	doc = frappe.get_doc(
		{
			"doctype": "Payroll Period",
			"__newname": f"{year} - {company}",
			"company": company,
			"start_date": f"{year}-01-01",
			"end_date": f"{year}-12-31",
		}
	)
	doc.insert()


def fix_foreign_components(company):
	used = set(frappe.get_all("Salary Detail", filters={"parenttype": "Salary Structure"}, pluck="salary_component"))
	for name in FOREIGN_COMPONENTS:
		if frappe.db.exists("Salary Component", name) and name not in used:
			frappe.db.set_value("Salary Component", name, "disabled", 1)


def fix_leave_holidays(company):
	for name in frappe.get_all("Leave Type", filters={"is_lwp": 0, "include_holiday": 1}, pluck="name"):
		frappe.db.set_value("Leave Type", name, "include_holiday", 0)


def ensure_leave_types():
	for name, days in STATUTORY_LEAVES.items():
		if not frappe.db.exists("Leave Type", name):
			frappe.get_doc(
				{"doctype": "Leave Type", "leave_type_name": name, "max_leaves_allowed": days, "include_holiday": 0}
			).insert()
	if not frappe.db.exists("Leave Type", LWP_LEAVE):
		frappe.get_doc({"doctype": "Leave Type", "leave_type_name": LWP_LEAVE, "is_lwp": 1}).insert()


def fix_leave_policy(company):
	ensure_leave_types()
	year = getdate().year
	if not current_leave_period(company):
		frappe.get_doc(
			{
				"doctype": "Leave Period",
				"from_date": f"{year}-01-01",
				"to_date": f"{year}-12-31",
				"is_active": 1,
				"company": company,
			}
		).insert()
	if not frappe.db.get_value("Leave Policy", {"docstatus": 1}, "name"):
		frappe.get_doc(
			{
				"doctype": "Leave Policy",
				"title": LEAVE_POLICY,
				"leave_policy_details": [
					{"leave_type": name, "annual_allocation": days} for name, days in STATUTORY_LEAVES.items()
				],
			}
		).submit()


def fix_leave_allocations(company):
	period = current_leave_period(company)
	if not period:
		frappe.throw(_("สร้างรอบวันลาก่อน"))
	policy = frappe.db.get_value("Leave Policy", {"title": LEAVE_POLICY, "docstatus": 1}, "name") or frappe.db.get_value(
		"Leave Policy", {"docstatus": 1}, "name"
	)
	if not policy:
		frappe.throw(_("สร้างนโยบายวันลาก่อน"))
	for employee in employees_without_leave(company):
		joined = frappe.db.get_value("Employee", employee.name, "date_of_joining")
		doc = frappe.get_doc(
			{
				"doctype": "Leave Policy Assignment",
				"employee": employee.name,
				"leave_policy": policy,
				"assignment_based_on": "Leave Period",
				"leave_period": period.name,
				"effective_from": max(getdate(period.from_date), getdate(joined)),
				"effective_to": period.to_date,
				"company": company,
			}
		)
		doc.insert()
		doc.submit()
	for row in short_allocations(company):
		allocation = frappe.get_doc("Leave Allocation", row.name)
		allocation.new_leaves_allocated = STATUTORY_LEAVES[row.leave_type]
		allocation.save()


FIXES = {
	"advance_component": fix_advance_component,
	"unpaid_component": fix_unpaid_component,
	"payroll_settings": fix_payroll_settings,
	"salary_proration": fix_salary_proration,
	"sso": fix_sso,
	"tax_slab": fix_tax_slab,
	"payroll_period": fix_payroll_period,
	"foreign_components": fix_foreign_components,
	"leave_holidays": fix_leave_holidays,
	"leave_policy": fix_leave_policy,
	"leave_allocations": fix_leave_allocations,
}


@frappe.whitelist(methods=["POST"])
def apply_fix(key, company=None):
	hr_attendance.require_hr()
	if not can_fix():
		frappe.throw(_("แก้การตั้งค่าได้เฉพาะ HR Manager / System Manager"), frappe.PermissionError)
	if key not in FIXES:
		frappe.throw(_("ข้อนี้แก้อัตโนมัติไม่ได้"))
	company = hr_attendance.default_company(company)
	FIXES[key](company)
	check = next(c for c in CHECKS if c[1] == key)
	return {"key": key, **check[3](company)}
