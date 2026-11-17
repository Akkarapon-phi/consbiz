# Copyright (c) 2026, Siricons and contributors
# For license information, please see license.txt

"""หมวดผู้รับเหมาช่วงของแอปออฟฟิศ (/conserp/subcontract): สัญญา (agreements), ใบเบิกงวด (claims), ใบงานเพิ่ม (variations)
หน้าจอครอบ Subcontract Agreement / Claim / Variation กฎอยู่ใน consbiz/subcontract.py, consbiz/subcontract_variation.py
1 หน้าต่อเอกสาร: ร่าง = แก้ในหน้าเดียวกัน, Submit แล้ว = ดู + ปุ่มสร้าง PO / จ่ายเงินล่วงหน้า / สร้าง PI
ใบเบิก/ใบงานเพิ่ม: `preview_claim` / `preview_variation` คำนวณยอดจากค่าที่กรอก (ยังไม่บันทึก) ให้ฟอร์มแสดงยอดทันที"""

import frappe
from frappe import _
from frappe.utils import cint, flt

from consbiz import store_app, subcontract

LIST_LIMIT = 500
KINDS = {
	"agreements": {
		"doctype": "Subcontract Agreement",
		"list": (
			"title",
			"supplier",
			"supplier_name",
			"project",
			"company",
			"contract_date",
			"total_amount",
			"claimed_amount",
			"progress_percent",
			"status",
			"billing_method",
		),
		"date": "contract_date",
	},
	"claims": {
		"doctype": "Subcontract Claim",
		"list": (
			"subcontract_agreement",
			"title",
			"supplier",
			"supplier_name",
			"project",
			"company",
			"claim_no",
			"posting_date",
			"gross_amount",
			"net_amount",
			"status",
			"purchase_invoice",
			"from_contractor",
		),
		"date": "posting_date",
	},
	"variations": {
		"doctype": "Subcontract Variation",
		"list": (
			"subcontract_agreement",
			"title",
			"supplier",
			"supplier_name",
			"project",
			"company",
			"revision_no",
			"posting_date",
			"addition_amount",
			"revised_amount",
			"status",
		),
		"date": "posting_date",
	},
}
AGREEMENT_FIELDS = (
	"title",
	"supplier",
	"contract_no",
	"project",
	"contract_date",
	"start_date",
	"end_date",
	"billing_method",
	"retention_percent",
	"retention_cap_percent",
	"wht_percent",
	"advance_percent",
	"advance_recovery_percent",
	"penalty_per_day",
	"warranty_days",
	"remarks",
)
AGREEMENT_ITEM_FIELDS = ("wbs", "item_name", "uom", "qty", "rate")
MILESTONE_FIELDS = ("description", "percent", "target_date", "condition")
CLAIM_FIELDS = (
	"subcontract_agreement",
	"posting_date",
	"period_from",
	"period_to",
	"milestone",
	"penalty_days",
	"remarks",
)
VARIATION_FIELDS = ("subcontract_agreement", "posting_date", "variation_order", "reason")
VARIATION_ITEM_FIELDS = ("wbs", "item_name", "uom", "qty", "rate")
SEARCH = {
	"Supplier": "supplier_name",
	"Project": "project_name",
	"UOM": "uom_name",
	"Variation Order": "title",
}
STATUS = {
	"Draft": (_("ร่าง"), "gray"),
	"Active": (_("ดำเนินการ"), "blue"),
	"Completed": (_("เบิกครบ"), "green"),
	"Closed": (_("ปิดสัญญา"), "gray"),
	"Pending Review": (_("ผรม. ส่งมา รอตรวจ"), "amber"),
	"Returned": (_("ส่งกลับ ผรม. แก้"), "rose"),
	"Approved": (_("อนุมัติแล้ว"), "blue"),
	"Cancelled": (_("ยกเลิก"), "rose"),
}


def config_of(kind):
	if kind not in KINDS:
		frappe.throw(_("ไม่รองรับเอกสารชนิดนี้"), frappe.PermissionError)
	return KINDS[kind]


