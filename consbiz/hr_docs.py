# Copyright (c) 2026, Siricons and contributors
# For license information, please see license.txt

"""เอกสารพนักงานในหมวดบุคคลของแอปออฟฟิศ (/conserp/hr): สัญญาจ้าง (Employment Contract) และ
หนังสือรับรองการหักภาษี ณ ที่จ่ายของพนักงาน (WHT Employee, 50 ทวิ) หน้าจอครอบ DocType เดิม
รายการใช้ KindList (office_app/views/hr/kinds.js) หน้าเอกสาร = HrDocPage.vue
สิทธิ์ = สิทธิ์ของ DocType (ตั้งในหน้าตั้งค่าของแอป หมวดบุคคล) แอปส่งเฉพาะช่องใน `input` ของ KINDS"""

import json

import frappe
from frappe import _
from frappe.utils import add_days, cint, flt, getdate, nowdate

from consbiz import row_social, store_app

# kind = ชื่อหน้ารายการใน sections.js
KINDS = {
	"hr-contracts": {
		"doctype": "Employment Contract",
		"list": ("employee", "full_name", "company", "date", "base", "prob_end_date", "probation"),
		"date": "date",
		"input": (
			"company",
			"employee",
			"date",
			"base",
			"prob_start_date",
			"prob_days",
			"prob_end_date",
			"probation",
			# เนื้อหาสัญญา (ตกลง 2026-11-18, consbiz/contract_terms.py): แม่แบบ + เนื้อหาเฉพาะฉบับ
			"contract_template",
			"heading",
			"designation",
			"department",
			"employer_signer",
			"witnesses",
			"terms",
			"layout",
		),
		# ช่องที่แก้หลัง Submit ได้ (สถานะทดลองงาน ตัดสินเมื่อครบกำหนด)
		"after": ("probation",),
		# Employment Contract TH = HTML จากเนื้อหาสัญญา / Employment Contract = แบบเดิม (Print Designer) ของสัญญาที่ไม่มีเนื้อหา
		"formats": ("Employment Contract TH", "Employment Contract", "Employee Evaluation Form"),
	},
	"hr-wht": {
		"doctype": "WHT Employee",
		"list": ("employee", "full_name", "company", "date", "income_tax_form", "tax_payer"),
		"date": "date",
		"input": (
			"company",
			"employee",
			"full_name",
			"tax_id",
			"address",
			"company_address",
			"is_agent",
			"withholding_agent_for",
			"income_tax_form",
			"tax_payer",
			"date",
		),
		"after": (),
		"formats": ("WHT Employee",),
	},
	# ใบเตือน (Employee Warning, ตกลง 2026-11-17) หลังยืนยันแก้ได้เฉพาะการรับทราบ
	"hr-warnings": {
		"doctype": "Employee Warning",
		"list": ("employee", "employee_name", "company", "date", "level", "category", "acknowledged", "refused"),
		"date": "date",
		"input": (
			"employee",
			"date",
			"level",
			"category",
			"incident_date",
			"description",
			"regulation",
			"corrective_action",
			"witness",
			"acknowledged",
			"acknowledged_date",
			"refused",
		),
		"after": ("acknowledged", "acknowledged_date", "refused"),
		"formats": ("Employee Warning",),
	},
}
WHT_ITEM = ("type_of_income", "description", "tax_base", "tax_rate")
STATUS = {0: (_("ร่าง"), "gray"), 1: (_("ยืนยันแล้ว"), "green"), 2: (_("ยกเลิก"), "rose")}
PROBATION = {"ผ่าน": (_("ผ่านทดลองงาน"), "green"), "ไม่ผ่าน": (_("ไม่ผ่านทดลองงาน"), "rose")}


def config_of(kind):
	if kind not in KINDS:
		frappe.throw(_("ไม่รองรับเอกสารชนิดนี้"), frappe.PermissionError)
	return KINDS[kind]


def readable_kinds():
	return [kind for kind, c in KINDS.items() if frappe.has_permission(c["doctype"], "read")]


def boot_permissions():
	"""boot.hr_docs: ชนิดที่อ่านได้ = มีเมนู, create = ปุ่มสร้าง"""
	return {
		kind: {"create": bool(frappe.has_permission(KINDS[kind]["doctype"], "create"))}
		for kind in readable_kinds()
	}


