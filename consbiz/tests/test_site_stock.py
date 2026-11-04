# Copyright (c) 2026, Siricons and Contributors
# See license.txt

# สต็อกหน้างาน (consbiz/site_stock.py): คลังวัสดุผู้ว่าจ้าง, เบิกตัดคลังผู้ว่าจ้างก่อน

from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from consbiz.employer_supplied import employer_item
from consbiz.site_stock import (
	COMPANY_FIRST,
	ensure_project_warehouse,
	project_warehouse,
	split_employer_stock,
	split_qty,
	validate_warehouses,
)
from consbiz.tests.test_employer_supplied import make_item

IGNORE_TEST_RECORD_DEPENDENCIES = ["Item", "Item Group", "UOM", "Company", "Warehouse", "Project"]

MODULE = "consbiz.site_stock"
OWNER_WH = "_Test Owner Store - X"
COMPANY_WH = "_Test Site Store - X"


class IntegrationTestSiteStock(IntegrationTestCase):
	def setUp(self):
		self.base = make_item()
		self.twin = employer_item(self.base.name)

	def issue(self, *rows):
		entry = frappe.new_doc("Stock Entry")
		entry.purpose = "Material Issue"
		entry.company = "_Test Company"
		entry.project = "_Test Project"
		for row in rows:
			entry.append("items", {"s_warehouse": COMPANY_WH, "conversion_factor": 1, "uom": "Nos", **row})
		return entry

	def split(self, entry, stock, priority="Employer First", owners=(OWNER_WH,)):
		"""stock: {(item_code, warehouse): actual_qty}"""
		with (
			patch(f"{MODULE}.project_owner_warehouses", return_value=list(owners)),
			patch(f"{MODULE}.owner_warehouses", side_effect=lambda names: {n for n in names if n == OWNER_WH}),
			patch(f"{MODULE}.actual_qty", side_effect=lambda item, wh: stock.get((item, wh), 0)),
			patch(f"{MODULE}.issue_priority", return_value=priority),
			patch(f"{MODULE}.row_project", return_value="_Test Project"),
		):
			split_employer_stock(entry)
		return [(row.item_code, row.s_warehouse, row.qty) for row in entry.items]

	def test_split_qty(self):
		self.assertEqual(split_qty(10, [("a", 4), ("b", 3)], "c"), [("a", 4), ("b", 3), ("c", 3)])
		self.assertEqual(split_qty(5, [("a", 8)], "c"), [("a", 5)])
		# fallback อยู่ใน sources: ได้ทั้งส่วนของตัวเองและส่วนที่เหลือ / ของติดลบนับเป็น 0
		self.assertEqual(split_qty(10, [("c", 4), ("a", -2)], "c"), [("c", 10)])

	def test_issue_takes_employer_stock_first(self):
		entry = self.issue({"item_code": self.base.name, "qty": 10})
		rows = self.split(entry, {(self.twin, OWNER_WH): 6, (self.base.name, COMPANY_WH): 20})
		self.assertEqual(rows, [(self.twin, OWNER_WH, 6), (self.base.name, COMPANY_WH, 4)])
		self.assertTrue(all(row.custom_employer_checked for row in entry.items))
		self.assertEqual(entry.items[0].allow_zero_valuation_rate, 1)

		# บันทึกซ้ำไม่แยกอีก
		self.assertEqual(self.split(entry, {(self.twin, OWNER_WH): 6}), rows)

	def test_issue_all_from_employer_stock(self):
		entry = self.issue({"item_code": self.base.name, "qty": 5})
		self.assertEqual(self.split(entry, {(self.twin, OWNER_WH): 6}), [(self.twin, OWNER_WH, 5)])

	def test_issue_company_first(self):
		entry = self.issue({"item_code": self.base.name, "qty": 10})
		rows = self.split(entry, {(self.twin, OWNER_WH): 6, (self.base.name, COMPANY_WH): 7}, priority=COMPANY_FIRST)
		self.assertEqual(rows, [(self.base.name, COMPANY_WH, 7), (self.twin, OWNER_WH, 3)])

	def test_issue_counts_other_rows(self):
		# สองแถวของ Item เดียวกัน ของผู้ว่าจ้างมี 6: แถวแรกใช้หมด แถวที่สองตัดคลังบริษัททั้งหมด
		entry = self.issue({"item_code": self.base.name, "qty": 6}, {"item_code": self.base.name, "qty": 2})
		rows = self.split(entry, {(self.twin, OWNER_WH): 6})
		self.assertEqual(rows, [(self.twin, OWNER_WH, 6), (self.base.name, COMPANY_WH, 2)])

	def test_receipt_only_issue_is_split(self):
		entry = self.issue({"item_code": self.base.name, "qty": 3})
		entry.purpose = "Material Receipt"
		self.assertEqual(self.split(entry, {(self.twin, OWNER_WH): 6}), [(self.base.name, COMPANY_WH, 3)])

	def test_warehouse_owner_rules(self):
		def receipt(item_code, warehouse):
			entry = frappe.new_doc("Stock Entry")
			entry.purpose = "Material Receipt"
			entry.append("items", {"item_code": item_code, "t_warehouse": warehouse})
			return entry

		with patch(f"{MODULE}.owner_warehouses", side_effect=lambda names: {n for n in names if n == OWNER_WH}):
			validate_warehouses(receipt(self.twin, OWNER_WH))
			validate_warehouses(receipt(self.base.name, COMPANY_WH))
			# 1 คลังต่อโครงการ: ของผู้ว่าจ้างจัดหาอยู่คลังเดียวกับของบริษัทได้ (แยกด้วย Item คู่)
			validate_warehouses(receipt(self.twin, COMPANY_WH))
			with self.assertRaises(frappe.ValidationError):
				validate_warehouses(receipt(self.base.name, OWNER_WH))

	def test_issue_takes_employer_item_in_same_warehouse(self):
		# ไม่มีคลังผู้ว่าจ้างแยก: Item คู่อยู่คลังเดียวกัน ตัดก่อน
		entry = self.issue({"item_code": self.base.name, "qty": 10})
		rows = self.split(entry, {(self.twin, COMPANY_WH): 4}, owners=[])
		self.assertEqual(rows, [(self.twin, COMPANY_WH, 4), (self.base.name, COMPANY_WH, 6)])

	def test_project_warehouse_created_once(self):
		company = frappe.db.get_value("Company", {}, "name")
		if not company:
			self.skipTest("ไซต์ทดสอบไม่มีบริษัท")
		project = frappe.get_doc({"doctype": "Project", "project_name": "_Test Site Stock Project", "company": company}).insert()
		warehouse = project_warehouse(project.name)
		self.assertTrue(warehouse)
		parent = frappe.db.get_value("Warehouse", warehouse, "parent_warehouse")
		self.assertIn(frappe.db.get_value("Warehouse", parent, "warehouse_name"), ("โครงการ", "Project", "Projects"))
		self.assertEqual(ensure_project_warehouse(project), warehouse)
		self.assertEqual(frappe.db.get_value("Warehouse", warehouse, "warehouse_name"), "_Test Site Stock Project")

		# ตั้งชื่อคลังเอง / ชื่อซ้ำกับคลังที่มีอยู่บันทึกไม่ได้ (แก้ชื่อคลังภายหลังไม่ได้)
		named = frappe.get_doc(
			{"doctype": "Project", "project_name": "_Test Named Project", "company": company, "custom_warehouse_name": "_Test Site A"}
		).insert()
		self.assertEqual(frappe.db.get_value("Warehouse", project_warehouse(named.name), "warehouse_name"), "_Test Site A")
		with self.assertRaises(frappe.ValidationError):
			frappe.get_doc(
				{"doctype": "Project", "project_name": "_Test Other", "company": company, "custom_warehouse_name": "_Test Site A"}
			).insert()
