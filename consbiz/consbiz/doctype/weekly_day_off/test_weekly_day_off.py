# Copyright (c) 2026, Siricons and contributors
# For license information, please see license.txt

# วันหยุดประจำสัปดาห์: เลือกเสาร์/อาทิตย์ ใครลงก่อนได้ก่อนตามโควตาของโครงการ (self_service.book_day_off)

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, getdate, nowdate

from consbiz import self_service
from consbiz.consbiz.doctype.weekly_day_off.weekly_day_off import capacity, week_start_of
from consbiz.tests.test_self_service import COMPANY, make_employee

IGNORE_TEST_RECORD_DEPENDENCIES = ["Employee", "Project", "Company", "User"]

USERS = [f"day-off-{c}@example.com" for c in "abcd"]


class IntegrationTestWeeklyDayOff(IntegrationTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		self.project = frappe.db.get_value("Project", {"project_name": "_Test Day Off Project"}) or (
			frappe.get_doc(
				{
					"doctype": "Project",
					"project_name": "_Test Day Off Project",
					"company": COMPANY,
					"custom_warehouse_name": "_Test Day Off WH",
				}
			)
			.insert(ignore_permissions=True)
			.name
		)
		frappe.db.set_value("Project", self.project, "custom_day_off_saturday_percent", 50)
		self.employees = [make_employee(user, custom_project=self.project) for user in USERS]
		frappe.db.delete("Weekly Day Off", {"employee": ("in", self.employees)})
		# สัปดาห์หน้า: ทุกวันยังไม่ผ่าน
		self.week = str(add_days(week_start_of(nowdate()), 7))

	def tearDown(self):
		frappe.set_user("Administrator")

	def book(self, index, day):
		frappe.set_user(USERS[index])
		try:
			return self_service.book_day_off(self.week, day)
		finally:
			frappe.set_user("Administrator")

	def test_capacity_rounds_up_both_days(self):
		self.assertEqual(capacity(self.project), {"Saturday": 2, "Sunday": 2})
		frappe.db.set_value("Project", self.project, "custom_day_off_saturday_percent", 30)
		self.assertEqual(capacity(self.project), {"Saturday": 2, "Sunday": 3})
		self.assertEqual(capacity(None), {"Saturday": None, "Sunday": None})

	def test_first_come_first_served(self):
		self.book(0, "Saturday")
		result = self.book(1, "Saturday")
		self.assertEqual(result["mine"], "Saturday")
		self.assertRaises(frappe.ValidationError, self.book, 2, "Saturday")
		self.assertEqual(self.book(2, "Sunday")["mine"], "Sunday")
		# เปลี่ยนวัน = แถวเดิม ไม่ซ้ำ แล้วที่ว่างคืนให้คนอื่น
		self.book(0, "Sunday")
		self.assertEqual(frappe.db.count("Weekly Day Off", {"employee": self.employees[0]}), 1)
		self.assertEqual(self.book(3, "Saturday")["mine"], "Saturday")
		doc = frappe.get_doc("Weekly Day Off", {"employee": self.employees[0], "week_start": self.week})
		self.assertEqual(getdate(doc.off_date), getdate(add_days(self.week, 6)))
		self.assertEqual(doc.project, self.project)

	def test_cancel_frees_slot(self):
		self.book(0, "Saturday")
		self.book(1, "Saturday")
		self.assertIsNone(self.book(0, None)["mine"])
		self.assertFalse(frappe.db.exists("Weekly Day Off", {"employee": self.employees[0]}))
		self.assertEqual(self.book(2, "Saturday")["mine"], "Saturday")

	def test_week_range(self):
		last_week = str(add_days(week_start_of(nowdate()), -7))
		frappe.set_user(USERS[0])
		self.assertRaises(frappe.ValidationError, self_service.book_day_off, last_week, "Saturday")
		far = str(add_days(week_start_of(nowdate()), 7 * self_service.DAY_OFF_WEEKS))
		self.assertRaises(frappe.ValidationError, self_service.book_day_off, far, "Saturday")
		data = self_service.get_day_off()
		self.assertEqual(len(data["weeks"]), self_service.DAY_OFF_WEEKS)
		self.assertEqual(data["team_size"], 4)

	def test_only_app_or_hr_can_write(self):
		row = {"doctype": "Weekly Day Off", "employee": self.employees[0], "week_start": self.week, "day_off": "Sunday"}
		frappe.set_user(USERS[0])
		self.assertRaises(frappe.PermissionError, frappe.get_doc(row).insert, ignore_permissions=True)
		frappe.set_user("Administrator")
		# HR เกินโควตาได้ (แค่เตือน)
		self.book(1, "Sunday")
		self.book(2, "Sunday")
		self.assertTrue(frappe.get_doc(row).insert().name)

	def test_team_schedule(self):
		self.book(0, "Saturday")
		self.book(1, "Sunday")
		frappe.set_user(USERS[0])
		team = self_service.get_team_day_off(add_days(self.week, 3))
		self.assertEqual([p.name for p in team["Saturday"]], [self.employees[0]])
		self.assertTrue(team["Saturday"][0].me)
		self.assertEqual([p.name for p in team["Sunday"]], [self.employees[1]])
		self.assertEqual({p.name for p in team["none"]}, set(self.employees[2:]))
