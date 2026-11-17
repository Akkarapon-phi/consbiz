# Copyright (c) 2026, Siricons and contributors
# For license information, please see license.txt

"""หมวดสารบรรณของแอปออฟฟิศ (/conserp/saraban): หนังสือเข้า, หนังสือออก, ใบนำส่งเอกสาร, ใบปะหน้าซอง
หน้าจอครอบ DocType เดิม (Letter In / Letter Out / Transmittal / Envelope) กฎของเอกสารอยู่ใน DocType เหมือนเดิม
แอปส่งเฉพาะช่องที่กรอกได้ตาม KINDS หลัง Submit แก้ได้เฉพาะช่อง after (Allow on Submit ของ DocType)
หนังสือเข้า: Submit แล้วเสนออนุมัติ → ผู้อนุมัติ (Role Approver) อนุมัติ/ไม่อนุมัติ ระหว่างรอ ถอนเรื่อง/เปลี่ยนผู้อนุมัติได้
(ขั้นตอนเดียวกับปุ่มในฟอร์มระบบเต็ม public/js ของ letter_in.js แจ้งผู้อนุมัติด้วย Assign To)"""

import frappe
from frappe import _
from frappe.contacts.doctype.address.address import get_default_address
from frappe.desk.form import assign_to
from frappe.utils import cint, getdate, nowdate

from consbiz import store_app
from consbiz.consbiz.doctype.envelope.envelope import make_envelope
from consbiz.site_app import pdf_url

LIST_LIMIT = 500
APPROVER_ROLE = "Approver"

# สถานะของหนังสือเข้า (ค่าใน DocType เป็นภาษาไทย)
LI_WAIT, LI_PROPOSE, LI_APPROVED, LI_REJECTED = "รอเสนอ", "เสนออนุมัติ", "อนุมัติ", "ไม่อนุมัติ"

KINDS = {
	"letters-in": {
		"doctype": "Letter In",
		"fields": ("document_no", "title", "document_date", "company", "project", "receiver", "receive_date"),
		"list": (
			"document_no",
			"title",
			"document_date",
			"receive_date",
			"company",
			"project",
			"status",
			"receiver_name",
			"approver",
			"approver_name",
		),
		"date": "receive_date",
		"after": (),
	},
	"letters-out": {
		"doctype": "Letter Out",
		"fields": (
			"title",
			"document_date",
			"company",
			"project",
			"sender",
			"sent_date",
			"receiver",
			"receive_date",
			"document_status",
		),
		"list": (
			"title",
			"document_date",
			"sent_date",
			"company",
			"project",
			"sender_name",
			"receiver",
			"receive_date",
			"document_status",
		),
		"date": "sent_date",
		"after": ("document_status",),
	},
	"transmittals": {
		"doctype": "Transmittal",
		"fields": (
			"company",
			"title",
			"project",
			"date",
			"to_date",
			"recipient_type",
			"party",
			"recipient_name",
			"contact_person",
		),
		"items": (
			"reference_doctype",
			"reference_name",
			"document_no",
			"date",
			"description",
			"qty",
			"unit",
			"amount",
			"remark",
		),
		"list": (
			"title",
			"date",
			"company",
			"project",
			"recipient_type",
			"recipient_name",
			"status",
			"sent_date",
		),
		"date": "date",
		"after": ("sent_date", "received_by", "received_date"),
	},
	"envelopes": {
		"doctype": "Envelope",
		"fields": (
			"company",
			"from",
			"sender",
			"sender_name",
			"sender_tel",
			"send_date",
			"to",
			"receiver",
			"remark",
			"reference_doctype",
			"reference_name",
		),
		"list": ("company", "send_date", "to", "receiver", "remark", "sender_name", "reference_name"),
		"date": "send_date",
		"after": (),
	},
}

# ค้นหาในฟอร์ม: {DocType: ช่องชื่อที่แสดง}
SEARCH = {
	"Project": "project_name",
	"Customer": "customer_name",
	"Supplier": "supplier_name",
	"User": "full_name",
	"Address": "address_title",
	"Contact": "full_name",
}
# Print Format ของใบปะหน้า (ขนาดซอง) ที่ให้เลือกในแอป ตัวแรก = ค่าตั้งต้น
ENVELOPE_FORMATS = ("Envelope", "Envelope DL", "Envelope 9/125")


