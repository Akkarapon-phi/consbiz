# Copyright (c) 2026, Siricons and Contributors
# See license.txt

# วัสดุผู้ว่าจ้างจัดหา (consbiz/employer_supplied.py): Item คู่ และ Material Request ประเภท Customer Provided

import frappe
from frappe.tests import IntegrationTestCase

from consbiz.employer_supplied import (
	SUFFIX,
	base_item,
	employer_item,
	employer_series,
	set_request_series,
	swap_request_items,
)

ITEM_GROUP = "_Test Employer Supplied Group"


def make_item(item_name="_Test Base Rebar", **values):
	"""Item หลักสำหรับเทสต์ (สร้างกลุ่ม/หน่วยที่ต้องใช้ถ้าไซต์ยังไม่มี)"""
	if not frappe.db.exists("UOM", "Nos"):
		frappe.get_doc({"doctype": "UOM", "uom_name": "Nos"}).insert()
	if not frappe.db.exists("UOM", "_Test Bundle"):
		frappe.get_doc({"doctype": "UOM", "uom_name": "_Test Bundle"}).insert()
	if not frappe.db.exists("Item Group", ITEM_GROUP):
		frappe.get_doc({"doctype": "Item Group", "item_group_name": ITEM_GROUP, "is_group": 0}).insert()
	item = frappe.new_doc("Item")
	item.update(
		{
			"item_code": frappe.generate_hash(length=10),
			"item_name": item_name,
			"item_group": ITEM_GROUP,
			"stock_uom": "Nos",
			"is_stock_item": 1,
			"is_purchase_item": 1,
			**values,
		}
	)
	item.append("uoms", {"uom": "_Test Bundle", "conversion_factor": 10})
	return item.insert()


class IntegrationTestEmployerSupplied(IntegrationTestCase):
	def test_create_and_reuse_employer_item(self):
		base = make_item()
		code = employer_item(base.name)
		twin = frappe.get_doc("Item", code)
		self.assertEqual(twin.custom_base_item, base.name)
		self.assertEqual(twin.item_name, base.item_name + SUFFIX)
		self.assertEqual(
			(twin.is_customer_provided_item, twin.is_purchase_item, twin.is_sales_item), (1, 0, 0)
		)
		self.assertEqual((twin.item_group, twin.stock_uom), (base.item_group, base.stock_uom))
		self.assertIn(("_Test Bundle", 10), [(r.uom, r.conversion_factor) for r in twin.uoms])

		# เรียกซ้ำได้ตัวเดิม, Item คู่เรียกได้ตัวเอง, กลับเป็น Item หลักได้
		self.assertEqual(employer_item(base.name), code)
		self.assertEqual(employer_item(code), code)
		self.assertEqual((base_item(code), base_item(base.name)), (base.name, base.name))

	def test_employer_item_follows_base(self):
		base = make_item()
		code = employer_item(base.name)

		base.item_name = "_Test Renamed Rebar"
		base.description = "_Test Renamed Rebar"
		base.save()
		self.assertEqual(frappe.db.get_value("Item", code, "item_name"), "_Test Renamed Rebar" + SUFFIX)

		# แก้ที่ Item คู่ตรงๆ ถูกทับด้วยค่าของ Item หลัก
		twin = frappe.get_doc("Item", code)
		twin.item_name = "Something else"
		twin.is_purchase_item = 1
		twin.save()
		self.assertEqual((twin.item_name, twin.is_purchase_item), ("_Test Renamed Rebar" + SUFFIX, 0))

	def test_base_must_not_be_employer_item(self):
		code = employer_item(make_item().name)
		other = make_item()
		other.custom_base_item = code
		with self.assertRaises(frappe.ValidationError):
			other.save()

	def test_merge_bases_merges_employer_items(self):
		keep, gone = make_item("_Test Keep"), make_item("_Test Gone")
		keep_twin, gone_twin = employer_item(keep.name), employer_item(gone.name)

		frappe.rename_doc("Item", gone.name, keep.name, merge=True, show_alert=False)

		self.assertFalse(frappe.db.exists("Item", gone_twin))
		self.assertEqual(
			frappe.get_all("Item", filters={"custom_base_item": keep.name}, pluck="name"), [keep_twin]
		)

	def test_request_swaps_to_employer_item(self):
		base = make_item()
		request = frappe.new_doc("Material Request")
		request.material_request_type = "Customer Provided"
		request.append("items", {"item_code": base.name, "item_name": base.item_name})
		swap_request_items(request)
		code = request.items[0].item_code
		self.assertEqual(frappe.db.get_value("Item", code, "custom_base_item"), base.name)
		self.assertEqual(request.items[0].item_name, base.item_name + SUFFIX)

		# ประเภทซื้อไม่สลับ
		request = frappe.new_doc("Material Request")
		request.material_request_type = "Purchase"
		request.append("items", {"item_code": base.name})
		swap_request_items(request)
		self.assertEqual(request.items[0].item_code, base.name)

	def test_request_series(self):
		employer, default = employer_series()
		if not employer:
			self.skipTest("ไซต์นี้ไม่มีเลขชุด OPO- ของ Material Request (Property Setter ใน fixtures)")
		request = frappe.new_doc("Material Request")
		request.material_request_type = "Customer Provided"
		request.naming_series = default
		set_request_series(request)
		self.assertEqual(request.naming_series, employer)

		request.material_request_type = "Purchase"
		set_request_series(request)
		self.assertEqual(request.naming_series, default)
