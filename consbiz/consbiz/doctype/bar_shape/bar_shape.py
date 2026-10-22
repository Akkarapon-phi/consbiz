# Copyright (c) 2026, Siricons and contributors
# For license information, please see license.txt

# รูปแบบการดัดเหล็ก: ด้านที่ต้องกรอก (A-D), สูตรผลรวมด้าน และจำนวนจุดดัด/ขอ
# ความยาวตัดคำนวณใน bar_cut_plan.get_cut_length

import math

import frappe
from frappe import _
from frappe.model.document import Document

DIMENSIONS = ("A", "B", "C", "D")


class BarShape(Document):
	def validate(self):
		dims = self.get_dimensions()
		if not dims or any(dim not in DIMENSIONS for dim in dims):
			frappe.throw(_("ด้านที่ต้องกรอกใช้ได้เฉพาะ A, B, C, D คั่นด้วยจุลภาค"))
		self.dimensions = ",".join(dims)
		# ลองคำนวณสูตรด้วยค่าตัวอย่าง จะได้รู้ตั้งแต่ตอนบันทึกถ้าสูตรผิด
		try:
			self.sum_of_sides(dict.fromkeys(DIMENSIONS, 1000), 12)
		except Exception as e:
			frappe.throw(_("สูตรผลรวมด้านไม่ถูกต้อง: {0}").format(e))

	def get_dimensions(self):
		return [dim.strip().upper() for dim in (self.dimensions or "").split(",") if dim.strip()]

	def sum_of_sides(self, values, diameter):
		return float(frappe.safe_eval(self.sides_formula, None, {**values, "d": diameter, "pi": math.pi}))
