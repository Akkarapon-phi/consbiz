# Copyright (c) 2026, Siricons and contributors
# For license information, please see license.txt

"""หมวดจัดซื้อ (buy) และขาย (sell) ของแอปหน้างาน (/site/buy, /site/sell) ใช้เอกสารมาตรฐานของ ERPNext

- จัดซื้อ: ขอซื้อ (Material Request ประเภท Purchase) → สั่งซื้อ (Purchase Order) → ใบแจ้งหนี้ซื้อ (Purchase Invoice)
- ขาย: ใบเสนอราคา (Quotation) → ใบสั่งขาย (Sales Order) → ใบแจ้งหนี้ขาย (Sales Invoice)
แอปทำได้: ดูรายการ/รายละเอียด, ติดตามเอกสารต้นทาง-ปลายทาง, ส่งเอกสารร่าง (Submit), PDF
สร้างเอกสารใหม่/สร้างเอกสารถัดไปทำในระบบเต็ม (ต้องเลือกผู้ขาย ราคา ภาษี)
ขอบเขต: โครงการที่เลือก (ช่องโครงการของเอกสาร) หรือทุกโครงการ (Quotation ไม่มีช่องโครงการ = ทุกโครงการเสมอ)
สิทธิ์ตามเอกสารแต่ละชนิด (get_list / get_doc ตรวจสิทธิ์ของผู้ใช้เอง)
"""

import frappe
from frappe import _
from frappe.utils import add_days, cint, flt, getdate, nowdate

from consbiz import store_app

PAGE = 30
SOON_DAYS = 7

# kind → ค่าของเอกสาร (todo = รอดำเนินการ ต่อจากเอกสารนี้)
DOCS = {
	"mr": {
		"doctype": "Material Request",
		"section": "buy",
		"project": "custom_project",
		"party": None,
		"date": "transaction_date",
		"due": "schedule_date",
		"amount": None,
		"progress": ("per_ordered", "per_received"),
		"base": {"material_request_type": "Purchase"},
		"todo": {"docstatus": 1, "status": ("in", ("Pending", "Partially Ordered"))},
	},
	"po": {
		"doctype": "Purchase Order",
		"section": "buy",
		"project": "project",
		"party": "supplier_name",
		"date": "transaction_date",
		"due": "schedule_date",
		"amount": "grand_total",
		"progress": ("per_received", "per_billed"),
		"todo": {"docstatus": 1, "status": ("in", ("To Receive and Bill", "To Receive", "To Bill"))},
	},
	"pi": {
		"doctype": "Purchase Invoice",
		"section": "buy",
		"project": "project",
		"party": "supplier_name",
		"date": "posting_date",
		"due": "due_date",
		"amount": "grand_total",
		"outstanding": "outstanding_amount",
		"extra": ("bill_no",),
		"todo": {"docstatus": 1, "outstanding_amount": (">", 0)},
	},
	"qtn": {
		"doctype": "Quotation",
		"section": "sell",
		"project": None,
		"party": "customer_name",
		"date": "transaction_date",
		"due": "valid_till",
		"amount": "grand_total",
		"todo": {"docstatus": 1, "status": ("in", ("Open", "Replied", "Partially Ordered"))},
	},
	"so": {
		"doctype": "Sales Order",
		"section": "sell",
		"project": "project",
		"party": "customer_name",
		"date": "transaction_date",
		"due": "delivery_date",
		"amount": "grand_total",
		"progress": ("per_delivered", "per_billed"),
		"todo": {"docstatus": 1, "status": ("in", ("To Deliver and Bill", "To Deliver", "To Bill"))},
	},
	"si": {
		"doctype": "Sales Invoice",
		"section": "sell",
		"project": "project",
		"party": "customer_name",
		"date": "posting_date",
		"due": "due_date",
		"amount": "grand_total",
		"outstanding": "outstanding_amount",
		"todo": {"docstatus": 1, "outstanding_amount": (">", 0)},
	},
}
KIND_OF = {config["doctype"]: kind for kind, config in DOCS.items()}

