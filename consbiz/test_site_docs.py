# Copyright (c) 2026, Siricons and Contributors
# See license.txt

# หมวดจัดซื้อ/ขายของแอปหน้างาน (site_docs.py): รายการ ตัวกรอง ขอบเขตโครงการ รายละเอียด และส่งเอกสาร

import json

import frappe
from frappe.tests import IntegrationTestCase

from consbiz import site_docs, store_app
from consbiz.test_store_app import ITEM, SUPPLIER, make_po, setup_store

IGNORE_TEST_RECORD_DEPENDENCIES = ["Company", "Customer", "Supplier", "Project", "Account", "Mode of Payment"]


class IntegrationTestSiteDocs(IntegrationTestCase):
	def setUp(self):
		self.project = setup_store()

	def names(self, **kwargs):
		return [r.name for r in site_docs.get_docs("po", project=self.project, **kwargs)["rows"]]

	def test_purchase_order_list_and_detail(self):
		po = make_po(self.project)
		self.assertIn(po.name, self.names(filter="todo"))
		self.assertNotIn(po.name, self.names(filter="draft"))
		self.assertNotIn(po.name, self.names(filter="done"))
		self.assertIn(po.name, self.names(filter="all", search=po.name))

		row = next(r for r in site_docs.get_docs("po", project=self.project)["rows"] if r.name == po.name)
		self.assertEqual((row.status_label, row.status_tone), ("รอรับของ/วางบิล", "amber"))
		self.assertEqual(row.amount, po.grand_total)

		detail = site_docs.get_doc("po", po.name)
		self.assertEqual(detail["totals"]["grand_total"], po.grand_total)
		self.assertEqual(len(detail["items"]), 1)
		self.assertFalse(detail["can_submit"])
		self.assertIn("download_pdf", detail["pdf_url"])

		summary = site_docs.get_summary("buy", project=self.project)
		self.assertGreaterEqual(summary["po_receive"]["count"], 1)

	def test_scope_and_submit(self):
		po = make_po(self.project)
		po.cancel()
		draft = frappe.copy_doc(po)
		draft.insert()
		self.assertIn(draft.name, self.names(filter="draft"))
		# อีกโครงการ: ไม่เห็นเมื่อเลือกขอบเขตโครงการ เห็นเมื่อทุกโครงการ
		other = frappe.get_doc({"doctype": "Project", "project_name": "_Test Site Docs Other", "company": po.company})
		other.insert(ignore_permissions=True)
		rows = site_docs.get_docs("po", project=other.name, filter="draft")["rows"]
		self.assertNotIn(draft.name, [r.name for r in rows])
		rows = site_docs.get_docs("po", project=other.name, scope="all", filter="draft")["rows"]
		self.assertIn(draft.name, [r.name for r in rows])

		self.assertTrue(site_docs.get_doc("po", draft.name)["can_submit"])
		site_docs.submit_doc("po", draft.name)
		self.assertEqual(frappe.db.get_value("Purchase Order", draft.name, "docstatus"), 1)

	def test_status_and_kind(self):
		self.assertEqual(site_docs.status_of("Overdue", 1), ("เกินกำหนด", "rose"))
		self.assertEqual(site_docs.status_of("Unpaid", 0), ("ร่าง", "gray"))
		self.assertRaises(frappe.ValidationError, site_docs.get_docs, "xx")

	def test_create_and_edit_purchase_order(self):
		form = site_docs.get_form("po", project=self.project)
		self.assertEqual(form["project"], self.project)
		self.assertIsNone(form["name"])
		data = {
			"project": self.project,
			"supplier": SUPPLIER,
			"transaction_date": form["transaction_date"],
			"schedule_date": form["schedule_date"],
			"taxes_and_charges": None,
			"items": [{"key": None, "item_code": ITEM, "qty": 4, "rate": 25}],
		}
		preview = site_docs.preview_doc("po", json.dumps(data, default=str))
		self.assertEqual(preview["totals"]["grand_total"], 100)

		saved = site_docs.save_doc("po", json.dumps(data, default=str))
		po = frappe.get_doc("Purchase Order", saved["name"])
		self.assertEqual((po.docstatus, po.project, po.items[0].qty), (0, self.project, 4))
		self.assertEqual(po.items[0].warehouse, store_app.project_warehouse(self.project))

		# แก้ร่าง: แถวเดิมจับคู่ด้วย key (name ของแถว) แล้วส่ง
		form = site_docs.get_form("po", name=po.name)
		row = form["items"][0]
		self.assertEqual(row["key"], po.items[0].name)
		data["name"] = po.name
		data["items"] = [{**row, "qty": 6}]
		site_docs.save_doc("po", json.dumps(data, default=str), submit=1)
		po.reload()
		self.assertEqual((po.docstatus, len(po.items), po.items[0].qty, po.grand_total), (1, 1, 6, 150))

	def test_next_document_from_purchase_order(self):
		po = make_po(self.project)
		self.assertEqual(site_docs.get_doc("po", po.name)["next_kind"], "pi")
		form = site_docs.get_form("pi", source=po.name)
		self.assertEqual(form["supplier"], po.supplier)
		data = {**form, "items": [{**form["items"][0], "qty": 3}]}
		saved = site_docs.save_doc("pi", json.dumps(data, default=str))
		pi = frappe.get_doc("Purchase Invoice", saved["name"])
		self.assertEqual((pi.items[0].purchase_order, pi.items[0].qty), (po.name, 3))

	def test_form_rejects_submitted_and_unknown(self):
		po = make_po(self.project)
		self.assertRaises(frappe.ValidationError, site_docs.get_form, "po", name=po.name)
		self.assertRaises(frappe.ValidationError, site_docs.get_form, "qtn", source=po.name)

	def test_list_counts_sums_sort_and_filters(self):
		first = make_po(self.project, qty=2)
		second = make_po(self.project, qty=5)
		result = site_docs.get_docs("po", project=self.project, filter="todo", sort="amount", order="asc")
		names = [r.name for r in result["rows"]]
		self.assertLess(names.index(first.name), names.index(second.name))
		self.assertEqual(result["total"], result["counts"]["todo"])
		self.assertGreaterEqual(result["sums"]["amount"], first.grand_total + second.grand_total)
		self.assertIn("download_pdf", result["rows"][0].pdf_url)

		# ช่วงวันที่ในอนาคต = ไม่พบ, คู่ค้า = ผู้ขายของใบ
		empty = site_docs.get_docs("po", project=self.project, filter="all", date_from="2999-01-01")
		self.assertEqual(empty["total"], 0)
		by_party = site_docs.get_docs("po", project=self.project, filter="all", party=SUPPLIER)
		self.assertIn(first.name, [r.name for r in by_party["rows"]])
		exported = site_docs.get_docs("po", project=self.project, filter="all", export=1)
		self.assertNotIn("total", exported)

	def test_bulk_submit_reports_each_document(self):
		po = make_po(self.project)
		po.cancel()
		draft = frappe.copy_doc(po)
		draft.insert()
		results = site_docs.submit_docs("po", json.dumps([draft.name, po.name]))
		self.assertEqual([r["ok"] for r in results], [True, False])
		self.assertEqual(frappe.db.get_value("Purchase Order", draft.name, "docstatus"), 1)

