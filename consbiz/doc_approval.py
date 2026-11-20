# Copyright (c) 2026, Siricons and contributors
# For license information, please see license.txt

"""ขั้นอนุมัติ/ลงนามของเอกสารจัดซื้อในแอป (ตกลง 2026-11-19)

- ใบขอซื้อ (MR ซื้อ/ผู้ว่าจ้างจัดหา) = อนุมัติ: ร่าง → ส่งอนุมัติ → อนุมัติ (= Submit) / ไม่อนุมัติ (ส่งกลับแก้ไข)
- ใบสั่งซื้อ (PO) / ใบแจ้งหนี้ซื้อ (PI) = ลงนาม: ร่าง → ส่งลงนาม → ลงนาม (= Submit) / ส่งกลับแก้ไข
- ผู้ส่งดึงเอกสารกลับได้ระหว่างรอ ผู้มีสิทธิ์อนุมัติ/ลงนามกดจากร่างได้เลย (อนุมัติของตัวเองได้ถ้ามีสิทธิ์)
- บันทึกการลงนามแทน (PO/PI, เมนู ⋯): ผู้บริหารที่ไม่ได้ใช้ระบบเซ็นบนกระดาษ เจ้าหน้าที่บันทึกในระบบแทน
  ผู้ลงนาม + วันที่ลงนาม + ไฟล์สแกน/รูปเอกสารที่เซ็นแล้ว (บังคับ) → Submit โดยผู้ลงนาม = คนนั้น, Comment + แจ้งผู้ลงนาม

Role ที่อนุมัติ/ลงนาม และ Role ที่บันทึกแทนได้ ตั้งในหน้า ตั้งค่าจัดซื้อ > การอนุมัติ/ลงนาม
(global default `consbiz_approval::<DocType>` = JSON {"roles": [...], "proxy_roles": [...]}) ยังไม่ตั้ง = DEFAULTS
Submit ทุกทาง (แอป, ระบบเต็ม, ยืนยันหลายใบ) ตรวจ Role ใน before_submit (guard_submit) รออนุมัติ = แก้ไม่ได้ (guard_pending)
ช่องที่ใช้ (Custom Field บนทั้ง 3 DocType): custom_approval_status ("" / Pending / Approved / Rejected), custom_sent_by,
custom_sent_on, custom_review_note, custom_signed_by, custom_signed_on, custom_signed_by_proxy, custom_signed_proof
"""

import json

import frappe
from frappe import _
from frappe.utils import cint, get_datetime, getdate, now_datetime

FLOWS = {
	"Material Request": {"kind": "mr", "mode": "approve", "label": "ใบขอซื้อ"},
	"Purchase Order": {"kind": "po", "mode": "sign", "label": "ใบสั่งซื้อ"},
	"Purchase Invoice": {"kind": "pi", "mode": "sign", "label": "ใบแจ้งหนี้ซื้อ"},
}
# ใบขอซื้อประเภทอื่น (โอน/เบิก ของคลัง) ไม่ผ่านขั้นนี้
MR_TYPES = ("Purchase", "Customer Provided")
DEFAULTS = {
	"Material Request": {"roles": ["Purchase Manager", "Projects Manager"], "proxy_roles": []},
	"Purchase Order": {"roles": ["Purchase Manager", "Projects Manager"], "proxy_roles": ["Purchase User"]},
	"Purchase Invoice": {"roles": ["Purchase Manager", "Accounts Manager"], "proxy_roles": ["Accounts User"]},
}
EDIT_ROLES = ("Purchase Manager", "System Manager")
WORDS = {
	"approve": {
		"send": "ส่งอนุมัติ",
		"do": "อนุมัติ",
		"done": "อนุมัติแล้ว",
		"pending": "รออนุมัติ",
		"reject": "ส่งกลับแก้ไข",
		# ไม่อนุมัติแบบปิดเลย (ตกลง 2026-11-19, ใบขอซื้อ): ร่างล็อก ส่งใหม่ไม่ได้ เก็บเป็นประวัติ
		"decline": "ไม่อนุมัติ",
		"who": "ผู้อนุมัติ",
	},
	"sign": {
		"send": "ส่งลงนาม",
		"do": "ลงนาม",
		"done": "ลงนามแล้ว",
		"pending": "รอลงนาม",
		"reject": "ส่งกลับแก้ไข",
		"who": "ผู้ลงนาม",
	},
}
STATUS_LABELS = {"Pending": None, "Rejected": "ส่งกลับแก้ไข", "Declined": "ไม่อนุมัติ"}


