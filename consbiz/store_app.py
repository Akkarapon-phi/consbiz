# Copyright (c) 2026, Siricons and contributors
# For license information, please see license.txt

"""แอปสโตร์หน้างานบนมือถือ (/store, www/store.html + public/js/site_store/) ใช้เอกสารมาตรฐานทั้งหมด

- รับของ:
  - ซื้อเอง: PO ของโครงการที่ยังรับไม่ครบ → Purchase Receipt (บัญชีทำ PI ต่อจาก PR)
  - ผู้ว่าจ้างจัดหา: MR ประเภท Customer Provided (OPO-) ที่ยังรับไม่ครบ → Stock Entry Material Receipt
  - ตีกลับที่หน้างาน = ไม่รับเข้าสต็อก (ยอดยังค้างที่ PO/MR ให้ผู้ขายส่งใหม่)
    เก็บจำนวน/เหตุผลในแถว (custom_site_rejected_qty / custom_site_reject_reason)
    รายการที่ตีกลับทั้งหมดไม่มีแถวในใบรับ: บันทึกในหมายเหตุของใบรับ หรือเป็น Comment ที่ PO/MR ถ้าไม่ได้รับอะไรเลย
- เบิก: Stock Entry Material Issue จากคลังของโครงการ (ตัดวัสดุผู้ว่าจ้างก่อนที่ site_stock.split_employer_stock)
- คอนกรีต: Concrete Usage ของแผนงานของโครงการ
- ยืม-คืน: Equipment Borrowing (คืนผ่าน equipment_borrowing.record_return)
- คลัง: construction_management/stock.py ชุดเดียวกับ Tab คลังวัสดุ
สิทธิ์ตามเอกสารแต่ละชนิด (get_list / insert / submit ตรวจสิทธิ์ของผู้ใช้เอง)
"""

import json

import frappe
from frappe import _
from frappe.utils import add_days, cint, flt, getdate, nowdate, nowtime

from consbiz.consbiz.doctype.construction_management.construction_management import get_task_options
from consbiz.consbiz.doctype.equipment_borrowing.equipment_borrowing import get_outstanding
from consbiz.site_stock import construction_management_of, project_warehouse

EPSILON = 1e-9
HISTORY_DAYS = 90
CLOSED_PO = ("Closed", "On Hold", "Completed", "Delivered", "Cancelled")
CLOSED_MR = ("Stopped", "Cancelled", "Received")


def hhmm(value):
	"""เวลา (timedelta / "H:MM:SS.ffff") เป็น "HH:MM" """
	if not value:
		return ""
	parts = str(value).split(":")
	return f"{int(parts[0]):02d}:{parts[1][:2]}" if len(parts) > 1 else str(value)


def parse(value):
	return json.loads(value) if isinstance(value, str) else (value or {})


def check_project(project):
	if not project:
		frappe.throw(_("กรุณาเลือกโครงการ"))
	frappe.has_permission("Project", "read", project, throw=True)
	return frappe.db.get_value("Project", project, ["name", "project_name", "company"], as_dict=True)


def item_images(codes):
	codes = [c for c in set(codes) if c]
	if not codes:
		return {}
	return {
		r.name: r
		for r in frappe.get_all(
			"Item",
			filters={"name": ("in", codes)},
			fields=["name", "item_name", "image", "stock_uom", "custom_base_item", "is_customer_provided_item"],
		)
	}


def preview(names):
	"""ชื่อวัสดุ 3 รายการแรก + จำนวนรายการ"""
	names = list(dict.fromkeys(n for n in names if n))
	return {"names": names[:3], "count": len(names)}


def attach_files(files, doctype, name):
	for file_name in files or []:
		if frappe.db.exists("File", file_name):
			frappe.db.set_value(
				"File", file_name, {"attached_to_doctype": doctype, "attached_to_name": name}, update_modified=False
			)


# ---------------------------------------------------------------- ข้อมูลเริ่มต้น


def can_delete(doc):
	"""ลบได้เฉพาะร่างและเอกสารที่ยกเลิกแล้ว ตามสิทธิ์ลบของผู้ใช้ (กติกาเดียวกับปุ่ม Delete ของระบบเต็ม)"""
	return bool(doc.docstatus != 1 and doc.has_permission("delete"))


def delete_document(doc):
	"""Document.delete ตรวจสิทธิ์ลบ, สถานะเอกสาร และเอกสารอื่นที่อ้างถึงให้เอง"""
	doc.delete()


