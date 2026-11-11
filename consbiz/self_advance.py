# Copyright (c) 2026, Siricons and contributors
# For license information, please see license.txt

"""เบิกเงินในแอป Self Service (ตกลง 2026-11-11) ครอบ Employee Advance / Expense Claim / Additional Salary ของ HRMS

ประเภท (Employee Advance.custom_advance_type):
- Salary Advance เบิกเงินเดือนล่วงหน้า: วงเงิน = Company.custom_salary_advance_limit_percent (50%) ของ base ใน Salary Structure Assignment
  รวมใบที่ยังหักคืนไม่ครบ เกินวงเงิน = ผู้บริหาร (Role Executive Approver) ต้องอนุมัติด้วย
  หักคืน 1..MAX_INSTALLMENTS งวด: จ่ายเงินแล้ว (Payment Entry submit) ระบบสร้าง Additional Salary (Company.custom_salary_advance_component) งวดละเดือน
  งวดแรก = เดือนที่จ่าย (ถ้าสลิปเดือนนั้นออกแล้ว = เดือนถัดไป) งวดสุดท้ายรับเศษ
- Expense Advance เงินสำรองจ่าย: จ่ายแล้วกำหนดเคลียร์ = วันจ่าย + Company.custom_expense_clear_days (15) วัน
  เคลียร์ด้วย Expense Claim ที่ตัดยอด Advance เลยกำหนดแล้วแจ้งเตือนพนักงาน (remind_overdue_clearing) ไม่หักเงินเอง เงินเหลือฝ่ายบัญชีรับคืนในระบบเต็ม
เบิกค่าใช้จ่ายคืน (สำรองจ่ายเอง) = Expense Claim ไม่มี Advance ทุกรายการต้องแนบรูปบิล (Expense Claim Detail.custom_receipt)

อนุมัติ: ผู้มี Role Expense Approver (ไม่ใช้ Reports To เพราะตั้งได้คนเดียว) อนุมัติในแอป = Submit (Employee Advance / Expense Claim Approved)
ไม่อนุมัติ = คงเป็นร่าง + เหตุผล อนุมัติของตัวเองไม่ได้ จ่ายเงิน/รับคืนเงินเหลือ ฝ่ายบัญชีทำ Payment Entry ในระบบเต็ม
before_submit ของ Employee Advance (doc_events) บังคับกติกาเดียวกันเมื่อ Submit จากระบบเต็ม
"""

import calendar

import frappe
from frappe import _
from frappe.utils import add_days, add_months, cint, flt, get_first_day, getdate, nowdate

from consbiz import store_app
from consbiz.self_service import LIST_LIMIT, my_employee

APPROVER_ROLE = "Expense Approver"
EXECUTIVE_ROLE = "Executive Approver"
MAX_INSTALLMENTS = 6
DEFAULT_LIMIT_PERCENT = 50
DEFAULT_CLEAR_DAYS = 15
# แจ้งเตือนเคลียร์ซ้ำทุกกี่วันหลังเลยกำหนด
REMIND_EVERY_DAYS = 3
TYPES = ("Salary Advance", "Expense Advance")
ADVANCE_FIELDS = [
	"name",
	"custom_advance_type as advance_type",
	"purpose",
	"posting_date",
	"advance_amount",
	"paid_amount",
	"claimed_amount",
	"return_amount",
	"status",
	"docstatus",
	"currency",
	"custom_installments as installments",
	"custom_required_date as required_date",
	"custom_approval_status as approval",
	"custom_over_limit as over_limit",
	"custom_reject_reason as reject_reason",
	"custom_clear_due_date as clear_due_date",
	"custom_approved_by as approved_by",
	"custom_executive_approved_by as executive_approved_by",
	"employee",
	"employee_name",
]
CLAIM_FIELDS = [
	"name",
	"posting_date",
	"total_claimed_amount",
	"total_sanctioned_amount",
	"total_advance_amount",
	"grand_total",
	"approval_status",
	"status",
	"docstatus",
	"remark",
	"custom_reject_reason as reject_reason",
	"employee",
	"employee_name",
]


def roles(user=None):
	return set(frappe.get_roles(user))


