# Copyright (c) 2026, Siricons and contributors
# For license information, please see license.txt

"""หมวดจัดซื้อ (buy) และขาย (sell) ของแอปหน้างาน (/site/buy, /site/sell) ใช้เอกสารมาตรฐานของ ERPNext

- จัดซื้อ: ขอซื้อ (Material Request ประเภท Purchase) → สั่งซื้อ (Purchase Order) → ใบแจ้งหนี้ซื้อ (Purchase Invoice)
- ขาย: ใบเสนอราคา (Quotation) → ใบสั่งขาย (Sales Order) → ใบแจ้งหนี้ขาย (Sales Invoice)
แอปทำได้: ดูรายการ/รายละเอียด, ติดตามเอกสารต้นทาง-ปลายทาง, ส่งเอกสารร่าง (Submit), PDF
สร้าง/แก้ไขร่าง และสร้างเอกสารถัดไป (ขอซื้อ → สั่งซื้อ → แจ้งหนี้, เสนอราคา → สั่งขาย → แจ้งหนี้) ด้วย mapper ของ ERPNext
(ช่องที่แอปไม่แสดง เช่น หัก ณ ที่จ่าย/เงินประกัน คงค่าจาก mapper หรือแก้ในระบบเต็ม)
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
		"amount": "custom_grand_total",
		"progress": ("per_ordered", "per_received"),
		"extra": ("material_request_type",),
		# ซื้อเอง + ผู้ว่าจ้างจัดหา (วัตถุประสงค์อื่น เช่น โอน/เบิก ไม่ใช่งานจัดซื้อ)
		"base": {"material_request_type": ("in", ("Purchase", "Customer Provided"))},
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
# ช่องลิงก์คู่ค้า (กรองตามผู้ขาย/ลูกค้าที่เลือก) config["party"] เป็นชื่อสำหรับแสดง
PARTY_LINK = {
	"Purchase Order": "supplier",
	"Purchase Invoice": "supplier",
	"Quotation": "party_name",
	"Sales Order": "customer",
	"Sales Invoice": "customer",
}

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
	fields = ["name", "status", "docstatus", "title", "currency", "modified", "_assign", "_liked_by"]
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


PURPOSE = {"Purchase": "ซื้อ", "Customer Provided": "ผู้ว่าจ้างจัดหา"}


def user_list(value):
	"""ช่อง _assign / _liked_by (JSON รายชื่อผู้ใช้)"""
	try:
		return [u for u in frappe.parse_json(value or "[]") if u]
	except Exception:
		return []


def people(users):
	return [{"user": u, "name": frappe.utils.get_fullname(u)} for u in users]


def decorate(rows, config):
	today = getdate(nowdate())
	projects = {r.get("project") for r in rows if r.get("project")}
	project_names = (
		dict(frappe.get_all("Project", filters={"name": ("in", list(projects))}, fields=["name", "project_name"], as_list=True))
		if projects
		else {}
	)
	me = frappe.session.user
	for row in rows:
		row.project_name = project_names.get(row.get("project"))
		row.assigned = people(user_list(row.pop("_assign", None)))
		liked = user_list(row.pop("_liked_by", None))
		row.liked = me in liked
		row.likes = len(liked)
		if row.get("material_request_type"):
			row.purpose = _(PURPOSE.get(row.material_request_type, row.material_request_type))
		row.status_label, row.status_tone = status_of(row.status, row.docstatus)
		row.overdue = bool(
			row.docstatus == 1
			and row.get("due")
			and getdate(row.due) < today
			and (flt(row.get("outstanding")) > 0 if config.get("outstanding") else row.status_tone == "amber")
		)
	return rows


# คอลัมน์ที่เรียงได้ (key ของแอป → ช่องของเอกสาร ตาม config)
SORTS = ("date", "due", "name", "party", "amount", "outstanding", "status")
PAGE_SIZES = (30, 50, 100)
EXPORT_LIMIT = 5000


def sort_field(config, sort):
	field = {
		"date": config["date"],
		"due": config["due"],
		"name": "name",
		"party": config["party"],
		"amount": config["amount"],
		"outstanding": config.get("outstanding"),
		"status": "status",
	}.get(sort)
	return field or config["date"]


def list_filters(config, project, scope, filter, date_from=None, date_to=None, party=None, overdue=0):
	"""ตัวกรองของรายการ (ไม่รวมคำค้น) filter = todo / draft / done / all"""
	doctype = config["doctype"]
	filters = {**config.get("base", {}), **scope_filters(config, project, scope)}
	if date_from and date_to:
		filters[config["date"]] = ("between", (getdate(date_from), getdate(date_to)))
	elif date_from:
		filters[config["date"]] = (">=", getdate(date_from))
	elif date_to:
		filters[config["date"]] = ("<=", getdate(date_to))
	if party and doctype in PARTY_LINK:
		filters[PARTY_LINK[doctype]] = party
	if cint(overdue):
		filters.update(config["todo"])
		filters[config["due"]] = ("<", getdate(nowdate()))
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
	return filters


def search_filters(config, search):
	if not search or not search.strip():
		return None
	like = f"%{search.strip()}%"
	or_filters = {"name": ("like", like), "title": ("like", like)}
	if config["party"]:
		or_filters[config["party"]] = ("like", like)
	return or_filters


def count(doctype, filters, or_filters):
	return cint(
		frappe.get_list(
			doctype, filters=filters, or_filters=or_filters, fields=[{"COUNT": "name", "as": "n"}], order_by=None
		)[0].n
	)


@frappe.whitelist()
def get_docs(
	kind,
	project=None,
	scope="project",
	filter="todo",
	search=None,
	start=0,
	sort=None,
	order="desc",
	date_from=None,
	date_to=None,
	party=None,
	overdue=0,
	page_size=PAGE,
	export=0,
):
	"""รายการเอกสาร ล่าสุดก่อน (เรียงตาม sort/order ได้)
	คืน rows + total (จำนวนตามตัวกรอง) + sums (ยอดรวมทั้งชุด) + counts (จำนวนของแต่ละแท็บ)
	export = 1: คืนทุกแถว (ไม่เกิน EXPORT_LIMIT) สำหรับส่งออก CSV"""
	from urllib.parse import quote_plus

	from consbiz.site_app import pdf_url

	config = config_of(kind)
	doctype = config["doctype"]
	frappe.has_permission(doctype, "read", throw=True)
	extra = {"date_from": date_from, "date_to": date_to, "party": party, "overdue": overdue}
	filters = list_filters(config, project, scope, filter, **extra)
	or_filters = search_filters(config, search)
	page_size = cint(page_size) if cint(page_size) in PAGE_SIZES else PAGE
	order = "asc" if order == "asc" else "desc"
	field = sort_field(config, sort if sort in SORTS else None)
	rows = frappe.get_list(
		doctype,
		filters=filters,
		or_filters=or_filters,
		fields=list_fields(config),
		order_by=f"`tab{doctype}`.`{field}` {order}, `tab{doctype}`.creation desc",
		start=0 if cint(export) else cint(start),
		limit_page_length=EXPORT_LIMIT if cint(export) else page_size,
	)
	decorate(rows, config)
	base_pdf = pdf_url(doctype, "__NAME__")
	for row in rows:
		row.pdf_url = base_pdf.replace("__NAME__", quote_plus(row.name))
	if cint(export):
		return {"rows": rows}

	sum_fields = [f for f in (config["amount"], config.get("outstanding")) if f]
	sums = {}
	if sum_fields:
		result = frappe.get_list(
			doctype,
			filters=filters,
			or_filters=or_filters,
			fields=[{"SUM": f, "as": f} for f in sum_fields],
			order_by=None,
		)[0]
		sums = {
			"amount": flt(result.get(config["amount"])) if config["amount"] else None,
			"outstanding": flt(result.get(config.get("outstanding"))) if config.get("outstanding") else None,
		}
	counts = {
		tab: count(doctype, list_filters(config, project, scope, tab, **extra), or_filters)
		for tab in ("todo", "draft", "done", "all")
	}
	total = counts[filter] if filter in counts else count(doctype, filters, or_filters)
	return {
		"rows": rows,
		"total": total,
		"more": cint(start) + len(rows) < total,
		"sums": sums,
		"counts": counts,
	}


@frappe.whitelist(methods=["POST"])
def submit_docs(kind, names):
	"""ส่งเอกสารร่างหลายใบ (เลือกจากรายการ) ใบที่ไม่ผ่านย้อนกลับเฉพาะใบนั้น (savepoint) คืนผลรายใบ"""
	config = config_of(kind)
	names = frappe.parse_json(names) if isinstance(names, str) else names
	results = []
	for name in (names or [])[:100]:
		frappe.db.savepoint("site_bulk_submit")
		try:
			doc = frappe.get_doc(config["doctype"], name)
			if doc.docstatus != 0:
				frappe.throw(_("ส่งแล้ว"))
			doc.submit()
			results.append({"name": name, "ok": True})
		except Exception as error:
			frappe.db.rollback(save_point="site_bulk_submit")
			message = frappe.utils.strip_html(str(error)) or _("ส่งไม่สำเร็จ")
			results.append({"name": name, "ok": False, "error": message[:200]})
		frappe.local.message_log = []
	return results


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
	"name",
	"custom_vat_nocal",
	"custom_wbs",
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


def next_of(doc, kind):
	"""kind ของเอกสารถัดไปที่สร้างต่อในแอปได้ (ยังค้างดำเนินการ + มีสิทธิ์สร้าง) ไม่ได้ = None"""
	target = next_kind(kind)
	if not target or doc.docstatus != 1:
		return None
	if kind == "mr" and doc.material_request_type != "Purchase":
		return None
	statuses = DOCS[kind]["todo"].get("status", (None, ()))[1]
	if doc.status not in statuses:
		return None
	if doc.meta.has_field("per_billed") and kind != "mr" and flt(doc.per_billed) >= 100:
		return None
	if not frappe.has_permission(DOCS[target]["doctype"], "create"):
		return None
	return target


def signature_name(name):
	return (frappe.db.get_value("Signature", name, "full_name") or name) if name else None


def header_info(doc, kind):
	"""ข้อมูลหัวเอกสารสำหรับหน้าดู: เรื่อง วัตถุประสงค์ ผู้ขอ/ผู้อนุมัติ (MR ใช้ Signature) ตัวเลือกภาษีของ MR"""
	out = {"title": doc.get("title")}
	if kind == "mr":
		out.update(
			{
				"purpose": _(PURPOSE.get(doc.material_request_type, doc.material_request_type)),
				"material_request_type": doc.material_request_type,
				"request_by": signature_name(doc.get("custom_request_by")),
				"approve_by": signature_name(doc.get("custom_approve_by")),
				"included_vat": cint(doc.get("custom_included_vat")),
				"vat_override": cint(doc.get("custom_vat_override")),
			}
		)
	return out


def summary_of(doc, kind):
	"""สรุปยอดท้ายเอกสารแบบระบบเต็ม: แถว (ป้าย, ยอด) + ยอดสุทธิ + ตัวอักษร
	MR ใช้ช่อง custom_* (request_totals.py) เอกสารอื่นใช้ยอด/ภาษีของ ERPNext"""
	from consbiz.utils import thai_baht_text

	rows = []
	if kind == "mr":
		if flt(doc.get("custom_net_total_novat")):
			rows.append({"label": _("มูลค่าสินค้า (ไม่คิดภาษี)"), "value": flt(doc.custom_net_total_novat)})
		rows.append({"label": _("มูลค่าก่อนภาษี"), "value": flt(doc.get("custom_net_total"))})
		if doc.material_request_type != "Customer Provided":
			rows.append({"label": _("ภาษีมูลค่าเพิ่ม 7%"), "value": flt(doc.get("custom_vat")), "tax": 1})
		grand = flt(doc.get("custom_grand_total"))
	else:
		rows.append({"label": _("รวมเป็นเงิน"), "value": flt(doc.get("total"))})
		if flt(doc.get("discount_amount")):
			rows.append({"label": _("ส่วนลด"), "value": -flt(doc.discount_amount)})
		for t in doc.get("taxes") or []:
			label = t.description + (f" {flt(t.rate):g}%" if flt(t.rate) else "")
			rows.append({"label": label, "value": flt(t.tax_amount), "tax": 1})
		grand = flt(doc.get("rounded_total")) or flt(doc.get("grand_total"))
	return {"rows": rows, "grand": grand, "in_words": thai_baht_text(grand) if grand else ""}


def steps_of(doc, kind):
	"""ขั้นตอนของเอกสาร (แถบความคืบหน้าในหน้าดู) state = done / current / todo / error, note = % ของขั้นนั้น"""
	if kind == "mr":
		flow = [("สั่งซื้อ", "per_ordered"), ("รับของ", "per_received")]
		if doc.material_request_type == "Customer Provided":
			flow = [("รับของ", "per_received")]
		labels = ("ร่าง", "ส่งแล้ว")
	elif kind == "po":
		flow, labels = [("รับของ", "per_received"), ("วางบิล", "per_billed")], ("ร่าง", "ส่งแล้ว")
	elif kind == "so":
		flow, labels = [("ส่งมอบ", "per_delivered"), ("วางบิล", "per_billed")], ("ร่าง", "ยืนยันแล้ว")
	elif kind in ("pi", "si"):
		paid = 100 - (flt(doc.outstanding_amount) / flt(doc.grand_total) * 100 if flt(doc.grand_total) else 0)
		flow = [("รับชำระ" if kind == "si" else "ชำระเงิน", paid)]
		labels = ("ร่าง", "ส่งแล้ว")
	else:  # ใบเสนอราคา
		ordered = {"Ordered": 100, "Partially Ordered": 50}.get(doc.status, 0)
		flow, labels = [("ลูกค้าสั่งซื้อ", ordered)], ("ร่าง", "เสนอราคาแล้ว")

	steps = [{"label": _(labels[0])}, {"label": _(labels[1])}]
	for label, field in flow:
		steps.append({"label": _(label), "pct": flt(field if not isinstance(field, str) else doc.get(field))})
	steps.append({"label": _("เสร็จสิ้น")})

	if doc.docstatus == 2:
		return [{**steps[0], "state": "done"}, {"label": _("ยกเลิก"), "state": "error"}]
	if doc.docstatus == 0:
		return [{**s, "state": "current" if i == 0 else "todo"} for i, s in enumerate(steps)]
	closed = doc.status in ("Completed", "Closed", "Paid", "Received", "Ordered", "Delivered")
	lost = doc.status in ("Lost", "Expired")
	current_set = False
	for i, s in enumerate(steps):
		if i < 2:
			s["state"] = "done"
		elif "pct" in s:
			if s["pct"] >= 100 or closed:
				s["state"] = "done"
			elif not current_set:
				s["state"] = "error" if lost else "current"
				current_set = True
			else:
				s["state"] = "todo"
			s["note"] = f"{round(min(s['pct'], 100))}%"
		else:
			s["state"] = "done" if not current_set and not lost else "todo"
	return steps


@frappe.whitelist()
def get_doc(kind, name):
	from consbiz.site_app import pdf_url

	config = config_of(kind)
	doc = frappe.get_doc(config["doctype"], name)
	doc.check_permission("read")
	label, tone = status_of(doc.status, doc.docstatus)
	before, after = links_of(doc)
	items = [{field: row.get(field) for field in ITEM_FIELDS if row.meta.has_field(field)} for row in doc.items]
	project = doc.get(config["project"]) if config["project"] else None
	return {
		**header_info(doc, kind),
		"project_name": frappe.db.get_value("Project", project, "project_name") if project else None,
		"steps": steps_of(doc, kind),
		"summary": summary_of(doc, kind),
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
		"remarks": doc.get(FORM[kind].get("remarks") or "remarks") if doc.meta.has_field(FORM[kind].get("remarks") or "remarks") else None,
		"before": before,
		"after": after,
		"can_submit": bool(doc.docstatus == 0 and frappe.has_permission(doc.doctype, "submit", doc)),
		"can_edit": bool(doc.docstatus == 0 and frappe.has_permission(doc.doctype, "write", doc)),
		"next_kind": next_of(doc, kind),
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


# ---------------------------------------------------------------- สร้าง / แก้ไขร่างในแอป

# ส่วนลดท้ายบิล (%) ERPNext คำนวณยอดหลังส่วนลดเองใน calculate_taxes_and_totals
DISCOUNT = "additional_discount_percentage"

# ช่องหัวเอกสารที่แอปส่งมาได้ (ช่องอื่นไม่รับ) และช่องของแถวรายการ
FORM = {
	"mr": {
		"party": None,
		"header": (
			"material_request_type",
			"title",
			"transaction_date",
			"schedule_date",
			"custom_request_by",
			"custom_approve_by",
			"custom_included_vat",
			"custom_vat_override",
			"custom_vat",
			"custom_remark",
		),
		"item": ("item_code", "qty", "uom", "rate", "schedule_date", "description", "custom_wbs", "custom_vat_nocal"),
		"remarks": "custom_remark",
	},
	"po": {
		"party": "supplier",
		"header": ("supplier", "transaction_date", "schedule_date", "taxes_and_charges", DISCOUNT),
		"item": ("item_code", "qty", "uom", "rate", "schedule_date", "description"),
	},
	"pi": {
		"party": "supplier",
		# tax_invoice_* มาจาก erpnext_thailand (บังคับเมื่อมีภาษีซื้อ) ไม่มีช่อง = ข้าม
		"header": (
			"supplier",
			"posting_date",
			"bill_no",
			"bill_date",
			"tax_invoice_number",
			"tax_invoice_date",
			"due_date",
			"taxes_and_charges",
			DISCOUNT,
			"remarks",
		),
		"item": ("item_code", "qty", "uom", "rate", "description"),
		"remarks": "remarks",
	},
	"qtn": {
		"party": "party_name",
		"header": ("party_name", "transaction_date", "valid_till", "taxes_and_charges", DISCOUNT),
		"item": ("item_code", "qty", "uom", "rate", "description"),
	},
	"so": {
		"party": "customer",
		"header": ("customer", "transaction_date", "delivery_date", "taxes_and_charges", DISCOUNT),
		"item": ("item_code", "qty", "uom", "rate", "delivery_date", "description"),
	},
	"si": {
		"party": "customer",
		"header": ("customer", "posting_date", "due_date", "taxes_and_charges", DISCOUNT, "remarks"),
		"item": ("item_code", "qty", "uom", "rate", "description"),
		"remarks": "remarks",
	},
}
# เอกสารถัดไป: kind ปลายทาง → (kind ต้นทาง, mapper ของ ERPNext)
MAPPERS = {
	"po": ("mr", "erpnext.stock.doctype.material_request.material_request.make_purchase_order"),
	"pi": ("po", "erpnext.buying.doctype.purchase_order.purchase_order.make_purchase_invoice"),
	"so": ("qtn", "erpnext.selling.doctype.quotation.quotation.make_sales_order"),
	"si": ("so", "erpnext.selling.doctype.sales_order.sales_order.make_sales_invoice"),
}
DATE_FIELDS = {"transaction_date", "schedule_date", "posting_date", "bill_date", "due_date", "valid_till", "delivery_date"}
PARTY_DOCTYPE = {"supplier": "Supplier", "customer": "Customer", "party_name": "Customer"}


def next_kind(kind):
	"""kind ของเอกสารถัดไปที่สร้างจากเอกสารนี้ได้ (ไม่มี = None)"""
	return next((target for target, (source, _m) in MAPPERS.items() if source == kind), None)


def mapped_doc(kind, source):
	if kind not in MAPPERS:
		frappe.throw(_("สร้าง{0}จากเอกสารอื่นไม่ได้").format(_(DOCS[kind]["doctype"])))
	source_kind, method = MAPPERS[kind]
	source_doc = frappe.get_doc(DOCS[source_kind]["doctype"], source)
	source_doc.check_permission("read")
	if source_doc.docstatus != 1:
		frappe.throw(_("{0} ต้องส่งแล้วจึงสร้างเอกสารถัดไปได้").format(source))
	doc = frappe.get_attr(method)(source)
	if not doc.get("items"):
		frappe.throw(_("{0} ดำเนินการครบทุกรายการแล้ว").format(source))
	return doc


def new_doc(kind, project):
	config = DOCS[kind]
	doc = frappe.new_doc(config["doctype"])
	if kind == "mr":
		doc.material_request_type = "Purchase"
	if kind == "qtn":
		doc.quotation_to = "Customer"
	company = frappe.db.get_value("Project", project, "company") if project else None
	doc.company = company or frappe.defaults.get_user_default("Company")
	today = nowdate()
	for field in ("transaction_date", "posting_date"):
		if doc.meta.has_field(field):
			doc.set(field, today)
	# วันต้องการ/กำหนดส่งเริ่มต้น 7 วัน (แก้ได้ในฟอร์ม)
	for field in ("schedule_date", "delivery_date"):
		if kind in ("mr", "po", "so") and doc.meta.has_field(field):
			doc.set(field, add_days(today, 7))
	if config["project"] and project:
		doc.set(config["project"], project)
	if kind in ("so", "si") and project and not doc.get("customer"):
		doc.customer = frappe.db.get_value("Project", project, "customer")
	# แม่แบบภาษีค่าเริ่มต้นของบริษัท (แถวภาษีใส่ตอน apply_form)
	if doc.meta.has_field("taxes_and_charges"):
		doc.taxes_and_charges = frappe.db.get_value(
			doc.meta.get_field("taxes_and_charges").options, {"is_default": 1, "company": doc.company, "disabled": 0}
		)
	return doc


def load_doc(kind, name=None, source=None, project=None):
	"""เอกสารร่างเดิม / เอกสารใหม่จาก mapper / เอกสารใหม่เปล่า ยังไม่บันทึก"""
	config = config_of(kind)
	doctype = config["doctype"]
	if name:
		doc = frappe.get_doc(doctype, name)
		doc.check_permission("write")
		if doc.docstatus != 0:
			frappe.throw(_("{0} ส่งแล้ว แก้ไขไม่ได้").format(name))
		return doc
	frappe.has_permission(doctype, "create", throw=True)
	if source:
		doc = mapped_doc(kind, source)
		if config["project"] and project and not doc.get(config["project"]):
			doc.set(config["project"], project)
		return doc
	return new_doc(kind, project)


def row_key(row, index):
	"""ตัวจับคู่แถวระหว่างแอปกับเอกสาร: แถวที่บันทึกแล้วใช้ name, แถวจาก mapper ใช้ลำดับ"""
	return row.name if row.get("name") and not row.is_new() else f"m{index}"


def project_of(doc, kind):
	field = DOCS[kind]["project"]
	return doc.get(field) if field else None


def apply_form(doc, kind, data):
	"""ใส่ค่าจากแอปลงเอกสาร: ช่องหัวเอกสารตาม FORM, แถวเดิมจับคู่ด้วย key, แถวใหม่ตั้งค่าเริ่มจาก ERPNext"""
	from erpnext.stock.get_item_details import get_conversion_factor

	from consbiz.site_stock import project_warehouse

	form = FORM[kind]
	old_template = doc.get("taxes_and_charges")
	if kind == "mr" and data.get("material_request_type") not in (None, "Purchase", "Customer Provided"):
		frappe.throw(_("วัตถุประสงค์ต้องเป็น ซื้อ หรือ ผู้ว่าจ้างจัดหา"))
	for field in form["header"]:
		if field in data and doc.meta.has_field(field):
			value = data.get(field) or None
			doc.set(field, value)
	if kind in ("pi", "si") and data.get("posting_date"):
		doc.set_posting_time = 1
	if kind == "pi":
		if doc.get("bill_no") and not doc.get("bill_date"):
			doc.bill_date = doc.posting_date
		if doc.get("tax_invoice_number") and not doc.get("tax_invoice_date"):
			doc.tax_invoice_date = doc.get("bill_date") or doc.posting_date

	project = project_of(doc, kind)
	warehouse = project_warehouse(project) if kind in ("mr", "po") else None
	if warehouse and doc.meta.has_field("set_warehouse") and not doc.get("set_warehouse"):
		doc.set_warehouse = warehouse

	existing = {row_key(row, i): row for i, row in enumerate(doc.get("items") or [])}
	rows = []
	for item in data.get("items") or []:
		if not item.get("item_code") or flt(item.get("qty")) <= 0:
			continue
		row = existing.pop(item.get("key"), None)
		if row and row.item_code != item["item_code"]:
			row = None
		values = {field: item.get(field) for field in form["item"] if field in item}
		if row is None:
			row = frappe.new_doc(doc.meta.get_field("items").options, parent_doc=doc, parentfield="items")
			if warehouse and row.meta.has_field("warehouse"):
				row.warehouse = warehouse
			if project and row.meta.has_field("project"):
				row.project = project
		old_uom = row.get("uom")
		row.update(values)
		if not row.get("uom"):
			row.uom = frappe.db.get_value("Item", row.item_code, "stock_uom")
		if row.uom != old_uom or not row.get("conversion_factor"):
			row.conversion_factor = flt(get_conversion_factor(row.item_code, row.uom).get("conversion_factor")) or 1
		for field in ("schedule_date", "delivery_date"):
			if row.meta.has_field(field) and not row.get(field):
				row.set(field, doc.get(field) or doc.get("transaction_date"))
		rows.append(row)
	doc.set("items", rows)
	# ลำดับแถวตามที่จัดในแอป (ลากย้ายได้)
	for index, row in enumerate(doc.items, 1):
		row.idx = index
		if kind == "mr":
			row.amount = flt(row.qty) * flt(row.rate)
		if row.meta.has_field("stock_qty"):
			row.stock_qty = flt(row.qty) * flt(row.conversion_factor or 1)

	# วันกำหนดส่งของหัวเอกสาร = วันแรกสุดของแถว (ERPNext ตั้งเองตอน validate ถ้าว่าง)
	if kind in ("po", "so"):
		field = "schedule_date" if kind == "po" else "delivery_date"
		dates = [getdate(r.get(field)) for r in doc.items if r.get(field)]
		if dates and not doc.get(field):
			doc.set(field, min(dates))

	# เปลี่ยนแม่แบบภาษี = แทนแถวภาษีด้วยแถวของแม่แบบใหม่
	template = doc.get("taxes_and_charges")
	if doc.meta.has_field("taxes") and (template != old_template or (template and not doc.get("taxes"))):
		doc.set("taxes", [])
		if doc.get("taxes_and_charges"):
			doc.append_taxes_from_master()
	doc.set_missing_values(for_validate=True)
	if kind == "mr":
		from consbiz.request_totals import calculate

		calculate(doc)
	else:
		doc.calculate_taxes_and_totals()
	return doc


def tax_templates(doc):
	if not doc.meta.has_field("taxes_and_charges"):
		return []
	doctype = doc.meta.get_field("taxes_and_charges").options
	return frappe.get_all(
		doctype,
		filters={"company": doc.company, "disabled": 0},
		fields=["name", "title", "is_default"],
		order_by="is_default desc, title asc",
	)


def serialize_form(doc, kind):
	config = DOCS[kind]
	form = FORM[kind]
	party_field = form["party"]
	party_name = None
	if party_field and doc.get(party_field):
		party_doctype = PARTY_DOCTYPE[party_field]
		party_name = frappe.db.get_value(
			party_doctype, doc.get(party_field), "supplier_name" if party_doctype == "Supplier" else "customer_name"
		)
	items = []
	for i, row in enumerate(doc.get("items") or []):
		items.append(
			{
				"key": row_key(row, i),
				"item_code": row.item_code,
				"item_name": row.item_name,
				"qty": flt(row.qty),
				"uom": row.uom,
				"stock_uom": row.get("stock_uom"),
				"rate": flt(row.get("rate")),
				"amount": flt(row.get("amount")),
				"schedule_date": row.get("schedule_date"),
				"delivery_date": row.get("delivery_date"),
				"description": row.get("description"),
				"custom_wbs": row.get("custom_wbs"),
				"custom_vat_nocal": cint(row.get("custom_vat_nocal")),
				"uoms": item_uoms(row.item_code),
			}
		)
	header = {field: doc.get(field) for field in form["header"] if doc.meta.has_field(field)}
	return {
		"kind": kind,
		"name": None if doc.is_new() else doc.name,
		"company": doc.company,
		"project": project_of(doc, kind),
		"party_label": party_name,
		**header,
		"request_by_label": signature_name(doc.get("custom_request_by")),
		"approve_by_label": signature_name(doc.get("custom_approve_by")),
		"project_name": frappe.db.get_value("Project", project_of(doc, kind), "project_name")
		if project_of(doc, kind)
		else None,
		"items": items,
		"totals": totals_of(doc),
		"summary": summary_of(doc, kind),
		"taxes": [
			{"description": t.description, "rate": flt(t.rate), "amount": flt(t.tax_amount)}
			for t in doc.get("taxes") or []
		],
	}


def totals_of(doc):
	if not doc.meta.has_field("grand_total"):
		return {}
	return {
		field: flt(doc.get(field))
		for field in ("total", "discount_amount", "total_taxes_and_charges", "grand_total", "rounded_total")
		if doc.meta.has_field(field)
	}


def item_uoms(item_code):
	stock_uom = frappe.get_cached_value("Item", item_code, "stock_uom")
	uoms = frappe.get_all("UOM Conversion Detail", filters={"parent": item_code, "parenttype": "Item"}, pluck="uom")
	return list(dict.fromkeys([stock_uom, *uoms]))


@frappe.whitelist()
def get_form(kind, name=None, source=None, project=None):
	"""ข้อมูลฟอร์มสร้าง/แก้ไข: เอกสาร (ยังไม่บันทึก) + ตัวเลือกภาษี"""
	doc = load_doc(kind, name=name, source=source, project=project)
	apply_form(doc, kind, {"items": serialize_form(doc, kind)["items"]})
	out = serialize_form(doc, kind)
	out["source"] = source
	out["fields"] = [field for field in FORM[kind]["header"] if doc.meta.has_field(field)]
	out["tax_templates"] = tax_templates(doc)
	out["can_submit"] = frappe.has_permission(doc.doctype, "submit")
	return out


def parse(data):
	return frappe.parse_json(data) if isinstance(data, str) else frappe._dict(data or {})


@frappe.whitelist(methods=["POST"])
def preview_doc(kind, data):
	"""คำนวณยอด/ภาษีตามที่กรอก (ไม่บันทึก)"""
	data = parse(data)
	doc = load_doc(kind, name=data.get("name"), source=data.get("source"), project=data.get("project"))
	try:
		apply_form(doc, kind, data)
		out = serialize_form(doc, kind)
	finally:
		# ERPNext อาจเขียนข้อมูลระหว่างเติมค่า (เช่น สร้าง Item Price อัตโนมัติ) ตัวอย่างยอดต้องไม่บันทึกอะไร
		frappe.db.rollback()
		frappe.local.message_log = []
	return {"totals": out["totals"], "taxes": out["taxes"], "summary": out["summary"], "items": out["items"]}


def keep_request_rates(doc, wanted):
	"""MR ใหม่: ERPNext (MaterialRequest.on_update → update_item_rates) ทับราคาทุกแถวด้วย Price List ตอนบันทึกครั้งแรก
	ใช้ราคาที่ผู้ใช้กรอกในแอปคืน แล้วคำนวณยอดใหม่ (request_totals)"""
	from consbiz.request_totals import calculate

	changed = False
	for row, rate in zip(doc.items, wanted, strict=False):
		if flt(row.rate) != rate:
			row.rate, row.amount, changed = rate, flt(rate * flt(row.qty), row.precision("amount")), True
			row.db_update()
	if changed:
		calculate(doc)
		doc.db_update()


@frappe.whitelist(methods=["POST"])
def save_doc(kind, data, submit=0):
	"""บันทึกร่าง (submit=1 ส่งเอกสารต่อเลย) ตรวจสิทธิ์และเงื่อนไขของ ERPNext ตามปกติ"""
	data = parse(data)
	doc = load_doc(kind, name=data.get("name"), source=data.get("source"), project=data.get("project"))
	apply_form(doc, kind, data)
	if not doc.get("items"):
		frappe.throw(_("เพิ่มรายการอย่างน้อย 1 รายการ"))
	wanted = [flt(row.rate) for row in doc.items] if kind == "mr" else None
	doc.save()
	if wanted:
		keep_request_rates(doc, wanted)
	if cint(submit):
		doc.submit()
	return {"name": doc.name, "docstatus": doc.docstatus}


@frappe.whitelist()
def search_items(kind, txt=None, project=None):
	"""สินค้า/บริการสำหรับเลือกในฟอร์ม พร้อมราคาแนะนำ (ซื้อ = ราคาซื้อล่าสุด, ขาย = ราคาขายมาตรฐาน)"""
	config = config_of(kind)
	buying = config["section"] == "buy"
	filters = {"disabled": 0, "has_variants": 0}
	filters["is_purchase_item" if buying else "is_sales_item"] = 1
	if frappe.get_meta("Item").has_field("custom_base_item"):
		filters["custom_base_item"] = ("is", "not set")
	or_filters = None
	if txt:
		like = f"%{txt.strip()}%"
		or_filters = {"name": ("like", like), "item_name": ("like", like), "item_group": ("like", like)}
	rows = frappe.get_list(
		"Item",
		filters=filters,
		or_filters=or_filters,
		fields=["name as item_code", "item_name", "item_group", "stock_uom", "last_purchase_rate", "standard_rate"],
		order_by="modified desc",
		limit_page_length=40,
	)
	prices = {}
	if rows and not buying:
		price_list = frappe.db.get_single_value("Selling Settings", "selling_price_list") or "Standard Selling"
		prices = dict(
			frappe.get_all(
				"Item Price",
				filters={"price_list": price_list, "item_code": ("in", [r.item_code for r in rows])},
				fields=["item_code", "price_list_rate"],
				as_list=True,
			)
		)
	for row in rows:
		row.rate = flt(row.last_purchase_rate) if buying else flt(prices.get(row.item_code) or row.standard_rate)
		row.uoms = item_uoms(row.item_code)
		row.pop("last_purchase_rate")
		row.pop("standard_rate")
	return rows


@frappe.whitelist()
def search_parties(kind, txt=None, company=None):
	"""ผู้ขาย (จัดซื้อ) / ลูกค้า (ขาย) ไม่รวมรายที่จำกัดให้ทำรายการกับบริษัทอื่นเท่านั้น (Allowed To Transact With)"""
	config_of(kind)
	field = FORM[kind]["party"]
	if not field:
		return []
	doctype = PARTY_DOCTYPE[field]
	label = "supplier_name" if doctype == "Supplier" else "customer_name"
	filters = {"disabled": 0}
	if company:
		restricted = frappe.get_all(
			"Allowed To Transact With", filters={"parenttype": doctype}, fields=["parent", "company"]
		)
		allowed = {r.parent for r in restricted if r.company == company}
		blocked = {r.parent for r in restricted} - allowed
		if blocked:
			filters["name"] = ("not in", list(blocked))
	or_filters = None
	if txt:
		like = f"%{txt.strip()}%"
		or_filters = {"name": ("like", like), label: ("like", like)}
	return frappe.get_list(
		doctype,
		filters=filters,
		or_filters=or_filters,
		fields=["name as value", f"{label} as label"],
		order_by="modified desc",
		limit_page_length=30,
	)


@frappe.whitelist()
def search_signatures(txt=None):
	"""ผู้ขอ/ผู้อนุมัติของใบขอซื้อ (Signature: ชื่อ + ลายเซ็น)"""
	or_filters = None
	if txt:
		like = f"%{txt.strip()}%"
		or_filters = {"name": ("like", like), "full_name": ("like", like)}
	return frappe.get_list(
		"Signature",
		or_filters=or_filters,
		fields=["name as value", "full_name as label"],
		order_by="full_name asc",
		limit_page_length=30,
	)

