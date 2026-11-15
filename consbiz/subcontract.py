# Copyright (c) 2026, Siricons and contributors
# For license information, please see license.txt

"""สัญญาจ้างเหมาช่วง (Subcontract Agreement) และใบเบิกงวด ผรม. (Subcontract Claim)

สัญญา: รายการงาน (ปริมาณ x ราคา) + เงื่อนไขเงิน (เงินประกัน/เพดาน, หัก ณ ที่จ่าย, เงินล่วงหน้า/หักคืน, ค่าปรับ)
  ปริมาณจ้างรวมทุกสัญญาต่อ WBS ต้องไม่เกินแผนงาน (`check_plan_quantity`) เกินต้องทำ VO ฝั่งผู้ว่าจ้างก่อน
  งานเพิ่ม = ใบงานเพิ่ม ผรม. (consbiz/subcontract_variation.py) เป็นรายการแนบท้าย (แถวที่มี `variation`) แยกจากงานหลัก
  งานหลักไม่เปลี่ยน (% งวดคงเดิม) แนบท้ายเบิกตามปริมาณจริงเสมอ ไม่มีงานลด: งานจบต่ำกว่าสัญญาหรือ ผรม. ไม่ทำต่อ = ปิดสัญญา (`close_agreement`)
  วิธีเบิก Measured = กรอกปริมาณงวดนี้รายแถว, Milestone = เลือกงวด แล้วระบบเบิก % ของงวดจากทุกแถว
  ทั้งสองวิธีจึงเป็น "ปริมาณต่อแถว" เหมือนกัน (PO/PI ผูกรายแถวได้ ยอดผูกพันของหน้าการเงินถูกต้อง)
  Submit แล้วกดปุ่มสร้าง PO (`make_purchase_order`) และจ่ายเงินล่วงหน้า (`make_advance_payment` = Payment Entry อ้าง PO)
ใบเบิก: ร่างโดยวิศวกรหน้างานหรือ ผรม. → Submit = อนุมัติ → ปุ่มสร้าง PI (`make_purchase_invoice`)
  PI ผูก PO รายแถว, หัก ณ ที่จ่าย/เงินประกันลงตาราง custom_payment_entry_deduction (ระบบเดิม: deductions.py,
  Submit PI แล้ว retention.py สร้าง Retention Payable ให้), เงินล่วงหน้าหักผ่านตาราง advances ของ PI, ค่าปรับเป็นแถวหักบัญชีรายได้ค่าปรับ
ยอดสรุปของสัญญา (เบิกแล้ว, เงินประกันที่หักไว้, หักคืนเงินล่วงหน้า, ค่าปรับ) คำนวณใหม่จากใบเบิกที่ Submit ทุกครั้ง (`refresh_agreement`)
ยอดในใบเบิกเป็นยอดก่อน VAT (VAT เป็นของ PI ตามแม่แบบภาษีของ ผรม.)"""

import json
from contextlib import contextmanager

import frappe
from frappe import _
from frappe.utils import add_days, cint, flt, getdate, nowdate

QTY_TOLERANCE = 0.0001
PURCHASE_ROLES = ("Purchase Manager", "Purchase User")


def money(value):
	return flt(value, 2)


@contextmanager
def as_system():
	"""ทำงานต่อจากการอนุมัติในนามระบบ (Administrator) เช่น แก้/ปิด PO ตามสัญญา ผู้อนุมัติไม่ต้องมีสิทธิ์แก้ PO
	ตรวจสิทธิ์ของผู้ใช้ก่อนเรียกเสมอ แล้วคืน session เดิมครบ (frappe.set_user ล้าง sid/form_dict ของคำขอ)"""
	local = frappe.local
	saved = {
		key: getattr(local, key, None)
		for key in ("cache", "form_dict", "role_permissions", "new_doc_templates", "user_perms")
	}
	session = {key: local.session.get(key) for key in ("user", "sid", "data")}
	frappe.set_user("Administrator")
	try:
		yield
	finally:
		local.session.update(session)
		for key, value in saved.items():
			setattr(local, key, value)


def require_settings(company, *fields):
	from consbiz.consbiz.doctype.labour_settings.labour_settings import require, settings_of

	settings = settings_of(company)
	require(settings, *fields)
	return settings


# ---------------------------------------------------------------- สัญญา


def set_company(doc):
	"""บริษัทตามโครงการเสมอ: เรียกตอน before_insert ด้วย เพราะเลขที่ (.ABBR.) ตั้งก่อน validate
	และค่าตั้งต้นของผู้ใช้เติมบริษัทก่อน fetch_if_empty จึงอาจเป็นบริษัทอื่น"""
	if doc.get("project"):
		doc.company = frappe.db.get_value("Project", doc.project, "company") or doc.company