def can_approve(user=None):
	return bool(roles(user) & {APPROVER_ROLE, EXECUTIVE_ROLE})


def is_executive(user=None):
	return EXECUTIVE_ROLE in roles(user)


def company_setting(company, field, default):
	value = frappe.db.get_value("Company", company, field)
	return default if value in (None, "") else value


# ---------------------------------------------------------------- วงเงินเงินเดือนล่วงหน้า


def base_salary(employee):
	return flt(
		frappe.db.get_value(
			"Salary Structure Assignment",
			{"employee": employee, "docstatus": 1, "from_date": ("<=", nowdate())},
			"base",
			order_by="from_date desc",
		)
	)


def outstanding_salary_advance(employee, exclude=None):
	"""ยอดเงินเดือนล่วงหน้าที่ยังหักคืนไม่ครบ (รวมใบที่รออนุมัติ) ไม่นับใบที่ไม่อนุมัติ/ยกเลิก"""
	filters = {
		"employee": employee,
		"custom_advance_type": "Salary Advance",
		"docstatus": ("<", 2),
		"custom_approval_status": ("!=", "Rejected"),
		"status": ("not in", ["Returned", "Claimed", "Partly Claimed and Returned", "Cancelled"]),
	}
	if exclude:
		filters["name"] = ("!=", exclude)
	rows = frappe.get_all("Employee Advance", filters=filters, fields=["advance_amount", "return_amount"])
	return sum(flt(r.advance_amount) - flt(r.return_amount) for r in rows)


def salary_limit(employee, company, exclude=None):
	base = base_salary(employee)
	percent = flt(company_setting(company, "custom_salary_advance_limit_percent", DEFAULT_LIMIT_PERCENT))
	limit = flt(base * percent / 100, 2)
	used = outstanding_salary_advance(employee, exclude)
	return {"base": base, "percent": percent, "limit": limit, "used": used, "available": max(0, limit - used)}


# ---------------------------------------------------------------- ข้อมูลของพนักงาน


@frappe.whitelist()
def get_advance_data():
	"""หน้าเบิกเงิน: ใบเบิก (ล่วงหน้า/สำรองจ่าย) + ใบเคลียร์/เบิกคืน ของตัวเอง + วงเงิน + ประเภทค่าใช้จ่าย"""
	employee = my_employee()
	advances = frappe.get_all(
		"Employee Advance",
		filters={"employee": employee.name, "custom_advance_type": ("in", TYPES)},
		fields=ADVANCE_FIELDS,
		order_by="posting_date desc, creation desc",
		limit_page_length=LIST_LIMIT,
	)
	today = getdate()
	for row in advances:
		decorate_advance(row, today)
	claims = frappe.get_all(
		"Expense Claim",
		filters={"employee": employee.name},
		fields=CLAIM_FIELDS,
		order_by="posting_date desc, creation desc",
		limit_page_length=LIST_LIMIT,
	)
	for row in claims:
		row.can_delete = row.docstatus == 0 and row.approval_status == "Draft" and not row.reject_reason
	return {
		"advances": advances,
		"claims": claims,
		"salary": salary_limit(employee.name, employee.company),
		"max_installments": MAX_INSTALLMENTS,
		"expense_types": frappe.get_all("Expense Claim Type", pluck="name", order_by="name asc"),
	}


def decorate_advance(row, today=None):
	today = today or getdate()
	row.unclaimed = max(0, flt(row.paid_amount) - flt(row.claimed_amount) - flt(row.return_amount))
	row.can_delete = row.docstatus == 0 and row.approval in ("Pending", "Pending Executive", None, "")
	row.can_clear = bool(
		row.advance_type == "Expense Advance" and row.docstatus == 1 and row.unclaimed > 0
	)
	row.overdue = bool(row.can_clear and row.clear_due_date and getdate(row.clear_due_date) < today)
	return row


