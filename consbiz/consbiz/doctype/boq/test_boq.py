# Copyright (c) 2026, Siricons and Contributors
# See license.txt

import base64

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import getdate
from frappe.utils.xlsxutils import read_xlsx_file_from_attached_file

from consbiz.consbiz.doctype.boq.boq_excel import (
	apply_boq_matches,
	build_workbook,
	import_boq_items,
	parse_boq_rows,
)

EXTRA_TEST_RECORD_DEPENDENCIES = []
IGNORE_TEST_RECORD_DEPENDENCIES = ["Customer", "Company", "UOM", "BOQ Item", "BOQ Item Group"]


def import_rows(rows):
	"""นำเข้าโดยยอมรับการจับคู่ที่ระบบเลือกไว้ให้ (เหมือนกดนำเข้าโดยไม่แก้หน้าตรวจ)"""
	return apply_boq_matches(parse_boq_rows(rows)["items"])


class IntegrationTestBOQ(IntegrationTestCase):
	def make_item(self, **values):
		item = frappe.get_doc({"doctype": "BOQ Item", "naming_series": "Q.####", **values})
		item.insert(ignore_links=True, ignore_mandatory=True)
		return item

	def test_totals(self):
		doc = frappe.new_doc("BOQ")
		doc.append("boq_details", {"quantity": 2, "material_rate": 100, "labour_rate": 30})
		doc.append("boq_details", {"quantity": 1.5, "material_rate": 10})
		doc.run_method("validate")

		self.assertEqual(doc.boq_details[0].total_amount, 260)
		self.assertEqual(doc.boq_details[1].material_amount, 15)
		self.assertEqual(doc.total_material_cost, 215)
		self.assertEqual(doc.total_labour_cost, 60)
		self.assertEqual(doc.grand_total, 275)

	def test_parse_rows(self):
		item = self.make_item(item_name="คอนกรีต 240 ksc", material_rate=2000, labour_rate=300)
		rows = [
			["บัญชีแสดงปริมาณวัสดุและราคา (BOQ)"],
			["ลูกค้า", None, None, "เลขที่ BOQ", None],
			["โครงการ:", "อาคาร 3 ชั้น", None, "วันที่", "2026-11-02"],
			[" WBS ", "Item Code", "Item Name", "Quantity", "Material Rate", "ไม่รู้จัก"],
			["1", None, "งานโครงสร้าง", None, None, "x"],
			["1.1", item.name, None, "1,000", None],
			["1.2", item.name, "ชื่อแก้เอง", 2, 1500],
			[None, "", "", None, None],
			[None, None, "รวมทั้งสิ้น", None, 99],
			["9", None, "หลังแถวรวม ต้องไม่ถูกนำเข้า"],
		]

		result = parse_boq_rows(rows)
		# ช่องลูกค้าว่าง ต้องไม่อ่านป้าย "เลขที่ BOQ" เป็นชื่อลูกค้า
		self.assertEqual(result["info"], {"project": "อาคาร 3 ชั้น", "date": getdate("2026-11-02")})
		self.assertEqual([i["match"] for i in result["items"]], ["heading", "exact", "exact"])
		rows = apply_boq_matches(result["items"])
		self.assertEqual(len(rows), 3)
		self.assertEqual(rows[0].item_name, "งานโครงสร้าง")
		self.assertEqual(rows[0].total_amount, 0)
		self.assertEqual(rows[1].item_name, "คอนกรีต 240 ksc")
		self.assertEqual(rows[1].quantity, 1000)
		self.assertEqual(rows[1].total_amount, 2300000)
		self.assertEqual(rows[2].item_name, "ชื่อแก้เอง")
		self.assertEqual(rows[2].material_rate, 1500)
		self.assertEqual(rows[2].labour_rate, 300)

	def test_two_row_header(self):
		# รูปแบบเดียวกับแบบฟอร์ม BOQ: หัวกลุ่มรวมเซลล์ อ่านได้แค่ช่องแรก ช่องถัดไปเป็น None
		rows = [
			["BILL OF QUANTITIES"],
			["ใบแสดงปริมาณงานและราคา (BOQ)", None, None, None, None, "บริษัท", None],
			["โครงการ :", "บ้านพักอาศัย", None, "ลูกค้า :", None, None, None, "เลขที่ :", None],
			["สถานที่ :", "ขอนแก่น", None, None, None, None, None, "วันที่ :", None],
			["ลำดับที่\n(WBS)", "รายการ", "จำนวน", "หน่วย", "ค่าวัสดุ", None, "ค่าแรง", None, "รวมค่าวัสดุและค่าแรง"],
			[None, None, None, None, "ราคาต่อหน่วย", "จำนวนเงิน", "ราคาต่อหน่วย", "จำนวนเงิน", None],
			["1", "เทคอนกรีต", 3, None, 100, 999, 20, 999, 999],
		]

		self.assertEqual(parse_boq_rows(rows)["info"], {"project": "บ้านพักอาศัย", "location": "ขอนแก่น"})
		row = import_rows(rows)[0]
		self.assertEqual((row.wbs, row.quantity, row.material_rate, row.labour_rate), ("1", 3, 100, 20))
		# ยอดเงินคำนวณใหม่ ไม่ใช้ค่าในไฟล์
		self.assertEqual(row.total_amount, 360)

	def test_match_item_by_name(self):
		item = self.make_item(item_name="ทดสอบจับคู่ชื่อ BOQ", material_rate=50, labour_rate=5)
		concrete = self.make_item(item_name="คอนกรีตทดสอบจับคู่ 240 ksc")
		header = ["รายการ", "จำนวน", "ค่าวัสดุ/หน่วย"]
		items = parse_boq_rows(
			[
				header,
				["ทดสอบจับคู่ชื่อ  boq", 2, 70],  # ต่างแค่ช่องว่าง/ตัวพิมพ์ = ตรงกันพอดี
				["คอนกรีต ทดสอบจับคู่ 240", 1, 1],  # ใกล้เคียง เลือกไว้ให้
				["คอนกรีตทดสอบจับคู่ 280 ksc", 1, 1],  # ต่างแค่ตัวเลข ไม่เลือกให้
			]
		)["items"]

		self.assertEqual((items[0]["match"], items[0]["item_code"]), ("exact", item.name))
		self.assertEqual((items[1]["match"], items[1]["item_code"]), ("suggest", concrete.name))
		self.assertEqual((items[2]["match"], items[2]["item_code"]), ("suggest", None))
		self.assertTrue(items[2]["suggestions"][0]["number_conflict"])

		row = apply_boq_matches(items[:1])[0]
		# ราคาใน Excel เป็นหลัก ช่องที่ไฟล์ว่างใช้ราคามาตรฐาน
		self.assertEqual((row.material_rate, row.labour_rate, row.total_amount), (70, 5, 150))

	def test_create_item_on_import(self):
		entry = {"row": {"item_name": "รายการใหม่จาก Excel", "uom": None, "material_rate": 30}, "create": 1}
		rows = apply_boq_matches([entry, entry])
		self.assertTrue(rows[0].item_code)
		self.assertEqual(rows[0].item_code, rows[1].item_code)  # ชื่อซ้ำสร้างครั้งเดียว
		self.assertEqual(frappe.db.get_value("BOQ Item", rows[0].item_code, "material_rate"), 30)

	def test_parse_rows_errors(self):
		with self.assertRaises(frappe.ValidationError):
			parse_boq_rows([["WBS", "Quantity"], ["1", 2]])
		# รหัสที่ไม่มีในระบบ ไม่ error แต่ให้ผู้ใช้ตรวจในหน้าจับคู่
		item = parse_boq_rows([["Item Code", "Quantity"], ["ไม่มีรหัสนี้", 2]])["items"][0]
		self.assertEqual(item["match"], "none")
		self.assertTrue(item["note"])

	def test_unknown_customer_is_warning(self):
		result = parse_boq_rows([["ลูกค้า", "ไม่มีลูกค้ารายนี้"], ["Item Name"], ["งานดิน"]])
		self.assertNotIn("customer", result["info"])
		self.assertEqual(len(result["warnings"]), 1)
		self.assertEqual(len(result["items"]), 1)

	def test_export_round_trip(self):
		self.make_item(item_name="เหล็ก DB12", material_rate=25)
		doc = frappe.new_doc("BOQ")
		doc.project = "บ้านพักอาศัย"
		doc.location = "ขอนแก่น"
		doc.date = "2026-11-02"
		doc.append("boq_details", {"wbs": "1", "item_name": "งานโครงสร้าง"})
		doc.append(
			"boq_details",
			{"wbs": "1.1", "item_name": "เทคอนกรีต", "quantity": 3, "material_rate": 100, "labour_rate": 20},
		)
		doc.run_method("validate")

		result = parse_boq_rows(read_xlsx_file_from_attached_file(fcontent=build_workbook(doc)))
		expected = {"project": "บ้านพักอาศัย", "location": "ขอนแก่น", "date": getdate("2026-11-02")}
		if doc.company:  # new_doc ใส่บริษัทเริ่มต้นของผู้ใช้ให้
			expected["company"] = doc.company
		self.assertEqual(result["info"], expected)
		rows = apply_boq_matches(result["items"])
		self.assertEqual([r.item_name for r in rows], ["งานโครงสร้าง", "เทคอนกรีต"])
		self.assertEqual(rows[1].total_amount, 360)

		# แม่แบบเปล่ามีแถวเตรียมกรอกพร้อมสูตร แต่อ่านกลับมาต้องไม่มีรายการ
		blank = parse_boq_rows(read_xlsx_file_from_attached_file(fcontent=build_workbook()))
		self.assertEqual(blank["items"], [])

	def test_import_from_content(self):
		doc = frappe.new_doc("BOQ")
		doc.append("boq_details", {"wbs": "1", "item_name": "งานดิน", "quantity": 2, "material_rate": 50})
		content = base64.b64encode(build_workbook(doc)).decode()
		result = import_boq_items("BOQ Template.xlsx", content)
		self.assertEqual([i["row"]["item_name"] for i in result["items"]], ["งานดิน"])
		# ไม่สร้าง File
		self.assertFalse(frappe.db.exists("File", {"file_name": "BOQ Template.xlsx"}))

		with self.assertRaises(frappe.ValidationError):
			import_boq_items("เสีย.xlsx", base64.b64encode(b"not an excel file").decode())
		with self.assertRaises(frappe.ValidationError):
			import_boq_items("รูป.png", content)