def validate_agreement(doc):
	set_company(doc)
	if doc.project:
		doc.construction_management = frappe.db.get_value(
			"Construction Management", {"project": doc.project, "docstatus": ("<", 2)}, "name"
		)
	if doc.start_date and doc.end_date and getdate(doc.end_date) < getdate(doc.start_date):
		frappe.throw(_("วันสิ้นสุดสัญญาต้องไม่ก่อนวันเริ่มงาน"))
	if not doc.items:
		frappe.throw(_("สัญญาต้องมีรายการงานอย่างน้อย 1 แถว"))
	for row in doc.items:
		if flt(row.qty) <= 0:
			frappe.throw(_("แถว {0}: ปริมาณต้องมากกว่า 0").format(row.idx))
		if flt(row.rate) < 0:
			frappe.throw(_("แถว {0}: ราคาต่อหน่วยติดลบไม่ได้").format(row.idx))
		row.amount = money(flt(row.qty) * flt(row.rate))
	doc.total_amount = money(sum(flt(row.amount) for row in doc.items))
	if doc.total_amount <= 0:
		frappe.throw(_("มูลค่าสัญญาต้องมากกว่า 0"))
	for field, label in (
		("retention_percent", _("เงินประกันผลงาน")),
		("retention_cap_percent", _("เพดานเงินประกัน")),
		("wht_percent", _("หัก ณ ที่จ่าย")),
		("advance_percent", _("เงินล่วงหน้า")),
		("advance_recovery_percent", _("หักคืนเงินล่วงหน้า")),
	):
		if not 0 <= flt(doc.get(field)) <= 100:
			frappe.throw(_("{0} ต้องอยู่ระหว่าง 0 ถึง 100%").format(label))
	doc.advance_amount = money(doc.total_amount * flt(doc.advance_percent) / 100)
	if doc.advance_amount and not flt(doc.advance_recovery_percent):
		frappe.throw(_("มีเงินล่วงหน้า ต้องกำหนด % หักคืนต่องวด"))
	if doc.billing_method == "Milestone":
		if not doc.milestones:
			frappe.throw(_("เบิกตามงวดงาน ต้องมีงวดงานอย่างน้อย 1 งวด"))
		total_percent = sum(flt(m.percent) for m in doc.milestones)
		if abs(total_percent - 100) > 0.01:
			frappe.throw(_("% ของงวดงานรวมกันต้องเท่ากับ 100% (ตอนนี้ {0}%)").format(flt(total_percent, 2)))
		main = money(sum(flt(r.amount) for r in doc.items if not r.get("variation")))
		for m in doc.milestones:
			m.amount = money(main * flt(m.percent) / 100)
	if doc.docstatus == 0:
		doc.status = "Draft"
	check_plan_quantity(doc.construction_management, doc.items, exclude=doc.name)


def on_submit_agreement(doc):
	doc.db_set(
		{"status": "Active", "original_amount": doc.total_amount, "variation_amount": 0, "revision": 0}
	)


def plan_pools(construction_management):
	"""ปริมาณในแผนต่องาน: แถวงานเพิ่ม (VO) ของงานเดิม (source_wbs) รวมกองเดียวกับงานเดิม
	คืน (pools, key_of) pools[WBS งานเดิม] = ปริมาณรวม/หน่วย/ชื่อ, key_of[WBS ใดก็ได้] = WBS งานเดิม"""
	pools, key_of = {}, {}
	for t in frappe.get_all(
		"Construction Management Task",
		filters={"parent": construction_management, "parenttype": "Construction Management", "is_group": 0},
		fields=["wbs", "item_name", "uom", "quantity", "is_variation", "source_wbs"],
		order_by="idx",
	):
		wbs = (t.wbs or "").strip()
		if not wbs:
			continue
		key = (t.source_wbs or "").strip() if t.is_variation and t.source_wbs else wbs
		key_of[wbs] = key
		pool = pools.setdefault(key, {"qty": 0, "uom": None, "item_name": None, "lump": False})
		if key == wbs:
			pool.update(uom=t.uom, item_name=t.item_name, lump=flt(t.quantity) <= 0)
		pool["qty"] += flt(t.quantity)
	return pools, key_of


def check_plan_quantity(construction_management, rows, exclude=None):
	"""ปริมาณจ้างรวมต่องานในแผน (สัญญานี้ + สัญญาอื่นที่ Submit แล้ว, สัญญาที่ปิดแล้วนับเฉพาะที่เบิกจริง)
	ต้องไม่เกินปริมาณในแผนงาน (รวม VO ผู้ว่าจ้าง) ตรวจเฉพาะแถวที่ระบุ WBS และหน่วยตรงกับแผน งานเหมา (ไม่มีปริมาณ) ไม่ตรวจ
	rows = แถวของสัญญานี้ตามปริมาณที่จะเป็น (มี wbs, uom, qty)"""
	if not construction_management:
		return
	pools, key_of = plan_pools(construction_management)

	def pool_key(row):
		key = key_of.get((row.get("wbs") or "").strip())
		pool = pools.get(key)
		if not pool or pool["lump"] or not pool["uom"] or row.get("uom") != pool["uom"]:
			return None
		return key

	mine = {}
	for row in rows:
		key = pool_key(row)
		if key:
			mine[key] = mine.get(key, 0) + flt(row.get("qty"))
	if not mine:
		return
	agreements = {
		a.name: a.status
		for a in frappe.get_all(
			"Subcontract Agreement",
			filters={
				"construction_management": construction_management,
				"docstatus": 1,
				"name": ("!=", exclude or ""),
			},
			fields=["name", "status"],
		)
	}
	others = {}
	if agreements:
		for row in frappe.get_all(
			"Subcontract Agreement Item",
			filters={"parent": ("in", list(agreements)), "parenttype": "Subcontract Agreement"},
			fields=["parent", "wbs", "uom", "qty", "claimed_qty"],
		):
			key = pool_key(row)
			if key in mine:
				used = row.claimed_qty if agreements[row.parent] == "Closed" else row.qty
				others[key] = others.get(key, 0) + flt(used)
	for key, qty in mine.items():
		pool, other = pools[key], others.get(key, 0)
		if qty + other > pool["qty"] + QTY_TOLERANCE:
			frappe.throw(
				_(
					"งาน {0} {1}: จ้างรวม {2:g} {3} เกินปริมาณในแผนงาน {4:g} (สัญญาอื่น {5:g}) "
					"ต้องทำงานเพิ่ม (VO) ฝั่งผู้ว่าจ้างก่อน"
				).format(
					key,
					pool["item_name"] or "",
					flt(qty + other, 4),
					pool["uom"],
					flt(pool["qty"], 4),
					flt(other, 4),
				),
				title=_("เกินปริมาณในแผนงาน"),
			)


