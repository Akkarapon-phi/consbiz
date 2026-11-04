# Copyright (c) 2026, Siricons and contributors
# For license information, please see license.txt

"""คลังวัสดุของโครงการ ใช้ใน Tab "คลังวัสดุ" ของ CM และรายงาน Project Stock Summary (ข้อมูลชุดเดียวกัน)

- คลังของโครงการ = Warehouse ที่ custom_project = โครงการ (+ คลังของแผนวัสดุ) คลังผู้ว่าจ้าง = custom_is_owner_warehouse
- 1 แถวต่อ Item หลัก: Item คู่ของผู้ว่าจ้างจัดหา (custom_base_item) รวมเข้า Item หลัก แยกเป็นส่วนบริษัท / ผู้ว่าจ้าง
  - เข้า / ออก / คงเหลือ: Stock Ledger Entry ของคลังโครงการ (โอนระหว่างคลังของโครงการนับทั้งเข้าและออก)
  - ขอ / สั่งซื้อ / รับ: get_supply ของแผนวัสดุ (MR รวมฉบับร่าง / PO / รับของ ที่ระบุโครงการ) ยังไม่ส่ง = สั่งแล้ว - รับแล้ว
  - ต้องใช้ตามแผน: แผนวัสดุ (หน่วยสต็อก)
- ใช้ต่องาน: Stock Entry ประเภท Material Issue ที่ระบุ WBS (custom_wbs) เทียบแผนวัสดุของงานนั้น
- PO ค้างส่ง: รายการ PO ของโครงการที่ยังรับไม่ครบ เลยวันที่ต้องได้รับ = เลยกำหนด
หน่วยเป็นหน่วยสต็อกทั้งหมด
"""

import frappe
from frappe.query_builder import Case
from frappe.query_builder.functions import Sum
from frappe.utils import add_days, date_diff, flt, getdate, nowdate

MATERIAL_PLAN = "Construction Material Plan"
SOURCES = ("company", "employer")
# รับของล่าสุดย้อนหลังกี่วัน
RECENT_DAYS = 30
EPSILON = 1e-9


@frappe.whitelist()
def get_overview(name):
	"""ข้อมูลของ Tab คลังวัสดุ"""
	doc = frappe.get_doc("Construction Management", name)
	doc.check_permission("read")
	return project_stock(doc.project, doc.company, name)


def project_stock(project, company, construction_management=None):
	if not project:
		return {"project": None, "warehouses": [], "items": [], "usage": [], "late_orders": [], "deliveries": []}
	stock = stock_items(project, construction_management)
	return {
		"project": project,
		"company": company,
		"warehouses": [{"name": w.name, "owner": w.owner} for w in stock.warehouses],
		"items": stock["items"],
		"usage": usage_rows(project, stock.info, stock.plan_rows),
		"late_orders": open_orders(project),
		"deliveries": recent_deliveries(project, company),
	}


def stock_items(project, construction_management=None):
	"""วัสดุต่อ Item หลักของโครงการ (ใช้ทั้ง Tab และรายงาน) แผนวัสดุ = ของ CM ที่ระบุ ไม่ระบุ = CM ของโครงการ"""
	from consbiz.site_stock import construction_management_of

	construction_management = construction_management or construction_management_of(project)
	plan = (
		frappe.get_doc(MATERIAL_PLAN, construction_management)
		if construction_management and frappe.db.exists(MATERIAL_PLAN, construction_management)
		else None
	)
	warehouses = project_warehouses(project, plan)
	owners = {w.name for w in warehouses if w.owner}
	plan_rows = plan_stock_rows(plan)
	ledger = ledger_totals([w.name for w in warehouses])
	codes = {row.item_code for row in ledger} | {row["item_code"] for row in plan_rows} | project_item_codes(project)
	info = item_info(codes)
	return frappe._dict(
		warehouses=warehouses,
		plan_rows=plan_rows,
		info=info,
		items=item_rows(project, info, ledger, owners, plan_rows),
	)


def project_warehouses(project, plan=None):
	rows = frappe.get_all(
		"Warehouse",
		filters={"custom_project": project, "is_group": 0},
		fields=["name", "custom_is_owner_warehouse as owner"],
		order_by="name",
	)
	if plan and plan.warehouse and plan.warehouse not in {row.name for row in rows}:
		owner = frappe.db.get_value("Warehouse", plan.warehouse, "custom_is_owner_warehouse")
		rows.append(frappe._dict(name=plan.warehouse, owner=owner))
	for row in rows:
		row.owner = bool(row.owner)
	return rows