def key_of(doctype):
	return f"consbiz_approval::{doctype}"


def settings_of(doctype):
	try:
		saved = json.loads(frappe.db.get_default(key_of(doctype)) or "{}")
	except ValueError:
		saved = {}
	out = dict(DEFAULTS[doctype])
	for field in ("roles", "proxy_roles"):
		if isinstance(saved.get(field), list):
			out[field] = saved[field]
	out["custom"] = bool(saved)
	return out


def flow_of(doc):
	"""ขั้นตอนของเอกสาร (None = ไม่มีขั้นอนุมัติ/ลงนาม)"""
	flow = FLOWS.get(doc.doctype)
	if not flow or not doc.meta.has_field("custom_approval_status"):
		return None
	if doc.doctype == "Material Request" and doc.get("material_request_type") not in MR_TYPES:
		return None
	return flow


def has_role(roles, user=None):
	user = user or frappe.session.user
	if user == "Administrator":
		return True
	return bool(set(roles) & set(frappe.get_roles(user)))


# ช่องผู้อนุมัติ/ผู้ลงนามที่ผู้ส่งเลือก (ตกลง 2026-11-19): ใบขอซื้อใช้ช่องเดิม (Signature, ชื่อ = User)
APPROVER_FIELD = {
	"Material Request": "custom_approve_by",
	"Purchase Order": "custom_approver",
	"Purchase Invoice": "custom_approver",
}


def approver_of(doc):
	field = APPROVER_FIELD.get(doc.doctype)
	return doc.get(field) if field and doc.meta.has_field(field) else None


def can_approve(doc, user=None):
	"""ปุ่มอนุมัติ/ลงนาม = เฉพาะผู้ที่ระบุในเอกสาร (และยังมี Role) ไม่ระบุ = ผู้มี Role (เอกสารเก่า/ระบบเต็ม)"""
	user = user or frappe.session.user
	named = approver_of(doc)
	if named:
		return user == named and has_role(settings_of(doc.doctype)["roles"], user)
	return has_role(settings_of(doc.doctype)["roles"], user)


def can_record(doc):
	"""ปุ่มลงนามแทน (เอกสารที่ลงนามบนกระดาษแล้ว): ผู้มี Role บันทึกแทน / ผู้ลงนาม / System Manager ที่ไม่ใช่ผู้ลงนามที่ระบุ"""
	flow = flow_of(doc)
	if not flow or flow["mode"] != "sign" or doc.docstatus != 0 or can_approve(doc):
		return False
	s = settings_of(doc.doctype)
	return has_role(s["proxy_roles"] + s["roles"] + ["System Manager"])


def approvers(doctype):
	"""ผู้ใช้ที่อนุมัติ/ลงนามได้ (Enabled, System User)"""
	roles = settings_of(doctype)["roles"]
	if not roles:
		return []
	return sorted(
		set(
			frappe.get_all(
				"Has Role",
				filters={"role": ("in", roles), "parenttype": "User"},
				pluck="parent",
			)
		)
		& set(frappe.get_all("User", filters={"enabled": 1, "user_type": "System User"}, pluck="name"))
		- {"Administrator"}
	)


def words(doc):
	flow = flow_of(doc)
	return {k: _(v) for k, v in WORDS[flow["mode"]].items()} if flow else None


# ---------------------------------------------------------------- doc_events


def declined(doc):
	return doc.get("custom_approval_status") == "Declined"