# สถานะของ ERPNext → (ป้าย, tone ของแอป) ชนิดที่ความหมายต่างกันระบุแยก
STATUS = {
	"Draft": ("ร่าง", "gray"),
	"Cancelled": ("ยกเลิก", "gray"),
	"Pending": ("รอสั่งซื้อ", "amber"),
	"Partially Ordered": ("สั่งบางส่วน", "blue"),
	"Ordered": ("สั่งครบแล้ว", "green"),
	"Partially Received": ("รับบางส่วน", "blue"),
	"Received": ("รับครบแล้ว", "green"),
	"Stopped": ("หยุด", "gray"),
	"Issued": ("เบิกแล้ว", "green"),
	"Transferred": ("โอนแล้ว", "green"),
	"On Hold": ("พักไว้", "gray"),
	"To Pay": ("รอชำระ", "amber"),
	"To Receive and Bill": ("รอรับของ/วางบิล", "amber"),
	"To Receive": ("รอรับของ", "amber"),
	"To Bill": ("รอวางบิล", "amber"),
	"To Deliver and Bill": ("รอส่งมอบ/วางบิล", "amber"),
	"To Deliver": ("รอส่งมอบ", "amber"),
	"Completed": ("เสร็จสิ้น", "green"),
	"Closed": ("ปิดแล้ว", "gray"),
	"Delivered": ("ส่งตรงแล้ว", "green"),
	"Submitted": ("ส่งแล้ว", "green"),
	"Paid": ("ชำระแล้ว", "green"),
	"Partly Paid": ("ชำระบางส่วน", "blue"),
	"Unpaid": ("ยังไม่ชำระ", "amber"),
	"Overdue": ("เกินกำหนด", "rose"),
	"Return": ("ใบลดหนี้", "gray"),
	"Debit Note Issued": ("ออกใบลดหนี้แล้ว", "gray"),
	"Credit Note Issued": ("ออกใบลดหนี้แล้ว", "gray"),
	"Unpaid and Discounted": ("ยังไม่ชำระ (ขายลด)", "amber"),
	"Partly Paid and Discounted": ("ชำระบางส่วน (ขายลด)", "blue"),
	"Overdue and Discounted": ("เกินกำหนด (ขายลด)", "rose"),
	"Internal Transfer": ("โอนภายใน", "gray"),
	"Open": ("รอตอบรับ", "amber"),
	"Replied": ("ลูกค้าตอบแล้ว", "blue"),
	"Lost": ("ไม่ได้งาน", "rose"),
	"Expired": ("หมดอายุ", "gray"),
}


def status_of(status, docstatus):
	if cint(docstatus) == 0:
		return STATUS["Draft"]
	if cint(docstatus) == 2:
		return STATUS["Cancelled"]
	label, tone = STATUS.get(status, (status or "ส่งแล้ว", "gray"))
	return _(label), tone


def config_of(kind):
	if kind not in DOCS:
		frappe.throw(_("ไม่รองรับเอกสาร {0}").format(kind))
	return DOCS[kind]


def scope_filters(config, project, scope):
	"""ขอบเขตโครงการที่เลือก: ช่องโครงการของเอกสาร (ไม่มีช่อง = ทุกโครงการ)"""
	if scope == "project" and project and config["project"]:
		store_app.check_project(project)
		return {config["project"]: project}
	return {}


def list_fields(config):
	fields = ["name", "status", "docstatus", "title", "currency", "modified"]
	fields += [f"{config['date']} as date", f"{config['due']} as due"]
	if config["party"]:
		fields.append(f"{config['party']} as party")
	if config["amount"]:
		fields.append(f"{config['amount']} as amount")
	if config.get("outstanding"):
		fields.append(f"{config['outstanding']} as outstanding")
	if config["project"]:
		fields.append(f"{config['project']} as project")
	fields += list(config.get("progress", ())) + list(config.get("extra", ()))
	return fields


def decorate(rows, config):
	today = getdate(nowdate())
	for row in rows:
		row.status_label, row.status_tone = status_of(row.status, row.docstatus)
		row.overdue = bool(
			row.docstatus == 1
			and row.get("due")
			and getdate(row.due) < today
			and (flt(row.get("outstanding")) > 0 if config.get("outstanding") else row.status_tone == "amber")
		)
	return rows


@frappe.whitelist()
def get_docs(kind, project=None, scope="project", filter="todo", search=None, start=0):
	"""รายการเอกสาร filter = todo (รอดำเนินการ) / draft / done / all ล่าสุดก่อน"""
	config = config_of(kind)
	doctype = config["doctype"]
	frappe.has_permission(doctype, "read", throw=True)
	filters = {**config.get("base", {}), **scope_filters(config, project, scope)}
	if filter == "todo":
		filters.update(config["todo"])
	elif filter == "draft":
		filters["docstatus"] = 0
	elif filter == "done":
		filters["docstatus"] = 1
		todo_names = frappe.get_list(doctype, filters={**filters, **config["todo"]}, pluck="name", limit_page_length=0)
		if todo_names:
			filters["name"] = ("not in", todo_names)
	else:
		filters["docstatus"] = ("<", 2)
	or_filters = None
	if search:
		like = f"%{search.strip()}%"
		or_filters = {"name": ("like", like), "title": ("like", like)}
		if config["party"]:
			or_filters[config["party"]] = ("like", like)
	rows = frappe.get_list(
		doctype,
		filters=filters,
		or_filters=or_filters,
		fields=list_fields(config),
		order_by=f"{config['date']} desc, creation desc",
		start=cint(start),
		limit_page_length=PAGE + 1,
	)
	return {"rows": decorate(rows[:PAGE], config), "more": len(rows) > PAGE}


