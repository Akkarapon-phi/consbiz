# หมวดต้นทุนตั้งต้นของ Cost Control (ข้ามที่มีอยู่แล้ว แก้ชื่อ/ลบ/เพิ่มเองได้ในหน้า Cost Category)

import frappe

DEFAULT_CATEGORIES = ["วัสดุ", "ค่าแรง", "เครื่องจักร", "ผู้รับเหมาช่วง", "ค่าใช้จ่ายหน้างาน"]


def execute():
	for sequence, name in enumerate(DEFAULT_CATEGORIES, start=1):
		if not frappe.db.exists("Cost Category", name):
			frappe.get_doc({"doctype": "Cost Category", "category_name": name, "sequence": sequence}).insert(
				ignore_permissions=True
			)
