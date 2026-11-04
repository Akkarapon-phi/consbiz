import re

import frappe
from frappe.utils import flt

# ชุดบันทึกการส่งใบกำกับภาษีให้สำนักงานบัญชีที่เลิกใช้แล้ว (ตารางในฐานข้อมูลยังอยู่ ลบแค่ DocType)
OLD_DOCTYPES = ("Transmittal Note", "Transmittal Item", "Transmittal Entry")

# ของที่ผูกกับ DocType: (doctype, fieldname ที่เก็บชื่อ DocType)
LINKED = (
	("Custom Field", "dt"),
	("Property Setter", "doc_type"),
	("Client Script", "dt"),
	("Print Format", "doc_type"),
	("Workflow", "document_type"),
)

NUMBER = re.compile(r"^(-?[\d,]*\.?\d+)\s*(.*)$")


def execute():
	"""ใบนำส่งเอกสารเหลือตัวเดียว: ลบ Transmittal Entry / Note แล้วเปลี่ยนชื่อ Transmittal Ext เป็น Transmittal

	รันก่อน model sync เพราะโฟลเดอร์ DocType เก่าไม่มีใน repo แล้ว (ไม่งั้น migrate ลบเป็น orphan)
	และคอลัมน์ amount (ข้อความ เก็บจำนวน) ต้องย้ายเป็น qty ก่อน sync เปลี่ยน amount เป็นยอดเงิน
	"""
	for doctype in OLD_DOCTYPES:
		remove_doctype(doctype)

	if not frappe.db.exists("DocType", "Transmittal Ext") or frappe.db.exists("DocType", "Transmittal"):
		return

	# Workflow (ปิดใช้อยู่), workflow_state และ Property Setter เดิมไม่ใช้แล้ว (ค่าย้ายไปอยู่ใน DocType)
	# default_print_format สร้างใหม่ใน set_transmittal_status
	remove_linked("Transmittal Ext", keep=("Print Format",))
	move_amount_to_qty()

	if frappe.db.exists("Print Format", "Transmittal Ext") and not frappe.db.exists(
		"Print Format", "Transmittal"
	):
		frappe.rename_doc("Print Format", "Transmittal Ext", "Transmittal", force=True)
		replace_in_print_designer("Transmittal")

	frappe.rename_doc("DocType", "Transmittal Ext", "Transmittal", force=True)


def remove_doctype(doctype):
	if not frappe.db.exists("DocType", doctype):
		return
	remove_linked(doctype)
	frappe.delete_doc("DocType", doctype, force=True, ignore_permissions=True, ignore_missing=True)


def remove_linked(doctype, keep=()):
	for linked, field in LINKED:
		if linked in keep or not frappe.db.table_exists(linked):
			continue
		for name in frappe.get_all(linked, filters={field: doctype}, pluck="name"):
			frappe.delete_doc(linked, name, force=True, ignore_permissions=True, ignore_missing=True)


def move_amount_to_qty():
	"""amount เดิมเป็นข้อความ เช่น "5", " 817.00 ", "7380กก." ย้ายเป็น qty (ตัวเลข) + unit
	ค่าที่อ่านเป็นตัวเลขไม่ได้ย้ายไปต่อท้ายหมายเหตุ"""
	if not frappe.db.has_column("Transmittal List", "amount") or frappe.db.has_column(
		"Transmittal List", "qty"
	):
		return

	frappe.db.rename_column("Transmittal List", "amount", "qty")

	table = frappe.qb.DocType("Transmittal List")
	rows = frappe.qb.from_(table).select(table.name, table.qty, table.unit, table.remark).run(as_dict=True)
	for row in rows:
		qty, unit, remark = parse_qty(row.qty, row.unit, row.remark)
		(
			frappe.qb.update(table)
			.set(table.qty, qty)
			.set(table.unit, unit)
			.set(table.remark, remark)
			.where(table.name == row.name)
		).run()


def parse_qty(raw, unit, remark):
	# qty เป็น Float (NOT NULL) ค่าว่าง/อ่านไม่ได้ = 0
	raw = (raw or "").strip()
	if not raw:
		return 0, unit, remark

	match = NUMBER.match(raw)
	rest = match.group(2).strip() if match else ""
	if not match or re.search(r"\d", rest):
		return 0, unit, " ".join(filter(None, [remark, raw]))

	return flt(match.group(1).replace(",", "")), unit or rest or None, remark


def replace_in_print_designer(print_format):
	"""Print Designer เก็บชื่อ DocType ไว้ใน JSON ของรูปแบบ"""
	fields = [
		"print_designer_body",
		"print_designer_header",
		"print_designer_footer",
		"print_designer_after_table",
		"print_designer_print_format",
		"print_designer_settings",
	]
	meta = frappe.get_meta("Print Format")
	fields = [f for f in fields if meta.has_field(f)]
	if not fields:
		return
	values = frappe.db.get_value("Print Format", print_format, fields, as_dict=True) or {}
	updates = {f: v.replace("Transmittal Ext", "Transmittal") for f, v in values.items() if v}
	if updates:
		frappe.db.set_value("Print Format", print_format, updates, update_modified=False)
