# เงินประกันผลงาน (Retention)
#
# ฝั่งผู้ว่าจ้าง: Sales Invoice    → Retention Receivable (RR) → Retention Invoice (RI) → Journal Entry รับเงินคืน
# ฝั่ง ผรม.:     Purchase Invoice → Retention Payable (RP)    → Retention Release    → Journal Entry จ่ายเงินคืน
#
# - RR / RP = ยอดที่ถูกหักไว้ในใบแจ้งหนี้ ระบบสร้างและ Submit เองตอน Submit ใบแจ้งหนี้ ไม่ลงบัญชี
#   (ยอดเข้าบัญชีเงินประกันตอนรับ/จ่ายชำระใบแจ้งหนี้ ผ่านตาราง custom_payment_entry_deduction)
# - RI / Release = ใบเบิกคืน 1 ใบรวมได้หลาย RR / RP และเบิกบางส่วนได้
#   แถว `Retention Claim Item` อ้าง RR / RP ด้วย Dynamic Link (retention_doctype + retention_reference)
# - ยอดวางบิล / รับเงินแล้ว / คงเหลือ และสถานะของ RR / RP คำนวณจากใบเบิกคืนเสมอ (update_source)
# - RI / Release เป็น Paid เมื่อ Journal Entry ที่ผูก (ช่อง journal_entry) Submit แล้ว

import frappe
from frappe import _
from frappe.query_builder.functions import Sum
from frappe.utils import add_days, cint, flt, getdate, nowdate

from consbiz.utils import thai_baht_text

SIDES = {
	"Retention Receivable": frappe._dict(
		claim="Retention Invoice",
		invoice="Sales Invoice",
		invoice_field="sales_invoice_no",
		party_type="Customer",
		party_field="customer",
		account_field="custom_retention_receivable",
	),
	"Retention Payable": frappe._dict(
		claim="Retention Release",
		invoice="Purchase Invoice",
		invoice_field="purchase_invoice_no",
		party_type="Supplier",
		party_field="supplier",
		account_field="custom_retention_payable",
	),
}
SOURCE_OF_CLAIM = {side.claim: source for source, side in SIDES.items()}
SOURCE_OF_INVOICE = {side.invoice: source for source, side in SIDES.items()}
OPEN_STATUSES = ("Active", "Overdue", "Partly Billed")


def money(value):
	return flt(value, 2)


def is_overdue(due_date):
	return bool(due_date) and getdate(due_date) < getdate(nowdate())


def set_totals(doc):
	doc.grand_total = money(sum(flt(row.amount) for row in doc.get("retention_items") or []))
	doc.in_words = thai_baht_text(doc.grand_total)


# ---------------------------------------------------------------------------
# ยอดและสถานะ
# ---------------------------------------------------------------------------


def claimed(source, names, docstatus=(1,), exclude=None, paid_only=False):
	"""{ชื่อ RR/RP: ยอดเบิกรวม} จากใบเบิกคืนที่มี docstatus ตามที่ระบุ"""
	names = [name for name in names if name]
	if not names:
		return {}
	claim_doctype = SIDES[source].claim
	item = frappe.qb.DocType("Retention Claim Item")
	claim = frappe.qb.DocType(claim_doctype)
	query = (
		frappe.qb.from_(item)
		.join(claim)
		.on(item.parent == claim.name)
		.select(item.retention_reference, Sum(item.amount))
		.where(item.parenttype == claim_doctype)
		.where(item.retention_doctype == source)
		.where(item.retention_reference.isin(names))
		.where(claim.docstatus.isin(list(docstatus)))
		.groupby(item.retention_reference)
	)
	if exclude:
		query = query.where(claim.name != exclude)
	if paid_only:
		query = query.where(claim.status == "Paid")
	return {name: money(total) for name, total in query.run()}


