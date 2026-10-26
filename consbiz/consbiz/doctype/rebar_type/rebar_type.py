# Copyright (c) 2026, Siricons and contributors
# For license information, please see license.txt

import math

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class RebarType(Document):
	def validate(self):
		if flt(self.diameter) <= 0:
			frappe.throw(_("ขนาดเหล็กต้องมากกว่า 0"))
		if not flt(self.unit_weight):
			self.unit_weight = nominal_mass(self.diameter)
		lengths = [
			flt(part) for part in (self.standard_lengths or "").replace(";", ",").split(",") if flt(part) > 0
		]
		if not lengths:
			frappe.throw(_("กรอกความยาวมาตรฐานอย่างน้อย 1 ค่า เช่น 10, 12"))
		self.standard_lengths = ", ".join(f"{length:g}" for length in lengths)


# มวลระบุ (กก./ม.) ตามตารางที่ 1 ของ มอก. 20 (RB) และ มอก. 24 (DB) ตารางปัดเศษเอง สูตรให้ค่าไม่ตรงทุกขนาด
NOMINAL_MASS = {
	6: 0.222,
	8: 0.395,
	9: 0.499,
	10: 0.616,
	12: 0.888,
	15: 1.387,
	16: 1.578,
	19: 2.226,
	20: 2.466,
	22: 2.984,
	25: 3.853,
	28: 4.834,
	32: 6.313,
	34: 7.127,
	36: 7.990,
	40: 9.865,
}


def nominal_mass(diameter):
	"""มวลระบุ (กก./ม.) ขนาดนอกตาราง มอก. ใช้ 0.00785 x พื้นที่หน้าตัด (มม.²)"""
	diameter = flt(diameter)
	return NOMINAL_MASS.get(diameter) or round(0.00785 * math.pi * diameter**2 / 4, 3)