@frappe.whitelist(methods=["POST"])
def request_advance(advance_type, amount, purpose, installments=1, required_date=None):
	"""ขอเบิกเงินเดือนล่วงหน้า / เงินสำรองจ่าย = Employee Advance ร่าง รอผู้อนุมัติ (Expense Approver)"""
	employee = my_employee()
	if advance_type not in TYPES:
		frappe.throw(_("ประเภทการเบิกไม่ถูกต้อง"))
	amount = flt(amount, 2)
	if amount <= 0:
		frappe.throw(_("ระบุจำนวนเงิน"))
	purpose = (purpose or "").strip()
	if not purpose:
		frappe.throw(_("ระบุวัตถุประสงค์"))
	installments = cint(installments) or 1
	if advance_type == "Salary Advance" and not 1 <= installments <= MAX_INSTALLMENTS:
		frappe.throw(_("หักคืนได้ 1 ถึง {0} งวด").format(MAX_INSTALLMENTS))
	values = {
		"doctype": "Employee Advance",
		"employee": employee.name,
		"company": employee.company,
		"posting_date": nowdate(),
		"purpose": purpose,
		"advance_amount": amount,
		"currency": frappe.get_cached_value("Company", employee.company, "default_currency"),
		"exchange_rate": 1,
		"custom_advance_type": advance_type,
		"custom_installments": installments if advance_type == "Salary Advance" else 1,
		"custom_required_date": getdate(required_date) if required_date else None,
		"custom_approval_status": "Pending",
		"repay_unclaimed_amount_from_salary": 1 if advance_type == "Salary Advance" else 0,
	}
	if advance_type == "Salary Advance":
		limit = salary_limit(employee.name, employee.company)
		values.update(
			custom_base_salary=limit["base"],
			custom_limit_amount=limit["limit"],
			custom_over_limit=1 if limit["used"] + amount > limit["limit"] else 0,
		)
	doc = frappe.get_doc(values)
	doc.insert(ignore_permissions=True)
	notify_users(
		approver_users(),
		doc,
		_("{0} ขอ{1} {2} บาท").format(employee.employee_name, type_label(advance_type), frappe.format(amount, "Currency")),
	)
	return decorate_advance(frappe.get_all("Employee Advance", filters={"name": doc.name}, fields=ADVANCE_FIELDS)[0])


def type_label(advance_type):
	return {"Salary Advance": _("เบิกเงินเดือนล่วงหน้า"), "Expense Advance": _("เบิกเงินสำรองจ่าย")}.get(
		advance_type, advance_type
	)


@frappe.whitelist(methods=["POST"])
def delete_advance(name):
	"""ถอนใบเบิกที่ยังไม่อนุมัติของตัวเอง"""
	employee = my_employee()
	row = frappe.db.get_value(
		"Employee Advance", name, ["employee", "docstatus", "custom_approval_status"], as_dict=True
	)
	if not row or row.employee != employee.name:
		frappe.throw(_("ไม่พบใบเบิก"), frappe.PermissionError)
	if row.docstatus != 0 or row.custom_approval_status == "Rejected":
		frappe.throw(_("ใบเบิกที่พิจารณาแล้วถอนไม่ได้"))
	frappe.delete_doc("Employee Advance", name, ignore_permissions=True)


# ---------------------------------------------------------------- เคลียร์ / เบิกค่าใช้จ่ายคืน (Expense Claim)


def clean_rows(rows):
	rows = frappe.parse_json(rows) if isinstance(rows, str) else rows
	if not rows:
		frappe.throw(_("เพิ่มรายการค่าใช้จ่ายอย่างน้อย 1 รายการ"))
	types = set(frappe.get_all("Expense Claim Type", pluck="name"))
	out = []
	for i, row in enumerate(rows, 1):
		row = frappe._dict(row)
		if row.get("expense_type") not in types:
			frappe.throw(_("รายการที่ {0}: เลือกประเภทค่าใช้จ่าย").format(i))
		if flt(row.get("amount")) <= 0:
			frappe.throw(_("รายการที่ {0}: ระบุจำนวนเงิน").format(i))
		if not row.get("receipt"):
			frappe.throw(_("รายการที่ {0}: แนบรูปบิล/ใบเสร็จ").format(i))
		out.append(row)
	return out


def own_receipt(file_name):
	"""ไฟล์รูปบิลที่ผู้ใช้เพิ่งอัปโหลดเอง (ยังไม่ผูกเอกสาร) → file_url"""
	row = frappe.db.get_value(
		"File", file_name, ["file_url", "owner", "attached_to_name"], as_dict=True
	)
	if not row or row.owner != frappe.session.user or row.attached_to_name:
		frappe.throw(_("รูปบิลไม่ถูกต้อง แนบใหม่อีกครั้ง"))
	return row.file_url