def before_cancel_agreement(doc):
	if doc.purchase_order and frappe.db.get_value("Purchase Order", doc.purchase_order, "docstatus") == 1:
		frappe.throw(_("ยกเลิกใบสั่งซื้อ {0} ก่อนยกเลิกสัญญา").format(doc.purchase_order))


def submitted_claims(agreement, exclude=None):
	filters = {"subcontract_agreement": agreement, "docstatus": 1}
	if exclude:
		filters["name"] = ("!=", exclude)
	return frappe.get_all(
		"Subcontract Claim",
		filters=filters,
		fields=[
			"name",
			"milestone",
			"gross_amount",
			"retention_amount",
			"advance_recovery",
			"penalty_amount",
		],
	)


def claimed_qty_by_row(agreement, exclude=None):
	claims = [c.name for c in submitted_claims(agreement, exclude)]
	out = {}
	if not claims:
		return out
	for row in frappe.get_all(
		"Subcontract Claim Item",
		filters={"parent": ("in", claims)},
		fields=["agreement_item", "qty", "amount"],
	):
		qty, amount = out.get(row.agreement_item, (0, 0))
		out[row.agreement_item] = (qty + flt(row.qty), amount + flt(row.amount))
	return out


def refresh_agreement(name):
	"""ยอดเบิกของสัญญา คำนวณใหม่จากใบเบิกที่ Submit ทั้งหมด"""
	doc = frappe.get_doc("Subcontract Agreement", name)
	by_row = claimed_qty_by_row(name)
	for row in doc.items:
		qty, amount = by_row.get(row.name, (0, 0))
		row.db_set({"claimed_qty": flt(qty, 6), "claimed_amount": money(amount)}, update_modified=False)
	claims = submitted_claims(name)
	used = {c.milestone: c.name for c in claims if c.milestone}
	for m in doc.milestones:
		m.db_set("subcontract_claim", used.get(m.name), update_modified=False)
	claimed = money(sum(flt(c.gross_amount) for c in claims))
	values = {
		"claimed_amount": claimed,
		"progress_percent": flt(claimed / doc.total_amount * 100, 2) if doc.total_amount else 0,
		"retention_held": money(sum(flt(c.retention_amount) for c in claims)),
		"advance_recovered": money(sum(flt(c.advance_recovery) for c in claims)),
		"penalty_total": money(sum(flt(c.penalty_amount) for c in claims)),
	}
	if doc.docstatus == 1 and doc.status != "Closed":
		values["status"] = "Completed" if claimed >= doc.total_amount - 0.005 else "Active"
	doc.db_set(values)


def drafts_of(agreement):
	"""ใบเบิก/ใบงานเพิ่มที่ยังเป็นร่างของสัญญา"""
	return [
		name
		for doctype in ("Subcontract Claim", "Subcontract Variation")
		for name in frappe.get_all(
			doctype, filters={"subcontract_agreement": agreement, "docstatus": 0}, pluck="name"
		)
	]


def set_po_closed(doc, closed):
	"""ปิด/เปิด PO ตามสัญญา (ERPNext Close / Re-open) ในนามระบบ ผู้ปิดสัญญาไม่ต้องมีสิทธิ์ PO แล้วแจ้งฝ่ายจัดซื้อ"""
	from erpnext.buying.doctype.purchase_order.purchase_order import close_or_unclose_purchase_orders

	if not doc.purchase_order:
		return
	po = frappe.db.get_value("Purchase Order", doc.purchase_order, ["docstatus", "status"], as_dict=True)
	if not po or po.docstatus != 1 or (closed and po.status in ("Closed", "Completed")):
		return
	if not closed and po.status != "Closed":
		return
	user = frappe.session.user
	with as_system():
		close_or_unclose_purchase_orders(json.dumps([doc.purchase_order]), "Closed" if closed else "Draft")
	subject = (_("ปิดใบสั่งซื้อ {0} ตามการปิดสัญญา {1}") if closed else _("เปิดใบสั่งซื้อ {0} อีกครั้งตามสัญญา {1}")).format(
		doc.purchase_order, doc.name
	)
	add_po_comment(doc.purchase_order, subject, user)
	notify_purchasing(doc.company, "Purchase Order", doc.purchase_order, subject)


