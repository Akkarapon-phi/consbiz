# Copyright (c) 2026, Siricons and contributors
# For license information, please see license.txt

# เงินประกันผลงานที่ถูกหักจาก Purchase Invoice (ระบบสร้างเองตอน Submit Purchase Invoice) logic อยู่ใน consbiz/retention.py

from frappe.model.document import Document

from consbiz import retention


class RetentionPayable(Document):
	def validate(self):
		retention.validate_source(self)

	def on_submit(self):
		self.refresh_amounts()

	def on_update_after_submit(self):
		# แก้วันครบกำหนดคืนหลัง Submit ได้ สถานะ Overdue คิดใหม่
		self.refresh_amounts()

	def before_cancel(self):
		retention.before_cancel_source(self)

	def on_cancel(self):
		self.refresh_amounts()

	def refresh_amounts(self):
		values = retention.update_source(self.doctype, self.name)
		if values:
			self.update(values)
