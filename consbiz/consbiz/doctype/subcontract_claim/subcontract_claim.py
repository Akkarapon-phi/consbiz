# Copyright (c) 2026, Siricons and contributors
# For license information, please see license.txt

"""ใบเบิกงวด ผรม.: Submit = อนุมัติ กฎและการคำนวณอยู่ใน consbiz/subcontract.py"""

from frappe.model.document import Document

from consbiz import subcontract


class SubcontractClaim(Document):
	def before_insert(self):
		subcontract.before_insert_claim(self)

	def validate(self):
		subcontract.validate_claim(self)

	def before_submit(self):
		subcontract.before_submit_claim(self)

	def on_submit(self):
		subcontract.on_submit_claim(self)

	def before_cancel(self):
		subcontract.before_cancel_claim(self)

	def on_cancel(self):
		subcontract.on_cancel_claim(self)
