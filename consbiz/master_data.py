# Copyright (c) 2026, Siricons and contributors
# For license information, please see license.txt

"""ข้อมูลหลักในแอปออฟฟิศ (/conserp/master): ทะเบียนพนักงาน, สินค้า/วัสดุ, ลูกค้า, ผู้ขาย, โครงการ
หน้าจอครอบ DocType เดิมของ ERPNext/HRMS (ไม่มี DocType ใหม่) สร้าง/แก้ได้โดยไม่ต้องเข้าระบบเต็ม

- รายการ = KindList (office_app/views/master/kinds.js) หน้าเดียวทั้งดูและแก้ = MasterPage.vue (`md-doc/<kind>/<name>`)
- ฟอร์มสร้างจาก KINDS ที่นี่ที่เดียว: tab = แต่ละหมวดของ `sections` ชนิดช่อง/ตัวเลือก/บังคับกรอกอ่านจาก meta ของ DocType
  (`schema`) แอปส่งเฉพาะช่องในฟอร์มกลับมา (`save_doc` ตั้งเฉพาะช่องที่อยู่ใน KINDS)
- สิทธิ์ = สิทธิ์ของ DocType (ตั้งในหน้าตั้งค่า หมวดข้อมูลหลัก) ช่อง permlevel ที่ผู้ใช้ไม่มีสิทธิ์ ไม่ส่ง/ไม่รับ
- ลูกค้า/ผู้ขาย: ที่อยู่หลัก (Address ที่ผูกด้วย Dynamic Link) แก้ในหน้าเดียวกัน ใช้ในใบกำกับภาษี/หนังสือรับรอง
- สินค้าคู่ของวัสดุผู้ว่าจ้างจัดหา (custom_base_item, consbiz/employer_supplied.py) ไม่ขึ้นในรายการ เปิดได้แต่แก้ไม่ได้"""

import json

import frappe
from frappe import _
from frappe.utils import cint, flt, getdate

from consbiz import store_app

# ช่องของฟอร์ม: (fieldname, {label, reqd, create_only (แก้ได้ตอนสร้างเท่านั้น), wide (เต็มแถว), filters (Link: {ช่องของ
# DocType ปลายทาง: ช่องในฟอร์ม}), show (แสดงเมื่อ {ช่อง: ค่า}), labels (ป้ายไทยของ Select), select (Link ที่แสดงเป็นตัวเลือก)})
# ช่อง "address.*" = ที่อยู่หลักของลูกค้า/ผู้ขาย (ADDRESS_FIELDS)
STATUS_EMPLOYEE = {"Active": "ทำงานอยู่", "Inactive": "ไม่ใช้งาน", "Suspended": "พักงาน", "Left": "ลาออก"}
PARTY_TYPES = {"Company": "นิติบุคคล", "Individual": "บุคคลธรรมดา", "Partnership": "ห้างหุ้นส่วน"}
GENDERS = {"Male": "ชาย", "Female": "หญิง"}
MARITAL = {"Single": "โสด", "Married": "สมรส", "Divorced": "หย่า", "Widowed": "หม้าย"}
PROJECT_STATUS = {"Open": "ดำเนินการ", "On hold": "พักไว้", "Completed": "เสร็จสิ้น", "Cancelled": "ยกเลิก"}

ADDRESS_FIELDS = (
	("address_line1", "ที่อยู่ (เลขที่ ถนน)", 1),
	("address_line2", "ตำบล / แขวง", 0),
	("city", "อำเภอ / เขต", 1),
	("state", "จังหวัด", 0),
	("pincode", "รหัสไปรษณีย์", 0),
	("phone", "โทรศัพท์", 0),
	("email_id", "อีเมล", 0),
)
ADDRESS_SECTION = {
	"label": "ที่อยู่",
	"note": "ที่อยู่หลักที่ใช้ในใบกำกับภาษีและหนังสือรับรองหัก ณ ที่จ่าย",
	"fields": [
		(
			f"address.{field}",
			{"label": label, "wide": field == "address_line1", "reqd": reqd, "address": True},
		)
		for field, label, reqd in ADDRESS_FIELDS
	],
}

