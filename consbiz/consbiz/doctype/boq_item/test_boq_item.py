# Copyright (c) 2026, Siricons and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase

from consbiz.consbiz.doctype.boq_item.boq_item import get_price_history

EXTRA_TEST_RECORD_DEPENDENCIES = []
IGNORE_TEST_RECORD_DEPENDENCIES = ["UOM", "BOQ Item Group", "BOQ", "Customer", "Company"]


class IntegrationTestBOQItem(IntegrationTestCase):
	def test_price_history(self):
		item = frappe.get_doc(
			{
				"doctype": "BOQ Item",
				"naming_series": "Q.####",
				"item_name": "ทดสอบประวัติราคา",
				"material_rate": 90,
			}
		).insert(ignore_links=True, ignore_mandatory=True)
		for date, rate, cancel in (
			("2026-02-01", 110, False),
			("2026-01-01", 100, False),
			("2026-03-01", 999, True),
		):
			boq = frappe.new_doc("BOQ")
			boq.date = date
			boq.append("boq_details", {"item_code": item.name, "quantity": 1, "material_rate": rate})
			boq.insert(ignore_links=True, ignore_mandatory=True)
			if cancel:
				boq.submit()
				boq.cancel()

		data = get_price_history(item.name)
		self.assertEqual(data["material_rate"], 90)
		# เรียงจากเก่าไปใหม่ และไม่นับ BOQ ที่ยกเลิก
		self.assertEqual([row.material_rate for row in data["history"]], [100, 110])
