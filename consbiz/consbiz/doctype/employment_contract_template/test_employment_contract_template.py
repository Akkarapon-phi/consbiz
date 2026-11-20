# Copyright (c) 2026, Siricons and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase

from consbiz.contract_terms import render_terms, unknown_variables

IGNORE_TEST_RECORD_DEPENDENCIES = ["Company"]


class IntegrationTestEmploymentContractTemplate(IntegrationTestCase):
	def test_render_escapes_and_marks_blank(self):
		html = render_terms("<p>{{ employee_name }} / {{ designation }}</p>", {"employee_name": "<b>A</b>", "designation": ""})
		self.assertIn("&lt;b&gt;A&lt;/b&gt;", html)
		self.assertIn("ec-blank", html)

	def test_spacing_variants(self):
		self.assertIn("X", render_terms("{{base}}{{  base  }}", {"base": "X"}))

	def test_unknown_variables(self):
		self.assertEqual(unknown_variables("{{ employee_name }} {{ nope }}"), ["nope"])

	def test_single_default_per_company(self):
		a = frappe.get_doc({"doctype": "Employment Contract Template", "title": "_T1", "terms": "<p>x</p>", "is_default": 1}).insert()
		b = frappe.get_doc({"doctype": "Employment Contract Template", "title": "_T2", "terms": "<p>y</p>", "is_default": 1}).insert()
		self.assertEqual(frappe.db.get_value("Employment Contract Template", a.name, "is_default"), 0)
		self.assertEqual(b.is_default, 1)