def config_of(kind):
	if kind not in KINDS:
		frappe.throw(_("ไม่รองรับเอกสารชนิดนี้"), frappe.PermissionError)
	return KINDS[kind]


def saraban_kinds():
	"""ชนิดเอกสารที่ผู้ใช้อ่านได้ (ไม่มีเลย = ไม่เห็นหมวดสารบรรณ)"""
	return [kind for kind, config in KINDS.items() if frappe.has_permission(config["doctype"], "read")]


def boot_permissions():
	"""สิทธิ์ของแต่ละชนิด (boot.saraban) ชนิดที่อ่านไม่ได้ไม่อยู่ในรายการ = ไม่มีเมนู"""
	return {
		kind: {"create": bool(frappe.has_permission(KINDS[kind]["doctype"], "create"))}
		for kind in saraban_kinds()
	}


def status_of(kind, row):
	"""(ป้าย, สี) ของเอกสารในแอป"""
	if cint(row.get("docstatus")) == 2:
		return _("ยกเลิก"), "rose"
	if cint(row.get("docstatus")) == 0:
		return _("ร่าง"), "gray"
	if kind == "letters-in":
		return {
			LI_PROPOSE: (_("รออนุมัติ"), "amber"),
			LI_APPROVED: (_("อนุมัติ"), "green"),
			LI_REJECTED: (_("ไม่อนุมัติ"), "rose"),
		}.get(row.get("status"), (_("รอเสนอ"), "blue"))
	if kind == "letters-out":
		return {
			"พิจารณา": (_("พิจารณา"), "amber"),
			"อนุมัติ": (_("อนุมัติ"), "green"),
			"ไม่อนุมัติ": (_("ไม่อนุมัติ"), "rose"),
		}.get(row.get("document_status"), (_("ดำเนินการ"), "blue"))
	if kind == "transmittals":
		return {
			"Sent": (_("ส่งแล้ว"), "blue"),
			"Received": (_("รับแล้ว"), "green"),
		}.get(row.get("status"), (_("รอส่ง"), "amber"))
	return _("ส่งแล้ว"), "green"


def with_labels(kind, rows):
	for row in rows:
		row["status_label"], row["status_tone"] = status_of(kind, row)
	return rows


@frappe.whitelist()
def get_list(kind, company=None, project=None):
	config = config_of(kind)
	frappe.has_permission(config["doctype"], "read", throw=True)
	filters = {}
	if company:
		filters["company"] = company
	if project and kind != "envelopes":
		filters["project"] = project
	rows = frappe.get_list(
		config["doctype"],
		filters=filters,
		fields=["name", "docstatus", "modified", *config["list"]],
		order_by=f"{config['date']} desc, creation desc",
		limit_page_length=LIST_LIMIT,
	)
	return with_labels(kind, rows)


@frappe.whitelist()
def get_summary(company=None, project=None, **_kwargs):
	"""ตัวเลขบนเมนู: หนังสือเข้าที่รอผู้ใช้คนนี้อนุมัติ และใบนำส่งที่ยังไม่ได้ส่ง"""
	out = {}
	if frappe.has_permission("Letter In", "read"):
		filters = {"docstatus": 1, "status": LI_PROPOSE, "approver": frappe.session.user}
		if company:
			filters["company"] = company
		out["to_approve"] = {"count": frappe.db.count("Letter In", filters)}
	if frappe.has_permission("Transmittal", "read"):
		filters = {"docstatus": 1, "status": "To Send"}
		if company:
			filters["company"] = company
		if project:
			filters["project"] = project
		out["to_send"] = {
			"count": len(frappe.get_list("Transmittal", filters=filters, pluck="name", limit=999))
		}
	return out


def load_doc(kind, name):
	doc = frappe.get_doc(config_of(kind)["doctype"], name)
	doc.check_permission("read")
	return doc


