# Copyright (c) 2026, Siricons and contributors
# For license information, please see license.txt

import frappe
from frappe.tests import IntegrationTestCase

from consbiz.patches.seed_cost_categories import DEFAULT_CATEGORIES, execute


class TestCostCategory(IntegrationTestCase):
	def test_seed_defaults(self):
		execute()
		for name in DEFAULT_CATEGORIES:
			self.assertTrue(frappe.db.exists("Cost Category", name))
		# รันซ้ำได้ ไม่ซ้ำ ไม่ error
		execute()
		self.assertEqual(frappe.db.count("Cost Category", {"name": ("in", DEFAULT_CATEGORIES)}), len(DEFAULT_CATEGORIES))