def add_po_comment(po_name, text, user):
	frappe.get_doc("Purchase Order", po_name).add_comment(
		"Info", _("{0} (โดย {1})").format(text, frappe.utils.get_fullname(user))
	)


def purchase_users(company):
	"""ผู้ใช้ฝ่ายจัดซื้อทุกคน (Role ใน PURCHASE_ROLES) ที่เห็นบริษัทนี้ (มี User Permission ของ Company = ต้องมีบริษัทนี้)"""
	users = set(
		frappe.get_all(
			"Has Role",
			filters={"role": ("in", PURCHASE_ROLES), "parenttype": "User"},
			pluck="parent",
		)
	)
	users = set(
		frappe.get_all(
			"User",
			filters={"name": ("in", list(users)), "enabled": 1, "user_type": "System User"},
			pluck="name",
		)
	) - {"Administrator", "Guest"}
	limited = {}
	for row in frappe.get_all(
		"User Permission",
		filters={"allow": "Company", "user": ("in", list(users))},
		fields=["user", "for_value"],
	):
		limited.setdefault(row.user, set()).add(row.for_value)
	return sorted(u for u in users if u not in limited or company in limited[u])


def notify_purchasing(company, doctype, name, subject):
	from frappe.desk.doctype.notification_log.notification_log import enqueue_create_notification

	users = [u for u in purchase_users(company) if u != frappe.session.user]
	if users:
		enqueue_create_notification(
			users,
			{
				"type": "Alert",
				"document_type": doctype,
				"document_name": name,
				"subject": subject,
				"from_user": frappe.session.user,
			},
		)


@frappe.whitelist(methods=["POST"])
def mark_po_sent(name):
	"""ฝ่ายจัดซื้อส่ง PO ฉบับแก้ไขให้ผู้รับเหมาแล้ว (ใครในฝ่ายก็กดได้ ไม่ผูกคนสร้าง PO)"""
	po = frappe.get_doc("Purchase Order", name)
	if not po.has_permission("write") and not set(PURCHASE_ROLES) & set(frappe.get_roles()):
		frappe.throw(_("เฉพาะฝ่ายจัดซื้อ"), frappe.PermissionError)
	if not cint(po.get("custom_revision_pending")):
		frappe.throw(_("ใบสั่งซื้อนี้ไม่มีฉบับแก้ไขที่รอส่ง"))
	po.db_set(
		{
			"custom_revision_pending": 0,
			"custom_revision_sent_by": frappe.session.user,
			"custom_revision_sent_on": frappe.utils.now_datetime(),
		}
	)
	po.add_comment("Info", _("ส่งใบสั่งซื้อ Rev.{0} ให้ผู้รับเหมาแล้ว").format(cint(po.get("custom_revision"))))


@frappe.whitelist(methods=["POST"])
def close_agreement(name, reason=None):
	"""ปิดสัญญา: งานจบต่ำกว่าสัญญาหรือ ผรม. ไม่ทำต่อ (ไม่ต้องทำงานลด) สถานะ Closed + ปิด PO
	หลังปิดเบิก/ทำงานเพิ่มไม่ได้ การตรวจปริมาณแผนงานนับเฉพาะที่เบิกจริง ปริมาณที่เหลือคืนให้งานนั้น"""
	doc = frappe.get_doc("Subcontract Agreement", name)
	doc.check_permission("submit")
	if doc.docstatus != 1 or doc.status not in ("Active", "Completed"):
		frappe.throw(_("ปิดได้เฉพาะสัญญาที่ดำเนินการอยู่"))
	if not (reason or "").strip():
		frappe.throw(_("กรอกเหตุผลที่ปิดสัญญา"))
	drafts = drafts_of(name)
	if drafts:
		frappe.throw(_("มีเอกสารร่างค้างอยู่ ลบหรืออนุมัติก่อนปิดสัญญา: {0}").format(", ".join(drafts)))
	if doc.purchase_order and frappe.db.get_value("Purchase Order", doc.purchase_order, "docstatus") == 0:
		frappe.throw(_("ใบสั่งซื้อ {0} ยังเป็นร่าง ลบหรือ Submit ก่อนปิดสัญญา").format(doc.purchase_order))
	today = nowdate()
	doc.db_set(
		{
			"status": "Closed",
			"closed_on": today,
			"close_reason": reason.strip(),
			"warranty_end": add_days(today, cint(doc.warranty_days)) if cint(doc.warranty_days) else None,
		}
	)
	doc.add_comment("Info", _("ปิดสัญญา: {0}").format(reason.strip()))
	set_po_closed(doc, True)


@frappe.whitelist(methods=["POST"])
def reopen_agreement(name):
	"""เปิดสัญญาที่ปิดไปแล้วอีกครั้ง (ปิดผิด) ปริมาณเต็มสัญญาต้องยังไม่เกินแผนงาน"""
	doc = frappe.get_doc("Subcontract Agreement", name)
	doc.check_permission("submit")
	if doc.docstatus != 1 or doc.status != "Closed":
		frappe.throw(_("สัญญานี้ไม่ได้ปิดอยู่"))
	check_plan_quantity(doc.construction_management, doc.items, exclude=doc.name)
	doc.db_set({"status": "Active", "closed_on": None, "close_reason": None, "warranty_end": None})
	refresh_agreement(name)
	doc.add_comment("Info", _("เปิดสัญญาอีกครั้ง"))
	set_po_closed(doc, False)


