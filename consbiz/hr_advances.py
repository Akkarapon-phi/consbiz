# Copyright (c) 2026, Siricons and contributors
# For license information, please see license.txt

"""เบิกเงิน (หมวด hr ของแอปออฟฟิศ, หน้า hr-advances) ภาพรวมใบเบิก/ใบเคลียร์ทั้งบริษัทสำหรับ HR (ตกลง 2026-11-11)

ใบเบิก = Employee Advance (self_advance.TYPES) ขั้น (stage):
pending รออนุมัติ / rejected ไม่อนุมัติ / to_pay อนุมัติแล้วรอจ่าย (บัญชีทำ Payment Entry) /
repaying เงินเดือนล่วงหน้าที่ยังหักคืนไม่ครบ / to_clear เงินทดรองจ่ายที่ยังเคลียร์ไม่ครบ (overdue = เลยกำหนด) / done จบแล้ว
ใบเคลียร์/สำรองจ่าย = Expense Claim ดูอย่างเดียว อนุมัติที่โมดูลอนุมัติ จ่ายเงินที่ระบบเต็ม (ฝ่ายบัญชี)
"""

import frappe
from frappe.utils import add_months, flt, nowdate

from consbiz import accounting_app, approvals, hr_attendance, row_social, self_advance

HISTORY_MONTHS = 12


def stage_of(row):
	if row.docstatus == 0:
		return "rejected" if row.approval == "Rejected" else "pending"
	if flt(row.paid_amount) < flt(row.advance_amount):
		return "to_pay"
	if row.advance_type == "Salary Advance":
		return "repaying" if row.repayment and row.repayment["remaining"] > 0 else "done"
	return "to_clear" if row.can_clear else "done"


@frappe.whitelist()
def get_advances(company=None):
	hr_attendance.require_hr()
	return advance_rows(company)


@frappe.whitelist()
def get_accounting_advances(company=None):
	if not accounting_app.can_account():
		frappe.throw(frappe._("ไม่มีสิทธิ์เข้าหมวดบัญชี"), frappe.PermissionError)
	frappe.has_permission("Employee Advance", "read", throw=True)
	return advance_rows(company, accounting=True)


def advance_rows(company, accounting=False):
	company = hr_attendance.default_company(company)
	since = add_months(nowdate(), -HISTORY_MONTHS)
	query = frappe.get_list if accounting else frappe.get_all
	rows = query(
		"Employee Advance",
		filters={
			"company": company,
			"docstatus": ("<", 2),
			"custom_advance_type": "Expense Advance" if accounting else ("in", self_advance.TYPES),
		},
		or_filters={"posting_date": (">=", since), "status": ("in", ["Unpaid", "Paid", "Partly Claimed and Returned"])},
		fields=[*self_advance.ADVANCE_FIELDS, "modified"],
		order_by="posting_date desc",
		limit_page_length=500,
	)
	row_social.attach(rows, "Employee Advance")
	for row in rows:
		self_advance.decorate_advance(row)
		row.repayment = approvals.repayment_of(row.name) if row.advance_type == "Salary Advance" and row.docstatus == 1 else None
		row.stage = stage_of(row)
	claims = []
	if not accounting or frappe.has_permission("Expense Claim", "read"):
		filters = {"company": company, "docstatus": ("<", 2), "posting_date": (">=", since)}
		if accounting:
			filters["total_advance_amount"] = (">", 0)
		claims = query(
			"Expense Claim",
			filters=filters,
			fields=["name", "employee", "employee_name", "posting_date", "total_claimed_amount", "total_advance_amount", "approval_status", "status", "docstatus"],
			order_by="posting_date desc",
			limit_page_length=500,
		)
	return {"company": company, "advances": rows, "claims": claims}
