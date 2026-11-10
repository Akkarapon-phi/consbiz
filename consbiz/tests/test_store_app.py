# Copyright (c) 2026, Siricons and Contributors
# See license.txt

# API ของแอปสโตร์ (consbiz/store_app.py)

import frappe
from frappe.tests import IntegrationTestCase

from consbiz.store_app import get_projects


class IntegrationTestStoreApp(IntegrationTestCase):
	def test_get_projects_includes_project_abbreviation(self):
		project = frappe.get_doc(
			{
				"doctype": "Project",
				"project_name": frappe.generate_hash(length=10),
				"company": frappe.db.get_value("Company", {}, "name"),
				"custom_abbr": "TST",
				"status": "Open",
			}
		).insert(ignore_permissions=True)

		row = next(p for p in get_projects() if p.name == project.name)

		self.assertEqual(row.custom_abbr, "TST")
