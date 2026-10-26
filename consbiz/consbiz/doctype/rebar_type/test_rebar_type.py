# Copyright (c) 2026, Siricons and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase

from consbiz.consbiz.doctype.rebar_type.rebar_type import nominal_mass

EXTRA_TEST_RECORD_DEPENDENCIES = []
IGNORE_TEST_RECORD_DEPENDENCIES = []


class IntegrationTestRebarType(IntegrationTestCase):
	def test_nominal_mass(self):
		# ตามตารางที่ 1 ของ มอก. 20 / มอก. 24
		self.assertEqual(nominal_mass(10), 0.616)
		self.assertEqual(nominal_mass(16), 1.578)
		self.assertEqual(nominal_mass(40), 9.865)
		# ขนาดนอกตาราง ใช้สูตร
		self.assertEqual(nominal_mass(14), 1.208)

	def test_defaults(self):
		doc = frappe.get_doc(
			{
				"doctype": "Rebar Type",
				"rebar_name": "T-DB25-SD50",
				"surface": "DB",
				"diameter": 25,
				"grade": "SD50",
				"standard_lengths": "12; 10",
			}
		).insert()
		self.assertEqual(doc.unit_weight, 3.853)
		self.assertEqual(doc.standard_lengths, "12, 10")

		doc.diameter = 0
		with self.assertRaises(frappe.ValidationError):
			doc.save()
