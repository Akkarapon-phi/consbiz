# Copyright (c) 2026, Siricons and contributors
# For license information, please see license.txt

"""เงินประกันผลงานในแอปออฟฟิศ: หมวดบัญชี (/conserp/accounting) เห็นทั้ง 2 ฝั่ง
หมวดขายเห็นฝั่งรับ (ผู้ว่าจ้างหักเรา) หมวดจัดซื้อเห็นฝั่งจ่าย (เราหัก ผรม.) ใช้หน้าจอและ API ชุดเดียวกัน
สิทธิ์ของแต่ละฝั่ง = สิทธิ์ของ DocType ฝั่งนั้น (ตั้งได้ในหน้าตั้งค่าของแอป หมวดขาย/จัดซื้อ/บัญชี)

ฝั่งรับ (in):  Retention Receivable (rr, ระบบสร้างตอน Submit ใบแจ้งหนี้ขาย) → Retention Invoice (ri, ใบขอคืน) → JE รับเงิน
ฝั่งจ่าย (out): Retention Payable (rp, ระบบสร้างตอน Submit ใบแจ้งหนี้ซื้อ) → Retention Release (rl, ใบคืน) → JE จ่ายเงิน
กฎ/ยอด/สถานะทั้งหมดอยู่ consbiz/retention.py ไฟล์นี้เป็นหน้าจอครอบเท่านั้น"""

import json

import frappe
from frappe import _
from frappe.utils import cint, flt, getdate, nowdate

from consbiz import retention, store_app

LIST_LIMIT = 500
SIDES = {
	"in": frappe._dict(
		source="Retention Receivable",
		claim="Retention Invoice",
		party_field="customer",
		party_type="Customer",
		party_name="customer_name",
		invoice="Sales Invoice",
		invoice_field="sales_invoice_no",
		ref_field="customer_po",
	),
	"out": frappe._dict(
		source="Retention Payable",
		claim="Retention Release",
		party_field="supplier",
		party_type="Supplier",
		party_name="supplier_name",
		invoice="Purchase Invoice",
		invoice_field="purchase_invoice_no",
		ref_field="po",
	),
}
# ชนิดเอกสารในหน้าจอ (params.type) → (ฝั่ง, source / claim)
TYPES = {"rr": ("in", "source"), "ri": ("in", "claim"), "rp": ("out", "source"), "rl": ("out", "claim")}
TYPE_OF = {SIDES[side][role]: key for key, (side, role) in TYPES.items()}
# หน้ารายการ (view ใน sections.js) → ฝั่ง
LISTS = {
	"acc-retention-in": "in",
	"acc-retention-out": "out",
	"sell-retention": "in",
	"buy-retention": "out",
}
SOURCE_STATUS = {
	"in": {
		"Draft": (_("ร่าง"), "gray"),
		"Active": (_("ยังไม่ถึงกำหนดคืน"), "blue"),
		"Overdue": (_("ถึงกำหนดขอคืน"), "amber"),
		"Partly Billed": (_("ขอคืนบางส่วน"), "teal"),
		"Billed": (_("ขอคืนครบ รอรับเงิน"), "teal"),
		"Paid": (_("รับคืนแล้ว"), "green"),
		"Cancelled": (_("ยกเลิก"), "rose"),
	},
	"out": {
		"Draft": (_("ร่าง"), "gray"),
		"Active": (_("ยังไม่ถึงกำหนดคืน"), "blue"),
		"Overdue": (_("ถึงกำหนดคืน ผรม."), "amber"),
		"Partly Billed": (_("คืนบางส่วน"), "teal"),
		"Billed": (_("ทำใบคืนครบ รอจ่าย"), "teal"),
		"Paid": (_("จ่ายคืนแล้ว"), "green"),
		"Cancelled": (_("ยกเลิก"), "rose"),
	},
}
CLAIM_STATUS = {
	"in": {
		"Draft": (_("ร่าง"), "gray"),
		"Unpaid": (_("รอรับเงิน"), "blue"),
		"Overdue": (_("เลยกำหนดรับเงิน"), "rose"),
		"Paid": (_("รับเงินแล้ว"), "green"),
		"Cancelled": (_("ยกเลิก"), "rose"),
	},
	"out": {
		"Draft": (_("ร่าง"), "gray"),
		"Unpaid": (_("รอจ่ายเงิน"), "blue"),
		"Overdue": (_("เลยกำหนดจ่าย"), "rose"),
		"Paid": (_("จ่ายเงินแล้ว"), "green"),
		"Cancelled": (_("ยกเลิก"), "rose"),
	},
}
SEARCH = {"Customer": "customer_name", "Supplier": "supplier_name", "Project": "project_name"}