@frappe.whitelist(methods=["POST"])
def submit_claim(rows, remark=None, advance=None):
	"""ส่งใบเคลียร์ (advance = Employee Advance เงินสำรองจ่าย) หรือเบิกค่าใช้จ่ายคืน (ไม่มี advance)
	= Expense Claim ร่าง approval_status Draft รอผู้อนุมัติ"""
	from hrms.hr.doctype.expense_claim.expense_claim import get_expense_claim_advances

	employee = my_employee()
	rows = clean_rows(rows)
	company = employee.company
	payable = frappe.db.get_value("Company", company, "default_expense_claim_payable_account")
	if not payable:
		frappe.throw(_("บริษัทยังไม่ได้ตั้งบัญชีเจ้าหนี้ค่าใช้จ่ายพนักงาน (Default Expense Claim Payable Account) ติดต่อฝ่ายบัญชี"))
	doc = frappe.new_doc("Expense Claim")
	doc.update(
		{
			"employee": employee.name,
			"company": company,
			"posting_date": nowdate(),
			"currency": frappe.get_cached_value("Company", company, "default_currency"),
			"exchange_rate": 1,
			"payable_account": payable,
			"cost_center": frappe.get_cached_value("Company", company, "cost_center"),
			"project": employee.custom_project,
			"remark": (remark or "").strip(),
			"approval_status": "Draft",
		}
	)
	files = []
	cost_center = frappe.get_cached_value("Company", company, "cost_center")
	for row in rows:
		files.append(row.receipt)
		doc.append(
			"expenses",
			{
				"expense_date": getdate(row.get("expense_date") or nowdate()),
				"expense_type": row.expense_type,
				"description": (row.get("description") or row.expense_type).strip(),
				"amount": flt(row.amount, 2),
				"sanctioned_amount": flt(row.amount, 2),
				"custom_receipt": own_receipt(row.receipt),
				"cost_center": cost_center,
				"project": employee.custom_project,
			},
		)
	if advance:
		info = frappe.db.get_value(
			"Employee Advance",
			advance,
			["employee", "docstatus", "custom_advance_type", "paid_amount", "claimed_amount", "return_amount", "name", "purpose", "posting_date", "advance_account"],
			as_dict=True,
		)
		if not info or info.employee != employee.name or info.docstatus != 1:
			frappe.throw(_("ไม่พบใบเบิกเงินสำรองจ่าย"), frappe.PermissionError)
		unclaimed = flt(info.paid_amount) - flt(info.claimed_amount) - flt(info.return_amount)
		if unclaimed <= 0:
			frappe.throw(_("ใบเบิก {0} เคลียร์ครบแล้ว").format(advance))
		if frappe.db.exists(
			"Expense Claim Advance", {"employee_advance": advance, "docstatus": 0, "parenttype": "Expense Claim"}
		):
			frappe.throw(_("ใบเบิก {0} มีใบเคลียร์ที่รออนุมัติอยู่แล้ว").format(advance))
		get_expense_claim_advances(doc, info)
		if not doc.advances:
			frappe.throw(_("ใบเบิก {0} ยังไม่ได้จ่ายเงิน").format(advance))
		# ตัดยอดเท่าค่าใช้จ่าย ไม่เกินยอดคงค้างของแต่ละการจ่าย (1 ใบเบิกอาจจ่ายหลายครั้ง)
		left = sum(flt(r.amount) for r in rows)
		for adv in doc.advances:
			adv.allocated_amount = max(0, min(flt(adv.unclaimed_amount) - flt(adv.return_amount), left))
			left -= adv.allocated_amount
	doc.flags.ignore_permissions = True
	doc.insert(ignore_permissions=True)
	store_app.attach_files(files, "Expense Claim", doc.name)
	notify_users(
		approver_users(),
		doc,
		_("{0} ส่ง{1} {2} บาท").format(
			employee.employee_name,
			_("ใบเคลียร์เงินสำรองจ่าย") if advance else _("เบิกค่าใช้จ่ายคืน"),
			frappe.format(doc.total_claimed_amount, "Currency"),
		),
	)
	return {"name": doc.name, "total": doc.total_claimed_amount, "advance": flt(doc.total_advance_amount)}


