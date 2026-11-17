# Copyright (c) 2026, Siricons and contributors
# For license information, please see license.txt

"""ใบงานเพิ่ม ผรม.: Submit = อนุมัติ (เพิ่มปริมาณ/รายการในสัญญา + อัปเดต PO เดิม) กฎอยู่ใน consbiz/subcontract_variation.py"""

from frappe.model.document import Document

from consbiz import subcontract_variation


class SubcontractVariation(Document):
	def before_insert(self):
		subcontract_variation.before_insert(self)

	def validate(self):
		subcontract_variation.validate(self)

	def on_submit(self):
		subcontract_variation.on_submit(self)

	def before_cancel(self):
		subcontract_variation.before_cancel(self)

	def on_cancel(self):
		subcontract_variation.on_cancel(self)