def advance_paid(doc):
	"""เงินล่วงหน้าที่จ่ายแล้ว = Payment Entry ที่อ้าง PO ของสัญญา (PO.advance_paid ของ ERPNext)"""
	if not doc.purchase_order:
		return 0
	return flt(frappe.db.get_value("Purchase Order", doc.purchase_order, "advance_paid"))


def po_description(row):
	"""คำอธิบายแถว PO: [งานเพิ่ม] WBS + รายการ + (ปริมาณ หน่วยจริง) เพราะ PO ใช้หน่วยของ Item ตั้งค่า"""
	extra = _("[งานเพิ่ม {0}]").format(row.variation) if row.get("variation") else None
	return " ".join(filter(None, [extra, row.wbs, row.item_name, f"({flt(row.qty):g} {row.uom or ''})"]))


def po_item(doc, row, settings, stock_uom, cost_center, schedule):
	return {
		"item_code": settings.subcontract_item,
		"item_name": (row.item_name or "")[:140],
		"description": po_description(row),
		"qty": row.qty,
		"uom": stock_uom,
		"stock_uom": stock_uom,
		"conversion_factor": 1,
		"rate": row.rate,
		"schedule_date": schedule,
		"project": doc.project,
		"cost_center": cost_center,
		"expense_account": settings.get("subcontract_expense_account"),
	}


@frappe.whitelist(methods=["POST"])
def make_purchase_order(name):
	"""ร่าง PO จากสัญญา 1 แถวสัญญา = 1 แถว PO (หน่วยของ Item ตั้งค่า ปริมาณ/หน่วยจริงอยู่ในคำอธิบาย)"""
	from consbiz.consbiz.doctype.labour_advance.labour_advance import cost_center_of

	doc = frappe.get_doc("Subcontract Agreement", name)
	doc.check_permission("write")
	frappe.has_permission("Purchase Order", "create", throw=True)
	if doc.docstatus != 1:
		frappe.throw(_("ต้อง Submit สัญญาก่อนสร้างใบสั่งซื้อ"))
	if doc.purchase_order and frappe.db.get_value("Purchase Order", doc.purchase_order, "docstatus") in (
		0,
		1,
	):
		frappe.throw(_("สัญญานี้มีใบสั่งซื้อ {0} แล้ว").format(doc.purchase_order))
	settings = require_settings(doc.company, "subcontract_item")
	item = frappe.get_cached_value("Item", settings.subcontract_item, ["stock_uom"], as_dict=True)
	cost_center = cost_center_of(doc.project, doc.company)
	schedule = doc.end_date or doc.start_date or doc.contract_date
	po = frappe.new_doc("Purchase Order")
	po.update(
		{
			"supplier": doc.supplier,
			"company": doc.company,
			"transaction_date": doc.contract_date
			if getdate(doc.contract_date) <= getdate(nowdate())
			else nowdate(),
			"schedule_date": schedule,
			"project": doc.project,
			"ignore_pricing_rule": 1,
		}
	)
	for row in doc.items:
		po.append("items", po_item(doc, row, settings, item.stock_uom, cost_center, schedule))
	if po.meta.has_field("custom_subject_to_wht"):
		po.custom_subject_to_wht = 1 if flt(doc.wht_percent) else 0
		po.custom_wht_percent = flt(doc.wht_percent)
		po.custom_subject_to_retention = 1 if flt(doc.retention_percent) else 0
		po.custom_retention_percent = flt(doc.retention_percent)
	po.insert()
	from consbiz import deductions

	deductions.calculate(po)
	po.save()
	for row, po_row in zip(doc.items, po.items, strict=True):
		row.db_set("purchase_order_item", po_row.name, update_modified=False)
	doc.db_set("purchase_order", po.name)
	return po.name


@frappe.whitelist(methods=["POST"])
def make_advance_payment(name):
	"""ร่าง Payment Entry จ่ายเงินล่วงหน้าอ้าง PO (ยอด = เงินล่วงหน้า - ที่จ่ายแล้ว) ฝ่ายบัญชีเลือกบัญชีเงินแล้ว Submit เอง"""
	from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

	doc = frappe.get_doc("Subcontract Agreement", name)
	doc.check_permission("read")
	if not flt(doc.advance_amount):
		frappe.throw(_("สัญญานี้ไม่มีเงินล่วงหน้า"))
	if not doc.purchase_order or frappe.db.get_value("Purchase Order", doc.purchase_order, "docstatus") != 1:
		frappe.throw(_("ต้องสร้างและ Submit ใบสั่งซื้อ (PO) ก่อนจ่ายเงินล่วงหน้า"))
	remaining = money(flt(doc.advance_amount) - advance_paid(doc))
	if remaining <= 0:
		frappe.throw(_("จ่ายเงินล่วงหน้าครบแล้ว"))
	pe = get_payment_entry("Purchase Order", doc.purchase_order, party_amount=remaining)
	pe.paid_amount = pe.received_amount = remaining
	for ref in pe.references:
		ref.allocated_amount = remaining
	pe.project = doc.project
	# บัญชีธนาคารบังคับเลขที่/วันที่อ้างอิงแม้เป็นร่าง ใส่เลขสัญญาไว้ก่อน ฝ่ายบัญชีแก้เป็นเลขที่โอนจริง
	pe.reference_no = pe.reference_no or doc.contract_no or doc.name
	pe.reference_date = pe.reference_date or nowdate()
	pe.remarks = _("เงินล่วงหน้าตามสัญญาจ้างเหมาช่วง {0}").format(doc.name)
	pe.flags.ignore_mandatory = True
	pe.insert()
	return pe.name


