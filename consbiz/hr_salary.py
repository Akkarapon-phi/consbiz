# Copyright (c) 2026, Siricons and contributors
# For license information, please see license.txt

"""รายการเพิ่ม/หักรายเดือน + เงินเดือนพนักงาน (หมวด hr ของแอปออฟฟิศ, หน้า hr-adjustments / hr-salaries) ตกลง 2026-11-11

- รายการเพิ่ม/หัก = Additional Salary ของ HRMS (Submit ทันที) งวดเดือน = payroll_date วันสุดท้ายของเดือน
  เลือกได้เฉพาะรายการที่บริษัทผูกบัญชีแล้ว ยกเว้นที่ระบบคำนวณเอง (MANAGED: เงินเดือนตามสูตร ประกันสังคม ภาษี
  หักคืนเงินเดือนล่วงหน้า (self_advance) หักเวลาที่ไม่ได้ทำงาน (hr_attendance)) ยกเลิกได้จนกว่าจะยืนยันสลิปของเดือนนั้น
- เงินเดือนพนักงาน = Salary Structure Assignment (Submit ทันที) ปรับเงินเดือน = ใบใหม่ from_date ใหม่ (ประวัติคงอยู่)
  ขั้นภาษีใช้ของใบล่าสุดของบริษัท/ขั้นภาษีที่ใช้งานของบริษัท บัญชีค้างจ่าย = ของบริษัท
เห็นตัวเลขเงินเดือนเฉพาะ HR ที่ทำเงินเดือนได้ (hr_payroll.can_manage)
"""

import frappe
from frappe import _
from frappe.utils import flt, getdate

from consbiz import hr_attendance, hr_payroll

# ตัวย่อรายการที่ระบบคำนวณ/สร้างเอง ไม่ให้ลงด้วยมือ
MANAGED_ABBR = {"SAL", "SSF", "WHT", "SAD", "UNP"}


def require():
	hr_payroll.require_hr()


def managed_components(company):
	names = set(frappe.get_all("Salary Component", filters={"salary_component_abbr": ("in", list(MANAGED_ABBR))}, pluck="name"))
	for field in ("custom_salary_advance_component", "custom_unpaid_time_component"):
		value = frappe.db.get_value("Company", company, field)
		if value:
			names.add(value)
	# รายการที่โครงสร้างคิดด้วยสูตร (เช่น เงินเดือน ประกันสังคม)
	names |= set(
		frappe.get_all(
			"Salary Detail",
			filters={"parenttype": "Salary Structure", "amount_based_on_formula": 1},
			pluck="salary_component",
		)
	)
	return names


def component_options(company):
	with_account = set(frappe.get_all("Salary Component Account", filters={"company": company}, pluck="parent"))
	managed = managed_components(company)
	return [
		{"value": c.name, "label": c.name, "type": c.type, "description": "รายได้" if c.type == "Earning" else "รายการหัก"}
		for c in frappe.get_all(
			"Salary Component",
			filters={"disabled": 0, "statistical_component": 0},
			fields=["name", "type"],
			order_by="type desc, name asc",
		)
		if c.name in with_account and c.name not in managed
	]


def employee_options(company):
	return [
		{"value": e.name, "label": e.employee_name, "description": e.designation or e.name}
		for e in frappe.get_all(
			"Employee",
			filters={"company": company, "status": "Active"},
			fields=["name", "employee_name", "designation"],
			order_by="employee_name asc",
		)
	]


def slip_submitted(employee, day):
	return frappe.db.get_value(
		"Salary Slip",
		{"employee": employee, "docstatus": 1, "start_date": ("<=", day), "end_date": (">=", day)},
		"name",
	)


def last_comment(doctype, name):
	return frappe.db.get_value(
		"Comment",
		{"reference_doctype": doctype, "reference_name": name, "comment_type": "Comment"},
		"content",
		order_by="creation desc",
	)


# ---------------------------------------------------------------- รายการเพิ่ม/หัก


@frappe.whitelist()
def get_adjustments(month, company=None):
	require()
	company = hr_attendance.default_company(company)
	start, end = hr_attendance.period_of(month)
	rows = frappe.get_all(
		"Additional Salary",
		filters={"company": company, "docstatus": 1, "payroll_date": ("between", [start, end])},
		fields=["name", "employee", "employee_name", "salary_component", "type", "amount", "payroll_date", "owner", "creation"],
		order_by="employee_name asc, creation asc",
		limit_page_length=0,
	)
	managed = managed_components(company)
	for row in rows:
		row.note = last_comment("Additional Salary", row.name)
		row.managed = row.salary_component in managed
		row.locked = bool(slip_submitted(row.employee, row.payroll_date))
	return {
		"company": company,
		"start": start,
		"end": end,
		"rows": rows,
		"components": component_options(company),
		"employees": employee_options(company),
		"totals": {
			"earning": flt(sum(r.amount for r in rows if r.type == "Earning"), 2),
			"deduction": flt(sum(r.amount for r in rows if r.type == "Deduction"), 2),
		},
	}


