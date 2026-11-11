# Copyright (c) 2026, Siricons and Contributors
# See license.txt

# เบิกเงินใน Self Service (consbiz/self_advance.py): เงินเดือนล่วงหน้า (วงเงิน/ผู้บริหาร/หักเป็นงวด), เงินสำรองจ่าย + เคลียร์, เบิกคืน

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, add_months, get_first_day, getdate, nowdate

from consbiz import self_advance
from consbiz.tests.test_self_service import COMPANY, make_employee, make_user

EMPLOYEE = "advance-emp@example.com"
APPROVER = "advance-approver@example.com"
EXECUTIVE = "advance-exec@example.com"
COMPONENT = "_Test Salary Advance Deduction"


def add_role(user, role):
	doc = frappe.get_doc("User", user)
	if role not in [r.role for r in doc.roles]:
		doc.append("roles", {"role": role})
		doc.save(ignore_permissions=True)


class IntegrationTestSelfAdvance(IntegrationTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		self.employee = make_employee(EMPLOYEE, custom_project=None)
		self.approver_employee = make_employee(APPROVER, custom_project=None)
		make_user(EXECUTIVE)
		add_role(APPROVER, "Expense Approver")
		add_role(EXECUTIVE, "Executive Approver")
		if not frappe.db.exists("Salary Component", COMPONENT):
			frappe.get_doc(
				{"doctype": "Salary Component", "salary_component": COMPONENT, "salary_component_abbr": "TSAD", "type": "Deduction"}
			).insert()
		frappe.db.set_value(
			"Company",
			COMPANY,
			{
				"custom_salary_advance_component": COMPONENT,
				"custom_salary_advance_limit_percent": 50,
				"custom_expense_clear_days": 15,
				"default_expense_claim_payable_account": "_Test Payable - _TC",
			},
		)
		# บัญชีเงินทดรองจ่ายพนักงานจริงเป็น Receivable (ข้อมูลเทสต์ของ ERPNext ตั้งเป็น Payable ทำให้ HRMS หายอดที่จ่ายเพื่อเคลียร์ไม่เจอ)
		frappe.db.set_value("Account", "Employee Advances - _TC", "account_type", "Receivable")
		# erpnext_thailand บังคับให้บริษัทมีแถวใน Thai Tax Settings ก่อนลง Payment Entry (เหมือน test_retention_receivable)
		settings = frappe.get_single("Thai Tax Settings")
		if not any(row.company == COMPANY for row in settings.company_accounts):
			settings.append("company_accounts", {"company": COMPANY})
			settings.save(ignore_permissions=True)
		for doctype in ("Additional Salary", "Expense Claim", "Employee Advance", "Salary Structure Assignment"):
			for row in frappe.get_all(doctype, filters={"employee": self.employee}, pluck="name"):
				frappe.db.delete(doctype, row)
		# เงินเดือน 20,000 = วงเงิน 10,000 (db_insert ไม่ต้องสร้าง Salary Structure จริง)
		ssa = frappe.get_doc(
			{
				"doctype": "Salary Structure Assignment",
				"employee": self.employee,
				"company": COMPANY,
				"salary_structure": "_Test Self Advance Structure",
				"from_date": "2020-01-01",
				"base": 20000,
				"currency": "INR",
				"docstatus": 1,
			}
		)
		ssa.name = frappe.generate_hash(length=10)
		ssa.db_insert()

	def tearDown(self):
		frappe.set_user("Administrator")

	def as_user(self, user, fn, *args, **kwargs):
		frappe.set_user(user)
		try:
			return fn(*args, **kwargs)
		finally:
			frappe.set_user("Administrator")

	def request(self, amount, advance_type="Salary Advance", installments=1):
		return self.as_user(
			EMPLOYEE, self_advance.request_advance, advance_type, amount, "ทดสอบ", installments
		)

	def pay(self, name):
		from hrms.overrides.employee_payment_entry import get_payment_entry_for_employee

		pe = get_payment_entry_for_employee("Employee Advance", name)
		pe.reference_no = "TEST"
		pe.reference_date = nowdate()
		pe.submit()
		return pe

	# ------------------------------------------------------------ เงินเดือนล่วงหน้า

	def test_within_limit_approver_submits(self):
		row = self.request(6000)
		self.assertEqual((row.approval, row.over_limit), ("Pending", 0))
		self.assertEqual(self.as_user(APPROVER, self_advance.review_advance, row.name, 1), "Approved")
		doc = frappe.get_doc("Employee Advance", row.name)
		self.assertEqual((doc.docstatus, doc.custom_approved_by, doc.repay_unclaimed_amount_from_salary), (1, APPROVER, 1))

	def test_over_limit_needs_executive(self):
		self.request(6000)
		row = self.request(5000)
		self.assertEqual(row.over_limit, 1)
		self.assertEqual(self.as_user(APPROVER, self_advance.review_advance, row.name, 1), "Pending Executive")
		self.assertEqual(frappe.db.get_value("Employee Advance", row.name, "docstatus"), 0)
		# ผู้อนุมัติทั่วไปไม่เห็นใบที่รอผู้บริหาร / Submit จากระบบเต็มก็ไม่ได้
		self.assertNotIn(row.name, [a.name for a in self.as_user(APPROVER, self_advance.get_approvals)["advances"]])
		self.assertRaises(frappe.ValidationError, self.as_user, APPROVER, self_advance.review_advance, row.name, 1)
		doc = frappe.get_doc("Employee Advance", row.name)
		frappe.set_user(APPROVER)
		doc.flags.ignore_permissions = True
		self.assertRaises(frappe.ValidationError, doc.submit)
		frappe.set_user("Administrator")

		self.assertIn(row.name, [a.name for a in self.as_user(EXECUTIVE, self_advance.get_approvals)["advances"]])
		self.assertEqual(self.as_user(EXECUTIVE, self_advance.review_advance, row.name, 1), "Approved")
		doc = frappe.get_doc("Employee Advance", row.name)
		self.assertEqual((doc.docstatus, doc.custom_approved_by, doc.custom_executive_approved_by), (1, APPROVER, EXECUTIVE))

	def test_reject_and_withdraw(self):
		row = self.request(1000)
		self.assertRaises(frappe.ValidationError, self.as_user, APPROVER, self_advance.review_advance, row.name, 0)
		self.as_user(APPROVER, self_advance.review_advance, row.name, 0, "ยังไม่ถึงรอบ")
		self.assertEqual(frappe.db.get_value("Employee Advance", row.name, "custom_approval_status"), "Rejected")
		self.assertRaises(frappe.ValidationError, self.as_user, EMPLOYEE, self_advance.delete_advance, row.name)
		other = self.request(1000)
		self.as_user(EMPLOYEE, self_advance.delete_advance, other.name)
		self.assertFalse(frappe.db.exists("Employee Advance", other.name))

	def test_no_self_approval_and_only_approvers(self):
		mine = self.as_user(APPROVER, self_advance.request_advance, "Expense Advance", 500, "ของตัวเอง")
		self.assertRaises(frappe.PermissionError, self.as_user, APPROVER, self_advance.review_advance, mine.name, 1)
		row = self.request(500)
		self.assertRaises(frappe.PermissionError, self.as_user, EMPLOYEE, self_advance.review_advance, row.name, 1)

	def test_payment_creates_installment_deductions(self):
		row = self.request(5000, installments=3)
		self.as_user(APPROVER, self_advance.review_advance, row.name, 1)
		self.pay(row.name)
		rows = frappe.get_all(
			"Additional Salary",
			filters={"ref_doctype": "Employee Advance", "ref_docname": row.name, "docstatus": 1},
			fields=["amount", "payroll_date", "salary_component"],
			order_by="payroll_date asc",
		)
		self.assertEqual([r.amount for r in rows], [1666.67, 1666.67, 1666.66])
		first = get_first_day(nowdate())
		self.assertEqual([getdate(r.payroll_date).replace(day=1) for r in rows], [getdate(add_months(first, i)) for i in range(3)])
		self.assertEqual({r.salary_component for r in rows}, {COMPONENT})
		self.assertTrue(frappe.db.get_value("Employee Advance", row.name, "custom_deductions_created"))

	def test_installments_split(self):
		self.assertEqual(self_advance.installment_amounts(1000, 3), [333.33, 333.33, 333.34])
		self.assertEqual(self_advance.installment_amounts(1000, 1), [1000])

	# ------------------------------------------------------------ เงินสำรองจ่าย / เบิกคืน

	def receipt(self):
		frappe.set_user(EMPLOYEE)
		try:
			return frappe.get_doc(
				{"doctype": "File", "file_name": f"bill-{frappe.generate_hash(length=6)}.txt", "content": "bill", "is_private": 1}
			).insert(ignore_permissions=True).name
		finally:
			frappe.set_user("Administrator")

	def test_expense_advance_clear(self):
		row = self.request(3000, "Expense Advance")
		self.as_user(APPROVER, self_advance.review_advance, row.name, 1)
		pe = self.pay(row.name)
		due = frappe.db.get_value("Employee Advance", row.name, "custom_clear_due_date")
		self.assertEqual(getdate(due), getdate(add_days(pe.posting_date, 15)))

		rows = [{"expense_type": "Travel", "amount": 1200, "description": "ค่ารถ", "receipt": None}]
		self.assertRaises(frappe.ValidationError, self.as_user, EMPLOYEE, self_advance.submit_claim, rows, None, row.name)
		rows[0]["receipt"] = self.receipt()
		result = self.as_user(EMPLOYEE, self_advance.submit_claim, rows, "เคลียร์", row.name)
		self.assertEqual((result["total"], result["advance"]), (1200, 1200))
		claim = frappe.get_doc("Expense Claim", result["name"])
		self.assertTrue(claim.expenses[0].custom_receipt)
		self.assertEqual(frappe.db.get_value("File", rows[0]["receipt"], "attached_to_name"), claim.name)

		self.assertEqual(self.as_user(APPROVER, self_advance.review_claim, claim.name, 1), "Approved")
		advance = frappe.get_doc("Employee Advance", row.name)
		self.assertEqual(advance.claimed_amount, 1200)
		data = self.as_user(EMPLOYEE, self_advance.get_advance_data)
		mine = next(a for a in data["advances"] if a.name == row.name)
		self.assertEqual((mine.unclaimed, mine.can_clear), (1800, True))

	def test_reimbursement_without_advance(self):
		rows = [{"expense_type": "Food", "amount": 350, "receipt": self.receipt()}]
		result = self.as_user(EMPLOYEE, self_advance.submit_claim, rows)
		self.assertEqual(result["advance"], 0)
		self.as_user(APPROVER, self_advance.review_claim, result["name"], 0, "บิลไม่ชัด")
		self.assertEqual(frappe.db.get_value("Expense Claim", result["name"], "docstatus"), 0)
		self.assertRaises(frappe.ValidationError, self.as_user, EMPLOYEE, self_advance.delete_claim, result["name"])

	def test_overdue_reminder(self):
		row = self.request(1000, "Expense Advance")
		self.as_user(APPROVER, self_advance.review_advance, row.name, 1)
		self.pay(row.name)
		frappe.db.set_value("Employee Advance", row.name, "custom_clear_due_date", add_days(nowdate(), -1))
		self_advance.remind_overdue_clearing()
		self.assertEqual(getdate(frappe.db.get_value("Employee Advance", row.name, "custom_last_reminder")), getdate())

	# ------------------------------------------------------------ ข้อมูลประกอบการอนุมัติ / หน้าเบิกเงินของ HR

	def test_money_context_and_hr_advances(self):
		from consbiz import approvals, hr_advances

		row = self.request(5000, installments=2)
		# หัวหน้าหน้างาน (ไม่มี Role การเบิก) ไม่เห็นข้อมูลเงิน
		make_user("advance-site-boss@example.com")
		self.assertRaises(frappe.PermissionError, self.as_user, "advance-site-boss@example.com", approvals.get_context, self.employee, "advance")
		ctx = self.as_user(APPROVER, approvals.get_context, self.employee, "advance")
		self.assertEqual((ctx["money"]["limit"]["base"], ctx["money"]["limit"]["limit"]), (20000, 10000))
		self.assertEqual(ctx["money"]["advances"][0].name, row.name)

		stage = lambda: next(a for a in hr_advances.get_advances(COMPANY)["advances"] if a.name == row.name).stage  # noqa: E731
		self.assertEqual(stage(), "pending")
		self.as_user(APPROVER, self_advance.review_advance, row.name, 1)
		self.assertEqual(stage(), "to_pay")
		self.pay(row.name)
		self.assertEqual(stage(), "repaying")
		repay = approvals.repayment_of(row.name)
		self.assertEqual((repay["total"], repay["deducted"], repay["remaining"]), (5000, 0, 5000))
