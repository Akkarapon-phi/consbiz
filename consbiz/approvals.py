# Copyright (c) 2026, Siricons and contributors
# For license information, please see license.txt

"""โมดูลอนุมัติ (/conserp/approve, หมวด approve ของ bundle self_app) รวมเอกสารที่รอผู้ใช้อนุมัติไว้ที่เดียว (ตกลง 2026-11-11)

ตอนนี้เฉพาะงาน HR แต่ละชนิดใช้กติกาผู้อนุมัติเดิมของตัวเอง:
- leave   ใบลา (Leave Application Open) Role Leave Approver หรือ HR
- checkin ลงเวลานอกพื้นที่ / แจ้งลืมลงเวลาออก Role Leave Approver หรือ HR
  (ผู้อนุมัติที่ประจำโครงการเห็นเฉพาะพนักงานโครงการเดียวกัน: self_service.scope_employees)
- advance ใบเบิกเงินเดือนล่วงหน้า / เงินสำรองจ่าย (self_advance: Role Expense Approver, เกินวงเงิน Executive Approver)
- claim   ใบเคลียร์ / เบิกค่าใช้จ่ายคืน (self_advance: Role Expense Approver)
ชนิดใหม่: เพิ่มใน KINDS (ฟังก์ชันรายการ + ฟังก์ชันอนุมัติ) และหน้า ApproveInbox.vue
"""

import frappe
from frappe import _
from frappe.utils import add_days, cint, nowdate

from consbiz import self_advance, self_service

HR_ROLES = self_service.HR_ROLES
HISTORY_DAYS = 31
# โมดูลเจ้าของเอกสาร (ตรงกับ MODULES / KINDS[].module ใน public/js/shared/approvals/kinds.js)
# โมดูลอนุมัติเป็นแค่ที่รวม แต่ละโมดูลอนุมัติในหน้าของตัวเองได้ (API อนุมัติชุดเดียวกัน)
MODULES = {"hr": ("leave", "checkin", "advance", "claim")}


def kinds_of(module=None):
	if module and module not in MODULES:
		frappe.throw(_("ไม่รู้จักโมดูล {0}").format(module))
	return MODULES[module] if module else tuple(k for kinds in MODULES.values() for k in kinds)


# ---------------------------------------------------------------- ใบลา


def can_approve_leave(user=None):
	return self_service.is_approver(user)


def leave_filters(pending=True):
	"""รออนุมัติ = ใบลา Open ของพนักงานในขอบเขต / พิจารณาแล้ว = ใบที่ผู้ใช้อนุมัติเอง (HR เห็นทุกใบ)"""
	if pending:
		return self_service.scope_filters({"docstatus": 0, "status": "Open"})
	filters = {
		"docstatus": 1,
		"status": ("in", ["Approved", "Rejected"]),
		"modified": (">=", add_days(nowdate(), -HISTORY_DAYS)),
	}
	if not self_service.is_hr():
		filters["leave_approver"] = frappe.session.user
	return filters


def leave_rows(pending=True):
	from hrms.hr.doctype.leave_application.leave_application import get_leave_balance_on

	if not can_approve_leave():
		return []
	rows = frappe.get_all(
		"Leave Application",
		filters=leave_filters(pending),
		fields=[
			"name",
			"employee",
			"employee_name",
			"leave_type",
			"from_date",
			"to_date",
			"half_day",
			"total_leave_days",
			"description",
			"status",
			"posting_date",
			"leave_approver",
			"modified",
		],
		order_by="from_date asc" if pending else "modified desc",
		limit_page_length=200,
	)
	for row in rows:
		if pending:
			row.balance = get_leave_balance_on(row.employee, row.leave_type, row.from_date, consider_all_leaves_in_the_allocation_period=True)
		row.attachments = frappe.get_all(
			"File",
			filters={"attached_to_doctype": "Leave Application", "attached_to_name": row.name},
			fields=["name", "file_url", "file_name"],
		)
		for f in row.attachments:
			f.url = attachment_url(f.name)
	return rows


def attachment_url(file_name):
	from urllib.parse import urlencode

	return "/api/method/consbiz.approvals.attachment?" + urlencode({"name": file_name})