def source_status(docstatus, total, billed, paid, due_date):
	if docstatus == 0:
		return "Draft"
	if docstatus == 2:
		return "Cancelled"
	total = money(total)
	if money(paid) >= total:
		return "Paid"
	if money(billed) >= total:
		return "Billed"
	if is_overdue(due_date):
		return "Overdue"
	return "Partly Billed" if money(billed) > 0 else "Active"


def update_source(source, name):
	"""คำนวณยอดวางบิล / รับเงินแล้ว / คงเหลือ และสถานะของ RR / RP ใหม่จากใบเบิกคืน"""
	doc = frappe.db.get_value(source, name, ["docstatus", "grand_total", "due_date"], as_dict=True)
	if not doc:
		return None
	billed = claimed(source, [name]).get(name, 0)
	paid = claimed(source, [name], paid_only=True).get(name, 0)
	values = {
		"billed_amount": billed,
		"paid_amount": paid,
		"outstanding_amount": money(flt(doc.grand_total) - billed),
		"status": source_status(doc.docstatus, doc.grand_total, billed, paid, doc.due_date),
	}
	frappe.db.set_value(source, name, values, update_modified=False)
	return values


def claim_status(docstatus, journal_entry, due_date):
	if docstatus == 0:
		return "Draft"
	if docstatus == 2:
		return "Cancelled"
	if journal_entry and frappe.db.get_value("Journal Entry", journal_entry, "docstatus") == 1:
		return "Paid"
	return "Overdue" if is_overdue(due_date) else "Unpaid"


def update_claim(doctype, name, sources=True):
	"""สถานะของ RI / Release ตาม Journal Entry และวันครบกำหนด แล้วคำนวณ RR / RP ที่อ้างถึงใหม่"""
	doc = frappe.db.get_value(doctype, name, ["docstatus", "journal_entry", "due_date"], as_dict=True)
	if not doc:
		return None
	status = claim_status(doc.docstatus, doc.journal_entry, doc.due_date)
	frappe.db.set_value(doctype, name, "status", status, update_modified=False)
	if sources:
		source = SOURCE_OF_CLAIM[doctype]
		refs = frappe.get_all(
			"Retention Claim Item",
			filters={"parenttype": doctype, "parent": name},
			pluck="retention_reference",
			distinct=True,
		)
		for ref in refs:
			update_source(source, ref)
	return status


# ---------------------------------------------------------------------------
# RR / RP (ที่มาของเงินประกัน)
# ---------------------------------------------------------------------------


def used_by_invoice(source, invoice, exclude=None, docstatus=(0, 1)):
	"""ชื่อ RR / RP ที่มีใบแจ้งหนี้นี้อยู่แล้ว"""
	field = SIDES[source].invoice_field
	item = frappe.qb.DocType("Retention Items")
	parent = frappe.qb.DocType(source)
	query = (
		frappe.qb.from_(item)
		.join(parent)
		.on(item.parent == parent.name)
		.select(parent.name)
		.distinct()
		.where(item.parenttype == source)
		.where(item[field] == invoice)
		.where(parent.docstatus.isin(list(docstatus)))
	)
	if exclude:
		query = query.where(parent.name != exclude)
	return query.run(pluck=True)