KINDS = {
	"md-employees": {
		"doctype": "Employee",
		"title": "employee_name",
		"list": (
			"employee_name",
			"designation",
			"department",
			"company",
			"date_of_joining",
			"status",
			"custom_project",
		),
		"order": "status asc, name asc",
		"company": True,
		"sections": [
			{
				"label": "ข้อมูลส่วนตัว",
				"fields": [
					("salutation", {"label": "คำนำหน้า"}),
					("first_name", {"label": "ชื่อ"}),
					("last_name", {"label": "นามสกุล"}),
					("gender", {"label": "เพศ", "select": True, "labels": GENDERS}),
					("date_of_birth", {"label": "วันเกิด"}),
					("custom_id_card", {"label": "เลขบัตรประชาชน", "digits": 13}),
					("marital_status", {"label": "สถานภาพ", "labels": MARITAL}),
					("blood_group", {"label": "กรุ๊ปเลือด"}),
				],
			},
			{
				"label": "การจ้างงาน",
				"fields": [
					("company", {"label": "บริษัท", "create_only": True}),
					("date_of_joining", {"label": "วันที่เริ่มงาน"}),
					("status", {"label": "สถานะ", "labels": STATUS_EMPLOYEE}),
					("relieving_date", {"label": "วันที่ออก", "show": {"status": "Left"}, "reqd": 1}),
					("department", {"label": "แผนก", "filters": {"company": "company"}}),
					("designation", {"label": "ตำแหน่ง"}),
					("employment_type", {"label": "ประเภทการจ้าง"}),
					("branch", {"label": "สาขา"}),
					# ไม่กรองตามบริษัท (ตกลง 2026-11-17): พนักงานบริษัทหนึ่งไปประจำโครงการของอีกบริษัทในเครือได้
					("custom_project", {"label": "โครงการที่ประจำ"}),
					("custom_checkin_location", {"label": "จุดลงเวลา (เฉพาะคน)", "widget": "checkin_location", "note": "ว่าง = ใช้จุดของโครงการที่ประจำ"}),
					(
						"reports_to",
						{"label": "หัวหน้างาน", "filters": {"company": "company", "status": "Active"}},
					),
					("user_id", {"label": "ผู้ใช้ในระบบ (User)"}),
				],
			},
			{
				"label": "ติดต่อ",
				"fields": [
					("cell_number", {"label": "มือถือ"}),
					("personal_email", {"label": "อีเมลส่วนตัว"}),
					("company_email", {"label": "อีเมลบริษัท"}),
					("current_address", {"label": "ที่อยู่ปัจจุบัน", "wide": True}),
					("permanent_address", {"label": "ที่อยู่ตามทะเบียนบ้าน", "wide": True}),
					("person_to_be_contacted", {"label": "ผู้ติดต่อกรณีฉุกเฉิน"}),
					("emergency_phone_number", {"label": "เบอร์ฉุกเฉิน"}),
					("relation", {"label": "ความสัมพันธ์"}),
				],
			},
			{
				"label": "เงินเดือนและการลา",
				"fields": [
					(
						"salary_mode",
						{
							"label": "วิธีจ่ายเงินเดือน",
							"labels": {"Bank": "โอนธนาคาร", "Cash": "เงินสด", "Cheque": "เช็ค"},
						},
					),
					("bank_name", {"label": "ธนาคาร", "show": {"salary_mode": "Bank"}}),
					("bank_ac_no", {"label": "เลขบัญชี", "show": {"salary_mode": "Bank"}}),
					("holiday_list", {"label": "ปฏิทินวันหยุด"}),
					("default_shift", {"label": "กะทำงาน"}),
					("leave_approver", {"label": "ผู้อนุมัติการลา"}),
					("expense_approver", {"label": "ผู้อนุมัติเบิกเงิน"}),
				],
			},
		],
	},
	"md-items": {
		"doctype": "Item",
		"title": "item_name",
		"list": ("item_name", "item_group", "stock_uom", "disabled", "is_stock_item", "custom_base_item"),
		"order": "item_name asc",
		# สินค้าคู่ของวัสดุผู้ว่าจ้าง (ระบบสร้าง/ซิงก์เอง) ไม่แสดงในรายการ
		"filters": {"custom_base_item": ("is", "not set")},
		"sections": [
			{
				"label": "ข้อมูลสินค้า",
				"fields": [
					("item_name", {"label": "ชื่อสินค้า/วัสดุ", "wide": True, "reqd": 1}),
					("item_group", {"label": "กลุ่มสินค้า", "filters": {"is_group": 0}}),
					("stock_uom", {"label": "หน่วยนับหลัก"}),
					("purchase_uom", {"label": "หน่วยที่ซื้อ"}),
					("brand", {"label": "ยี่ห้อ"}),
					("standard_rate", {"label": "ราคาขายมาตรฐาน", "create_only": True}),
					("description", {"label": "รายละเอียด", "wide": True, "plain": True}),
					("is_stock_item", {"label": "นับสต็อก", "note": "รับเข้า-เบิกออกผ่านคลัง"}),
					("is_purchase_item", {"label": "ซื้อได้"}),
					("is_sales_item", {"label": "ขายได้"}),
					("disabled", {"label": "ปิดใช้งาน", "note": "ไม่แสดงให้เลือกในเอกสารใหม่"}),
				],
			},
			{
				"label": "หน่วยแปลง",
				"note": "หน่วยอื่นที่ใช้ซื้อ/เบิก เช่น 1 เส้น = 6.17 กก. (หน่วยหลักเท่ากับ 1 เสมอ)",
				"fields": [
					(
						"uoms",
						{
							"label": "หน่วยแปลง",
							"wide": True,
							"columns": (("uom", "หน่วย"), ("conversion_factor", "เท่ากับหน่วยหลัก")),
						},
					),
				],
			},
		],
	},
	"md-customers": {
		"doctype": "Customer",
		"title": "customer_name",
		"list": ("customer_name", "customer_type", "customer_group", "tax_id", "branch_code", "disabled"),
		"order": "customer_name asc",
		"party": "customer_primary_address",
		"sections": [
			{
				"label": "ข้อมูลลูกค้า",
				"fields": [
					("customer_name", {"label": "ชื่อลูกค้า", "wide": True}),
					("customer_type", {"label": "ประเภท", "labels": PARTY_TYPES}),
					("customer_group", {"label": "กลุ่มลูกค้า"}),
					("tax_id", {"label": "เลขประจำตัวผู้เสียภาษี", "digits": 13}),
					("branch_code", {"label": "รหัสสาขา", "note": "สำนักงานใหญ่ = 00000"}),
					("territory", {"label": "เขตการขาย"}),
					("payment_terms", {"label": "เงื่อนไขการชำระเงิน"}),
					("disabled", {"label": "ปิดใช้งาน", "note": "ไม่แสดงให้เลือกในเอกสารใหม่"}),
				],
			},
			ADDRESS_SECTION,
		],
	},
	"md-suppliers": {
		"doctype": "Supplier",
		"title": "supplier_name",
		"list": (
			"supplier_name",
			"supplier_type",
			"supplier_group",
			"tax_id",
			"branch_code",
			"disabled",
			"on_hold",
		),
		"order": "supplier_name asc",
		"party": "supplier_primary_address",
		"sections": [
			{
				"label": "ข้อมูลผู้ขาย",
				"fields": [
					("supplier_name", {"label": "ชื่อผู้ขาย / ผู้รับเหมา", "wide": True}),
					(
						"supplier_type",
						{
							"label": "ประเภท",
							"labels": PARTY_TYPES,
							"note": "บุคคลธรรมดา = ภ.ง.ด.3 อื่น = ภ.ง.ด.53",
						},
					),
					("supplier_group", {"label": "กลุ่มผู้ขาย"}),
					("tax_id", {"label": "เลขประจำตัวผู้เสียภาษี", "digits": 13}),
					("branch_code", {"label": "รหัสสาขา", "note": "สำนักงานใหญ่ = 00000"}),
					("payment_terms", {"label": "เงื่อนไขการชำระเงิน"}),
					("disabled", {"label": "ปิดใช้งาน", "note": "ไม่แสดงให้เลือกในเอกสารใหม่"}),
					("on_hold", {"label": "ระงับการซื้อ/จ่าย"}),
				],
			},
			ADDRESS_SECTION,
		],
	},
	"md-projects": {
		"doctype": "Project",
		"title": "project_name",
		"list": (
			"project_name",
			"company",
			"status",
			"customer",
			"expected_start_date",
			"expected_end_date",
			"custom_abbr",
		),
		"order": "creation desc",
		"company": True,
		"sections": [
			{
				"label": "ข้อมูลโครงการ",
				"fields": [
					("project_name", {"label": "ชื่อโครงการ", "wide": True}),
					(
						"custom_abbr",
						{
							"label": "ตัวย่อ",
							"reqd": 1,
							"create_only": True,
							"note": "ใช้ในเลขโครงการ แก้ภายหลังไม่ได้",
						},
					),
					("company", {"label": "บริษัท", "create_only": True}),
					("status", {"label": "สถานะ", "labels": PROJECT_STATUS}),
					("project_type", {"label": "ประเภทงาน"}),
					("customer", {"label": "ผู้ว่าจ้าง (ลูกค้า)"}),
					("department", {"label": "แผนก", "filters": {"company": "company"}}),
					("expected_start_date", {"label": "วันเริ่มสัญญา"}),
					("expected_end_date", {"label": "วันสิ้นสุดสัญญา"}),
					("cost_center", {"label": "ศูนย์ต้นทุน", "filters": {"company": "company", "is_group": 0}}),
				],
			},
			{
				"label": "หน้างาน",
				"fields": [
					(
						"custom_warehouse_name",
						{
							"label": "ชื่อคลังโครงการ",
							"create_only": True,
							"wide": True,
							"note": "ระบบสร้างคลังให้ตอนบันทึก ว่าง = ใช้ชื่อโครงการ แก้ภายหลังไม่ได้",
						},
					),
					(
						"custom_issue_priority",
						{
							"label": "เบิกวัสดุจากคลังไหนก่อน",
							"labels": {"Employer First": "ของผู้ว่าจ้างก่อน", "Company First": "ของบริษัทก่อน"},
						},
					),
					("custom_checkin_location", {"label": "จุดลงเวลา", "widget": "checkin_location"}),
					("custom_day_off_saturday_percent", {"label": "สัดส่วนหยุดวันเสาร์ (%)"}),
					("holiday_list", {"label": "ปฏิทินวันหยุด"}),
				],
			},
		],
	},
}

