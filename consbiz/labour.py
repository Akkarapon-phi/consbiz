# ลงเวลาคนงานรายวันของธุรการ (ConsERP > ธุรการ > ลงเวลาคนงาน, views/admin/Labour.vue)
# 1 หน้า = 1 รอบ (Labour Timesheet ของโครงการ, period_of) ช่อง = ชั่วโมงทำงานจริงของคนงานในวันนั้น
# บันทึกเฉพาะช่องที่แก้ (save_sheet) ไม่มีใบของรอบ = สร้างใหม่ ล็อกแถว Project ก่อนหา/สร้างใบ
# กันสร้างซ้ำและเขียนทับกันเมื่อหลายคนลงพร้อมกัน

import json

import frappe
from frappe import _
from frappe.utils import flt, getdate, nowdate

from consbiz.consbiz.doctype.labour_timesheet.labour_timesheet import MAX_HOURS, period_of

WORKER_FIELDS = ["name", "worker_name", "position", "team", "payee_type", "supplier", "daily_rate", "sso_registered"]
NO_TEAM = "ไม่ระบุทีม"


def team_of(worker, suppliers):
	"""ทีมในหน้าลงเวลา: ช่องทีม > ชื่อ ผรม. (คนงานของ ผรม.) > ไม่ระบุทีม"""
	if worker.team:
		return worker.team.strip()
	if worker.payee_type == "Subcontractor" and worker.supplier:
		return suppliers.get(worker.supplier) or worker.supplier
	return NO_TEAM
PAY_FIELDS = (
	"days_worked",
	"holiday_days",
	"ot_hours",
	"wage",
	"ot_amount",
	"gross",
	"advance",
	"sso",
	"employer_sso",
	"other_deduction",
	"net",
)


def can_edit_sheet():
	return bool(frappe.has_permission("Labour Timesheet", "create"))


def timesheet_of(project, day, for_update=False):
	"""ใบลงเวลา (ไม่ยกเลิก) ของโครงการที่ครอบวัน day"""
	names = frappe.get_all(
		"Labour Timesheet",
		filters={
			"project": project,
			"docstatus": ("<", 2),
			"from_date": ("<=", day),
			"to_date": (">=", day),
		},
		pluck="name",
		limit=1,
	)
	if not names:
		return None
	if for_update:
		frappe.db.get_value("Labour Timesheet", names[0], "name", for_update=True)
	return frappe.get_doc("Labour Timesheet", names[0])


def parse(value):
	return json.loads(value) if isinstance(value, str) else (value or [])


