# Copyright (c) 2026, Siricons and Contributors
# See license.txt

# แอปสโตร์หน้างาน (store_app.py): รับของตาม PO + ตีกลับ, เบิก, ยืม-คืน

import json

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, nowdate

from consbiz import store_app
from consbiz.consbiz.doctype.retention_receivable.test_retention_receivable import (
	COMPANY,
	SUPPLIER,
	ensure_master,
	setup_retention_masters,
)

IGNORE_TEST_RECORD_DEPENDENCIES = ["Company", "Customer", "Supplier", "Project", "Account", "Mode of Payment"]
PROJECT_NAME = "_Test Store Project"
ITEM = "_Test Store Item"


def setup_store():
	setup_retention_masters()
	project = frappe.db.get_value("Project", {"project_name": PROJECT_NAME})
	if not project:
		project = (
			frappe.get_doc(
				{
					"doctype": "Project",
					"project_name": PROJECT_NAME,
					"company": COMPANY,
					"custom_warehouse_name": "_Test Store Site",
				}
			)
			.insert(ignore_permissions=True)
			.name
		)
	group = frappe.db.get_value("Item Group", {"is_group": 0}, "name")
	ensure_master(
		"Item", ITEM, item_code=ITEM, item_name=ITEM, item_group=group, stock_uom="Nos", is_stock_item=1
	)
	return project


def make_po(project, qty=10):
	po = frappe.new_doc("Purchase Order")
	po.update(
		{
			"company": COMPANY,
			"supplier": SUPPLIER,
			"transaction_date": nowdate(),
			"schedule_date": add_days(nowdate(), 3),
			"project": project,
		}
	)
	po.append(
		"items",
		{
			"item_code": ITEM,
			"qty": qty,
			"rate": 100,
			"schedule_date": add_days(nowdate(), 3),
			"project": project,
			"warehouse": store_app.project_warehouse(project),
		},
	)
	po.insert()
	po.submit()
	return po


class IntegrationTestStoreApp(IntegrationTestCase):
	def setUp(self):
		self.project = setup_store()

	def test_hhmm(self):
		self.assertEqual(store_app.hhmm("1:09:46.845421"), "01:09")
		self.assertEqual(store_app.hhmm("13:05:00"), "13:05")
		self.assertEqual(store_app.hhmm(None), "")

	def test_receive_with_rejection(self):
		po = make_po(self.project)
		pending = store_app.get_pending_receipts(self.project)
		self.assertIn(po.name, [p["name"] for p in pending])

		row = store_app.get_receipt_source("Purchase Order", po.name)["items"][0]
		self.assertEqual(row["pending"], 10)

		# รับ + ตีกลับ เกินยอดค้าง
		self.assertRaises(
			frappe.ValidationError,
			store_app.submit_receipt,
			"Purchase Order",
			po.name,
			json.dumps([{"row": row["row"], "qty": 9, "rejected_qty": 2}]),
			project=self.project,
		)

		result = store_app.submit_receipt(
			"Purchase Order",
			po.name,
			json.dumps([{"row": row["row"], "qty": 6, "rejected_qty": 1, "reason": "ชำรุด"}]),
			project=self.project,
			delivery_note="DN-1",
		)
		self.assertEqual(result["doctype"], "Purchase Receipt")
		receipt = store_app.get_receipt("Purchase Receipt", result["name"])
		self.assertEqual(receipt["delivery_note"], "DN-1")
		self.assertEqual((receipt["items"][0]["qty"], receipt["items"][0]["rejected_qty"]), (6, 1))
		self.assertEqual(
			frappe.db.get_value("Purchase Receipt Item", {"parent": result["name"]}, "warehouse"),
			store_app.project_warehouse(self.project),
		)
		# ตีกลับไม่รับเข้า: ยอดยังค้างที่ PO
		self.assertEqual(store_app.get_receipt_source("Purchase Order", po.name)["items"][0]["pending"], 4)

		# ตีกลับทั้งหมด: ไม่มีใบรับ บันทึกเป็น Comment ที่ PO
		result = store_app.submit_receipt(
			"Purchase Order",
			po.name,
			json.dumps([{"row": row["row"], "qty": 0, "rejected_qty": 4, "reason": "ไม่ตรงสเปก"}]),
			project=self.project,
		)
		self.assertTrue(result["rejected_only"])
		self.assertTrue(
			frappe.db.exists(
				"Comment", {"reference_doctype": "Purchase Order", "reference_name": po.name, "comment_type": "Comment"}
			)
		)

		# เบิกจากคลังของโครงการ
		stock = {i["item_code"]: i for i in store_app.get_stock(self.project)["items"]}
		self.assertEqual(stock[ITEM]["balance"], 6)
		issue = store_app.submit_issue(self.project, json.dumps([{"item_code": ITEM, "qty": 2}]), issued_to="ผรม. ก")
		self.assertIn(issue["name"], [h["name"] for h in store_app.get_issue_history(self.project)])
		stock = {i["item_code"]: i for i in store_app.get_stock(self.project)["items"]}
		self.assertEqual(stock[ITEM]["balance"], 4)

	def test_issue_needs_items(self):
		self.assertRaises(frappe.ValidationError, store_app.submit_issue, self.project, json.dumps([]))
