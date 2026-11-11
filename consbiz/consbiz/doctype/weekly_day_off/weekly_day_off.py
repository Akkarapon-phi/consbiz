# Copyright (c) 2026, Siricons and contributors
# For license information, please see license.txt

"""วันหยุดประจำสัปดาห์: บริษัทให้หยุด 1 วันต่อสัปดาห์ เลือกเสาร์หรืออาทิตย์ (ตกลง 2026-11-11)

- 1 เอกสารต่อพนักงานต่อสัปดาห์ (ชื่อ = WDO-<พนักงาน>-<วันจันทร์>) สัปดาห์เริ่มวันจันทร์
- โควตาต่อโครงการที่ประจำ: เสาร์ = ceil(ทีม x Project.custom_day_off_saturday_percent%), อาทิตย์ = ceil(ทีม x ส่วนที่เหลือ)
  ปัดขึ้นทั้งสองวัน ทุกคนจึงได้ที่เสมอ ทีม = พนักงาน Active ที่ Employee.custom_project = โครงการนั้น
- พนักงานลง/เปลี่ยนผ่านแอปได้ถึงวันหยุดนั้น ใครลงก่อนได้ก่อน (self_service.book_day_off ตรวจโควตา ล็อกแถว Project กันแย่งพร้อมกัน)
- HR แก้ในระบบได้ทุกเวลา (รวมย้อนหลัง) เกินโควตาแค่เตือน
"""

import math

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, cint, getdate

HR_ROLES = ("HR User", "HR Manager", "System Manager")
DAY_OFFSET = {"Saturday": 5, "Sunday": 6}
DAY_LABEL = {"Saturday": "เสาร์", "Sunday": "อาทิตย์"}
DEFAULT_SATURDAY_PERCENT = 50


def week_start_of(date):
	date = getdate(date)
	return add_days(date, -date.weekday())


def off_date_of(week_start, day_off):
	return getdate(add_days(week_start, DAY_OFFSET[day_off]))


def team_size(project):
	return frappe.db.count("Employee", {"custom_project": project, "status": "Active"}) if project else 0


def capacity(project):
	"""{Saturday: n, Sunday: n} ไม่มีโครงการ = ไม่จำกัด (None)"""
	if not project:
		return {"Saturday": None, "Sunday": None}
	size = team_size(project)
	percent = frappe.db.get_value("Project", project, "custom_day_off_saturday_percent")
	percent = DEFAULT_SATURDAY_PERCENT if percent is None else min(100, max(0, cint(percent)))
	return {
		"Saturday": math.ceil(size * percent / 100),
		"Sunday": math.ceil(size * (100 - percent) / 100),
	}


def booked(project, week_start, exclude_employee=None):
	"""จำนวนที่ลงแล้วของสัปดาห์ {Saturday: n, Sunday: n}"""
	counts = {"Saturday": 0, "Sunday": 0}
	if not project:
		return counts
	filters = {"project": project, "week_start": week_start}
	if exclude_employee:
		filters["employee"] = ("!=", exclude_employee)
	for row in frappe.get_all(
		"Weekly Day Off", filters=filters, fields=["day_off", {"COUNT": "name", "as": "n"}], group_by="day_off"
	):
		counts[row.day_off] = row.n
	return counts


def is_hr():
	return bool(set(frappe.get_roles()) & set(HR_ROLES))


class WeeklyDayOff(Document):
	def autoname(self):
		self.week_start = week_start_of(self.week_start)
		self.name = f"WDO-{self.employee}-{self.week_start}"

	def validate(self):
		# ลงผ่านแอป (self_service) หรือ HR / Administrator เท่านั้น
		if not (self.flags.from_self_service or frappe.session.user == "Administrator" or is_hr()):
			frappe.throw(_("ลงวันหยุดผ่านแอป ConsERP (Self Service) เท่านั้น"), frappe.PermissionError)
		self.week_start = week_start_of(self.week_start)
		if not self.is_new() and self.has_value_changed("week_start"):
			frappe.throw(_("เปลี่ยนสัปดาห์ไม่ได้ ลบแล้วลงสัปดาห์ใหม่"))
		if not self.is_new() and self.has_value_changed("employee"):
			frappe.throw(_("เปลี่ยนพนักงานไม่ได้"))
		if self.day_off not in DAY_OFFSET:
			frappe.throw(_("วันหยุดต้องเป็นเสาร์หรืออาทิตย์"))
		self.off_date = off_date_of(self.week_start, self.day_off)
		if not self.project and self.is_new():
			self.project = frappe.db.get_value("Employee", self.employee, "custom_project")
		if not self.flags.from_self_service:
			self.warn_over_quota()

	def over_quota(self):
		limit = capacity(self.project)[self.day_off]
		if limit is None:
			return False
		return booked(self.project, self.week_start, self.employee)[self.day_off] >= limit

	def warn_over_quota(self):
		if self.project and self.over_quota():
			frappe.msgprint(
				_("วัน{0}ของสัปดาห์นี้ในโครงการ {1} เกินโควตาแล้ว").format(DAY_LABEL[self.day_off], self.project),
				indicator="orange",
				alert=True,
			)

	def on_trash(self):
		if not (self.flags.from_self_service or frappe.session.user == "Administrator" or is_hr()):
			frappe.throw(_("ลบวันหยุดผ่านแอป ConsERP (Self Service) เท่านั้น"), frappe.PermissionError)
