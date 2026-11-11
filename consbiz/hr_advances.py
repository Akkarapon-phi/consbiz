# Copyright (c) 2026, Siricons and contributors
# For license information, please see license.txt

"""เบิกเงิน (หมวด hr ของแอปออฟฟิศ, หน้า hr-advances) ภาพรวมใบเบิก/ใบเคลียร์ทั้งบริษัทสำหรับ HR (ตกลง 2026-11-11)

ใบเบิก = Employee Advance (self_advance.TYPES) ขั้น (stage):
pending รออนุมัติ / rejected ไม่อนุมัติ / to_pay อนุมัติแล้วรอจ่าย (บัญชีทำ Payment Entry) /
repaying เงินเดือนล่วงหน้าที่ยังหักคืนไม่ครบ / to_clear เงินสำรองจ่ายที่ยังเคลียร์ไม่ครบ (overdue = เลยกำหนด) / done จบแล้ว
ใบเคลียร์/เบิกคืน = Expense Claim ดูอย่างเดียว อนุมัติที่โมดูลอนุมัติ จ่ายเงินที่ระบบเต็ม (ฝ่ายบัญชี)
"""

import frappe
from frappe.utils import add_months, flt, nowdate

from consbiz import approvals, hr_attendance, self_advance

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
	company = hr_attendance.default_company(company)
	since = add_months(nowdate(), -HISTORY_MONTHS)
	rows = frappe.get_all(
		"Employee Advance",
		filters={"company": company, "docstatus": ("<", 2), "custom_advance_type": ("in", self_advance.TYPES)},
		or_filters={"posting_date": (">=", since), "status": ("in", ["Unpaid", "Paid", "Partly Claimed and Returned"])},
		fields=self_advance.ADVANCE_FIELDS,
		order_by="posting_date desc",
		limit_page_length=500,
	)
	for row in rows:
		self_advance.decorate_advance(row)
		row.repayment = approvals.repayment_of(row.name) if row.advance_type == "Salary Advance" and row.docstatus == 1 else None
		row.stage = stage_of(row)
	claims = frappe.get_all(
		"Expense Claim",
		filters={"company": company, "docstatus": ("<", 2), "posting_date": (">=", since)},
		fields=["name", "employee", "employee_name", "posting_date", "total_claimed_amount", "total_advance_amount", "approval_status", "status", "docstatus"],
		order_by="posting_date desc",
		limit_page_length=500,
	)
	return {"company": company, "advances": rows, "claims": claims}
