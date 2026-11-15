# Copyright (c) 2026, Siricons and contributors
# For license information, please see license.txt

"""แอปผู้รับเหมาช่วง (/contractor, www/contractor.py) สำหรับคนนอก เข้าได้ 2 แบบ (หน้าจอชุดเดียวกัน):
1. บัญชีผู้ใช้ (Website User ในตาราง Portal Users ของ Supplier) เห็นทุกสัญญาของผู้รับเหมาที่ผูก
2. ลิงก์ของสัญญา (`/contractor/k/<Subcontract Agreement.contractor_token>`, ไม่ต้อง login) เห็นเฉพาะสัญญานั้น
   ใช้ได้จนสัญญาปิด (Closed) หรือยกเลิก เจ้าหน้าที่สร้างลิงก์ใหม่ได้ (ลิงก์เดิมใช้ไม่ได้ทันที, subcontract_app.reset_contractor_link)

ทุก endpoint เป็น allow_guest และต้องเรียก `use(token)` เป็นบรรทัดแรก (ตั้งขอบเขตของคำขอ: ผู้รับเหมา + สัญญาที่เห็นได้)
แล้วตรวจเอกสารกับขอบเขตนั้นก่อนอ่าน/บันทึกแบบ ignore_permissions ห้ามรับชื่อ field อิสระจากภายนอก (รับเฉพาะ CLAIM_INPUT และปริมาณรายแถว)

ใบเบิกที่ ผรม. ร่าง (`from_contractor`, `prepared_by` = ผู้ใช้ที่ login หรือว่างเมื่อมาจากลิงก์):
ร่าง (Draft) → ส่งให้ตรวจ (Pending Review) → เจ้าหน้าที่ Submit (อนุมัติ) หรือส่งกลับแก้ (Returned + เหตุผล, subcontract.return_claim)
ผรม. แก้ได้เฉพาะ Draft/Returned เจ้าหน้าที่แก้/อนุมัติได้เมื่อ Pending Review ใบที่เจ้าหน้าที่ร่างเอง ผรม. เห็นเมื่ออนุมัติแล้วเท่านั้น
ค่าปรับ (penalty_days) และ % งานจริงในแผนเป็นของฝ่ายเรา ผรม. ไม่กรอก/ไม่เห็น % แผน
ไฟล์แนบอัปโหลดผ่าน `upload_file` ของโมดูลนี้ (คนที่ไม่ได้ login ใช้ upload_file ของ Frappe ไม่ได้) เปิดผ่าน `open_file`"""

import re

import frappe
from frappe import _
from frappe.utils import flt, now_datetime, nowdate

from consbiz import store_app, subcontract
from consbiz.subcontract_app import claim_context

CLAIM_INPUT = ("posting_date", "period_from", "period_to", "milestone", "remarks")
EDITABLE = ("Draft", "Returned")
STATUS = {
	"Draft": (_("ร่าง"), "gray"),
	"Pending Review": (_("รอตรวจ"), "amber"),
	"Returned": (_("ส่งกลับแก้"), "rose"),
	"Approved": (_("อนุมัติแล้ว"), "blue"),
	"Paid": (_("ตั้งหนี้แล้ว"), "green"),
	"Cancelled": (_("ยกเลิก"), "gray"),
	"Active": (_("ดำเนินการ"), "blue"),
	"Completed": (_("เบิกครบ"), "green"),
	"Closed": (_("ปิดสัญญา"), "gray"),
}
MAX_FILES = 30
MAX_FILE_SIZE = 10 * 1024 * 1024
UPLOAD_TYPES = ("jpg", "jpeg", "png", "webp", "heic", "heif", "gif", "pdf")
IMAGE_TYPES = ("jpg", "jpeg", "png", "webp", "heic", "heif", "gif")
TOKEN_PATTERN = re.compile(r"^[A-Za-z0-9_-]{20,64}$")


class LinkExpired(frappe.PermissionError):
	pass


# ---------------------------------------------------------------- ขอบเขตของคำขอ


def my_suppliers(user=None):
	"""ผู้รับเหมา (Supplier) ที่ผู้ใช้ผูกอยู่ใน Portal Users"""
	user = user or frappe.session.user
	if user == "Guest":
		return []
	return frappe.get_all(
		"Portal User", filters={"parenttype": "Supplier", "user": user}, pluck="parent", distinct=True
	)


