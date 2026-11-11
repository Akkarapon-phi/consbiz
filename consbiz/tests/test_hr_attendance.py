# Copyright (c) 2026, Siricons and Contributors
# See license.txt

# สรุปวันทำงาน (consbiz/hr_attendance.py): สถานะรายวันจากการลงเวลา + วันหยุดประจำสัปดาห์ แล้วสร้าง Attendance

from datetime import timedelta

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_months, get_first_day, get_last_day, getdate, nowdate

from consbiz import hr_attendance
from consbiz.tests.test_self_service import COMPANY, make_employee, make_project, make_user

EMPLOYEE = "hr-att-emp@example.com"
IDLE = "hr-att-idle@example.com"
OUTSIDER = "hr-att-none@example.com"


def first_full_week(start, end):
	"""วันจันทร์แรกของเดือนที่ทั้งสัปดาห์ (จันทร์-อาทิตย์) อยู่ในเดือน"""
	day = start
	while day.weekday() != 0:
		day += timedelta(days=1)
	assert day + timedelta(days=6) <= end
	return day


class IntegrationTestHrAttendance(IntegrationTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		self.project = make_project("_Test HR Attendance Project")
		self.employee = make_employee(EMPLOYEE, custom_project=self.project, holiday_list="_Test Holiday List")
		# พนักงานที่ไม่ได้ลงเวลาเลยทั้งเดือน (อาจไม่ได้ใช้แอป)
		self.idle = make_employee(IDLE, custom_project=self.project, holiday_list="_Test Holiday List")
		make_user(OUTSIDER)
		# วันหยุดของพนักงาน (Holiday List Assignment ของพนักงานชนะของบริษัท): รายการว่าง ไม่มีวันหยุด
		self.start = getdate(get_first_day(add_months(nowdate(), -1)))
		empty = "_Test ConsBiz No Holidays"
		if not frappe.db.exists("Holiday List", empty):
			frappe.get_doc(
				{
					"doctype": "Holiday List",
					"holiday_list_name": empty,
					"from_date": self.start.replace(month=1, day=1),
					"to_date": self.start.replace(month=12, day=31),
				}
			).insert()
		for employee in (self.employee, self.idle):
			if not frappe.db.exists("Holiday List Assignment", {"assigned_to": employee, "docstatus": 1}):
				frappe.get_doc(
					{
						"doctype": "Holiday List Assignment",
						"applicable_for": "Employee",
						"assigned_to": employee,
						"holiday_list": empty,
						"from_date": self.start.replace(month=1, day=1),
					}
				).submit()
		for doctype in ("Attendance", "Employee Checkin", "Weekly Day Off", "Leave Application"):
			frappe.db.delete(doctype, {"employee": ("in", [self.employee, self.idle])})
		# เดือนที่แล้ว: ทุกวันผ่านไปแล้ว
		self.start = getdate(get_first_day(add_months(nowdate(), -1)))
		self.end = getdate(get_last_day(self.start))
		self.month = str(self.start)[:7]
		self.monday = first_full_week(self.start, self.end)

	def tearDown(self):
		frappe.set_user("Administrator")

	def log(self, day, log_type, time):
		frappe.get_doc(
			{"doctype": "Employee Checkin", "employee": self.employee, "log_type": log_type, "time": f"{day} {time}"}
		).insert()

	def week(self):
		m = self.monday
		# มาก่อน 8 โมง/อยู่เกิน 5 โมงเย็น ไม่นับเพิ่ม: 8 ชม. (หักพักเที่ยง)
		self.log(m, "IN", "07:30:00")
		self.log(m, "OUT", "17:30:00")
		self.log(m + timedelta(1), "IN", "08:00:00")
		self.log(m + timedelta(1), "OUT", "13:00:00")
		self.log(m + timedelta(2), "IN", "08:00:00")
		self.log(m + timedelta(4), "IN", "08:00:00")
		self.log(m + timedelta(4), "OUT", "10:00:00")
		# สัปดาห์ถัดไป: ผ่อนผันถึง 08:05, เกินแล้วนับสายจาก 08:00 (ปัดวินาทีทิ้ง)
		for offset, came in ((7, "08:05:59"), (8, "08:10:00"), (9, "08:06:30")):
			self.log(m + timedelta(offset), "IN", came)
			self.log(m + timedelta(offset), "OUT", "17:00:00")
		frappe.get_doc(
			{"doctype": "Weekly Day Off", "employee": self.employee, "week_start": m, "day_off": "Saturday"}
		).insert()

	def summary(self):
		data = hr_attendance.get_summary_month(self.month, COMPANY, self.project)
		return {row["employee"]: row for row in data["rows"]}

	def test_day_states(self):
		self.week()
		rows = self.summary()
		days = rows[self.employee]["days"]
		m = self.monday
		state = lambda offset: days[str(m + timedelta(offset))]  # noqa: E731
		self.assertEqual(state(0)["s"], "present")
		# 4 ชม. ขึ้นไป = มาทำงาน (ไม่ตัดครึ่งวัน) กลับก่อนนับนาทีจนถึง 17:00 ไม่หักพักเที่ยง
		self.assertEqual((state(0)["hours"], state(0).get("late"), state(0).get("early")), (8, None, None))
		self.assertEqual((state(1)["s"], state(1)["hours"], state(1)["early"]), ("present", 4, 240))
		self.assertEqual([state(o).get("late") for o in (7, 8, 9)], [None, 10, 6])
		self.assertEqual((state(2)["s"], state(2)["suggest"]), ("flag", None))
		self.assertEqual(state(3)["s"], "absent")
		# น้อยกว่า 4 ชม. ต้องพิจารณา
		self.assertEqual((state(4)["s"], state(4)["suggest"], state(4)["hours"]), ("flag", None, 2))
		# ลงหยุดเสาร์ไว้ อาทิตย์ที่ไม่มาจึงเป็นขาดงาน
		self.assertEqual((state(5)["s"], state(6)["s"]), ("day_off", "absent"))
		# สัปดาห์ที่ไม่ได้ลง: อาทิตย์ = วันหยุด เสาร์ = ขาดงาน
		next_sat, next_sun = m + timedelta(12), m + timedelta(13)
		if next_sun <= self.end:
			self.assertEqual(days[str(next_sun)]["s"], "day_off")
			self.assertEqual(days[str(next_sat)]["s"], "absent")
		totals = rows[self.employee]["totals"]
		self.assertEqual((totals["flag"], totals["half"]), (2, 0))
		self.assertEqual(
			(totals["late_count"], totals["late_min"], totals["early_count"], totals["early_min"]), (2, 16, 1, 240)
		)
		# ไม่ลงเวลาเลยทั้งเดือน: วันทำงานรอ HR ตัดสิน (แนะนำมาทำงาน) ไม่ตัดขาดเอง
		idle = [c for c in rows[self.idle]["days"].values() if c["s"] not in ("day_off", "holiday")]
		self.assertTrue(idle and all(c["s"] == "flag" and c["suggest"] == "Present" for c in idle))

	def test_decide_and_close(self):
		self.week()
		frappe.db.set_value("Employee", self.idle, "custom_project", None)
		self.assertRaises(frappe.ValidationError, hr_attendance.close_period, self.month, COMPANY, self.project)

		flagged = [d for d, c in self.summary()[self.employee]["days"].items() if c["s"] == "flag"]
		frappe.local.message_log = []
		hr_attendance.decide_days(self.employee, flagged[:1], "Half Day", "ออกก่อน")
		# ครึ่งวันไม่มีใบลา: ไม่แสดงข้อความ "No leave record found" ของ HRMS
		self.assertFalse([m for m in frappe.local.message_log if "No leave record" in str(m)])
		hr_attendance.decide_days(self.employee, flagged[1:], "Absent")
		half = frappe.get_all(
			"Attendance", filters={"employee": self.employee, "docstatus": 1, "attendance_date": flagged[0]}, fields=["status", "half_day_status"]
		)
		self.assertEqual([(a.status, a.half_day_status) for a in half], [("Half Day", "Absent")])

		auto = sum(c["s"] in ("present", "absent") for c in self.summary()[self.employee]["days"].values())
		result = hr_attendance.close_period(self.month, COMPANY, self.project)
		self.assertEqual(result["created"], auto)
		self.assertEqual(hr_attendance.close_period(self.month, COMPANY, self.project)["created"], 0)
		monday = frappe.db.get_value("Attendance", {"employee": self.employee, "attendance_date": self.monday, "docstatus": 1}, ["status", "working_hours"], as_dict=True)
		self.assertEqual((monday.status, monday.working_hours), ("Present", 8))
		tuesday = frappe.db.get_value(
			"Attendance",
			{"employee": self.employee, "attendance_date": self.monday + timedelta(1), "docstatus": 1},
			["status", "early_exit", "late_entry"],
		)
		self.assertEqual(tuesday, ("Present", 1, 0))
		# รายการลงเวลาผูกกับ Attendance ของวันนั้น
		self.assertTrue(frappe.db.get_value("Employee Checkin", {"employee": self.employee, "time": f"{self.monday} 07:30:00"}, "attendance"))

		# แก้วันที่บันทึกแล้ว = ยกเลิกของเดิม สร้างใหม่
		hr_attendance.decide_days(self.employee, [str(self.monday)], "Half Day", "แก้")
		rows = frappe.get_all("Attendance", filters={"employee": self.employee, "attendance_date": self.monday}, fields=["status", "docstatus"], order_by="creation")
		self.assertEqual([(r.status, r.docstatus) for r in rows], [("Present", 2), ("Half Day", 1)])
		# วันหยุดประจำสัปดาห์บันทึกไม่ได้
		self.assertRaises(frappe.ValidationError, hr_attendance.decide_days, self.employee, [str(self.monday + timedelta(5))], "Present")

	def test_work_hours_inside_shift_without_lunch(self):
		from datetime import datetime

		hours = lambda a, b: hr_attendance.work_hours(datetime(2026, 1, 5, *a), datetime(2026, 1, 5, *b))  # noqa: E731
		self.assertEqual(hours((8, 0), (17, 0)), 8)
		self.assertEqual(hours((6, 0), (20, 0)), 8)
		self.assertEqual(hours((8, 0), (12, 0)), 4)
		self.assertEqual(hours((8, 0), (13, 0)), 4)
		self.assertEqual(hours((13, 0), (17, 0)), 4)
		self.assertEqual(hours((12, 30), (17, 0)), 4)
		self.assertEqual(hours((8, 15), (17, 0)), 7.75)
		self.assertEqual(hours((17, 30), (19, 0)), 0)

	def test_unpaid_time(self):
		from unittest.mock import patch

		self.week()
		component = "_Test Unpaid Time"
		if not frappe.db.exists("Salary Component", component):
			frappe.get_doc({"doctype": "Salary Component", "salary_component": component, "type": "Deduction"}).insert()
		previous = frappe.db.get_value("Company", COMPANY, "custom_unpaid_time_component")
		frappe.db.set_value("Company", COMPANY, "custom_unpaid_time_component", None)
		with (
			patch("consbiz.self_advance.base_salary", return_value=28800),
			patch(
				"hrms.payroll.doctype.additional_salary.additional_salary.AdditionalSalary.validate_salary_structure"
			),
		):
			info = hr_attendance.get_person(self.employee, self.month)
			# 28800 / 30 / 8 / 60 = 2 บาทต่อนาที, สาย 16 + กลับก่อน 240 นาที
			self.assertEqual((info.minutes, info.per_minute, info.amount), (256, 2, 512))
			self.assertRaises(frappe.ValidationError, hr_attendance.set_unpaid_time, self.employee, self.month)
			frappe.db.set_value("Company", COMPANY, "custom_unpaid_time_component", component)
			name = hr_attendance.set_unpaid_time(self.employee, self.month, "สายบ่อย")["name"]
			doc = frappe.get_doc("Additional Salary", name)
			self.assertEqual((doc.amount, doc.docstatus, str(doc.payroll_date)), (512, 1, str(self.end)))
			self.assertRaises(frappe.ValidationError, hr_attendance.set_unpaid_time, self.employee, self.month)
			self.assertEqual(hr_attendance.get_person(self.employee, self.month).existing.name, name)
			hr_attendance.cancel_unpaid_time(self.employee, self.month)
			self.assertIsNone(hr_attendance.get_person(self.employee, self.month).existing)
		frappe.db.set_value("Company", COMPANY, "custom_unpaid_time_component", previous)

	def test_only_hr(self):
		frappe.set_user(OUTSIDER)
		self.assertEqual(hr_attendance.hr_sections(), [])
		self.assertRaises(frappe.PermissionError, hr_attendance.get_summary_month, self.month, COMPANY)
		self.assertRaises(frappe.PermissionError, hr_attendance.decide_days, self.employee, [str(self.monday)], "Present")
		frappe.set_user("Administrator")
		self.assertEqual(hr_attendance.hr_sections(), ["hr"])

	def test_waive_deduction_then_charge(self):
		self.week()
		thursday, friday = str(self.monday + timedelta(3)), str(self.monday + timedelta(4))
		self.assertEqual(self.summary()[self.employee]["days"][thursday]["s"], "absent")
		# ติ๊กไม่หักเงิน: ขาด / ครึ่งวัน บันทึกเป็นมาทำงาน สถานะจริงเก็บแยก
		hr_attendance.decide_days(self.employee, [thursday], "Absent", "ตักเตือนครั้งแรก", waive=1)
		hr_attendance.decide_days(self.employee, [friday], "Half Day", waive=1)
		get = lambda d: frappe.db.get_value(  # noqa: E731
			"Attendance", {"employee": self.employee, "attendance_date": d, "docstatus": 1}, ["status", "custom_waived_status"]
		)
		self.assertEqual((get(thursday), get(friday)), (("Present", "Absent"), ("Present", "Half Day")))
		row = self.summary()[self.employee]
		self.assertEqual((row["days"][thursday]["status"], row["days"][thursday].get("waived")), ("Absent", 1))
		self.assertEqual(row["totals"]["waived"], 2)
		# ติ๊กซ้ำไม่สร้างใหม่ / เอาติ๊กออก = หักเงินวันนั้น
		self.assertEqual(hr_attendance.decide_days(self.employee, [thursday], "Absent", waive=1)["done"], [])
		# ขาดบ่อย: หักเงินจริงทั้งเดือน = สถานะจริง
		hr_attendance.charge_waived(self.employee, self.month)
		self.assertEqual((get(thursday), get(friday)), (("Absent", ""), ("Half Day", "")))
		self.assertRaises(frappe.ValidationError, hr_attendance.charge_waived, self.employee, self.month)