@frappe.whitelist(methods=["POST"])
def delete_claim(name):
	employee = my_employee()
	row = frappe.db.get_value(
		"Expense Claim", name, ["employee", "docstatus", "approval_status", "custom_reject_reason"], as_dict=True
	)
	if not row or row.employee != employee.name:
		frappe.throw(_("ไม่พบใบเบิก"), frappe.PermissionError)
	if row.docstatus != 0 or row.approval_status != "Draft" or row.custom_reject_reason:
		frappe.throw(_("ใบที่พิจารณาแล้วถอนไม่ได้"))
	frappe.delete_doc("Expense Claim", name, ignore_permissions=True)


@frappe.whitelist()
def get_claim(name):
	"""รายละเอียดใบเคลียร์/เบิกคืน: เจ้าของหรือผู้อนุมัติ"""
	doc = frappe.get_doc("Expense Claim", name)
	mine = frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "name")
	if doc.employee != mine and not can_approve():
		frappe.throw(_("ไม่มีสิทธิ์ดูใบนี้"), frappe.PermissionError)
	data = {field.split(" as ")[-1]: doc.get(field.split(" as ")[0]) for field in CLAIM_FIELDS}
	data["expenses"] = [
		{
			"expense_date": r.expense_date,
			"expense_type": r.expense_type,
			"description": r.description,
			"amount": r.amount,
			"receipt": r.custom_receipt and receipt_url(name, r.idx),
		}
		for r in doc.expenses
	]
	data["advances"] = [{"employee_advance": a.employee_advance, "allocated_amount": a.allocated_amount} for a in doc.advances]
	return data


def receipt_url(name, idx):
	from urllib.parse import urlencode

	return "/api/method/consbiz.self_advance.receipt?" + urlencode({"name": name, "idx": idx})


@frappe.whitelist()
def receipt(name, idx):
	"""รูปบิลของใบเคลียร์ (ไฟล์ private): เจ้าของและผู้อนุมัติ"""
	doc = frappe.get_doc("Expense Claim", name)
	mine = frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "name")
	if doc.employee != mine and not can_approve():
		frappe.throw(_("ไม่มีสิทธิ์ดูรูปนี้"), frappe.PermissionError)
	row = next((r for r in doc.expenses if r.idx == cint(idx)), None)
	file_name = row and row.custom_receipt and frappe.db.get_value("File", {"file_url": row.custom_receipt})
	if not file_name:
		frappe.throw(_("ไม่พบรูปบิล"), frappe.DoesNotExistError)
	file = frappe.get_doc("File", file_name)
	frappe.local.response.filename = file.file_name
	frappe.local.response.filecontent = file.get_content()
	frappe.local.response.type = "download"
	frappe.local.response.display_content_as = "inline"


# ---------------------------------------------------------------- อนุมัติ (Expense Approver / Executive Approver)


def approver_users():
	from frappe.utils.user import get_users_with_role

	return get_users_with_role(APPROVER_ROLE)


def executive_users():
	from frappe.utils.user import get_users_with_role

	return get_users_with_role(EXECUTIVE_ROLE)


def notify_users(users, doc, subject):
	from frappe.desk.doctype.notification_log.notification_log import enqueue_create_notification

	users = [u for u in set(users or []) if u and u != frappe.session.user]
	if users:
		enqueue_create_notification(
			users,
			{
				"type": "Alert",
				"document_type": doc.doctype,
				"document_name": doc.name,
				"subject": subject,
				"from_user": frappe.session.user,
			},
		)


def check_approver():
	if not can_approve():
		frappe.throw(_("ไม่มีสิทธิ์อนุมัติการเบิก (ต้องมี Role {0})").format(APPROVER_ROLE), frappe.PermissionError)


def check_not_self(employee):
	if frappe.db.get_value("Employee", employee, "user_id") == frappe.session.user:
		frappe.throw(_("อนุมัติใบเบิกของตัวเองไม่ได้"), frappe.PermissionError)