def boot_data():
	user = frappe.get_cached_doc("User", frappe.session.user)
	can = {
		"receive": bool(frappe.has_permission("Purchase Receipt", "create")),
		"receive_employer": bool(frappe.has_permission("Stock Entry", "create")),
		"issue": bool(frappe.has_permission("Stock Entry", "create")),
		"concrete": bool(frappe.has_permission("Concrete Usage", "create")),
		"borrow": bool(frappe.has_permission("Equipment Borrowing", "create")),
		"concrete_submit": bool(frappe.has_permission("Concrete Usage", "submit")),
		# view_* = เห็นเมนู/รายการ (สิทธิ์อ่าน) ปุ่มทำรายการใช้สิทธิ์สร้างด้านบน
		"view_receive": bool(frappe.has_permission("Purchase Receipt", "read") or frappe.has_permission("Stock Entry", "read")),
		"view_stock": bool(frappe.has_permission("Stock Entry", "read")),
		"view_borrow": bool(frappe.has_permission("Equipment Borrowing", "read")),
		"view_concrete": bool(frappe.has_permission("Concrete Usage", "read")),
	}
	return {
		"user": user.name,
		"full_name": user.full_name or user.name,
		"user_image": user.user_image,
		"can": can,
		"today": nowdate(),
		"desk": bool(frappe.has_permission("Stock Entry", "read")),
	}


@frappe.whitelist()
def get_projects():
	return frappe.get_list(
		"Project",
		filters={"status": "Open"},
		fields=["name", "project_name", "company", "custom_abbr"],
		order_by="modified desc",
		limit_page_length=300,
	)


@frappe.whitelist()
def get_summary(project):
	info = check_project(project)
	cm = construction_management_of(project)
	borrowings = get_outstanding(project) if frappe.has_permission("Equipment Borrowing", "read") else []
	pending = get_pending_receipts(project)
	month_start = getdate(nowdate()).replace(day=1)

	concrete = 0.0
	if cm and frappe.has_permission("Concrete Usage", "read"):
		concrete = sum(
			flt(r.total_qty)
			for r in frappe.get_list(
				"Concrete Usage",
				filters={"construction_management": cm, "docstatus": 1, "date": (">=", month_start)},
				fields=["total_qty"],
				limit_page_length=0,
			)
		)
	issues_today = (
		frappe.db.count(
			"Stock Entry",
			{"project": project, "purpose": "Material Issue", "docstatus": 1, "posting_date": nowdate()},
		)
		if frappe.has_permission("Stock Entry", "read")
		else 0
	)
	receipts_today = 0
	if frappe.has_permission("Purchase Receipt", "read"):
		receipts_today += len(
			frappe.get_list(
				"Purchase Receipt",
				filters={"project": project, "docstatus": 1, "posting_date": nowdate()},
				pluck="name",
				limit_page_length=0,
			)
		)
	if frappe.has_permission("Stock Entry", "read"):
		receipts_today += frappe.db.count(
			"Stock Entry",
			{"project": project, "purpose": "Material Receipt", "docstatus": 1, "posting_date": nowdate()},
		)
	return {
		"project": project,
		"project_name": info.project_name,
		"receipts_today": receipts_today,
		"company": info.company,
		"construction_management": cm,
		"warehouse": project_warehouse(project),
		"pending_count": len(pending),
		"due_soon": [p for p in pending if p["schedule_date"]][:5],
		"borrow_count": len(borrowings),
		"overdue_count": sum(1 for b in borrowings if b.overdue),
		"issues_today": issues_today,
		"concrete_month": concrete,
	}


# ---------------------------------------------------------------- รับของ: รายการรอรับ


def pending_purchase_orders(project):
	# รายการรอรับ = งานที่ต้องกดรับ จึงเห็นเฉพาะผู้ที่สร้างใบรับได้
	if not (frappe.has_permission("Purchase Order", "read") and frappe.has_permission("Purchase Receipt", "create")):
		return []
	po = frappe.qb.DocType("Purchase Order")
	poi = frappe.qb.DocType("Purchase Order Item")
	rows = (
		frappe.qb.from_(poi)
		.join(po)
		.on(po.name == poi.parent)
		.select(
			po.name,
			po.supplier,
			po.supplier_name,
			po.transaction_date,
			po.schedule_date,
			po.per_received,
			poi.item_name,
			poi.schedule_date.as_("item_schedule_date"),
		)
		.where(po.docstatus == 1)
		.where(po.status.notin(CLOSED_PO))
		.where(poi.received_qty < poi.qty)
		.where(poi.delivered_by_supplier == 0)
		.where((poi.project == project) | (po.project == project))
		.orderby(po.schedule_date)
		.orderby(poi.idx)
	).run(as_dict=True)
	allowed = set(
		frappe.get_list(
			"Purchase Order", filters={"name": ("in", list({r.name for r in rows}) or [""])}, pluck="name"
		)
	)
	return group_pending(rows, allowed, "Purchase Order", "supplier_name", "per_received")


