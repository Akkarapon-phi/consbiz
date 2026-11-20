"""Bank register permission boundaries and company-currency running balance."""

from decimal import Decimal
from unittest import TestCase
from unittest.mock import Mock, patch

import frappe

from consbiz import bank_app
from consbiz.accounting_app import report_docname


class TestBankAccount(TestCase):
	def setUp(self):
		self.doc = Mock(company="company", account="bank-gl", is_company_account=True)
		self.doc.get.side_effect = {"account": "bank-gl"}.get
		self.doc.has_permission.return_value = False

	def test_read_only_without_ledger_permission(self):
		with (
			patch.object(frappe, "get_doc", return_value=self.doc),
			patch.object(frappe, "has_permission", return_value=False),
			patch.object(frappe, "get_list", return_value=[frappe._dict(name="bank")]) as query,
		):
			result = bank_app.get_account("bank")
			self.doc.check_permission.assert_called_once_with("read")
			self.assertFalse(result["can_write"])
			self.assertFalse(result["can_gl"])
			self.assertNotIn("rows", result)
			self.assertNotIn("balance", result)
			query.assert_not_called()

			register = bank_app.list_accounts("company")
			self.assertFalse(register["can_gl"])
			self.assertNotIn("balance", register["rows"][0])
			self.assertEqual(query.call_args.args, ("Bank Account",))
			self.assertEqual(
				query.call_args.kwargs["filters"], {"company": "company", "is_company_account": 1}
			)

	def test_period_starts_with_opening_and_keeps_current_balance_separate(self):
		from datetime import date

		movements = [
			frappe._dict(debit="20.15", credit="0", voucher_type="Journal Entry"),
			frappe._dict(debit="0", credit="10.05", voucher_type="Journal Entry"),
		]
		# Query order: opening, movements, balance through today, company currency.
		with (
			patch.object(frappe, "get_doc", return_value=self.doc),
			patch.object(frappe, "has_permission", return_value=True),
			patch.object(
				bank_app, "getdate", side_effect=lambda value=None: date.fromisoformat(value or "2026-11-20")
			),
			patch.object(
				frappe,
				"get_list",
				side_effect=[
					[frappe._dict(account="bank-gl", debit="110.75", credit="10.50")],
					movements,
					[frappe._dict(account="bank-gl", debit="230.90", credit="20.55")],
					[("company", "THB")],
				],
			) as query,
		):
			result = bank_app.get_account("bank", "2026-10")
			self.assertEqual(result["opening"], Decimal("100.25"))
			self.assertEqual([r.balance for r in movements], [Decimal("120.40"), Decimal("110.35")])
			self.assertEqual(result["closing"], Decimal("110.35"))
			self.assertEqual(result["balance"], Decimal("210.35"))
			gl = [c.kwargs for c in query.call_args_list if c.args[0] == "GL Entry"]
			self.assertTrue(all(c["filters"]["is_cancelled"] == 0 for c in gl))
			self.assertEqual(gl[0]["filters"]["posting_date"], ["<", date(2026, 10, 1)])
			self.assertEqual(
				gl[1]["filters"]["posting_date"], ["between", [date(2026, 10, 1), date(2026, 10, 31)]]
			)
			self.assertEqual(gl[2]["filters"]["posting_date"], ["<=", date(2026, 11, 20)])

	def test_purchase_tax_report_uses_internal_key_for_permissions(self):
		self.assertEqual(report_docname("purchase", {"name": "SUP-5", "tax_invoice": "PT-1"}), "PT-1")
		self.assertEqual(report_docname("sales", {"name": "ST-1 (CANCEL)"}), "ST-1")
