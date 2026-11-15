# Copyright (c) 2026, Siricons and contributors
# For license information, please see license.txt

"""ใบงานเพิ่ม ผรม. (Subcontract Variation): รายการแนบท้ายสัญญา แยกจากงานหลัก (ตกลง 2026-11-15)
งานหลักไม่เปลี่ยน (ปริมาณ/มูลค่า/% งวดคงเดิม) แถวแนบท้ายในสัญญามี `variation` = ใบนี้ เบิกตามปริมาณจริงเสมอ
ใช้ได้ทั้งสัญญาเบิกตามปริมาณและตามงวดงาน ไม่มีงานลด (งานจบต่ำกว่าสัญญา = ปิดสัญญา `subcontract.close_agreement`)

Submit = อนุมัติ (สิทธิ์ที่ตรวจ = Submit ใบงานเพิ่ม ผู้อนุมัติไม่ต้องมีสิทธิ์ PO งานต่อจากนี้ระบบทำ `as_system`):
  1. PO ที่ Submit แล้ว: เก็บ PDF ฉบับปัจจุบันไว้ก่อน (`<PO>-Rev<n>.pdf` แนบที่ PO, ลิงก์ที่ `po_snapshot`)
  2. เพิ่มแถวแนบท้ายในสัญญา (`revision` = ครั้งที่, `variation_amount`, `original_amount` = งานหลัก)
  3. PO เดิมเลขที่เดิม: เพิ่มแถวด้วย Update Items ของ ERPNext (`update_child_qty_rate`) + คำนวณหักใหม่
     `custom_revision` / `custom_revision_note` = Rev. ที่พิมพ์ในใบ PO, `custom_revision_pending` = รอฝ่ายจัดซื้อส่งผู้รับเหมา
  4. แจ้งฝ่ายจัดซื้อทุกคนของบริษัท (`notify_purchasing`) ใครก็กด "ส่งผู้รับเหมาแล้ว" ได้ (`mark_po_sent`)
ปริมาณจ้างรวมต่องานต้องไม่เกินแผนงาน (`subcontract.check_plan_quantity`) เกินต้องทำ VO ผู้ว่าจ้างก่อน
ยกเลิกได้เฉพาะฉบับล่าสุด และแถวแนบท้ายต้องยังไม่ถูกเบิก (ลบแถวในสัญญาและ PO, PO กลับ Rev. ก่อนหน้า + รอส่งใหม่)"""

import json

import frappe
from frappe import _
from frappe.utils import cint, flt, formatdate

from consbiz.subcontract import (
	add_po_comment,
	as_system,
	check_plan_quantity,
	claimed_qty_by_row,
	money,
	notify_purchasing,
	po_item,
	refresh_agreement,
	require_settings,
)

HEADER = ("title", "supplier", "supplier_name", "project", "company", "purchase_order")
PO_TOTAL_FIELDS = (
	"custom_wht_amount",
	"custom_retention_amount",
	"custom_paid_amount",
	"custom_paid_amount_in_words",
	"custom_in_words_th",
)


def agreement_of(doc):
	agreement = frappe.get_doc("Subcontract Agreement", doc.subcontract_agreement)
	if agreement.docstatus != 1:
		frappe.throw(_("สัญญา {0} ยังไม่ได้ Submit หรือถูกยกเลิกแล้ว").format(agreement.name))
	return agreement


def before_insert(doc):
	"""เลขที่ (.ABBR.) ตั้งก่อน validate ใช้บริษัทของสัญญา"""
	if doc.subcontract_agreement:
		doc.company = frappe.db.get_value("Subcontract Agreement", doc.subcontract_agreement, "company")


def validate(doc):
	agreement = agreement_of(doc)
	if agreement.status == "Closed":
		frappe.throw(_("สัญญา {0} ปิดแล้ว ทำใบงานเพิ่มไม่ได้ (เปิดสัญญาอีกครั้งก่อน)").format(agreement.name))
	for field in HEADER:
		doc.set(field, agreement.get(field))
	if doc.docstatus == 0:
		doc.status = "Draft"
	doc.revision_no = cint(agreement.revision) + 1
	if doc.variation_order:
		vo = frappe.db.get_value(
			"Variation Order", doc.variation_order, ["construction_management", "docstatus"], as_dict=True
		)
		if not vo or vo.docstatus != 1 or vo.construction_management != agreement.construction_management:
			frappe.throw(_("VO {0} ต้อง Submit แล้วและเป็นของแผนงานเดียวกับสัญญา").format(doc.variation_order))
	if not doc.items:
		frappe.throw(_("ใส่รายการงานเพิ่มอย่างน้อย 1 แถว"))
	for v in doc.items:
		if not (v.item_name or "").strip():
			frappe.throw(_("แถว {0}: กรอกชื่อรายการ").format(v.idx))
		if flt(v.qty) <= 0:
			frappe.throw(_("แถว {0} ({1}): กรอกปริมาณ").format(v.idx, v.item_name))
		if flt(v.rate) < 0:
			frappe.throw(_("แถว {0} ({1}): ราคาต่อหน่วยติดลบไม่ได้").format(v.idx, v.item_name))
		v.amount = money(flt(v.qty) * flt(v.rate))
	doc.previous_amount = money(agreement.total_amount)
	doc.addition_amount = money(sum(flt(v.amount) for v in doc.items))
	doc.revised_amount = money(doc.previous_amount + doc.addition_amount)
	if doc.addition_amount <= 0:
		frappe.throw(_("มูลค่างานเพิ่มต้องมากกว่า 0"))
	planned = [{"wbs": r.wbs, "uom": r.uom, "qty": r.qty} for r in agreement.items] + [
		{"wbs": v.wbs, "uom": v.uom, "qty": v.qty} for v in doc.items
	]
	check_plan_quantity(agreement.construction_management, planned, exclude=agreement.name)


