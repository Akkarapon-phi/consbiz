# กลุ่ม Item ของชนิดคอนกรีตใน Concrete Usage (ช่อง "ชนิดคอนกรีต" แสดงเฉพาะ Item ในกลุ่มนี้และกลุ่มย่อย)
# สร้างให้ถ้ายังไม่มี Item คอนกรีตที่มีอยู่แล้วต้องย้ายเข้ากลุ่มเอง (เป็นข้อมูล ไม่ใช่โค้ด)

import frappe

from consbiz.consbiz.doctype.concrete_usage.concrete_usage import CONCRETE_GROUP


def execute():
	if frappe.db.exists("Item Group", CONCRETE_GROUP):
		return
	root = frappe.db.get_value("Item Group", {"is_group": 1, "parent_item_group": ("is", "not set")}, "name")
	if not root:
		return
	frappe.get_doc(
		{"doctype": "Item Group", "item_group_name": CONCRETE_GROUP, "parent_item_group": root, "is_group": 0}
	).insert(ignore_permissions=True)