def type_of(key):
	if key not in TYPES:
		frappe.throw(_("ไม่รองรับเอกสารชนิดนี้"), frappe.PermissionError)
	side, role = TYPES[key]
	return side, role, SIDES[side][role]


def can_read(doctype):
	return bool(frappe.has_permission(doctype, "read"))


def readable_sides():
	"""ฝั่งที่ผู้ใช้อ่านได้อย่างน้อย 1 ชนิด (เงินประกันที่ถูกหัก หรือใบขอคืน/ใบคืน)"""
	return [side for side, s in SIDES.items() if can_read(s.source) or can_read(s.claim)]


def can_account():
	"""หมวดบัญชี: ผู้ที่อ่าน Journal Entry ได้ (ฝ่ายบัญชี) และเห็นเงินประกันอย่างน้อย 1 ฝั่ง"""
	return can_read("Journal Entry") and bool(readable_sides())


def boot_permissions():
	"""boot.retention: sides.<ฝั่ง> = สิทธิ์ของฝั่ง, <หน้ารายการ>.create = ปุ่มสร้างใบขอคืน/ใบคืน (KindList)"""
	sides = {}
	for side in readable_sides():
		s = SIDES[side]
		sides[side] = {
			"source": can_read(s.source),
			"claim": can_read(s.claim),
			"create": bool(frappe.has_permission(s.claim, "create")),
		}
	out = {"sides": sides}
	for view, side in LISTS.items():
		if side in sides:
			out[view] = {"create": sides[side]["create"]}
	return out


def party_names(side, parties):
	s = SIDES[side]
	parties = list({p for p in parties if p})
	if not parties:
		return {}
	return dict(
		frappe.get_all(
			s.party_type, filters={"name": ("in", parties)}, fields=["name", s.party_name], as_list=True
		)
	)


def label(side, role, row):
	statuses = (SOURCE_STATUS if role == "source" else CLAIM_STATUS)[side]
	text, tone = statuses.get(row.get("status"), statuses["Draft"])
	if role == "claim" and row.get("status") in ("Unpaid", "Overdue") and row.get("je_status") == 0:
		text, tone = (_("ร่างรายการรับเงินแล้ว") if side == "in" else _("ร่างรายการจ่ายเงินแล้ว")), "teal"
	row["status_label"], row["status_tone"] = text, tone
	return row


def scope_filters(company=None, project=None):
	filters = {}
	if company:
		filters["company"] = company
	if project:
		filters["project"] = project
	return filters


def child_values(child, parenttype, parents, field):
	"""{แม่: [ค่าในแถวลูกตามลำดับ]}"""
	if not parents:
		return {}
	out = {}
	for parent, value in frappe.get_all(
		child,
		filters={"parenttype": parenttype, "parent": ("in", parents)},
		fields=["parent", field],
		order_by="idx asc",
		as_list=True,
	):
		if value:
			out.setdefault(parent, []).append(value)
	return out


def je_statuses(names):
	names = [n for n in names if n]
	if not names:
		return {}
	return dict(
		frappe.get_all(
			"Journal Entry", filters={"name": ("in", names)}, fields=["name", "docstatus"], as_list=True
		)
	)