def guard_pending(doc, method=None):
	"""validate: เอกสารรออนุมัติ/ลงนามแก้ไม่ได้ (ดึงกลับก่อน) ยกเว้นคำสั่งของโมดูลนี้และตอน Submit
	ไม่อนุมัติแล้ว = ปิด แก้/ส่งไม่ได้อีก (ทำซ้ำเป็นใบใหม่แทน)"""
	if doc.is_new() or doc.docstatus != 0 or doc.flags.approval_action or not flow_of(doc):
		return
	before = doc.get_doc_before_save()
	if before and before.get("custom_approval_status") == "Declined":
		frappe.throw(_("เอกสารนี้ไม่อนุมัติแล้ว แก้ไขไม่ได้ (ทำซ้ำเป็นใบใหม่ได้)"), title=_("แก้ไขไม่ได้"))
	if doc.get("custom_approval_status") != "Pending":
		return
	before = doc.get_doc_before_save()
	if before and before.get("custom_approval_status") == "Pending":
		frappe.throw(_("เอกสาร{0}อยู่ ดึงเอกสารกลับก่อนแก้ไข").format(words(doc)["pending"]), title=_("แก้ไขไม่ได้"))


def guard_submit(doc, method=None):
	"""before_submit: ผู้ Submit (หรือผู้ลงนามที่บันทึกแทน) ต้องมี Role อนุมัติ/ลงนาม แล้วเก็บผู้ลงนาม + เวลา"""
	flow = flow_of(doc)
	if not flow:
		return
	if declined(doc):
		frappe.throw(_("เอกสารนี้ไม่อนุมัติแล้ว ยืนยันไม่ได้"), frappe.PermissionError)
	signer = doc.flags.approval_signer or frappe.session.user
	if not doc.flags.approval_signer and not can_approve(doc):
		named = approver_of(doc)
		frappe.throw(
			_("{0}เอกสารนี้ได้เฉพาะ {1}").format(words(doc)["do"], frappe.utils.get_fullname(named))
			if named
			else _("ไม่มีสิทธิ์{0}{1} ใช้ปุ่ม {2} ให้ผู้มีสิทธิ์").format(
				words(doc)["do"], _(flow["label"]), words(doc)["send"]
			),
			frappe.PermissionError,
		)
	field = APPROVER_FIELD.get(doc.doctype)
	if (
		field
		and doc.meta.has_field(field)
		and (doc.doctype != "Material Request" or frappe.db.exists("Signature", signer))
	):
		# ผู้ลงนามจริงลงช่องผู้อนุมัติ/ผู้ลงนาม (ใบขอซื้อใช้ Signature: มีเฉพาะผู้ที่มีลายเซ็น)
		doc.set(field, signer)
	doc.custom_approval_status = "Approved"
	doc.custom_signed_by = signer
	if not doc.flags.approval_signer:
		doc.custom_signed_on = now_datetime()
		doc.custom_signed_by_proxy = None


def guard_trash(doc, method=None):
	"""on_trash: ใบที่ไม่อนุมัติแล้วเก็บเป็นประวัติ ลบได้เฉพาะ System Manager"""
	if flow_of(doc) and declined(doc) and "System Manager" not in frappe.get_roles():
		frappe.throw(_("เอกสารที่ไม่อนุมัติแล้วเก็บไว้เป็นประวัติ ลบไม่ได้"), frappe.PermissionError)


def after_submit(doc, method=None):
	"""on_submit: แจ้งผู้ส่งว่าอนุมัติ/ลงนามแล้ว ทุกทาง (ปุ่มในหน้า, ยืนยันหลายใบ, ระบบเต็ม) บันทึกแทนแจ้งเองใน record_signing"""
	if not flow_of(doc) or doc.flags.approval_signer:
		return
	sender = doc.get("custom_sent_by")
	if sender:
		notify(
			[sender],
			doc,
			_("{0} {1}: {2}").format(frappe.utils.get_fullname(), words(doc)["done"], doc_title(doc)),
		)


