# Copyright (c) 2026, Siricons and Contributors
# See license.txt

# หมวดสารบรรณในแอปออฟฟิศ (saraban.py): หนังสือเข้า (เสนออนุมัติ), หนังสือออก, ใบนำส่ง, ใบปะหน้า

import json

import frappe
from frappe.tests import IntegrationTestCase

from consbiz import saraban
from consbiz.consbiz.doctype.retention_receivable.test_retention_receivable import COMPANY

APPROVER = "test_saraban_approver@example.com"


def make_approver():
	if not frappe.db.exists("User", APPROVER):
		frappe.get_doc(
			{"doctype": "User", "email": APPROVER, "first_name": "Saraban Approver", "send_welcome_email": 0}
		).insert(ignore_permissions=True)
	user = frappe.get_doc("User", APPROVER)
	user.add_roles("Approver")
	return APPROVER


class IntegrationTestSaraban(IntegrationTestCase):
	def save(self, kind, data, submit=0):
		return saraban.save_doc(kind, json.dumps(data, default=str), submit=submit)

	def letter_in(self):
		return self.save(
			"letters-in",
			{
				"document_no": "T-1",
				"title": "ทดสอบหนังสือเข้า",
				"document_date": "2026-11-14",
				"company": COMPANY,
				"receiver": "Administrator",
				"receive_date": "2026-11-14",
			},
			submit=1,
		)["name"]

	def test_unknown_kind(self):
		self.assertRaises(frappe.PermissionError, saraban.get_view, "user", "Administrator")

	def test_form_defaults(self):
		doc = saraban.get_form("letters-in", company=COMPANY)["doc"]
		self.assertEqual(doc["receiver"], "Administrator")
		self.assertEqual(doc["status"], saraban.LI_WAIT)
		self.assertEqual(saraban.get_form("letters-out", company=COMPANY)["doc"]["sender"], "Administrator")

	def test_letter_in_approval(self):
		approver = make_approver()
		name = self.letter_in()

		view = saraban.propose(name, approver)
		self.assertEqual(view["doc"]["status"], saraban.LI_PROPOSE)
		self.assertTrue(view["can_withdraw"])
		self.assertTrue(
			frappe.db.exists("ToDo", {"reference_name": name, "allocated_to": approver, "status": "Open"})
		)

		view = saraban.withdraw(name)
		self.assertEqual(view["doc"]["status"], saraban.LI_WAIT)
		self.assertFalse(view["doc"]["approver"])

		saraban.propose(name, approver)
		# ผู้อื่นพิจารณาไม่ได้
		self.assertRaises(frappe.PermissionError, saraban.decide, name, 1)
		frappe.set_user(approver)
		try:
			# ไม่อนุมัติต้องมีเหตุผล
			self.assertRaises(frappe.ValidationError, saraban.decide, name, 0, None, "")
			view = saraban.decide(name, 0, "2026-11-14", "ข้อมูลไม่ครบ")
			self.assertEqual(view["doc"]["status"], saraban.LI_REJECTED)
		finally:
			frappe.set_user("Administrator")

		# เสนอใหม่ล้างผลเดิม
		view = saraban.propose(name, approver)
		self.assertFalse(view["doc"]["approve_remark"])
		frappe.set_user(approver)
		try:
			view = saraban.decide(name, 1, "2026-11-14")
		finally:
			frappe.set_user("Administrator")
		self.assertEqual(view["doc"]["status"], saraban.LI_APPROVED)
		self.assertFalse(saraban.get_view("letters-in", name).get("can_propose"))

	def test_propose_requires_approver_role(self):
		name = self.letter_in()
		self.assertRaises(frappe.ValidationError, saraban.propose, name, "Guest")

	def test_letter_out_update_after_submit(self):
		name = self.save(
			"letters-out",
			{
				"title": "หนังสือออก",
				"document_date": "2026-11-14",
				"company": COMPANY,
				"sender": "Administrator",
				"sent_date": "2026-11-14",
				"document_status": "ดำเนินการ",
			},
			submit=1,
		)["name"]
		view = saraban.update_submitted(
			"letters-out", name, json.dumps({"document_status": "อนุมัติ", "title": "x"})
		)
		self.assertEqual(view["doc"]["document_status"], "อนุมัติ")
		# ช่องที่ไม่ได้อยู่ใน after ไม่ถูกแก้
		self.assertEqual(view["doc"]["title"], "หนังสือออก")

	def test_transmittal_and_envelope(self):
		name = self.save(
			"transmittals",
			{
				"company": COMPANY,
				"title": "ส่งเอกสาร",
				"date": "2026-11-14",
				"recipient_type": "Other",
				"recipient_name": "สำนักงานบัญชี",
				"items": [{"description": "สำเนาสัญญา", "qty": 1, "unit": "ฉบับ"}],
			},
		)["name"]
		form = saraban.get_form("transmittals", name=name)["doc"]
		self.assertEqual(len(form["items"]), 1)

		view = saraban.submit_doc("transmittals", name)
		self.assertEqual(view["doc"]["status"], "To Send")
		view = saraban.update_submitted("transmittals", name, json.dumps({"sent_date": "2026-11-14"}))
		self.assertEqual(view["doc"]["status"], "Sent")
		self.assertTrue(view["can_envelope"])

		envelope = saraban.get_form("envelopes", source=name)["doc"]
		self.assertEqual(envelope["reference_name"], name)
		saved = self.save("envelopes", envelope, submit=1)
		self.assertIn(saved["name"], [e.name for e in saraban.get_view("transmittals", name)["envelopes"]])

		saraban.cancel_doc("envelopes", saved["name"])
		saraban.delete_doc("envelopes", saved["name"])
		self.assertFalse(frappe.db.exists("Envelope", saved["name"]))