def side_rows(side, role, filters):
	s = SIDES[side]
	doctype = s[role]
	fields = [
		"name",
		"docstatus",
		"modified",
		"company",
		"project",
		"posting_date",
		"due_date",
		"grand_total",
		"status",
		f"{s.party_field} as party",
	]
	if role == "source":
		fields += ["billed_amount", "paid_amount", "outstanding_amount"]
	else:
		fields += ["journal_entry"]
	rows = frappe.get_list(
		doctype,
		filters=filters,
		fields=fields,
		order_by="modified desc",
		limit_page_length=LIST_LIMIT,
	)
	names = [r.name for r in rows]
	if role == "source":
		refs = child_values("Retention Items", doctype, names, s.invoice_field)
	else:
		refs = child_values("Retention Claim Item", doctype, names, "retention_reference")
		jes = je_statuses([r.journal_entry for r in rows])
	for row in rows:
		row.type = TYPE_OF[doctype]
		row.role = role
		row.refs = ", ".join(refs.get(row.name, []))
		if role == "source":
			# ยอดที่ยังถือไว้ (ยังไม่ได้ทำใบขอคืน/ใบคืน) ร่าง = ยอดทั้งหมด
			row.amount = flt(row.outstanding_amount) if row.docstatus == 1 else flt(row.grand_total)
		else:
			row.amount = flt(row.grand_total)
			row.je_status = jes.get(row.journal_entry)
		label(side, role, row)
	return rows


@frappe.whitelist()
def get_list(kind, company=None, project=None):
	"""หน้ารายการของฝั่ง (KindList): เงินประกันที่ถูกหัก + ใบขอคืน/ใบคืน รวมกัน แยกด้วย row.type"""
	if kind not in LISTS:
		frappe.throw(_("ไม่รองรับ"), frappe.PermissionError)
	side = LISTS[kind]
	s = SIDES[side]
	if side not in readable_sides():
		frappe.throw(_("ไม่มีสิทธิ์ดูเงินประกันผลงานฝั่งนี้"), frappe.PermissionError)
	filters = scope_filters(company, project)
	rows = []
	for role in ("source", "claim"):
		if can_read(s[role]):
			rows += side_rows(side, role, filters)
	names = party_names(side, [r.party for r in rows])
	for row in rows:
		row.party_name = names.get(row.party) or row.party
	rows.sort(key=lambda r: r.modified, reverse=True)
	return rows


def side_counts(side, company=None, project=None):
	"""ตัวเลขเมนูของฝั่ง: เงินประกันที่ถึงกำหนดคืน (ยังไม่ได้ทำใบ) + ใบขอคืน/ใบคืนที่ยังไม่ได้รับ/จ่ายเงิน"""
	s = SIDES[side]
	filters = scope_filters(company, project)
	out = {}
	if can_read(s.source):
		out["due"] = frappe.db.count(s.source, {**filters, "docstatus": 1, "status": "Overdue"})
	if can_read(s.claim):
		out["unpaid"] = frappe.db.count(
			s.claim, {**filters, "docstatus": 1, "status": ("in", ("Unpaid", "Overdue"))}
		)
		out["late"] = frappe.db.count(s.claim, {**filters, "docstatus": 1, "status": "Overdue"})
	out["count"] = out.get("due", 0) + out.get("unpaid", 0)
	return out


def sides_summary(company=None, project=None, sides=None):
	readable = readable_sides()
	return {
		f"retention_{side}": side_counts(side, company, project)
		for side in sides or SIDES
		if side in readable
	}


@frappe.whitelist()
def get_summary(company=None, project=None, **_kwargs):
	"""ตัวเลขเมนูของหมวดบัญชี"""
	return sides_summary(company, project)


# ---------------------------------------------------------------- หน้าเอกสาร