# ---------------------------------------------------------------- ข้อมูลหน้าดู


def info(doc):
	"""ขั้นอนุมัติ/ลงนามของเอกสารสำหรับหน้าดู (site_docs.get_doc) ไม่มีขั้นนี้ = None"""
	flow = flow_of(doc)
	if not flow:
		return None
	w = words(doc)
	status = doc.get("custom_approval_status") or ""
	draft = doc.docstatus == 0
	pending = draft and status == "Pending"
	closed = draft and status == "Declined"
	user = frappe.session.user
	writer = draft and frappe.has_permission(doc.doctype, "write", doc)
	approver = draft and not closed and can_approve(doc) and frappe.has_permission(doc.doctype, "read", doc)
	named = approver_of(doc)

	def fullname(u):
		return frappe.utils.get_fullname(u) if u else None

	return {
		"mode": flow["mode"],
		"words": w,
		"status": status if draft else ("Approved" if doc.docstatus == 1 else status),
		"pending": pending,
		"sent_by": doc.get("custom_sent_by"),
		"sent_by_name": fullname(doc.get("custom_sent_by")),
		"sent_on": doc.get("custom_sent_on"),
		"approver": named,
		"approver_name": person_name(doc.doctype, named),
		"review_note": doc.get("custom_review_note"),
		"signed_by_name": fullname(doc.get("custom_signed_by")),
		"signed_on": doc.get("custom_signed_on"),
		"proxy_name": fullname(doc.get("custom_signed_by_proxy")),
		"proof": doc.get("custom_signed_proof"),
		"closed": closed,
		"can_send": bool(writer and not pending and not closed),
		"can_withdraw": bool(pending and (doc.get("custom_sent_by") == user or doc.owner == user)),
		"can_approve": bool(approver),
		"can_reject": bool(pending and approver),
		"can_decline": bool(pending and approver and "decline" in w),
		"can_record": bool(draft and not closed and can_record(doc)),
	}


def person_name(doctype, user):
	if not user:
		return None
	if doctype == "Material Request":
		return frappe.db.get_value("Signature", user, "full_name") or frappe.utils.get_fullname(user)
	return frappe.utils.get_fullname(user)


def status_label(row_status, docstatus, approval_status, doctype):
	"""ป้ายสถานะของร่างที่อยู่ในขั้นอนุมัติ/ลงนาม (รายการ/หน้าดู) ไม่ใช่ = None"""
	if cint(docstatus) != 0 or doctype not in FLOWS:
		return None
	if approval_status == "Pending":
		return _(WORDS[FLOWS[doctype]["mode"]]["pending"]), "amber"
	if approval_status == "Rejected":
		return _(STATUS_LABELS["Rejected"]), "rose"
	if approval_status == "Declined":
		return _(STATUS_LABELS["Declined"]), "gray"
	return None


# ---------------------------------------------------------------- คำสั่ง


def load(kind, name):
	from consbiz.site_docs import config_of

	doc = frappe.get_doc(config_of(kind)["doctype"], name)
	doc.check_permission("read")
	if not flow_of(doc):
		frappe.throw(_("เอกสารนี้ไม่มีขั้นอนุมัติ/ลงนาม"))
	if doc.docstatus != 0:
		frappe.throw(_("เอกสารนี้ไม่ใช่ร่างแล้ว"))
	if declined(doc):
		frappe.throw(_("เอกสารนี้ไม่อนุมัติแล้ว"))
	return doc


def save_state(doc, **values):
	doc.update(values)
	doc.flags.approval_action = True
	doc.flags.ignore_permissions = True
	doc.save()


def notify(users, doc, subject):
	from consbiz.self_advance import notify_users

	notify_users(users, doc, subject)


def doc_title(doc):
	party = doc.get("supplier_name") or doc.get("title") or ""
	return f"{doc.name} {party}".strip()


def result(kind, name):
	from consbiz.site_docs import get_doc

	return get_doc(kind, name)