def pending_advance_states():
	"""ผู้อนุมัติเห็น Pending ผู้บริหารเห็นทั้ง Pending และ Pending Executive"""
	states = []
	if APPROVER_ROLE in roles():
		states.append("Pending")
	if is_executive():
		states += ["Pending", "Pending Executive"]
	return list(dict.fromkeys(states))


@frappe.whitelist()
def get_approvals():
	"""ใบเบิกและใบเคลียร์/เบิกคืนที่รออนุมัติ"""
	check_approver()
	me = frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "name")
	advances = frappe.get_all(
		"Employee Advance",
		filters={
			"docstatus": 0,
			"custom_advance_type": ("in", TYPES),
			"custom_approval_status": ("in", pending_advance_states() or [""]),
			"employee": ("!=", me or ""),
		},
		fields=ADVANCE_FIELDS + ["custom_limit_amount as limit_amount", "custom_base_salary as base_salary"],
		order_by="posting_date asc, creation asc",
		limit_page_length=200,
	)
	for row in advances:
		decorate_advance(row)
		row.needs_executive = bool(row.over_limit and not is_executive())
	claims = (
		frappe.get_all(
			"Expense Claim",
			filters={
				"docstatus": 0,
				"approval_status": "Draft",
				"custom_reject_reason": ("is", "not set"),
				"employee": ("!=", me or ""),
			},
			fields=CLAIM_FIELDS,
			order_by="posting_date asc, creation asc",
			limit_page_length=200,
		)
		if APPROVER_ROLE in roles()
		else []
	)
	return {"advances": advances, "claims": claims, "executive": is_executive()}


@frappe.whitelist(methods=["POST"])
def review_advance(name, approve, reason=None):
	"""อนุมัติ: ไม่เกินวงเงิน หรือผู้บริหารอนุมัติ = Submit / เกินวงเงินโดยผู้อนุมัติทั่วไป = ส่งต่อผู้บริหาร (Pending Executive)
	ไม่อนุมัติ = คงร่าง + เหตุผล"""
	check_approver()
	doc = frappe.get_doc("Employee Advance", name)
	check_not_self(doc.employee)
	if doc.docstatus != 0 or doc.custom_approval_status not in pending_advance_states():
		frappe.throw(_("ใบเบิกนี้พิจารณาแล้วหรือรอผู้บริหาร"))
	user = frappe.session.user
	employee_user = frappe.db.get_value("Employee", doc.employee, "user_id")
	if not cint(approve):
		reason = (reason or "").strip()
		if not reason:
			frappe.throw(_("ระบุเหตุผลที่ไม่อนุมัติ"))
		doc.db_set({"custom_approval_status": "Rejected", "custom_reject_reason": reason, "custom_approved_by": user})
		notify_users([employee_user], doc, _("ใบเบิก {0} ไม่ได้รับอนุมัติ: {1}").format(doc.name, reason))
		return "Rejected"

	if doc.custom_advance_type == "Salary Advance":
		# วงเงินอาจเปลี่ยนระหว่างรอ (ใบอื่นถูกอนุมัติ/หักคืน)
		limit = salary_limit(doc.employee, doc.company, exclude=doc.name)
		doc.custom_over_limit = 1 if limit["used"] + flt(doc.advance_amount) > limit["limit"] else 0
		doc.custom_limit_amount = limit["limit"]
	if doc.custom_over_limit and not is_executive():
		doc.custom_approval_status = "Pending Executive"
		doc.custom_approved_by = user
		doc.save(ignore_permissions=True)
		notify_users(
			executive_users(),
			doc,
			_("{0} ขอเบิกเงินเดือนล่วงหน้าเกินวงเงิน รอผู้บริหารอนุมัติ").format(doc.employee_name),
		)
		return "Pending Executive"
	if doc.custom_over_limit:
		doc.custom_executive_approved_by = user
	if not doc.custom_approved_by:
		doc.custom_approved_by = user
	doc.custom_approval_status = "Approved"
	doc.flags.consbiz_approved = True
	# ตรวจ Role เองแล้ว (ผู้บริหารอาจไม่มีสิทธิ์ Submit ของ HRMS)
	doc.flags.ignore_permissions = True
	doc.submit()
	notify_users(
		[employee_user], doc, _("ใบเบิก {0} อนุมัติแล้ว รอฝ่ายบัญชีจ่ายเงิน").format(doc.name)
	)
	return "Approved"