def agreement_of_token(token):
	"""สัญญาของลิงก์ที่ยังใช้ได้ (Submit แล้ว ไม่ปิด/ไม่ยกเลิก) ไม่พบ/หมดอายุ = None"""
	if not token or not TOKEN_PATTERN.match(token):
		return None
	row = frappe.db.get_value(
		"Subcontract Agreement",
		{"contractor_token": token},
		["name", "supplier", "supplier_name", "title", "docstatus", "status"],
		as_dict=True,
	)
	if not row or row.docstatus != 1 or row.status == "Closed":
		return None
	return row


def use(token=None):
	"""ตั้งขอบเขตของคำขอนี้ (ทุก endpoint เรียกก่อนทำอย่างอื่น)
	ลิงก์ = ผู้รับเหมาของสัญญานั้น + เฉพาะสัญญานั้น / ไม่มีลิงก์ = ต้อง login และผูก Portal Users"""
	if token:
		row = agreement_of_token(token)
		if not row:
			frappe.throw(
				_("ลิงก์นี้ใช้ไม่ได้แล้ว (สัญญาปิด/ยกเลิก หรือมีการสร้างลิงก์ใหม่) ติดต่อเจ้าหน้าที่ของบริษัท"),
				LinkExpired,
			)
		frappe.local.contractor_scope = frappe._dict(suppliers=[row.supplier], agreement=row.name)
	else:
		if frappe.session.user == "Guest":
			frappe.throw(_("กรุณาเข้าสู่ระบบ หรือเปิดจากลิงก์ที่บริษัทส่งให้"), frappe.PermissionError)
		frappe.local.contractor_scope = frappe._dict(suppliers=my_suppliers(), agreement=None)
	return frappe.local.contractor_scope


def scope():
	current = getattr(frappe.local, "contractor_scope", None)
	if current is None:
		deny()
	return current


def scope_filters(field="subcontract_agreement"):
	"""ตัวกรองของรายการตามขอบเขต (ลิงก์ = เฉพาะสัญญานั้น)"""
	current = scope()
	filters = {"supplier": ("in", current.suppliers or [""])}
	if current.agreement:
		filters[field] = current.agreement
	return filters


def website_user_home_page(user):
	"""หน้าแรกหลัง login / ที่ "/" (hook get_website_user_home_page ซึ่ง Frappe เรียกกับผู้ใช้ทุกคน)
	เฉพาะ Website User ที่ผูกกับผู้รับเหมา = /contractor คนอื่นคืน None ให้ Frappe ใช้หน้าปกติ (System User = desk)"""
	if user in ("Guest", "Administrator") or frappe.db.get_value("User", user, "user_type") != "Website User":
		return None
	return "contractor" if my_suppliers(user) else None


def deny():
	frappe.throw(_("ไม่พบเอกสาร หรือคุณไม่มีสิทธิ์ดูเอกสารนี้"), frappe.PermissionError)


def in_scope(supplier, agreement):
	current = scope()
	return supplier in current.suppliers and (not current.agreement or agreement == current.agreement)


def check_agreement(name):
	"""สัญญาที่ Submit แล้วในขอบเขตของคำขอนี้"""
	if not name:
		deny()
	row = frappe.db.get_value("Subcontract Agreement", name, ["supplier", "docstatus"], as_dict=True)
	if not row or row.docstatus != 1 or not in_scope(row.supplier, name):
		deny()
	return frappe.get_doc("Subcontract Agreement", name)


def visible(claim):
	"""ใบเบิกที่ ผรม. เห็น: ที่ ผรม. ร่างเอง (ทุกสถานะ) หรือที่อนุมัติแล้ว"""
	return bool(claim.from_contractor) or claim.docstatus == 1


def check_claim(name):
	if not name or not frappe.db.exists("Subcontract Claim", name):
		deny()
	doc = frappe.get_doc("Subcontract Claim", name)
	if not in_scope(doc.supplier, doc.subcontract_agreement) or not visible(doc):
		deny()
	return doc


def check_editable(doc):
	if doc.docstatus != 0 or not doc.from_contractor or doc.status not in EDITABLE:
		frappe.throw(_("ใบเบิกนี้ส่งให้ตรวจแล้ว แก้ไม่ได้ (ถอนกลับก่อนถ้ายังไม่ตรวจ)"))


# ---------------------------------------------------------------- boot / หน้าแรก