# ชนิดช่องของ Frappe → ชนิดในฟอร์มของแอป
TYPES = {
	"Data": "text",
	"Small Text": "textarea",
	"Text": "textarea",
	"Long Text": "textarea",
	"Text Editor": "textarea",
	"Date": "date",
	"Check": "check",
	"Select": "select",
	"Link": "link",
	"Int": "int",
	"Float": "float",
	"Percent": "float",
	"Currency": "money",
	"Table": "table",
}


def config_of(kind):
	if kind not in KINDS:
		frappe.throw(_("ไม่รองรับข้อมูลชนิดนี้"), frappe.PermissionError)
	return KINDS[kind]


def readable_kinds():
	return [kind for kind, c in KINDS.items() if frappe.has_permission(c["doctype"], "read")]


def boot_permissions():
	"""boot.master: ชนิดที่อ่านได้ = มีเมนู, create = ปุ่มสร้าง"""
	return {
		kind: {"create": bool(frappe.has_permission(KINDS[kind]["doctype"], "create"))}
		for kind in readable_kinds()
	}


def form_fields(config):
	for section in config["sections"]:
		yield from section["fields"]


def doc_fields(config):
	"""ช่องของ DocType ที่ฟอร์มรับ (ไม่รวมที่อยู่)"""
	return [field for field, _opts in form_fields(config) if not field.startswith("address.")]


