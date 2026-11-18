# Copyright (c) 2026, Siricons and contributors
# For license information, please see license.txt

"""พนักงาน (กลุ่มพนักงานของหมวดบุคคล หน้า hr-employees, office_app/views/hr/HrEmployees.vue) ตกลง 2026-11-17

รายการพนักงาน + แผงตัวอย่าง (จอกว้าง) / หน้าเต็ม (hr-employee/<รหัส>) แสดงข้อมูลหลัก เวลาทำงานเดือนนี้ วันลาคงเหลือ
ค่าจ้าง (เฉพาะผู้ทำเงินเดือน hr_payroll.can_manage) และเอกสารทุกชนิดที่ผูกกับพนักงาน (LINKS) เฉพาะชนิดที่ผู้ใช้อ่านได้
แก้ข้อมูลพนักงานที่หมวดข้อมูลหลัก (md-doc/md-employees/<รหัส>)
"""

import frappe
from frappe import _
from frappe.utils import add_days, date_diff, flt, getdate, nowdate

from consbiz import hr_attendance, hr_payroll

# เอกสารที่ผูกกับพนักงาน: (doctype, ป้าย, ช่องวันที่, ช่องสรุป, หน้าในแอป (kind ของ hr-doc) / None = ระบบเต็ม, เฉพาะผู้ทำเงินเดือน)
LINKS = (
	("Employment Contract", _("สัญญาจ้าง"), "date", "base", "hr-contracts", False),
	("Employee Warning", _("ใบเตือน"), "date", "level", "hr-warnings", False),
	("Leave Application", _("ใบลา"), "from_date", "leave_type", None, False),
	("Attendance Request", _("แจ้งมาทำงาน"), "from_date", "reason", None, False),
	("Shift Assignment", _("กำหนดกะ"), "start_date", "shift_type", None, False),
	("Employee Advance", _("ใบเบิก"), "posting_date", "advance_amount", None, False),
	("Expense Claim", _("เคลียร์/สำรองจ่าย"), "posting_date", "total_claimed_amount", None, False),
	("Salary Slip", _("สลิปเงินเดือน"), "start_date", "net_pay", None, True),
	("Salary Structure Assignment", _("ค่าจ้าง"), "from_date", "base", None, True),
	("Additional Salary", _("เพิ่ม/หัก"), "payroll_date", "amount", None, True),
	("WHT Employee", _("50 ทวิ"), "date", None, "hr-wht", True),
)
LIST_FIELDS = [
	"name",
	"employee_name",
	"image",
	"status",
	"company",
	"department",
	"designation",
	"custom_project as project",
	"date_of_joining",
	"relieving_date",
	"user_id",
	"cell_number",
]


@frappe.whitelist()
def get_employees(company=None):
	hr_attendance.require_hr()
	company = hr_attendance.default_company(company)
	rows = frappe.get_all(
		"Employee", filters={"company": company}, fields=LIST_FIELDS, order_by="status asc, employee_name asc", limit_page_length=0
	)
	projects = {r.project for r in rows if r.project}
	names = dict(frappe.get_all("Project", filters={"name": ("in", list(projects) or [""])}, fields=["name", "project_name"], as_list=True))
	probation = set(
		frappe.get_all(
			"Employment Contract",
			filters={"docstatus": 1, "probation": ("in", ("", None)), "prob_end_date": (">=", add_days(nowdate(), -30))},
			pluck="employee",
		)
	)
	warnings = {}
	if frappe.db.exists("DocType", "Employee Warning") and frappe.has_permission("Employee Warning", "read"):
		for employee in frappe.get_all("Employee Warning", filters={"docstatus": 1, "date": (">=", add_days(nowdate(), -365))}, pluck="employee"):
			warnings[employee] = warnings.get(employee, 0) + 1
	for row in rows:
		row.project_name = names.get(row.project)
		row.probation = row.name in probation
		row.warnings = warnings.get(row.name, 0)
	return {"company": company, "rows": rows}


def linked_docs(employee, can_pay):
	out = []
	for doctype, label, date_field, value_field, app_kind, pay_only in LINKS:
		if pay_only and not can_pay:
			continue
		if not frappe.db.exists("DocType", doctype) or not frappe.has_permission(doctype, "read"):
			continue
		fields = ["name", "docstatus", f"{date_field} as date"]
		if value_field:
			fields.append(f"{value_field} as value")
		meta = frappe.get_meta(doctype)
		if meta.has_field("status"):
			fields.append("status")
		rows = frappe.get_all(
			doctype,
			filters={"employee": employee, "docstatus": ("<", 2)},
			fields=fields,
			order_by=f"{date_field} desc, creation desc",
			limit_page_length=6,
		)
		count = frappe.db.count(doctype, {"employee": employee, "docstatus": ("<", 2)})
		out.append(
			{
				"doctype": doctype,
				"label": label,
				"count": count,
				"app_kind": app_kind,
				"slug": doctype.lower().replace(" ", "-"),
				"rows": rows,
			}
		)
	return out


@frappe.whitelist()
def get_employee(name):
	"""ข้อมูลพนักงาน 1 คน + เวลาทำงานเดือนนี้ + วันลาคงเหลือ + ค่าจ้าง (ผู้ทำเงินเดือน) + เอกสารที่ผูก"""
	from hrms.hr.doctype.leave_application.leave_application import get_leave_details

	hr_attendance.require_hr()
	doc = frappe.get_doc("Employee", name)
	doc.check_permission("read")
	info = {field: doc.get(field) for field in (
		"name", "employee_name", "image", "status", "company", "department", "designation", "gender", "date_of_birth",
		"date_of_joining", "relieving_date", "user_id", "cell_number", "personal_email", "default_shift",
		"custom_checkin_location", "custom_project", "employment_type", "branch",
	)}
	info["project_name"] = doc.custom_project and frappe.db.get_value("Project", doc.custom_project, "project_name")
	today = getdate()
	joined = getdate(doc.date_of_joining) if doc.date_of_joining else None
	if joined:
		days = date_diff(doc.relieving_date or today, joined)
		info["tenure"] = {"years": days // 365, "months": days % 365 // 30}
	can_pay = hr_payroll.can_manage()
	month = nowdate()[:7]
	_start, _end, rows = hr_attendance.build(doc.company, month, employee=doc.name)
	leave = []
	try:
		for leave_type, v in get_leave_details(doc.name, nowdate())["leave_allocation"].items():
			leave.append({"leave_type": leave_type, "allocated": flt(v.get("total_leaves")), "taken": flt(v.get("leaves_taken")), "remaining": flt(v.get("remaining_leaves"))})
	except Exception:
		leave = []
	pay = None
	if can_pay:
		ssa = frappe.get_all(
			"Salary Structure Assignment",
			filters={"employee": doc.name, "docstatus": 1},
			fields=["from_date", "base"],
			order_by="from_date desc",
			limit_page_length=5,
		)
		current = next((r for r in ssa if getdate(r.from_date) <= today), None)
		pay = {"current": current, "upcoming": [r for r in ssa if getdate(r.from_date) > today]}
	return {
		"info": info,
		"month": month,
		"attendance": rows[0]["totals"] if rows else None,
		"leave": leave,
		"pay": pay,
		"docs": linked_docs(doc.name, can_pay),
		"can_edit": bool(doc.has_permission("write")),
	}