def pending_employer_requests(project):
	if not (frappe.has_permission("Material Request", "read") and frappe.has_permission("Stock Entry", "create")):
		return []
	mr = frappe.qb.DocType("Material Request")
	mri = frappe.qb.DocType("Material Request Item")
	rows = (
		frappe.qb.from_(mri)
		.join(mr)
		.on(mr.name == mri.parent)
		.select(
			mr.name,
			mr.customer.as_("supplier"),
			mr.customer.as_("supplier_name"),
			mr.transaction_date,
			mr.schedule_date,
			mr.per_ordered.as_("per_received"),
			mri.item_name,
			mri.schedule_date.as_("item_schedule_date"),
		)
		.where(mr.docstatus == 1)
		.where(mr.material_request_type == "Customer Provided")
		.where(mr.status.notin(CLOSED_MR))
		.where(mri.ordered_qty < mri.stock_qty)
		.where((mri.project == project) | (mr.custom_project == project))
		.orderby(mr.schedule_date)
		.orderby(mri.idx)
	).run(as_dict=True)
	allowed = set(
		frappe.get_list(
			"Material Request", filters={"name": ("in", list({r.name for r in rows}) or [""])}, pluck="name"
		)
	)
	return group_pending(rows, allowed, "Material Request", "supplier_name", "per_received")


def group_pending(rows, allowed, doctype, party_field, progress_field):
	docs = {}
	for row in rows:
		if row.name not in allowed:
			continue
		doc = docs.setdefault(
			row.name,
			{
				"doctype": doctype,
				"name": row.name,
				"party": row.get(party_field) or row.supplier,
				"date": row.transaction_date,
				"schedule_date": row.schedule_date,
				"progress": flt(row.get(progress_field)),
				"employer": doctype == "Material Request",
				"_items": [],
			},
		)
		doc["_items"].append(row.item_name)
		if row.item_schedule_date and (
			not doc["schedule_date"] or getdate(row.item_schedule_date) < getdate(doc["schedule_date"])
		):
			doc["schedule_date"] = row.item_schedule_date
	today = getdate(nowdate())
	out = []
	for doc in docs.values():
		doc["items"] = preview(doc.pop("_items"))
		doc["overdue"] = bool(doc["schedule_date"] and getdate(doc["schedule_date"]) < today)
		out.append(doc)
	return out


@frappe.whitelist()
def get_pending_receipts(project):
	check_project(project)
	docs = pending_purchase_orders(project) + pending_employer_requests(project)
	return sorted(docs, key=lambda d: (str(d["schedule_date"] or "9999"), d["name"]))


# ---------------------------------------------------------------- รับของ: ฟอร์มรับ


@frappe.whitelist()
def get_receipt_source(doctype, name):
	"""รายการที่ยังค้างรับของ PO / MR ผู้ว่าจ้างจัดหา (หน่วยตามเอกสาร)"""
	if doctype not in ("Purchase Order", "Material Request"):
		frappe.throw(_("ไม่รองรับ {0}").format(doctype))
	doc = frappe.get_doc(doctype, name)
	doc.check_permission("read")
	images = item_images(row.item_code for row in doc.items)
	items = []
	for row in doc.items:
		if doctype == "Purchase Order":
			if row.delivered_by_supplier:
				continue
			ordered, done, uom = flt(row.qty), flt(row.received_qty), row.uom
		else:
			factor = flt(row.conversion_factor) or 1
			ordered, done, uom = flt(row.qty), flt(row.ordered_qty) / factor, row.uom
		pending = ordered - done
		if pending <= EPSILON:
			continue
		items.append(
			{
				"row": row.name,
				"item_code": row.item_code,
				"item_name": row.item_name,
				"description": row.description if row.description != row.item_name else "",
				"uom": uom,
				"ordered": ordered,
				"received": done,
				"pending": pending,
				"image": (images.get(row.item_code) or {}).get("image"),
			}
		)
	return {
		"doctype": doctype,
		"name": name,
		"party": doc.get("supplier_name") or doc.get("customer") or "",
		"date": doc.transaction_date,
		"schedule_date": doc.schedule_date,
		"employer": doctype == "Material Request",
		"project": doc.get("project") or doc.get("custom_project"),
		"items": items,
	}


def rejection_note(rows):
	parts = [
		f"{r['item_name']} {flt(r['rejected_qty']):g} {r.get('uom') or ''}".strip()
		+ (f" ({r['reason']})" if r.get("reason") else "")
		for r in rows
	]
	return _("ตีกลับ: {0}").format(", ".join(parts)) if parts else ""