@frappe.whitelist()
def attachment(name):
	"""ไฟล์แนบของใบลา (private): เจ้าของ ผู้อนุมัติของใบนั้น หรือ HR"""
	file = frappe.get_doc("File", name)
	if file.attached_to_doctype != "Leave Application":
		frappe.throw(_("ไม่มีสิทธิ์ดูไฟล์นี้"), frappe.PermissionError)
	leave = frappe.db.get_value(
		"Leave Application", file.attached_to_name, ["employee", "leave_approver"], as_dict=True
	)
	owner = leave and frappe.db.get_value("Employee", leave.employee, "user_id")
	if not leave or not (
		frappe.session.user in (owner, leave.leave_approver) or self_service.can_approve_employee(leave.employee)
	):
		frappe.throw(_("ไม่มีสิทธิ์ดูไฟล์นี้"), frappe.PermissionError)
	frappe.local.response.filename = file.file_name
	frappe.local.response.filecontent = file.get_content()
	frappe.local.response.type = "download"
	frappe.local.response.display_content_as = "inline"


@frappe.whitelist(methods=["POST"])
def review_leave(name, approve, reason=None):
	"""อนุมัติ/ไม่อนุมัติใบลา = ตั้งสถานะแล้ว Submit ตามแบบ HRMS (ไม่อนุมัติต้องมีเหตุผล บันทึกเป็น Comment)"""
	doc = frappe.get_doc("Leave Application", name)
	if not self_service.can_approve_employee(doc.employee):
		frappe.throw(_("ไม่มีสิทธิ์อนุมัติใบลานี้"), frappe.PermissionError)
	if frappe.db.get_value("Employee", doc.employee, "user_id") == frappe.session.user:
		frappe.throw(_("อนุมัติใบลาของตัวเองไม่ได้"), frappe.PermissionError)
	if doc.docstatus != 0 or doc.status != "Open":
		frappe.throw(_("ใบลานี้พิจารณาแล้ว"))
	approve = cint(approve)
	reason = (reason or "").strip()
	if not approve and not reason:
		frappe.throw(_("ระบุเหตุผลที่ไม่อนุมัติ"))
	doc.status = "Approved" if approve else "Rejected"
	# ผู้อนุมัติจริง (ตอนส่งใบลาตั้งคนแรกในขอบเขตไว้ก่อน) รายงานของ HRMS จึงแสดงถูกคน
	doc.leave_approver = frappe.session.user
	doc.flags.ignore_permissions = True
	doc.submit()
	if reason:
		doc.add_comment("Comment", (_("อนุมัติ: {0}") if approve else _("ไม่อนุมัติ: {0}")).format(reason))
	user = frappe.db.get_value("Employee", doc.employee, "user_id")
	self_advance.notify_users(
		[user],
		doc,
		(_("ใบลา {0} อนุมัติแล้ว") if approve else _("ใบลา {0} ไม่ได้รับอนุมัติ: {1}")).format(doc.name, reason),
	)
	return doc.status


# ---------------------------------------------------------------- รวม


def can_approve_any():
	return {
		"leave": can_approve_leave(),
		"checkin": self_service.can_review(),
		"advance": self_advance.can_approve(),
		"claim": self_advance.APPROVER_ROLE in self_advance.roles(),
	}


def approve_sections():
	return ["approve"] if any(can_approve_any().values()) else []


@frappe.whitelist()
def get_inbox(module=None, quiet=0):
	"""เอกสารที่รอผู้ใช้อนุมัติ (เฉพาะชนิดที่มีสิทธิ์) module = เฉพาะโมดูลนั้น
	quiet = ไม่มีสิทธิ์คืนค่าว่าง (หน้าของโมดูลใช้หาว่าผู้ใช้อนุมัติเอกสารไหนได้)"""
	kinds = kinds_of(module)
	can = {k: v for k, v in can_approve_any().items() if k in kinds}
	if not any(can.values()):
		if cint(quiet):
			return {"can": can}
		frappe.throw(_("ไม่มีเอกสารที่คุณอนุมัติได้"), frappe.PermissionError)
	money = self_advance.get_approvals() if can.get("advance") else {"advances": [], "claims": []}
	return {
		"can": can,
		"leave": leave_rows() if can.get("leave") else [],
		"checkin": self_service.get_reviews() if can.get("checkin") else [],
		"advance": money["advances"],
		"claim": money["claims"] if can.get("claim") else [],
	}