def count_and_sum(kind, filters, field=None):
	config = DOCS[kind]
	if not frappe.has_permission(config["doctype"], "read"):
		return {"count": 0, "amount": 0}
	rows = frappe.get_list(
		config["doctype"],
		filters={**config.get("base", {}), **filters},
		fields=[field or "name"],
		limit_page_length=0,
	)
	return {"count": len(rows), "amount": sum(flt(r.get(field)) for r in rows) if field else 0}


def top(kind, filters, order_by, limit=5):
	config = DOCS[kind]
	if not frappe.has_permission(config["doctype"], "read"):
		return []
	rows = frappe.get_list(
		config["doctype"],
		filters={**config.get("base", {}), **filters},
		fields=list_fields(config),
		order_by=order_by,
		limit_page_length=limit,
	)
	for row in decorate(rows, config):
		row.kind = kind
	return rows


@frappe.whitelist()
def get_summary(section, project=None, scope="project"):
	"""ตัวเลขหน้าหลักของหมวดจัดซื้อ/ขาย และรายการที่ต้องตามต่อ"""
	today = getdate(nowdate())
	soon = getdate(add_days(today, SOON_DAYS))

	def scoped(kind, extra=None):
		return {**scope_filters(DOCS[kind], project, scope), **(extra or {})}

	if section == "buy":
		return {
			"mr_todo": count_and_sum("mr", scoped("mr", DOCS["mr"]["todo"])),
			"po_receive": count_and_sum(
				"po", scoped("po", {"docstatus": 1, "status": ("in", ("To Receive and Bill", "To Receive"))}), "grand_total"
			),
			"po_bill": count_and_sum("po", scoped("po", {"docstatus": 1, "status": "To Bill"}), "grand_total"),
			"pi_unpaid": count_and_sum("pi", scoped("pi", DOCS["pi"]["todo"]), "outstanding_amount"),
			"pi_overdue": count_and_sum(
				"pi", scoped("pi", {**DOCS["pi"]["todo"], "due_date": ("<", today)}), "outstanding_amount"
			),
			"drafts": sum(count_and_sum(k, scoped(k, {"docstatus": 0}))["count"] for k in ("mr", "po", "pi")),
			"due_soon": top(
				"po",
				scoped("po", {"docstatus": 1, "status": ("in", ("To Receive and Bill", "To Receive")), "schedule_date": ("<=", soon)}),
				"schedule_date asc",
			),
			"to_pay": top("pi", scoped("pi", {**DOCS["pi"]["todo"], "due_date": ("<=", soon)}), "due_date asc"),
		}
	if section == "sell":
		return {
			"qtn_open": count_and_sum("qtn", scoped("qtn", DOCS["qtn"]["todo"]), "grand_total"),
			"so_todo": count_and_sum("so", scoped("so", DOCS["so"]["todo"]), "grand_total"),
			"si_unpaid": count_and_sum("si", scoped("si", DOCS["si"]["todo"]), "outstanding_amount"),
			"si_overdue": count_and_sum(
				"si", scoped("si", {**DOCS["si"]["todo"], "due_date": ("<", today)}), "outstanding_amount"
			),
			"drafts": sum(count_and_sum(k, scoped(k, {"docstatus": 0}))["count"] for k in ("qtn", "so", "si")),
			"expiring": top("qtn", scoped("qtn", {**DOCS["qtn"]["todo"], "valid_till": ("<=", soon)}), "valid_till asc"),
			"to_collect": top("si", scoped("si", {**DOCS["si"]["todo"], "due_date": ("<=", soon)}), "due_date asc"),
		}
	frappe.throw(_("ไม่รองรับหมวด {0}").format(section))


# ---------------------------------------------------------------- รายละเอียด

ITEM_FIELDS = (
	"item_code",
	"item_name",
	"description",
	"qty",
	"uom",
	"rate",
	"amount",
	"schedule_date",
	"delivery_date",
	"received_qty",
	"ordered_qty",
	"delivered_qty",
	"billed_amt",
)

