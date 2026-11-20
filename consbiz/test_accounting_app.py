# Copyright (c) 2026, Siricons and Contributors
# See license.txt

# หมวดบัญชีของแอปออฟฟิศ (accounting_app.py): จ่ายชำระต่อจากใบแจ้งหนี้ซื้อ (หัก ณ ที่จ่ายจากใบแจ้งหนี้),
# หนังสือรับรองหัก ณ ที่จ่ายจากการจ่ายชำระ, ยกเลิกจ่ายชำระพร้อมหนังสือรับรอง, ข้อห้ามของยอด/บัญชี

import json

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, getdate, nowdate

from consbiz import accounting_app
from consbiz.consbiz.doctype.retention_receivable.test_retention_receivable import (
	ABBR,
	COMPANY,
	SUPPLIER,
	cash_account,
	setup_retention_masters,
)

ITEM = "_Test Accounting Service"
WHT_TYPE = "_Test WHT 3 (Pay)"


def setup_accounting_masters():
	setup_retention_masters()
	wht_account = f"_Test WHT Payable - {ABBR}"
	if not frappe.db.exists("Account", wht_account):
		parent = frappe.db.get_value(
			"Account", {"company": COMPANY, "account_name": "Current Liabilities", "is_group": 1}, "name"
		)
		frappe.get_doc(
			{
				"doctype": "Account",
				"account_name": "_Test WHT Payable",
				"parent_account": parent,
				"company": COMPANY,
			}
		).insert(ignore_permissions=True)
	frappe.db.set_value("Company", COMPANY, "custom_wht_payable", wht_account)
	if not frappe.db.exists("Withholding Tax Type", WHT_TYPE):
		frappe.get_doc(
			{
				"doctype": "Withholding Tax Type",
				"title": WHT_TYPE,
				"percent": 3,
				"for_payment_type": "Pay",
				"accounts": [{"company": COMPANY, "account": wht_account}],
			}
		).insert(ignore_permissions=True)
	if not frappe.db.exists("Item", ITEM):
		frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": ITEM,
				"item_name": ITEM,
				"item_group": frappe.db.get_value("Item Group", {"is_group": 0}, "name"),
				"stock_uom": "Nos",
				"is_stock_item": 0,
			}
		).insert(ignore_permissions=True)
	if not frappe.db.exists("Withholding Tax Type Of Income", accounting_app.DEFAULT_INCOME):
		frappe.get_doc(
			{
				"doctype": "Withholding Tax Type Of Income",
				"__newname": accounting_app.DEFAULT_INCOME,
				"description": "ค่าจ้างทำของ",
			}
		).insert(ignore_permissions=True)
	return wht_account


def make_invoice(amount=1000, wht=30):
	wht_account = setup_accounting_masters()
	expense = frappe.db.get_value(
		"Account", {"company": COMPANY, "root_type": "Expense", "is_group": 0}, "name"
	)
	pi = frappe.new_doc("Purchase Invoice")
	pi.company = COMPANY
	pi.supplier = SUPPLIER
	pi.posting_date = nowdate()
	pi.set_posting_time = 1
	pi.bill_no = frappe.generate_hash(length=8)
	pi.append("items", {"item_code": ITEM, "qty": 1, "rate": amount, "expense_account": expense})
	pi.custom_subject_to_wht = 1
	pi.custom_wht_percent = 3
	pi.append(
		"custom_payment_entry_deduction",
		{
			"account": wht_account, "amount": wht, "description": "ภาษีหัก ณ ที่จ่าย",
			"cost_center": frappe.get_cached_value("Company", COMPANY, "cost_center"),
		},
	)
	pi.insert()
	pi.submit()
	return pi