# ---------------------------------------------------------------- ใบเบิกงวด


def agreement_of(doc):
	agreement = frappe.get_doc("Subcontract Agreement", doc.subcontract_agreement)
	if agreement.docstatus != 1:
		frappe.throw(_("สัญญา {0} ยังไม่ได้ Submit หรือถูกยกเลิกแล้ว").format(agreement.name))
	return agreement


def task_progress(agreement):
	"""% ความคืบหน้าจริงของงานในแผน ตาม WBS"""
	if not agreement.construction_management:
		return {}
	return {
		t.wbs: flt(t.progress)
		for t in frappe.get_all(
			"Construction Management Task",
			filters={"parent": agreement.construction_management, "parenttype": "Construction Management"},
			fields=["wbs", "progress"],
		)
		if t.wbs
	}


def free_milestones(agreement, exclude=None):
	"""งวดงานที่ยังไม่มีใบเบิก (ใบที่ยังไม่ยกเลิก)"""
	filters = {"subcontract_agreement": agreement.name, "docstatus": ("<", 2), "milestone": ("is", "set")}
	if exclude:
		filters["name"] = ("!=", exclude)
	used = set(frappe.get_all("Subcontract Claim", filters=filters, pluck="milestone"))
	return [m for m in agreement.milestones if m.name not in used]


def before_insert_claim(doc):
	"""เลขที่ใบเบิก (.ABBR.) ตั้งก่อน validate ใช้บริษัทของสัญญา"""
	if doc.subcontract_agreement:
		doc.company = frappe.db.get_value("Subcontract Agreement", doc.subcontract_agreement, "company")