def readable_kinds():
	return [kind for kind, config in KINDS.items() if frappe.has_permission(config["doctype"], "read")]


def boot_permissions():
	"""boot.subcontract: ชนิดที่อ่านได้ = มีเมนู, create = ปุ่มสร้าง"""
	return {
		kind: {"create": bool(frappe.has_permission(KINDS[kind]["doctype"], "create"))}
		for kind in readable_kinds()
	}


def label_status(row, invoice_status=None):
	label, tone = STATUS.get(row.get("status"), STATUS["Draft"])
	if row.get("status") == "Draft" and row.get("from_contractor"):
		label, tone = _("ผรม. กำลังร่าง"), "gray"
	if row.get("status") == "Approved" and row.get("purchase_invoice"):
		label, tone = (_("ตั้งหนี้แล้ว"), "green") if invoice_status == 1 else (_("ร่างใบแจ้งหนี้แล้ว"), "teal")
	row["status_label"], row["status_tone"] = label, tone
	return row


@frappe.whitelist()
def get_list(kind, company=None, project=None, agreement=None):
	config = config_of(kind)
	frappe.has_permission(config["doctype"], "read", throw=True)
	filters = {}
	if company:
		filters["company"] = company
	if project:
		filters["project"] = project
	if agreement and kind in ("claims", "variations"):
		filters["subcontract_agreement"] = agreement
	rows = frappe.get_list(
		config["doctype"],
		filters=filters,
		fields=["name", "docstatus", "modified", *config["list"]],
		order_by=f"{config['date']} desc, creation desc",
		limit_page_length=LIST_LIMIT,
	)
	invoices = {}
	if kind == "claims":
		names = [r.purchase_invoice for r in rows if r.purchase_invoice]
		if names:
			invoices = dict(
				frappe.get_all(
					"Purchase Invoice",
					filters={"name": ("in", names)},
					fields=["name", "docstatus"],
					as_list=True,
				)
			)
	return [label_status(row, invoices.get(row.get("purchase_invoice"))) for row in rows]


@frappe.whitelist()
def get_summary(company=None, project=None, **_kwargs):
	"""ตัวเลขเมนู: ใบเบิกที่รออนุมัติ (ร่าง) และใบเบิกที่อนุมัติแล้วแต่ยังไม่มีใบแจ้งหนี้"""
	if not frappe.has_permission("Subcontract Claim", "read"):
		return {}
	filters = {}
	if company:
		filters["company"] = company
	if project:
		filters["project"] = project
	# รออนุมัติ = ร่างของเจ้าหน้าที่ + ที่ ผรม. ส่งมาแล้ว (ใบที่ ผรม. ยังร่าง/แก้อยู่ไม่นับ)
	draft = len(
		[
			row
			for row in frappe.get_list(
				"Subcontract Claim",
				filters={**filters, "docstatus": 0},
				fields=["from_contractor", "status"],
				limit=999,
			)
			if not contractor_busy(row)
		]
	)
	to_invoice = len(
		frappe.get_list(
			"Subcontract Claim",
			filters={**filters, "docstatus": 1, "purchase_invoice": ("is", "not set")},
			pluck="name",
			limit=999,
		)
	)
	out = {"claims_draft": {"count": draft}, "to_invoice": {"count": to_invoice}}
	if frappe.has_permission("Subcontract Variation", "read"):
		out["variations_draft"] = {
			"count": len(
				frappe.get_list(
					"Subcontract Variation", filters={**filters, "docstatus": 0}, pluck="name", limit=999
				)
			)
		}
	return out


# ---------------------------------------------------------------- สัญญา


def doc_status(doctype, name):
	return frappe.db.get_value(doctype, name, "docstatus") if name else None