def doc_base(doc, side, role):
	s = SIDES[side]
	party = doc.get(s.party_field)
	out = {
		"type": TYPE_OF[doc.doctype],
		"side": side,
		"role": role,
		"doctype": doc.doctype,
		"name": doc.name if not doc.is_new() else None,
		"docstatus": doc.docstatus,
		"modified": str(doc.modified) if not doc.is_new() else None,
		"company": doc.company,
		"party": party,
		"party_name": party_names(side, [party]).get(party) or party,
		"project": doc.project,
		"posting_date": doc.posting_date,
		"due_date": doc.due_date,
		"ref": doc.get(s.ref_field),
		"grand_total": flt(doc.grand_total),
		"in_words": doc.in_words,
		"status": doc.status,
	}
	return label(side, role, out)


def source_view(doc, side):
	s = SIDES[side]
	out = doc_base(doc, side, "source")
	out.update(
		{
			"billed_amount": flt(doc.billed_amount),
			"paid_amount": flt(doc.paid_amount),
			"outstanding_amount": flt(doc.outstanding_amount),
			"period": doc.get("period"),
			"items": [
				{
					"invoice": row.get(s.invoice_field),
					"posting_date": row.posting_date,
					"description": frappe.utils.strip_html(row.description or ""),
					"base_amount": flt(row.base_amount),
					"retention_percent": flt(row.retention_percent),
					"amount": flt(row.amount),
					"reference_no": row.reference_no,
				}
				for row in doc.retention_items
			],
		}
	)
	claims = []
	if doc.name and can_read(s.claim):
		item = frappe.qb.DocType("Retention Claim Item")
		claim = frappe.qb.DocType(s.claim)
		rows = (
			frappe.qb.from_(item)
			.join(claim)
			.on(item.parent == claim.name)
			.select(
				claim.name,
				claim.docstatus,
				claim.status,
				claim.posting_date,
				claim.journal_entry,
				item.amount,
			)
			.where(item.parenttype == s.claim)
			.where(item.retention_reference == doc.name)
			.orderby(claim.posting_date)
			.run(as_dict=True)
		)
		jes = je_statuses([r.journal_entry for r in rows])
		for row in rows:
			row.je_status = jes.get(row.journal_entry)
			row.type = TYPE_OF[s.claim]
			claims.append(label(side, "claim", row))
	# ยอดที่ยังทำใบได้ = ยอดทั้งหมด - ใบขอคืน/ใบคืนที่ร่างหรือ Submit แล้ว
	remaining = flt(doc.grand_total) - sum(flt(c.amount) for c in claims if c.docstatus < 2)
	return {
		"doc": out,
		"claims": claims,
		"remaining": max(remaining, 0),
		"can_edit_due": doc.docstatus == 1 and bool(doc.has_permission("write")),
		"can_claim": doc.docstatus == 1
		and remaining > 0.005
		and bool(frappe.has_permission(s.claim, "create")),
	}


def claim_view(doc, side):
	from consbiz.site_app import pdf_url

	out = doc_base(doc, side, "claim")
	je_status = (
		frappe.db.get_value("Journal Entry", doc.journal_entry, "docstatus") if doc.journal_entry else None
	)
	out.update(
		{
			"credit_day": cint(doc.credit_day),
			"journal_entry": doc.journal_entry,
			"je_status": je_status,
			"mode_of_payment": doc.mode_of_payment,
			"account": doc.account,
			"bank": doc.get("bank"),
			"bank_account_no": doc.get("bank_account_no"),
			"items": [
				{
					"retention_reference": row.retention_reference,
					"invoice_no": row.invoice_no,
					"description": row.description,
					"posting_date": row.posting_date,
					"due_date": row.due_date,
					"retention_amount": flt(row.retention_amount),
					"outstanding_amount": flt(row.outstanding_amount),
					"amount": flt(row.amount),
				}
				for row in doc.retention_items
			],
		}
	)
	label(side, "claim", out)
	saved = not doc.is_new()
	can_submit = saved and bool(doc.has_permission("submit"))
	return {
		"doc": out,
		"pdf_url": pdf_url(doc.doctype, doc.name) if saved else None,
		"can_edit": doc.docstatus == 0 and (not saved or bool(doc.has_permission("write"))),
		"can_submit": doc.docstatus == 0 and can_submit,
		"can_cancel": doc.docstatus == 1 and je_status != 1 and bool(doc.has_permission("cancel")),
		"can_delete": saved and store_app.can_delete(doc),
		# make_journal_entry ต้องการสิทธิ์ Submit ใบนี้ + สร้าง Journal Entry
		"can_pay": doc.docstatus == 1
		and je_status != 1
		and can_submit
		and bool(frappe.has_permission("Journal Entry", "create")),
		"can_submit_je": bool(frappe.has_permission("Journal Entry", "submit")),
	}


