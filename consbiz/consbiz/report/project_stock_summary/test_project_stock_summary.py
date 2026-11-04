# Copyright (c) 2026, Siricons and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from consbiz.consbiz.report.project_stock_summary.project_stock_summary import execute

IGNORE_TEST_RECORD_DEPENDENCIES = ["Project", "Company", "Item", "Construction Management"]

MODULE = "consbiz.consbiz.report.project_stock_summary.project_stock_summary"


def source(**values):
	return {"requested": 0, "ordered": 0, "received": 0, "pending": 0, "qty_in": 0, "qty_out": 0, "balance": 0, **values}


class IntegrationTestProjectStockSummary(IntegrationTestCase):
	def test_requires_project(self):
		self.assertEqual(execute({})[1], [])

	def test_flattens_sources(self):
		item = {
			"item_code": "A",
			"item_name": "Rebar",
			"stock_uom": "Nos",
			"need": 10,
			"balance": 7,
			"short": 2,
			"company": source(pending=3, qty_in=5, qty_out=1, balance=4),
			"employer": source(qty_in=3, balance=3),
		}
		with patch(f"{MODULE}.stock_items", return_value={"items": [item]}):
			columns, (row,) = execute({"project": "_Test Project"})
		fields = [column["fieldname"] for column in columns]
		self.assertTrue({"company_pending", "employer_balance", "short"} <= set(fields))
		self.assertEqual((row["company_pending"], row["employer_qty_in"], row["balance"]), (3, 3, 7))
