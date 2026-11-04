# Copyright (c) 2026, Siricons and Contributors
# See license.txt

# คลังวัสดุของโครงการ (construction_management/stock.py)

from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from consbiz.consbiz.doctype.construction_management.stock import item_info, item_rows, wbs_key
from consbiz.consbiz.doctype.construction_material_plan.construction_material_plan import empty_supply, with_totals
from consbiz.employer_supplied import employer_item
from consbiz.tests.test_employer_supplied import make_item

IGNORE_TEST_RECORD_DEPENDENCIES = ["Item", "Item Group", "UOM", "Project", "Warehouse", "Construction Management"]

PLAN_MODULE = "consbiz.consbiz.doctype.construction_material_plan.construction_material_plan"


class IntegrationTestProjectStock(IntegrationTestCase):
	def test_employer_item_merged_into_base(self):
		base = make_item("_Test Stock Rebar")
		twin = employer_item(base.name)
		info = item_info([base.name, twin])
		ledger = [
			frappe._dict(item_code=base.name, warehouse="Site", qty_in=10, qty_out=4, balance=6),
			frappe._dict(item_code=twin, warehouse="Owner", qty_in=8, qty_out=3, balance=5),
		]
		purchase = empty_supply()
		purchase["purchase"].update(ordered=12, received=10)
		employer = empty_supply()
		employer["customer"].update(requested=8, received=8)
		supply = {base.name: with_totals(purchase), twin: with_totals(employer)}
		plan_rows = [{"item_code": base.name, "wbs": "1.1", "stock_qty": 20}, {"item_code": twin, "wbs": "1.2", "stock_qty": 5}]

		with patch(f"{PLAN_MODULE}.get_supply", return_value=supply):
			(row,) = item_rows("_Test Project", info, ledger, {"Owner"}, plan_rows)

		self.assertEqual((row["item_code"], row["item_name"]), (base.name, "_Test Stock Rebar"))
		self.assertEqual((row["company"]["balance"], row["employer"]["balance"], row["balance"]), (6, 5, 11))
		self.assertEqual((row["company"]["pending"], row["employer"]["pending"]), (2, 0))
		self.assertEqual(row["used"], 7)
		# ตามแผน 25 ขอแล้ว 12 + 8 = ยังไม่ได้ขอ 5
		self.assertEqual((row["need"], row["short"]), (25, 5))

	def test_wbs_sort(self):
		self.assertEqual(sorted(["1.10", "1.2", "2", "1.1"], key=wbs_key), ["1.1", "1.2", "1.10", "2"])
