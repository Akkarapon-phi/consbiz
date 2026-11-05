# Copyright (c) 2026, Siricons and Contributors
# See license.txt

from frappe.tests import IntegrationTestCase

from consbiz.consbiz.report.borrowed_equipment_outstanding.borrowed_equipment_outstanding import execute


class IntegrationTestBorrowedEquipmentOutstanding(IntegrationTestCase):
	def test_runs(self):
		columns, data = execute({"project": "_Test Project", "overdue_only": 1})
		self.assertIn("responsible", [column["fieldname"] for column in columns])
		self.assertEqual(data, [])