@frappe.whitelist()
def get_sheet(project, date=None):
	"""รอบที่ครอบวัน date (ว่าง = วันนี้) พร้อมชั่วโมงของทุกคน"""
	frappe.has_permission("Project", "read", project, throw=True)
	frappe.has_permission("Labour Timesheet", "read", throw=True)
	day = getdate(date or nowdate())
	sheet = timesheet_of(project, day)
	start, end = (getdate(sheet.from_date), getdate(sheet.to_date)) if sheet else period_of(day)

	hours = {}
	for row in sheet.days if sheet else []:
		hours.setdefault(row.worker, {})[str(row.date)] = flt(row.hours)
	workers = frappe.get_all(
		"Daily Worker",
		filters={"project": project, "status": "Active"},
		fields=WORKER_FIELDS,
		order_by="worker_name asc",
	)
	# คนงานที่มีชั่วโมงในรอบนี้แต่ย้ายโครงการ/เลิกจ้างทีหลัง ยังต้องเห็นแถว
	listed = {w.name for w in workers}
	missing = [name for name in hours if name not in listed]
	if missing:
		workers += frappe.get_all(
			"Daily Worker", filters={"name": ("in", missing)}, fields=WORKER_FIELDS, order_by="worker_name asc"
		)
	suppliers = dict(
		frappe.get_all(
			"Supplier",
			filters={"name": ("in", list({w.supplier for w in workers if w.supplier}))},
			fields=["name", "supplier_name"],
			as_list=True,
		)
	)
	pay = {
		row.worker: {
			**{f: flt(row.get(f)) for f in PAY_FIELDS},
			"deduction_remark": row.deduction_remark,
			"purchase_invoice": row.purchase_invoice,
		}
		for row in (sheet.pay if sheet else [])
	}

	today = getdate(nowdate())
	rows = [
		{
			"worker": w.name,
			"worker_name": w.worker_name,
			"position": w.position,
			"team": team_of(w, suppliers),
			"payee": suppliers.get(w.supplier) if w.payee_type == "Subcontractor" else None,
			"daily_rate": flt(w.daily_rate),
			"sso_registered": w.sso_registered,
			"hours": hours.get(w.name, {}),
			"pay": pay.get(w.name),
		}
		for w in workers
	]
	# เรียงตามทีม (ไม่ระบุทีมไว้ท้าย) แล้วตามชื่อ
	rows.sort(key=lambda r: (r["team"] == NO_TEAM, r["team"], r["worker_name"] or ""))
	return {
		"project": project,
		"from_date": str(start),
		"to_date": str(end),
		"today": str(today),
		"timesheet": sheet.name if sheet else None,
		"docstatus": sheet.docstatus if sheet else 0,
		"holidays": [str(row.date) for row in sheet.holidays] if sheet else [],
		"workers": rows,
		"totals": {
			field: flt(sheet.get(f"total_{field}")) if sheet else 0
			for field in ("gross", "advance", "sso", "other_deduction", "net", "employer_sso")
		},
		"journal_entry": sheet.journal_entry if sheet else None,
		"can_print": bool(sheet and frappe.has_permission("Labour Timesheet", "print", sheet)),
		"can_edit": can_edit_sheet() and (not sheet or sheet.docstatus == 0) and start <= today,
		"can_submit": bool(sheet and sheet.docstatus == 0 and sheet.days and frappe.has_permission("Labour Timesheet", "submit", sheet)),
		"can_add_worker": bool(frappe.has_permission("Daily Worker", "create")),
		"max_hours": MAX_HOURS,
	}


@frappe.whitelist(methods=["POST"])
def save_sheet(project, date, cells=None, holidays=None):
	"""cells = [{worker, date, hours (ว่าง/0 = ลบ)}] เฉพาะช่องที่แก้, holidays = วันหยุดทั้งรอบ (ไม่ส่ง = คงเดิม)
	date = วันใดก็ได้ในรอบ"""
	frappe.has_permission("Project", "read", project, throw=True)
	if not can_edit_sheet():
		frappe.throw(_("ไม่มีสิทธิ์ลงเวลาคนงาน"), frappe.PermissionError)
	cells = parse(cells)
	today = getdate(nowdate())

	# ล็อกโครงการ: คนที่ 2 รอจนคนแรกสร้าง/บันทึกใบเสร็จ แล้วจะเห็นใบเดียวกัน
	frappe.db.get_value("Project", project, "name", for_update=True)
	sheet = timesheet_of(project, getdate(date), for_update=True)
	if sheet and sheet.docstatus == 1:
		frappe.throw(_("ใบลงเวลา {0} อนุมัติแล้ว แก้ไขไม่ได้").format(sheet.name))
	if not sheet:
		start, end = period_of(date)
		sheet = frappe.new_doc("Labour Timesheet")
		sheet.update(
			{
				"project": project,
				"company": frappe.db.get_value("Project", project, "company"),
				"from_date": start,
				"to_date": end,
			}
		)
	start, end = getdate(sheet.from_date), getdate(sheet.to_date)

	changes = {}
	for cell in cells:
		day = getdate(cell.get("date"))
		if not cell.get("worker") or not start <= day <= end:
			frappe.throw(_("วันที่ {0} อยู่นอกรอบ {1} - {2}").format(cell.get("date"), start, end))
		value = flt(cell.get("hours"), 2)
		if value and day > today:
			frappe.throw(_("ลงเวลาล่วงหน้าไม่ได้ ({0})").format(day))
		changes[(cell["worker"], day)] = value

	kept = [row for row in sheet.days if (row.worker, getdate(row.date)) not in changes]
	sheet.days = []
	for row in kept:
		sheet.append("days", row)
	for (worker, day), value in sorted(changes.items(), key=lambda item: item[0][1]):
		if value:
			sheet.append("days", {"worker": worker, "date": day, "hours": value})

	if holidays is not None:
		sheet.holidays = []
		for day in sorted({getdate(d) for d in parse(holidays)}):
			sheet.append("holidays", {"date": day})

	if sheet.is_new() and not sheet.days and not sheet.holidays:
		return get_sheet(project, str(start))
	sheet.save()
	return get_sheet(project, str(start))