def view_of(doc):
	side, role, _doctype = type_of(TYPE_OF[doc.doctype])
	return source_view(doc, side) if role == "source" else claim_view(doc, side)


@frappe.whitelist()
def get_doc(type, name=None, source=None, company=None, project=None):
	"""หน้าเอกสาร: name = เปิดใบเดิม / ใบขอคืน-ใบคืนใหม่: source = เงินประกันต้นทาง (เติมให้ 1 แถว)"""
	side, role, doctype = type_of(type)
	if name:
		doc = frappe.get_doc(doctype, name)
		doc.check_permission("read")
	elif role == "source":
		frappe.throw(_("เงินประกันผลงานสร้างจากใบแจ้งหนี้เท่านั้น"))
	elif source:
		doc = retention.make_claim(SIDES[side].source, source)
	else:
		doc = frappe.new_doc(doctype)
		doc.check_permission("create")
		doc.company = company or frappe.defaults.get_user_default("Company")
		doc.project = project
		doc.posting_date = nowdate()
	return view_of(doc)


def load(type, name):
	_side, _role, doctype = type_of(type)
	doc = frappe.get_doc(doctype, name)
	doc.check_permission("read")
	return doc


@frappe.whitelist(methods=["POST"])
def set_due_date(type, name, due_date=None):
	"""วันครบกำหนดคืนของเงินประกันที่ถูกหัก (แก้หลัง Submit ได้ สถานะถึงกำหนดคิดใหม่)"""
	doc = load(type, name)
	if TYPES[type][1] != "source":
		frappe.throw(_("ไม่รองรับ"))
	doc.check_permission("write")
	doc.due_date = due_date or None
	doc.save()
	return view_of(doc)


@frappe.whitelist()
def open_sources(type, company, party, project=None, exclude=None):
	"""เงินประกันที่ยังขอคืน/คืนได้ของคู่ค้า (ปุ่มเพิ่มรายการในใบขอคืน/ใบคืน)"""
	_side, role, doctype = type_of(type)
	if role != "claim":
		frappe.throw(_("ไม่รองรับ"))
	return retention.get_open_retentions(doctype, company, party, project or None, exclude or None)


@frappe.whitelist(methods=["POST"])
def save_claim(type, data, submit=0):
	side, role, doctype = type_of(type)
	if role != "claim":
		frappe.throw(_("ไม่รองรับ"))
	s = SIDES[side]
	data = frappe._dict(json.loads(data) if isinstance(data, str) else data)
	if data.name:
		doc = frappe.get_doc(doctype, data.name)
		doc.check_permission("write")
		if doc.docstatus != 0:
			frappe.throw(_("{0} ไม่ใช่ร่างแล้ว แก้ไขไม่ได้").format(doc.name))
		if data.modified and str(doc.modified) != str(data.modified):
			frappe.throw(_("มีผู้อื่นแก้ไข {0} ไปแล้ว กรุณาโหลดใหม่").format(doc.name))
	else:
		doc = frappe.new_doc(doctype)
		doc.check_permission("create")
	doc.company = data.company
	doc.set(s.party_field, data.party)
	doc.project = data.project or None
	doc.posting_date = data.posting_date or nowdate()
	doc.credit_day = cint(data.credit_day)
	if not doc.credit_day:
		doc.due_date = data.due_date or doc.posting_date
	doc.set(s.ref_field, data.ref or None)
	doc.set("retention_items", [])
	for row in data.get("items") or []:
		doc.append(
			"retention_items",
			{
				"retention_doctype": s.source,
				"retention_reference": row.get("retention_reference"),
				"amount": flt(row.get("amount")),
				"description": row.get("description"),
			},
		)
	doc.save()
	if cint(submit):
		doc.submit()
	return view_of(doc)


