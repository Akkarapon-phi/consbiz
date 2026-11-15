# Copyright (c) 2026, Siricons and Contributors
# See license.txt

# แอปผู้รับเหมาช่วง (contractor_app.py): สิทธิ์ตามผู้รับเหมาที่ผูก (Portal Users), ใบเบิกที่ ผรม. ร่าง
# ร่าง → ส่งให้ตรวจ → ส่งกลับแก้ / ถอน → อนุมัติ และเจ้าหน้าที่แก้/อนุมัติไม่ได้ระหว่าง ผรม. ยังแก้อยู่
# ลิงก์ของสัญญา (ไม่ login): เห็นเฉพาะสัญญานั้น, หมดอายุเมื่อปิดสัญญา, สร้างใหม่แล้วลิงก์เดิมใช้ไม่ได้
# การอัปโหลดไฟล์ (multipart) ตรวจในเบราว์เซอร์

import frappe
from frappe.tests import IntegrationTestCase

from consbiz import contractor_app, subcontract, subcontract_app
from consbiz.test_store_app import setup_store
from consbiz.test_subcontract import make_supplier

CONTRACTOR = "_test_contractor@example.com"
OUTSIDER = "_test_outsider@example.com"
OTHER_SUPPLIER = "_Test Other Subcontractor"


def make_website_user(email):
	if not frappe.db.exists("User", email):
		frappe.get_doc(
			{"doctype": "User", "email": email, "first_name": email.split("@")[0], "user_type": "Website User"}
		).insert(ignore_permissions=True)
	return email


def link_user(supplier, user):
	doc = frappe.get_doc("Supplier", supplier)
	if not any(r.user == user for r in doc.portal_users):
		doc.append("portal_users", {"user": user})
		doc.save(ignore_permissions=True)


