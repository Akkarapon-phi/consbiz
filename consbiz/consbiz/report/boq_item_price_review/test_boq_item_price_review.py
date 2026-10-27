# Copyright (c) 2026, Siricons and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase

from consbiz.consbiz.report.boq_item_price_review.boq_item_price_review import execute, update_standard_rates

EXTRA_TEST_RECORD_DEPENDENCIES = []
IGNORE_TEST_RECORD_DEPENDENCIES = ["UOM", "BOQ Item Group", "BOQ Item", "BOQ", "Customer", "Company"]


class IntegrationTestBOQItemPriceReview(IntegrationTestCase):
	def make_item(self, **values):
		item = frappe.get_doc({"doctype": "BOQ Item", "naming_series": "Q.####", **values})
		return item.insert(ignore_links=True, ignore_mandatory=True)

	def make_boq(self, date, rows, submit=True):
		boq = frappe.new_doc("BOQ")
		boq.date = date
		for row in rows:
			boq.append("boq_details", {"quantity": 1, **row})
		boq.insert(ignore_links=True, ignore_mandatory=True)
		if submit:
			boq.submit()
		return boq

	def report(self, **filters):
		filters = {"from_date": "2026-01-01", "to_date": "2026-12-31", **filters}
		return execute(filters)[1]

	def test_review_and_update(self):
		item = self.make_item(item_name="ทดสอบทบทวนราคา", material_rate=100, labour_rate=20)
		code = item.name
		# มัธยฐานค่าวัสดุ = 120 (ใบที่ 999 ไม่ดึงค่า) / ค่าแรงตรงมาตรฐาน / ใบ Draft ไม่นับ
		self.make_boq("2026-02-01", [{"item_code": code, "material_rate": 110, "labour_rate": 20}])
		self.make_boq("2026-03-01", [{"item_code": code, "material_rate": 120, "labour_rate": 20}])
		self.make_boq("2026-04-01", [{"item_code": code, "material_rate": 999, "labour_rate": 20}])
		self.make_boq("2026-05-01", [{"item_code": code, "material_rate": 5000}], submit=False)
		# ราคารวม แยกค่าวัสดุ/ค่าแรงไม่ได้ ไม่นับ
		self.make_boq("2026-06-01", [{"item_code": code, "material_rate": 7000, "combined_rate": 1}])

		rows = {row["rate_field"]: row for row in self.report() if row["item_code"] == code}
		material, labour = rows["material_rate"], rows["labour_rate"]
		self.assertEqual((material["boq_count"], material["median_rate"]), (3, 120))
		self.assertEqual((material["min_rate"], material["max_rate"], material["last_rate"]), (110, 999, 999))
		self.assertAlmostEqual(material["diff_percent"], 20)
		self.assertEqual(material["status_color"], "orange")
		self.assertEqual(labour["status_color"], "green")

		# BOQ น้อยกว่าเกณฑ์ = ข้อมูลน้อย และกรองเฉพาะที่ควรทบทวน
		few = {r["rate_field"]: r for r in self.report(min_boq=5) if r["item_code"] == code}
		self.assertEqual(few["material_rate"]["status_color"], "gray")
		only = [r["rate_field"] for r in self.report(only_review=1) if r["item_code"] == code]
		self.assertEqual(only, ["material_rate"])
		# รวม Draft ด้วย
		draft = {r["rate_field"]: r for r in self.report(include_draft=1) if r["item_code"] == code}
		self.assertEqual(draft["material_rate"]["boq_count"], 4)

		updates = [{"item_code": code, "rate_field": "material_rate", "rate": 120}]
		self.assertEqual(update_standard_rates(updates), 1)
		self.assertEqual(frappe.db.get_value("BOQ Item", code, "material_rate"), 120)
		with self.assertRaises(frappe.ValidationError):
			update_standard_rates([{"item_code": code, "rate_field": "item_name", "rate": 1}])
		with self.assertRaises(frappe.ValidationError):
			update_standard_rates([{"item_code": code, "rate_field": "labour_rate", "rate": -1}])