@frappe.whitelist(methods=["POST"])
def add_adjustment(employee, salary_component, amount, month, note=None):
	"""ลงรายการเพิ่ม/หักของเดือน = Additional Salary (Submit)"""
	require()
	company = frappe.db.get_value("Employee", employee, "company")
	if not company:
		frappe.throw(_("ไม่พบพนักงาน"), frappe.DoesNotExistError)
	if salary_component not in {c["value"] for c in component_options(company)}:
		frappe.throw(_("รายการ {0} ลงในหน้านี้ไม่ได้ (ระบบคำนวณเอง หรือบริษัทยังไม่ได้ผูกบัญชี)").format(salary_component))
	amount = flt(amount, 2)
	if amount <= 0:
		frappe.throw(_("จำนวนเงินต้องมากกว่า 0"))
	_start, end = hr_attendance.period_of(month)
	slip = slip_submitted(employee, end)
	if slip:
		frappe.throw(_("ยืนยันสลิปเดือนนี้แล้ว ({0}) ลงเพิ่มไม่ได้").format(slip))
	doc = frappe.get_doc(
		{
			"doctype": "Additional Salary",
			"employee": employee,
			"company": company,
			"salary_component": salary_component,
			"amount": amount,
			"payroll_date": end,
			"currency": frappe.get_cached_value("Company", company, "default_currency"),
			"overwrite_salary_structure_amount": 1,
		}
	)
	doc.insert()
	doc.submit()
	if (note or "").strip():
		doc.add_comment("Comment", note.strip())
	return {"name": doc.name}


@frappe.whitelist(methods=["POST"])
def cancel_adjustment(name):
	require()
	doc = frappe.get_doc("Additional Salary", name)
	if doc.salary_component in managed_components(doc.company):
		frappe.throw(_("รายการนี้ระบบสร้างเอง ยกเลิกที่หน้าต้นทาง"))
	slip = slip_submitted(doc.employee, doc.payroll_date)
	if slip:
		frappe.throw(_("ยืนยันสลิปเดือนนี้แล้ว ({0}) ยกเลิกไม่ได้").format(slip))
	doc.cancel()
	return {"name": name}


# ---------------------------------------------------------------- เงินเดือนพนักงาน


def structure_options(company):
	return [
		{"value": s, "label": s}
		for s in frappe.get_all(
			"Salary Structure",
			filters={"company": company, "docstatus": 1, "is_active": "Yes", "payroll_frequency": hr_payroll.PAYROLL_FREQUENCY},
			pluck="name",
		)
	]


@frappe.whitelist()
def get_salaries(company=None):
	require()
	company = hr_attendance.default_company(company)
	today = getdate()
	assignments = frappe.get_all(
		"Salary Structure Assignment",
		filters={"company": company, "docstatus": 1},
		fields=["name", "employee", "salary_structure", "base", "from_date"],
		order_by="from_date asc",
		limit_page_length=0,
	)
	current, upcoming = {}, {}
	for a in assignments:
		if getdate(a.from_date) <= today:
			current[a.employee] = a
		else:
			upcoming.setdefault(a.employee, a)
	rows = []
	for e in frappe.get_all(
		"Employee",
		filters={"company": company, "status": "Active"},
		fields=["name", "employee_name", "designation", "department", "date_of_joining", "custom_project as project"],
		order_by="employee_name asc",
	):
		e.current = current.get(e.name)
		e.upcoming = upcoming.get(e.name)
		rows.append(e)
	return {
		"company": company,
		"rows": rows,
		"structures": structure_options(company),
		"total_base": flt(sum(flt(r.current.base) for r in rows if r.current), 2),
	}


@frappe.whitelist()
def get_salary_history(employee):
	require()
	rows = frappe.get_all(
		"Salary Structure Assignment",
		filters={"employee": employee, "docstatus": 1},
		fields=["name", "salary_structure", "base", "from_date", "owner"],
		order_by="from_date desc",
	)
	for row in rows:
		row.note = last_comment("Salary Structure Assignment", row.name)
	return rows


def tax_slab_for(company, structure):
	slab = frappe.db.get_value(
		"Salary Structure Assignment",
		{"company": company, "salary_structure": structure, "docstatus": 1, "income_tax_slab": ("is", "set")},
		"income_tax_slab",
		order_by="from_date desc",
	)
	return slab or frappe.db.get_value(
		"Income Tax Slab", {"company": company, "docstatus": 1, "disabled": 0}, "name", order_by="effective_from desc"
	)


@frappe.whitelist(methods=["POST"])
def set_salary(employee, salary_structure, base, from_date, note=None):
	"""กำหนด/ปรับเงินเดือน = Salary Structure Assignment ใหม่ (Submit) ใบเดิมคงเป็นประวัติ"""
	require()
	emp = frappe.db.get_value("Employee", employee, ["company", "date_of_joining", "status"], as_dict=True)
	if not emp or emp.status != "Active":
		frappe.throw(_("ไม่พบพนักงาน"), frappe.DoesNotExistError)
	if salary_structure not in {s["value"] for s in structure_options(emp.company)}:
		frappe.throw(_("โครงสร้างเงินเดือนไม่ถูกต้อง"))
	base = flt(base, 2)
	if base <= 0:
		frappe.throw(_("เงินเดือนต้องมากกว่า 0"))
	from_date = getdate(from_date)
	if emp.date_of_joining and from_date < getdate(emp.date_of_joining):
		frappe.throw(_("วันที่มีผลต้องไม่ก่อนวันเริ่มงาน"))
	slip = frappe.db.get_value(
		"Salary Slip", {"employee": employee, "docstatus": 1, "end_date": (">=", from_date)}, "name"
	)
	if slip:
		frappe.throw(_("ยืนยันสลิป {0} ที่ครอบวันที่มีผลแล้ว เลือกวันที่หลังงวดนั้น").format(slip))
	doc = frappe.get_doc(
		{
			"doctype": "Salary Structure Assignment",
			"employee": employee,
			"company": emp.company,
			"salary_structure": salary_structure,
			"from_date": from_date,
			"base": base,
			"currency": frappe.get_cached_value("Company", emp.company, "default_currency"),
			"income_tax_slab": tax_slab_for(emp.company, salary_structure),
			"payroll_payable_account": frappe.get_cached_value("Company", emp.company, "default_payroll_payable_account"),
		}
	)
	doc.insert()
	doc.submit()
	if (note or "").strip():
		doc.add_comment("Comment", note.strip())
	return {"name": doc.name}