@frappe.whitelist(methods=["POST"])
def send(kind, name):
	"""ส่งอนุมัติ/ส่งลงนาม: ร่างที่บันทึกแล้ว ผู้มีสิทธิ์แก้ไขเอกสาร → รอ (แก้ไม่ได้) + แจ้งผู้อนุมัติ/ผู้ลงนาม"""
	doc = load(kind, name)
	doc.check_permission("write")
	if doc.custom_approval_status == "Pending":
		frappe.throw(_("ส่งไปแล้ว"))
	w = words(doc)
	named = approver_of(doc)
	if not named:
		frappe.throw(
			_("เลือก{0}ในเอกสารก่อน{1} (กดแก้ไข)").format(w["who"], w["send"]),
			title=_("ยังไม่มี{0}").format(w["who"]),
		)
	if named not in approvers(doc.doctype):
		frappe.throw(
			_("{0} ไม่มีสิทธิ์{1} เลือก{2}คนอื่น").format(person_name(doc.doctype, named), w["do"], w["who"])
		)
	save_state(
		doc,
		custom_approval_status="Pending",
		custom_sent_by=frappe.session.user,
		custom_sent_on=now_datetime(),
		custom_review_note=None,
	)
	doc.add_comment("Info", _("{0} {1}").format(frappe.utils.get_fullname(), w["send"]))
	notify([named], doc, _("{0} {1}: {2}").format(frappe.utils.get_fullname(), w["send"], doc_title(doc)))
	return result(kind, name)


@frappe.whitelist(methods=["POST"])
def withdraw(kind, name):
	"""ดึงกลับ: ผู้ส่ง (หรือผู้สร้าง) ระหว่างรอ → ร่าง แก้ไขได้อีก"""
	doc = load(kind, name)
	if doc.custom_approval_status != "Pending":
		frappe.throw(_("เอกสารนี้ไม่ได้รออยู่"))
	if frappe.session.user not in (doc.custom_sent_by, doc.owner):
		frappe.throw(_("ดึงกลับได้เฉพาะผู้ส่ง"), frappe.PermissionError)
	save_state(doc, custom_approval_status="", custom_sent_by=None, custom_sent_on=None)
	doc.add_comment("Info", _("{0} ดึงเอกสารกลับ").format(frappe.utils.get_fullname()))
	return result(kind, name)


@frappe.whitelist(methods=["POST"])
def reject(kind, name, reason=None):
	"""ไม่อนุมัติ/ส่งกลับแก้ไข: ผู้อนุมัติ/ผู้ลงนาม ระหว่างรอ + เหตุผล → ร่าง (แก้ได้) แจ้งผู้ส่ง"""
	doc = load(kind, name)
	if not can_approve(doc):
		frappe.throw(_("ไม่มีสิทธิ์{0}").format(words(doc)["reject"]), frappe.PermissionError)
	if doc.custom_approval_status != "Pending":
		frappe.throw(_("เอกสารนี้ไม่ได้รออยู่"))
	reason = (reason or "").strip()
	if not reason:
		frappe.throw(_("ระบุเหตุผล"))
	w = words(doc)
	sender = doc.custom_sent_by or doc.owner
	save_state(doc, custom_approval_status="Rejected", custom_review_note=reason)
	doc.add_comment("Info", _("{0} {1}: {2}").format(frappe.utils.get_fullname(), w["reject"], reason))
	notify([sender], doc, _("{0} {1}: {2}").format(doc_title(doc), w["reject"], reason))
	return result(kind, name)


