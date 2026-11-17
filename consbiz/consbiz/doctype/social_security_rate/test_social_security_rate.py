# Copyright (c) 2026, Siricons and contributors
# For license information, please see license.txt

# การคิดเงินสมทบอยู่ในเทสต์ของ Labour Timesheet

import frappe
from frappe.tests import IntegrationTestCase

from consbiz.social_security import contribution, due, rate_on


class IntegrationTestSocialSecurityRate(IntegrationTestCase):
	def test_validation(self):
		doc = frappe.get_doc(
			{
				"doctype": "Social Security Rate",
				"from_date": "2027-02-01",
				"to_date": "2027-01-01",
				"employee_rate": 5,
				"employer_rate": 5,
				"min_base": 1650,
				"max_base": 17500,
			}
		)
		self.assertRaises(frappe.ValidationError, doc.insert)

	def test_contribution_telescopes(self):
		rate = rate_on("2026-05-10")
		self.assertEqual(due(30000, rate), 875)
		first = contribution(0, 9000, rate, False)
		second = contribution(9000, 9000, rate, True)
		self.assertEqual(first[0] + second[0], 875)