def allowed_levels(doctype, ptype):
	return frappe.get_meta(doctype).get_permlevel_access(ptype)


def option_list(df, opts):
	labels = opts.get("labels") or {}
	if opts.get("select"):
		values = frappe.get_all(df.options, pluck="name", order_by="name asc")
		values = [v for v in values if v in labels] or values
	else:
		values = [v for v in (df.options or "").split("\n") if v]
	return [{"value": v, "label": _(labels.get(v, v))} for v in values]


def field_schema(meta, field, opts):
	if opts.get("address"):
		return {
			"fieldname": field,
			"type": "text",
			"label": _(opts["label"]),
			"reqd": opts.get("reqd", 0),
			"wide": opts.get("wide"),
		}
	df = meta.get_field(field)
	if not df:
		return None
	kind = TYPES.get(df.fieldtype, "text")
	if opts.get("select"):
		kind = "select"
	if df.fieldtype == "Text Editor" and not opts.get("plain"):
		kind = "textarea"
	out = {
		"fieldname": field,
		"type": kind,
		"label": _(opts.get("label") or df.label),
		"reqd": cint(opts.get("reqd", df.reqd)),
		"create_only": bool(opts.get("create_only")),
		"wide": bool(opts.get("wide") or kind in ("textarea", "table")),
		"note": _(opts["note"]) if opts.get("note") else None,
		"show": opts.get("show"),
		"digits": opts.get("digits"),
		"read_only": bool(df.read_only),
		"permlevel": df.permlevel,
		"widget": opts.get("widget"),
	}
	if kind == "select":
		out["options"] = option_list(df, opts)
	elif kind == "link":
		out["doctype"] = df.options
		out["filters"] = opts.get("filters")
	elif kind == "table":
		child = frappe.get_meta(df.options)
		out["columns"] = [
			{
				"fieldname": col,
				"label": _(label),
				"type": TYPES.get(child.get_field(col).fieldtype, "text"),
				"doctype": child.get_field(col).options if child.get_field(col).fieldtype == "Link" else None,
			}
			for col, label in opts["columns"]
		]
	return out