def serialize(kind, doc):
	config = config_of(kind)
	out = doc.as_dict(no_default_fields=True)
	out.update(
		name=doc.name if not doc.is_new() else None, docstatus=doc.docstatus, modified=str(doc.modified or "")
	)
	if config.get("items"):
		out["items"] = [
			{**row.as_dict(no_default_fields=True), "name": row.name} for row in doc.get("transmittal_list")
		]
		out.pop("transmittal_list", None)
	out["status_label"], out["status_tone"] = status_of(kind, out)
	labels = {}
	for field in ("project", "party", "from", "to", "receiver"):
		if field == "receiver" and kind != "envelopes":
			continue
		value = doc.get(field)
		doctype = link_doctype(kind, field, doc)
		if value and doctype:
			labels[field] = label_of(doctype, value)
	out["labels"] = labels
	if kind == "envelopes":
		out["from_display"] = address_text(doc.get("from"))
		out["to_display"] = address_text(doc.get("to"))
	return out


def link_doctype(kind, field, doc):
	if field == "party":
		return doc.get("party_type")
	return {
		"project": "Project",
		"from": "Address",
		"to": "Address",
		"receiver": "Contact",
	}.get(field)


def label_of(doctype, name):
	field = SEARCH.get(doctype)
	label = frappe.db.get_value(doctype, name, field) if field else None
	return label or name


def address_text(name):
	if not name:
		return ""
	from frappe.contacts.doctype.address.address import get_address_display

	return get_address_display(name) or ""


def form_setup(kind):
	if kind == "transmittals":
		from consbiz.consbiz.doctype.transmittal.transmittal import get_source_doctypes

		return {"sources": get_source_doctypes()}
	if kind == "letters-in":
		return {"approvers": approvers()}
	return {}


def new_doc(kind, company=None, project=None):
	config = config_of(kind)
	doc = frappe.new_doc(config["doctype"])
	if company:
		doc.company = company
	if project and kind != "envelopes":
		doc.project = project
	if kind == "letters-in":
		doc.receiver = frappe.session.user
		doc.receive_date = nowdate()
		doc.status = LI_WAIT
	elif kind == "letters-out":
		doc.sender = frappe.session.user
		doc.sent_date = nowdate()
		doc.document_status = "ดำเนินการ"
	elif kind == "transmittals":
		doc.date = nowdate()
	elif kind == "envelopes":
		doc.sender = frappe.session.user
		doc.send_date = nowdate()
		doc.sender_name, doc.sender_tel = frappe.db.get_value(
			"User", frappe.session.user, ["full_name", "mobile_no"]
		) or (None, None)
		if company:
			doc.set("from", get_default_address("Company", company))
	return doc


@frappe.whitelist()
def get_form(kind, name=None, source=None, company=None, project=None):
	"""ค่าตั้งต้นของฟอร์ม name = ร่างที่แก้ source = ใบนำส่งต้นทางของใบปะหน้าใหม่"""
	config = config_of(kind)
	if name:
		doc = load_doc(kind, name)
		doc.check_permission("write")
		if doc.docstatus != 0:
			frappe.throw(_("เอกสารนี้ Submit แล้ว แก้ในฟอร์มไม่ได้"))
	elif kind == "envelopes" and source:
		doc = make_envelope("Transmittal", source)
		doc.check_permission("create")
	else:
		doc = new_doc(kind, company, project)
		doc.check_permission("create")
	return {
		"doc": serialize(kind, doc),
		"setup": form_setup(kind),
		"can_submit": bool(frappe.has_permission(config["doctype"], "submit")),
	}


