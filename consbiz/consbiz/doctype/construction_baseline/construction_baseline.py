# Copyright (c) 2026, Siricons and contributors
# For license information, please see license.txt

# Baseline 1 ชุดของแผนงาน: สำเนาวันเริ่ม/วันจบ/% แผนที่กำหนดเอง/น้ำหนักของทุกแถวงาน ณ วันที่บันทึก
# แผนงานมีได้หลายชุด เปิดดูย้อนหลังในหน้า Gantt ได้ทีละชุด
# ชุดที่ใช้เทียบกับความคืบหน้าจริง (Construction Management.active_baseline) ถูกคัดลอกลงช่อง baseline_* ของแถวงาน
# สร้าง เลือกใช้ และลบผ่านหน้า Gantt (API ใน construction_management.py) ชุดที่ใช้เทียบอยู่ลบไม่ได้

import frappe
from frappe import _
from frappe.model.document import Document


class ConstructionBaseline(Document):
	def on_trash(self):
		if (
			frappe.db.get_value("Construction Management", self.construction_management, "active_baseline")
			== self.name
		):
			frappe.throw(_("Baseline {0} ใช้เทียบกับความคืบหน้าจริงอยู่ ให้เลือกชุดอื่นเป็นตัวเทียบก่อนลบ").format(self.title))