# เอกสารต้นทาง/ปลายทาง: (DocType ของแถวลูก, ช่องที่อ้างเอกสารนี้, DocType แม่)
NEXT_DOCS = {
	"Material Request": (("Purchase Order Item", "material_request", "Purchase Order"),),
	"Purchase Order": (
		("Purchase Receipt Item", "purchase_order", "Purchase Receipt"),
		("Purchase Invoice Item", "purchase_order", "Purchase Invoice"),
	),
	"Quotation": (("Sales Order Item", "prevdoc_docname", "Sales Order"),),
	"Sales Order": (
		("Delivery Note Item", "against_sales_order", "Delivery Note"),
		("Sales Invoice Item", "sales_order", "Sales Invoice"),
	),
}
# ช่องในแถวของเอกสารนี้ที่อ้างเอกสารต้นทาง
PREV_FIELDS = {
	"Purchase Order": (("material_request", "Material Request"),),
	"Purchase Invoice": (("purchase_order", "Purchase Order"), ("purchase_receipt", "Purchase Receipt")),
	"Sales Order": (("prevdoc_docname", "Quotation"),),
	"Sales Invoice": (("sales_order", "Sales Order"), ("delivery_note", "Delivery Note")),
}


def linked(doctype, names):
	if not names or not frappe.has_permission(doctype, "read"):
		return []
	rows = frappe.get_list(
		doctype,
		filters={"name": ("in", list(names)), "docstatus": ("<", 2)},
		fields=["name", "status", "docstatus"],
		order_by="creation asc",
	)
	for row in rows:
		row.doctype = doctype
		row.kind = KIND_OF.get(doctype)
		row.status_label, row.status_tone = status_of(row.status, row.docstatus)
	return rows


def links_of(doc):
	before, after = [], []
	for field, doctype in PREV_FIELDS.get(doc.doctype, ()):
		before += linked(doctype, {row.get(field) for row in doc.items if row.get(field)})
	for child, field, parent in NEXT_DOCS.get(doc.doctype, ()):
		names = set(frappe.get_all(child, filters={field: doc.name, "docstatus": ("<", 2)}, pluck="parent"))
		after += linked(parent, names)
	if doc.doctype in ("Purchase Invoice", "Sales Invoice") and doc.docstatus == 1:
		payments = set(
			frappe.get_all(
				"Payment Entry Reference",
				filters={"reference_doctype": doc.doctype, "reference_name": doc.name, "docstatus": 1},
				pluck="parent",
			)
		)
		after += linked("Payment Entry", payments)
	return before, after


@frappe.whitelist()
def get_doc(kind, name):
	from consbiz.site_app import pdf_url

	config = config_of(kind)
	doc = frappe.get_doc(config["doctype"], name)
	doc.check_permission("read")
	label, tone = status_of(doc.status, doc.docstatus)
	before, after = links_of(doc)
	items = [{field: row.get(field) for field in ITEM_FIELDS if row.meta.has_field(field)} for row in doc.items]
	return {
		"kind": kind,
		"doctype": doc.doctype,
		"name": doc.name,
		"title": doc.get("title"),
		"docstatus": doc.docstatus,
		"status": doc.status,
		"status_label": label,
		"status_tone": tone,
		"party": doc.get(config["party"]) if config["party"] else None,
		"date": doc.get(config["date"]),
		"due": doc.get(config["due"]),
		"project": doc.get(config["project"]) if config["project"] else None,
		"company": doc.company,
		"currency": doc.get("currency"),
		"owner_name": frappe.utils.get_fullname(doc.owner),
		"progress": {field: flt(doc.get(field)) for field in config.get("progress", ())},
		"bill_no": doc.get("bill_no"),
		"items": items,
		"totals": {
			field: flt(doc.get(field))
			for field in (
				"total",
				"discount_amount",
				"total_taxes_and_charges",
				"grand_total",
				"rounded_total",
				"outstanding_amount",
			)
			if doc.meta.has_field(field)
		},
		"taxes": [
			{"description": t.description, "rate": flt(t.rate), "amount": flt(t.tax_amount)}
			for t in doc.get("taxes") or []
		],
		"remarks": doc.get("remarks") if doc.meta.has_field("remarks") else None,
		"before": before,
		"after": after,
		"can_submit": bool(doc.docstatus == 0 and frappe.has_permission(doc.doctype, "submit", doc)),
		"pdf_url": pdf_url(doc.doctype, doc.name),
	}


@frappe.whitelist(methods=["POST"])
def submit_doc(kind, name):
	"""ส่งเอกสารร่าง (Submit) ตรวจสิทธิ์และเงื่อนไขของ ERPNext ตามปกติ"""
	config = config_of(kind)
	doc = frappe.get_doc(config["doctype"], name)
	doc.submit()
	label, tone = status_of(doc.status, doc.docstatus)
	return {"name": doc.name, "status_label": label}