@frappe.whitelist(methods=["POST"])
def submit_sheet(name):
	"""อนุมัติค่าแรงของรอบ (Submit) หลังจากนี้แก้ไม่ได้"""
	sheet = frappe.get_doc("Labour Timesheet", name)
	sheet.check_permission("submit")
	sheet.submit()
	return get_sheet(sheet.project, str(sheet.from_date))


@frappe.whitelist(methods=["POST"])
def add_worker(project, worker_name, daily_rate, position=None, payee_type="Company", supplier=None, team=None):
	"""เพิ่มคนงานใหม่จากหน้าลงเวลา (ข้อมูลอื่นเติมทีหลังในทะเบียนคนงาน)"""
	frappe.has_permission("Project", "read", project, throw=True)
	frappe.has_permission("Daily Worker", "create", throw=True)
	doc = frappe.get_doc(
		{
			"doctype": "Daily Worker",
			"worker_name": (worker_name or "").strip(),
			"company": frappe.db.get_value("Project", project, "company"),
			"project": project,
			"position": (position or "").strip() or None,
			"team": (team or "").strip() or None,
			"payee_type": payee_type if payee_type in ("Company", "Subcontractor") else "Company",
			"supplier": supplier or None,
			# ค่าแรงแรกเริ่มต้นรอบปัจจุบัน ลงเวลาย้อนหลังในรอบนี้ได้ตามอัตรานี้
			"rates": [{"from_date": period_of(nowdate())[0], "daily_rate": flt(daily_rate)}],
		}
	)
	doc.insert()
	suppliers = {doc.supplier: frappe.db.get_value("Supplier", doc.supplier, "supplier_name")} if doc.supplier else {}
	return {
		"name": doc.name,
		"worker_name": doc.worker_name,
		"team": team_of(doc, suppliers),
		"payee": suppliers.get(doc.supplier),
	}


@frappe.whitelist()
def get_workers(project=None, status="Active"):
	"""ทะเบียนคนงาน (หน้า workers) project ว่าง = ทุกโครงการที่อ่านได้"""
	frappe.has_permission("Daily Worker", "read", throw=True)
	filters = {}
	if project:
		filters["project"] = project
	if status in ("Active", "Inactive"):
		filters["status"] = status
	rows = frappe.get_list(
		"Daily Worker",
		filters=filters,
		fields=[
			"name",
			"worker_name",
			"position",
			"team",
			"project",
			"payee_type",
			"supplier",
			"daily_rate",
			"ot_flat",
			"ot_hourly_rate",
			"sso_registered",
			"nationality",
			"phone",
			"status",
		],
		order_by="worker_name asc",
		limit_page_length=0,
	)
	suppliers = dict(
		frappe.get_all(
			"Supplier",
			filters={"name": ("in", list({r.supplier for r in rows if r.supplier}))},
			fields=["name", "supplier_name"],
			as_list=True,
		)
	)
	for row in rows:
		row.payee = suppliers.get(row.supplier) if row.payee_type == "Subcontractor" else None
	return {"rows": rows, "can_create": bool(frappe.has_permission("Daily Worker", "create"))}


@frappe.whitelist(methods=["POST"])
def set_deduction(name, worker, amount=0, remark=None):
	"""หักอื่นๆ ของคนงานในใบร่าง (ค่าอื่นคำนวณใหม่ทั้งใบ)"""
	sheet = frappe.get_doc("Labour Timesheet", name)
	sheet.check_permission("write")
	if sheet.docstatus != 0:
		frappe.throw(_("ใบลงเวลา {0} อนุมัติแล้ว แก้ไขไม่ได้").format(name))
	row = next((r for r in sheet.pay if r.worker == worker), None)
	if not row:
		frappe.throw(_("คนงานนี้ไม่มีค่าแรงในรอบนี้"))
	amount = flt(amount, 2)
	if amount < 0:
		frappe.throw(_("ยอดหักต้องไม่ติดลบ"))
	row.other_deduction = amount
	row.deduction_remark = (remark or "").strip()[:140] or None
	sheet.save()
	return get_sheet(sheet.project, str(sheet.from_date))