def validate_source(doc):
	side = SIDES[doc.doctype]
	if not doc.get("retention_items"):
		frappe.throw(_("กรุณาระบุรายการเงินประกันผลงานอย่างน้อย 1 รายการ"))

	seen = set()
	for row in doc.retention_items:
		if not flt(row.amount) and flt(row.base_amount) and flt(row.retention_percent):
			row.amount = money(flt(row.base_amount) * flt(row.retention_percent) / 100)
		if money(row.amount) <= 0:
			frappe.throw(_("แถวที่ {0}: ยอดเงินประกันต้องมากกว่า 0").format(row.idx))

		invoice = row.get(side.invoice_field)
		if not invoice:
			continue
		if invoice in seen:
			frappe.throw(_("แถวที่ {0}: {1} ซ้ำกับแถวอื่น").format(row.idx, invoice))
		seen.add(invoice)

		other = used_by_invoice(doc.doctype, invoice, exclude=doc.name)
		if other:
			frappe.throw(
				_("{0} {1} ถูกใช้แล้วในเอกสาร {2}").format(
					_(side.invoice), invoice, frappe.utils.get_link_to_form(doc.doctype, other[0])
				)
			)
		values = frappe.db.get_value(side.invoice, invoice, ["company", side.party_field, "docstatus"], as_dict=True)
		if values and (values.company != doc.company or values[side.party_field] != doc.get(side.party_field)):
			frappe.throw(_("แถวที่ {0}: {1} เป็นของบริษัทหรือคู่ค้าอื่น").format(row.idx, invoice))

	set_totals(doc)
	if doc.docstatus == 0:
		doc.status = "Draft"
		doc.billed_amount = 0
		doc.paid_amount = 0
		doc.outstanding_amount = doc.grand_total


def open_claims(source, name):
	"""ใบเบิกคืน (ร่าง / Submit แล้ว) ที่อ้าง RR / RP นี้"""
	claim_doctype = SIDES[source].claim
	item = frappe.qb.DocType("Retention Claim Item")
	claim = frappe.qb.DocType(claim_doctype)
	return (
		frappe.qb.from_(item)
		.join(claim)
		.on(item.parent == claim.name)
		.select(claim.name)
		.distinct()
		.where(item.parenttype == claim_doctype)
		.where(item.retention_doctype == source)
		.where(item.retention_reference == name)
		.where(claim.docstatus < 2)
		.run(pluck=True)
	)


def before_cancel_source(doc):
	claims = open_claims(doc.doctype, doc.name)
	if claims:
		frappe.throw(
			_("ยกเลิก {0} ไม่ได้ เพราะถูกนำไปเบิกคืนในเอกสาร {1} กรุณายกเลิกหรือลบเอกสารนั้นก่อน").format(
				doc.name, ", ".join(frappe.utils.get_link_to_form(SIDES[doc.doctype].claim, c) for c in claims)
			)
		)


# ---------------------------------------------------------------------------
# สร้าง / ยกเลิก RR / RP ตามใบแจ้งหนี้ (doc_events ของ Sales Invoice / Purchase Invoice)
# ---------------------------------------------------------------------------


def make_source_from_invoice(invoice):
	source = SOURCE_OF_INVOICE[invoice.doctype]
	side = SIDES[source]
	doc = frappe.new_doc(source)
	doc.company = invoice.company
	doc.set(side.party_field, invoice.get(side.party_field))
	doc.posting_date = invoice.posting_date
	doc.project = invoice.project or next((i.project for i in invoice.items if i.get("project")), None)
	if source == "Retention Receivable":
		doc.customer_po = invoice.get("po_no")
	else:
		doc.po = next((i.purchase_order for i in invoice.items if i.get("purchase_order")), None)

	row = {
		side.invoice_field: invoice.name,
		"posting_date": invoice.posting_date,
		"description": _("เงินประกันผลงานจาก {0}").format(invoice.name),
		"base_amount": invoice.net_total,
		"retention_percent": invoice.get("custom_retention_percent"),
		"amount": invoice.get("custom_retention_amount"),
	}
	if source == "Retention Payable":
		row["reference_no"] = invoice.get("bill_no")
	doc.append("retention_items", row)
	return doc


def has_retention(invoice):
	return bool(invoice.get("custom_subject_to_retention")) and flt(invoice.get("custom_retention_amount")) > 0


def create_from_invoice(doc, method=None):
	"""on_submit ของ Sales Invoice / Purchase Invoice: สร้างและ Submit RR / RP"""
	source = SOURCE_OF_INVOICE[doc.doctype]
	if not has_retention(doc) or used_by_invoice(source, doc.name):
		return None
	retention = make_source_from_invoice(doc)
	retention.flags.ignore_permissions = True
	retention.insert()
	retention.submit()
	frappe.msgprint(
		_("สร้าง {0} {1} แล้ว").format(_(source), frappe.utils.get_link_to_form(source, retention.name)),
		indicator="green",
		alert=True,
	)
	return retention.name