def boot_data(token=None):
	base = {"today": nowdate(), "desk": False, "can": {}, "user_image": None}
	if token:
		# ลิงก์: ไม่มีผู้ใช้ ชื่อที่แสดง = ผู้รับเหมา หน้าแรก = สัญญานั้น
		row = agreement_of_token(token)
		if not row:
			return {
				**base,
				"guest": True,
				"user": "Guest",
				"full_name": _("ผู้รับเหมา"),
				"sections": [],
				"suppliers": [],
				"link_error": _(
					"ลิงก์นี้ใช้ไม่ได้แล้ว (สัญญาปิด/ยกเลิก หรือมีการสร้างลิงก์ใหม่) ติดต่อเจ้าหน้าที่ของบริษัทเพื่อขอลิงก์ใหม่"
				),
			}
		return {
			**base,
			"guest": frappe.session.user == "Guest",
			"user": row.supplier_name,
			"full_name": row.supplier_name,
			"token": token,
			"agreement": row.name,
			"sections": ["contractor"],
			"suppliers": [{"name": row.supplier, "supplier_name": row.supplier_name}],
		}
	user = frappe.get_cached_doc("User", frappe.session.user)
	suppliers = my_suppliers()
	return {
		**base,
		"user": user.name,
		"full_name": user.full_name or user.name,
		"user_image": user.user_image,
		"sections": ["contractor"] if suppliers else [],
		"suppliers": [
			{"name": s, "supplier_name": frappe.db.get_value("Supplier", s, "supplier_name") or s}
			for s in suppliers
		],
	}


def label(row, status=None):
	status = status or row.get("status")
	row["status_label"], row["status_tone"] = STATUS.get(status, STATUS["Draft"])
	return row


def claim_status(row):
	"""ใบเบิกที่อนุมัติแล้วและตั้งหนี้แล้ว (PI Submit) = ตั้งหนี้แล้ว"""
	if row.get("status") == "Approved" and row.get("purchase_invoice"):
		if frappe.db.get_value("Purchase Invoice", row["purchase_invoice"], "docstatus") == 1:
			return "Paid"
	return row.get("status")


def claim_rows(filters):
	rows = frappe.get_all(
		"Subcontract Claim",
		filters={"docstatus": ("<", 2), **filters},
		or_filters={"from_contractor": 1, "docstatus": 1},
		fields=[
			"name",
			"subcontract_agreement",
			"title",
			"supplier_name",
			"claim_no",
			"posting_date",
			"gross_amount",
			"net_amount",
			"status",
			"docstatus",
			"purchase_invoice",
			"return_reason",
			"modified",
		],
		order_by="posting_date desc, creation desc",
		limit_page_length=200,
	)
	for row in rows:
		label(row, claim_status(row))
		row.pop("purchase_invoice", None)
	return rows


@frappe.whitelist(allow_guest=True)
def get_summary(token=None, **_kwargs):
	"""ตัวเลขเมนู: ใบเบิกที่ถูกส่งกลับแก้ และที่รอตรวจ"""
	if not use(token).suppliers:
		return {}
	base = {**scope_filters(), "docstatus": 0, "from_contractor": 1}
	return {
		"returned": frappe.db.count("Subcontract Claim", {**base, "status": "Returned"}),
		"pending": frappe.db.count("Subcontract Claim", {**base, "status": "Pending Review"}),
	}


AGREEMENT_LIST = (
	"name",
	"title",
	"contract_no",
	"supplier",
	"supplier_name",
	"project",
	"contract_date",
	"start_date",
	"end_date",
	"billing_method",
	"total_amount",
	"claimed_amount",
	"progress_percent",
	"status",
)


@frappe.whitelist(allow_guest=True)
def get_home(token=None):
	if not use(token).suppliers:
		return {"agreements": [], "claims": []}
	agreements = frappe.get_all(
		"Subcontract Agreement",
		filters={**scope_filters("name"), "docstatus": 1},
		fields=list(AGREEMENT_LIST),
		order_by="contract_date desc, creation desc",
		limit_page_length=200,
	)
	projects = project_names({a.project for a in agreements})
	for a in agreements:
		a.project_name = projects.get(a.project, a.project)
		label(a)
	return {"agreements": agreements, "claims": claim_rows(scope_filters())}


def project_names(projects):
	projects = [p for p in projects if p]
	if not projects:
		return {}
	return dict(
		frappe.get_all(
			"Project", filters={"name": ("in", projects)}, fields=["name", "project_name"], as_list=True
		)
	)


