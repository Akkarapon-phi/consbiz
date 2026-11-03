# Copyright (c) 2026, Siricons and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from consbiz.consbiz.doctype.construction_management.construction_management import (
	create_from_boq,
	save_tasks,
)
from consbiz.consbiz.doctype.construction_management.evm import evm_at, indices
from consbiz.consbiz.report.construction_earned_value.construction_earned_value import execute

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

EVM = "consbiz.consbiz.doctype.construction_management.evm"


class IntegrationTestConstructionEarnedValue(IntegrationTestCase):
	def setUp(self):
		boq = frappe.new_doc("BOQ")
		boq.naming_series = frappe.get_meta("BOQ").get_field("naming_series").options.split("\n")[0]
		boq.date = "2026-11-02"
		for row in (
			{"wbs": "1", "item_name": "หมวด", "quantity": 0},
			{"wbs": "1.1", "item_name": "งานมีปริมาณ", "quantity": 10, "total_amount": 3000},
			{"wbs": "1.2", "item_name": "งานเหมา", "quantity": 0, "total_amount": 1000},
		):
			boq.append("boq_details", row)
		boq.insert()
		self.plan = create_from_boq(boq.name)
		doc = frappe.get_doc("Construction Management", self.plan)
		doc.start_date = "2026-11-02"
		doc.save()
		_group, a, b = doc.tasks
		# 1.1 = 2-11 พ.ย. (10 วัน), 1.2 = 12-21 พ.ย. ณ 6 พ.ย. แผน 75% x 50% = 37.5%
		save_tasks(
			self.plan,
			frappe.as_json(
				[
					{"name": a.name, "start_date": "2026-11-02", "end_date": "2026-11-11"},
					{"name": b.name, "start_date": "2026-11-12", "end_date": "2026-11-21"},
				]
			),
			str(frappe.db.get_value("Construction Management", self.plan, "modified")),
			# ทำได้ 4 จาก 10 = 75% x 40% = 30%
			frappe.as_json([{"task": a.name, "date": "2026-11-06", "qty": 4}]),
		)

	def get_doc(self):
		return frappe.get_doc("Construction Management", self.plan)

	def test_values_from_contract_amount(self):
		with patch(f"{EVM}.actual_cost", return_value=1000):
			values = evm_at(self.get_doc(), "2026-11-06")
		self.assertEqual(values.bac, 4000)
		self.assertAlmostEqual(values.pv, 1500)
		self.assertAlmostEqual(values.ev, 1200)
		self.assertAlmostEqual(values.spi, 0.8)
		self.assertAlmostEqual(values.cpi, 1.2)
		self.assertAlmostEqual(values.eac, 4000 / 1.2)

	def test_budget_cost_is_bac(self):
		frappe.db.set_value("Construction Management", self.plan, "budget_cost", 3000)
		with patch(f"{EVM}.actual_cost", return_value=1000):
			values = evm_at(self.get_doc(), "2026-11-06")
		self.assertAlmostEqual(values.ev, 900)
		self.assertAlmostEqual(values.cpi, 0.9)
		self.assertAlmostEqual(values.tcpi, 2100 / 2000)

	def test_no_cost_yet(self):
		values = indices(date=None, bac=100, pv=0, ev=0, ac=0, plan=0, actual=0)
		self.assertIsNone(values["spi"])
		self.assertIsNone(values["cpi"])
		self.assertIsNone(values["eac"])

	def test_report_series(self):
		with patch(f"{EVM}.actual_cost", return_value=0):
			_columns, rows, message, chart, summary = execute(
				{"construction_management": self.plan, "to_date": "2026-11-20", "periodicity": "Weekly"}
			)
		# สัปดาห์ที่เริ่ม 2, 9, 16 พ.ย. ช่วงสุดท้ายจบที่ to_date
		self.assertEqual([str(row.date) for row in rows], ["2026-11-08", "2026-11-15", "2026-11-20"])
		self.assertEqual(len(chart["data"]["datasets"]), 3)
		self.assertTrue(message)
		self.assertEqual(summary[0]["label"], "SPI")
