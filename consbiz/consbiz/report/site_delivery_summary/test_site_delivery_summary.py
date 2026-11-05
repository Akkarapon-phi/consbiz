# Copyright (c) 2026, Siricons and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from consbiz.consbiz.report.site_delivery_summary.site_delivery_summary import execute
from consbiz.employer_supplied import employer_item
from consbiz.tests.test_employer_supplied import make_item

MODULE = "consbiz.consbiz.report.site_delivery_summary.site_delivery_summary"
FILTERS = {"company": "_Test Company", "from_date": "2026-11-01", "to_date": "2026-11-30"}


class IntegrationTestSiteDeliverySummary(IntegrationTestCase):
	def test_runs_without_data(self):
		columns, data = execute({**FILTERS, "project": "_Test Project", "delivery_note": "DN-"})
		self.assertIn("delivery_note", [column["fieldname"] for column in columns])
		self.assertEqual(data, [])

	def test_supply_and_order(self):
		base = make_item()
		twin = employer_item(base.name)

		def row(date, voucher, item_code):
			return frappe._dict(posting_date=date, voucher_no=voucher, idx=1, item_code=item_code)

		with (
			patch(f"{MODULE}.purchase_receipt_rows", return_value=[row("2026-11-05", "PR-2", base.name)]),
			patch(f"{MODULE}.stock_entry_rows", return_value=[row("2026-11-03", "SE-1", twin)]),
		):
			data = execute(FILTERS)[1]
			employer_only = execute({**FILTERS, "supply": "Employer"})[1]
		self.assertEqual(
			[(r.voucher_no, r.supply) for r in data], [("SE-1", "ผู้ว่าจ้างจัดหา"), ("PR-2", "ซื้อเอง")]
		)
		self.assertEqual([r.voucher_no for r in employer_only], ["SE-1"])
