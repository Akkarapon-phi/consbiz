# Copyright (c) 2026, Siricons and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase

from consbiz.consbiz.doctype.construction_management.construction_management import create_from_boq
from consbiz.consbiz.doctype.inspection_request.inspection_request import make_reinspection

EXTRA_TEST_RECORD_DEPENDENCIES = []
IGNORE_TEST_RECORD_DEPENDENCIES = [
	"Construction Management",
	"BOQ",
	"Customer",
	"Company",
	"Holiday List",
	"UOM",
	"Project",
]


def make_plan():
	boq = frappe.new_doc("BOQ")
	boq.naming_series = frappe.get_meta("BOQ").get_field("naming_series").options.split("\n")[0]
	boq.date = "2026-11-02"
	for row in (
		{"wbs": "1", "item_name": "หมวด", "quantity": 0},
		{"wbs": "1.1", "item_name": "งานฐานราก", "quantity": 10, "total_amount": 3000},
	):
		boq.append("boq_details", row)
	boq.insert()
	return create_from_boq(boq.name)


class IntegrationTestInspectionRequest(IntegrationTestCase):
	def setUp(self):
		self.plan = make_plan()

	def make_request(self, **values):
		doc = frappe.new_doc("Inspection Request")
		doc.update({"construction_management": self.plan, "title": "ตรวจเหล็กเสริม", "wbs": "1.1", **values})
		return doc.insert()

	def test_result_after_submit_and_reinspection(self):
		doc = self.make_request()
		self.assertEqual(doc.item_name, "งานฐานราก")
		doc.submit()
		with self.assertRaises(frappe.ValidationError):
			make_reinspection(doc.name)

		doc.result = "Failed"
		doc.save()
		self.assertTrue(doc.inspected_on)

		again = make_reinspection(doc.name)
		self.assertEqual(again.reinspection_of, doc.name)
		self.assertEqual(again.wbs, "1.1")
		again.insert()

	def test_group_wbs_not_allowed(self):
		with self.assertRaises(frappe.ValidationError):
			self.make_request(wbs="1")