def po_revision(po_name):
	"""ฉบับแก้ไขของ PO และสถานะส่งผู้รับเหมา (ฝ่ายจัดซื้อกด "ส่งผู้รับเหมาแล้ว")"""
	if not po_name or not frappe.get_meta("Purchase Order").has_field("custom_revision_pending"):
		return None
	po = frappe.db.get_value(
		"Purchase Order",
		po_name,
		[
			"custom_revision as revision",
			"custom_revision_pending as pending",
			"custom_revision_sent_by as sent_by",
			"custom_revision_sent_on as sent_on",
		],
		as_dict=True,
	)
	if not po or not (cint(po.revision) or po.pending or po.sent_by):
		return None
	po.sent_by_name = frappe.utils.get_fullname(po.sent_by) if po.sent_by else None
	return po


def serialize_agreement(doc):
	out = {
		field: doc.get(field)
		for field in (
			*AGREEMENT_FIELDS,
			"supplier_name",
			"company",
			"construction_management",
			"status",
			"total_amount",
			"advance_amount",
			"purchase_order",
			"claimed_amount",
			"progress_percent",
			"retention_held",
			"advance_recovered",
			"penalty_total",
			"amended_from",
			"original_amount",
			"variation_amount",
			"revision",
			"closed_on",
			"close_reason",
			"warranty_end",
		)
	}
	out.update(
		name=doc.name if not doc.is_new() else None,
		docstatus=doc.docstatus,
		modified=str(doc.modified or ""),
		project_name=doc.project and frappe.db.get_value("Project", doc.project, "project_name"),
		items=[
			{
				**{f: row.get(f) for f in AGREEMENT_ITEM_FIELDS},
				"name": row.name,
				"variation": row.variation,
				"amount": row.amount,
				"claimed_qty": row.claimed_qty,
				"claimed_amount": row.claimed_amount,
			}
			for row in doc.items
		],
		milestones=[
			{
				**{f: m.get(f) for f in MILESTONE_FIELDS},
				"name": m.name,
				"amount": m.amount,
				"subcontract_claim": m.subcontract_claim,
			}
			for m in doc.milestones
		],
	)
	label_status(out)
	return out


def agreement_actions(doc):
	can_write = bool(doc.has_permission("write"))
	can_approve = doc.docstatus == 1 and bool(doc.has_permission("submit"))
	po_status = doc_status("Purchase Order", doc.purchase_order)
	out = {
		"can_close": can_approve and doc.status in ("Active", "Completed"),
		"can_reopen": can_approve and doc.status == "Closed",
		"can_vary": doc.docstatus == 1
		and doc.status in ("Active", "Completed")
		and bool(frappe.has_permission("Subcontract Variation", "create")),
		"po_revision": po_revision(doc.purchase_order),
		"can_delete": store_app.can_delete(doc),
		"can_edit": doc.docstatus == 0 and can_write,
		"can_submit": doc.docstatus == 0 and bool(doc.has_permission("submit")),
		"can_cancel": doc.docstatus == 1 and bool(doc.has_permission("cancel")),
		"po_status": po_status,
		"can_make_po": doc.docstatus == 1
		and can_write
		and po_status not in (0, 1)
		and bool(frappe.has_permission("Purchase Order", "create")),
		"advance_paid": subcontract.advance_paid(doc),
		# ปุ่มลิงก์ผู้รับเหมา (contractor_link)
		"can_share_link": doc.docstatus == 1 and doc.status != "Closed",
		"can_claim": doc.docstatus == 1
		and doc.status == "Active"
		and bool(frappe.has_permission("Subcontract Claim", "create")),
	}
	out["can_pay_advance"] = (
		doc.docstatus == 1
		and flt(doc.advance_amount) > out["advance_paid"] + 0.005
		and po_status == 1
		and bool(frappe.has_permission("Payment Entry", "create"))
	)
	return out


@frappe.whitelist()
def get_agreement(name=None, company=None, project=None):
	if name:
		doc = frappe.get_doc("Subcontract Agreement", name)
		doc.check_permission("read")
	else:
		doc = frappe.new_doc("Subcontract Agreement")
		doc.check_permission("create")
		if project:
			doc.project = project
			subcontract.set_company(doc)
		elif company:
			doc.company = company
	out = {"doc": serialize_agreement(doc), **agreement_actions(doc)}
	if name:
		out["claims"] = get_list("claims", agreement=name)
		if frappe.has_permission("Subcontract Variation", "read"):
			out["variations"] = get_list("variations", agreement=name)
	return out