@frappe.whitelist()
def get_print_url(name):
	from consbiz.site_app import pdf_url

	frappe.has_permission("Labour Timesheet", "print", name, throw=True)
	return pdf_url("Labour Timesheet", name)


# ---------------------------------------------------------------- เบิกล่วงหน้า


@frappe.whitelist()
def get_advances(project):
	frappe.has_permission("Project", "read", project, throw=True)
	frappe.has_permission("Labour Advance", "read", throw=True)
	rows = frappe.get_list(
		"Labour Advance",
		filters={"project": project, "docstatus": ("<", 2)},
		fields=[
			"name",
			"worker",
			"worker_name",
			"date",
			"amount",
			"deducted_amount",
			"outstanding_amount",
			"status",
			"docstatus",
			"remark",
			"paid_from_account",
		],
		order_by="date desc, creation desc",
		limit_page_length=500,
	)
	company = frappe.db.get_value("Project", project, "company")
	workers = frappe.get_all(
		"Daily Worker",
		filters={"project": project, "status": "Active", "payee_type": "Company"},
		fields=["name", "worker_name", "position"],
		order_by="worker_name asc",
	)
	return {
		"rows": rows,
		"workers": workers,
		"cash_accounts": cash_accounts(company),
		"can_create": bool(frappe.has_permission("Labour Advance", "create")),
		"can_submit": bool(frappe.has_permission("Labour Advance", "submit")),
		"can_cancel": bool(frappe.has_permission("Labour Advance", "cancel")),
	}


def cash_accounts(company):
	return frappe.get_all(
		"Account",
		filters={"company": company, "is_group": 0, "disabled": 0, "account_type": ("in", ("Cash", "Bank"))},
		fields=["name as value", "account_name as label"],
		order_by="account_type desc, account_name asc",
	)


@frappe.whitelist(methods=["POST"])
def create_advance(worker, amount, paid_from_account, date=None, remark=None):
	"""บันทึกเบิกล่วงหน้า ผู้มีสิทธิ์ Submit = จ่ายเงินทันที (ลง Journal Entry) ไม่มีสิทธิ์ = ร่างรอผู้อนุมัติ"""
	frappe.has_permission("Labour Advance", "create", throw=True)
	doc = frappe.get_doc(
		{
			"doctype": "Labour Advance",
			"worker": worker,
			"amount": flt(amount, 2),
			"paid_from_account": paid_from_account,
			"date": date or nowdate(),
			"remark": (remark or "").strip() or None,
		}
	)
	frappe.has_permission("Project", "read", frappe.db.get_value("Daily Worker", worker, "project"), throw=True)
	doc.insert()
	if frappe.has_permission("Labour Advance", "submit", doc):
		doc.submit()
	return {"name": doc.name, "docstatus": doc.docstatus}


@frappe.whitelist(methods=["POST"])
def submit_advance(name):
	doc = frappe.get_doc("Labour Advance", name)
	doc.check_permission("submit")
	doc.submit()
	return {"name": doc.name, "docstatus": doc.docstatus}


@frappe.whitelist(methods=["POST"])
def cancel_advance(name):
	"""ร่าง = ลบ, จ่ายแล้ว = ยกเลิก (ยกเลิก Journal Entry ตาม) ห้ามถ้าหักคืนแล้ว"""
	doc = frappe.get_doc("Labour Advance", name)
	if doc.docstatus == 0:
		doc.check_permission("delete")
		frappe.delete_doc("Labour Advance", name)
		return {"deleted": True}
	doc.check_permission("cancel")
	doc.cancel()
	return {"deleted": False}


# ---------------------------------------------------------------- รายงานประจำวัน


@frappe.whitelist()
def labour_on(project, date):
	"""จำนวนคนงานรายวันที่ลงเวลาไว้ในวันนั้น แยกตามตำแหน่ง (ปุ่มดึงในรายงานประจำวัน)"""
	frappe.has_permission("Project", "read", project, throw=True)
	day = getdate(date)
	sheet = timesheet_of(project, day)
	if not sheet:
		return []
	workers = [row.worker for row in sheet.days if getdate(row.date) == day and flt(row.hours) > 0]
	if not workers:
		return []
	positions = dict(
		frappe.get_all(
			"Daily Worker", filters={"name": ("in", workers)}, fields=["name", "position"], as_list=True
		)
	)
	counts = {}
	for worker in workers:
		role = positions.get(worker) or _("คนงาน")
		counts[role] = counts.get(role, 0) + 1
	return [{"role": role, "qty": qty} for role, qty in sorted(counts.items())]