@frappe.whitelist(methods=["POST"])
def decline(kind, name, reason=None):
	"""ไม่อนุมัติ (ปิดเลย, ใบขอซื้อ): ผู้อนุมัติ ระหว่างรอ + เหตุผล → ร่างล็อก สถานะไม่อนุมัติ แจ้งผู้ส่ง
	แถวแผนวัสดุที่ผูกใบนี้ปลดออก (ขอซื้อใหม่ได้) ยอดขอซื้อของแผนไม่นับใบนี้"""
	doc = load(kind, name)
	w = words(doc)
	if "decline" not in w:
		frappe.throw(_("เอกสารนี้ไม่มีขั้นไม่อนุมัติ ใช้ {0}").format(w["reject"]))
	if not can_approve(doc):
		frappe.throw(_("ไม่มีสิทธิ์{0}").format(w["decline"]), frappe.PermissionError)
	if doc.custom_approval_status != "Pending":
		frappe.throw(_("เอกสารนี้ไม่ได้รออยู่"))
	reason = (reason or "").strip()
	if not reason:
		frappe.throw(_("ระบุเหตุผล"))
	sender = doc.custom_sent_by or doc.owner
	save_state(doc, custom_approval_status="Declined", custom_review_note=reason)
	if doc.doctype == "Material Request":
		frappe.db.set_value(
			"Construction Material Plan Item", {"material_request": doc.name}, "material_request", None
		)
	doc.add_comment("Info", _("{0} {1}: {2}").format(frappe.utils.get_fullname(), w["decline"], reason))
	notify([sender], doc, _("{0} {1}: {2}").format(doc_title(doc), w["decline"], reason))
	return result(kind, name)


@frappe.whitelist(methods=["POST"])
def approve(kind, name):
	"""อนุมัติ/ลงนาม = Submit (ตรวจ Role ใน guard_submit) แจ้งผู้ส่ง"""
	doc = load(kind, name)
	doc.flags.approval_action = True
	doc.submit()  # แจ้งผู้ส่งใน after_submit
	return result(kind, name)


def signer_options(doctype):
	return [{"value": u, "label": frappe.utils.get_fullname(u)} for u in approvers(doctype)]


@frappe.whitelist()
def get_signers(kind, name):
	"""ผู้ลงนามที่เลือกได้ในหน้าบันทึกการลงนามแทน"""
	doc = load(kind, name)
	if not can_record(doc):
		frappe.throw(_("ไม่มีสิทธิ์บันทึกการลงนามแทน"), frappe.PermissionError)
	# ผู้ลงนามที่ระบุในเอกสารขึ้นก่อน (ค่าเริ่มต้นในหน้าบันทึก)
	options = signer_options(doc.doctype)
	named = approver_of(doc)
	options.sort(key=lambda o: o["value"] != named)
	return {"options": options, "default": named if any(o["value"] == named for o in options) else None}


@frappe.whitelist()
def search_approvers(kind, txt=None):
	"""ผู้ลงนามที่เลือกได้ในฟอร์ม (ผู้มี Role ลงนามของเอกสารชนิดนี้)"""
	from consbiz.site_docs import config_of

	doctype = config_of(kind)["doctype"]
	if doctype not in FLOWS:
		frappe.throw(_("เอกสารนี้ไม่มีขั้นอนุมัติ/ลงนาม"))
	frappe.has_permission(doctype, "read", throw=True)
	txt = (txt or "").strip().lower()
	options = signer_options(doctype)
	if doctype == "Material Request":
		# ผู้อนุมัติใบขอซื้อเป็นช่อง Signature (ชื่อ = User): เฉพาะผู้มี Role ที่มีลายเซ็นในระบบ
		names = dict(
			frappe.get_all(
				"Signature",
				filters={"name": ("in", [o["value"] for o in options] or [""])},
				fields=["name", "full_name"],
				as_list=True,
			)
		)
		options = [
			{"value": o["value"], "label": names[o["value"]] or o["label"]}
			for o in options
			if o["value"] in names
		]
	return [o for o in options if not txt or txt in o["label"].lower() or txt in o["value"].lower()]


