# Copyright (c) 2026, Siricons and contributors
# For license information, please see license.txt

# อัตราเงินสมทบประกันสังคม ใช้ผ่าน consbiz.social_security (rate_on / contribution)

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate


class SocialSecurityRate(Document):
	def validate(self):
		if self.to_date and getdate(self.to_date) < getdate(self.from_date):
			frappe.throw(_("วันที่สิ้นสุดต้องไม่ก่อนวันที่เริ่ม"))
		if flt(self.min_base) > flt(self.max_base):
			frappe.throw(_("ฐานค่าจ้างต่ำสุดต้องไม่เกินเพดาน"))
		duplicate = frappe.db.exists(
			"Social Security Rate",
			{"from_date": self.from_date, "to_date": self.to_date, "name": ("!=", self.name)},
		)
		if duplicate:
			frappe.throw(_("มีอัตราของช่วงเดียวกันแล้ว ({0})").format(duplicate))