# ---------------------------------------------------------------- ตั้งค่าบัญชี (แอป: ตั้งค่า > ค่าแรงคนงาน)

SETTING_FIELDS = (
	"wage_expense_account",
	"employer_sso_expense_account",
	"wage_payable_account",
	"sso_payable_account",
	"advance_account",
	"other_deduction_account",
	"subcontract_item",
	"subcontract_wht_percent",
)


def can_edit_settings():
	return bool(frappe.has_permission("Labour Settings", "write") and frappe.has_permission("Labour Settings", "create"))


@frappe.whitelist()
def get_settings(company=None):
	if not frappe.has_permission("Labour Settings", "read"):
		frappe.throw(_("ไม่มีสิทธิ์ดูตั้งค่าค่าแรง"), frappe.PermissionError)
	companies = frappe.get_list("Company", pluck="name", order_by="name asc", limit_page_length=0)
	company = company or frappe.defaults.get_user_default("Company") or (companies[0] if companies else None)
	values = {}
	if company and frappe.db.exists("Labour Settings", company):
		doc = frappe.get_doc("Labour Settings", company)
		values = {field: doc.get(field) for field in SETTING_FIELDS}
	else:
		values = {"subcontract_wht_percent": 3}
	return {
		"company": company,
		"companies": companies,
		"values": values,
		"labels": labels_of(values),
		"checks": setting_checks(company, values) if company else [],
		"can_edit": can_edit_settings(),
		"can_create_account": bool(frappe.has_permission("Account", "create")),
		"can_create_item": bool(frappe.has_permission("Item", "create")),
	}


def labels_of(values):
	out = {}
	for field, value in values.items():
		if not value or field == "subcontract_wht_percent":
			continue
		if field == "subcontract_item":
			out[field] = frappe.db.get_value("Item", value, "item_name") or value
		else:
			out[field] = frappe.db.get_value("Account", value, "account_name") or value
	return out


def setting_checks(company, values):
	"""ข้อที่ต้องตั้งนอกหน้านี้ (ok = พร้อม)"""
	from consbiz.social_security import rate_on

	# erpnext_thailand บังคับแถวของบริษัทใน Thai Tax Settings ก่อนลง Journal Entry
	thai = True
	if frappe.db.exists("DocType", "Thai Tax Settings Company"):
		thai = frappe.db.exists("Thai Tax Settings Company", {"parent": "Thai Tax Settings", "company": company})
	wht_account = True
	if frappe.get_meta("Company").has_field("custom_wht_payable"):
		wht_account = frappe.db.get_value("Company", company, "custom_wht_payable")
	rate = rate_on(nowdate())
	return [
		{
			"label": _("อัตราประกันสังคมเดือนนี้"),
			"ok": bool(rate),
			"text": _("{0}% เพดาน {1:,.0f} บาท").format(flt(rate.employee_rate), flt(rate.max_base))
			if rate
			else _("ยังไม่มี: เพิ่มใน Social Security Rate"),
			"link": "/app/social-security-rate",
		},
		{
			"label": _("Thai Tax Settings ของบริษัท"),
			"ok": bool(thai),
			"text": _("พร้อม") if thai else _("ยังไม่มีแถวของบริษัทนี้ (erpnext_thailand บังคับก่อนลง Journal Entry)"),
			"link": "/app/thai-tax-settings",
		},
		{
			"label": _("บัญชีภาษีหัก ณ ที่จ่ายรอจ่าย (Company)"),
			"ok": bool(wht_account) or not flt(values.get("subcontract_wht_percent")),
			"text": _("พร้อม") if wht_account else _("ยังไม่ได้ตั้ง (ใช้กับ PI ของ ผรม.)"),
			"link": f"/app/company/{company}",
		},
	]