def actions_of(kind, doc):
	"""ปุ่มของหน้าดูเอกสาร (สิทธิ์ของผู้ใช้คนนี้)"""
	can_write = bool(doc.has_permission("write"))
	out = {
		"can_delete": store_app.can_delete(doc),
		"can_edit": doc.docstatus == 0 and can_write,
		"can_submit": doc.docstatus == 0 and bool(doc.has_permission("submit")),
		"can_cancel": doc.docstatus == 1 and bool(doc.has_permission("cancel")),
		"can_update": doc.docstatus == 1 and can_write and bool(config_of(kind)["after"]),
	}
	if kind == "letters-in" and doc.docstatus == 1:
		me = frappe.session.user
		waiting = doc.status == LI_PROPOSE
		is_approver = waiting and doc.approver == me
		out.update(
			can_propose=can_write and doc.status not in (LI_PROPOSE, LI_APPROVED),
			can_decide=is_approver,
			can_withdraw=waiting and can_write and not is_approver,
			can_change_approver=waiting and (can_write or is_approver or APPROVER_ROLE in frappe.get_roles()),
		)
	if kind == "transmittals" and doc.docstatus == 1:
		out["can_envelope"] = bool(frappe.has_permission("Envelope", "create"))
	return out


@frappe.whitelist()
def get_view(kind, name):
	doc = load_doc(kind, name)
	result = {"doc": serialize(kind, doc), **actions_of(kind, doc)}
	if kind == "transmittals":
		result["pdf_url"] = pdf_url("Transmittal", name)
		result["envelopes"] = frappe.get_list(
			"Envelope",
			filters={"reference_doctype": "Transmittal", "reference_name": name, "docstatus": ("<", 2)},
			fields=["name", "send_date", "docstatus"],
			order_by="creation desc",
		)
	elif kind == "envelopes":
		result["prints"] = [
			{"format": fmt, "url": envelope_pdf_url(name, fmt)}
			for fmt in ENVELOPE_FORMATS
			if frappe.db.exists("Print Format", fmt)
		]
	elif kind == "letters-in" and doc.docstatus == 1:
		result["approvers"] = approvers()
	return result


def envelope_pdf_url(name, print_format):
	from urllib.parse import urlencode

	generator = (
		frappe.db.get_value("Print Format", print_format, "pdf_generator")
		or frappe.db.get_single_value("Print Settings", "pdf_generator")
		or "wkhtmltopdf"
	)
	params = {
		"doctype": "Envelope",
		"name": name,
		"format": print_format,
		"no_letterhead": 1,
		"pdf_generator": generator,
	}
	return "/api/method/frappe.utils.print_format.download_pdf?" + urlencode(params)


def fill(kind, doc, data):
	config = config_of(kind)
	for field in config["fields"]:
		if field in data:
			doc.set(field, data[field] or None)
	if config.get("items"):
		existing = {row.name for row in doc.get("transmittal_list")}
		doc.set("transmittal_list", [])
		for row in data.get("items") or []:
			values = {field: row.get(field) for field in config["items"] if field in row}
			if row.get("name") in existing:
				values["name"] = row["name"]
			doc.append("transmittal_list", values)


@frappe.whitelist(methods=["POST"])
def save_doc(kind, data, submit=0):
	"""บันทึก/แก้ร่าง แล้ว Submit ถ้า submit=1"""
	config = config_of(kind)
	data = store_app.parse(data)
	if data.get("name"):
		doc = load_doc(kind, data["name"])
		if doc.docstatus != 0:
			frappe.throw(_("เอกสารนี้ Submit แล้ว แก้ในฟอร์มไม่ได้"))
		if data.get("modified") and str(doc.modified) != data["modified"]:
			frappe.throw(_("เอกสารนี้ถูกแก้ไขจากที่อื่น โหลดใหม่ก่อนบันทึก"))
	else:
		doc = frappe.new_doc(config["doctype"])
		if kind == "letters-in":
			doc.status = LI_WAIT
	fill(kind, doc, data)
	doc.save()
	if cint(submit):
		doc.submit()
	return {"name": doc.name, "docstatus": doc.docstatus}


@frappe.whitelist(methods=["POST"])
def submit_doc(kind, name):
	doc = load_doc(kind, name)
	doc.submit()
	return get_view(kind, name)


@frappe.whitelist(methods=["POST"])
def cancel_doc(kind, name):
	doc = load_doc(kind, name)
	doc.cancel()
	return get_view(kind, name)


@frappe.whitelist(methods=["POST"])
def delete_doc(kind, name):
	store_app.delete_document(load_doc(kind, name))