@frappe.whitelist()
def get_history(module=None):
	"""เอกสารที่พิจารณาแล้วใน HISTORY_DAYS วัน (ของผู้ใช้ / HR เห็นทุกคน)"""
	kinds_of(module)
	can = can_approve_any()
	since = add_days(nowdate(), -HISTORY_DAYS)
	hr = self_service.is_hr()
	user = frappe.session.user
	out = {"leave": leave_rows(pending=False) if can["leave"] else []}
	out["checkin"] = self_service.get_reviews(status="Done") if can["checkin"] else []
	advances = []
	if can["advance"]:
		filters = {
			"custom_advance_type": ("in", self_advance.TYPES),
			"custom_approval_status": ("in", ["Approved", "Rejected"]),
			"modified": (">=", since),
		}
		advances = frappe.get_all(
			"Employee Advance",
			filters=filters,
			or_filters=None if hr else {"custom_approved_by": user, "custom_executive_approved_by": user},
			fields=self_advance.ADVANCE_FIELDS,
			order_by="modified desc",
			limit_page_length=200,
		)
		for row in advances:
			self_advance.decorate_advance(row)
	out["advance"] = advances
	claims = []
	if can["claim"]:
		filters = {"modified": (">=", since), "expense_approver": ("is", "set")}
		if not hr:
			filters["expense_approver"] = user
		claims = [
			c
			for c in frappe.get_all(
				"Expense Claim",
				filters=filters,
				fields=self_advance.CLAIM_FIELDS,
				order_by="modified desc",
				limit_page_length=200,
			)
			if c.docstatus == 1 or c.reject_reason
		]
	out["claim"] = claims
	return out


@frappe.whitelist()
def get_summary(project=None):
	"""ตัวเลขบนเมนู/ไอคอนโมดูล: จำนวนที่รออนุมัติแต่ละชนิด"""
	can = can_approve_any()
	counts = {
		"leave": len(leave_rows()) if can["leave"] else 0,
		"checkin": frappe.db.count("Employee Checkin", self_service.review_filters()) if can["checkin"] else 0,
		"advance": 0,
		"claim": 0,
	}
	if can["advance"]:
		money = self_advance.get_approvals()
		counts["advance"] = len(money["advances"])
		counts["claim"] = len(money["claims"]) if can["claim"] else 0
	counts["total"] = sum(counts.values())
	# ตัวเลขของเมนูย่อยรายโมดูล (approve-<โมดูล>)
	for module, kinds in MODULES.items():
		counts[module] = sum(counts[k] for k in kinds)
	return counts


# ---------------------------------------------------------------- ข้อมูลประกอบการอนุมัติ (ตกลง 2026-11-11)
# ใบลา/ลงเวลา: สิทธิ์วันลา ประวัติลา ใครในโครงการลาชนวัน การเข้างานเดือนนี้ (ผู้อนุมัติที่ดูแลพนักงานคนนั้น)
# ใบเบิก/ใบเคลียร์: เงินเดือน วงเงิน ยอดค้างหักคืน ประวัติการเบิก (เฉพาะผู้อนุมัติการเบิก/HR: หัวหน้าหน้างานไม่เห็นเงินเดือน)


def can_see_money(user=None):
	return self_advance.can_approve(user) or self_service.is_hr(user)