class IntegrationTestContractorApp(IntegrationTestCase):
	def setUp(self):
		self.project = setup_store()
		self.supplier = make_supplier()
		if not frappe.db.exists("Supplier", OTHER_SUPPLIER):
			frappe.get_doc({"doctype": "Supplier", "supplier_name": OTHER_SUPPLIER}).insert(
				ignore_permissions=True
			)
		link_user(self.supplier, make_website_user(CONTRACTOR))
		link_user(OTHER_SUPPLIER, make_website_user(OUTSIDER))
		self.agreement = frappe.get_doc(
			{
				"doctype": "Subcontract Agreement",
				"title": "งานผนัง",
				"supplier": self.supplier,
				"project": self.project,
				"contract_date": "2026-11-01",
				"billing_method": "Measured",
				"retention_percent": 5,
				"wht_percent": 3,
				"penalty_per_day": 500,
				"items": [{"item_name": "ก่ออิฐ", "uom": "Nos", "qty": 100, "rate": 300}],
			}
		).insert()
		self.agreement.submit()

	def tearDown(self):
		frappe.set_user("Administrator")

	def payload(self, qty, name=None, modified=None):
		return {
			"name": name,
			"modified": modified,
			"subcontract_agreement": self.agreement.name,
			"posting_date": "2026-11-15",
			"remarks": "งวดแรก",
			"penalty_days": 9,  # ผรม. ส่งมาก็ไม่ใช้
			"items": [{"agreement_item": self.agreement.items[0].name, "qty": qty}],
		}

	def test_only_own_supplier(self):
		frappe.set_user(OUTSIDER)
		self.assertRaises(frappe.PermissionError, contractor_app.get_agreement, self.agreement.name)
		self.assertRaises(frappe.PermissionError, contractor_app.get_claim, None, self.agreement.name)
		self.assertEqual(contractor_app.get_home()["agreements"], [])

		frappe.set_user(CONTRACTOR)
		view = contractor_app.get_agreement(self.agreement.name)
		self.assertTrue(view["can_claim"])
		self.assertEqual([a.name for a in contractor_app.get_home()["agreements"]], [self.agreement.name])

	def test_draft_send_return_approve(self):
		frappe.set_user(CONTRACTOR)
		view = contractor_app.save_claim(frappe.as_json(self.payload(10)))
		name = view["doc"]["name"]
		doc = frappe.get_doc("Subcontract Claim", name)
		self.assertEqual((doc.prepared_by, doc.from_contractor), (CONTRACTOR, 1))
		self.assertEqual(doc.status, "Draft")
		self.assertEqual(doc.gross_amount, 3000)
		self.assertEqual(doc.penalty_days, 0)
		# ใบที่สองของสัญญาเดียวกันระหว่างยังไม่อนุมัติ
		self.assertRaises(frappe.ValidationError, contractor_app.get_claim, None, self.agreement.name)

		# เจ้าหน้าที่แก้/อนุมัติไม่ได้ระหว่าง ผรม. ร่าง
		frappe.set_user("Administrator")
		self.assertTrue(subcontract_app.get_claim(name)["contractor_busy"])
		self.assertRaises(frappe.ValidationError, doc.submit)

		frappe.set_user(CONTRACTOR)
		view = contractor_app.send_claim(name)
		self.assertEqual(view["doc"]["status"], "Pending Review")
		self.assertFalse(view["can_edit"])
		self.assertRaises(
			frappe.ValidationError,
			contractor_app.save_claim,
			frappe.as_json(self.payload(5, name, view["doc"]["modified"])),
		)

		frappe.set_user("Administrator")
		self.assertRaises(frappe.ValidationError, subcontract.return_claim, name, "")
		subcontract.return_claim(name, "ปริมาณไม่ตรงหน้างาน")
		doc.reload()
		self.assertEqual((doc.status, doc.return_reason), ("Returned", "ปริมาณไม่ตรงหน้างาน"))

		frappe.set_user(CONTRACTOR)
		view = contractor_app.save_claim(frappe.as_json(self.payload(8, name, str(doc.modified))), send=1)
		self.assertEqual(view["doc"]["status"], "Pending Review")
		self.assertEqual(view["doc"]["gross_amount"], 2400)
		self.assertIsNone(view["doc"]["return_reason"])

		frappe.set_user("Administrator")
		doc.reload()
		doc.penalty_days = 2
		doc.save()
		self.assertEqual(doc.status, "Pending Review")
		doc.submit()
		self.assertEqual(frappe.db.get_value("Subcontract Claim", name, "status"), "Approved")

		frappe.set_user(CONTRACTOR)
		view = contractor_app.get_claim(name)
		self.assertEqual(view["doc"]["penalty_amount"], 1000)
		self.assertFalse(view["can_edit"])
		self.assertTrue(contractor_app.get_agreement(self.agreement.name)["can_claim"])

	def test_withdraw_and_delete(self):
		frappe.set_user(CONTRACTOR)
		name = contractor_app.save_claim(frappe.as_json(self.payload(10)), send=1)["doc"]["name"]
		self.assertEqual(contractor_app.withdraw_claim(name)["doc"]["status"], "Draft")
		contractor_app.delete_claim(name)
		self.assertFalse(frappe.db.exists("Subcontract Claim", name))

	def test_staff_claims_hidden_until_approved(self):
		claim = frappe.get_doc(
			{
				"doctype": "Subcontract Claim",
				"subcontract_agreement": self.agreement.name,
				"items": [{"agreement_item": self.agreement.items[0].name, "qty": 5}],
			}
		).insert()
		frappe.set_user(CONTRACTOR)
		self.assertRaises(frappe.PermissionError, contractor_app.get_claim, claim.name)
		self.assertEqual(contractor_app.get_home()["claims"], [])
		frappe.set_user("Administrator")
		claim.submit()
		frappe.set_user(CONTRACTOR)
		self.assertEqual(contractor_app.get_claim(claim.name)["doc"]["status"], "Approved")

	def test_link_scope_expiry_and_reset(self):
		other = frappe.get_doc(
			{
				"doctype": "Subcontract Agreement",
				"title": "งานหลังคา",
				"supplier": self.supplier,
				"project": self.project,
				"contract_date": "2026-11-01",
				"billing_method": "Measured",
				"items": [{"item_name": "มุงหลังคา", "uom": "Nos", "qty": 10, "rate": 1000}],
			}
		).insert()
		other.submit()
		token = subcontract_app.contractor_link(self.agreement.name)["path"].rsplit("/", 1)[-1]

		frappe.set_user("Guest")
		self.assertRaises(frappe.PermissionError, contractor_app.get_home)
		self.assertRaises(contractor_app.LinkExpired, contractor_app.get_home, token="x" * 32)
		# ลิงก์เห็นเฉพาะสัญญาของลิงก์ แม้ผู้รับเหมาเดียวกัน
		self.assertEqual([a.name for a in contractor_app.get_home(token=token)["agreements"]], [self.agreement.name])
		self.assertRaises(frappe.PermissionError, contractor_app.get_agreement, other.name, token)
		view = contractor_app.save_claim(frappe.as_json(self.payload(10)), send=1, token=token)
		claim = frappe.get_doc("Subcontract Claim", view["doc"]["name"])
		self.assertEqual((claim.from_contractor, claim.prepared_by, claim.status), (1, None, "Pending Review"))

		# สร้างลิงก์ใหม่: ลิงก์เดิมใช้ไม่ได้
		frappe.set_user("Administrator")
		new_token = subcontract_app.reset_contractor_link(self.agreement.name)["path"].rsplit("/", 1)[-1]
		self.assertNotEqual(token, new_token)
		frappe.set_user("Guest")
		self.assertRaises(contractor_app.LinkExpired, contractor_app.get_claim, claim.name, None, token)
		self.assertEqual(contractor_app.get_claim(claim.name, token=new_token)["doc"]["status"], "Pending Review")

		# ปิดสัญญา: ลิงก์หมดอายุ / เปิดอีกครั้ง: ใช้ได้
		frappe.set_user("Administrator")
		claim.submit()
		subcontract.close_agreement(self.agreement.name, "งานจบ")
		frappe.set_user("Guest")
		self.assertRaises(contractor_app.LinkExpired, contractor_app.get_home, token=new_token)
		self.assertTrue(contractor_app.boot_data(new_token)["link_error"])
		frappe.set_user("Administrator")
		subcontract.reopen_agreement(self.agreement.name)
		frappe.set_user("Guest")
		self.assertEqual(contractor_app.boot_data(new_token)["agreement"], self.agreement.name)