# ---------------------------------------------------------------- สัญญา


def open_claim(agreement):
	"""ใบเบิกที่ ผรม. ร่างค้างอยู่ (ยังไม่อนุมัติ) ของสัญญานี้ (1 สัญญามีได้ใบเดียว)"""
	return frappe.db.get_value(
		"Subcontract Claim",
		{"subcontract_agreement": agreement, "docstatus": 0, "from_contractor": 1},
		"name",
	)


@frappe.whitelist(allow_guest=True)
def get_agreement(name=None, token=None):
	use(token)
	# ลิงก์: ไม่ส่งชื่อ = สัญญาของลิงก์
	doc = check_agreement(name or scope().agreement)
	out = {field: doc.get(field) for field in AGREEMENT_LIST}
	out.update(
		{
			field: doc.get(field)
			for field in (
				"retention_percent",
				"retention_cap_percent",
				"wht_percent",
				"advance_percent",
				"advance_amount",
				"advance_recovery_percent",
				"penalty_per_day",
				"warranty_days",
				"retention_held",
				"advance_recovered",
				"penalty_total",
				"original_amount",
				"variation_amount",
				"revision",
				"closed_on",
				"close_reason",
				"warranty_end",
				"purchase_order",
			)
		}
	)
	out["project_name"] = project_names([doc.project]).get(doc.project, doc.project)
	out["items"] = [
		{
			f: row.get(f)
			for f in (
				"name",
				"wbs",
				"item_name",
				"uom",
				"qty",
				"rate",
				"amount",
				"claimed_qty",
				"claimed_amount",
				"variation",
			)
		}
		for row in doc.items
	]
	out["milestones"] = [
		{
			f: m.get(f)
			for f in ("name", "description", "percent", "amount", "target_date", "condition", "subcontract_claim")
		}
		for m in doc.milestones
	]
	label(out)
	draft = open_claim(doc.name)
	return {
		"doc": out,
		"claims": claim_rows({"subcontract_agreement": doc.name}),
		"variations": frappe.get_all(
			"Subcontract Variation",
			filters={"subcontract_agreement": doc.name, "docstatus": 1},
			fields=["name", "revision_no", "posting_date", "reason", "addition_amount", "revised_amount"],
			order_by="revision_no asc",
		),
		"open_claim": draft,
		"can_claim": doc.status == "Active" and not draft,
	}


# ---------------------------------------------------------------- ใบเบิก


ITEM_FIELDS = (
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
)


def serialize_claim(doc):
	out = {
		field: doc.get(field)
		for field in (
			*CLAIM_INPUT,
			"subcontract_agreement",
			"title",
			"supplier_name",
			"billing_method",
			"claim_no",
			"status",
			"milestone_description",
			"milestone_percent",
			"gross_amount",
			"advance_recovery",
			"retention_amount",
			"wht_amount",
			"penalty_days",
			"penalty_amount",
			"net_amount",
			"submitted_on",
			"return_reason",
		)
	}
	out.update(
		name=doc.name if not doc.is_new() else None,
		docstatus=doc.docstatus,
		modified=str(doc.modified or ""),
		items=[{f: row.get(f) for f in ITEM_FIELDS} for row in doc.items],
	)
	label(out, claim_status({"status": doc.status, "purchase_invoice": doc.purchase_invoice}))
	return out


def files_of(doc):
	if doc.is_new():
		return []
	return frappe.get_all(
		"File",
		filters={"attached_to_doctype": "Subcontract Claim", "attached_to_name": doc.name, "is_folder": 0},
		fields=["name", "file_name", "file_size", "owner", "creation"],
		order_by="creation asc",
	)


def extension(file_name):
	return (file_name or "").lower().rsplit(".", 1)[-1]


def claim_view(doc):
	ctx = claim_context(doc)
	editable = doc.is_new() or (doc.docstatus == 0 and bool(doc.from_contractor) and doc.status in EDITABLE)
	files = files_of(doc)
	for f in files:
		f["is_image"] = extension(f.file_name) in IMAGE_TYPES
		# ลิงก์ = ทุกคนที่ถือลิงก์คือผู้รับเหมาเดียวกัน (ไฟล์เป็นของ Guest) / บัญชีผู้ใช้ = ไฟล์ที่แนบเอง
		f["can_remove"] = editable and f.pop("owner") == frappe.session.user
	return {
		"doc": serialize_claim(doc),
		"agreement": ctx["agreement"],
		"milestones": ctx.get("milestones"),
		"appendix": ctx.get("appendix"),
		"files": files,
		"can_edit": editable,
		"can_send": not doc.is_new() and editable,
		"can_withdraw": doc.docstatus == 0 and doc.status == "Pending Review",
		"can_delete": not doc.is_new() and editable,
		"can_upload": not doc.is_new() and editable and len(files) < MAX_FILES,
	}