@frappe.whitelist(methods=["POST"])
def submit_receipt(doctype, name, items, project=None, delivery_note=None, delivered_by=None, vehicle_no=None, remarks=None, files=None):
	"""รับของตาม PO / MR ผู้ว่าจ้างจัดหา items: [{row, qty, rejected_qty, reason}]"""
	source = get_receipt_source(doctype, name)
	items = {r["row"]: r for r in parse(items) or []}
	files = parse(files) or []
	project = project or source["project"]
	warehouse = project_warehouse(project)

	accepted, rejected_only, all_rejected = {}, [], []
	for src in source["items"]:
		row = items.get(src["row"])
		if not row:
			continue
		qty, rejected = flt(row.get("qty")), flt(row.get("rejected_qty"))
		if qty < 0 or rejected < 0:
			frappe.throw(_("{0}: จำนวนต้องไม่ติดลบ").format(src["item_name"]))
		if qty + rejected > src["pending"] + EPSILON:
			frappe.throw(
				_("{0}: รับ + ตีกลับ ({1}) เกินยอดค้างรับ ({2})").format(src["item_name"], qty + rejected, src["pending"])
			)
		info = {**src, "qty": qty, "rejected_qty": rejected, "reason": (row.get("reason") or "").strip()}
		if rejected:
			all_rejected.append(info)
		if qty > EPSILON:
			accepted[src["row"]] = info
		elif rejected:
			rejected_only.append(info)

	if not accepted:
		if not all_rejected:
			frappe.throw(_("กรอกจำนวนที่รับหรือตีกลับอย่างน้อย 1 รายการ"))
		# ไม่ได้รับอะไรเลย: บันทึกการตีกลับไว้ที่ PO / MR
		note = " / ".join(filter(None, [rejection_note(all_rejected), delivery_note and _("ใบส่งของ {0}").format(delivery_note), remarks]))
		frappe.get_doc(doctype, name).add_comment("Comment", note)
		attach_files(files, doctype, name)
		return {"doctype": doctype, "name": name, "rejected_only": True}

	note = "\n".join(filter(None, [remarks, rejection_note(rejected_only)]))
	if doctype == "Purchase Order":
		doc = receipt_from_po(name, accepted, warehouse, project)
		doc.supplier_delivery_note = delivery_note
		doc.transporter_name = delivered_by
		doc.lr_no = vehicle_no
		doc.remarks = note or None
	else:
		doc = receipt_from_employer_request(name, accepted, warehouse, project)
		doc.custom_supplier_delivery_note = delivery_note
		doc.custom_delivered_by = delivered_by
		doc.custom_vehicle_no = vehicle_no
		doc.remarks = note or None

	doc.insert()
	doc.submit()
	attach_files(files, doc.doctype, doc.name)
	return {"doctype": doc.doctype, "name": doc.name}


def is_project_warehouse(warehouse, project):
	return bool(warehouse and project and frappe.db.get_value("Warehouse", warehouse, "custom_project") == project)


def receipt_from_po(name, accepted, warehouse, project):
	from erpnext.buying.doctype.purchase_order.purchase_order import make_purchase_receipt

	doc = make_purchase_receipt(name)
	rows = []
	for row in doc.items:
		info = accepted.get(row.purchase_order_item)
		if not info:
			continue
		row.qty = row.received_qty = info["qty"]
		row.rejected_qty = 0
		row.stock_qty = flt(row.qty) * flt(row.conversion_factor or 1)
		row.custom_site_rejected_qty = info["rejected_qty"]
		row.custom_site_reject_reason = info["reason"] or None
		if warehouse and not is_project_warehouse(row.warehouse, project):
			row.warehouse = warehouse
		row.project = row.project or project
		rows.append(row)
	doc.set("items", rows)
	if project and doc.meta.has_field("project"):
		doc.project = doc.project or project
	if warehouse and not is_project_warehouse(doc.set_warehouse, project):
		doc.set_warehouse = warehouse
	return doc


def receipt_from_employer_request(name, accepted, warehouse, project):
	from erpnext.stock.doctype.material_request.material_request import make_stock_entry

	doc = make_stock_entry(name)
	rows = []
	for row in doc.items:
		info = accepted.get(row.material_request_item)
		if not info:
			continue
		row.qty = info["qty"]
		row.transfer_qty = flt(row.qty) * flt(row.conversion_factor or 1)
		row.custom_site_rejected_qty = info["rejected_qty"]
		row.custom_site_reject_reason = info["reason"] or None
		if not row.t_warehouse:
			row.t_warehouse = warehouse
		rows.append(row)
	doc.set("items", rows)
	doc.project = project
	doc.posting_date, doc.posting_time = nowdate(), nowtime()
	return doc