def ledger_totals(warehouses):
	"""[{item_code, warehouse, qty_in, qty_out, balance}] จาก Stock Ledger Entry ที่ไม่ยกเลิก"""
	if not warehouses:
		return []
	sle = frappe.qb.DocType("Stock Ledger Entry")
	positive = Case().when(sle.actual_qty > 0, sle.actual_qty).else_(0)
	negative = Case().when(sle.actual_qty < 0, -sle.actual_qty).else_(0)
	return (
		frappe.qb.from_(sle)
		.select(
			sle.item_code,
			sle.warehouse,
			Sum(positive).as_("qty_in"),
			Sum(negative).as_("qty_out"),
			Sum(sle.actual_qty).as_("balance"),
		)
		.where((sle.is_cancelled == 0) & sle.warehouse.isin(warehouses))
		.groupby(sle.item_code, sle.warehouse)
		.run(as_dict=True)
	)


def project_item_codes(project):
	"""Item ที่มี MR / PO ของโครงการ (มีแต่ยังไม่ได้รับเข้าคลังก็ต้องแสดง)"""
	mr = frappe.qb.DocType("Material Request")
	mri = frappe.qb.DocType("Material Request Item")
	requested = (
		frappe.qb.from_(mri)
		.join(mr)
		.on(mri.parent == mr.name)
		.select(mri.item_code)
		.distinct()
		.where(
			(mr.docstatus < 2)
			& mr.material_request_type.isin(("Purchase", "Customer Provided"))
			& ((mr.custom_project == project) | (mri.project == project))
		)
		.run(pluck=True)
	)
	poi = frappe.qb.DocType("Purchase Order Item")
	po = frappe.qb.DocType("Purchase Order")
	ordered = (
		frappe.qb.from_(poi)
		.join(po)
		.on(poi.parent == po.name)
		.select(poi.item_code)
		.distinct()
		.where((po.docstatus == 1) & ((po.project == project) | (poi.project == project)))
		.run(pluck=True)
	)
	return set(requested) | set(ordered)


def item_info(codes):
	"""{item_code: {item_name, stock_uom, base (Item หลัก), employer (เป็นของผู้ว่าจ้างจัดหา)}}"""
	codes = [code for code in codes if code]
	if not codes:
		return {}
	rows = frappe.get_all(
		"Item",
		filters={"name": ("in", codes)},
		fields=["name", "item_name", "stock_uom", "custom_base_item", "is_customer_provided_item"],
	)
	bases = {row.custom_base_item for row in rows if row.custom_base_item} - set(codes)
	base_names = (
		dict(frappe.get_all("Item", filters={"name": ("in", list(bases))}, fields=["name", "item_name"], as_list=True))
		if bases
		else {}
	)
	names = {row.name: row.item_name for row in rows} | base_names
	return {
		row.name: frappe._dict(
			item_name=names.get(row.custom_base_item or row.name),
			stock_uom=row.stock_uom,
			base=row.custom_base_item or row.name,
			employer=bool(row.is_customer_provided_item),
		)
		for row in rows
	}


def plan_stock_rows(plan):
	"""แถวแผนวัสดุในหน่วยสต็อก [{item_code, wbs, task_name, stock_qty}] (item_name ของแถวแผน = ชื่องาน)"""
	if not plan:
		return []
	from consbiz.consbiz.doctype.construction_material_plan.construction_material_plan import conversion_factors

	factors = conversion_factors([row.as_dict() for row in plan.items])
	return [
		{
			"item_code": row.item_code,
			"wbs": row.wbs,
			"task_name": row.item_name,
			"stock_qty": flt(row.qty) * factors.get((row.item_code, row.uom), 1.0),
		}
		for row in plan.items
	]


def empty_source():
	return {"requested": 0.0, "ordered": 0.0, "received": 0.0, "pending": 0.0, "qty_in": 0.0, "qty_out": 0.0, "balance": 0.0}


def item_rows(project, info, ledger, owners, plan_rows):
	from consbiz.consbiz.doctype.construction_material_plan.construction_material_plan import get_supply

	rows = {}

	def row_of(code):
		item = info.get(code) or frappe._dict(item_name=code, stock_uom=None, base=code, employer=False)
		base = info.get(item.base) or item
		return rows.setdefault(
			item.base,
			{
				"item_code": item.base,
				"item_name": item.item_name,
				"stock_uom": base.stock_uom or item.stock_uom,
				"need": 0.0,
				**{source: empty_source() for source in SOURCES},
			},
		), item

	for entry in ledger:
		row, item = row_of(entry.item_code)
		source = row["employer" if item.employer or entry.warehouse in owners else "company"]
		for key in ("qty_in", "qty_out", "balance"):
			source[key] += flt(entry[key])

	for supply_code, supply in get_supply(project, list(info)).items():
		row, _item = row_of(supply_code)
		for key in ("requested", "ordered", "received"):
			row["company"][key] += supply["purchase"][key]
			row["employer"][key] += supply["customer"][key]

	for plan_row in plan_rows:
		row, _item = row_of(plan_row["item_code"])
		row["need"] += plan_row["stock_qty"]

	for row in rows.values():
		for source in SOURCES:
			values = row[source]
			values["pending"] = max(values["ordered"] - values["received"], 0)
		row["balance"] = row["company"]["balance"] + row["employer"]["balance"]
		row["used"] = row["company"]["qty_out"] + row["employer"]["qty_out"]
		row["short"] = max(row["need"] - row["company"]["requested"] - row["employer"]["requested"], 0)
	return sorted(rows.values(), key=lambda row: (row["item_name"] or row["item_code"]).lower())