def schema(config):
	meta = frappe.get_meta(config["doctype"])
	readable = allowed_levels(config["doctype"], "read")
	sections = []
	for section in config["sections"]:
		fields = [field_schema(meta, field, opts) for field, opts in section["fields"]]
		fields = [f for f in fields if f and f.get("permlevel", 0) in readable]
		if fields:
			sections.append(
				{
					"label": _(section["label"]),
					"note": _(section["note"]) if section.get("note") else None,
					"fields": fields,
				}
			)
	return sections


# ---------------------------------------------------------------- รายการ


def label_status(kind, row):
	if kind == "md-employees":
		tone = {"Active": "green", "Left": "gray", "Suspended": "amber"}.get(row.status, "gray")
		label = STATUS_EMPLOYEE.get(row.status, row.status)
	elif kind == "md-projects":
		tone = {"Open": "blue", "Completed": "green", "Cancelled": "rose", "On hold": "amber"}.get(
			row.status, "gray"
		)
		label = PROJECT_STATUS.get(row.status, row.status)
	elif cint(row.get("disabled")):
		label, tone = "ปิดใช้งาน", "gray"
	elif cint(row.get("on_hold")):
		label, tone = "ระงับ", "amber"
	else:
		label, tone = "ใช้งาน", "green"
	row["status_label"], row["status_tone"] = _(label), tone
	return row


@frappe.whitelist()
def get_list(kind, company=None, project=None):
	config = config_of(kind)
	frappe.has_permission(config["doctype"], "read", throw=True)
	filters = dict(config.get("filters") or {})
	if company and config.get("company"):
		filters["company"] = company
	rows = frappe.get_list(
		config["doctype"],
		filters=filters,
		fields=["name", "modified", "creation", *config["list"]],
		order_by=config["order"],
		limit_page_length=2000,
	)
	if kind == "md-employees":
		projects = {r.custom_project for r in rows if r.custom_project}
		names = (
			dict(
				frappe.get_all(
					"Project",
					filters={"name": ("in", list(projects))},
					fields=["name", "project_name"],
					as_list=True,
				)
			)
			if projects
			else {}
		)
		for row in rows:
			row.project = row.custom_project and names.get(row.custom_project, row.custom_project)
	if kind == "md-projects":
		customers = {r.customer for r in rows if r.customer}
		names = (
			dict(
				frappe.get_all(
					"Customer",
					filters={"name": ("in", list(customers))},
					fields=["name", "customer_name"],
					as_list=True,
				)
			)
			if customers
			else {}
		)
		for row in rows:
			row.customer_name = row.customer and names.get(row.customer, row.customer)
	return [label_status(kind, row) for row in rows]


# ---------------------------------------------------------------- หน้าข้อมูล


def link_titles(meta, doc, sections):
	"""ป้ายของช่อง Link ที่ค่าเป็นรหัส (โครงการ/ลูกค้า/พนักงาน) → ชื่อที่อ่านได้"""
	titles = {}
	for section in sections:
		for f in section["fields"]:
			value = doc.get(f["fieldname"]) if not f["fieldname"].startswith("address.") else None
			if f["type"] != "link" or not value:
				continue
			title_field = frappe.get_meta(f["doctype"]).title_field
			if title_field and title_field != "name":
				title = frappe.db.get_value(f["doctype"], value, title_field)
				if title and title != value:
					titles[f["fieldname"]] = f"{title} ({value})"
	return titles


def primary_address(config, doc):
	"""ที่อยู่หลักของลูกค้า/ผู้ขาย: ช่อง *_primary_address ก่อน ไม่ตั้ง = Address ที่ผูกไว้ (Billing / preferred ก่อน)"""
	if doc.is_new():
		return None
	name = doc.get(config["party"])
	if name and frappe.db.exists("Address", name):
		return name
	rows = frappe.get_all(
		"Address",
		filters=[
			["Dynamic Link", "link_doctype", "=", doc.doctype],
			["Dynamic Link", "link_name", "=", doc.name],
			["Address", "disabled", "=", 0],
		],
		fields=["name", "is_primary_address", "address_type"],
		order_by="is_primary_address desc, modified desc",
	)
	billing = [r for r in rows if r.address_type == "Billing"]
	return (billing or rows or [frappe._dict(name=None)])[0].name