@frappe.whitelist(methods=["POST"])
def update_submitted(kind, name, data):
	"""แก้หลัง Submit: สถานะหนังสือออก, วันที่ส่ง/ผู้รับ/วันที่รับของใบนำส่ง"""
	config = config_of(kind)
	data = store_app.parse(data)
	doc = load_doc(kind, name)
	if doc.docstatus != 1:
		frappe.throw(_("ใช้ได้กับเอกสารที่ Submit แล้วเท่านั้น"))
	doc.check_permission("write")
	for field in config["after"]:
		if field in data:
			doc.set(field, data[field] or None)
	doc.save()
	return get_view(kind, name)


# ---------------------------------------------------------------- ค้นหาในฟอร์ม


@frappe.whitelist()
def search(doctype, txt="", company=None, address=None):
	"""ช่องค้นหาของฟอร์ม Address ของบริษัท (company) / Contact ที่อยู่ address นั้น (address)"""
	label = SEARCH.get(doctype)
	if not label:
		frappe.throw(_("ค้นหา {0} ไม่ได้").format(doctype))
	if not saraban_kinds():
		frappe.throw(_("ไม่มีสิทธิ์"), frappe.PermissionError)
	txt = (txt or "").strip()
	filters = []
	if doctype == "User":
		filters += [
			["enabled", "=", 1],
			["user_type", "=", "System User"],
			["name", "not in", ("Administrator", "Guest")],
		]
	if doctype == "Address":
		filters.append(["disabled", "=", 0])
		if company:
			filters += [
				["Dynamic Link", "link_doctype", "=", "Company"],
				["Dynamic Link", "link_name", "=", company],
			]
	if doctype == "Contact" and address:
		filters.append(["address", "=", address])
	if doctype in ("Customer", "Supplier"):
		filters.append(["disabled", "=", 0])
	or_filters = [["name", "like", f"%{txt}%"], [label, "like", f"%{txt}%"]] if txt else None
	fields = ["name", f"{label} as label"]
	if doctype == "Address":
		fields += ["address_line1", "city"]
	rows = frappe.get_list(
		doctype,
		filters=filters,
		or_filters=or_filters,
		fields=fields,
		order_by="modified desc",
		limit_page_length=30,
		distinct=True,
	)
	out = []
	for row in rows:
		description = " ".join(filter(None, [row.get("address_line1"), row.get("city")])) or (
			row.name if row.label and row.label != row.name else ""
		)
		out.append({"value": row.name, "label": row.label or row.name, "description": description})
	return out


@frappe.whitelist()
def address_display(name):
	frappe.has_permission("Address", "read", name, throw=True)
	return address_text(name)


@frappe.whitelist()
def user_contact(user):
	"""ชื่อและเบอร์ของผู้ส่ง (ใบปะหน้า)"""
	frappe.has_permission("Envelope", "read", throw=True)
	values = frappe.db.get_value("User", user, ["full_name", "mobile_no"], as_dict=True) or {}
	return {"sender_name": values.get("full_name"), "sender_tel": values.get("mobile_no")}


@frappe.whitelist()
def transmittal_documents(
	source, company, recipient_type=None, party=None, from_date=None, to_date=None, project=None, exclude=None
):
	"""เอกสารที่ดึงเข้าใบนำส่งได้ (transmittal.get_documents ตรวจสิทธิ์อ่านของเอกสารต้นทางเอง)"""
	from consbiz.consbiz.doctype.transmittal.transmittal import get_documents

	frappe.has_permission("Transmittal", "write", throw=True)
	return get_documents(
		source,
		company,
		recipient_type=recipient_type,
		party=party,
		from_date=from_date,
		to_date=to_date,
		project=project,
		exclude=exclude,
	)


# ---------------------------------------------------------------- หนังสือเข้า: เสนออนุมัติ


def approvers():
	users = frappe.get_all(
		"Has Role", filters={"role": APPROVER_ROLE, "parenttype": "User"}, pluck="parent", distinct=True
	)
	users = [u for u in users if u not in ("Administrator", "Guest")]
	if not users:
		return []
	rows = frappe.get_all(
		"User",
		filters={"name": ("in", users), "enabled": 1},
		fields=["name", "full_name"],
		order_by="full_name asc",
	)
	return [{"value": r.name, "label": r.full_name or r.name, "description": r.name} for r in rows]


