# Copyright (c) 2026, Siricons and contributors
# For license information, please see license.txt

# ทะเบียนคนงานรายวัน ค่าแรงเก็บเป็นประวัติ (rates) ใบลงเวลาคิดตามอัตราของแต่ละวัน (rate_on)

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate, nowdate


class DailyWorker(Document):
	def validate(self):
		if self.payee_type != "Subcontractor":
			self.supplier = None
		else:
			# คนงานของ ผรม. ประกันสังคมเป็นของ ผรม.
			self.sso_registered = 0
		if not self.ot_flat:
			self.ot_hourly_rate = 0
		self.bank_account = "".join(ch for ch in (self.bank_account or "") if ch.isdigit()) or None
		if self.bank_account and not 10 <= len(self.bank_account) <= 15:
			frappe.throw(_("เลขที่บัญชีต้องเป็นตัวเลข 10-15 หลัก"))
		if self.bank_account and not self.bank_name:
			frappe.throw(_("ระบุธนาคารของเลขที่บัญชี"))
		if not self.account_holder_other:
			self.account_holder = None
			self.account_holder_relation = None
		elif not (self.account_holder or "").strip():
			frappe.throw(_("รับเงินผ่านบัญชีผู้อื่น: ระบุชื่อเจ้าของบัญชี"))
		if self.project:
			company = frappe.db.get_value("Project", self.project, "company")
			if company and company != self.company:
				frappe.throw(_("โครงการ {0} ไม่ได้อยู่ในบริษัท {1}").format(self.project, self.company))
		seen = set()
		for row in self.rates:
			if row.from_date in seen:
				frappe.throw(_("ประวัติค่าแรงมีวันที่ {0} ซ้ำ").format(row.from_date))
			seen.add(row.from_date)
			if flt(row.daily_rate) <= 0:
				frappe.throw(_("ค่าแรง/วัน ต้องมากกว่า 0"))
		self.rates.sort(key=lambda row: getdate(row.from_date))
		for index, row in enumerate(self.rates, 1):
			row.idx = index
		self.daily_rate = self.rate_on(nowdate())

	def rate_on(self, day):
		return rate_on(self.rates, day)


def rate_on(rates, day):
	"""ค่าแรงของวัน day = แถวล่าสุดที่เริ่มไม่เกินวันนั้น
	วันก่อนแถวแรก (ลงเวลาย้อนหลังก่อนบันทึกค่าแรง) ใช้แถวแรก"""
	rows = sorted(rates, key=lambda row: getdate(row.from_date))
	if not rows:
		return 0.0
	day = getdate(day)
	current = rows[0]
	for row in rows:
		if getdate(row.from_date) <= day:
			current = row
	return flt(current.daily_rate)