# ---------------------------------------------------------------- อนุมัติ / ยกเลิก


def po_state(agreement):
	if not agreement.purchase_order:
		return None
	return frappe.db.get_value("Purchase Order", agreement.purchase_order, "docstatus")


def snapshot_po(po_name, revision):
	"""PDF ของ PO ฉบับปัจจุบัน (แบบพิมพ์ตั้งต้น) แนบที่ PO ก่อนแก้ สร้างไม่ได้ = ไม่อนุมัติ (ฉบับเดิมต้องไม่หาย)"""
	try:
		pdf = frappe.get_print("Purchase Order", po_name, as_pdf=True)
	except Exception:
		frappe.log_error(title=f"PO snapshot {po_name}")
		frappe.throw(_("สร้าง PDF ใบสั่งซื้อ {0} ฉบับเดิมไม่ได้ จึงยังไม่อนุมัติ (ตรวจการตั้งค่า PDF)").format(po_name))
	file = frappe.get_doc(
		{
			"doctype": "File",
			"file_name": f"{po_name}-Rev{revision}.pdf",
			"attached_to_doctype": "Purchase Order",
			"attached_to_name": po_name,
			"is_private": 1,
			"content": pdf,
		}
	)
	file.save(ignore_permissions=True)
	return file.file_url


def on_submit(doc):
	agreement = agreement_of(doc)
	user = frappe.session.user
	state = po_state(agreement)
	if state == 1:
		with as_system():
			url = snapshot_po(agreement.purchase_order, doc.revision_no - 1)
		doc.db_set("po_snapshot", url)

	added = []
	for v in doc.items:
		row = agreement.append(
			"items",
			{
				"variation": doc.name,
				"wbs": v.wbs,
				"item_name": v.item_name,
				"uom": v.uom,
				"qty": v.qty,
				"rate": v.rate,
				"amount": money(flt(v.qty) * flt(v.rate)),
			},
		)
		row.name = frappe.generate_hash(length=10)
		row.db_insert()
		v.db_set("new_agreement_item", row.name, update_modified=False)
		added.append(row)
	save_agreement_totals(agreement, doc.revision_no)

	if state in (0, 1):
		with as_system():
			update_po(agreement, added=added, revision=doc.revision_no, note=revision_note(doc))
	if state == 1:
		after_po_change(
			agreement,
			_("ใบสั่งซื้อ {0} แก้เป็น Rev.{1} ตามใบงานเพิ่ม {2} รอส่งผู้รับเหมา").format(
				agreement.purchase_order, doc.revision_no, doc.name
			),
			user,
		)
	refresh_agreement(agreement.name)
	doc.db_set("status", "Approved")


def before_cancel(doc):
	agreement = agreement_of(doc)
	if agreement.status == "Closed":
		frappe.throw(_("สัญญา {0} ปิดแล้ว เปิดสัญญาอีกครั้งก่อนยกเลิกใบงานเพิ่ม").format(agreement.name))
	if cint(doc.revision_no) != cint(agreement.revision):
		frappe.throw(_("ยกเลิกได้เฉพาะใบงานเพิ่มล่าสุดของสัญญา (ครั้งที่ {0})").format(cint(agreement.revision)))
	claimed = claimed_qty_by_row(agreement.name)
	for v in doc.items:
		done = flt(claimed.get(v.new_agreement_item, (0, 0))[0])
		if done > 0:
			frappe.throw(
				_("{0}: เบิกไปแล้ว {1:g} {2} ยกเลิกใบเบิกก่อน").format(v.item_name, flt(done, 4), v.uom or "")
			)