# ---------------------------------------------------------------- รับของ: ประวัติ


@frappe.whitelist()
def get_receipt_history(project, days=HISTORY_DAYS):
	check_project(project)
	since = add_days(nowdate(), -cint(days))
	out = []
	if frappe.has_permission("Purchase Receipt", "read"):
		docs = frappe.get_list(
			"Purchase Receipt",
			filters={"docstatus": 1, "posting_date": (">=", since), "is_return": 0},
			or_filters=[["project", "=", project], ["Purchase Receipt Item", "project", "=", project]],
			fields=["name", "supplier_name", "posting_date", "posting_time", "supplier_delivery_note"],
			order_by="posting_date desc, posting_time desc",
			limit_page_length=100,
			distinct=True,
		)
		out += history_rows(docs, "Purchase Receipt", "Purchase Receipt Item", "supplier_name", "supplier_delivery_note")
	if frappe.has_permission("Stock Entry", "read"):
		docs = frappe.get_list(
			"Stock Entry",
			filters={"docstatus": 1, "purpose": "Material Receipt", "project": project, "posting_date": (">=", since)},
			fields=["name", "custom_delivered_by", "posting_date", "posting_time", "custom_supplier_delivery_note"],
			order_by="posting_date desc, posting_time desc",
			limit_page_length=100,
		)
		out += history_rows(
			docs, "Stock Entry", "Stock Entry Detail", "custom_delivered_by", "custom_supplier_delivery_note"
		)
	return sorted(out, key=lambda r: (str(r["date"]), str(r["time"])), reverse=True)


def history_rows(docs, doctype, child, party_field, note_field):
	if not docs:
		return []
	items = frappe.get_all(
		child,
		filters={"parent": ("in", [d.name for d in docs]), "parenttype": doctype},
		fields=["parent", "item_code", "item_name", "custom_site_rejected_qty"],
		order_by="idx",
	)
	codes = item_images(r.item_code for r in items)
	out = []
	for doc in docs:
		rows = [r for r in items if r.parent == doc.name]
		employer = any((codes.get(r.item_code) or {}).get("custom_base_item") for r in rows)
		out.append(
			{
				"doctype": doctype,
				"name": doc.name,
				"party": doc.get(party_field) or "",
				"date": doc.posting_date,
				"time": hhmm(doc.posting_time),
				"delivery_note": doc.get(note_field),
				"items": preview(r.item_name for r in rows),
				"rejected": any(flt(r.custom_site_rejected_qty) for r in rows),
				"employer": doctype == "Stock Entry" or employer,
			}
		)
	return out


@frappe.whitelist()
def get_receipt(doctype, name):
	"""รายละเอียดใบรับของที่รับแล้ว (PR / Stock Entry)"""
	if doctype not in ("Purchase Receipt", "Stock Entry"):
		frappe.throw(_("ไม่รองรับ {0}").format(doctype))
	doc = frappe.get_doc(doctype, name)
	doc.check_permission("read")
	images = item_images(r.item_code for r in doc.items)
	is_pr = doctype == "Purchase Receipt"
	files = frappe.get_all(
		"File",
		filters={"attached_to_doctype": doctype, "attached_to_name": name},
		fields=["file_url", "file_name"],
	)
	return {
		"doctype": doctype,
		"name": name,
		"party": doc.supplier_name if is_pr else (doc.get("custom_delivered_by") or ""),
		"date": doc.posting_date,
		"time": hhmm(doc.posting_time),
		"delivery_note": doc.supplier_delivery_note if is_pr else doc.get("custom_supplier_delivery_note"),
		"delivered_by": doc.transporter_name if is_pr else doc.get("custom_delivered_by"),
		"vehicle_no": doc.lr_no if is_pr else doc.get("custom_vehicle_no"),
		"remarks": doc.remarks,
		"source": next(
			(r.purchase_order if is_pr else r.material_request for r in doc.items if (r.purchase_order if is_pr else r.material_request)),
			None,
		),
		"owner": frappe.utils.get_fullname(doc.owner),
		"items": [
			{
				"item_name": r.item_name,
				"qty": flt(r.qty),
				"uom": r.uom,
				"rejected_qty": flt(r.get("custom_site_rejected_qty")),
				"reason": r.get("custom_site_reject_reason"),
				"image": (images.get(r.item_code) or {}).get("image"),
			}
			for r in doc.items
		],
		"files": [f for f in files if f.file_url],
	}


# ---------------------------------------------------------------- คลัง / เบิก