def validate_claim(doc):
	agreement = agreement_of(doc)
	if agreement.status == "Closed":
		frappe.throw(_("สัญญา {0} ปิดแล้ว เบิกเพิ่มไม่ได้").format(agreement.name))
	if agreement.status == "Completed" and doc.docstatus == 0 and doc.is_new():
		frappe.throw(_("สัญญา {0} เบิกครบแล้ว").format(agreement.name))
	for field in ("title", "supplier", "supplier_name", "project", "company", "billing_method"):
		doc.set(field, agreement.get(field))
	if doc.docstatus == 0:
		doc.status = "Draft"
		doc.claim_no = len(submitted_claims(agreement.name, exclude=doc.name)) + 1
	if doc.period_from and doc.period_to and getdate(doc.period_to) < getdate(doc.period_from):
		frappe.throw(_("วันสิ้นสุดช่วงงานต้องไม่ก่อนวันเริ่ม"))

	previous = claimed_qty_by_row(agreement.name, exclude=doc.name)
	entered = {row.agreement_item: row.qty for row in doc.items}
	percent = None
	# สัญญางวดงาน: เลือกงวด = % ของงานหลัก, ไม่เลือกงวด = เบิกเฉพาะงานเพิ่มแนบท้าย (งานหลักคงเดิม)
	main_fixed = False
	if agreement.billing_method == "Milestone" and doc.milestone:
		milestone = next((m for m in agreement.milestones if m.name == doc.milestone), None)
		if not milestone:
			frappe.throw(_("ไม่พบงวดงานนี้ในสัญญา"))
		if milestone.name not in {m.name for m in free_milestones(agreement, exclude=doc.name)}:
			frappe.throw(_("งวด {0} มีใบเบิกแล้ว").format(milestone.description))
		doc.milestone_description = milestone.description
		doc.milestone_percent = milestone.percent
		percent = flt(milestone.percent)
		last = len(free_milestones(agreement, exclude=doc.name)) == 1
	elif agreement.billing_method == "Milestone":
		if not any(r.variation for r in agreement.items):
			frappe.throw(_("เลือกงวดงานที่จะเบิก"))
		main_fixed = True
		doc.milestone_description = None
		doc.milestone_percent = 0
	else:
		doc.milestone = doc.milestone_description = None
		doc.milestone_percent = 0

	progress = task_progress(agreement)
	doc.set("items", [])
	for row in agreement.items:
		prev_qty = flt(previous.get(row.name, (0, 0))[0], 6)
		if percent is not None and not row.variation:
			# งวดงาน: % ของงวด x ปริมาณงานหลัก (งวดสุดท้ายเบิกส่วนที่เหลือ)
			cumulative = flt(row.qty) if last else prev_qty + flt(row.qty) * percent / 100
		elif main_fixed and not row.variation:
			cumulative = prev_qty
		else:
			# ตามปริมาณ + งานเพิ่มแนบท้ายทุกสัญญา: กรอกปริมาณงวดนี้ สะสม = ก่อนหน้า + งวดนี้
			qty = entered.get(row.name)
			qty = 0 if qty in (None, "") else flt(qty)
			if qty < -QTY_TOLERANCE:
				frappe.throw(_("{0}: ปริมาณงวดนี้ติดลบไม่ได้").format(row.item_name))
			cumulative = prev_qty + qty
		cumulative = flt(cumulative, 6)
		if cumulative > flt(row.qty) + QTY_TOLERANCE:
			frappe.throw(
				_("{0}: งวดนี้เกินปริมาณคงเหลือ ({1:g} {2}) เกินสัญญาต้องทำใบงานเพิ่มก่อน").format(
					row.item_name, flt(max(flt(row.qty) - prev_qty, 0), 4), row.uom or ""
				)
			)
		qty = flt(cumulative - prev_qty, 6)
		doc.append(
			"items",
			{
				"agreement_item": row.name,
				"variation": row.variation,
				"wbs": row.wbs,
				"item_name": row.item_name,
				"uom": row.uom,
				"contract_qty": row.qty,
				"previous_qty": prev_qty,
				"cumulative_qty": cumulative,
				"qty": qty,
				"remaining_qty": flt(max(flt(row.qty) - cumulative, 0), 6),
				"rate": row.rate,
				"amount": money(qty * flt(row.rate)),
				"claimed_progress": flt(cumulative / flt(row.qty) * 100, 2) if flt(row.qty) else 0,
				"actual_progress": progress.get(row.wbs) if row.wbs in progress else None,
			},
		)
	doc.gross_amount = money(sum(flt(r.amount) for r in doc.items))
	if doc.gross_amount <= 0:
		frappe.throw(_("ยอดเบิกงวดนี้ต้องมากกว่า 0"))
	over = [
		r.item_name
		for r in doc.items
		if r.wbs in progress and flt(r.claimed_progress) > flt(r.actual_progress) + 0.01
	]
	if over:
		frappe.msgprint(
			_("เบิกเกินความคืบหน้าจริงในแผนงาน: {0}").format(", ".join(over)),
			indicator="orange",
			alert=True,
		)

	others = submitted_claims(agreement.name, exclude=doc.name)
	# หักคืนเงินล่วงหน้า: % ของงวด ไม่เกินยอดที่จ่ายจริงแล้วที่ยังหักไม่หมด
	recovered = sum(flt(c.advance_recovery) for c in others)
	open_advance = max(advance_paid(agreement) - recovered, 0)
	doc.advance_recovery = money(
		min(doc.gross_amount * flt(agreement.advance_recovery_percent) / 100, open_advance)
	)
	# เงินประกัน: % ของงวด ไม่เกินเพดาน (ถ้ามี)
	retention = doc.gross_amount * flt(agreement.retention_percent) / 100
	if flt(agreement.retention_cap_percent):
		cap = flt(agreement.total_amount) * flt(agreement.retention_cap_percent) / 100
		retention = min(retention, max(cap - sum(flt(c.retention_amount) for c in others), 0))
	doc.retention_amount = money(retention)
	doc.wht_amount = money(doc.gross_amount * flt(agreement.wht_percent) / 100)
	doc.penalty_days = max(cint(doc.penalty_days), 0)
	doc.penalty_amount = money(doc.penalty_days * flt(agreement.penalty_per_day))
	doc.net_amount = money(
		doc.gross_amount - doc.advance_recovery - doc.retention_amount - doc.wht_amount - doc.penalty_amount
	)


def on_submit_claim(doc):
	doc.db_set("status", "Approved")
	refresh_agreement(doc.subcontract_agreement)


def before_cancel_claim(doc):
	if doc.purchase_invoice:
		status = frappe.db.get_value("Purchase Invoice", doc.purchase_invoice, "docstatus")
		if status == 1:
			frappe.throw(_("ยกเลิกใบแจ้งหนี้ {0} ก่อนยกเลิกใบเบิก").format(doc.purchase_invoice))
		if status == 0:
			frappe.delete_doc("Purchase Invoice", doc.purchase_invoice, ignore_permissions=True)
		doc.db_set("purchase_invoice", None)


def on_cancel_claim(doc):
	doc.db_set("status", "Cancelled")
	refresh_agreement(doc.subcontract_agreement)


