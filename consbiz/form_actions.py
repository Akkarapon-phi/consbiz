"""คำสั่งกลางของหัวฟอร์มในแอป ConsERP (เมนู ⋯ ของ FormHead.vue)

ทำซ้ำ (duplicate) = แบบปุ่ม Duplicate ของระบบเต็ม: คัดลอกช่องที่ไม่ใช่ no_copy เป็นร่างใหม่
ต่างกันที่แอปบันทึกร่างให้ทันที (หน้าฟอร์มของแอปเปิดเอกสารด้วยเลขที่) แล้วพาไปแก้ต่อ
ทำซ้ำได้เฉพาะชนิดใน DUPLICATE (ชนิดที่มีได้ใบเดียวต่อโครงการ/รอบ หรือต้องอ้างเอกสารต้นทาง ไม่ทำซ้ำ)
"""

import frappe
from frappe import _
from frappe.utils import getdate, nowdate

# ชนิดเอกสารที่ทำซ้ำได้ → ช่อง/ตารางที่ล้างเพิ่มจาก no_copy
DUPLICATE = {
	"Material Request": [],
	"Purchase Order": ["payment_schedule"],
	"Purchase Invoice": ["payment_schedule", "due_date", "bill_no", "bill_date"],
	"Quotation": ["payment_schedule"],
	"Sales Order": ["payment_schedule"],
	"Sales Invoice": ["payment_schedule", "due_date"],
	"Letter Out": [],
	"Transmittal": ["sent_date", "received_date"],
	"Envelope": [],
	"Subcontract Agreement": [],
	"Inspection Request": [],
	"Punch List": [],
	"Concrete Usage": [],
	"Bar Cut Plan": [],
	"Employment Contract": [],
}

# วันที่ที่ห้ามก่อนวันเอกสาร: ของเดิมผ่านมาแล้ว = วันนี้
FUTURE_DATES = ("schedule_date", "delivery_date", "valid_till", "required_by")


def duplicable():
	"""ชนิดที่ผู้ใช้ทำซ้ำได้ (มีสิทธิ์สร้าง) ใส่ใน boot ของแอป"""
	return [doctype for doctype in DUPLICATE if frappe.has_permission(doctype, "create")]


@frappe.whitelist(methods=["POST"])
def duplicate(doctype, name):
	if doctype not in DUPLICATE:
		frappe.throw(_("เอกสารชนิดนี้ทำซ้ำในแอปไม่ได้"))
	source = frappe.get_doc(doctype, name)
	source.check_permission("read")
	frappe.has_permission(doctype, "create", throw=True)

	doc = frappe.copy_doc(source)
	doc.docstatus = 0
	for row in doc.get_all_children():
		row.docstatus = 0
	if doc.meta.has_field("amended_from"):
		doc.amended_from = None
	for field in DUPLICATE[doctype]:
		df = doc.meta.get_field(field)
		if df and df.fieldtype == "Table":
			doc.set(field, [])
		elif df:
			doc.set(field, None)
	if doctype == "Subcontract Agreement":
		# รายการแนบท้าย (ใบงานเพิ่ม) เป็นของสัญญาเดิม
		doc.set("items", [row for row in doc.get("items") if not row.get("variation")])
	keep_mandatory(doc, source)
	reset_dates(doc)
	reset_status(doc)
	doc.insert()
	return {"name": doc.name}


def keep_mandatory(doc, source):
	"""ช่องบังคับกรอกที่เป็น no_copy (เช่น ชื่อเรื่องของใบนำส่ง) ใช้ค่าเดิม ไม่งั้นบันทึกร่างไม่ได้"""
	for df in doc.meta.fields:
		if df.reqd and df.no_copy and not doc.get(df.fieldname) and source.get(df.fieldname):
			if df.fieldtype not in ("Table", "Table MultiSelect"):
				doc.set(df.fieldname, source.get(df.fieldname))


def reset_dates(doc):
	today = getdate(nowdate())
	for df in doc.meta.fields:
		if df.fieldtype == "Date" and (df.default or "").lower() == "today":
			doc.set(df.fieldname, today)
	for row in [doc, *doc.get_all_children()]:
		for field in FUTURE_DATES:
			value = row.get(field)
			if value and getdate(value) < today:
				row.set(field, today)


def reset_status(doc):
	df = doc.meta.get_field("status")
	if df and df.fieldtype == "Select":
		options = [o for o in (df.options or "").split("\n") if o]
		doc.status = df.default or ("Draft" if "Draft" in options else (options[0] if options else None))
