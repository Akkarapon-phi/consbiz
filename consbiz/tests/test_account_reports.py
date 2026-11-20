from datetime import date, timedelta
from unittest import TestCase
from unittest.mock import patch

import frappe

from consbiz import account_dashboard, account_ledger, accounting_app, received_wht, vat_report_print


class TestAccountingReports(TestCase):
	def test_tax_list_uses_filing_month_and_company_branch(self):
		for kind, date_field, branch_field in (
			("acc-sales-tax", "report_date", "company_tax_address"),
			("acc-purchase-tax", "report_date", "company_tax_address"),
			("acc-wht", "date", "company_address"),
		):
			with self.subTest(kind=kind), patch.object(accounting_app, "can_read", return_value=True), patch.object(
				frappe, "get_list", return_value=[]
			) as query:
				accounting_app.get_list(kind, "Example", year=2026, month=7, company_address="Branch")
				self.assertEqual(query.call_args.kwargs["filters"], {
					"company": "Example",
					date_field: ["between", (date(2026, 7, 1), date(2026, 7, 31))],
					branch_field: "Branch",
					"docstatus": ["in", [0, 1, 2]],
				})

	def test_empty_tax_reports(self):
		with patch.object(accounting_app, "run_report", return_value=("Report", [], {})):
			self.assertEqual(accounting_app.get_official_form("pnd53", 2026, 7), {"empty": True})
		with patch.object(frappe, "render_template") as render, patch.object(vat_report_print.contract_terms, "font_css"):
			vat_report_print.render_report(
				"sales", 2026, 7, [], {}, empty_headers=[{"operator": "Example"}, {"operator": "Second"}]
			)
		sections = render.call_args.args[1]["sections"]
		self.assertEqual([section["operator"] for section in sections], ["Example", "Second"])
		for section in sections:
			self.assertEqual(section["rows"], [])
			self.assertEqual(section["totals"], ["0.00"] * 3)

	def test_aging_edges_and_credit(self):
		today = date(2026, 11, 20)
		rows = [frappe._dict(outstanding_amount=n, due_date=today - timedelta(days=days),
			party_account_currency="THB") for days, n in ((-1, 4), (0, 10), (1, 1), (30, 2),
			(31, 3), (60, 4), (61, 5), (90, 6), (91, 7), (91, -2))]
		result = account_dashboard.aging(rows, today, "THB")
		self.assertEqual(result, {"amount": 40, "count": 10, "overdue": 7, "buckets": [14, 3, 7, 11, 5]})

	def test_dashboard_without_source_permissions(self):
		with patch.object(frappe, "has_permission", return_value=False), patch.object(frappe, "get_list") as read:
			result = account_dashboard.currency_summary(["Example"], "THB", None, date.today())
			self.assertEqual(result, {"currency": "THB"})
			read.assert_not_called()

	def test_receivable_account_fallback_only_without_mapping(self):
		with patch("consbiz.received_wht.accounting_app.wht_accounts", return_value={"Receive": None}), patch.object(
			frappe, "get_all", side_effect=[[], ["asset"]]) as lookup:
			self.assertEqual(received_wht.receivable_accounts("C"), {"asset"})
			self.assertEqual(lookup.call_args.kwargs["filters"]["company"], "C")
		with patch("consbiz.received_wht.accounting_app.wht_accounts", return_value={"Receive": "configured"}), patch.object(
			frappe, "get_all", return_value=[frappe._dict(account="mapped")]):
			self.assertEqual(received_wht.receivable_accounts("C"), {"configured", "mapped"})

	def test_chart_sign_and_nested_totals(self):
		rows = [
			frappe._dict(name="root", root_type="Liability", is_group=1),
			frappe._dict(name="group", parent_account="root", root_type="Liability", is_group=1),
			frappe._dict(name="leaf", parent_account="group", root_type="Liability", is_group=0),
		]
		with patch.object(account_ledger, "check_access"), patch.object(frappe, "get_list", return_value=rows), patch.object(
			account_ledger.bank_app, "_balances", return_value={"leaf": -70}):
			self.assertEqual([(r.depth, r.balance) for r in account_ledger.chart("C")], [(0, 70), (1, 70), (2, 70)])
