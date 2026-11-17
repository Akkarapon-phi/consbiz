# Copyright (c) 2026, Siricons and Contributors
# See license.txt

# ตั้งค่า HR (consbiz/hr_setup.py): ตรวจ + แก้การตั้งค่า HR/เงินเดือนของบริษัท

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import getdate

from consbiz import hr_setup
from consbiz.tests.test_self_service import COMPANY, make_employee, make_user

OUTSIDER = "hr-setup-none@example.com"


class IntegrationTestHrSetup(IntegrationTestCase):
	def setUp(self):
		frappe.set_user("Administrator")

	def tearDown(self):
		frappe.set_user("Administrator")

	def test_all_checks_run(self):
		data = hr_setup.get_checks(COMPANY)
		self.assertEqual(len(data["checks"]), len(hr_setup.CHECKS))
		self.assertFalse([c for c in data["checks"] if "ตรวจไม่สำเร็จ" in (c["detail"] or "")])
		self.assertTrue(data["can_fix"])

	def test_sso_formula_uses_actual_wage(self):
		from hrms.payroll.utils import COMPONENT_EVAL_GLOBALS

		run = lambda **d: frappe.safe_eval(hr_setup.sso_formula("2026-05-01"), COMPONENT_EVAL_GLOBALS, {"OT": 0, **d})  # noqa: E731
		self.assertEqual(run(base=30000, payment_days=30, total_working_days=30), 875)
		self.assertEqual(run(base=15000, payment_days=15, total_working_days=30), 375)
		self.assertEqual(run(base=12000, payment_days=30, total_working_days=30, OT=2000), 700)

	def test_tax_slab_gaps_are_fixed(self):
		slab = frappe.get_doc(
			{
				"doctype": "Income Tax Slab",
				"name": "_Test ConsBiz Slab",
				"__newname": "_Test ConsBiz Slab",
				"effective_from": "2025-01-01",
				"company": COMPANY,
				"currency": frappe.db.get_value("Company", COMPANY, "default_currency"),
				"slabs": [
					{"from_amount": 0, "to_amount": 150000, "percent_deduction": 0},
					{"from_amount": 150001, "to_amount": 100000, "percent_deduction": 5},
					{"from_amount": 300001, "to_amount": 0, "percent_deduction": 10},
				],
			}
		)
		slab.insert()
		slab.submit()
		self.assertEqual(hr_setup.check_tax_slab(COMPANY)["status"], "error")
		hr_setup.apply_fix("tax_slab", COMPANY)
		rows = frappe.get_all("Taxable Salary Slab", filters={"parent": slab.name}, fields=["from_amount", "to_amount"], order_by="from_amount")
		self.assertEqual([r.to_amount for r in rows], [150000, 300000, 0])
		self.assertFalse(hr_setup.tax_slab_problems(slab.name))

	def test_leave_policy_and_allocations(self):
		employee = make_employee("hr-setup-emp@example.com", custom_project=None)
		# เข้างานกลางปี
		frappe.db.set_value("Employee", employee, "date_of_joining", f"{getdate().year}-08-01")
		frappe.db.delete("Leave Allocation", {"employee": employee})
		frappe.db.delete("Leave Policy Assignment", {"employee": employee})
		hr_setup.apply_fix("leave_holidays", COMPANY)
		self.assertFalse(frappe.get_all("Leave Type", filters={"is_lwp": 0, "include_holiday": 1}))
		hr_setup.apply_fix("leave_policy", COMPANY)
		self.assertTrue(hr_setup.current_leave_period(COMPANY))
		hr_setup.apply_fix("leave_allocations", COMPANY)
		year = getdate().year
		allocated = dict(
			frappe.get_all(
				"Leave Allocation",
				filters={"employee": employee, "docstatus": 1, "to_date": (">=", f"{year}-01-01")},
				fields=["leave_type", "new_leaves_allocated"],
				as_list=True,
			)
		)
		for leave_type in hr_setup.STATUTORY_LEAVES:
			self.assertIn(leave_type, allocated)
		# เข้างานกลางปี: ลาป่วย/ลากิจ ได้เต็มสิทธิ์ (ไม่ลดตามสัดส่วน)
		for leave_type in hr_setup.FULL_YEAR_LEAVES:
			self.assertEqual(allocated[leave_type], hr_setup.STATUTORY_LEAVES[leave_type])
		self.assertNotIn(employee, [e.name for e in hr_setup.employees_without_leave(COMPANY)])
		# รันซ้ำไม่สร้างซ้ำ
		hr_setup.apply_fix("leave_allocations", COMPANY)
		self.assertEqual(frappe.db.count("Leave Policy Assignment", {"employee": employee, "docstatus": 1}), 1)

	def test_unpaid_component(self):
		frappe.db.set_value("Company", COMPANY, "custom_unpaid_time_component", None)
		hr_setup.apply_fix("unpaid_component", COMPANY)
		self.assertEqual(frappe.db.get_value("Company", COMPANY, "custom_unpaid_time_component"), hr_setup.UNPAID_COMPONENT)
		self.assertEqual(frappe.db.get_value("Salary Component", hr_setup.UNPAID_COMPONENT, "type"), "Deduction")

	def test_only_managers_fix(self):
		make_user(OUTSIDER)
		frappe.set_user(OUTSIDER)
		self.assertRaises(frappe.PermissionError, hr_setup.get_checks, COMPANY)
		self.assertRaises(frappe.PermissionError, hr_setup.apply_fix, "tax_slab", COMPANY)
