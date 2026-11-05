# Copyright (c) 2026, Siricons and Contributors
# See license.txt

# หมวดจัดซื้อ/ขายของแอปหน้างาน (site_docs.py): รายการ ตัวกรอง ขอบเขตโครงการ รายละเอียด และส่งเอกสาร

import frappe
from frappe.tests import IntegrationTestCase

from consbiz import site_docs
from consbiz.test_store_app import make_po, setup_store

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
