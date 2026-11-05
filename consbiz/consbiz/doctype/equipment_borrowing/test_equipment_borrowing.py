# Copyright (c) 2026, Siricons and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from consbiz.consbiz.doctype.equipment_borrowing.equipment_borrowing import record_return
from consbiz.tests.test_employer_supplied import make_item

IGNORE_TEST_RECORD_DEPENDENCIES = [
	"Item",
	"Item Group",
	"UOM",
	"Company",
	"Warehouse",
	"Project",
	"Employee",
	"Supplier",
	"Stock Entry",
	"User",
]

MODULE = "consbiz.consbiz.doctype.equipment_borrowing.equipment_borrowing"


class IntegrationTestEquipmentBorrowing(IntegrationTestCase):
	def setUp(self):
		self.drill = make_item("_Test Drill")
		self.ladder = make_item("_Test Ladder")
		self.entries = []
		patcher = patch(f"{MODULE}.make_stock_entry", side_effect=self.fake_entry)
		patcher.start()
		self.addCleanup(patcher.stop)
		# คลัง/บริษัทในเทสต์ไม่มีอยู่จริง (ใบที่โหลดใหม่ตอนรับคืนตั้ง ignore_links ไม่ได้)
		links = patch("frappe.model.document.Document._validate_links")
		links.start()
		self.addCleanup(links.stop)
		cancel = patch(f"{MODULE}.cancel_stock_entry")
		self.cancelled = cancel.start()
		self.addCleanup(cancel.stop)

	def fake_entry(self, doc, purpose, lines, source, target=None):
		self.entries.append((purpose, lines, source, target))
		return f"SE-{len(self.entries)}"

	def make_borrowing(self, submit=True, **values):
		doc = frappe.new_doc("Equipment Borrowing")
		doc.update(
			{
				"borrower_type": "Worker",
				"worker_name": "สมชาย",
				"company": "_Test Company",
				"date": "2026-11-04",
				"due_date": "2026-11-10",
				"source_warehouse": "Store",
				"loan_warehouse": "On Loan",
				**values,
			}
		)
		doc.append("items", {"item_code": self.drill.name, "qty": 2})
		doc.append("items", {"item_code": self.ladder.name, "qty": 1})
		doc.flags.ignore_links = True
		doc.insert()
		if submit:
			doc.submit()
		return doc

	def test_handover_and_returns(self):
		doc = self.make_borrowing()
		self.assertEqual((doc.status, doc.borrower_name), ("Borrowed", "สมชาย"))
		self.assertEqual(
			self.entries[0],
			("Material Transfer", [(self.drill.name, 2), (self.ladder.name, 1)], "Store", "On Loan"),
		)

		# คืนสว่าน 1 ปกติ + บันไดหาย: โอนกลับคลังต้นทาง 1 ใบ และตัดของหาย 1 ใบ
		record_return(
			doc.name,
			[
				{"item_code": self.drill.name, "qty": 1},
				{"item_code": self.ladder.name, "qty": 1, "condition": "Lost"},
			],
			returned_by="สมชาย",
		)
		doc.reload()
		self.assertEqual(doc.status, "Partially Returned")
		self.assertEqual(
			[(r.returned_qty, r.lost_qty, r.outstanding_qty) for r in doc.items], [(1, 0, 1), (0, 1, 0)]
		)
		self.assertEqual([e[0] for e in self.entries[1:]], ["Material Transfer", "Material Issue"])
		self.assertEqual([r.stock_entry for r in doc.returns], ["SE-2", "SE-3"])

		record_return(doc.name, [{"item_code": self.drill.name, "qty": 1, "condition": "Damaged"}])
		doc.reload()
		self.assertEqual(doc.status, "Returned")

	def test_cannot_return_more_than_outstanding(self):
		doc = self.make_borrowing()
		with self.assertRaises(frappe.ValidationError):
			record_return(doc.name, [{"item_code": self.drill.name, "qty": 3}])

	def test_saved_returns_are_locked(self):
		doc = self.make_borrowing()
		record_return(doc.name, [{"item_code": self.drill.name, "qty": 1}])
		doc.reload()
		doc.returns[0].qty = 2
		with self.assertRaises(frappe.ValidationError):
			doc.save()
		doc.reload()
		doc.set("returns", [])
		with self.assertRaises(frappe.ValidationError):
			doc.save()

	def test_cancel_reverses_stock_entries(self):
		doc = self.make_borrowing()
		record_return(doc.name, [{"item_code": self.drill.name, "qty": 1}])
		doc.reload()
		doc.cancel()
		self.assertEqual([c.args[0] for c in self.cancelled.call_args_list], ["SE-2", "SE-1"])
		self.assertEqual(frappe.db.get_value("Equipment Borrowing", doc.name, "status"), "Cancelled")

	def test_validation(self):
		with self.assertRaises(frappe.ValidationError):
			self.make_borrowing(submit=False, loan_warehouse="Store")
		with self.assertRaises(frappe.ValidationError):
			self.make_borrowing(submit=False, due_date="2026-11-01")
