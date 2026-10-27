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

	def test_auto_wbs(self):
		doc = frappe.new_doc("BOQ")
		for wbs in ["1", "1.1", "1.1.1", "1.1.1.1", "", "1.5", "7", "3.3", "", "2.9.9.9"]:
			doc.append("boq_details", {"wbs": wbs})
		doc.run_method("validate")

		# คงระดับไว้, แถวว่างใช้ระดับแถวก่อนหน้า, ลึกเกินแถวก่อนหน้า 1 ระดับถูกจำกัด
		self.assertEqual(
			[row.wbs for row in doc.boq_details],
			["1", "1.1", "1.1.1", "1.1.1.1", "1.1.1.2", "1.2", "2", "2.1", "2.2", "2.2.1"],
		)
		# รันซ้ำได้ผลเดิม และ WBS ไม่ซ้ำกัน
		doc.run_method("validate")
		self.assertEqual(len({row.wbs for row in doc.boq_details}), len(doc.boq_details))

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

	def test_combined_rate(self):
		doc = frappe.new_doc("BOQ")
		doc.append(
			"boq_details", {"quantity": 2, "material_rate": 100, "labour_rate": 30, "combined_rate": 1}
		)
		doc.append("boq_details", {"quantity": 1, "material_rate": 10, "labour_rate": 5})
		doc.run_method("validate")
		# แถวราคารวม: ค่าแรงย้ายไปรวมที่ค่าวัสดุ ยอดรวมเท่าเดิม
		row = doc.boq_details[0]
		self.assertEqual((row.material_rate, row.labour_rate, row.total_amount), (130, 0, 260))
		self.assertEqual(doc.boq_details[1].labour_rate, 5)

		# ราคารวมทั้งใบ: ติ๊กให้ทุกแถว
		doc.combined_rate = 1
		doc.run_method("validate")
		self.assertEqual([r.combined_rate for r in doc.boq_details], [1, 1])
		self.assertEqual((doc.total_material_cost, doc.total_labour_cost, doc.grand_total), (275, 0, 275))

	def test_import_combined_rate(self):
		item = self.make_item(item_name="ทดสอบราคารวม BOQ", material_rate=40, labour_rate=10)
		result = parse_boq_rows(
			[
				["ลำดับ", "รายการ", "จำนวน", "ราคาต่อหน่วย", "จำนวนเงิน"],
				["1", "งานรื้อถอน", 2, 150, 300],
				["2", "งานเหมาไม่มีจำนวน", None, None, 5000],
				["3", "งานเหมามีจำนวน", 4, None, 1000],
				["4", "ทดสอบราคารวม BOQ", 3, None, None],
			]
		)
		self.assertEqual(len(result["warnings"]), 1)
		rows = apply_boq_matches(result["items"])
		rates = [(r.combined_rate, r.quantity, r.material_rate, r.labour_rate, r.total_amount) for r in rows]
		self.assertEqual(rates[0], (1, 2, 150, 0, 300))
		self.assertEqual(rates[1], (1, 1, 5000, 0, 5000))  # ไม่มีจำนวน ถือเป็น 1 หน่วย
		self.assertEqual(rates[2], (1, 4, 250, 0, 1000))
		# ไม่มีราคาในไฟล์ จับคู่ได้ BOQ Item: ไม่ติ๊กราคารวม ใช้ราคามาตรฐานแยกตามเดิม
		self.assertEqual(rows[3].item_code, item.name)
		self.assertEqual(rates[3], (0, 3, 40, 10, 150))

	def test_combined_rate_with_item(self):
		item = self.make_item(item_name="ทดสอบราคารวมจับคู่", material_rate=40, labour_rate=10)
		base = {"item_code": item.name, "missing": ["material_rate", "labour_rate"]}
		# ติ๊กราคารวมในไฟล์แต่ไม่มีราคา: ใช้ราคามาตรฐานรวมกัน
		row = apply_boq_matches([{**base, "row": {"quantity": 2, "combined_rate": 1}}])[0]
		self.assertEqual((row.material_rate, row.labour_rate, row.total_amount), (50, 0, 100))
		# มีราคารวมในไฟล์: ไม่เติมค่าแรงมาตรฐาน
		entry = {
			**base,
			"missing": ["labour_rate"],
			"row": {"quantity": 2, "material_rate": 70, "combined_rate": 1},
		}
		row = apply_boq_matches([entry])[0]
		self.assertEqual((row.material_rate, row.labour_rate), (70, 0))

		# สร้าง BOQ Item จากแถวราคารวม: ไม่ใส่ราคามาตรฐาน
		entry = {
			"row": {"item_name": "รายการราคารวมใหม่", "material_rate": 90, "combined_rate": 1},
			"create": 1,
		}
		row = apply_boq_matches([entry])[0]
		self.assertEqual(row.material_rate, 90)
		self.assertEqual(
			frappe.db.get_value("BOQ Item", row.item_code, ["material_rate", "labour_rate"]), (0, 0)
		)

	def test_import_uom(self):
		for name in ("ตร.ม.", "Square Meter"):
			if not frappe.db.exists("UOM", name):
				frappe.get_doc({"doctype": "UOM", "uom_name": name}).insert()
		result = parse_boq_rows(
			[
				["รายการ", "จำนวน", "หน่วย"],
				["งานผนัง", 1, "ตรม"],  # ต่างแค่จุด
				["งานพื้น", 1, "sq.m"],  # ชื่อเรียกอื่น ใช้หน่วยไทยก่อน
				["งานฝ้า", 1, "square  meter"],  # ตรงกันไม่นับตัวพิมพ์/ช่องว่าง
				["งานติดตั้ง", 1, "จุดทดสอบนำเข้า"],
				["งานติดตั้งซ้ำ", 1, "จุดทดสอบนำเข้า"],
			]
		)
		uoms = [i["row"]["uom"] for i in result["items"]]
		self.assertEqual(uoms, ["ตร.ม.", "ตร.ม.", "Square Meter", "จุดทดสอบนำเข้า", "จุดทดสอบนำเข้า"])
		self.assertEqual(len(result["warnings"]), 2)  # ใช้หน่วยในระบบแทน + สร้างใหม่
		# สร้างหน่วยตอนยืนยันนำเข้า ไม่ใช่ตอนอ่านไฟล์
		self.assertFalse(frappe.db.exists("UOM", "จุดทดสอบนำเข้า"))
		rows = apply_boq_matches(result["items"])
		self.assertEqual(rows[3].uom, "จุดทดสอบนำเข้า")
		self.assertTrue(frappe.db.exists("UOM", "จุดทดสอบนำเข้า"))

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
		doc.append(
			"boq_details",
			{"wbs": "1.2", "item_name": "งานเหมา", "quantity": 1, "material_rate": 500, "combined_rate": 1},
		)
		doc.run_method("validate")

		result = parse_boq_rows(read_xlsx_file_from_attached_file(fcontent=build_workbook(doc)))
		expected = {"project": "บ้านพักอาศัย", "location": "ขอนแก่น", "date": getdate("2026-11-02")}
		if doc.company:  # new_doc ใส่บริษัทเริ่มต้นของผู้ใช้ให้
			expected["company"] = doc.company
		self.assertEqual(result["info"], expected)
		rows = apply_boq_matches(result["items"])
		self.assertEqual([r.item_name for r in rows], ["งานโครงสร้าง", "เทคอนกรีต", "งานเหมา"])
		self.assertEqual(rows[1].total_amount, 360)
		self.assertEqual([r.combined_rate for r in rows], [0, 0, 1])
		self.assertEqual((rows[2].material_rate, rows[2].labour_rate), (500, 0))

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