def leave_context(employee, from_date=None, to_date=None):
	from frappe.utils import getdate

	from hrms.hr.doctype.leave_application.leave_application import get_leave_details

	from consbiz import hr_attendance

	today = getdate()
	details = get_leave_details(employee, nowdate())
	balances = [
		{
			"leave_type": name,
			"allocated": v.get("total_leaves"),
			"taken": v.get("leaves_taken"),
			"pending": v.get("leaves_pending_approval"),
			"remaining": v.get("remaining_leaves"),
		}
		for name, v in details["leave_allocation"].items()
	]
	recent = frappe.get_all(
		"Leave Application",
		filters={
			"employee": employee,
			"docstatus": ("<", 2),
			"status": ("in", ["Open", "Approved"]),
			"from_date": (">=", f"{today.year}-01-01"),
		},
		fields=["name", "leave_type", "from_date", "to_date", "total_leave_days", "status"],
		order_by="from_date desc",
		limit_page_length=10,
	)
	overlap = []
	project = frappe.db.get_value("Employee", employee, "custom_project")
	if project and from_date and to_date:
		team = frappe.get_all("Employee", filters={"custom_project": project, "status": "Active", "name": ("!=", employee)}, pluck="name")
		overlap = frappe.get_all(
			"Leave Application",
			filters={
				"employee": ("in", team or [""]),
				"docstatus": ("<", 2),
				"status": ("in", ["Open", "Approved"]),
				"from_date": ("<=", to_date),
				"to_date": (">=", from_date),
			},
			fields=["employee_name", "leave_type", "from_date", "to_date", "status"],
			order_by="from_date asc",
		)
	company = frappe.db.get_value("Employee", employee, "company")
	_start, _end, rows = hr_attendance.build(company, nowdate()[:7], employee=employee)
	return {
		"balances": balances,
		"recent": recent,
		"overlap": overlap,
		"project": project,
		"attendance": rows[0]["totals"] if rows else None,
	}


def money_context(employee):
	company = frappe.db.get_value("Employee", employee, "company")
	advances = frappe.get_all(
		"Employee Advance",
		filters={"employee": employee, "docstatus": ("<", 2), "custom_advance_type": ("in", self_advance.TYPES)},
		fields=self_advance.ADVANCE_FIELDS,
		order_by="posting_date desc",
		limit_page_length=8,
	)
	for row in advances:
		self_advance.decorate_advance(row)
		row.repayment = repayment_of(row.name)
	claims = frappe.get_all(
		"Expense Claim",
		filters={"employee": employee, "docstatus": ("<", 2)},
		fields=["name", "posting_date", "total_claimed_amount", "approval_status", "docstatus"],
		order_by="posting_date desc",
		limit_page_length=5,
	)
	return {"limit": self_advance.salary_limit(employee, company), "advances": advances, "claims": claims}


def repayment_of(advance):
	"""งวดหักคืนเงินเดือนล่วงหน้า: ทั้งหมด / หักแล้ว (สลิปยืนยันแล้ว) / คงเหลือ"""
	from frappe.utils import flt

	rows = frappe.get_all(
		"Additional Salary",
		filters={"ref_doctype": "Employee Advance", "ref_docname": advance, "docstatus": 1},
		fields=["name", "employee", "amount", "payroll_date"],
		order_by="payroll_date asc",
	)
	if not rows:
		return None
	done = 0
	for row in rows:
		row.deducted = bool(
			frappe.db.exists(
				"Salary Slip",
				{"employee": row.employee, "docstatus": 1, "start_date": ("<=", row.payroll_date), "end_date": (">=", row.payroll_date)},
			)
		)
		done += flt(row.amount) if row.deducted else 0
	total = sum(flt(r.amount) for r in rows)
	return {"rows": rows, "total": total, "deducted": done, "remaining": total - done}


@frappe.whitelist()
def get_context(employee, kind, from_date=None, to_date=None):
	"""ข้อมูลประกอบของพนักงานในหน้ารายละเอียดเอกสารที่รออนุมัติ"""
	info = frappe.db.get_value(
		"Employee", employee, ["name", "employee_name", "designation", "department", "date_of_joining", "custom_project as project"], as_dict=True
	)
	if not info:
		frappe.throw(_("ไม่พบพนักงาน"), frappe.DoesNotExistError)
	out = {"employee": info}
	if kind in ("leave", "checkin"):
		if not self_service.can_approve_employee(employee):
			frappe.throw(_("ไม่มีสิทธิ์ดูข้อมูลพนักงานคนนี้"), frappe.PermissionError)
		out["leave"] = leave_context(employee, from_date, to_date)
	elif kind in ("advance", "claim"):
		if not can_see_money():
			frappe.throw(_("ไม่มีสิทธิ์ดูข้อมูลการเงินของพนักงาน"), frappe.PermissionError)
		out["money"] = money_context(employee)
	else:
		frappe.throw(_("ชนิดเอกสารไม่ถูกต้อง"))
	return out