def cancel_from_invoice(doc, method=None):
	"""before_cancel ของ Sales Invoice / Purchase Invoice: ยกเลิก RR / RP ที่มาจากใบนี้ (ร่าง = ลบ)"""
	source = SOURCE_OF_INVOICE[doc.doctype]
	for name in used_by_invoice(source, doc.name):
		retention = frappe.get_doc(source, name)
		if retention.docstatus == 0:
			frappe.delete_doc(source, name, ignore_permissions=True)
			continue
		if len(retention.retention_items) > 1:
			frappe.throw(
				_("{0} รวมหลายใบแจ้งหนี้ กรุณายกเลิกและแก้ไข {0} เองก่อนยกเลิก {1}").format(
					frappe.utils.get_link_to_form(source, name), doc.name
				)
			)
		retention.flags.ignore_permissions = True
		retention.cancel()
		frappe.msgprint(_("ยกเลิก {0} แล้ว").format(name), indicator="green", alert=True)


@frappe.whitelist()
def get_retention_for_invoice(doctype, name):
	"""ชื่อ RR / RP (ร่าง / Submit แล้ว) ของใบแจ้งหนี้ ใช้แสดงปุ่มในฟอร์มใบแจ้งหนี้"""
	if doctype not in SOURCE_OF_INVOICE:
		frappe.throw(_("ไม่รองรับ {0}").format(doctype))
	frappe.has_permission(doctype, "read", name, throw=True)
	names = used_by_invoice(SOURCE_OF_INVOICE[doctype], name)
	return names[0] if names else None


@frappe.whitelist()
def create_retention_for_invoice(doctype, name):
	"""ปุ่มในใบแจ้งหนี้ที่ Submit ก่อนมีการสร้างอัตโนมัติ"""
	if doctype not in SOURCE_OF_INVOICE:
		frappe.throw(_("ไม่รองรับ {0}").format(doctype))
	invoice = frappe.get_doc(doctype, name)
	invoice.check_permission("submit")
	frappe.has_permission(SOURCE_OF_INVOICE[doctype], "create", throw=True)
	if invoice.docstatus != 1:
		frappe.throw(_("กรุณา Submit {0} ก่อน").format(name))
	if not has_retention(invoice):
		frappe.throw(_("{0} ไม่มีเงินประกันผลงาน").format(name))
	return create_from_invoice(invoice) or get_retention_for_invoice(doctype, name)


# ---------------------------------------------------------------------------
# RI / Release (ใบเบิกคืน)
# ---------------------------------------------------------------------------


def source_details(source, name):
	side = SIDES[source]
	doc = frappe.db.get_value(
		source,
		name,
		["name", "docstatus", "company", side.party_field, "project", "grand_total", "posting_date", "due_date"],
		as_dict=True,
	)
	if doc:
		doc.party = doc.get(side.party_field)
		invoices = frappe.get_all(
			"Retention Items",
			filters={"parenttype": source, "parent": name},
			pluck=side.invoice_field,
			order_by="idx",
		)
		doc.invoice_no = ", ".join(i for i in invoices if i)
	return doc


def fill_claim_row(row, source, details, remaining):
	row.retention_doctype = source
	row.retention_amount = money(details.grand_total)
	row.outstanding_amount = remaining
	row.posting_date = details.posting_date
	row.due_date = details.due_date
	row.invoice_no = details.invoice_no
	if not row.description:
		row.description = _("เงินประกันผลงาน {0}").format(details.name)