def new_claim(agreement):
	doc = check_agreement(agreement)
	if doc.status != "Active":
		frappe.throw(_("สัญญานี้เบิกเพิ่มไม่ได้ (สถานะ: {0})").format(STATUS.get(doc.status, (doc.status,))[0]))
	draft = open_claim(doc.name)
	if draft:
		frappe.throw(_("มีใบเบิก {0} ที่ยังไม่อนุมัติอยู่แล้ว แก้ใบนั้นแทน").format(draft))
	claim = frappe.new_doc("Subcontract Claim")
	claim.subcontract_agreement = doc.name
	claim.supplier = doc.supplier
	claim.from_contractor = 1
	claim.prepared_by = frappe.session.user if frappe.session.user != "Guest" else None
	claim.posting_date = nowdate()
	return claim


@frappe.whitelist(allow_guest=True)
def get_claim(name=None, agreement=None, token=None):
	use(token)
	if name:
		return claim_view(check_claim(name))
	doc = new_claim(agreement or scope().agreement)
	try:
		# ค่าตั้งต้น: งวดงานแรกที่ว่าง (สัญญาตามงวด) / ปริมาณงวดนี้ 0 (ตามปริมาณ)
		ctx = claim_context(doc)
		if ctx.get("milestones"):
			doc.milestone = ctx["milestones"][0]["value"]
		subcontract.validate_claim(doc)
	except frappe.ValidationError:
		pass
	frappe.clear_messages()
	return claim_view(doc)


def fill(doc, data):
	for field in CLAIM_INPUT:
		if field in data:
			doc.set(field, data[field] or None)
	doc.set("items", [])
	for row in data.get("items") or []:
		if row.get("agreement_item"):
			doc.append("items", {"agreement_item": str(row["agreement_item"]), "qty": flt(row.get("qty"))})


def load_for_edit(data):
	if data.get("name"):
		doc = check_claim(data["name"])
		check_editable(doc)
		if data.get("modified") and str(doc.modified) != data["modified"]:
			frappe.throw(_("ใบเบิกนี้ถูกแก้ไขจากที่อื่น โหลดใหม่ก่อนบันทึก"))
		return doc
	return new_claim(data.get("subcontract_agreement") or scope().agreement)


@frappe.whitelist(allow_guest=True, methods=["POST"])
def preview_claim(data, token=None):
	"""คำนวณยอดจากค่าที่กรอก (ไม่บันทึก) ข้อผิดพลาดส่งกลับเป็นข้อความ"""
	use(token)
	data = store_app.parse(data)
	doc = load_for_edit(data)
	fill(doc, data)
	error = None
	try:
		subcontract.validate_claim(doc)
	except frappe.ValidationError as e:
		error = str(e)
	frappe.clear_messages()
	return {"doc": serialize_claim(doc), "error": error}


@frappe.whitelist(allow_guest=True, methods=["POST"])
def save_claim(data, send=0, token=None):
	use(token)
	data = store_app.parse(data)
	doc = load_for_edit(data)
	fill(doc, data)
	doc.flags.ignore_permissions = True
	doc.save()
	# % งานจริงในแผนเป็นข้อมูลภายใน: ไม่ส่งคำเตือนเบิกเกินแผนให้ ผรม.
	frappe.clear_messages()
	if frappe.utils.cint(send):
		send_for_review(doc)
	return claim_view(doc)


def send_for_review(doc):
	doc.db_set({"status": "Pending Review", "submitted_on": now_datetime(), "return_reason": None})
	doc.add_comment("Info", _("ผู้รับเหมาส่งใบเบิกให้ตรวจ"))
	subcontract.notify_users(
		subcontract.role_users(doc.company, subcontract.CLAIM_REVIEW_ROLES),
		"Subcontract Claim",
		doc.name,
		_("{0} ส่งใบเบิกงวดที่ {1} ({2}) ให้ตรวจ").format(doc.supplier_name, doc.claim_no, doc.title),
	)


