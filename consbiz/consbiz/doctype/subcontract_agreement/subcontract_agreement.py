# Copyright (c) 2026, Siricons and contributors
# For license information, please see license.txt

"""สัญญาจ้างเหมาช่วง: กฎและการคำนวณอยู่ใน consbiz/subcontract.py"""

from frappe.model.document import Document

from consbiz import subcontract


class SubcontractAgreement(Document):
	def before_insert(self):
		subcontract.set_company(self)

	def validate(self):
		subcontract.validate_agreement(self)

	def on_submit(self):
		subcontract.on_submit_agreement(self)

	def before_cancel(self):
		subcontract.before_cancel_agreement(self)

	def on_cancel(self):
		self.db_set("status", "Cancelled")