@frappe.whitelist(methods=["POST"])
def record_signing(kind, name, signer, signed_on, proof, note=None):
	"""บันทึกการลงนามแทน (PO/PI): ผู้ลงนามเซ็นบนกระดาษแล้ว เจ้าหน้าที่ (proxy_roles) บันทึกให้
	signer ต้องเป็นผู้มีสิทธิ์ลงนาม, proof = ไฟล์ที่แนบกับเอกสารนี้แล้ว (สแกน/รูปเอกสารที่เซ็น)"""
	doc = load(kind, name)
	if not can_record(doc):
		frappe.throw(_("ไม่มีสิทธิ์บันทึกการลงนามแทน"), frappe.PermissionError)
	if signer not in approvers(doc.doctype):
		frappe.throw(
			_("{0} ไม่มีสิทธิ์ลงนาม{1}").format(frappe.utils.get_fullname(signer), _(FLOWS[doc.doctype]["label"]))
		)
	if not proof or not frappe.db.exists(
		"File", {"file_url": proof, "attached_to_doctype": doc.doctype, "attached_to_name": doc.name}
	):
		frappe.throw(_("แนบไฟล์เอกสารที่ลงนามแล้ว"))
	when = get_datetime(signed_on) if signed_on else None
	if not when:
		frappe.throw(_("ระบุวันที่ลงนาม"))
	if getdate(when) > getdate():
		frappe.throw(_("วันที่ลงนามต้องไม่เกินวันนี้"))
	sender = doc.custom_sent_by
	doc.update(
		{
			"custom_signed_on": when,
			"custom_signed_by_proxy": frappe.session.user,
			"custom_signed_proof": proof,
		}
	)
	doc.flags.approval_action = True
	doc.flags.approval_signer = signer
	# ผู้บันทึกแทนอาจไม่มีสิทธิ์ Submit เอง (สิทธิ์มาจาก Role บันทึกแทนที่ตั้งไว้)
	doc.flags.ignore_permissions = True
	doc.submit()
	note = (note or "").strip()
	doc.add_comment(
		"Info",
		_("{0} บันทึกการลงนามแทน {1} (ลงนามวันที่ {2})").format(
			frappe.utils.get_fullname(),
			frappe.utils.get_fullname(signer),
			frappe.format(getdate(when), "Date"),
		)
		+ (f": {note}" if note else ""),
	)
	notify(
		[signer, sender],
		doc,
		_("{0} บันทึกการลงนามแทน {1}: {2}").format(
			frappe.utils.get_fullname(), frappe.utils.get_fullname(signer), doc_title(doc)
		),
	)
	return result(kind, name)


# ---------------------------------------------------------------- หน้าตั้งค่า (ตั้งค่าจัดซื้อ > การอนุมัติ/ลงนาม)


def role_options():
	skip = {"Administrator", "Guest", "All", "Desk User"}
	return [
		r
		for r in frappe.get_all(
			"Role", filters={"disabled": 0, "desk_access": 1}, pluck="name", order_by="name"
		)
		if r not in skip
	]


@frappe.whitelist()
def get_settings():
	docs = []
	for doctype, flow in FLOWS.items():
		if not frappe.has_permission(doctype, "read"):
			continue
		s = settings_of(doctype)
		docs.append(
			{
				"doctype": doctype,
				"label": _(flow["label"]),
				"mode": flow["mode"],
				"words": {k: _(v) for k, v in WORDS[flow["mode"]].items()},
				"roles": s["roles"],
				"proxy_roles": s["proxy_roles"],
				"custom": s["custom"],
				"default_roles": DEFAULTS[doctype]["roles"],
				"default_proxy_roles": DEFAULTS[doctype]["proxy_roles"],
				"people": [o["label"] for o in signer_options(doctype)],
			}
		)
	return {"docs": docs, "roles": role_options(), "can_edit": has_role(EDIT_ROLES)}