@frappe.whitelist()
def get_stock(project):
	from consbiz.consbiz.doctype.construction_management.stock import stock_items

	info = check_project(project)
	frappe.has_permission("Stock Entry", "read", throw=True)
	stock = stock_items(project)
	images = item_images(r["item_code"] for r in stock["items"])
	rows = []
	for r in stock["items"]:
		rows.append(
			{
				"item_code": r["item_code"],
				"item_name": r["item_name"],
				"uom": r["stock_uom"],
				"balance": flt(r["balance"]),
				"company": flt(r["company"]["balance"]),
				"employer": flt(r["employer"]["balance"]),
				"received": flt(r["company"]["qty_in"]) + flt(r["employer"]["qty_in"]),
				"used": flt(r["used"]),
				"pending": flt(r["company"]["pending"]) + flt(r["employer"]["pending"]),
				"need": flt(r["need"]),
				"image": (images.get(r["item_code"]) or {}).get("image"),
			}
		)
	return {
		"company": info.company,
		"warehouse": project_warehouse(project),
		"warehouses": [w.name for w in stock.warehouses],
		"items": rows,
	}


@frappe.whitelist()
def get_wbs(project):
	cm = construction_management_of(project)
	return get_task_options(cm) if cm else []


@frappe.whitelist(methods=["POST"])
def submit_issue(project, items, issued_to=None, remarks=None):
	"""เบิกวัสดุ items: [{item_code, qty, wbs}] (Item หลัก ระบบแยกตัดวัสดุผู้ว่าจ้างให้)"""
	info = check_project(project)
	warehouse = project_warehouse(project)
	if not warehouse:
		frappe.throw(_("โครงการนี้ยังไม่มีคลัง"))
	items = [r for r in parse(items) if flt(r.get("qty")) > 0]
	if not items:
		frappe.throw(_("เลือกวัสดุที่จะเบิกอย่างน้อย 1 รายการ"))

	doc = frappe.new_doc("Stock Entry")
	doc.purpose = doc.stock_entry_type = "Material Issue"
	doc.company = info.company
	doc.project = project
	doc.from_warehouse = warehouse
	doc.remarks = "\n".join(filter(None, [issued_to and _("ผู้เบิก: {0}").format(issued_to), remarks])) or None
	for r in items:
		doc.append(
			"items",
			{
				"item_code": r["item_code"],
				"qty": flt(r["qty"]),
				"s_warehouse": warehouse,
				"project": project,
				"custom_wbs": (r.get("wbs") or "").strip() or None,
			},
		)
	doc.insert()
	doc.submit()
	return {"name": doc.name}


@frappe.whitelist()
def get_issue_history(project, days=HISTORY_DAYS):
	check_project(project)
	if not frappe.has_permission("Stock Entry", "read"):
		return []
	docs = frappe.get_list(
		"Stock Entry",
		filters={
			"docstatus": 1,
			"purpose": "Material Issue",
			"project": project,
			"posting_date": (">=", add_days(nowdate(), -cint(days))),
		},
		fields=["name", "posting_date", "posting_time", "remarks", "owner"],
		order_by="posting_date desc, posting_time desc",
		limit_page_length=100,
	)
	if not docs:
		return []
	# ใบเบิกอุปกรณ์จากการยืม (Equipment Borrowing) ไม่นับเป็นการเบิกวัสดุ
	items = frappe.get_all(
		"Stock Entry Detail",
		filters={"parent": ("in", [d.name for d in docs]), "parenttype": "Stock Entry"},
		fields=["parent", "item_name", "qty", "uom", "custom_wbs", "custom_task_name"],
		order_by="idx",
	)
	out = []
	for doc in docs:
		if (doc.remarks or "").startswith(_("Equipment Borrowing")):
			continue
		rows = [r for r in items if r.parent == doc.name]
		out.append(
			{
				"name": doc.name,
				"date": doc.posting_date,
				"time": hhmm(doc.posting_time),
				"remarks": doc.remarks,
				"owner": frappe.utils.get_fullname(doc.owner),
				"items": [
					{"item_name": r.item_name, "qty": flt(r.qty), "uom": r.uom, "wbs": r.custom_wbs, "task": r.custom_task_name}
					for r in rows
				],
			}
		)
	return out


# ---------------------------------------------------------------- คอนกรีต