def guard_advance_submit(doc, method=None):
	"""doc_events Employee Advance.before_submit: ใบที่ขอจากแอปต้องผ่านการอนุมัติ (Submit จากระบบเต็มก็ใช้กติกานี้)"""
	if not doc.custom_advance_type:
		return
	check_not_self(doc.employee)
	if doc.flags.consbiz_approved:
		return
	if doc.custom_over_limit and not is_executive():
		frappe.throw(_("ใบเบิกนี้เกินวงเงิน ต้องให้ผู้บริหาร (Role {0}) อนุมัติ").format(EXECUTIVE_ROLE))
	doc.custom_approval_status = "Approved"
	doc.custom_approved_by = doc.custom_approved_by or frappe.session.user
	if doc.custom_over_limit:
		doc.custom_executive_approved_by = frappe.session.user


@frappe.whitelist(methods=["POST"])
def review_claim(name, approve, reason=None):
	"""อนุมัติใบเคลียร์/เบิกคืน = approval_status Approved + Submit / ไม่อนุมัติ = คงร่าง + เหตุผล"""
	check_approver()
	if APPROVER_ROLE not in roles():
		frappe.throw(_("ไม่มีสิทธิ์อนุมัติใบเคลียร์ (ต้องมี Role {0})").format(APPROVER_ROLE), frappe.PermissionError)
	doc = frappe.get_doc("Expense Claim", name)
	check_not_self(doc.employee)
	if doc.docstatus != 0 or doc.approval_status != "Draft" or doc.custom_reject_reason:
		frappe.throw(_("ใบนี้พิจารณาแล้ว"))
	employee_user = frappe.db.get_value("Employee", doc.employee, "user_id")
	if not cint(approve):
		reason = (reason or "").strip()
		if not reason:
			frappe.throw(_("ระบุเหตุผลที่ไม่อนุมัติ"))
		doc.db_set({"custom_reject_reason": reason, "expense_approver": frappe.session.user})
		notify_users([employee_user], doc, _("ใบเบิก {0} ไม่ได้รับอนุมัติ: {1}").format(doc.name, reason))
		return "Rejected"
	doc.approval_status = "Approved"
	doc.expense_approver = frappe.session.user
	doc.flags.ignore_permissions = True
	doc.submit()
	notify_users([employee_user], doc, _("ใบเบิก {0} อนุมัติแล้ว").format(doc.name))
	return "Approved"


# ---------------------------------------------------------------- หลังจ่ายเงิน (Payment Entry)


def payroll_month_start(employee, date):
	"""งวดแรกที่หักได้: เดือนของวันที่จ่าย ถ้าสลิปที่ครอบวันนั้นออก (Submit) แล้ว = เดือนถัดไป"""
	date = getdate(date)
	slip = frappe.db.exists(
		"Salary Slip",
		{"employee": employee, "docstatus": 1, "start_date": ("<=", date), "end_date": (">=", date)},
	)
	return get_first_day(add_months(date, 1) if slip else date)


def installment_amounts(total, count):
	count = max(1, cint(count))
	each = flt(total / count, 2)
	amounts = [each] * (count - 1)
	amounts.append(flt(total - sum(amounts), 2))
	return amounts


