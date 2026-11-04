# Copyright (c) 2026, Siricons and contributors
# For license information, please see license.txt

"""หน้าซองจดหมาย: Submit เพื่อเก็บไว้ดูย้อนหลังว่าส่งอะไรให้ใคร
สร้างจากใบนำส่งเอกสาร (Transmittal) หรือใบแจ้งหนี้ขาย (Sales Invoice) ได้ (`make_envelope`)
ที่อยู่/ผู้ติดต่อผู้รับ: ของในเอกสารต้นทางก่อน ไม่มีใช้ค่าหลักของลูกค้า/ผู้ขาย
"""

import frappe
from frappe import _
from frappe.contacts.doctype.address.address import get_default_address
from frappe.contacts.doctype.contact.contact import get_default_contact
from frappe.model.document import Document
from frappe.utils import nowdate


class Envelope(Document):
	pass


def _from_transmittal(doc):
	address = get_default_address(doc.party_type, doc.party) if doc.party else None
	contact = get_default_contact(doc.party_type, doc.party) if doc.party else None
	return {"to": address, "receiver": contact, "remark": doc.title}


def _from_sales_invoice(doc):
	address = doc.customer_address or get_default_address("Customer", doc.customer)
	contact = doc.contact_person or get_default_contact("Customer", doc.customer)
	return {
		"to": address,
		"receiver": contact,
		"remark": _("Invoice / Tax Invoice {0}").format(doc.name),
	}


SOURCES = {
	"Transmittal": _from_transmittal,
	"Sales Invoice": _from_sales_invoice,
}


@frappe.whitelist()
def make_envelope(source_doctype: str, source_name: str):
	"""หน้าซองใบใหม่ (ยังไม่บันทึก) ที่เติมค่าจากเอกสารต้นทาง"""
	if source_doctype not in SOURCES:
		frappe.throw(_("Cannot create an envelope from {0}").format(_(source_doctype)))

	source = frappe.get_doc(source_doctype, source_name)
	source.check_permission("read")

	envelope = frappe.new_doc("Envelope")
	envelope.update(
		{
			"company": source.company,
			"from": get_default_address("Company", source.company) if source.company else None,
			"sender": frappe.session.user,
			"send_date": nowdate(),
			"reference_doctype": source_doctype,
			"reference_name": source_name,
			**SOURCES[source_doctype](source),
		}
	)
	if envelope.sender:
		envelope.sender_name, envelope.sender_tel = frappe.db.get_value(
			"User", envelope.sender, ["full_name", "mobile_no"]
		) or (None, None)
	return envelope