def label_status(kind, row):
	label, tone = STATUS.get(cint(row.get("docstatus")), STATUS[0])
	if kind == "hr-contracts" and cint(row.get("docstatus")) == 1:
		if row.get("probation") in PROBATION:
			label, tone = PROBATION[row.probation]
		elif row.get("prob_end_date") and getdate(row.prob_end_date) <= getdate(nowdate()):
			label, tone = _("ครบทดลองงาน รอประเมิน"), "amber"
		elif row.get("prob_end_date"):
			label, tone = _("ทดลองงาน"), "blue"
	if kind == "hr-warnings" and cint(row.get("docstatus")) == 1:
		if cint(row.get("acknowledged")):
			label, tone = _("รับทราบแล้ว"), "green"
		elif cint(row.get("refused")):
			label, tone = _("ไม่ยอมลงชื่อ"), "rose"
		else:
			label, tone = _("รอรับทราบ"), "amber"
	row["status_label"], row["status_tone"] = label, tone
	return row


@frappe.whitelist()
def get_list(kind, company=None, project=None):
	config = config_of(kind)
	frappe.has_permission(config["doctype"], "read", throw=True)
	filters = {"company": company} if company else {}
	rows = row_social.get_list(
		config["doctype"],
		filters=filters,
		fields=["name", "docstatus", "modified", *config["list"]],
		order_by=f"{config['date']} desc, creation desc",
		limit_page_length=500,
	)
	if kind == "hr-wht" and rows:
		totals = {}
		for parent, base, tax in frappe.get_all(
			"Withholding Tax Items",
			filters={"parenttype": "WHT Employee", "parent": ("in", [r.name for r in rows])},
			fields=["parent", "tax_base", "tax_amount"],
			as_list=True,
		):
			total = totals.setdefault(parent, [0, 0])
			total[0] += flt(base)
			total[1] += flt(tax)
		for row in rows:
			row.tax_base, row.tax_amount = totals.get(row.name, (0, 0))
	return [label_status(kind, row) for row in rows]


@frappe.whitelist()
def get_summary(**_kwargs):
	"""ตัวเลขเมนูสัญญาจ้าง: ครบทดลองงานแล้วยังไม่ได้ประเมิน (สถานะทดลองงานว่าง)"""
	if not frappe.has_permission("Employment Contract", "read"):
		return {}
	due = frappe.db.count(
		"Employment Contract",
		{"docstatus": 1, "probation": ("in", ("", None)), "prob_end_date": ("<=", nowdate())},
	)
	return {"probation_due": {"count": due}}


# ---------------------------------------------------------------- หน้าเอกสาร


def pdfs(kind, doc):
	from urllib.parse import urlencode

	from consbiz.site_app import print_options

	out = []
	for fmt in KINDS[kind]["formats"]:
		if not frappe.db.exists("Print Format", {"name": fmt, "disabled": 0}):
			continue
		if kind == "hr-contracts" and fmt in ("Employment Contract TH", "Employment Contract"):
			if bool(doc.get("terms")) != (fmt == "Employment Contract TH"):
				continue
		pf = frappe.db.get_value("Print Format", fmt, ["pdf_generator", "print_designer"], as_dict=True)
		# แบบของ Print Designer ออกแบบมาให้ Chrome สร้าง PDF (wkhtmltopdf วาดข้อความซ้อน)
		# สัญญาจ้าง HTML ฝังฟอนต์เป็น data URI: ต้องใช้ chrome (wkhtmltopdf อ่าน woff2 ไม่ได้ = ฟอนต์ระบบ) ตั้งใน JSON ของ Print Format แล้ว
		generator = "chrome" if pf.print_designer else pf.pdf_generator or print_options(doc.doctype)[1]
		params = {
			"doctype": doc.doctype,
			"name": doc.name,
			"format": fmt,
			"no_letterhead": 0,
			"pdf_generator": generator,
		}
		label = {"Employee Evaluation Form": _("แบบประเมินทดลองงาน"), "Employment Contract TH": _("สัญญาจ้าง")}.get(fmt, _("พิมพ์"))
		out.append(
			{"label": label, "url": "/api/method/frappe.utils.print_format.download_pdf?" + urlencode(params)}
		)
	return out


