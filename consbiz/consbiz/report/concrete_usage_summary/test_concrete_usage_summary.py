# Copyright (c) 2026, Siricons and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from consbiz.consbiz.report.concrete_usage_summary.concrete_usage_summary import execute

IGNORE_TEST_RECORD_DEPENDENCIES = ["Concrete Usage", "Project", "Company", "Supplier", "Item"]

MODULE = "consbiz.consbiz.report.concrete_usage_summary.concrete_usage_summary"


def ticket(name, qty, employer=0):
	return frappe._dict(concrete_usage=name, date="2026-11-04", project="P", wbs="1.1", task_name="ฐานราก", location="F1", concrete_item="C", strength="240", supplier="S", planned_qty=10, ticket_no=f"T{qty}", qty=qty, employer_supplied=employer)


class IntegrationTestConcreteUsageSummary(IntegrationTestCase):
	def test_runs_without_data(self):
		self.assertEqual(execute({"project": "_Test Project"})[1], [])
		self.assertEqual(execute({"project": "_Test Project", "show_tickets": 1})[1], [])

	def test_groups_tickets_per_usage(self):
		with patch(f"{MODULE}.fetch_tickets", return_value=[ticket("CU-1", 6), ticket("CU-1", 5, 1), ticket("CU-2", 3)]):
			rows = execute({})[1]
			tickets = execute({"show_tickets": 1})[1]
		first, second = rows
		self.assertEqual((first.trucks, first.qty, first.company_qty, first.employer_qty, first.variance), (2, 11, 6, 5, 1))
		self.assertEqual((second.qty, second.variance), (3, -7))
		self.assertEqual([t.supply for t in tickets], ["ซื้อเอง", "ผู้ว่าจ้างจัดหา", "ซื้อเอง"])
