# Copyright (c) 2026, Siricons and contributors
# For license information, please see license.txt

# รายการงานที่ต้องแก้ไข (Punch List) ก่อนส่งมอบ
# - Submit = ออกรายการให้แก้ ปิดแต่ละรายการ (status / closed_on / รูปหลังแก้) ได้หลัง Submit
# - สถานะเอกสาร = Closed เมื่อทุกรายการปิดแล้ว

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import nowdate

from consbiz.consbiz.doctype.daily_report.daily_report import get_leaf_tasks


class PunchList(Document):
	def validate(self):
		tasks = get_leaf_tasks(self.construction_management)
		for row in self.items:
			if (row.wbs or "").strip() and row.wbs.strip() not in tasks:
				frappe.throw(_("แถว {0}: ไม่พบงานย่อย WBS {1}").format(row.idx, row.wbs))
		self.set_status()

	def before_update_after_submit(self):
		self.set_status()

	def set_status(self):
		for row in self.items:
			if row.status == "Closed":
				row.closed_on = row.closed_on or nowdate()
			else:
				row.closed_on = None
		self.open_items = sum(1 for row in self.items if row.status != "Closed")
		self.status = "Open" if self.open_items else "Closed"
