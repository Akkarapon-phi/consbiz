# Copyright (c) 2026, Siricons and Contributors
# See license.txt

# รายการเพิ่ม/หักรายเดือน + เงินเดือนพนักงาน (consbiz/hr_salary.py)

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_months, get_first_day, get_last_day, getdate, nowdate

from consbiz import hr_salary
from consbiz.tests.test_self_service import COMPANY, make_employee, make_user

EMPLOYEE = "hr-sal-emp@example.com"
OUTSIDER = "hr-sal-none@example.com"
STRUCTURE = "_Test ConsBiz Salary"
BONUS = "_Test ConsBiz Bonus"


class IntegrationTestHrSalary(IntegrationTestCase):
	def setUp(self):
		from hrms.payroll.doctype.salary_structure.test_salary_structure import make_salary_structure

		frappe.set_user("Administrator")
		self.employee = make_employee(EMPLOYEE, custom_project=None)
		make_user(OUTSIDER)
		frappe.db.delete("Additional Salary", {"employee": self.employee})
		frappe.db.delete("Salary Slip", {"employee": self.employee})
		frappe.db.delete("Salary Structure Assignment", {"employee": self.employee})
		make_salary_structure(STRUCTURE, "Monthly", company=COMPANY, currency="INR", dont_submit=False)
		if not frappe.db.exists("Salary Component", BONUS):
			frappe.get_doc({"doctype": "Salary Component", "salary_component": BONUS, "salary_component_abbr": "TCB", "type": "Earning"}).insert()
		account = frappe.db.get_value("Account", {"company": COMPANY, "root_type": "Expense", "is_group": 0}, "name")
		bonus = frappe.get_doc("Salary Component", BONUS)
		if not any(a.company == COMPANY for a in bonus.accounts):
			bonus.append("accounts", {"company": COMPANY, "account": account})
			bonus.save()
		self.month = str(get_first_day(add_months(nowdate(), -1)))[:7]

	def tearDown(self):
		frappe.set_user("Administrator")

	def test_set_salary_and_history(self):
		data = hr_salary.get_salaries(COMPANY)
		self.assertIn(STRUCTURE, [s["value"] for s in data["structures"]])
		row = next(r for r in data["rows"] if r.name == self.employee)
		self.assertIsNone(row.current)
		hr_salary.set_salary(self.employee, STRUCTURE, 20000, "2026-01-01", "เริ่มงาน")
		hr_salary.set_salary(self.employee, STRUCTURE, 22000, str(get_first_day(nowdate())), "ปรับขึ้น")
		row = next(r for r in hr_salary.get_salaries(COMPANY)["rows"] if r.name == self.employee)
		self.assertEqual(row.current.base, 22000)
		history = hr_salary.get_salary_history(self.employee)
		self.assertEqual([(h.base, h.note) for h in history], [(22000, "ปรับขึ้น"), (20000, "เริ่มงาน")])
		self.assertRaises(frappe.ValidationError, hr_salary.set_salary, self.employee, STRUCTURE, 0, "2026-02-01")
		self.assertRaises(frappe.ValidationError, hr_salary.set_salary, self.employee, "ไม่มีโครงสร้างนี้", 1000, "2026-02-01")

	def test_adjustments(self):
		hr_salary.set_salary(self.employee, STRUCTURE, 20000, "2026-01-01")
		data = hr_salary.get_adjustments(self.month, COMPANY)
		options = [c["value"] for c in data["components"]]
		self.assertIn(BONUS, options)
		# รายการที่ระบบคำนวณเอง (สูตรในโครงสร้าง) ลงด้วยมือไม่ได้
		formula = frappe.db.get_value("Salary Detail", {"parent": STRUCTURE, "amount_based_on_formula": 1}, "salary_component")
		self.assertNotIn(formula, options)
		self.assertRaises(frappe.ValidationError, hr_salary.add_adjustment, self.employee, formula, 100, self.month)
		self.assertRaises(frappe.ValidationError, hr_salary.add_adjustment, self.employee, BONUS, 0, self.month)

		name = hr_salary.add_adjustment(self.employee, BONUS, 1500, self.month, "โบนัสงานเสร็จ")["name"]
		doc = frappe.get_doc("Additional Salary", name)
		self.assertEqual((doc.docstatus, doc.amount, getdate(doc.payroll_date)), (1, 1500, getdate(get_last_day(f"{self.month}-01"))))
		row = next(r for r in hr_salary.get_adjustments(self.month, COMPANY)["rows"] if r.name == name)
		self.assertEqual((row.note, row.locked), ("โบนัสงานเสร็จ", False))
		hr_salary.cancel_adjustment(name)
		self.assertEqual(frappe.db.get_value("Additional Salary", name, "docstatus"), 2)

	def test_only_hr(self):
		frappe.set_user(OUTSIDER)
		self.assertRaises(frappe.PermissionError, hr_salary.get_salaries, COMPANY)
		self.assertRaises(frappe.PermissionError, hr_salary.get_adjustments, self.month, COMPANY)
