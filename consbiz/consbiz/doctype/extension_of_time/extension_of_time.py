# Copyright (c) 2026, Siricons and contributors
# For license information, please see license.txt

# ขยายระยะเวลาก่อสร้าง (Extension of Time) ของแผนงาน Construction Management
# - Submit = ยื่นขอ วันสิ้นสุดสัญญาเลื่อนเมื่อ employer_status = Approved ตามจำนวนวันที่อนุมัติ (วันปฏิทิน)
# - ไม่เลื่อนวันของงานในแผน ถ้าต้องปรับแผนให้ปรับในหน้า Gantt แล้วบันทึก Baseline ชุดใหม่
# - ต้องแจ้งภายใน NOTICE_DAYS วันนับแต่เหตุสิ้นสุด (ระเบียบกระทรวงการคลังฯ 2560 ข้อ 182) ระบบแค่เตือน ไม่บังคับ
# การเลื่อนวันสิ้นสุดอยู่ใน Construction Management.apply_extensions (รวมจาก EOT ที่อนุมัติแล้วทุกฉบับ)

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, cint, getdate, nowdate

from consbiz.consbiz.doctype.construction_management.construction_management import (
	VARIATION_ORDER,
	get_extension_days,
)

NOTICE_DAYS = 15


class ExtensionofTime(Document):
	def validate(self):
		self.validate_event()
		self.set_requested_days()
		self.set_approval()
		self.set_finish_dates()

	def before_update_after_submit(self):
		self.set_approval()
		self.set_finish_dates()

	def on_submit(self):
		update_plan(self.construction_management)

	def on_update_after_submit(self):
		update_plan(self.construction_management)

	def on_cancel(self):
		update_plan(self.construction_management)

	def validate_event(self):
		if self.event_end and getdate(self.event_end) < getdate(self.event_start):
			frappe.throw(_("วันที่เหตุสิ้นสุดต้องไม่ก่อนวันที่เริ่มเกิดเหตุ"))
		self.notice_deadline = add_days(self.event_end, NOTICE_DAYS) if self.event_end else None
		if self.cause != "Variation Order":
			self.variation_order = None
		elif self.variation_order:
			plan, docstatus = frappe.db.get_value(
				VARIATION_ORDER, self.variation_order, ["construction_management", "docstatus"]
			)
			if plan != self.construction_management or docstatus != 1:
				frappe.throw(
					_("Variation Order {0} ต้อง Submit แล้วและเป็นของแผนงาน {1}").format(
						self.variation_order, self.construction_management
					)
				)

	def set_requested_days(self):
		if not cint(self.requested_days) and self.variation_order:
			self.requested_days = cint(
				frappe.db.get_value(VARIATION_ORDER, self.variation_order, "extension_days")
			)
		if cint(self.requested_days) <= 0:
			frappe.throw(_("กรอกจำนวนวันที่ขอขยาย"))

	def set_approval(self):
		if self.employer_status == "Pending":
			self.employer_approved_on = None
			self.approved_days = 0
		else:
			if not self.employer_approved_on:
				self.employer_approved_on = nowdate()
			if self.employer_status == "Rejected":
				self.approved_days = 0
			elif not cint(self.approved_days):
				self.approved_days = self.requested_days
		if cint(self.approved_days) < 0:
			frappe.throw(_("จำนวนวันที่อนุมัติต้องไม่ติดลบ"))

	def set_finish_dates(self):
		self.contract_finish_date = frappe.db.get_value(
			"Construction Management", self.construction_management, "finish_date"
		)
		# ฉบับอื่นที่ผู้ว่าจ้างอนุมัติแล้ว (ตรงกับ extension_days ของแผนงาน)
		self.previous_extension_days = get_extension_days(self.construction_management, exclude=self.name)
		days = self.previous_extension_days + (
			cint(self.approved_days) if self.employer_status == "Approved" else 0
		)
		self.revised_finish_date = (
			add_days(self.contract_finish_date, days) if self.contract_finish_date else None
		)


def update_plan(construction_management):
	"""คำนวณวันสิ้นสุดสัญญาปรับปรุงของแผนงานใหม่จาก EOT ที่อนุมัติแล้วทุกฉบับ"""
	plan = frappe.get_doc("Construction Management", construction_management)
	plan.flags.ignore_permissions = True
	plan.save()

