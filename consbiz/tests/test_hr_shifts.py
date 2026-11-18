# Copyright (c) 2026, Siricons and Contributors
# See license.txt

# กะ (consbiz/hr_shifts.py + hr_attendance.shift_of): ประเภทกะ, กำหนดกะเป็นช่วง (แทนที่ของเดิม), สาย/ชั่วโมงตามกะ

from datetime import datetime

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, getdate, nowdate

from consbiz import hr_attendance, hr_shifts
from consbiz.tests.test_self_service import make_employee

SHIFT = "_Test กะเช้า 7-16"


class IntegrationTestHrShifts(IntegrationTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		self.employee = make_employee("shift-emp@example.com")
		for name in frappe.get_all("Shift Assignment", filters={"employee": self.employee}, pluck="name"):
			frappe.db.delete("Shift Assignment", name)
		if not frappe.db.exists("Shift Type", SHIFT):
			hr_shifts.save_shift_type(
				{"name": SHIFT, "start": "07:00", "end": "16:00", "break_start": "11:30", "break_end": "12:30", "grace": 10}
			)

	def test_shift_math(self):
		shift = hr_attendance.shift_type(SHIFT)
		self.assertEqual(shift.hours, 8)
		self.assertEqual(hr_attendance.late_minutes(datetime(2026, 1, 5, 7, 10), shift), 0)
		self.assertEqual(hr_attendance.late_minutes(datetime(2026, 1, 5, 7, 15), shift), 15)
		self.assertEqual(hr_attendance.work_hours(datetime(2026, 1, 5, 7), datetime(2026, 1, 5, 16), shift), 8)
		# ไม่มีกะ = 08:00-17:00 พักเที่ยง ผ่อนผัน 5 นาที (ค่าเดิม)
		self.assertEqual(hr_attendance.late_minutes(datetime(2026, 1, 5, 8, 10)), 10)
		self.assertEqual(hr_attendance.work_hours(datetime(2026, 1, 5, 8), datetime(2026, 1, 5, 17)), 8)

	def test_invalid_shift_types(self):
		for bad in (
			{"name": "_Test ข้ามคืน", "start": "22:00", "end": "06:00"},
			{"name": "_Test พักนอกกะ", "start": "08:00", "end": "17:00", "break_start": "18:00", "break_end": "19:00"},
		):
			with self.assertRaises(frappe.ValidationError):
				hr_shifts.save_shift_type(bad)

	def test_assign_replaces_range(self):
		start = getdate(nowdate())
		hr_shifts.assign_shift([self.employee], start, None, SHIFT)
		# ล้างกะวันที่ 3-4 = กะเดิมตัดเหลือ 1-2 แล้วต่อใหม่ตั้งแต่วันที่ 5
		hr_shifts.assign_shift([self.employee], add_days(start, 2), add_days(start, 3), None)
		rows = frappe.get_all(
			"Shift Assignment",
			filters={"employee": self.employee, "docstatus": 1, "status": "Active"},
			fields=["start_date", "end_date"],
			order_by="start_date asc",
		)
		self.assertEqual([(getdate(r.start_date), r.end_date and getdate(r.end_date)) for r in rows], [(start, add_days(start, 1)), (add_days(start, 4), None)])
		data = {"assignments": hr_attendance.group_by_employee(frappe.get_all("Shift Assignment", filters={"employee": self.employee, "docstatus": 1, "status": "Active"}, fields=["employee", "shift_type", "start_date", "end_date"]))}
		emp = frappe._dict(name=self.employee, default_shift=None)
		self.assertEqual(hr_attendance.shift_of(data, emp, start).name, SHIFT)
		self.assertIsNone(hr_attendance.shift_of(data, emp, add_days(start, 2)).name)