@frappe.whitelist(methods=["POST"])
def save_settings(company, values):
	if not can_edit_settings():
		frappe.throw(_("ไม่มีสิทธิ์แก้ตั้งค่าค่าแรง"), frappe.PermissionError)
	values = json.loads(values) if isinstance(values, str) else values
	doc = (
		frappe.get_doc("Labour Settings", company)
		if frappe.db.exists("Labour Settings", company)
		else frappe.new_doc("Labour Settings")
	)
	doc.company = company
	for field in SETTING_FIELDS:
		if field in values:
			doc.set(field, values[field] or (0 if field == "subcontract_wht_percent" else None))
	doc.save()
	return get_settings(company)


# ช่อง → ตัวกรองบัญชีที่เลือกได้ (ตรงกับ ACCOUNT_RULES ของ Labour Settings)
ACCOUNT_FILTERS = {
	"wage_expense_account": ("Expense",),
	"employer_sso_expense_account": ("Expense",),
	"wage_payable_account": ("Liability",),
	"sso_payable_account": ("Liability",),
	"advance_account": ("Asset",),
	"other_deduction_account": ("Income", "Expense", "Liability"),
}


@frappe.whitelist()
def search_accounts(company, field, txt=""):
	frappe.has_permission("Labour Settings", "read", throw=True)
	if field not in ACCOUNT_FILTERS:
		frappe.throw(_("ไม่รองรับ {0}").format(field))
	txt = (txt or "").strip()
	rows = frappe.get_all(
		"Account",
		filters={
			"company": company,
			"is_group": 0,
			"disabled": 0,
			"root_type": ("in", ACCOUNT_FILTERS[field]),
			"account_type": ("not in", ("Payable", "Receivable")),
		},
		or_filters=[["name", "like", f"%{txt}%"], ["account_name", "like", f"%{txt}%"]] if txt else None,
		fields=["name", "account_name", "account_number", "root_type"],
		order_by="lft asc",
		limit_page_length=40,
	)
	return [
		{
			"value": r.name,
			"label": " ".join(filter(None, [r.account_number, r.account_name])),
			"description": r.name,
		}
		for r in rows
	]


@frappe.whitelist()
def search_service_items(txt=""):
	frappe.has_permission("Labour Settings", "read", throw=True)
	txt = (txt or "").strip()
	rows = frappe.get_all(
		"Item",
		filters={"is_stock_item": 0, "disabled": 0, "has_variants": 0},
		or_filters=[["name", "like", f"%{txt}%"], ["item_name", "like", f"%{txt}%"]] if txt else None,
		fields=["name", "item_name"],
		limit_page_length=30,
	)
	return [{"value": r.name, "label": r.item_name or r.name, "description": r.name} for r in rows]


# ---------------------------------------------------------------- สร้างบัญชี/Item ที่ยังไม่มี (ปุ่มในหน้าตั้งค่า)

# ช่อง → (ชื่อบัญชีที่เสนอ, คำในชื่อกลุ่มที่ควรเป็นกลุ่มแม่, ช่องบัญชีตั้งต้นของ Company ที่ใช้กลุ่มแม่ของมันแทน)
ACCOUNT_SUGGESTIONS = {
	"wage_expense_account": ("ค่าแรงงานก่อสร้าง", ("ต้นทุน",), "default_expense_account"),
	"employer_sso_expense_account": ("เงินสมทบประกันสังคม - คนงานรายวัน", ("ต้นทุน",), "default_expense_account"),
	"wage_payable_account": ("ค่าแรงค้างจ่าย", ("เจ้าหนี้อื่น", "ค้างจ่าย"), "default_payroll_payable_account"),
	"sso_payable_account": ("เงินประกันสังคมค้างนำส่ง", ("ประกันสังคม", "ภาษี"), "default_payroll_payable_account"),
	"advance_account": ("เงินเบิกล่วงหน้าคนงานรายวัน", ("หมุนเวียนอื่น", "เงินทดรอง"), "default_employee_advance_account"),
	"other_deduction_account": ("รายได้อื่น - หักค่าแรงคนงาน", ("รายได้อื่น",), None),
}


def require_account_manager():
	if not frappe.has_permission("Account", "create"):
		frappe.throw(_("สร้างบัญชีได้เฉพาะ Accounts Manager"), frappe.PermissionError)


def group_accounts(company, root_types):
	return frappe.get_all(
		"Account",
		filters={"company": company, "is_group": 1, "root_type": ("in", root_types)},
		fields=["name", "account_name", "account_number", "parent_account"],
		order_by="lft asc",
	)