@frappe.whitelist(methods=["POST"])
def close_agreement(name, reason=None):
	subcontract.close_agreement(name, reason)
	return get_agreement(name)


@frappe.whitelist(methods=["POST"])
def reopen_agreement(name):
	subcontract.reopen_agreement(name)
	return get_agreement(name)


def link_info(doc):
	"""ลิงก์ผู้รับเหมาของสัญญา (แอป /contractor ไม่ต้อง login) ใช้ได้เมื่อ Submit แล้วและยังไม่ปิด
	ส่งเฉพาะ path หน้าจอต่อโดเมนที่เจ้าหน้าที่เปิดอยู่เอง (get_url ของเครื่อง dev ใส่พอร์ต 8000 ที่คนนอกเข้าไม่ได้)"""
	valid = doc.docstatus == 1 and doc.status != "Closed"
	return {
		"path": f"/contractor/k/{doc.contractor_token}" if doc.contractor_token else None,
		"valid": valid,
		"can_reset": doc.docstatus == 1 and bool(doc.has_permission("submit")),
	}


@frappe.whitelist(methods=["POST"])
def contractor_link(name):
	"""ลิงก์ของสัญญา (สร้างครั้งแรกเมื่อมีคนขอ) ผู้ที่อ่านสัญญาได้ส่งลิงก์ให้ผู้รับเหมาได้"""
	doc = frappe.get_doc("Subcontract Agreement", name)
	doc.check_permission("read")
	if doc.docstatus != 1 or doc.status == "Closed":
		frappe.throw(_("ลิงก์ผู้รับเหมาใช้ได้กับสัญญาที่ Submit แล้วและยังไม่ปิดเท่านั้น"))
	if not doc.contractor_token:
		doc.db_set("contractor_token", frappe.generate_hash(length=32), update_modified=False)
	return link_info(doc)


@frappe.whitelist(methods=["POST"])
def reset_contractor_link(name):
	"""สร้างลิงก์ใหม่ ลิงก์เดิมใช้ไม่ได้ทันที (ลิงก์หลุด/เปลี่ยนผู้ติดต่อ) เฉพาะผู้อนุมัติสัญญา"""
	doc = frappe.get_doc("Subcontract Agreement", name)
	doc.check_permission("submit")
	if doc.docstatus != 1 or doc.status == "Closed":
		frappe.throw(_("ลิงก์ผู้รับเหมาใช้ได้กับสัญญาที่ Submit แล้วและยังไม่ปิดเท่านั้น"))
	doc.db_set("contractor_token", frappe.generate_hash(length=32), update_modified=False)
	doc.add_comment("Info", _("สร้างลิงก์ผู้รับเหมาใหม่ (ลิงก์เดิมใช้ไม่ได้แล้ว)"))
	return link_info(doc)


@frappe.whitelist(methods=["POST"])
def save_agreement(data, submit=0):
	data = store_app.parse(data)
	if data.get("name"):
		doc = frappe.get_doc("Subcontract Agreement", data["name"])
		if doc.docstatus != 0:
			frappe.throw(_("สัญญานี้ Submit แล้ว แก้ไม่ได้"))
		if data.get("modified") and str(doc.modified) != data["modified"]:
			frappe.throw(_("สัญญานี้ถูกแก้ไขจากที่อื่น โหลดใหม่ก่อนบันทึก"))
	else:
		doc = frappe.new_doc("Subcontract Agreement")
	for field in AGREEMENT_FIELDS:
		if field in data:
			doc.set(field, data[field])
	for table, fields in (("items", AGREEMENT_ITEM_FIELDS), ("milestones", MILESTONE_FIELDS)):
		existing = {row.name for row in doc.get(table)}
		doc.set(table, [])
		for row in data.get(table) or []:
			values = {f: row.get(f) for f in fields}
			if row.get("name") in existing:
				values["name"] = row["name"]
			doc.append(table, values)
	if doc.billing_method != "Milestone":
		doc.set("milestones", [])
	doc.save()
	if cint(submit):
		doc.submit()
	return get_agreement(doc.name)