def usage_rows(project, info, plan_rows):
	"""ต่อ (WBS, Item หลัก): ตามแผน เทียบเบิกใช้จริงจาก Stock Entry Material Issue ที่ระบุ WBS"""
	se = frappe.qb.DocType("Stock Entry")
	sed = frappe.qb.DocType("Stock Entry Detail")
	issued = (
		frappe.qb.from_(sed)
		.join(se)
		.on(sed.parent == se.name)
		.select(sed.custom_wbs.as_("wbs"), sed.custom_task_name.as_("task_name"), sed.item_code, Sum(sed.transfer_qty).as_("qty"))
		.where(
			(se.docstatus == 1)
			& (se.purpose == "Material Issue")
			& ((se.project == project) | (sed.project == project))
			& sed.custom_wbs.isnotnull()
			& (sed.custom_wbs != "")
		)
		.groupby(sed.custom_wbs, sed.custom_task_name, sed.item_code)
		.run(as_dict=True)
	)
	missing = {row.item_code for row in issued} - set(info)
	if missing:
		info = {**info, **item_info(missing)}

	rows = {}

	def row_of(wbs, code):
		item = info.get(code) or frappe._dict(item_name=code, stock_uom=None, base=code)
		return rows.setdefault(
			(wbs, item.base),
			{"wbs": wbs, "task_name": None, "item_code": item.base, "item_name": item.item_name, "stock_uom": item.stock_uom, "planned": 0.0, "used": 0.0},
		)

	for plan_row in plan_rows:
		row = row_of(plan_row["wbs"], plan_row["item_code"])
		row["planned"] += plan_row["stock_qty"]
		row["task_name"] = row["task_name"] or plan_row["task_name"]
	for entry in issued:
		row = row_of(entry.wbs, entry.item_code)
		row["used"] += flt(entry.qty)
		row["task_name"] = row["task_name"] or entry.task_name
	for row in rows.values():
		row["variance"] = row["used"] - row["planned"]
	return sorted(rows.values(), key=lambda row: (wbs_key(row["wbs"]), row["item_name"] or ""))


def wbs_key(wbs):
	return [int(part) if part.isdigit() else part for part in str(wbs or "").split(".")]


def open_orders(project):
	"""รายการ PO ของโครงการที่ยังรับไม่ครบ (หน่วยสต็อก) เรียงตามวันที่ต้องได้รับ"""
	po = frappe.qb.DocType("Purchase Order")
	poi = frappe.qb.DocType("Purchase Order Item")
	rows = (
		frappe.qb.from_(poi)
		.join(po)
		.on(poi.parent == po.name)
		.select(
			po.name.as_("purchase_order"),
			po.supplier_name,
			poi.item_code,
			poi.item_name,
			poi.stock_uom,
			poi.stock_qty,
			poi.received_qty,
			poi.conversion_factor,
			poi.schedule_date,
		)
		.where(
			(po.docstatus == 1)
			& po.status.notin(("Closed", "On Hold", "Completed"))
			& ((po.project == project) | (poi.project == project))
		)
		.orderby(poi.schedule_date)
		.run(as_dict=True)
	)
	today = getdate(nowdate())
	result = []
	for row in rows:
		pending = flt(row.stock_qty) - flt(row.received_qty) * flt(row.conversion_factor or 1)
		if pending <= EPSILON:
			continue
		row.pending_qty = pending
		row.days_late = max(date_diff(today, row.schedule_date), 0) if row.schedule_date else 0
		result.append(row)
	return result


def recent_deliveries(project, company, days=RECENT_DAYS):
	"""รับของ RECENT_DAYS วันล่าสุด (ข้อมูลเดียวกับรายงาน Site Delivery Summary) ใหม่สุดก่อน"""
	from consbiz.consbiz.report.site_delivery_summary.site_delivery_summary import get_data

	if not company:
		return []
	today = nowdate()
	rows = get_data(frappe._dict(company=company, project=project, from_date=add_days(today, -days), to_date=today))
	return list(reversed(rows))
