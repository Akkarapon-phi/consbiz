import frappe


def execute():
	"""ใบนำส่งเดิม (ก่อนมีผู้รับ/สถานะ): ผู้รับ = อื่นๆ, สถานะตามวันที่ส่ง และตั้ง Print Format เริ่มต้น"""
	if not frappe.db.table_exists("Transmittal"):
		return

	table = frappe.qb.DocType("Transmittal")
	frappe.qb.update(table).set(table.recipient_type, "Other").where(
		table.recipient_type.isnull() | (table.recipient_type == "")
	).run()

	for status, condition in (
		("Draft", table.docstatus == 0),
		("Cancelled", table.docstatus == 2),
		("Received", (table.docstatus == 1) & table.received_date.isnotnull()),
		("Sent", (table.docstatus == 1) & table.received_date.isnull() & table.sent_date.isnotnull()),
		("To Send", (table.docstatus == 1) & table.received_date.isnull() & table.sent_date.isnull()),
	):
		frappe.qb.update(table).set(table.status, status).where(condition).run()

	remove_naming_series_setters()
	set_default_print_format()


def remove_naming_series_setters():
	# ตอน sync Frappe เก็บตัวเลือกเลขชุดเดิมใน DocField (ซึ่งว่าง เพราะเดิมตั้งผ่าน Property Setter) เป็น Property Setter
	# ตัวเลือกอยู่ใน transmittal.json แล้ว ลบทิ้งไม่ให้ทับ
	for name in frappe.get_all(
		"Property Setter",
		filters={"doc_type": "Transmittal", "field_name": "naming_series", "property": ("in", ["options", "default"])},
		pluck="name",
	):
		frappe.delete_doc("Property Setter", name, force=True, ignore_permissions=True)
	frappe.clear_cache(doctype="Transmittal")


def set_default_print_format():
	# DocType standard มี default_print_format ไม่ได้ ใช้ Property Setter แบบที่ Customize Form ทำ
	if not frappe.db.exists("Print Format", "Transmittal"):
		return
	if frappe.db.exists(
		"Property Setter", {"doc_type": "Transmittal", "property": "default_print_format"}
	):
		return
	frappe.get_doc(
		{
			"doctype": "Property Setter",
			"doctype_or_field": "DocType",
			"doc_type": "Transmittal",
			"property": "default_print_format",
			"property_type": "Data",
			"value": "Transmittal",
			"module": "ConsBiz",
			"is_system_generated": 1,
		}
	).insert(ignore_permissions=True)