@frappe.whitelist(allow_guest=True, methods=["POST"])
def send_claim(name, token=None):
	use(token)
	doc = check_claim(name)
	check_editable(doc)
	# ตรวจยอดล่าสุดก่อนส่ง (ใบเบิกอื่นอาจอนุมัติไปแล้วระหว่างนี้)
	doc.flags.ignore_permissions = True
	doc.save()
	frappe.clear_messages()
	send_for_review(doc)
	return claim_view(doc)


@frappe.whitelist(allow_guest=True, methods=["POST"])
def withdraw_claim(name, token=None):
	"""ถอนใบเบิกที่ส่งไปแล้ว (ยังไม่ตรวจ) กลับมาแก้"""
	use(token)
	doc = check_claim(name)
	if doc.docstatus != 0 or not doc.from_contractor or doc.status != "Pending Review":
		frappe.throw(_("ถอนได้เฉพาะใบเบิกที่รอตรวจ"))
	doc.db_set({"status": "Draft", "submitted_on": None})
	doc.add_comment("Info", _("ผู้รับเหมาถอนใบเบิกกลับไปแก้"))
	return claim_view(doc)


@frappe.whitelist(allow_guest=True, methods=["POST"])
def delete_claim(name, token=None):
	use(token)
	doc = check_claim(name)
	check_editable(doc)
	frappe.delete_doc("Subcontract Claim", doc.name, ignore_permissions=True)


# ---------------------------------------------------------------- ไฟล์แนบ


def check_file(name, claim):
	row = frappe.db.get_value(
		"File", name, ["name", "attached_to_doctype", "attached_to_name", "owner"], as_dict=True
	)
	if not row or row.attached_to_doctype != "Subcontract Claim" or row.attached_to_name != claim.name:
		deny()
	return row


@frappe.whitelist(allow_guest=True, methods=["POST"])
def upload_file(name, token=None):
	"""แนบรูป/PDF 1 ไฟล์ (multipart ช่อง `file`) กับใบเบิกที่ยังแก้ได้ เก็บเป็นไฟล์ private"""
	use(token)
	doc = check_claim(name)
	check_editable(doc)
	upload = frappe.request.files.get("file") if frappe.request else None
	if not upload or not upload.filename:
		frappe.throw(_("ไม่พบไฟล์"))
	file_name = re.sub(r"[^\w.\- ]", "_", upload.filename.rsplit("/", 1)[-1])[-120:] or "file"
	if extension(file_name) not in UPLOAD_TYPES:
		frappe.throw(_("แนบได้เฉพาะรูปภาพหรือ PDF"))
	content = upload.stream.read(MAX_FILE_SIZE + 1)
	if len(content) > MAX_FILE_SIZE:
		frappe.throw(_("ไฟล์ใหญ่เกิน {0} MB").format(MAX_FILE_SIZE // 1024 // 1024))
	if len(files_of(doc)) >= MAX_FILES:
		frappe.throw(_("แนบไฟล์ได้ไม่เกิน {0} ไฟล์ต่อใบเบิก").format(MAX_FILES))
	frappe.get_doc(
		{
			"doctype": "File",
			"file_name": file_name,
			"content": content,
			"attached_to_doctype": "Subcontract Claim",
			"attached_to_name": doc.name,
			"is_private": 1,
		}
	).insert(ignore_permissions=True)
	return claim_view(doc)


@frappe.whitelist(allow_guest=True, methods=["POST"])
def remove_file(name, file, token=None):
	use(token)
	doc = check_claim(name)
	check_editable(doc)
	row = check_file(file, doc)
	if row.owner != frappe.session.user:
		frappe.throw(_("ลบได้เฉพาะไฟล์ที่คุณแนบเอง"))
	frappe.delete_doc("File", row.name, ignore_permissions=True)
	return claim_view(doc)


@frappe.whitelist(allow_guest=True)
def open_file(name, file, token=None):
	"""เปิดไฟล์แนบของใบเบิก (ไฟล์ private: ผู้รับเหมาเปิดตรงๆ ไม่ได้)"""
	use(token)
	doc = check_claim(name)
	row = check_file(file, doc)
	f = frappe.get_doc("File", row.name)
	frappe.local.response.filename = f.file_name
	frappe.local.response.filecontent = f.get_content()
	frappe.local.response.type = "download"
	frappe.local.response.display_content_as = "inline"