def validate_claim(doc):
	source = SOURCE_OF_CLAIM[doc.doctype]
	side = SIDES[source]
	party = doc.get(side.party_field)
	if not doc.get("retention_items"):
		frappe.throw(_("กรุณาเลือกเงินประกันผลงานที่จะเบิกคืนอย่างน้อย 1 รายการ"))

	names = [row.retention_reference for row in doc.retention_items]
	duplicates = {name for name in names if names.count(name) > 1}
	if duplicates:
		frappe.throw(_("เลือก {0} ซ้ำกันหลายแถว").format(", ".join(sorted(duplicates))))

	# รวมใบเบิกที่ยังเป็นร่าง กันไม่ให้ร่าง 2 ใบเบิก RR / RP เดียวกันเกินยอด
	others = claimed(source, names, docstatus=(0, 1), exclude=doc.name)
	for row in doc.retention_items:
		details = source_details(source, row.retention_reference)
		if not details:
			frappe.throw(_("แถวที่ {0}: ไม่พบ {1} {2}").format(row.idx, _(source), row.retention_reference))
		if details.docstatus != 1:
			frappe.throw(_("แถวที่ {0}: {1} ยังไม่ได้ Submit หรือถูกยกเลิกแล้ว").format(row.idx, details.name))
		if details.company != doc.company or details.party != party:
			frappe.throw(_("แถวที่ {0}: {1} เป็นของบริษัทหรือคู่ค้าอื่น").format(row.idx, details.name))
		if doc.project and details.project and details.project != doc.project:
			frappe.throw(_("แถวที่ {0}: {1} เป็นของโครงการ {2}").format(row.idx, details.name, details.project))

		remaining = money(flt(details.grand_total) - others.get(details.name, 0))
		fill_claim_row(row, source, details, remaining)
		if not flt(row.amount):
			row.amount = remaining
		if money(row.amount) <= 0:
			frappe.throw(_("แถวที่ {0}: ยอดเบิกต้องมากกว่า 0").format(row.idx))
		if money(row.amount) > remaining:
			frappe.throw(
				_("แถวที่ {0}: ยอดเบิก {1} เกินยอดคงเหลือของ {2} ({3} รวมใบเบิกที่ยังเป็นร่าง)").format(
					row.idx,
					frappe.format_value(row.amount, {"fieldtype": "Currency"}),
					details.name,
					frappe.format_value(remaining, {"fieldtype": "Currency"}),
				)
			)

	set_totals(doc)
	if not doc.posting_date:
		doc.posting_date = nowdate()
	if cint(doc.credit_day) > 0:
		doc.due_date = add_days(doc.posting_date, cint(doc.credit_day))
	elif not doc.due_date:
		doc.due_date = doc.posting_date
	if getdate(doc.due_date) < getdate(doc.posting_date):
		frappe.throw(_("วันครบกำหนดต้องไม่ก่อนวันที่เอกสาร"))
	if doc.docstatus == 0:
		doc.status = "Draft"


def on_submit_claim(doc):
	doc.status = update_claim(doc.doctype, doc.name)


def before_cancel_claim(doc):
	if doc.journal_entry and frappe.db.get_value("Journal Entry", doc.journal_entry, "docstatus") == 1:
		frappe.throw(
			_("กรุณายกเลิก Journal Entry {0} ก่อนยกเลิก {1}").format(
				frappe.utils.get_link_to_form("Journal Entry", doc.journal_entry), doc.name
			)
		)


def on_cancel_claim(doc):
	je = doc.journal_entry
	if je and frappe.db.get_value("Journal Entry", je, "docstatus") == 0:
		doc.db_set("journal_entry", None)
		frappe.delete_doc("Journal Entry", je, ignore_permissions=True)
	doc.status = update_claim(doc.doctype, doc.name)


