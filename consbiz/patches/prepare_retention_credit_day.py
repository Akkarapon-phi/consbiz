# credit_day ของ Retention Invoice / Release เปลี่ยนจาก Data เป็น Int
# ค่าว่าง/NULL/ไม่ใช่ตัวเลข ทำให้ ALTER เป็น int NOT NULL ไม่ผ่าน จึงตั้งเป็น "0" ก่อน migrate DocType

import frappe


def execute():
	for doctype in ("Retention Invoice", "Retention Release"):
		if not frappe.db.table_exists(doctype) or not frappe.db.has_column(doctype, "credit_day"):
			continue
		table = frappe.qb.DocType(doctype)
		rows = frappe.qb.from_(table).select(table.name, table.credit_day).run(as_dict=True)
		for row in rows:
			value = str(row.credit_day or "").strip()
			if not value.isdigit():
				frappe.qb.update(table).set(table.credit_day, "0").where(table.name == row.name).run()
			elif value != row.credit_day:
				frappe.qb.update(table).set(table.credit_day, value).where(table.name == row.name).run()