# ---------------------------------------------------------------- ใบเบิก


def serialize_claim(doc):
	fields = (
		*CLAIM_FIELDS,
		"title",
		"supplier",
		"supplier_name",
		"project",
		"company",
		"billing_method",
		"claim_no",
		"status",
		"milestone_description",
		"milestone_percent",
		"gross_amount",
		"advance_recovery",
		"retention_amount",
		"wht_amount",
		"penalty_amount",
		"net_amount",
		"purchase_invoice",
		"from_contractor",
		"prepared_by",
		"submitted_on",
		"return_reason",
	)
	out = {field: doc.get(field) for field in fields}
	out.update(
		name=doc.name if not doc.is_new() else None,
		docstatus=doc.docstatus,
		modified=str(doc.modified or ""),
		prepared_by_name=frappe.utils.get_fullname(doc.prepared_by) if doc.prepared_by else doc.supplier_name,
		items=[
			{
				f: row.get(f)
				for f in (
					"agreement_item",
					"variation",
					"wbs",
					"item_name",
					"uom",
					"contract_qty",
					"previous_qty",
					"cumulative_qty",
					"qty",
					"remaining_qty",
					"rate",
					"amount",
					"claimed_progress",
					"actual_progress",
				)
			}
			for row in doc.items
		],
	)
	label_status(out, doc_status("Purchase Invoice", doc.purchase_invoice))
	return out


def agreement_terms(agreement):
	return {
		"name": agreement.name,
		"title": agreement.title,
		"supplier_name": agreement.supplier_name,
		"billing_method": agreement.billing_method,
		"total_amount": agreement.total_amount,
		"claimed_amount": agreement.claimed_amount,
		"retention_percent": agreement.retention_percent,
		"retention_cap_percent": agreement.retention_cap_percent,
		"wht_percent": agreement.wht_percent,
		"advance_recovery_percent": agreement.advance_recovery_percent,
		"penalty_per_day": agreement.penalty_per_day,
		"end_date": agreement.end_date,
	}


def fill_claim(doc, data):
	for field in CLAIM_FIELDS:
		if field in data and (field != "subcontract_agreement" or doc.is_new()):
			doc.set(field, data[field])
	doc.set("items", [])
	for row in data.get("items") or []:
		if row.get("agreement_item"):
			doc.append(
				"items",
				{"agreement_item": row["agreement_item"], "qty": row.get("qty")},
			)


def claim_context(doc, agreement=None):
	agreement = agreement or frappe.get_doc("Subcontract Agreement", doc.subcontract_agreement)
	out = {"agreement": agreement_terms(agreement)}
	# สัญญางวดงานที่มีงานเพิ่มแนบท้าย: ไม่เลือกงวด = เบิกเฉพาะงานเพิ่ม
	out["appendix"] = any(r.variation for r in agreement.items)
	if agreement.billing_method == "Milestone":
		free = {
			m.name
			for m in subcontract.free_milestones(agreement, exclude=doc.name if not doc.is_new() else None)
		}
		out["milestones"] = [
			{
				"value": m.name,
				"label": m.description,
				"description": f"{flt(m.percent):g}%",
				"percent": m.percent,
			}
			for m in agreement.milestones
			if m.name in free or m.name == doc.milestone
		]
	return out


def contractor_busy(doc):
	"""ใบที่ ผรม. ร่างในแอป /contractor และยังไม่ส่ง (ร่าง/ส่งกลับแก้): เจ้าหน้าที่แก้/อนุมัติไม่ได้จนกว่า ผรม. ส่ง"""
	return bool(doc.get("from_contractor")) and doc.get("status") in ("Draft", "Returned")