def next_number(parent):
	"""เลขบัญชีถัดไปใต้กลุ่ม (บริษัทที่ใช้เลขบัญชี) ไม่มีเลข = ว่าง"""
	numbers = [
		n
		for n in frappe.get_all("Account", filters={"parent_account": parent, "is_group": 0}, pluck="account_number")
		if n and str(n).isdigit()
	]
	if numbers:
		top = max(numbers, key=int)
		candidate = str(int(top) + 1).zfill(len(top))
	else:
		base = frappe.db.get_value("Account", parent, "account_number")
		if not (base and str(base).isdigit()):
			return None
		# กลุ่ม 215000 → บัญชีแรก 215001
		candidate = str(int(base) + 1).zfill(len(base))
	# เลขถัดไปถูกใช้แล้ว (เช่น อยู่ในกลุ่มย่อย) ขยับหาเลขว่าง
	company = frappe.db.get_value("Account", parent, "company")
	for _step in range(50):
		if not frappe.db.exists("Account", {"account_number": candidate, "company": company}):
			return candidate
		candidate = str(int(candidate) + 1).zfill(len(candidate))
	return None


@frappe.whitelist()
def suggest_account(company, field):
	frappe.has_permission("Labour Settings", "read", throw=True)
	if field not in ACCOUNT_SUGGESTIONS:
		frappe.throw(_("ไม่รองรับ {0}").format(field))
	name, keywords, default_field = ACCOUNT_SUGGESTIONS[field]
	groups = group_accounts(company, ACCOUNT_FILTERS[field])
	parent = next((g.name for k in keywords for g in groups if k in (g.account_name or "")), None)
	if not parent and default_field:
		default = frappe.db.get_value("Company", company, default_field)
		parent = default and frappe.db.get_value("Account", default, "parent_account")
	parent = parent or (groups[0].name if groups else None)
	return {
		"account_name": name,
		"parent_account": parent,
		"account_number": next_number(parent) if parent else None,
		"parents": [
			{"value": g.name, "label": " ".join(filter(None, [g.account_number, g.account_name]))} for g in groups
		],
	}


@frappe.whitelist()
def number_for(parent):
	frappe.has_permission("Labour Settings", "read", throw=True)
	return next_number(parent)


@frappe.whitelist(methods=["POST"])
def create_account(company, field, account_name, parent_account, account_number=None):
	require_account_manager()
	if field not in ACCOUNT_FILTERS:
		frappe.throw(_("ไม่รองรับ {0}").format(field))
	parent = frappe.db.get_value(
		"Account", parent_account, ["company", "is_group", "root_type"], as_dict=True
	)
	if not parent or parent.company != company or not parent.is_group:
		frappe.throw(_("กลุ่มบัญชีไม่ถูกต้อง"))
	if parent.root_type not in ACCOUNT_FILTERS[field]:
		frappe.throw(_("กลุ่มบัญชีต้องเป็นประเภท {0}").format(" / ".join(ACCOUNT_FILTERS[field])))
	doc = frappe.get_doc(
		{
			"doctype": "Account",
			"company": company,
			"account_name": (account_name or "").strip(),
			"account_number": (account_number or "").strip() or None,
			"parent_account": parent_account,
			"is_group": 0,
		}
	).insert()
	return {
		"value": doc.name,
		"label": " ".join(filter(None, [doc.account_number, doc.account_name])),
	}


@frappe.whitelist(methods=["POST"])
def create_service_item(item_name="ค่าแรงผู้รับเหมาช่วง"):
	"""Item ที่ไม่ใช่สต็อกสำหรับร่าง PI ค่าแรงคนงานของ ผรม."""
	frappe.has_permission("Item", "create", throw=True)
	item_name = (item_name or "").strip() or "ค่าแรงผู้รับเหมาช่วง"
	group = (
		frappe.db.get_value("Item Group", {"name": ("in", ("Services", "บริการ")), "is_group": 0})
		or frappe.db.get_value("Item Group", {"is_group": 0}, order_by="lft asc")
	)
	uom = frappe.db.get_value("UOM", {"name": ("in", ("งาน", "Job", "Unit", "Nos"))}) or "Nos"
	existing = frappe.db.get_value("Item", {"item_name": item_name, "is_stock_item": 0, "disabled": 0})
	if existing:
		return {"value": existing, "label": item_name}
	doc = frappe.get_doc(
		{
			"doctype": "Item",
			"item_code": item_name,
			"item_name": item_name,
			"item_group": group,
			"stock_uom": uom,
			"is_stock_item": 0,
			"is_purchase_item": 1,
			"is_sales_item": 0,
			"include_item_in_manufacturing": 0,
		}
	).insert()
	return {"value": doc.name, "label": doc.item_name}