def letter_in(name):
	doc = load_doc("letters-in", name)
	if doc.docstatus != 1:
		frappe.throw(_("ต้อง Submit หนังสือก่อน"))
	return doc


def check_approver(user):
	if user not in {a["value"] for a in approvers()}:
		frappe.throw(_("{0} ไม่ได้เป็นผู้อนุมัติ (Role {1})").format(user, APPROVER_ROLE))


def save_after_submit(doc):
	# ผู้อนุมัติอาจไม่มีสิทธิ์เขียน Letter In: ตรวจสิทธิ์ของแต่ละขั้นแล้วก่อนเรียก
	doc.flags.ignore_permissions = True
	doc.save()


def assign(doc, user):
	try:
		assign_to._add(
			{
				"doctype": doc.doctype,
				"name": doc.name,
				"assign_to": [user],
				"description": _("เสนออนุมัติหนังสือรับ {0}").format(doc.name),
				"notify": 1,
			},
			ignore_permissions=True,
		)
	except frappe.DuplicateToDoError:
		frappe.clear_last_message()


def unassign(doc, user, close=False):
	if not user:
		return
	try:
		assign_to.set_status(
			doc.doctype,
			doc.name,
			assign_to=user,
			status="Closed" if close else "Cancelled",
			ignore_permissions=True,
		)
	except Exception:
		frappe.clear_last_message()


@frappe.whitelist(methods=["POST"])
def propose(name, approver):
	"""เสนออนุมัติ (ครั้งแรก หรือเสนอใหม่หลังถอนเรื่อง/ไม่อนุมัติ) ล้างผลพิจารณาเดิม"""
	doc = letter_in(name)
	if not actions_of("letters-in", doc).get("can_propose"):
		frappe.throw(_("เสนออนุมัติหนังสือนี้ไม่ได้"), frappe.PermissionError)
	check_approver(approver)
	doc.update({"status": LI_PROPOSE, "approver": approver, "approve_date": None, "approve_remark": ""})
	save_after_submit(doc)
	assign(doc, approver)
	return get_view("letters-in", name)


@frappe.whitelist(methods=["POST"])
def change_approver(name, approver):
	doc = letter_in(name)
	if not actions_of("letters-in", doc).get("can_change_approver"):
		frappe.throw(_("เปลี่ยนผู้อนุมัติไม่ได้"), frappe.PermissionError)
	check_approver(approver)
	current = doc.approver
	if current == approver:
		return get_view("letters-in", name)
	doc.approver = approver
	save_after_submit(doc)
	unassign(doc, current)
	assign(doc, approver)
	return get_view("letters-in", name)


@frappe.whitelist(methods=["POST"])
def withdraw(name):
	doc = letter_in(name)
	if not actions_of("letters-in", doc).get("can_withdraw"):
		frappe.throw(_("ถอนเรื่องไม่ได้"), frappe.PermissionError)
	current = doc.approver
	doc.update({"status": LI_WAIT, "approver": None})
	save_after_submit(doc)
	unassign(doc, current)
	return get_view("letters-in", name)


@frappe.whitelist(methods=["POST"])
def decide(name, approve, approve_date=None, remark=None):
	"""ผู้อนุมัติที่ถูกเสนอเท่านั้น ไม่อนุมัติต้องมีเหตุผล"""
	doc = letter_in(name)
	if not actions_of("letters-in", doc).get("can_decide"):
		frappe.throw(_("เฉพาะผู้อนุมัติที่ถูกเสนอเท่านั้น"), frappe.PermissionError)
	approve = cint(approve)
	remark = (remark or "").strip()
	if not approve and not remark:
		frappe.throw(_("กรุณาระบุเหตุผลที่ไม่อนุมัติ"))
	doc.update(
		{
			"status": LI_APPROVED if approve else LI_REJECTED,
			"approve_date": getdate(approve_date or nowdate()),
			"approve_remark": remark,
		}
	)
	save_after_submit(doc)
	unassign(doc, doc.approver, close=True)
	return get_view("letters-in", name)