@frappe.whitelist()
def get_concrete(project):
	check_project(project)
	cm = construction_management_of(project)
	if not cm or not frappe.has_permission("Concrete Usage", "read"):
		return {"construction_management": cm, "docs": []}
	docs = frappe.get_list(
		"Concrete Usage",
		filters={"construction_management": cm, "docstatus": ("<", 2)},
		fields=[
			"name",
			"date",
			"wbs",
			"task_name",
			"location",
			"strength",
			"total_qty",
			"ticket_count",
			"employer_qty",
			"planned_qty",
			"docstatus",
			"supplier",
		],
		order_by="date desc, creation desc",
		limit_page_length=100,
	)
	return {"construction_management": cm, "docs": docs}


@frappe.whitelist()
def get_concrete_setup(project):
	check_project(project)
	cm = construction_management_of(project)
	recent = frappe.get_list(
		"Concrete Usage",
		filters={"docstatus": ("<", 2)},
		fields=["concrete_item", "strength", "supplier"],
		order_by="creation desc",
		limit_page_length=50,
	)
	codes = list(dict.fromkeys(r.concrete_item for r in recent if r.concrete_item))
	names = item_images(codes)
	suppliers = list(dict.fromkeys(r.supplier for r in recent if r.supplier))
	return {
		"construction_management": cm,
		"wbs": get_task_options(cm) if cm else [],
		"items": [{"value": c, "label": (names.get(c) or {}).get("item_name") or c} for c in codes[:12]],
		"suppliers": [
			{"value": s, "label": frappe.db.get_value("Supplier", s, "supplier_name") or s} for s in suppliers[:8]
		],
	}


@frappe.whitelist()
def get_concrete_doc(name):
	doc = frappe.get_doc("Concrete Usage", name)
	doc.check_permission("read")
	out = doc.as_dict(no_default_fields=True)
	out["can_write"] = bool(doc.has_permission("write"))
	out["can_delete"] = can_delete(doc)
	out["concrete_item_name"] = frappe.db.get_value("Item", doc.concrete_item, "item_name")
	out["supplier_name"] = doc.supplier and frappe.db.get_value("Supplier", doc.supplier, "supplier_name")
	out["docstatus"] = doc.docstatus
	out["name"] = doc.name
	return out


@frappe.whitelist(methods=["POST"])
def delete_concrete(name):
	delete_document(frappe.get_doc("Concrete Usage", name))


CONCRETE_FIELDS = ("wbs", "location", "date", "concrete_item", "strength", "supplier", "employer_supplied", "planned_qty", "remarks")
TICKET_FIELDS = ("ticket_no", "vehicle_no", "arrive_time", "finish_time", "qty", "slump", "samples", "employer_supplied", "remarks")


@frappe.whitelist(methods=["POST"])
def save_concrete(project, data, submit=0):
	"""บันทึก/แก้ร่าง Concrete Usage แล้ว Submit ถ้า submit=1"""
	check_project(project)
	data = parse(data)
	cm = construction_management_of(project)
	if not cm:
		frappe.throw(_("โครงการนี้ยังไม่มีแผนงาน (Construction Management)"))
	if data.get("name"):
		doc = frappe.get_doc("Concrete Usage", data["name"])
		if doc.docstatus != 0:
			frappe.throw(_("ใบนี้ Submit แล้ว แก้ไม่ได้"))
	else:
		doc = frappe.new_doc("Concrete Usage")
		doc.construction_management = cm
	for f in CONCRETE_FIELDS:
		if f in data:
			doc.set(f, data[f])
	doc.set("tickets", [])
	for t in data.get("tickets") or []:
		doc.append("tickets", {f: t.get(f) for f in TICKET_FIELDS if f in t})
	doc.save()
	if cint(submit):
		doc.submit()
	return {"name": doc.name, "docstatus": doc.docstatus}


# ---------------------------------------------------------------- ยืม-คืน


@frappe.whitelist()
def get_borrowings(project):
	check_project(project)
	if not frappe.has_permission("Equipment Borrowing", "read"):
		return {"outstanding": [], "returned": []}
	returned = frappe.get_list(
		"Equipment Borrowing",
		filters={"project": project, "docstatus": 1, "status": "Returned"},
		fields=["name", "borrower_name", "date", "due_date", "status", "modified"],
		order_by="modified desc",
		limit_page_length=30,
	)
	return {"outstanding": get_outstanding(project), "returned": returned}