class IntegrationTestAccountingApp(IntegrationTestCase):
	def setUp(self):
		setup_accounting_masters()

	def pay(self, pi, **extra):
		defaults = accounting_app.payment_defaults("pi", pi.name)
		data = {"account": cash_account(), "deductions": defaults["deductions"], **extra}
		return defaults, accounting_app.make_payment("pi", pi.name, json.dumps(data), 1)

	def test_pay_invoice_with_wht_then_certificate(self):
		pi = make_invoice()
		defaults, result = self.pay(pi)
		row = defaults["deductions"][0]
		self.assertTrue(row["wht"])
		self.assertEqual(row["wht_type"], WHT_TYPE)
		self.assertEqual(row["wht_base"], 1000)

		view = accounting_app.get_payment(result["name"])
		self.assertEqual(view["doc"]["docstatus"], 1)
		self.assertEqual(view["doc"]["paid_amount"], 970)
		self.assertEqual(view["doc"]["total_allocated"], 1000)
		self.assertTrue(view["can_cert"])
		self.assertEqual(frappe.db.get_value("Purchase Invoice", pi.name, "outstanding_amount"), 0)
		self.assertFalse(accounting_app.can_pay(frappe.get_doc("Purchase Invoice", pi.name)))

		new = accounting_app.get_cert(source=result["name"])
		self.assertEqual(new["doc"]["supplier"], SUPPLIER)
		self.assertEqual(new["doc"]["items"][0]["tax_base"], 1000)
		self.assertEqual(new["doc"]["items"][0]["tax_amount"], 30)
		cert = accounting_app.save_cert(json.dumps(new["doc"], default=str), submit=1)
		self.assertEqual(cert["doc"]["docstatus"], 1)
		self.assertEqual(frappe.db.get_value("Payment Entry", result["name"], "wht_status"), "Issued")
		self.assertFalse(accounting_app.get_payment(result["name"])["can_cert"])
		with self.assertRaises(frappe.ValidationError):
			accounting_app.save_cert(json.dumps(new["doc"], default=str))

		cancelled = accounting_app.cancel_payment(result["name"])
		self.assertEqual(cancelled["doc"]["docstatus"], 2)
		self.assertEqual(frappe.db.get_value("Withholding Tax Cert", cert["doc"]["name"], "docstatus"), 2)
		self.assertEqual(frappe.db.get_value("Purchase Invoice", pi.name, "outstanding_amount"), 1000)

	def test_partial_payment_and_guards(self):
		pi = make_invoice()
		with self.assertRaises(frappe.ValidationError):
			self.pay(pi, allocated=2000)
		with self.assertRaises(frappe.ValidationError):
			accounting_app.make_payment("pi", pi.name, json.dumps({"account": None}), 1)
		_defaults, result = self.pay(pi, allocated=400, deductions=[])
		self.assertEqual(frappe.db.get_value("Purchase Invoice", pi.name, "outstanding_amount"), 600)
		again = accounting_app.payment_defaults("pi", pi.name)
		# จ่ายไปแล้วบางส่วน: ไม่เติมรายการหักซ้ำ
		self.assertTrue(again["paid_before"])
		self.assertEqual(again["deductions"], [])
		self.assertEqual(again["outstanding"], 600)
		rows = accounting_app.get_list("acc-payments", company=COMPANY)
		self.assertIn(result["name"], [r.name for r in rows])

	def test_postdated_cheque_clearance_and_undo(self):
		mode = "_Test Cheque"
		if not frappe.db.exists("Mode of Payment", mode):
			frappe.get_doc({"doctype": "Mode of Payment", "mode_of_payment": mode, "type": "Bank"}).insert()
		tomorrow = str(add_days(nowdate(), 1))
		_, payment = self.pay(make_invoice(), mode_of_payment=mode, reference_no="CHK-01", reference_date=tomorrow)
		name = payment["name"]

		def row():
			return next(r for r in accounting_app.get_list("acc-cheques-out", company=COMPANY) if r.name == name)

		waiting = accounting_app.get_summary(company=COMPANY)["acc-cheques-out"]["count"]
		self.assertTrue(row().postdated)
		self.assertEqual(row().amount, 970)
		self.assertFalse(any(r.name == name for r in accounting_app.get_list("acc-cheques-in")))
		with self.assertRaises(frappe.ValidationError):
			accounting_app.set_cheque_clearance(name, nowdate(), "")
		accounting_app.set_cheque_clearance(name, tomorrow, "")
		self.assertEqual(row().clearance_date, getdate(tomorrow))
		self.assertFalse(row().waiting)
		self.assertEqual(accounting_app.get_summary(company=COMPANY)["acc-cheques-out"]["count"], waiting - 1)
		with self.assertRaises(frappe.ValidationError):
			accounting_app.set_cheque_clearance(name, "", "")
		accounting_app.set_cheque_clearance(name, "", tomorrow)
		self.assertTrue(row().waiting)
		self.assertEqual(row().docstatus, 1)

	def test_unknown_list(self):
		with self.assertRaises(frappe.PermissionError):
			accounting_app.get_list("unknown")
