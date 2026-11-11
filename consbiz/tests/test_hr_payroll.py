# Copyright (c) 2026, Siricons and Contributors
# See license.txt

# เงินเดือน (consbiz/hr_payroll.py): Payroll Entry ของ HRMS ต้องบันทึกการเข้างานครบก่อนสร้าง/ยืนยันสลิป

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_months, get_first_day, get_last_day, getdate, nowdate

from consbiz import hr_attendance, hr_payroll
from consbiz.tests.test_self_service import COMPANY, make_employee, make_project, make_user

EMPLOYEE = "hr-pay-emp@example.com"
OUTSIDER = "hr-pay-none@example.com"
HOLIDAY_LIST = "_Test ConsBiz Payroll Holidays"


class IntegrationTestHrPayroll(IntegrationTestCase):
	def setUp(self):
		from hrms.payroll.doctype.salary_structure.test_salary_structure import make_salary_structure

		frappe.set_user("Administrator")
		self.start = getdate(get_first_day(add_months(nowdate(), -1)))
		self.end = getdate(get_last_day(self.start))
		self.month = str(self.start)[:7]
		if not frappe.db.exists("Holiday List", HOLIDAY_LIST):
			frappe.get_doc(
				{
					"doctype": "Holiday List",
					"holiday_list_name": HOLIDAY_LIST,
					"from_date": self.start.replace(month=1, day=1),
					"to_date": self.start.replace(month=12, day=31),
				}
			).insert()
		frappe.db.set_value(
			"Account", frappe.db.get_value("Company", COMPANY, "default_payroll_payable_account"), "account_type", "Payable"
		)
		self.project = make_project("_Test HR Payroll Project")
		self.employee = make_employee(EMPLOYEE, custom_project=self.project, holiday_list=HOLIDAY_LIST)
		make_user(OUTSIDER)
		for name in frappe.get_all(
			"Payroll Entry", filters={"company": COMPANY, "start_date": self.start, "docstatus": ("<", 2)}, pluck="name"
		):
			frappe.db.delete("Salary Slip", {"payroll_entry": name})
			frappe.db.delete("Payroll Employee Detail", {"parent": name})
			frappe.db.delete("Payroll Entry", name)
		for doctype in ("Attendance", "Employee Checkin", "Salary Slip"):
			frappe.db.delete(doctype, {"employee": self.employee})
		# งวดนี้มีเฉพาะพนักงานของเทสต์ (โครงสร้างเงินเดือนของคนอื่นในบริษัทเดียวกันไม่เกี่ยว)
		frappe.db.delete("Salary Structure Assignment", {"company": COMPANY})
		make_salary_structure(
			"_Test ConsBiz Monthly",
			"Monthly",
			employee=self.employee,
			company=COMPANY,
			currency="INR",
			from_date=self.start.replace(month=1, day=1),
			base=30000,
		)

	def tearDown(self):
		frappe.set_user("Administrator")

	def mark_month(self):
		"""ไม่มีการลงเวลาทั้งเดือน = รอตัดสินทุกวันทำงาน → ตัดสินเป็นมาทำงานทั้งหมด"""
		rows = hr_attendance.get_summary_month(self.month, COMPANY, self.project)["rows"]
		days = [d for d, c in next(r for r in rows if r["employee"] == self.employee)["days"].items() if c["s"] == "flag"]
		hr_attendance.decide_days(self.employee, days, "Present")

	def test_attendance_required_then_slips(self):
		data = hr_payroll.get_payroll(self.month, COMPANY)
		self.assertIsNone(data["entry"])
		self.assertTrue(data["attendance"]["flag"])
		self.assertRaises(frappe.ValidationError, hr_payroll.create_payroll, self.month, COMPANY)

		self.mark_month()
		name = hr_payroll.create_payroll(self.month, COMPANY)["name"]
		self.assertRaises(frappe.ValidationError, hr_payroll.create_payroll, self.month, COMPANY)
		data = hr_payroll.get_payroll(self.month, COMPANY)
		self.assertEqual(data["entry"].name, name)
		self.assertEqual([(s.employee, s.docstatus) for s in data["slips"]], [(self.employee, 0)])
		self.assertEqual(data["totals"]["gross_pay"], data["slips"][0].gross_pay)
		slip = hr_payroll.get_slip(data["slips"][0].name)
		self.assertTrue(slip["earnings"])

		# แก้การเข้างานหลังสร้างสลิป: วันขาดต้องมีผลตอนยืนยัน
		absent_day = next(d for d, c in hr_attendance.build(COMPANY, self.month, employee=self.employee)[2][0]["days"].items() if c["s"] == "marked")
		hr_attendance.decide_days(self.employee, [absent_day], "Absent")
		hr_payroll.submit_slips(name)
		slip = frappe.get_doc("Salary Slip", data["slips"][0].name)
		self.assertEqual((slip.docstatus, slip.absent_days), (1, 1))
		self.assertRaises(frappe.ValidationError, hr_payroll.cancel_payroll, name)

	def test_waived_absence_is_paid(self):
		self.mark_month()
		day = next(d for d, c in hr_attendance.build(COMPANY, self.month, employee=self.employee)[2][0]["days"].items() if c["s"] == "marked")
		hr_attendance.decide_days(self.employee, [day], "Absent", waive=1)
		name = hr_payroll.create_payroll(self.month, COMPANY)["name"]
		slip = frappe.get_doc("Salary Slip", {"payroll_entry": name})
		self.assertEqual((slip.absent_days, slip.leave_without_pay, slip.payment_days), (0, 0, slip.total_working_days))

	def test_cancel_before_submit_removes_slips(self):
		self.mark_month()
		name = hr_payroll.create_payroll(self.month, COMPANY)["name"]
		hr_payroll.cancel_payroll(name)
		self.assertFalse(frappe.db.exists("Salary Slip", {"payroll_entry": name, "docstatus": ("<", 2)}))
		self.assertIsNone(hr_payroll.get_payroll(self.month, COMPANY)["entry"])

	def test_only_hr(self):
		frappe.set_user(OUTSIDER)
		self.assertFalse(hr_payroll.can_manage())
		self.assertRaises(frappe.PermissionError, hr_payroll.get_payroll, self.month, COMPANY)
		self.assertRaises(frappe.PermissionError, hr_payroll.create_payroll, self.month, COMPANY)