def serialize(kind, doc):
	config = KINDS[kind]
	saved = not doc.is_new()
	out = frappe._dict(
		{
			"name": doc.name if saved else None,
			"docstatus": doc.docstatus,
			"modified": str(doc.modified) if saved else None,
			**{field: doc.get(field) for field in config["input"]},
		}
	)
	if kind == "hr-contracts":
		out.update(salutation=doc.salutation, full_name=doc.full_name)
	elif kind == "hr-warnings":
		out.update(
			employee_name=doc.employee_name,
			designation=doc.designation,
			company=doc.company,
			issued_by=doc.issued_by,
			previous=[
				{**r, "date": str(r.date)} for r in (doc.previous_warnings() if doc.employee else [])
			],
		)
	else:
		out.update(
			company_tax_id=doc.company_tax_id,
			withholding_agent_for_name=doc.withholding_agent_for_name,
			items=[
				{field: row.get(field) for field in (*WHT_ITEM, "tax_amount")}
				for row in doc.withholding_tax_items
			],
		)
	label_status(kind, out)
	can_write = bool(doc.has_permission("write")) if saved else True
	return {
		"doc": out,
		"can_edit": doc.docstatus == 0 and can_write,
		"can_edit_after": doc.docstatus == 1 and can_write and bool(config["after"]),
		"can_submit": saved and doc.docstatus == 0 and bool(doc.has_permission("submit")),
		"can_cancel": doc.docstatus == 1 and bool(doc.has_permission("cancel")),
		"can_delete": saved and store_app.can_delete(doc),
		"pdfs": pdfs(kind, doc) if saved else [],
	}


@frappe.whitelist()
def get_doc(kind, name=None, company=None):
	config = config_of(kind)
	if name:
		doc = frappe.get_doc(config["doctype"], name)
		doc.check_permission("read")
	else:
		doc = frappe.new_doc(config["doctype"])
		doc.check_permission("create")
		doc.company = company or frappe.defaults.get_user_default("Company")
		if kind == "hr-wht":
			doc.date = nowdate()
			doc.tax_payer = "Withholding"
		if kind == "hr-warnings":
			doc.date = nowdate()
			doc.level, doc.category = "Written 1", "Late"
		if kind == "hr-contracts":
			from consbiz.contract_terms import default_template

			apply_template(doc, default_template(doc.company))
	return serialize(kind, doc)


@frappe.whitelist()
def employee_info(employee):
	"""ข้อมูลพนักงานที่เติมให้ฟอร์ม (ชื่อ, เลขบัตร, ที่อยู่, บริษัท, เงินเดือนปัจจุบัน)"""
	frappe.has_permission("Employee", "read", employee, throw=True)
	info = frappe.db.get_value(
		"Employee",
		employee,
		["employee_name", "salutation", "company", "custom_id_card", "permanent_address", "date_of_joining"],
		as_dict=True,
	)
	from consbiz.contract_terms import strip_abbr

	info.designation = frappe.db.get_value("Employee", employee, "designation")
	info.department = strip_abbr(frappe.db.get_value("Employee", employee, "department"), info.company)
	info.base = frappe.db.get_value(
		"Salary Structure Assignment",
		{"employee": employee, "docstatus": 1},
		"base",
		order_by="from_date desc",
	)
	return info


def apply_template(doc, name):
	"""คัดลอกแม่แบบลงสัญญา (เนื้อหา ชื่อเอกสาร ผู้ลงนาม พยาน) แล้วแก้เฉพาะฉบับได้"""
	if not name:
		return
	tpl = frappe.db.get_value(
		"Employment Contract Template", name, ["heading", "employer_signer", "witnesses", "terms", "layout"], as_dict=True
	)
	if tpl:
		doc.contract_template = name
		doc.update(tpl)


def fill_contract(doc, data):
	from consbiz.contract_terms import strip_abbr

	if doc.employee:
		emp = frappe.db.get_value(
			"Employee", doc.employee, ["salutation", "employee_name", "designation", "department"], as_dict=True
		)
		doc.salutation, doc.full_name = emp.salutation, emp.employee_name
		doc.designation = doc.designation or emp.designation
		doc.department = doc.department or strip_abbr(emp.department, doc.company)
	if doc.contract_template and not doc.terms:
		apply_template(doc, doc.contract_template)
	if not doc.naming_series:
		doc.naming_series = (
			frappe.get_meta(doc.doctype).get_field("naming_series").default or "EC-.ABBR..YY..####"
		)
	if doc.prob_start_date and doc.prob_days and not data.get("prob_end_date"):
		doc.prob_end_date = add_days(doc.prob_start_date, cint(doc.prob_days) - 1)


def fill_warning(doc, data):
	if not doc.naming_series:
		doc.naming_series = frappe.get_meta(doc.doctype).get_field("naming_series").default