@frappe.whitelist(methods=["POST"])
def make_purchase_invoice(name):
	"""ร่าง PI จากใบเบิกที่อนุมัติแล้ว ฝ่ายบัญชีตรวจ/ใส่ภาษีซื้อแล้ว Submit เอง"""
	from consbiz.consbiz.doctype.labour_advance.labour_advance import cost_center_of

	claim = frappe.get_doc("Subcontract Claim", name)
	claim.check_permission("read")
	frappe.has_permission("Purchase Invoice", "create", throw=True)
	if claim.docstatus != 1:
		frappe.throw(_("ต้องอนุมัติ (Submit) ใบเบิกก่อน"))
	if claim.purchase_invoice and frappe.db.get_value(
		"Purchase Invoice", claim.purchase_invoice, "docstatus"
	) in (0, 1):
		frappe.throw(_("ใบเบิกนี้มีใบแจ้งหนี้ {0} แล้ว").format(claim.purchase_invoice))
	agreement = frappe.get_doc("Subcontract Agreement", claim.subcontract_agreement)
	fields = ["subcontract_item"] + (["penalty_income_account"] if flt(claim.penalty_amount) else [])
	settings = require_settings(claim.company, *fields)
	item = frappe.get_cached_value("Item", settings.subcontract_item, ["stock_uom"], as_dict=True)
	cost_center = cost_center_of(claim.project, claim.company)
	po = (
		agreement.purchase_order
		if frappe.db.get_value("Purchase Order", agreement.purchase_order, "docstatus") == 1
		else None
	)
	po_rows = {row.name: row.purchase_order_item for row in agreement.items} if po else {}

	pi = frappe.new_doc("Purchase Invoice")
	pi.update(
		{
			"supplier": claim.supplier,
			"company": claim.company,
			"posting_date": claim.posting_date,
			"set_posting_time": 1,
			"project": claim.project,
			"bill_no": _("งวดที่ {0}").format(claim.claim_no),
			"ignore_pricing_rule": 1,
			"remarks": _("เบิกงวดที่ {0} สัญญา {1} ({2})").format(claim.claim_no, agreement.name, claim.name),
		}
	)
	for row in claim.items:
		if flt(row.qty) <= 0:
			continue
		pi.append(
			"items",
			{
				"item_code": settings.subcontract_item,
				"item_name": row.item_name[:140],
				"description": " ".join(
					filter(
						None,
						[
							row.wbs,
							row.item_name,
							f"({flt(row.qty):g} {row.uom or ''})",
							_("งวดที่ {0}").format(claim.claim_no),
						],
					)
				),
				"qty": row.qty,
				"uom": item.stock_uom,
				"stock_uom": item.stock_uom,
				"conversion_factor": 1,
				"rate": row.rate,
				"project": claim.project,
				"cost_center": cost_center,
				"expense_account": settings.get("subcontract_expense_account"),
				"purchase_order": po if po_rows.get(row.agreement_item) else None,
				"po_detail": po_rows.get(row.agreement_item),
			},
		)
	pi.insert()

	# เงินล่วงหน้า: ดึงรายการจ่ายล่วงหน้าที่อ้าง PO แล้วจัดสรรไม่เกินยอดหักคืนของงวดนี้
	if flt(claim.advance_recovery) and po:
		pi.set_advances()
		left = flt(claim.advance_recovery)
		rows = []
		for adv in pi.advances:
			adv.allocated_amount = min(flt(adv.advance_amount), left)
			left -= adv.allocated_amount
			if adv.allocated_amount > 0:
				rows.append(adv)
		pi.set("advances", rows)
	if pi.meta.has_field("custom_subject_to_wht"):
		pi.custom_subject_to_wht = 1 if flt(claim.wht_amount) else 0
		pi.custom_wht_percent = flt(agreement.wht_percent)
		pi.custom_subject_to_retention = 1 if flt(claim.retention_amount) else 0
		# เปอร์เซ็นต์จริงของงวดนี้ (เพดานเงินประกันอาจทำให้ต่ำกว่าในสัญญา) แล้วใช้ยอดของใบเบิกตรงๆ
		pi.custom_retention_percent = (
			flt(claim.retention_amount / claim.gross_amount * 100, 6) if claim.gross_amount else 0
		)
	pi.save()
	set_deductions(pi, claim, settings)
	pi.save()
	claim.db_set("purchase_invoice", pi.name)
	return pi.name


def set_deductions(pi, claim, settings):
	"""ตารางหักของ PI = หัก ณ ที่จ่าย + เงินประกัน (ยอดจากใบเบิก) + ค่าปรับ แล้วคิดยอดสุทธิแบบ deductions.calculate"""
	from consbiz import deductions

	if not pi.meta.has_field("custom_subject_to_wht"):
		return
	pi.custom_wht_amount = flt(claim.wht_amount)
	pi.custom_retention_amount = flt(claim.retention_amount)
	deductions.sync_table(pi, flt(claim.wht_amount), flt(claim.retention_amount))
	table = deductions.TABLE
	account = settings.get("penalty_income_account")
	keep = ("account", "amount", "description", "cost_center")
	rows = [{f: r.get(f) for f in keep} for r in pi.get(table) or [] if r.account != account]
	if flt(claim.penalty_amount) and account:
		rows.append(
			{
				"account": account,
				"amount": flt(claim.penalty_amount),
				"description": _("ค่าปรับ {0} วัน").format(claim.penalty_days),
				"cost_center": pi.items[0].cost_center if pi.items else None,
			}
		)
	pi.set(table, rows)
	total = flt(sum(flt(r.amount) for r in pi.get(table) or []), 2)
	pi.custom_total_deductions = total
	net = flt(
		flt(pi.grand_total) - flt(pi.get("total_advance")) - total + flt(pi.get("rounding_adjustment")), 2
	)
	pi.custom_net_paid_amount = net
	if pi.meta.has_field("custom_paid_amount_in_words"):
		pi.custom_paid_amount_in_words = deductions.baht_words(net)
	if pi.meta.has_field("custom_in_words_th"):
		pi.custom_in_words_th = deductions.baht_words(flt(pi.grand_total))