@frappe.whitelist()
def get_open_retentions(doctype, company, party, project=None, exclude=None):
	"""RR / RP ที่ยังเบิกคืนได้ (ยอดคงเหลือหักใบเบิกร่าง / Submit แล้วทุกใบ ยกเว้น exclude) ให้ dialog ใน RI / Release"""
	if doctype not in SOURCE_OF_CLAIM:
		frappe.throw(_("ไม่รองรับ {0}").format(doctype))
	source = SOURCE_OF_CLAIM[doctype]
	side = SIDES[source]
	frappe.has_permission(source, "read", throw=True)
	filters = {"docstatus": 1, "company": company, side.party_field: party, "status": ("in", OPEN_STATUSES)}
	if project:
		filters["project"] = project
	rows = frappe.get_list(
		source,
		filters=filters,
		fields=["name", "project", "posting_date", "due_date", "grand_total", "status"],
		order_by="posting_date asc, name asc",
	)
	used = claimed(source, [r.name for r in rows], docstatus=(0, 1), exclude=exclude)
	out = []
	for row in rows:
		row.remaining = money(flt(row.grand_total) - used.get(row.name, 0))
		if row.remaining > 0:
			row.invoice_no = source_details(source, row.name).invoice_no
			out.append(row)
	return out


def make_claim(source, source_name):
	frappe.has_permission(SIDES[source].claim, "create", throw=True)
	details = source_details(source, source_name)
	if not details or details.docstatus != 1:
		frappe.throw(_("กรุณา Submit {0} ก่อน").format(source_name))
	frappe.has_permission(source, "read", source_name, throw=True)
	side = SIDES[source]
	remaining = money(
		flt(details.grand_total) - claimed(source, [source_name], docstatus=(0, 1)).get(source_name, 0)
	)
	if remaining <= 0:
		frappe.throw(_("{0} ถูกนำไปเบิกคืนครบแล้ว").format(source_name))

	doc = frappe.new_doc(side.claim)
	doc.company = details.company
	doc.set(side.party_field, details.party)
	doc.project = details.project
	doc.posting_date = nowdate()
	if source == "Retention Receivable":
		doc.customer_po = frappe.db.get_value(source, source_name, "customer_po")
	else:
		doc.po = frappe.db.get_value(source, source_name, "po")
	row = doc.append("retention_items", {"retention_reference": source_name, "amount": remaining})
	fill_claim_row(row, source, details, remaining)
	set_totals(doc)
	return doc


@frappe.whitelist()
def make_retention_invoice(source_name, target_doc=None):
	return make_claim("Retention Receivable", source_name)


@frappe.whitelist()
def make_retention_release(source_name, target_doc=None):
	return make_claim("Retention Payable", source_name)


# ---------------------------------------------------------------------------
# Journal Entry รับ / จ่ายเงินประกันคืน
# ---------------------------------------------------------------------------


