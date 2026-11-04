# Copyright (c) 2026, Siricons and contributors
# For license information, please see license.txt

# ใบตั้งเบิกจ่ายเงินประกันผลงานคืนผู้รับเหมาช่วง/ผู้ขาย (รวมหลาย Retention Payable / เบิกบางส่วนได้)
# จ่ายเงินผ่าน Journal Entry จากปุ่ม "บันทึกจ่ายเงิน" (consbiz.retention.make_journal_entry) logic อยู่ใน consbiz/retention.py

from frappe.model.document import Document

from consbiz import retention


class RetentionRelease(Document):
	def validate(self):
		retention.validate_claim(self)

	def on_submit(self):
		retention.on_submit_claim(self)

	def before_cancel(self):
		retention.before_cancel_claim(self)

	def on_cancel(self):
		retention.on_cancel_claim(self)
