# Copyright (c) 2026, Siricons and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase

from consbiz.consbiz.doctype.bar_cut_plan.optimizer import NotEnoughStock, plan_cuts

EXTRA_TEST_RECORD_DEPENDENCIES = []
IGNORE_TEST_RECORD_DEPENDENCIES = ["Rebar Type", "Bar Shape", "Project"]


class IntegrationTestBarCutPlan(IntegrationTestCase):
	def make_plan(self, items, stock=None, **settings):
		doc = frappe.new_doc("Bar Cut Plan")
		doc.title = "test"
		doc.update(settings)
		for item in items:
			doc.append("items", item)
		for row in stock or []:
			doc.append("stock", row)
		doc.insert()
		return doc

	def test_cut_length(self):
		doc = self.make_plan(
			[
				# L: 1000 + 500 - 2d(12) = 1476 -> ปัดขึ้น 1480
				{"shape": "11", "rebar_type": "DB12", "a": 1000, "b": 500, "qty": 4},
				# ปลอก: 2(200+400) - (3x2d + 2x3d)(9) + 2x10d(9) = 1272 -> 1280
				{"shape": "51", "rebar_type": "RB9", "a": 200, "b": 400, "qty": 10},
			]
		)
		self.assertEqual([row.cut_length for row in doc.items], [1480, 1280])
		self.assertAlmostEqual(doc.items[0].total_length, 5.92)
		self.assertAlmostEqual(doc.items[0].weight, 5.92 * 0.888, places=3)

		# ไม่หักจุดดัด: ผลรวมด้าน + ขอ
		doc.use_bend_deduction = 0
		doc.save()
		self.assertEqual([row.cut_length for row in doc.items], [1500, 1380])

		with self.assertRaises(frappe.ValidationError):
			self.make_plan([{"shape": "21", "rebar_type": "DB12", "a": 500, "b": 800, "qty": 1}])

	def test_extended_shapes(self):
		for code, dimensions, formula, extra in [
			("T-SPIRAL", "A,B,N", "N*sqrt((pi*(A-d))**2+B**2)", {}),
			("T-CRANK", "A,B,C,T", "A+B/sin(T)+C", {"bends_45": 2}),
			("T-SIX", "A,B,C,D,E,F", "A+B+C+D+E+F", {"bends_90": 5}),
			("T-TIE90", "A,B", "2*(A+B)", {"bends_90": 5, "hooks_90": 2}),
		]:
			if not frappe.db.exists("Bar Shape", code):
				frappe.get_doc(
					{
						"doctype": "Bar Shape",
						"shape_code": code,
						"shape_name": code,
						"dimensions": dimensions,
						"sides_formula": formula,
						**extra,
					}
				).insert()

		doc = self.make_plan(
			[
				# 5 รอบ x sqrt((pi*(600-9))^2 + 100^2) = 5 x 1859.38 = 9296.9 -> 9300
				{"shape": "T-SPIRAL", "rebar_type": "RB9", "a": 600, "b": 100, "n": 5, "qty": 1},
				# 500 + 200/sin(30) + 500 = 1400 - 2x1d(12) = 1376 -> 1380
				{"shape": "T-CRANK", "rebar_type": "DB12", "a": 500, "b": 200, "c": 500, "t": 30, "qty": 1},
				# 100+200+...+600 = 2100 - 5x2d(12) = 1980
				{
					"shape": "T-SIX",
					"rebar_type": "DB12",
					**dict(zip("abcdef", (100, 200, 300, 400, 500, 600), strict=True)),
					"qty": 1,
				},
				# ปลอกขอ 90°: 2(200+400) - 5x2d(9) + 2x6d(9) = 1218 -> 1220
				{"shape": "T-TIE90", "rebar_type": "RB9", "a": 200, "b": 400, "qty": 1},
			]
		)
		self.assertEqual([row.cut_length for row in doc.items], [9300, 1380, 1980, 1220])

		with self.assertRaises(frappe.ValidationError):
			self.make_plan([{"shape": "T-CRANK", "rebar_type": "DB12", "a": 500, "b": 200, "c": 500, "qty": 1}])
		with self.assertRaises(frappe.ValidationError):
			frappe.get_doc(
				{
					"doctype": "Bar Shape",
					"shape_code": "T-BAD",
					"shape_name": "T-BAD",
					"dimensions": "A,G",
					"sides_formula": "A",
				}
			).insert()

	def test_optimize_totals(self):
		doc = self.make_plan(
			[
				{"mark": "C1", "shape": "00", "rebar_type": "DB16", "a": 3200, "qty": 10},
				{"mark": "B1", "shape": "00", "rebar_type": "DB16", "a": 4500, "qty": 6},
				{"mark": "S1", "shape": "00", "rebar_type": "DB16", "a": 2100, "qty": 9},
			],
			stock=[{"rebar_type": "DB16", "length": 10}, {"rebar_type": "DB16", "length": 12}],
		)
		cut = sum(
			p.bars * sum(x["length"] * x["count"] for x in frappe.parse_json(p.pieces)) for p in doc.patterns
		)
		self.assertEqual(cut, 77900)
		self.assertAlmostEqual(doc.total_required_length, 77.9)
		self.assertAlmostEqual(
			doc.total_stock_length, doc.total_required_length + doc.reusable_offcut + doc.scrap
		)
		self.assertAlmostEqual(doc.loss_percent, doc.scrap / doc.total_stock_length * 100)
		self.assertEqual(doc.total_stock_length, 80)

	def test_stock_limits(self):
		items = [{"shape": "00", "rebar_type": "DB12", "a": 4000, "qty": 10}]
		doc = self.make_plan(
			items,
			stock=[{"rebar_type": "DB12", "length": 12, "qty": 3}, {"rebar_type": "DB12", "length": 10}],
		)
		self.assertLessEqual(sum(p.bars for p in doc.patterns if p.stock_length == 12), 3)
		with self.assertRaises(frappe.ValidationError):
			self.make_plan(items, stock=[{"rebar_type": "DB12", "length": 12, "qty": 2}])
		with self.assertRaises(frappe.ValidationError):
			self.make_plan([{"shape": "00", "rebar_type": "DB12", "a": 13000, "qty": 1}])


class UnitTestOptimizer(IntegrationTestCase):
	def test_all_pieces_cut_within_stock(self):
		pieces = [(3200, "C1")] * 10 + [(4500, "B1")] * 6 + [(2100, "S1")] * 9
		patterns = plan_cuts(pieces, [(10000, None), (12000, None)], kerf=5)
		cut = sorted(
			length for p in patterns for length, count, _ in p["cuts"] for _ in range(count * p["bars"])
		)
		self.assertEqual(cut, sorted(length for length, _ in pieces))
		for p in patterns:
			self.assertLessEqual(sum((length + 5) * count for length, count, _ in p["cuts"]), p["stock"] + 5)

	def test_not_enough(self):
		with self.assertRaises(NotEnoughStock):
			plan_cuts([(4000, "A")] * 10, [(12000, 2)])