def serialize(kind, doc):
	config = KINDS[kind]
	sections = schema(config)
	saved = not doc.is_new()
	values = {}
	for section in sections:
		for f in section["fields"]:
			field = f["fieldname"]
			if field.startswith("address."):
				continue
			if f["type"] == "table":
				values[field] = [
					{c["fieldname"]: row.get(c["fieldname"]) for c in f["columns"]}
					for row in doc.get(field) or []
				]
			else:
				values[field] = doc.get(field)
	address = None
	if config.get("party"):
		address = primary_address(config, doc)
		row = (
			frappe.db.get_value("Address", address, [f for f, _l, _r in ADDRESS_FIELDS], as_dict=True)
			if address
			else {}
		)
		for field, _label, _reqd in ADDRESS_FIELDS:
			values[f"address.{field}"] = (row or {}).get(field)
	out = frappe._dict(
		{
			"name": doc.name if saved else None,
			"modified": str(doc.modified) if saved else None,
			"title": doc.get(config["title"]) if saved else None,
			"address": address,
			**values,
		}
	)
	if saved:
		label_status(kind, out)
	twin = kind == "md-items" and doc.get("custom_base_item")
	can_write = (bool(doc.has_permission("write")) if saved else True) and not twin
	writable = allowed_levels(config["doctype"], "write")
	return {
		"doc": out,
		"sections": sections,
		"titles": link_titles(frappe.get_meta(config["doctype"]), doc, sections) if saved else {},
		"writable_levels": writable,
		"can_edit": can_write,
		"can_delete": saved and not twin and store_app.can_delete(doc),
		"note": _("วัสดุผู้ว่าจ้างจัดหาของ {0}: แก้ที่สินค้าหลัก").format(doc.custom_base_item) if twin else None,
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
		if config.get("company"):
			doc.company = company or frappe.defaults.get_user_default("Company")
	return serialize(kind, doc)


def fill_employee(doc):
	# เลขพนักงาน EMP-<ปีที่เริ่มงาน 2 หลัก>... (Naming Series ใช้ custom_year_of_joining แบบ employee.js ของระบบเต็ม)
	if doc.date_of_joining:
		doc.custom_year_of_joining = str(getdate(doc.date_of_joining).year)[-2:]
	if doc.is_new() and not doc.naming_series:
		doc.naming_series = frappe.get_meta("Employee").get_field("naming_series").default
	if doc.status != "Left":
		doc.relieving_date = None


def fill_project(doc):
	if doc.is_new():
		doc.custom_abbr = (doc.custom_abbr or "").strip().upper()
		if not doc.custom_abbr:
			frappe.throw(_("กรุณาใส่ตัวย่อโครงการ (ใช้ในเลขโครงการ)"))
		if not doc.naming_series:
			doc.naming_series = frappe.get_meta("Project").get_field("naming_series").default


def fill_item(doc):
	doc.item_name = (doc.item_name or "").strip()
	if doc.is_new():
		doc.naming_series = doc.naming_series or frappe.get_meta("Item").get_field("naming_series").default
	# หน่วยหลักอยู่ในตารางหน่วยแปลงเสมอ (= 1) แบบที่ ERPNext เติมให้ตอนบันทึก
	doc.uoms = [row for row in doc.uoms if row.uom and row.uom != doc.stock_uom]
	for row in doc.uoms:
		if flt(row.conversion_factor) <= 0:
			frappe.throw(_("หน่วย {0}: ใส่ค่าแปลงหน่วยมากกว่า 0").format(row.uom))
	doc.append("uoms", {"uom": doc.stock_uom, "conversion_factor": 1})
	if doc.purchase_uom and doc.purchase_uom not in {row.uom for row in doc.uoms}:
		frappe.throw(_("หน่วยที่ซื้อ {0} ต้องอยู่ในตารางหน่วยแปลง").format(doc.purchase_uom))


FILL = {"md-employees": fill_employee, "md-projects": fill_project, "md-items": fill_item}


def check_tax_id(value, label):
	if value and not (value.isdigit() and len(value) == 13):
		frappe.throw(_("{0} ต้องเป็นตัวเลข 13 หลัก").format(label))


def save_address(config, doc, data):
	"""ที่อยู่หลักของลูกค้า/ผู้ขาย: แก้ Address เดิม หรือสร้างใหม่แล้วตั้งเป็น *_primary_address"""
	values = {field: (data.get(f"address.{field}") or "").strip() for field, _l, _r in ADDRESS_FIELDS}
	name = primary_address(config, doc)
	if not any(values.values()):
		return
	for field, label, reqd in ADDRESS_FIELDS:
		if reqd and not values[field]:
			frappe.throw(_("กรุณากรอก{0}").format(label))
	if name:
		address = frappe.get_doc("Address", name)
		address.check_permission("write")
	else:
		address = frappe.new_doc("Address")
		address.check_permission("create")
		address.address_title = doc.get(config["title"])
		address.address_type = "Billing"
		address.country = frappe.db.get_default("country") or "Thailand"
		address.is_primary_address = 1
		address.append("links", {"link_doctype": doc.doctype, "link_name": doc.name})
	address.update(values)
	# ใบกำกับภาษี (erpnext_thailand) อ่านเลขภาษี/สาขาจากที่อยู่
	if address.meta.has_field("tax_id"):
		address.tax_id = doc.tax_id
		address.branch_code = doc.get("branch_code")
	address.save()
	if doc.get(config["party"]) != address.name:
		doc.db_set(config["party"], address.name)


@frappe.whitelist(methods=["POST"])
def save_doc(kind, data):
	config = config_of(kind)
	data = frappe._dict(json.loads(data) if isinstance(data, str) else data)
	if data.name:
		doc = frappe.get_doc(config["doctype"], data.name)
		doc.check_permission("write")
		if data.modified and str(doc.modified) != str(data.modified):
			frappe.throw(_("มีผู้อื่นแก้ไข {0} ไปแล้ว กรุณาโหลดใหม่").format(doc.name))
		if kind == "md-items" and doc.custom_base_item:
			frappe.throw(_("วัสดุผู้ว่าจ้างจัดหา แก้ที่สินค้าหลัก {0}").format(doc.custom_base_item))
	else:
		doc = frappe.new_doc(config["doctype"])
		doc.check_permission("create")

	writable = allowed_levels(config["doctype"], "write")
	meta = frappe.get_meta(config["doctype"])
	opts_of = dict(form_fields(config))
	for field in doc_fields(config):
		if field not in data:
			continue
		df = meta.get_field(field)
		if not df or df.read_only or df.permlevel not in writable:
			continue
		if opts_of[field].get("create_only") and not doc.is_new():
			continue
		if df.fieldtype == "Table":
			columns = [col for col, _label in opts_of[field]["columns"]]
			doc.set(field, [{col: row.get(col) for col in columns} for row in data[field] or []])
		else:
			value = data[field]
			doc.set(field, value.strip() if isinstance(value, str) else value)
	for field, opts in form_fields(config):
		if opts.get("digits") == 13 and not field.startswith("address."):
			check_tax_id(doc.get(field), _(opts["label"]))
	if FILL.get(kind):
		FILL[kind](doc)
	doc.save()
	if config.get("party"):
		save_address(config, doc, data)
		doc.reload()
	return serialize(kind, doc)


@frappe.whitelist(methods=["POST"])
def delete_doc(kind, name):
	doc = frappe.get_doc(config_of(kind)["doctype"], name)
	doc.check_permission("read")
	store_app.delete_document(doc)


@frappe.whitelist()
def search(kind, doctype, txt="", filters=None):
	"""ค้นหาช่อง Link ของฟอร์ม: เฉพาะ DocType ที่อยู่ในฟอร์มของ kind นี้ (สิทธิ์ตาม search_link ของ Frappe)"""
	config = config_of(kind)
	frappe.has_permission(config["doctype"], "read", throw=True)
	allowed = set()
	for section in schema(config):
		for f in section["fields"]:
			if f["type"] == "link":
				allowed.add(f["doctype"])
			for col in f.get("columns") or []:
				if col.get("doctype"):
					allowed.add(col["doctype"])
	if doctype not in allowed:
		frappe.throw(_("ค้นหา {0} ไม่ได้").format(doctype), frappe.PermissionError)
	from frappe.desk.search import search_link

	filters = json.loads(filters) if isinstance(filters, str) else filters or {}
	if frappe.get_meta(doctype).has_field("disabled") and "disabled" not in filters:
		filters["disabled"] = 0
	if doctype == "UOM":
		filters["enabled"] = 1
	return [
		{"value": r["value"], "label": r.get("label") or r["value"], "description": r.get("description")}
		for r in search_link(
			doctype, txt or "", filters=filters, page_length=30, reference_doctype=config["doctype"]
		)
	]


# ---------------------------------------------------------------- จุดลงเวลา (Shift Location) ตกลง 2026-11-17
# ตั้งจากฟอร์มโครงการ/พนักงานในแอป: ใช้ GPS ของมือถือที่หน้างาน + รัศมี ผู้ใช้ไม่ต้องรู้จัก Shift Location
# API คืนชื่อจุด แล้วฟอร์มใส่ลงช่อง custom_checkin_location บันทึกพร้อมฟอร์ม (เอกสารใหม่ก็ใช้ได้)
# สิทธิ์: เขียนชนิดเอกสารนั้นได้ (Project / Employee) หรือ HR จุดที่ใช้ร่วมกับเอกสารอื่น แก้แล้วสร้างจุดใหม่ (ไม่กระทบคนอื่น)

LOCATION_KINDS = ("md-projects", "md-employees")
MAX_RADIUS = 5000


def location_users(location, kind=None, name=None):
	"""เอกสารที่ใช้จุดนี้ (ไม่รวมเอกสารที่กำลังแก้)"""
	out = []
	for doctype in ("Project", "Employee"):
		rows = frappe.get_all(doctype, filters={"custom_checkin_location": location}, pluck="name")
		current = name if kind and KINDS[kind]["doctype"] == doctype else None
		out += [(doctype, r) for r in rows if r != current]
	return out


def check_location_rights(kind):
	from consbiz.self_service import is_hr

	if kind not in LOCATION_KINDS:
		frappe.throw(_("ไม่รองรับข้อมูลชนิดนี้"), frappe.PermissionError)
	if not (is_hr() or frappe.has_permission(KINDS[kind]["doctype"], "write")):
		frappe.throw(_("ไม่มีสิทธิ์ตั้งจุดลงเวลา"), frappe.PermissionError)


@frappe.whitelist()
def get_checkin_location(kind, location, name=None):
	check_location_rights(kind)
	row = frappe.db.get_value(
		"Shift Location", location, ["name", "location_name", "latitude", "longitude", "checkin_radius as radius"], as_dict=True
	)
	if not row:
		frappe.throw(_("ไม่พบจุดลงเวลา {0}").format(location))
	row.shared = len(location_users(location, kind, name))
	return row


def unique_location_name(label):
	label = (label or "").strip()[:120] or _("จุดลงเวลา")
	name, n = label, 2
	while frappe.db.exists("Shift Location", name):
		name, n = f"{label} ({n})", n + 1
	return name


@frappe.whitelist(methods=["POST"])
def save_checkin_location(kind, label, latitude, longitude, radius, location=None, name=None, in_place=0):
	"""สร้าง/แก้จุดลงเวลา คืน {name, location_name} location = จุดเดิมในช่อง name = เอกสารที่กำลังแก้ (ว่าง = เอกสารใหม่)
	in_place = แก้จุดเดิมแม้ใช้ร่วมกัน (หน้ากะของ HR จัดการจุดทั้งหมด) เฉพาะ HR"""
	from consbiz.self_service import is_hr

	check_location_rights(kind)
	latitude, longitude, radius = flt(latitude), flt(longitude), cint(radius)
	if not (-90 <= latitude <= 90 and -180 <= longitude <= 180) or (not latitude and not longitude):
		frappe.throw(_("พิกัดไม่ถูกต้อง"))
	if not 10 <= radius <= MAX_RADIUS:
		frappe.throw(_("รัศมีต้องอยู่ระหว่าง 10 ถึง {0} เมตร").format(MAX_RADIUS))
	label = (label or "").strip()
	if not label:
		frappe.throw(_("ระบุชื่อจุดลงเวลา"))
	shared = location and not (cint(in_place) and is_hr()) and location_users(location, kind, name)
	if location and frappe.db.exists("Shift Location", location) and not shared:
		doc = frappe.get_doc("Shift Location", location)
	else:
		doc = frappe.new_doc("Shift Location")
		doc.location_name = unique_location_name(label)
	doc.latitude, doc.longitude, doc.checkin_radius = latitude, longitude, radius
	# แผนที่ในฟอร์มระบบเต็ม (GeoJSON ลำดับ ลองจิจูด, ละติจูด)
	doc.geolocation = json.dumps(
		{
			"type": "FeatureCollection",
			"features": [{"type": "Feature", "properties": {}, "geometry": {"type": "Point", "coordinates": [longitude, latitude]}}],
		}
	)
	doc.save(ignore_permissions=True)
	return {"name": doc.name, "location_name": doc.location_name, "created": doc.name != location}
