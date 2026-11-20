# Copyright (c) 2026, Siricons and Contributors
# See license.txt

# Self Service (consbiz/self_home.py): หน้าแรก, แจ้งมาทำงาน (Attendance Request) + อนุมัติ, เงินเดือนสะสม

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, getdate, nowdate

from consbiz import approvals, hr_attendance, self_home
from consbiz.tests.test_self_service import COMPANY, make_employee, set_roles

EMPLOYEE = "home-emp@example.com"
APPROVER = "home-approver@example.com"


class IntegrationTestSelfHome(IntegrationTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		self.employee = make_employee(EMPLOYEE, custom_project=None)
		self.approver_employee = make_employee(APPROVER, custom_project=None)
		set_roles(APPROVER, "Employee", "Leave Approver")
		for doctype in ("Attendance", "Attendance Request"):
			for name in frappe.get_all(doctype, filters={"employee": self.employee}, pluck="name"):
				frappe.db.delete(doctype, name)

	def tearDown(self):
		frappe.set_user("Administrator")

	def as_user(self, user, fn, *args, **kwargs):
		frappe.set_user(user)
		try:
			return fn(*args, **kwargs)
		finally:
			frappe.set_user("Administrator")

	def request(self, day=None, **kwargs):
		day = day or add_days(nowdate(), -1)
		return self.as_user(EMPLOYEE, self_home.request_attendance, day, day, kwargs.pop("reason", "On Duty"), "ไปไซต์", **kwargs)

	def test_home_payload(self):
		data = self.as_user(EMPLOYEE, self_home.get_home)
		for key in ("calendar", "year", "pending", "suggestions", "first_name"):
			self.assertIn(key, data)
		self.assertEqual(data["calendar"]["month"], nowdate()[:7])

	def test_request_rules(self):
		with self.assertRaises(frappe.ValidationError):
			self.request(add_days(nowdate(), 1))
		with self.assertRaises(frappe.ValidationError):
			self.request(add_days(nowdate(), -(self_home.ATTENDANCE_REQUEST_DAYS + 1)))
		with self.assertRaises(frappe.ValidationError):
			self.as_user(EMPLOYEE, self_home.request_attendance, nowdate(), nowdate(), "On Duty", "")

	def test_pending_request_flags_day(self):
		day = add_days(nowdate(), -1)
		name = self.request(day)["name"]
		pending = self.as_user(EMPLOYEE, self_home.get_home)["pending"]
		self.assertIn(name, [p["name"] for p in pending if p["kind"] == "attendance"])
		_start, _end, rows = hr_attendance.build(COMPANY, str(day)[:7], employee=self.employee)
		cell = rows[0]["days"][str(getdate(day))]
		if cell["s"] not in ("holiday", "day_off"):
			self.assertEqual(cell["s"], "flag")

	def test_approve_creates_attendance(self):
		day = add_days(nowdate(), -1)
		name = self.request(day)["name"]
		inbox = self.as_user(APPROVER, approvals.get_inbox)
		self.assertIn(name, [r.name for r in inbox["attendance"]])
		self.assertEqual(self.as_user(APPROVER, self_home.review_attendance_request, name, 1), "Approved")
		self.assertEqual(frappe.db.get_value("Attendance Request", name, "docstatus"), 1)
		status = frappe.db.get_value("Attendance", {"attendance_request": name, "docstatus": 1}, "status")
		# วันหยุดตาม Holiday List: HRMS ไม่สร้าง Attendance
		if status:
			self.assertEqual(status, "Present")

	def test_cannot_approve_own(self):
		set_roles(EMPLOYEE, "Employee", "Leave Approver")
		try:
			name = self.request()["name"]
			with self.assertRaises(frappe.PermissionError):
				self.as_user(EMPLOYEE, self_home.review_attendance_request, name, 1)
		finally:
			set_roles(EMPLOYEE, "Employee")

	def test_reject_then_request_again(self):
		day = add_days(nowdate(), -2)
		name = self.request(day)["name"]
		with self.assertRaises(frappe.ValidationError):
			self.as_user(APPROVER, self_home.review_attendance_request, name, 0)
		self.as_user(APPROVER, self_home.review_attendance_request, name, 0, "ไม่มีหลักฐาน")
		self.assertEqual(frappe.db.get_value("Attendance Request", name, "custom_approval_status"), "Rejected")
		again = self.request(day)["name"]
		self.assertTrue(frappe.db.exists("Attendance Request", again))
		self.as_user(EMPLOYEE, self_home.delete_attendance_request, again)
		self.assertFalse(frappe.db.exists("Attendance Request", again))

	def test_pay_summary(self):
		data = self.as_user(EMPLOYEE, self_home.get_pay)
		for key in ("current", "upcoming", "ytd", "sso_total", "slips"):
			self.assertIn(key, data)
		self.assertEqual(data["year"], getdate().year)