@frappe.whitelist()
def get_teams(project=None):
	"""ชื่อทีมที่ใช้อยู่ (ให้เลือกตอนเพิ่ม/แก้คนงาน)"""
	frappe.has_permission("Daily Worker", "read", throw=True)
	filters = {"team": ("is", "set")}
	if project:
		filters["project"] = project
	return sorted(set(frappe.get_all("Daily Worker", filters=filters, pluck="team")))


@frappe.whitelist(methods=["POST"])
def set_team(workers, team=None):
	"""ย้ายคนงานหลายคนเข้าทีม (ว่าง = ไม่ระบุทีม)"""
	workers = parse(workers)
	team = (team or "").strip() or None
	for name in workers:
		doc = frappe.get_doc("Daily Worker", name)
		doc.check_permission("write")
		doc.team = team
		doc.save()
	return {"updated": len(workers)}



# ---------------------------------------------------------------- ทะเบียนคนงาน (ดู/แก้ในแอป)

WORKER_FORM = (
	"worker_name",
	"id_number",
	"nationality",
	"phone",
	"project",
	"position",
	"team",
	"payee_type",
	"supplier",
	"bank_name",
	"bank_account",
	"account_holder_other",
	"account_holder",
	"account_holder_relation",
	"ot_flat",
	"ot_hourly_rate",
	"sso_registered",
	"sso_number",
	"status",
)


@frappe.whitelist()
def get_worker(name):
	doc = frappe.get_doc("Daily Worker", name)
	doc.check_permission("read")
	data = {field: doc.get(field) for field in WORKER_FORM}
	data.update(
		{
			"name": doc.name,
			"daily_rate": flt(doc.daily_rate),
			"supplier_name": frappe.db.get_value("Supplier", doc.supplier, "supplier_name") if doc.supplier else None,
			"rates": [{"from_date": str(r.from_date), "daily_rate": flt(r.daily_rate), "remark": r.remark} for r in doc.rates],
			"can_write": bool(doc.has_permission("write")),
		}
	)
	return data


@frappe.whitelist(methods=["POST"])
def save_worker(values, name=None, project=None):
	"""เพิ่ม/แก้คนงาน values.daily_rate + values.rate_from = ค่าแรงใหม่ตั้งแต่วันนั้น (เพิ่มแถวประวัติ ไม่แก้แถวเดิม)"""
	values = parse(values) if isinstance(values, str) else (values or {})
	if name:
		doc = frappe.get_doc("Daily Worker", name)
		doc.check_permission("write")
	else:
		project = project or values.get("project")
		frappe.has_permission("Project", "read", project, throw=True)
		frappe.has_permission("Daily Worker", "create", throw=True)
		doc = frappe.new_doc("Daily Worker")
		doc.company = frappe.db.get_value("Project", project, "company")
		doc.project = project
	for field in WORKER_FORM:
		if field in values and not (field == "project" and not values[field]):
			value = values[field]
			doc.set(field, value.strip() if isinstance(value, str) else value)
	rate = flt(values.get("daily_rate"))
	if rate > 0:
		start = getdate(values.get("rate_from") or (period_of(nowdate())[0] if doc.is_new() else nowdate()))
		current = doc.rate_on(start) if doc.rates else 0
		if rate != current:
			same = next((r for r in doc.rates if getdate(r.from_date) == start), None)
			if same:
				same.daily_rate = rate
			else:
				doc.append("rates", {"from_date": start, "daily_rate": rate, "remark": values.get("rate_remark")})
	doc.save()
	suppliers = {doc.supplier: frappe.db.get_value("Supplier", doc.supplier, "supplier_name")} if doc.supplier else {}
	return {
		"name": doc.name,
		"worker_name": doc.worker_name,
		"position": doc.position,
		"team": team_of(doc, suppliers),
		"payee": suppliers.get(doc.supplier),
		"daily_rate": flt(doc.daily_rate),
	}