@frappe.whitelist()
def get_borrow_setup(project):
	info = check_project(project)
	source = project_warehouse(project)
	last = frappe.get_list(
		"Equipment Borrowing",
		filters={"company": info.company, "docstatus": ("<", 2)},
		fields=["loan_warehouse"],
		order_by="creation desc",
		limit_page_length=1,
	)
	loan = last[0].loan_warehouse if last else None
	if not loan:
		loan = frappe.db.get_value(
			"Warehouse",
			{"company": info.company, "is_group": 0, "disabled": 0, "warehouse_name": ("like", "%ยืม%")},
			"name",
		)
	warehouses = frappe.get_list(
		"Warehouse",
		filters={"company": info.company, "is_group": 0, "disabled": 0},
		fields=["name", "warehouse_name"],
		order_by="warehouse_name",
		limit_page_length=200,
	)
	return {
		"company": info.company,
		"source_warehouse": source,
		"loan_warehouse": loan,
		"warehouses": [{"value": w.name, "label": w.warehouse_name} for w in warehouses],
		"items": warehouse_items(source),
	}


@frappe.whitelist()
def warehouse_items(warehouse):
	if not warehouse:
		return []
	frappe.has_permission("Warehouse", "read", warehouse, throw=True)
	bins = frappe.get_all(
		"Bin",
		filters={"warehouse": warehouse, "actual_qty": (">", 0)},
		fields=["item_code", "actual_qty"],
	)
	info = item_images(b.item_code for b in bins)
	return sorted(
		[
			{
				"item_code": b.item_code,
				"item_name": (info.get(b.item_code) or {}).get("item_name") or b.item_code,
				"uom": (info.get(b.item_code) or {}).get("stock_uom"),
				"qty": flt(b.actual_qty),
				"image": (info.get(b.item_code) or {}).get("image"),
			}
			for b in bins
			if not (info.get(b.item_code) or {}).get("custom_base_item")
		],
		key=lambda r: r["item_name"].lower(),
	)


BORROW_FIELDS = (
	"borrower_type",
	"employee",
	"worker_name",
	"supplier",
	"contact",
	"due_date",
	"source_warehouse",
	"loan_warehouse",
	"borrower_signature",
	"photo",
	"remarks",
)


@frappe.whitelist(methods=["POST"])
def submit_borrowing(project, data):
	info = check_project(project)
	data = parse(data)
	doc = frappe.new_doc("Equipment Borrowing")
	doc.company = info.company
	doc.project = project
	doc.date = nowdate()
	doc.issued_by = frappe.session.user
	for f in BORROW_FIELDS:
		if data.get(f) not in (None, ""):
			doc.set(f, data[f])
	for r in data.get("items") or []:
		if flt(r.get("qty")) > 0:
			doc.append("items", {"item_code": r["item_code"], "qty": flt(r["qty"]), "condition": r.get("condition")})
	doc.insert()
	doc.submit()
	return {"name": doc.name}


@frappe.whitelist()
def get_borrowing(name):
	doc = frappe.get_doc("Equipment Borrowing", name)
	doc.check_permission("read")
	return {
		"name": doc.name,
		"borrower_name": doc.borrower_name,
		"borrower_type": doc.borrower_type,
		"date": doc.date,
		"due_date": doc.due_date,
		"status": doc.status,
		"can_return": bool(doc.docstatus == 1 and doc.has_permission("write")),
		"overdue": bool(doc.due_date and getdate(doc.due_date) < getdate(nowdate()) and doc.status != "Returned"),
		"items": [
			{
				"item_code": r.item_code,
				"item_name": r.item_name,
				"uom": r.uom,
				"qty": flt(r.qty),
				"returned_qty": flt(r.returned_qty),
				"lost_qty": flt(r.lost_qty),
				"outstanding_qty": flt(r.outstanding_qty),
			}
			for r in doc.items
		],
		"returns": [
			{
				"date": r.date,
				"item_code": r.item_code,
				"qty": flt(r.qty),
				"condition": r.condition,
				"returned_by": r.returned_by,
			}
			for r in doc.returns
		],
	}


# ---------------------------------------------------------------- ค้นหา


SEARCH = {
	"Employee": {"label": "employee_name", "filters": {"status": "Active"}},
	"Supplier": {"label": "supplier_name", "filters": {"disabled": 0}},
	"Item": {"label": "item_name", "filters": {"disabled": 0, "has_variants": 0}},
	"UOM": {"label": "uom_name", "filters": {"enabled": 1}},
}


@frappe.whitelist()
def search(doctype, txt=""):
	cfg = SEARCH.get(doctype)
	if not cfg:
		frappe.throw(_("ค้นหา {0} ไม่ได้").format(doctype))
	txt = (txt or "").strip()
	or_filters = [["name", "like", f"%{txt}%"], [cfg["label"], "like", f"%{txt}%"]] if txt else None
	rows = frappe.get_list(
		doctype,
		filters=cfg["filters"],
		or_filters=or_filters,
		fields=["name", f"{cfg['label']} as label"],
		order_by="modified desc",
		limit_page_length=30,
	)
	return [{"value": r.name, "label": r.label or r.name} for r in rows]