def create_salary_deductions(advance, paid_date):
	"""Additional Salary (Submit) งวดละเดือน ตาม custom_installments รวม = ยอดที่จ่ายแล้วหักด้วยยอดที่คืนแล้ว"""
	component = frappe.db.get_value("Company", advance.company, "custom_salary_advance_component")
	if not component:
		advance.add_comment(
			"Comment",
			_("ยังไม่ได้สร้างรายการหักเงินเดือน: ตั้ง {0} ที่บริษัท {1} ก่อน").format(
				_("รายการหักเงินเดือนล่วงหน้า"), advance.company
			),
		)
		return []
	total = flt(advance.paid_amount) - flt(advance.claimed_amount) - flt(advance.return_amount)
	if total <= 0:
		return []
	first = payroll_month_start(advance.employee, paid_date)
	names = []
	for i, amount in enumerate(installment_amounts(total, advance.custom_installments)):
		month = add_months(first, i)
		# วันสุดท้ายของเดือน: อยู่ในงวดเงินเดือนรายเดือนเสมอ
		payroll_date = month.replace(day=calendar.monthrange(month.year, month.month)[1])
		doc = frappe.get_doc(
			{
				"doctype": "Additional Salary",
				"employee": advance.employee,
				"company": advance.company,
				"salary_component": component,
				"amount": amount,
				"payroll_date": payroll_date,
				"currency": advance.currency,
				"overwrite_salary_structure_amount": 0,
				"ref_doctype": "Employee Advance",
				"ref_docname": advance.name,
			}
		)
		doc.insert(ignore_permissions=True)
		doc.submit()
		names.append(doc.name)
	advance.db_set("custom_deductions_created", 1, update_modified=False)
	return names


def on_payment_entry_submit(doc, method=None):
	"""doc_events Payment Entry.on_submit: จ่าย Employee Advance ของแอปครบแล้ว
	เงินเดือนล่วงหน้า = สร้างรายการหักเงินเดือน / เงินสำรองจ่าย = ตั้งกำหนดเคลียร์"""
	names = {r.reference_name for r in doc.references if r.reference_doctype == "Employee Advance"}
	for name in names:
		advance = frappe.get_doc("Employee Advance", name)
		if not advance.custom_advance_type or advance.docstatus != 1:
			continue
		if flt(advance.paid_amount) < flt(advance.advance_amount):
			continue
		if advance.custom_advance_type == "Salary Advance" and not advance.custom_deductions_created:
			frappe.db.savepoint("consbiz_salary_deductions")
			try:
				create_salary_deductions(advance, doc.posting_date)
			except Exception as e:
				# ไม่ขวางการจ่ายเงิน: ย้อนเฉพาะรายการหัก แล้วบันทึกไว้ให้ HR สร้างเอง
				frappe.db.rollback(save_point="consbiz_salary_deductions")
				advance.add_comment(
					"Comment", _("สร้างรายการหักเงินเดือนไม่สำเร็จ: {0}").format(frappe.utils.strip_html(str(e)))
				)
		elif advance.custom_advance_type == "Expense Advance" and not advance.custom_clear_due_date:
			days = cint(company_setting(advance.company, "custom_expense_clear_days", DEFAULT_CLEAR_DAYS))
			advance.db_set("custom_clear_due_date", add_days(doc.posting_date, days), update_modified=False)


def remind_overdue_clearing():
	"""scheduler รายวัน: เงินสำรองจ่ายเลยกำหนดเคลียร์ แจ้งเตือนพนักงานทุก REMIND_EVERY_DAYS วัน (ไม่หักเงินเอง)"""
	today = getdate()
	for row in frappe.get_all(
		"Employee Advance",
		filters={
			"docstatus": 1,
			"custom_advance_type": "Expense Advance",
			"custom_clear_due_date": ("<", today),
			"status": ("in", ["Paid", "Partially Paid", "Unpaid"]),
		},
		fields=["name", "employee", "paid_amount", "claimed_amount", "return_amount", "custom_last_reminder"],
	):
		if flt(row.paid_amount) - flt(row.claimed_amount) - flt(row.return_amount) <= 0:
			continue
		if row.custom_last_reminder and (today - getdate(row.custom_last_reminder)).days < REMIND_EVERY_DAYS:
			continue
		user = frappe.db.get_value("Employee", row.employee, "user_id")
		if user:
			from frappe.desk.doctype.notification_log.notification_log import enqueue_create_notification

			enqueue_create_notification(
				user,
				{
					"type": "Alert",
					"document_type": "Employee Advance",
					"document_name": row.name,
					"subject": _("เงินสำรองจ่าย {0} เลยกำหนดเคลียร์แล้ว ส่งใบเคลียร์ในแอป Self Service").format(row.name),
				},
			)
		frappe.db.set_value("Employee Advance", row.name, "custom_last_reminder", today, update_modified=False)