def on_cancel(doc):
	agreement = agreement_of(doc)
	user = frappe.session.user
	removed = [r for r in agreement.items if r.variation == doc.name]
	for row in removed:
		frappe.db.delete("Subcontract Agreement Item", row.name)
	agreement.set("items", [r for r in agreement.items if r.variation != doc.name])
	save_agreement_totals(agreement, cint(doc.revision_no) - 1)
	state = po_state(agreement)
	if state in (0, 1):
		previous = frappe.get_all(
			"Subcontract Variation",
			filters={
				"subcontract_agreement": agreement.name,
				"docstatus": 1,
				"revision_no": cint(doc.revision_no) - 1,
			},
			fields=["name", "posting_date", "revision_no"],
			limit=1,
		)
		with as_system():
			update_po(
				agreement,
				removed=removed,
				revision=cint(doc.revision_no) - 1,
				note=revision_note(previous[0]) if previous else None,
			)
	if state == 1:
		after_po_change(
			agreement,
			_("ยกเลิกใบงานเพิ่ม {0}: ใบสั่งซื้อ {1} กลับเป็น Rev.{2} รอส่งผู้รับเหมา").format(
				doc.name, agreement.purchase_order, cint(doc.revision_no) - 1
			),
			user,
		)
	refresh_agreement(agreement.name)
	doc.db_set("status", "Cancelled")


def save_agreement_totals(agreement, revision):
	main = money(sum(flt(r.amount) for r in agreement.items if not r.variation))
	extra = money(sum(flt(r.amount) for r in agreement.items if r.variation))
	agreement.db_set(
		{
			"original_amount": main,
			"variation_amount": extra,
			"total_amount": money(main + extra),
			"revision": revision,
		}
	)


def revision_note(variation):
	return _("Rev.{0} ตามใบงานเพิ่ม {1} วันที่ {2}").format(
		variation.revision_no, variation.name, formatdate(variation.posting_date)
	)


def after_po_change(agreement, subject, user):
	"""บันทึกในหน้า PO ว่าใครอนุมัติ แล้วแจ้งฝ่ายจัดซื้อทุกคนของบริษัท"""
	add_po_comment(agreement.purchase_order, subject, user)
	notify_purchasing(agreement.company, "Purchase Order", agreement.purchase_order, subject)


# ---------------------------------------------------------------- PO


def update_po(agreement, added=(), removed=(), revision=0, note=None):
	"""เพิ่มแถวแนบท้ายใหม่ / ลบแถวแนบท้ายที่ยกเลิก ใน PO เดิมเลขที่เดิม (เรียกใน as_system)"""
	from consbiz import deductions
	from consbiz.consbiz.doctype.labour_advance.labour_advance import cost_center_of

	po = frappe.get_doc("Purchase Order", agreement.purchase_order)
	settings = require_settings(agreement.company, "subcontract_item")
	stock_uom = frappe.get_cached_value("Item", settings.subcontract_item, "stock_uom")
	cost_center = cost_center_of(agreement.project, agreement.company)
	schedule = po.schedule_date
	drop = {r.purchase_order_item for r in removed if r.get("purchase_order_item")}
	before = {i.name for i in po.items}

	if po.docstatus == 0:
		# ร่าง: แก้ตรง ยังไม่ได้ส่งผู้รับเหมาจึงไม่ต้องมี Rev.
		po.set("items", [i for i in po.items if i.name not in drop])
		for row in added:
			po.append("items", po_item(agreement, row, settings, stock_uom, cost_center, schedule))
		po.save()
		deductions.calculate(po)
		po.save()
		link_new_rows(po, added, before)
		return

	from erpnext.controllers.accounts_controller import update_child_qty_rate

	trans = [
		{
			"docname": item.name,
			"item_code": item.item_code,
			"qty": item.qty,
			"rate": item.rate,
			"uom": item.uom,
			"conversion_factor": item.conversion_factor,
			"schedule_date": str(item.schedule_date),
			"description": item.description,
		}
		for item in po.items
		if item.name not in drop
	]
	for row in added:
		values = po_item(agreement, row, settings, stock_uom, cost_center, schedule)
		values["schedule_date"] = str(schedule)
		trans.append(values)
	update_child_qty_rate("Purchase Order", json.dumps(trans), po.name)

	po.reload()
	link_new_rows(po, added, before)
	# แถวใหม่จาก Update Items ไม่มีชื่อ/โครงการ/ศูนย์ต้นทุน/บัญชีค่าใช้จ่ายแบบแถวที่ระบบสร้าง
	names = {r.purchase_order_item: r.item_name for r in added}
	for item in po.items:
		if item.name not in before:
			item.db_set(
				{
					"item_name": (names.get(item.name) or item.item_name or "")[:140],
					"project": agreement.project,
					"cost_center": cost_center,
					"expense_account": settings.get("subcontract_expense_account") or item.expense_account,
				},
				update_modified=False,
			)
	deductions.calculate(po)
	values = {f: po.get(f) for f in PO_TOTAL_FIELDS if po.meta.has_field(f)}
	if po.meta.has_field("custom_revision_pending"):
		values.update(custom_revision=revision, custom_revision_note=note, custom_revision_pending=1)
	po.db_set(values)


def link_new_rows(po, added, before):
	"""แถว PO ที่เพิ่มใหม่ (ตามลำดับ) ↔ แถวแนบท้ายในสัญญา"""
	if not added:
		return
	new_items = [i for i in sorted(po.items, key=lambda i: i.idx) if i.name not in before][-len(added) :]
	for row, item in zip(added, new_items, strict=False):
		row.purchase_order_item = item.name
		row.db_set("purchase_order_item", item.name, update_modified=False)
