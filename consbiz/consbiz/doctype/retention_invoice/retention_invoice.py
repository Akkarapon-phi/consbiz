# Copyright (c) 2026, Siricons and contributors
# For license information, please see license.txt

# ใบวางบิลเรียกเงินประกันผลงานคืนจากผู้ว่าจ้าง (รวมหลาย Retention Receivable / เบิกบางส่วนได้)
# รับเงินผ่าน Journal Entry จากปุ่ม "บันทึกรับเงิน" (consbiz.retention.make_journal_entry) logic อยู่ใน consbiz/retention.py

import frappe
from frappe.model.document import Document

from consbiz import retention


class RetentionInvoice(Document):
	def validate(self):
		retention.validate_claim(self)
		if not self.bank or not self.bank_account_no:
			self.set_company_bank()

	def set_company_bank(self):
		bank = frappe.db.get_value(
			"Bank Account",
			{"company": self.company, "is_company_account": 1, "is_default": 1, "disabled": 0},
			["bank", "bank_account_no"],
			as_dict=True,
		)
		if bank:
			self.bank = bank.bank
			self.bank_account_no = bank.bank_account_no

	def on_submit(self):
		retention.on_submit_claim(self)

	def before_cancel(self):
		retention.before_cancel_claim(self)

	def on_cancel(self):
		retention.on_cancel_claim(self)