@frappe.whitelist(methods=["POST"])
def submit_doc(type, name):
	doc = load(type, name)
	doc.submit()
	return view_of(doc)


@frappe.whitelist(methods=["POST"])
def cancel_doc(type, name):
	doc = load(type, name)
	doc.cancel()
	return view_of(frappe.get_doc(doc.doctype, doc.name))


@frappe.whitelist(methods=["POST"])
def delete_doc(type, name):
	store_app.delete_document(load(type, name))


@frappe.whitelist()
def payment_options(company):
	"""บัญชีเงินสด/ธนาคาร และวิธีชำระเงินของบริษัท (dialog บันทึกรับ/จ่ายเงิน)"""
	accounts = frappe.get_list(
		"Account",
		filters={"company": company, "is_group": 0, "disabled": 0, "account_type": ("in", ("Bank", "Cash"))},
		fields=["name as value", "account_name as label", "account_type"],
		order_by="account_type asc, name asc",
		limit_page_length=0,
	)
	modes = frappe.get_list(
		"Mode of Payment", filters={"enabled": 1}, pluck="name", order_by="name asc", limit_page_length=0
	)
	return {"accounts": accounts, "modes": modes}


@frappe.whitelist(methods=["POST"])
def record_payment(type, name, account=None, mode_of_payment=None, posting_date=None, submit=1):
	"""บันทึกรับเงินคืน (ใบขอคืน) / จ่ายเงินคืน (ใบคืน): สร้าง Journal Entry แล้ว Submit ทันทีถ้ามีสิทธิ์
	มีร่าง JE อยู่แล้ว = ใช้ใบนั้น (account ที่ส่งมาไม่มีผล)"""
	doc = load(type, name)
	if TYPES[type][1] != "claim":
		frappe.throw(_("ไม่รองรับ"))
	je_name = doc.journal_entry
	if not je_name or frappe.db.get_value("Journal Entry", je_name, "docstatus") != 0:
		if not account:
			frappe.throw(_("กรุณาเลือกบัญชีเงินสด/ธนาคาร"))
		je_name = retention.make_journal_entry(
			doc.doctype, doc.name, account, mode_of_payment or None, posting_date or None
		)
	if cint(submit):
		je = frappe.get_doc("Journal Entry", je_name)
		je.check_permission("submit")
		if posting_date and getdate(je.posting_date) != getdate(posting_date):
			je.posting_date = posting_date
			je.cheque_date = posting_date
			je.save()
		je.submit()
	return {"journal_entry": je_name, "view": view_of(frappe.get_doc(doc.doctype, doc.name))}


@frappe.whitelist()
def search(doctype, txt=""):
	"""ค้นหาในฟอร์มใบขอคืน/ใบคืน: ลูกค้า / ผู้ขาย / โครงการ"""
	if not readable_sides():
		frappe.throw(_("ไม่มีสิทธิ์"), frappe.PermissionError)
	field = SEARCH.get(doctype)
	if not field:
		frappe.throw(_("ค้นหา {0} ไม่ได้").format(doctype))
	txt = (txt or "").strip()
	filters = {"Customer": {"disabled": 0}, "Supplier": {"disabled": 0}}.get(doctype)
	rows = frappe.get_list(
		doctype,
		filters=filters,
		or_filters=[["name", "like", f"%{txt}%"], [field, "like", f"%{txt}%"]] if txt else None,
		fields=["name", f"{field} as label"],
		order_by="modified desc",
		limit_page_length=30,
	)
	return [
		{
			"value": r.name,
			"label": r.label or r.name,
			"description": r.name if r.label and r.label != r.name else "",
		}
		for r in rows
	]
