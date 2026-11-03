# Copyright (c) 2026, Siricons and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase

from consbiz.consbiz.doctype.inspection_request.test_inspection_request import make_plan

EXTRA_TEST_RECORD_DEPENDENCIES = []
IGNORE_TEST_RECORD_DEPENDENCIES = [
	"Construction Management",
	"Inspection Request",
	"BOQ",
	"Customer",
	"Company",
	"Holiday List",
	"UOM",
	"Project",
]


class IntegrationTestPunchList(IntegrationTestCase):
	def setUp(self):
		self.plan = make_plan()

	def make_list(self, items):
		doc = frappe.new_doc("Punch List")
		doc.update({"construction_management": self.plan, "title": "ตรวจรับงาน"})
		for item in items:
			doc.append("items", item)
		return doc.insert()

	def test_close_items_after_submit(self):
		doc = self.make_list([{"description": "รอยร้าวผนัง", "wbs": "1.1"}, {"description": "สีไม่เรียบ"}])
		self.assertEqual((doc.status, doc.open_items), ("Open", 2))
		doc.submit()

		doc.items[0].status = "Closed"
		doc.save()
		self.assertEqual(doc.open_items, 1)
		self.assertTrue(doc.items[0].closed_on)

		doc.items[1].status = "Closed"
		doc.save()
		self.assertEqual(doc.status, "Closed")

	def test_unknown_wbs(self):
		with self.assertRaises(frappe.ValidationError):
			self.make_list([{"description": "x", "wbs": "9.9"}])
