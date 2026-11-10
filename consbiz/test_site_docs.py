# Copyright (c) 2026, Siricons and Contributors
# See license.txt

# หมวดจัดซื้อ/ขายของแอปหน้างาน (site_docs.py): รายการ ตัวกรอง ขอบเขตโครงการ รายละเอียด และส่งเอกสาร

import json
from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from consbiz import site_docs, store_app
from consbiz.consbiz.doctype.construction_management.construction_management import save_tasks
from consbiz.consbiz.doctype.construction_material_plan.construction_material_plan import empty_supply, with_totals
from consbiz.test_site_app import make_plan
from consbiz.test_store_app import ITEM, ITEM_2, SUPPLIER, make_po, setup_store


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
		# ค้นจากรหัส/ชื่อสินค้าในรายการ (คำบางส่วนได้) สินค้าที่ไม่มีในใบไม่เจอ
		self.assertIn(po.name, self.names(filter="all", search=ITEM))
		self.assertIn(po.name, self.names(filter="all", search="Store Ite"))
		self.assertNotIn(po.name, self.names(filter="all", search=ITEM_2))
		# ใบแจ้งหนี้ซื้อค้นเลขที่บิลผู้ขายได้ด้วย
		self.assertIn(["bill_no", "like", "%INV-9%"], site_docs.search_filters(site_docs.config_of("pi"), "INV-9"))
		self.assertNotIn(["bill_no", "like", "%INV-9%"], site_docs.search_filters(site_docs.config_of("po"), "INV-9"))

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
		draft.docstatus = 0  # copy_doc ของ v16 คง docstatus ของต้นฉบับ (ยกเลิกแล้ว = 2)
		draft.insert()
		self.assertIn(draft.name, self.names(filter="draft"))
		# อีกโครงการ: ไม่เห็นเมื่อเลือกขอบเขตโครงการ เห็นเมื่อทุกโครงการ
		other = frappe.get_doc(
			{"doctype": "Project", "project_name": "_Test Site Docs Other", "company": po.company}
		)
		other.insert(ignore_permissions=True)
		rows = site_docs.get_docs("po", project=other.name, filter="draft")["rows"]
		self.assertNotIn(draft.name, [r.name for r in rows])
		rows = site_docs.get_docs("po", project=other.name, scope="all", filter="draft")["rows"]
		self.assertIn(draft.name, [r.name for r in rows])

		self.assertTrue(site_docs.get_doc("po", draft.name)["can_submit"])
		site_docs.submit_doc("po", draft.name)
		self.assertEqual(frappe.db.get_value("Purchase Order", draft.name, "docstatus"), 1)

	def test_doc_permissions_for_each_kind(self):
		permissions = site_docs.doc_permissions()
		self.assertEqual(set(permissions), {*site_docs.DOCS, "boq"})
		self.assertTrue(permissions["po"]["create"])
		with patch("consbiz.site_docs.frappe.has_permission", return_value=False):
			self.assertFalse(site_docs.doc_permissions()["po"]["read"])

	def test_delete_only_draft_or_cancelled_with_permission(self):
		po = make_po(self.project)
		self.assertFalse(site_docs.get_doc("po", po.name)["can_delete"])
		self.assertRaises(frappe.ValidationError, site_docs.delete_doc, "po", po.name)

		po.cancel()
		self.assertTrue(site_docs.get_doc("po", po.name)["can_delete"])
		# ไม่มีสิทธิ์ลบ = ไม่เห็นปุ่ม
		with patch("frappe.model.document.Document.has_permission", return_value=False):
			self.assertFalse(store_app.can_delete(po))
		site_docs.delete_doc("po", po.name)
		self.assertFalse(frappe.db.exists("Purchase Order", po.name))

	def test_plan_request_is_saved_only_by_the_user(self):
		for name in frappe.get_all("Construction Management", {"project": self.project}, pluck="name"):
			frappe.db.set_value("Construction Management", name, "project", None)
		cm = make_plan(self.project)
		task = frappe.get_doc("Construction Management", cm).tasks[1]
		save_tasks(
			cm,
			frappe.as_json([{"name": task.name, "start_date": "2026-12-20", "end_date": "2026-12-20"}]),
			str(frappe.db.get_value("Construction Management", cm, "modified")),
		)
		# ช่อง company ของ CM ดึงจาก BOQ (ของเทสต์ไม่มี) จึงตั้งหลังบันทึกแผน
		frappe.db.set_value("Construction Management", cm, "company", frappe.db.get_value("Project", self.project, "company"))
		plan = frappe.get_doc(
			{
				"doctype": "Construction Material Plan",
				"construction_management": cm,
				"items": [{"wbs": "1.1", "item_code": ITEM, "qty": 5, "lead_time_days": 0}],
			}
		).insert()
		row = plan.items[0]
		rows = json.dumps([row.name])

		# ใบขอซื้อของเทสต์อื่นในโครงการเดียวกันนับเป็นยอดที่ขอแล้ว: ตัดออกให้แถวนี้ขาดครบ 5
		no_supply = {ITEM: with_totals(empty_supply())}
		plan_module = "consbiz.consbiz.doctype.construction_material_plan.construction_material_plan"
		supply = patch(f"{plan_module}.get_supply", return_value=no_supply)
		supply.start()
		self.addCleanup(supply.stop)

		before = frappe.db.count("Material Request")
		form = site_docs.get_form("mr", project=self.project, plan_rows=rows)
		self.assertEqual(frappe.db.count("Material Request"), before)
		self.assertEqual([(r["item_code"], r["qty"]) for r in form["items"]], [(ITEM, 5)])
		self.assertFalse(frappe.db.get_value(row.doctype, row.name, "material_request"))

		# ผู้ใช้แก้จำนวนแล้วกดบันทึก: ได้ร่างตามที่แก้ และแถวแผนอ้างเลขใบขอซื้อ
		form["items"][0]["qty"] = 3
		data = {**form, "project": self.project, "plan_rows": [row.name]}
		saved = site_docs.save_doc("mr", json.dumps(data, default=str))
		mr = frappe.get_doc("Material Request", saved["name"])
		self.assertEqual((mr.docstatus, mr.items[0].qty), (0, 3))
		self.assertEqual(frappe.db.get_value(row.doctype, row.name, "material_request"), mr.name)

		# ลบใบขอซื้อที่แถวแผนอ้างอยู่ได้ (ไม่ติด Link) และแถวกลับมาขอใหม่ได้
		site_docs.delete_doc("mr", mr.name)
		self.assertFalse(frappe.db.exists("Material Request", mr.name))
		self.assertFalse(frappe.db.get_value(row.doctype, row.name, "material_request"))

	def test_employer_supplied_progress(self):
		# ใบขอซื้อผู้ว่าจ้างจัดหา: ERPNext นับของที่รับเข้าใน per_ordered/ordered_qty แอปต้องแสดงเป็นรับของ ไม่มีขั้นสั่งซื้อ
		config = site_docs.config_of("mr")
		doc = frappe._dict(
			material_request_type="Customer Provided",
			status="Partially Received",
			docstatus=1,
			per_ordered=80,
			per_received=0,
		)
		steps = site_docs.steps_of(doc, "mr")
		self.assertEqual([s["label"] for s in steps], ["ร่าง", "ส่งแล้ว", "รับของ", "เสร็จสิ้น"])
		self.assertEqual((steps[2]["state"], steps[2]["note"]), ("current", "80%"))
		self.assertEqual(site_docs.progress_of(doc, config), {"per_ordered": None, "per_received": 80})
		self.assertEqual(
			site_docs.received_as_received({"ordered_qty": 4, "received_qty": 0}),
			{"ordered_qty": None, "received_qty": 4},
		)
		# ใบขอซื้อปกติไม่เปลี่ยน
		doc.material_request_type = "Purchase"
		self.assertEqual(site_docs.progress_of(doc, config), {"per_ordered": 80, "per_received": 0})
		self.assertEqual([s["label"] for s in site_docs.steps_of(doc, "mr")][2:4], ["สั่งซื้อ", "รับของ"])

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
		draft.docstatus = 0  # copy_doc ของ v16 คง docstatus ของต้นฉบับ (ยกเลิกแล้ว = 2)
		draft.insert()
		results = site_docs.submit_docs("po", json.dumps([draft.name, po.name]))
		self.assertEqual([r["ok"] for r in results], [True, False])
		self.assertEqual(frappe.db.get_value("Purchase Order", draft.name, "docstatus"), 1)

	def test_header_discount(self):
		data = {
			"project": self.project,
			"supplier": SUPPLIER,
			"schedule_date": frappe.utils.add_days(frappe.utils.nowdate(), 3),
			"additional_discount_percentage": 10,
			"items": [{"key": None, "item_code": ITEM, "qty": 2, "rate": 500}],
		}
		preview = site_docs.preview_doc("po", json.dumps(data, default=str))
		self.assertEqual((preview["totals"]["discount_amount"], preview["totals"]["grand_total"]), (100, 900))
		saved = site_docs.save_doc("po", json.dumps(data, default=str))
		self.assertEqual(frappe.db.get_value("Purchase Order", saved["name"], "grand_total"), 900)
		self.assertIn(
			"additional_discount_percentage", site_docs.get_form("po", name=saved["name"])["fields"]
		)

	def test_request_totals_match_desk_formula(self):
		from consbiz.request_totals import calculate

		doc = frappe._dict(
			material_request_type="Purchase",
			custom_included_vat=0,
			custom_vat_override=0,
			items=[
				frappe._dict(qty=2, rate=100, custom_vat_nocal=0),
				frappe._dict(qty=1, rate=50, custom_vat_nocal=1),
			],
		)
		calculate(doc)
		self.assertEqual((doc.custom_net_total, doc.custom_vat, doc.custom_grand_total), (200, 14, 264))
		doc.custom_included_vat = 1
		calculate(doc)
		self.assertEqual((doc.custom_net_total, doc.custom_vat, doc.custom_grand_total), (186.92, 13.08, 250))
		doc.custom_vat_override, doc.custom_vat = 1, 10
		calculate(doc)
		self.assertEqual((doc.custom_net_total, doc.custom_vat, doc.custom_grand_total), (190, 10, 250))

	def test_material_request_form_keeps_rates_and_order(self):
		data = {
			"project": self.project,
			"material_request_type": "Purchase",
			"title": "_Test ขอซื้อ",
			"custom_included_vat": 0,
			"items": [
				{"key": None, "item_code": ITEM, "qty": 2, "rate": 123, "custom_vat_nocal": 0},
				{"key": None, "item_code": ITEM_2, "qty": 1, "rate": 50, "custom_vat_nocal": 1},
			],
		}
		saved = site_docs.save_doc("mr", json.dumps(data, default=str))
		mr = frappe.get_doc("Material Request", saved["name"])
		self.assertEqual([r.rate for r in mr.items], [123, 50])
		self.assertEqual(mr.custom_grand_total, round(246 * 1.07, 2) + 50)

		form = site_docs.get_form("mr", name=mr.name)
		data.update({"name": mr.name, "items": list(reversed(form["items"]))})
		site_docs.save_doc("mr", json.dumps(data, default=str))
		mr.reload()
		self.assertEqual([r.rate for r in mr.items], [50, 123])
		view = site_docs.get_doc("mr", mr.name)
		self.assertEqual(view["purpose"], "ซื้อ")
		self.assertEqual(view["steps"][0]["state"], "current")
		self.assertEqual(view["summary"]["grand"], mr.custom_grand_total)

	def test_withholding_and_retention_in_app_form(self):
		data = {
			"project": self.project,
			"supplier": SUPPLIER,
			"schedule_date": frappe.utils.add_days(frappe.utils.nowdate(), 3),
			"taxes_and_charges": None,
			"custom_subject_to_wht": 1,
			"custom_wht_percent": 3,
			"custom_subject_to_retention": 1,
			"custom_retention_percent": 5,
			"items": [{"key": None, "item_code": ITEM, "qty": 10, "rate": 100}],
		}
		preview = site_docs.preview_doc("po", json.dumps(data, default=str))
		self.assertEqual([d["value"] for d in preview["summary"]["deductions"]], [-30, -50])
		self.assertEqual(preview["summary"]["net"], 920)
		saved = site_docs.save_doc("po", json.dumps(data, default=str))
		po = frappe.get_doc("Purchase Order", saved["name"])
		self.assertEqual(
			(po.custom_wht_amount, po.custom_retention_amount, po.custom_paid_amount), (30, 50, 920)
		)

	def test_item_insight(self):
		po = make_po(self.project, qty=4)
		info = site_docs.get_item_insight("po", ITEM, self.project)
		self.assertEqual(info["item_code"], ITEM)
		self.assertTrue(info["buying"])
		self.assertIn(po.name, [p["name"] for p in info["prices"]])
		pending = {o.name: o.pending for o in info["open_orders"]}
		self.assertEqual(pending.get(po.name), 4)
		self.assertIn("stock", info)
		sell = site_docs.get_item_insight("si", ITEM, self.project)
		self.assertFalse(sell["buying"])
		self.assertNotIn("open_orders", sell)

	def test_activity_comments_and_attachments(self):
		po = make_po(self.project)
		activity = site_docs.get_activity("po", po.name)
		self.assertEqual(activity["timeline"][-1]["type"], "created")
		# ระหว่างเทสต์ Frappe ไม่สร้าง Version (ignore_version = in_test) จึงเทสต์ข้อความจาก Version ตรงๆ
		self.assertEqual(site_docs.version_text(po, {"changed": [["docstatus", 0, 1]]}), "ส่งเอกสาร")
		self.assertIn(
			"แก้", site_docs.version_text(po, {"changed": [["schedule_date", "2026-01-01", "2026-01-02"]]})
		)

		site_docs.add_comment("po", po.name, "<p>ตรวจแล้ว</p><script>alert(1)</script>")
		comment = next(t for t in site_docs.get_activity("po", po.name)["timeline"] if t["type"] == "comment")
		self.assertNotIn("script", comment["html"])
		self.assertTrue(comment["mine"])
		site_docs.delete_comment("po", po.name, comment["name"])
		self.assertFalse(frappe.db.exists("Comment", comment["name"]))
		self.assertRaises(frappe.ValidationError, site_docs.add_comment, "po", po.name, "<p> </p>")

		file = frappe.get_doc(
			{
				"doctype": "File",
				"file_name": "_test_site_docs.txt",
				"content": b"test",
				"is_private": 1,
				"attached_to_doctype": "Purchase Order",
				"attached_to_name": po.name,
			}
		).insert()
		self.assertEqual([f.name for f in site_docs.get_activity("po", po.name)["files"]], [file.name])
		site_docs.remove_attachment("po", po.name, file.name)
		self.assertFalse(frappe.db.exists("File", file.name))

	def test_edit_after_submit(self):
		from frappe.utils import add_days, getdate, nowdate

		po = make_po(self.project)
		info = site_docs.get_doc("po", po.name)["after_submit"]
		fields = {f["fieldname"]: f for f in info["fields"]}
		self.assertIn("order_confirmation_no", fields)
		self.assertEqual(fields["schedule_date"]["label"], "กำหนดส่ง")
		self.assertEqual(info["items"], ["schedule_date"])
		row = site_docs.get_doc("po", po.name)["items"][0]["name"]

		# ช่องเดียว: เลขที่ผู้ขายยืนยัน (ค่าว่าง = ล้างค่า)
		site_docs.save_after_submit("po", po.name, values={"order_confirmation_no": " CONF-1 "})
		self.assertEqual(frappe.db.get_value("Purchase Order", po.name, "order_confirmation_no"), "CONF-1")

		# กำหนดส่งหัวเอกสาร + ใช้กับทุกรายการ
		new_date = add_days(nowdate(), 10)
		detail = site_docs.save_after_submit("po", po.name, values={"schedule_date": new_date}, apply_items=1)
		self.assertEqual(getdate(detail["due"]), getdate(new_date))
		self.assertEqual(getdate(detail["items"][0]["schedule_date"]), getdate(new_date))

		# รายแถว
		site_docs.save_after_submit(
			"po", po.name, items=json.dumps([{"name": row, "schedule_date": add_days(nowdate(), 5)}])
		)
		self.assertEqual(
			getdate(frappe.db.get_value("Purchase Order Item", row, "schedule_date")),
			getdate(add_days(nowdate(), 5)),
		)

		# ห้าม: ก่อนวันที่เอกสาร / ช่องที่ไม่อยู่ในรายการ / ค่าว่างของช่องบังคับ / เอกสารเปลี่ยนไปแล้ว
		self.assertRaises(
			frappe.ValidationError,
			site_docs.save_after_submit,
			"po",
			po.name,
			values={"schedule_date": add_days(nowdate(), -30)},
		)
		self.assertRaises(
			frappe.ValidationError, site_docs.save_after_submit, "po", po.name, values={"supplier": "X"}
		)
		self.assertRaises(
			frappe.ValidationError,
			site_docs.save_after_submit,
			"po",
			po.name,
			items=[{"name": row, "rate": 1}],
		)
		self.assertRaises(
			frappe.ValidationError, site_docs.save_after_submit, "po", po.name, values={"schedule_date": ""}
		)
		self.assertRaises(
			frappe.TimestampMismatchError,
			site_docs.save_after_submit,
			"po",
			po.name,
			values={"order_confirmation_no": "CONF-2"},
			modified="2000-01-01 00:00:00",
		)

		# เอกสารร่างใช้ฟอร์มแก้ไข ไม่มีดินสอ
		draft = frappe.copy_doc(po)
		draft.docstatus = 0
		draft.insert()
		self.assertIsNone(site_docs.get_doc("po", draft.name)["after_submit"])
		self.assertRaises(
			frappe.ValidationError,
			site_docs.save_after_submit,
			"po",
			draft.name,
			values={"order_confirmation_no": "X"},
		)

		# ความเคลื่อนไหว: แก้ช่องเดียวบอกค่าเดิม → ค่าใหม่
		self.assertEqual(
			site_docs.version_text(po, {"changed": [["order_confirmation_no", None, "CONF-1"]]}),
			"แก้ เลขที่ผู้ขายยืนยัน: (ว่าง) → CONF-1",
		)

	def test_office_company_filter_and_project_change(self):
		from consbiz.test_store_app import COMPANY

		po = make_po(self.project)
		other_company = frappe.db.get_value("Company", {"name": ("!=", COMPANY)}, "name")
		# แอปออฟฟิศ: กรองบริษัท (ทุกโครงการ)
		names = [r.name for r in site_docs.get_docs("po", scope="all", filter="all", company=COMPANY)["rows"]]
		self.assertIn(po.name, names)
		if other_company:
			names = [
				r.name
				for r in site_docs.get_docs("po", scope="all", filter="all", company=other_company)["rows"]
			]
			self.assertNotIn(po.name, names)
			self.assertGreaterEqual(
				site_docs.get_summary("buy", scope="all", company=COMPANY)["po_receive"]["count"], 1
			)

		# เอกสารใหม่ไม่ระบุโครงการ ใช้บริษัทที่เลือก แล้วเลือกโครงการในฟอร์ม
		form = site_docs.get_form("po", company=COMPANY)
		self.assertEqual((form["company"], form["project"]), (COMPANY, None))
		second = frappe.db.get_value("Project", {"project_name": "_Test Office Project"})
		if not second:
			second = (
				frappe.get_doc(
					{
						"doctype": "Project",
						"project_name": "_Test Office Project",
						"company": COMPANY,
						"custom_warehouse_name": "_Test Office Site",
					}
				)
				.insert(ignore_permissions=True)
				.name
			)
		data = {
			"company": COMPANY,
			"project": self.project,
			"supplier": SUPPLIER,
			"transaction_date": form["transaction_date"],
			"schedule_date": form["schedule_date"],
			"taxes_and_charges": None,
			"items": [{"key": None, "item_code": ITEM, "qty": 2, "rate": 10}],
		}
		saved = site_docs.save_doc("po", json.dumps(data, default=str))
		form = site_docs.get_form("po", name=saved["name"])
		data.update({"name": saved["name"], "project": second, "items": form["items"]})
		site_docs.save_doc("po", json.dumps(data, default=str))
		draft = frappe.get_doc("Purchase Order", saved["name"])
		self.assertEqual((draft.project, draft.items[0].project), (second, second))
		self.assertEqual(draft.items[0].warehouse, store_app.project_warehouse(second))

		# โครงการของบริษัทอื่นเลือกไม่ได้ (ย้ายโครงการที่สองไปอีกบริษัทชั่วคราว: ไม่ต้องสร้างคลังของบริษัทนั้น)
		frappe.db.set_value("Project", second, "company", other_company or "_Test Company 1")
		data["project"] = second
		data["items"] = site_docs.get_form("po", name=saved["name"])["items"]
		data["project"] = self.project
		site_docs.save_doc("po", json.dumps(data, default=str))
		data["project"] = second
		self.assertRaises(frappe.ValidationError, site_docs.save_doc, "po", json.dumps(data, default=str))
		frappe.db.set_value("Project", second, "company", COMPANY)