@frappe.whitelist(methods=["POST"])
def set_roles(doctype, roles=None, proxy_roles=None, reset=0):
	if doctype not in FLOWS:
		frappe.throw(_("ไม่รองรับเอกสารนี้"))
	if not has_role(EDIT_ROLES):
		frappe.throw(_("ไม่มีสิทธิ์ตั้งค่าการอนุมัติ"), frappe.PermissionError)
	if cint(reset):
		frappe.db.set_default(key_of(doctype), "")
		return get_settings()
	allowed = set(role_options())

	def parse(v):
		return [r for r in (frappe.parse_json(v) if isinstance(v, str) else v or []) if r in allowed]

	roles = parse(roles)
	if not roles:
		frappe.throw(_("เลือกอย่างน้อย 1 Role"))
	value = {"roles": roles, "proxy_roles": parse(proxy_roles) if FLOWS[doctype]["mode"] == "sign" else []}
	frappe.db.set_default(key_of(doctype), json.dumps(value))
	return get_settings()


# ---------------------------------------------------------------- โมดูลอนุมัติรวม (/conserp/approve, consbiz/approvals.py)

INBOX_KINDS = {"mr": "Material Request", "po": "Purchase Order", "pi": "Purchase Invoice"}
INBOX_FIELDS = {
	"Material Request": [
		"title",
		"custom_grand_total as amount",
		"transaction_date as date",
		"custom_project as project",
	],
	"Purchase Order": [
		"supplier_name as party",
		"grand_total as amount",
		"transaction_date as date",
		"project",
	],
	"Purchase Invoice": [
		"supplier_name as party",
		"grand_total as amount",
		"posting_date as date",
		"project",
	],
}


def can_inbox(kind):
	"""เห็นชนิดนี้ในโมดูลอนุมัติ = มี Role อนุมัติ/ลงนาม + อ่านเอกสารได้"""
	doctype = INBOX_KINDS[kind]
	return bool(
		frappe.get_meta(doctype).has_field("custom_approval_status")
		and frappe.session.user != "Guest"
		and has_role(settings_of(doctype)["roles"])
		and frappe.has_permission(doctype, "read")
	)


def inbox_rows(kind, pending=True, since=None):
	"""รอ = รอผู้ใช้คนนี้อนุมัติ/ลงนาม (ระบุชื่อไว้ หรือไม่ระบุแต่มี Role) / พิจารณาแล้ว = ที่ผู้ใช้ลงนาม/ส่งกลับ ตั้งแต่ since"""
	doctype = INBOX_KINDS[kind]
	if not can_inbox(kind):
		return []
	user = frappe.session.user
	field = APPROVER_FIELD[doctype]
	base = {"material_request_type": ("in", MR_TYPES)} if doctype == "Material Request" else {}
	if pending:
		filters = {**base, "docstatus": 0, "custom_approval_status": "Pending"}
		names = set(
			frappe.get_list(doctype, filters={**filters, field: user}, pluck="name", limit_page_length=200)
		)
		# เอกสารเก่าที่ไม่ระบุผู้ลงนาม: ผู้มี Role ทุกคน
		names |= set(
			frappe.get_list(
				doctype, filters={**filters, field: ("is", "not set")}, pluck="name", limit_page_length=200
			)
		)
		filters = {"name": ("in", list(names) or [""])}
	else:
		filters = {
			**base,
			"modified": (">=", since),
			field: user,
			"custom_approval_status": ("in", ["Approved", "Rejected", "Declined"]),
		}
	rows = frappe.get_list(
		doctype,
		filters=filters,
		fields=[
			"name",
			"docstatus",
			"custom_approval_status as approval",
			"custom_sent_by as sent_by",
			"custom_sent_on as sent_on",
			"custom_review_note as review_note",
			"custom_signed_on as signed_on",
			*INBOX_FIELDS[doctype],
		],
		order_by="custom_sent_on asc" if pending else "modified desc",
		limit_page_length=200,
	)
	w = WORDS[FLOWS[doctype]["mode"]]
	for row in rows:
		row.kind = kind
		row.employee = row.sent_by
		row.employee_name = frappe.utils.get_fullname(row.sent_by) if row.sent_by else ""
		row.action = _(w["do"])
		if not pending:
			row.result = (
				_(w["done"])
				if row.docstatus == 1
				else _(w["decline"])
				if row.approval == "Declined"
				else _(w["reject"])
			)
	return rows
