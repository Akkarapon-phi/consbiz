# Copyright (c) 2026, Siricons and contributors
# For license information, please see license.txt

# รูปแบบการดัดเหล็ก: ด้านที่ต้องกรอก, สูตรผลรวมด้าน และจำนวนจุดดัด/ขอ
# - ด้าน A-F และ R (รัศมี) เป็น มม., N = จำนวนรอบ (ปลอกเกลียว), T = มุม (องศา)
# - สูตรใช้ sqrt() และ sin() cos() tan() ที่รับมุมเป็นองศาได้ เช่น คอม้า A+B/sin(T)+C
# ความยาวตัดคำนวณใน bar_cut_plan.get_cut_length

import math

import frappe
from frappe import _
from frappe.model.document import Document

DIMENSIONS = ("A", "B", "C", "D", "E", "F", "R", "N", "T")
# ค่าตัวอย่างสำหรับตรวจสูตรตอนบันทึก
SAMPLE_VALUES = {**dict.fromkeys(DIMENSIONS, 1000), "N": 2, "T": 45}
FUNCTIONS = {
	"pi": math.pi,
	"sqrt": math.sqrt,
	"sin": lambda deg: math.sin(math.radians(deg)),
	"cos": lambda deg: math.cos(math.radians(deg)),
	"tan": lambda deg: math.tan(math.radians(deg)),
}


class BarShape(Document):
	def validate(self):
		dims = self.get_dimensions()
		if not dims or any(dim not in DIMENSIONS for dim in dims):
			frappe.throw(_("ด้านที่ต้องกรอกใช้ได้เฉพาะ {0} คั่นด้วยจุลภาค").format(", ".join(DIMENSIONS)))
		self.dimensions = ",".join(dims)
		# ลองคำนวณสูตรด้วยค่าตัวอย่าง จะได้รู้ตั้งแต่ตอนบันทึกถ้าสูตรผิด
		try:
			self.sum_of_sides(SAMPLE_VALUES, 12)
		except Exception as e:
			frappe.throw(_("สูตรผลรวมด้านไม่ถูกต้อง: {0}").format(e))

	def get_dimensions(self):
		return [dim.strip().upper() for dim in (self.dimensions or "").split(",") if dim.strip()]

	def sum_of_sides(self, values, diameter):
		return float(frappe.safe_eval(self.sides_formula, None, {**FUNCTIONS, **values, "d": diameter}))
