# Copyright (c) 2026, Siricons and contributors
# For license information, please see license.txt

"""ใบนำส่งเอกสาร: แนบเอกสารในระบบ (ใบกำกับภาษี, ใบแจ้งหนี้, หนังสือรับรองหัก ณ ที่จ่าย ฯลฯ) หรือพิมพ์รายการเอง
แล้วส่งให้ลูกค้า / ผู้ขาย / สำนักงานบัญชี

สถานะคำนวณจากวันที่เสมอ (`set_status`): ร่าง → รอส่ง → ส่งแล้ว (sent_date) → รับแล้ว (received_date)
เอกสารเดียวกันส่งให้ผู้รับต่างกันได้ (เช่น ลูกค้า และสำนักงานบัญชี) ส่งซ้ำให้ผู้รับเดิมได้แต่ระบบเตือน
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.query_builder.functions import Sum
from frappe.utils import flt, getdate

PARTY_TYPES = {"Customer": "Customer", "Supplier": "Supplier"}

# เอกสารที่ดึงเข้าใบนำส่งได้จากปุ่ม "ดึงเอกสาร" (ต้องตรงกับ SOURCE_DOCTYPES ใน public/js/transmittal.js)
# document_no = เลขที่ที่พิมพ์ในใบนำส่ง (ใบกำกับภาษีซื้อใช้เลขของผู้ขาย), amount = ยอดเงิน (tuple = บวกกัน)
SOURCES = {
	"Sales Tax Invoice": {
		"date": "date",
		"document_no": "name",
		"party_type": "Customer",
		"party": "party",
		"party_name": "party_name",
		"amount": ("tax_base", "tax_amount"),
	},
	"Purchase Tax Invoice": {
		"date": "date",
		"document_no": "number",
		"party_type": "Supplier",
		"party": "party",
		"party_name": "party_name",
		"amount": ("tax_base", "tax_amount"),
	},
	"Withholding Tax Cert": {
		"date": "date",
		"document_no": "name",
		"party_type": "Supplier",
		"party": "supplier",
		"party_name": "supplier_name",
		"amount": None,  # รวมจาก withholding_tax_items (_wht_amounts)
	},
	"Sales Invoice": {
		"date": "posting_date",
		"document_no": "name",
		"party_type": "Customer",
		"party": "customer",
		"party_name": "customer_name",
		"amount": "grand_total",
		"project": "project",
	},
	"Purchase Invoice": {
		"date": "posting_date",
		"document_no": "bill_no",
		"party_type": "Supplier",
		"party": "supplier",
		"party_name": "supplier_name",
		"amount": "grand_total",
		"project": "project",
	},
	"Retention Invoice": {
		"date": "posting_date",
		"document_no": "name",
		"party_type": "Customer",
		"party": "customer",
		"party_name": None,
		"amount": "grand_total",
		"project": "project",
	},
}


class Transmittal(Document):
	def validate(self):
		self.party_type = PARTY_TYPES.get(self.recipient_type)
		if not self.party_type:
			self.party = None
		if self.party and not self.recipient_name:
			self.recipient_name = get_party_name(self.party_type, self.party)
		self.validate_dates()
		self.warn_duplicates()
		self.set_status()

	def before_update_after_submit(self):
		self.validate_dates()
		self.set_status()

	def on_submit(self):
		self.set_status(update=True)

	def on_cancel(self):
		self.set_status(update=True)

	def validate_dates(self):
		if self.received_date and not self.sent_date:
			frappe.throw(_("Please set Sent Date before Received Date"))
		if self.sent_date and self.received_date and getdate(self.received_date) < getdate(self.sent_date):
			frappe.throw(_("Received Date cannot be before Sent Date"))

	def set_status(self, update=False):
		if self.docstatus == 0:
			status = "Draft"
		elif self.docstatus == 2:
			status = "Cancelled"
		elif self.received_date:
			status = "Received"
		elif self.sent_date:
			status = "Sent"
		else:
			status = "To Send"

		if update:
			self.db_set("status", status, update_modified=False)
		else:
			self.status = status

	def warn_duplicates(self):
		"""เตือน (ไม่บล็อก) เมื่อเอกสารเคยอยู่ในใบนำส่งอื่นที่ส่งให้ผู้รับเดียวกัน"""
		refs = {(d.reference_doctype, d.reference_name) for d in self.transmittal_list if d.reference_name}
		if not refs:
			return

		found = []
		for row in get_sent_references(self.recipient_type, self.party, exclude=self.name):
			if (row.reference_doctype, row.reference_name) in refs:
				found.append(f"{row.reference_name} ({row.parent})")

		if found:
			frappe.msgprint(
				_("These documents are already in another transmittal to the same recipient: {0}").format(
					", ".join(found)
				),
				indicator="orange",
				alert=True,
			)


def get_party_name(party_type, party):
	field = {"Customer": "customer_name", "Supplier": "supplier_name"}.get(party_type)
	return frappe.db.get_value(party_type, party, field) if field else party


def get_sent_references(recipient_type, party=None, exclude=None, reference_doctype=None):
	"""แถวเอกสารอ้างอิงในใบนำส่งที่ยังไม่ยกเลิก ของผู้รับประเภทนี้ (และคู่ค้านี้ ถ้าระบุ)"""
	parent = frappe.qb.DocType("Transmittal")
	child = frappe.qb.DocType("Transmittal List")
	query = (
		frappe.qb.from_(child)
		.join(parent)
		.on(parent.name == child.parent)
		.select(child.reference_doctype, child.reference_name, child.parent)
		.where(child.parenttype == "Transmittal")
		.where(parent.docstatus < 2)
		.where(parent.recipient_type == recipient_type)
		.where(child.reference_name.isnotnull())
	)
	if party:
		query = query.where(parent.party == party)
	if exclude:
		query = query.where(parent.name != exclude)
	if reference_doctype:
		query = query.where(child.reference_doctype == reference_doctype)
	return query.run(as_dict=True)


def _wht_amounts(names):
	if not names:
		return {}
	item = frappe.qb.DocType("Withholding Tax Items")
	rows = (
		frappe.qb.from_(item)
		.select(item.parent, Sum(item.tax_amount).as_("amount"))
		.where(item.parent.isin(list(names)))
		.where(item.parenttype == "Withholding Tax Cert")
		.groupby(item.parent)
	).run(as_dict=True)
	return {r.parent: flt(r.amount) for r in rows}


def _source_fields(doctype, cfg):
	meta = frappe.get_meta(doctype)
	fields = {"name", "docstatus", cfg["date"]}
	for key in ("document_no", "party", "party_name", "project"):
		if cfg.get(key) and (cfg[key] == "name" or meta.has_field(cfg[key])):
			fields.add(cfg[key])
	amount = cfg.get("amount")
	for f in (amount if isinstance(amount, tuple) else (amount,)):
		if f and meta.has_field(f):
			fields.add(f)
	return list(fields)


def _to_row(doctype, cfg, doc, wht=None):
	amount = cfg.get("amount")
	if isinstance(amount, tuple):
		value = sum(flt(doc.get(f)) for f in amount)
	elif amount:
		value = flt(doc.get(amount))
	else:
		value = flt((wht or {}).get(doc.name))

	party = doc.get(cfg["party_name"]) if cfg.get("party_name") else None
	if not party and doc.get(cfg["party"]):
		party = get_party_name(cfg["party_type"], doc.get(cfg["party"]))

	return {
		"reference_doctype": doctype,
		"reference_name": doc.name,
		"document_no": doc.get(cfg["document_no"]) or doc.name,
		"date": doc.get(cfg["date"]),
		"description": " ".join(filter(None, [_(doctype), party])),
		"amount": value,
	}


def _generic_row(doctype, name):
	doc = frappe.get_doc(doctype, name)
	meta = doc.meta
	date_field = next(
		(f for f in ("posting_date", "transaction_date", "date") if meta.has_field(f)),
		None,
	)
	amount_field = next((f for f in ("grand_total", "total_amount", "paid_amount", "amount") if meta.has_field(f)), None)
	title = doc.get(meta.title_field) if meta.title_field else None
	return {
		"reference_doctype": doctype,
		"reference_name": name,
		"document_no": name,
		"date": doc.get(date_field) if date_field else None,
		"description": " ".join(filter(None, [_(doctype), title if title != name else None])),
		"amount": flt(doc.get(amount_field)) if amount_field else 0,
	}


@frappe.whitelist()
def get_reference_details(reference_doctype: str, reference_name: str):
	"""ค่าของแถวเมื่อผู้ใช้เลือกเอกสารอ้างอิงเอง"""
	frappe.has_permission(reference_doctype, "read", reference_name, throw=True)
	cfg = SOURCES.get(reference_doctype)
	if not cfg:
		return _generic_row(reference_doctype, reference_name)

	doc = frappe.db.get_value(
		reference_doctype, reference_name, _source_fields(reference_doctype, cfg), as_dict=True
	)
	wht = _wht_amounts([reference_name]) if reference_doctype == "Withholding Tax Cert" else None
	return _to_row(reference_doctype, cfg, doc, wht)


@frappe.whitelist()
def get_source_doctypes():
	return [dt for dt in SOURCES if frappe.db.exists("DocType", dt)]


@frappe.whitelist()
def get_documents(
	source: str,
	company: str,
	recipient_type: str | None = None,
	party: str | None = None,
	from_date: str | None = None,
	to_date: str | None = None,
	project: str | None = None,
	include_sent: int = 0,
	exclude: str | None = None,
):
	"""เอกสารที่ Submit แล้วสำหรับปุ่ม "ดึงเอกสาร" (ไม่รวมที่เคยนำส่งให้ผู้รับเดียวกัน เว้นแต่ include_sent)"""
	cfg = SOURCES.get(source)
	if not cfg:
		frappe.throw(_("{0} cannot be added from this button").format(_(source)))

	meta = frappe.get_meta(source)
	filters = {"docstatus": 1}
	if meta.has_field("company"):
		filters["company"] = company
	if from_date and to_date:
		filters[cfg["date"]] = ["between", [from_date, to_date]]
	elif from_date:
		filters[cfg["date"]] = [">=", from_date]
	elif to_date:
		filters[cfg["date"]] = ["<=", to_date]
	# คู่ค้าของใบนำส่งใช้กรองเฉพาะเอกสารที่เป็นคู่ค้าประเภทเดียวกัน (ลูกค้า/ผู้ขาย)
	if party and PARTY_TYPES.get(recipient_type) == cfg["party_type"]:
		filters[cfg["party"]] = party
	if project and cfg.get("project"):
		filters[cfg["project"]] = project

	docs = frappe.get_list(
		source,
		filters=filters,
		fields=_source_fields(source, cfg),
		order_by=f"{cfg['date']} asc, name asc",
		limit_page_length=500,
	)

	if recipient_type and not int(include_sent):
		sent = {
			r.reference_name
			for r in get_sent_references(
				recipient_type,
				party if PARTY_TYPES.get(recipient_type) else None,
				exclude=exclude,
				reference_doctype=source,
			)
		}
		docs = [d for d in docs if d.name not in sent]

	wht = _wht_amounts([d.name for d in docs]) if source == "Withholding Tax Cert" else None
	return [_to_row(source, cfg, d, wht) for d in docs]


@frappe.whitelist()
def get_transmittals_for(reference_doctype: str, reference_name: str):
	"""ใบนำส่งที่มีเอกสารนี้ (ใช้แจ้งในฟอร์มเอกสารต้นทาง)"""
	return frappe.get_list(
		"Transmittal",
		filters=[
			["docstatus", "<", 2],
			["Transmittal List", "reference_doctype", "=", reference_doctype],
			["Transmittal List", "reference_name", "=", reference_name],
		],
		fields=["name", "recipient_type", "recipient_name", "status", "sent_date", "received_date"],
		order_by="creation desc",
		distinct=True,
	)