def claim_actions(doc):
	can_write = bool(doc.has_permission("write"))
	pi_status = doc_status("Purchase Invoice", doc.purchase_invoice)
	busy = contractor_busy(doc)
	return {
		"can_delete": store_app.can_delete(doc) and not doc.from_contractor,
		"can_edit": doc.docstatus == 0 and can_write and not busy,
		"can_submit": doc.docstatus == 0 and bool(doc.has_permission("submit")) and not busy,
		"can_return": doc.docstatus == 0 and can_write and doc.status == "Pending Review",
		"contractor_busy": doc.docstatus == 0 and busy,
		"can_cancel": doc.docstatus == 1 and bool(doc.has_permission("cancel")) and pi_status != 1,
		"pi_status": pi_status,
		"can_make_pi": doc.docstatus == 1
		and pi_status not in (0, 1)
		and bool(frappe.has_permission("Purchase Invoice", "create")),
	}


@frappe.whitelist()
def get_claim(name=None, agreement=None):
	if name:
		doc = frappe.get_doc("Subcontract Claim", name)
		doc.check_permission("read")
	else:
		if not agreement:
			frappe.throw(_("เลือกสัญญาก่อน"))
		doc = frappe.new_doc("Subcontract Claim")
		doc.subcontract_agreement = agreement
		doc.check_permission("create")
		try:
			# ค่าตั้งต้น: เติมรายการและยอด (Measured = ปริมาณเท่างวดก่อน, Milestone = งวดแรกที่ว่าง)
			ctx = claim_context(doc)
			if ctx.get("milestones"):
				doc.milestone = ctx["milestones"][0]["value"]
			doc.run_method("validate")
		except frappe.ValidationError:
			pass
		frappe.clear_messages()
	return {"doc": serialize_claim(doc), **claim_context(doc), **claim_actions(doc)}


@frappe.whitelist(methods=["POST"])
def return_claim(name, reason):
	subcontract.return_claim(name, reason)
	return get_claim(name)


@frappe.whitelist(methods=["POST"])
def preview_claim(data):
	"""คำนวณยอดจากค่าที่กรอก (ไม่บันทึก) ข้อผิดพลาดส่งกลับเป็นข้อความ ไม่ throw"""
	data = store_app.parse(data)
	if data.get("name"):
		doc = frappe.get_doc("Subcontract Claim", data["name"])
	else:
		doc = frappe.new_doc("Subcontract Claim")
	doc.check_permission("write" if not doc.is_new() else "create")
	fill_claim(doc, data)
	error = None
	try:
		subcontract.validate_claim(doc)
	except frappe.ValidationError as e:
		error = str(e)
	frappe.clear_messages()
	return {"doc": serialize_claim(doc), "error": error}


@frappe.whitelist(methods=["POST"])
def save_claim(data, submit=0):
	data = store_app.parse(data)
	if data.get("name"):
		doc = frappe.get_doc("Subcontract Claim", data["name"])
		if doc.docstatus != 0:
			frappe.throw(_("ใบเบิกนี้อนุมัติแล้ว แก้ไม่ได้"))
		if contractor_busy(doc):
			frappe.throw(_("ผู้รับเหมากำลังแก้ใบเบิกนี้ รอผู้รับเหมาส่งก่อน"))
		if data.get("modified") and str(doc.modified) != data["modified"]:
			frappe.throw(_("ใบเบิกนี้ถูกแก้ไขจากที่อื่น โหลดใหม่ก่อนบันทึก"))
	else:
		doc = frappe.new_doc("Subcontract Claim")
	fill_claim(doc, data)
	doc.save()
	if cint(submit):
		doc.submit()
	return get_claim(doc.name)


# ---------------------------------------------------------------- ทั่วไป


def load(kind, name):
	doc = frappe.get_doc(config_of(kind)["doctype"], name)
	doc.check_permission("read")
	return doc


def view_of(kind, name):
	return {"agreements": get_agreement, "claims": get_claim, "variations": get_variation}[kind](name)


@frappe.whitelist(methods=["POST"])
def submit_doc(kind, name):
	load(kind, name).submit()
	return view_of(kind, name)


