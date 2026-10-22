# Copyright (c) 2026, Siricons and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class RebarType(Document):
	def validate(self):
		if flt(self.diameter) <= 0:
			frappe.throw(_("ขนาดเหล็กต้องมากกว่า 0"))
		# น้ำหนักเหล็กต่อเมตร = 0.00617 x d² (กก./ม.)
		if not flt(self.unit_weight):
			self.unit_weight = round(0.00617 * flt(self.diameter) ** 2, 3)
		lengths = [
			flt(part) for part in (self.standard_lengths or "").replace(";", ",").split(",") if flt(part) > 0
		]
		if not lengths:
			frappe.throw(_("กรอกความยาวมาตรฐานอย่างน้อย 1 ค่า เช่น 10, 12"))
		self.standard_lengths = ", ".join(f"{length:g}" for length in lengths)
