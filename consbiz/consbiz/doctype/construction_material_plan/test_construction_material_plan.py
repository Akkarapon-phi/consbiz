# Copyright (c) 2026, Siricons and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import getdate

from consbiz.consbiz.doctype.construction_management.construction_management import create_from_boq, save_tasks
from consbiz.consbiz.doctype.construction_management.resources import get_overview
from consbiz.consbiz.doctype.construction_material_plan.construction_material_plan import (
	allocate,
	build_material_requests,
	due_lines,
	empty_supply,
	set_item_project,
	with_totals,
)

EXTRA_TEST_RECORD_DEPENDENCIES = []
IGNORE_TEST_RECORD_DEPENDENCIES = [
	"Construction Management",
	"Item",
	"Warehouse",
	"BOQ",
	"Customer",
	"Company",
	"Holiday List",
	"UOM",
	"Project",
]

MODULE = "consbiz.consbiz.doctype.construction_material_plan.construction_material_plan"


def supply_of(purchase=None, customer=None):
	"""ยอดของ Item เดียว เช่น supply_of(purchase={"requested": 5})"""
	supply = empty_supply()
	supply["purchase"].update(purchase or {})
	supply["customer"].update(customer or {})
	return with_totals(supply)


class IntegrationTestConstructionMaterialPlan(IntegrationTestCase):
	def setUp(self):
		boq = frappe.new_doc("BOQ")
		boq.naming_series = frappe.get_meta("BOQ").get_field("naming_series").options.split("\n")[0]
		boq.date = "2026-11-02"
		for row in (
			{"wbs": "1", "item_name": "หมวด", "quantity": 0},
			{"wbs": "1.1", "item_name": "งานฐานราก", "quantity": 10, "total_amount": 3000},
		):
			boq.append("boq_details", row)
		boq.insert()
		self.plan = create_from_boq(boq.name)
		self.task = frappe.get_doc("Construction Management", self.plan).tasks[1]
		self.set_start("2026-11-20")

	def set_start(self, start):
		save_tasks(
			self.plan,
			frappe.as_json([{"name": self.task.name, "start_date": start, "end_date": start}]),
			str(frappe.db.get_value("Construction Management", self.plan, "modified")),
		)

	def make_plan(self, **row):
		doc = frappe.new_doc("Construction Material Plan")
		doc.construction_management = self.plan
		doc.buffer_days = 3
		doc.append("items", {"wbs": "1.1", "item_code": "_Test Item", "qty": 5, "lead_time_days": 7, **row})
		doc.flags.ignore_links = True
		return doc.insert()

	def test_dates_follow_plan(self):
		doc = self.make_plan()
		self.assertEqual(getdate(doc.items[0].required_by), getdate("2026-11-17"))
		self.assertEqual(getdate(doc.items[0].order_by), getdate("2026-11-10"))

		# เลื่อนงานในแผน วันที่ต้องสั่งเลื่อนตาม
		self.set_start("2026-11-25")
		doc.reload()
		self.assertEqual(getdate(doc.items[0].order_by), getdate("2026-11-15"))

	def test_due_lines_and_request(self):
		doc = self.make_plan()
		with patch(f"{MODULE}.nowdate", return_value="2026-11-01"):
			self.assertEqual(due_lines(doc, 5), [])
			(line,) = due_lines(doc, 9)
			(request,) = build_material_requests(doc, [line])
		self.assertEqual(request.material_request_type, "Purchase")
		self.assertEqual(request.items[0].qty, 5)
		self.assertEqual(getdate(request.items[0].schedule_date), getdate("2026-11-17"))
		self.assertEqual(request.custom_project, doc.project)

		# ขอแล้ว 3 จาก 5 (MR จากที่ไหนก็ได้ของโครงการ): สั่งเพิ่มเฉพาะที่ขาด / ขอครบแล้วไม่ต้องสั่ง
		with patch(f"{MODULE}.nowdate", return_value="2026-11-01"):
			with patch(f"{MODULE}.get_supply", return_value={"_Test Item": supply_of({"requested": 3})}):
				self.assertEqual(due_lines(doc, 9)[0]["stock_qty"], 2)
			with patch(f"{MODULE}.get_supply", return_value={"_Test Item": supply_of({"ordered": 5})}):
				self.assertEqual(due_lines(doc, 30), [])

	def test_allocate_earliest_first(self):
		# MR ล็อตเดียว 150 ตัดให้งานที่ต้องการก่อนก่อน
		rows = [
			{"key": "c", "item_code": "CEM", "stock_qty": 70, "required_by": "2027-01-10"},
			{"key": "a", "item_code": "CEM", "stock_qty": 50, "required_by": "2026-12-01"},
			{"key": "b", "item_code": "CEM", "stock_qty": 80, "required_by": "2026-12-15"},
			{"key": "d", "item_code": "SAND", "stock_qty": 10, "required_by": None},
		]
		result = allocate(rows, {"CEM": supply_of({"requested": 150, "received": 50})})
		self.assertEqual([result[k]["state"] for k in "abcd"], ["received", "requested", "partial", "none"])
		self.assertEqual((result["b"]["received"], result["c"]["requested"]), (0, 20))

	def test_supply_totals_and_sources(self):
		# สั่งซื้อตรง (ไม่มี MR) ก็นับว่าขอแล้ว, ของลูกค้าจัดหานับรวมแต่แยกแหล่งไว้
		supply = supply_of({"ordered": 30, "received": 10}, {"requested": 20, "received": 5})
		self.assertEqual(supply["purchase"]["requested"], 30)
		self.assertEqual(supply["customer"]["ordered"], 20)
		self.assertEqual(supply["total"], {"requested": 50, "ordered": 50, "received": 15})

	def test_customer_provided_request(self):
		doc = self.make_plan()
		line = {"item_code": "_Test Item", "stock_qty": 4, "required_by": "2026-11-17", "rows": doc.items}
		provided = [frappe._dict(name="_Test Item", stock_uom="Nos", is_customer_provided_item=1)]
		with patch(f"{MODULE}.item_info", return_value={p.name: p for p in provided}):
			with patch(f"{MODULE}.customer_of", return_value="_Test Customer"):
				(request,) = build_material_requests(doc, [line])
		self.assertEqual((request.material_request_type, request.customer), ("Customer Provided", "_Test Customer"))

	def test_employer_supplied_row_uses_employer_item(self):
		from consbiz.tests.test_employer_supplied import make_item

		base = make_item()
		doc = self.make_plan(item_code=base.name, employer_supplied=1)
		row = doc.items[0]
		twin = frappe.get_doc("Item", row.item_code)
		self.assertEqual((twin.custom_base_item, twin.is_customer_provided_item), (base.name, 1))

		# เอาติ๊กออกจากแถวเดิม = กลับเป็น Item หลัก, แถวใหม่ที่เลือก Item คู่มาเลย = ติ๊กให้เอง
		row.employer_supplied = 0
		doc.append("items", {"wbs": "1.1", "item_code": twin.name, "qty": 1})
		doc.save()
		self.assertEqual([(r.item_code, r.employer_supplied) for r in doc.items], [(base.name, 0), (twin.name, 1)])

	def test_item_project_from_header(self):
		request = frappe.new_doc("Material Request")
		request.custom_project = "PROJ-TEST"
		request.append("items", {"item_code": "_Test Item"})
		request.append("items", {"item_code": "_Test Item", "project": "OTHER"})
		set_item_project(request)
		self.assertEqual([row.project for row in request.items], ["PROJ-TEST", "OTHER"])

	def test_request_skips_missing_user_link(self):
		# ช่อง Link ที่ค่าเริ่มต้นเป็น __user แต่ผู้ใช้ไม่มีเอกสารปลายทาง ต้องว่าง ไม่งั้น insert ไม่ผ่าน
		doc = self.make_plan()
		(request,) = build_material_requests(
			doc, [{"item_code": "_Test Item", "stock_qty": 5, "required_by": doc.items[0].required_by, "rows": doc.items}]
		)
		for df in request.meta.get_link_fields():
			if df.default == "__user" and request.get(df.fieldname):
				self.assertTrue(frappe.db.exists(df.options, request.get(df.fieldname)))

	def test_late_required_by_uses_today(self):
		doc = self.make_plan()
		with patch(f"{MODULE}.nowdate", return_value="2026-11-20"):
			(request,) = build_material_requests(
				doc, [{"item_code": "_Test Item", "stock_qty": 5, "required_by": doc.items[0].required_by, "rows": doc.items}]
			)
		self.assertEqual(getdate(request.items[0].schedule_date), getdate("2026-11-20"))

	def test_validation(self):
		with self.assertRaises(frappe.ValidationError):
			self.make_plan(wbs="1")
		with self.assertRaises(frappe.ValidationError):
			self.make_plan(qty=0)

	def test_save_from_gantt_edits_requested_rows(self):
		doc = self.make_plan()
		doc.append("items", {"wbs": "1.1", "item_code": "_Test Item", "qty": 2, "lead_time_days": 1})
		doc.flags.ignore_links = True
		doc.save()
		ordered, other = doc.items
		ordered.db_set("material_request", "MAT-MR-TEST")

		# สถานะคิดจากปริมาณ แถวที่เคยสร้าง MR แก้/ลบได้ เลข MR คงไว้อ้างอิง
		# (ข้ามการตรวจ Link เพราะ Item / Material Request ในเทสต์ไม่มีอยู่จริง)
		with patch("frappe.model.document.Document._validate_links"):
			self.save_with_materials(doc, [{**ordered.as_dict(), "qty": 9}])
		doc.reload()
		self.assertEqual([(r.name, r.qty, r.material_request) for r in doc.items], [(ordered.name, 9, "MAT-MR-TEST")])
		self.assertFalse(frappe.db.exists(other.doctype, other.name))

	def save_with_materials(self, doc, items):
		save_tasks(
			self.plan,
			"[]",
			str(frappe.db.get_value("Construction Management", self.plan, "modified")),
			materials=frappe.as_json(
				{"modified": str(frappe.db.get_value(doc.doctype, doc.name, "modified")), "items": items}
			),
		)

	def test_overview(self):
		doc = self.make_plan()
		# งานเริ่ม 20 พ.ย. buffer 3 lead 7 = ต้องสั่ง 10 พ.ย.
		(row,) = get_overview(self.plan, day="2026-11-01")["materials"]
		self.assertEqual((getdate(row["order_by"]), row["days_left"], row["status"]), (getdate("2026-11-10"), 9, "due"))
		self.assertEqual(get_overview(self.plan, day="2026-11-11")["materials"][0]["status"], "late")
		with patch(f"{MODULE}.get_supply", return_value={"_Test Item": supply_of({"requested": 5})}):
			overview = get_overview(self.plan, day="2026-11-11")
		self.assertEqual(overview["materials"][0]["status"], "done")
		self.assertEqual(overview["materials"][0]["coverage"]["state"], "requested")