@frappe.whitelist()
def make_journal_entry(doctype, name, account, mode_of_payment=None, posting_date=None):
	"""สร้าง Journal Entry (ร่าง) ของ RI / Release แล้วผูกไว้ที่ช่อง journal_entry
	รับคืน (RI):     Dr. เงินสด/ธนาคาร        Cr. เงินประกันผลงานรอเรียกเก็บ (Company.custom_retention_receivable)
	จ่ายคืน (Release): Dr. เงินประกันผลงานค้างจ่าย (Company.custom_retention_payable)  Cr. เงินสด/ธนาคาร"""
	if doctype not in SOURCE_OF_CLAIM:
		frappe.throw(_("ไม่รองรับ {0}").format(doctype))
	doc = frappe.get_doc(doctype, name)
	doc.check_permission("submit")
	frappe.has_permission("Journal Entry", "create", throw=True)
	if doc.docstatus != 1:
		frappe.throw(_("กรุณา Submit {0} ก่อน").format(name))

	if doc.journal_entry:
		je_status = frappe.db.get_value("Journal Entry", doc.journal_entry, "docstatus")
		if je_status == 0:
			return doc.journal_entry
		if je_status == 1:
			frappe.throw(_("{0} บันทึกรับ/จ่ายเงินแล้วใน {1}").format(name, doc.journal_entry))

	source = SOURCE_OF_CLAIM[doctype]
	side = SIDES[source]
	retention_account = frappe.get_cached_value("Company", doc.company, side.account_field)
	if not retention_account:
		label = _("Retention Receivable") if source == "Retention Receivable" else _("Retention Payable")
		frappe.throw(_("กรุณาตั้งบัญชี {0} ในหน้า Company {1}").format(label, doc.company))

	paid = frappe.db.get_value("Account", account, ["company", "account_type", "is_group"], as_dict=True)
	if not paid or paid.company != doc.company or paid.is_group or paid.account_type not in ("Bank", "Cash"):
		frappe.throw(_("{0} ต้องเป็นบัญชีเงินสดหรือธนาคารของบริษัท {1}").format(account, doc.company))

	posting_date = posting_date or nowdate()
	amount = money(doc.grand_total)
	remark = f"Retention Payment for {doc.name}"
	receive = source == "Retention Receivable"

	retention_row = {"account": retention_account, "project": doc.project, "user_remark": remark}
	if frappe.get_cached_value("Account", retention_account, "account_type") in ("Receivable", "Payable"):
		retention_row.update({"party_type": side.party_type, "party": doc.get(side.party_field)})
	paid_row = {"account": account, "project": doc.project, "user_remark": remark}
	if receive:
		paid_row["debit_in_account_currency"] = amount
		retention_row["credit_in_account_currency"] = amount
	else:
		retention_row["debit_in_account_currency"] = amount
		paid_row["credit_in_account_currency"] = amount

	je = frappe.new_doc("Journal Entry")
	je.voucher_type = "Bank Entry" if paid.account_type == "Bank" else "Cash Entry"
	je.company = doc.company
	je.posting_date = posting_date
	je.cheque_no = doc.name
	je.cheque_date = posting_date
	je.mode_of_payment = mode_of_payment
	je.user_remark = remark
	for row in (paid_row, retention_row) if receive else (retention_row, paid_row):
		je.append("accounts", row)
	je.insert()

	doc.db_set({"journal_entry": je.name, "mode_of_payment": mode_of_payment, "account": account})
	return je.name


def claims_of_journal_entry(journal_entry):
	return [
		(doctype, name)
		for doctype in SOURCE_OF_CLAIM
		for name in frappe.get_all(doctype, filters={"journal_entry": journal_entry}, pluck="name")
	]


def on_journal_entry_change(doc, method=None):
	"""on_submit / on_cancel ของ Journal Entry: สถานะ Paid ของ RI / Release และยอดรับ/จ่ายแล้วของ RR / RP"""
	for doctype, name in claims_of_journal_entry(doc.name):
		update_claim(doctype, name)


def before_journal_entry_cancel(doc, method=None):
	# RI / Release ที่ Submit แล้วผูก JE ไว้ (ช่อง journal_entry) ไม่ให้ Frappe กันการยกเลิก JE
	doc.ignore_linked_doctypes = tuple(doc.get("ignore_linked_doctypes") or ()) + tuple(SOURCE_OF_CLAIM)


def on_journal_entry_trash(doc, method=None):
	# ลบ JE ร่าง: ปลดการผูกก่อน Frappe ตรวจ link (on_trash ทำงานก่อน)
	for doctype, name in claims_of_journal_entry(doc.name):
		frappe.db.set_value(doctype, name, "journal_entry", None, update_modified=False)


# ---------------------------------------------------------------------------
# งานรายวัน
# ---------------------------------------------------------------------------


def update_overdue():
	"""scheduler รายวัน: Active → Overdue เมื่อเลยวันครบกำหนด (RR / RP / RI / Release)"""
	for source in SIDES:
		for name in frappe.get_all(source, filters={"docstatus": 1, "status": ("in", OPEN_STATUSES)}, pluck="name"):
			update_source(source, name)
	for doctype in SOURCE_OF_CLAIM:
		for name in frappe.get_all(
			doctype, filters={"docstatus": 1, "status": ("in", ("Unpaid", "Overdue"))}, pluck="name"
		):
			update_claim(doctype, name, sources=False)