@frappe.whitelist(methods=["POST"])
def cancel_doc(kind, name):
	load(kind, name).cancel()
	return view_of(kind, name)


@frappe.whitelist(methods=["POST"])
def delete_doc(kind, name):
	store_app.delete_document(load(kind, name))


@frappe.whitelist(methods=["POST"])
def run_action(kind, name, action):
	"""ปุ่มสร้างเอกสารปลายทาง คืนชื่อเอกสารที่สร้าง + หน้าดูใหม่"""
	actions = {
		("agreements", "purchase_order"): (subcontract.make_purchase_order, "Purchase Order"),
		("agreements", "advance"): (subcontract.make_advance_payment, "Payment Entry"),
		("claims", "purchase_invoice"): (subcontract.make_purchase_invoice, "Purchase Invoice"),
	}
	if (kind, action) not in actions:
		frappe.throw(_("ไม่รองรับ"), frappe.PermissionError)
	method, doctype = actions[(kind, action)]
	created = method(name)
	return {"doctype": doctype, "name": created, "view": view_of(kind, name)}


@frappe.whitelist()
def search(doctype, txt="", status=None):
	"""ค้นหาในฟอร์ม: ผรม. / โครงการ / หน่วย / สัญญาที่เบิกได้ (Active)"""
	if not readable_kinds():
		frappe.throw(_("ไม่มีสิทธิ์"), frappe.PermissionError)
	txt = (txt or "").strip()
	if doctype == "Subcontract Agreement":
		# status = "variation": สัญญาที่ทำใบงานเพิ่มได้ (ดำเนินการ/เบิกครบ) ไม่งั้น = สัญญาที่เบิกได้
		filters = (
			{"docstatus": 1, "status": ("in", ("Active", "Completed"))}
			if status == "variation"
			else {"docstatus": 1, "status": "Active"}
		)
		rows = frappe.get_list(
			doctype,
			filters=filters,
			or_filters=[
				["name", "like", f"%{txt}%"],
				["title", "like", f"%{txt}%"],
				["supplier_name", "like", f"%{txt}%"],
			]
			if txt
			else None,
			fields=["name", "title", "supplier_name", "project"],
			order_by="modified desc",
			limit_page_length=30,
		)
		return [
			{
				"value": r.name,
				"label": f"{r.supplier_name} · {r.title}",
				"description": f"{r.name} · {r.project}",
			}
			for r in rows
		]
	label = SEARCH.get(doctype)
	if not label:
		frappe.throw(_("ค้นหา {0} ไม่ได้").format(doctype))
	filters = {"Supplier": {"disabled": 0}, "UOM": {"enabled": 1}, "Variation Order": {"docstatus": 1}}.get(
		doctype
	)
	rows = frappe.get_list(
		doctype,
		filters=filters,
		or_filters=[["name", "like", f"%{txt}%"], [label, "like", f"%{txt}%"]] if txt else None,
		fields=["name", f"{label} as label"],
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


@frappe.whitelist()
def wbs_options(project):
	"""งานย่อยในแผนของโครงการ (ช่อง WBS ของรายการในสัญญา)"""
	cm = frappe.db.get_value("Construction Management", {"project": project, "docstatus": ("<", 2)}, "name")
	if not cm:
		return []
	from consbiz.consbiz.doctype.construction_management.construction_management import get_task_options

	# หน่วยของงานในแผน: ฟอร์มเติมให้ (การตรวจปริมาณไม่ให้เกินแผนเทียบเฉพาะแถวที่หน่วยตรงกัน)
	uoms = dict(
		frappe.get_all(
			"Construction Management Task",
			filters={"parent": cm, "parenttype": "Construction Management"},
			fields=["wbs", "uom"],
			as_list=True,
		)
	)
	return [{**o, "uom": uoms.get(o["value"])} for o in get_task_options(cm)]


# ---------------------------------------------------------------- ใบงานเพิ่ม


def serialize_variation(doc):
	fields = (
		*VARIATION_FIELDS,
		"title",
		"supplier",
		"supplier_name",
		"project",
		"company",
		"revision_no",
		"status",
		"previous_amount",
		"addition_amount",
		"revised_amount",
		"purchase_order",
		"po_snapshot",
	)
	out = {field: doc.get(field) for field in fields}
	out.update(
		name=doc.name if not doc.is_new() else None,
		docstatus=doc.docstatus,
		modified=str(doc.modified or ""),
		items=[{f: row.get(f) for f in (*VARIATION_ITEM_FIELDS, "amount")} for row in doc.items],
	)
	label_status(out)
	return out


def variation_context(agreement):
	return {
		"agreement": {
			**agreement_terms(agreement),
			"project": agreement.project,
			"revision": agreement.revision,
			"purchase_order": agreement.purchase_order,
		},
		"po_revision": po_revision(agreement.purchase_order),
	}


def variation_actions(doc):
	can_write = bool(doc.has_permission("write"))
	return {
		"can_delete": store_app.can_delete(doc),
		"can_edit": doc.docstatus == 0 and can_write,
		"can_submit": doc.docstatus == 0 and bool(doc.has_permission("submit")),
		"can_cancel": doc.docstatus == 1 and bool(doc.has_permission("cancel")),
	}


@frappe.whitelist()
def get_variation(name=None, agreement=None):
	if name:
		doc = frappe.get_doc("Subcontract Variation", name)
		doc.check_permission("read")
	else:
		doc = frappe.new_doc("Subcontract Variation")
		doc.check_permission("create")
		doc.subcontract_agreement = agreement
	out = {"doc": serialize_variation(doc), **variation_actions(doc)}
	if doc.subcontract_agreement:
		agreement_doc = frappe.get_doc("Subcontract Agreement", doc.subcontract_agreement)
		agreement_doc.check_permission("read")
		if doc.is_new():
			for field in ("title", "supplier", "supplier_name", "project", "company"):
				out["doc"][field] = agreement_doc.get(field)
			out["doc"]["previous_amount"] = agreement_doc.total_amount
			out["doc"]["revision_no"] = cint(agreement_doc.revision) + 1
		out.update(variation_context(agreement_doc))
	return out


def fill_variation(doc, data):
	for field in VARIATION_FIELDS:
		if field in data and (field != "subcontract_agreement" or doc.is_new()):
			doc.set(field, data[field])
	doc.set("items", [])
	for row in data.get("items") or []:
		doc.append("items", {f: row.get(f) for f in VARIATION_ITEM_FIELDS})


@frappe.whitelist(methods=["POST"])
def preview_variation(data):
	"""คำนวณยอด + ตรวจแผนงานจากค่าที่กรอก (ไม่บันทึก) ข้อผิดพลาดส่งกลับเป็นข้อความ"""
	from consbiz import subcontract_variation

	data = store_app.parse(data)
	doc = (
		frappe.get_doc("Subcontract Variation", data["name"])
		if data.get("name")
		else frappe.new_doc("Subcontract Variation")
	)
	doc.check_permission("write" if not doc.is_new() else "create")
	fill_variation(doc, data)
	error = None
	try:
		subcontract_variation.validate(doc)
	except frappe.ValidationError as e:
		error = str(e)
	frappe.clear_messages()
	return {"doc": serialize_variation(doc), "error": error}


@frappe.whitelist(methods=["POST"])
def save_variation(data, submit=0):
	data = store_app.parse(data)
	if data.get("name"):
		doc = frappe.get_doc("Subcontract Variation", data["name"])
		if doc.docstatus != 0:
			frappe.throw(_("ใบงานเพิ่มนี้อนุมัติแล้ว แก้ไม่ได้"))
		if data.get("modified") and str(doc.modified) != data["modified"]:
			frappe.throw(_("ใบงานเพิ่มนี้ถูกแก้ไขจากที่อื่น โหลดใหม่ก่อนบันทึก"))
	else:
		doc = frappe.new_doc("Subcontract Variation")
	fill_variation(doc, data)
	doc.save()
	if cint(submit):
		doc.submit()
	return get_variation(doc.name)