def fill_wht(doc, data):
	doc.company_tax_id = frappe.db.get_value("Company", doc.company, "tax_id")
	if not doc.company_address:
		doc.company_address = frappe.db.get_value("Company", doc.company, "custom_company_address")
	if doc.employee:
		emp = frappe.db.get_value(
			"Employee", doc.employee, ["employee_name", "custom_id_card", "permanent_address"], as_dict=True
		)
		doc.full_name = doc.full_name or emp.employee_name
		doc.tax_id = doc.tax_id or emp.custom_id_card
		doc.address = doc.address or emp.permanent_address
	if not cint(doc.is_agent):
		doc.withholding_agent_for = None
	doc.withholding_agent_for_name = (
		frappe.db.get_value("Supplier", doc.withholding_agent_for, "supplier_name")
		if doc.withholding_agent_for
		else None
	)
	doc.set("withholding_tax_items", [])
	for row in data.get("items") or []:
		base, rate = flt(row.get("tax_base")), flt(row.get("tax_rate"))
		doc.append(
			"withholding_tax_items",
			{
				"type_of_income": row.get("type_of_income"),
				"description": row.get("description"),
				"tax_base": base,
				"tax_rate": rate,
				"tax_amount": flt(base * rate / 100, 2),
			},
		)
	if not doc.withholding_tax_items:
		frappe.throw(_("กรุณาเพิ่มรายการเงินได้อย่างน้อย 1 รายการ"))


@frappe.whitelist(methods=["POST"])
def save_doc(kind, data, submit=0):
	config = config_of(kind)
	data = frappe._dict(json.loads(data) if isinstance(data, str) else data)
	if data.name:
		doc = frappe.get_doc(config["doctype"], data.name)
		doc.check_permission("write")
		if data.modified and str(doc.modified) != str(data.modified):
			frappe.throw(_("มีผู้อื่นแก้ไข {0} ไปแล้ว กรุณาโหลดใหม่").format(doc.name))
	else:
		doc = frappe.new_doc(config["doctype"])
		doc.check_permission("create")

	if doc.docstatus == 1:
		# หลังยืนยันแก้ได้เฉพาะช่อง after (ช่องที่ DocType อนุญาตหลัง Submit)
		if not config["after"]:
			frappe.throw(_("{0} ยืนยันแล้ว แก้ไขไม่ได้").format(doc.name))
		for field in config["after"]:
			if field in data:
				doc.set(field, data[field])
		doc.save()
		return serialize(kind, doc)
	if doc.docstatus == 2:
		frappe.throw(_("{0} ถูกยกเลิกแล้ว").format(doc.name))

	for field in config["input"]:
		if field in data:
			doc.set(field, data[field])
	{"hr-contracts": fill_contract, "hr-warnings": fill_warning}.get(kind, fill_wht)(doc, data)
	doc.save()
	if cint(submit):
		doc.submit()
	return serialize(kind, doc)


def load(kind, name):
	doc = frappe.get_doc(config_of(kind)["doctype"], name)
	doc.check_permission("read")
	return doc


@frappe.whitelist(methods=["POST"])
def submit_doc(kind, name):
	doc = load(kind, name)
	doc.submit()
	return serialize(kind, doc)


@frappe.whitelist(methods=["POST"])
def cancel_doc(kind, name):
	doc = load(kind, name)
	doc.cancel()
	return serialize(kind, frappe.get_doc(doc.doctype, doc.name))


@frappe.whitelist(methods=["POST"])
def delete_doc(kind, name):
	store_app.delete_document(load(kind, name))


@frappe.whitelist()
def income_types():
	"""ประเภทเงินได้ของ 50 ทวิ (Withholding Tax Type Of Income ของ erpnext_thailand) + คำอธิบายจากตารางเดิม"""
	if not frappe.has_permission("WHT Employee", "read"):
		frappe.throw(_("ไม่มีสิทธิ์"), frappe.PermissionError)
	return frappe.get_all("Withholding Tax Type Of Income", pluck="name", order_by="name asc")


SEARCH = {"Employee": "employee_name", "Supplier": "supplier_name"}


@frappe.whitelist()
def search(doctype, txt="", company=None):
	"""ค้นหาในฟอร์ม: พนักงาน (ของบริษัทที่เลือก) / ผู้ขาย (ผู้ถูกหักแทน)"""
	if not readable_kinds():
		frappe.throw(_("ไม่มีสิทธิ์"), frappe.PermissionError)
	field = SEARCH.get(doctype)
	if not field:
		frappe.throw(_("ค้นหา {0} ไม่ได้").format(doctype))
	txt = (txt or "").strip()
	filters = {"disabled": 0} if doctype == "Supplier" else {"status": ("!=", "Left")}
	if doctype == "Employee" and company:
		filters["company"] = company
	rows = frappe.get_list(
		doctype,
		filters=filters,
		or_filters=[["name", "like", f"%{txt}%"], [field, "like", f"%{txt}%"]] if txt else None,
		fields=["name", f"{field} as label"],
		order_by="modified desc",
		limit_page_length=30,
	)
	return [{"value": r.name, "label": r.label or r.name, "description": r.name} for r in rows]
