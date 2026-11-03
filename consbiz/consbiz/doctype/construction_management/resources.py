# Copyright (c) 2026, Siricons and contributors
# For license information, please see license.txt

"""ทรัพยากร (คน/เครื่องจักร) และวัสดุของแผนงาน ใช้ในหน้า Gantt (แผงด้านขวาของงาน) และ Tab "ทรัพยากร" ของ CM

ข้อมูลเก็บที่ Construction Resource Plan / Construction Material Plan (1 ฉบับต่อ CM ชื่อเดียวกับ CM) ที่เดียว
หน้า Gantt แก้ได้และบันทึกพร้อมแผนงานใน save_tasks (save_plans) ตรวจ modified ของแต่ละแผนกันบันทึกทับ
วันที่ต้องเตรียม (นับวันปฏิทิน ต้องตรงกับ prep_dates ใน public/js/construction_management/schedule.js):
- วัสดุ: ต้องการภายใน = วันเริ่มงาน - buffer_days, ต้องสั่งภายใน = ต้องการภายใน - lead_time_days
- คน/เครื่องจักร: ต้องจองภายใน = วันเริ่มงาน - lead_time_days
"""

import frappe
from frappe import _
from frappe.utils import add_days, cint, date_diff, flt, getdate, nowdate

RESOURCE_PLAN = "Construction Resource Plan"
MATERIAL_PLAN = "Construction Material Plan"
# แจ้งเตือนสิ่งที่ต้องเตรียมภายในกี่วัน (เท่ากับการ์ดวัสดุใน Tab ภาพรวม)
DUE_DAYS = 14

RESOURCE_FIELDS = ("name", "task", "wbs", "resource_type", "resource", "qty_per_day", "lead_time_days", "remarks")
MATERIAL_FIELDS = (
	"name",
	"task",
	"wbs",
	"item_code",
	"qty",
	"uom",
	"lead_time_days",
	"required_by",
	"order_by",
	"material_request",
	"remarks",
)


def plan_permissions(doctype, name):
	"""(อ่านได้, แก้ได้) ของแผนนี้ ยังไม่มีเอกสาร: แก้ได้ = สร้างได้"""
	if frappe.db.exists(doctype, name):
		return frappe.has_permission(doctype, "read", name), frappe.has_permission(doctype, "write", name)
	return frappe.has_permission(doctype, "read"), frappe.has_permission(doctype, "create")


def get_plans(name):
	"""แผนทรัพยากรและแผนวัสดุของ CM สำหรับหน้า Gantt (ไม่มีสิทธิ์อ่าน = None)"""
	return {"resource_plan": resource_plan_data(name), "material_plan": material_plan_data(name)}


def resource_plan_data(name):
	from consbiz.consbiz.doctype.daily_report.daily_report import get_default_resources

	can_read, can_write = plan_permissions(RESOURCE_PLAN, name)
	if not can_read:
		return None
	doc = frappe.get_doc(RESOURCE_PLAN, name) if frappe.db.exists(RESOURCE_PLAN, name) else None
	return {
		"exists": bool(doc),
		"modified": str(doc.modified) if doc else None,
		"can_write": bool(can_write),
		"items": [{f: row.get(f) for f in RESOURCE_FIELDS} for row in doc.items] if doc else [],
		# ชื่อที่หน้างานเคยลงใน Daily Report ตามด้วยรายการมาตรฐาน (ชื่อต้องตรงกันจึงเทียบกับที่ใช้จริงได้)
		"options": get_default_resources("Daily Report", name),
	}


def material_plan_data(name):
	"""แถววัสดุ + ยอดที่ขอ/สั่ง/รับแล้วของโครงการต่อ Item (supply) และตัวคูณหน่วยสต็อกของแถว (factor)
	หน้า Gantt ตัดยอดเอง (allocate_materials ใน schedule.js) เพราะวันที่ต้องการเปลี่ยนตามการลากงาน"""
	from consbiz.consbiz.doctype.construction_material_plan.construction_material_plan import (
		conversion_factors,
		get_supply,
	)

	can_read, can_write = plan_permissions(MATERIAL_PLAN, name)
	if not can_read:
		return None
	doc = frappe.get_doc(MATERIAL_PLAN, name) if frappe.db.exists(MATERIAL_PLAN, name) else None
	items = [{f: row.get(f) for f in MATERIAL_FIELDS} for row in doc.items] if doc else []
	set_item_info(items)
	set_request_status(items)
	factors = conversion_factors(items)
	for row in items:
		row["factor"] = factors.get((row["item_code"], row["uom"]), 1.0)
	project = frappe.db.get_value("Construction Management", name, "project")
	return {
		"project": project,
		"supply": get_supply(project, [row["item_code"] for row in items]),
		"exists": bool(doc),
		"modified": str(doc.modified) if doc else None,
		"can_write": bool(can_write),
		"buffer_days": cint(doc.buffer_days) if doc else cint(frappe.get_meta(MATERIAL_PLAN).get_field("buffer_days").default),
		"items": items,
	}


def set_item_info(items):
	codes = {row["item_code"] for row in items if row.get("item_code")}
	if not codes:
		return
	info = {
		r.name: r
		for r in frappe.get_all(
			"Item", filters={"name": ("in", list(codes))}, fields=["name", "item_name", "stock_uom", "is_customer_provided_item"]
		)
	}
	for row in items:
		item = info.get(row.get("item_code")) or frappe._dict()
		row["item_label"] = item.item_name or row.get("item_code")
		row["stock_uom"] = item.stock_uom
		row["customer_provided"] = cint(item.is_customer_provided_item)


def set_request_status(items):
	"""สถานะ Material Request ที่สร้างจากแถว (ร่าง/Submit/ยกเลิก)"""
	requests = {row["material_request"] for row in items if row.get("material_request")}
	if not requests:
		return
	status = {
		r.name: r
		for r in frappe.get_all(
			"Material Request", filters={"name": ("in", list(requests))}, fields=["name", "docstatus", "status"]
		)
	}
	for row in items:
		request = status.get(row.get("material_request"))
		if request:
			row["request_docstatus"] = request.docstatus
			row["request_status"] = request.status


def plan_versions(name):
	"""modified ของแผนทั้งสอง (ส่วนหนึ่งของ schedule_version: แก้แผนจากฟอร์มแล้วหน้า Gantt โหลดใหม่)"""
	return "|".join(str(frappe.db.get_value(doctype, name, "modified") or "") for doctype in (RESOURCE_PLAN, MATERIAL_PLAN))


# ---------- บันทึกจากหน้า Gantt ----------


def check_plans(name, resources=None, materials=None):
	"""ตรวจก่อนบันทึกแผนงาน: สิทธิ์ และแผนต้องไม่ถูกแก้จากที่อื่นหลังจากเปิดหน้า Gantt"""
	for doctype, payload in ((RESOURCE_PLAN, resources), (MATERIAL_PLAN, materials)):
		if payload is None:
			continue
		_can_read, can_write = plan_permissions(doctype, name)
		if not can_write:
			frappe.throw(_("ไม่มีสิทธิ์แก้ {0}").format(_(doctype)), frappe.PermissionError)
		current = frappe.db.get_value(doctype, name, "modified")
		if str(current or "") != str(payload.get("modified") or ""):
			frappe.throw(
				_("{0} ถูกแก้ไขหลังจากที่คุณเปิด กรุณาโหลดหน้าใหม่").format(_(doctype)),
				frappe.TimestampMismatchError,
			)


def save_plans(name, resources=None, materials=None):
	"""บันทึกรายการทั้งชุดจากหน้า Gantt (เรียกหลังบันทึกแผนงาน วันที่ของงานจึงเป็นค่าใหม่แล้ว)
	resources / materials: {modified, items: [...]} None = ไม่ได้แก้
	แถวที่มี name เดิมแก้ในที่ แถวใหม่เพิ่มต่อท้าย แถวที่ไม่ส่งมาถูกลบ
	(สถานะการสั่งวัสดุคิดจากปริมาณรวมของโครงการ จึงแก้/ลบแถวที่เคยสร้าง MR ได้ ช่อง material_request คงไว้อ้างอิง)"""
	if resources is not None:
		save_items(name, RESOURCE_PLAN, resources.get("items") or [], ("resource_type", "resource", "qty_per_day", "lead_time_days", "remarks"))
	if materials is not None:
		save_items(name, MATERIAL_PLAN, materials.get("items") or [], ("item_code", "qty", "uom", "lead_time_days", "remarks"))


def save_items(name, doctype, items, fields):
	if frappe.db.exists(doctype, name):
		doc = frappe.get_doc(doctype, name)
	else:
		if not items:
			return
		doc = frappe.new_doc(doctype)
		doc.construction_management = name
	existing = {row.name: row for row in doc.items}
	rows = []
	for item in items:
		row = existing.pop(item.get("name"), None)
		values = {"wbs": item.get("wbs"), **{f: item.get(f) for f in fields}}
		if row:
			row.update(values)
			rows.append(row)
		else:
			rows.append(values)
	doc.set("items", rows)
	doc.save()


# ---------- Tab "ทรัพยากร" ของ CM ----------


@frappe.whitelist()
def get_overview(name, day=None):
	"""ข้อมูลของ Tab ทรัพยากร: วัสดุที่ต้องสั่ง, คน/เครื่องจักรที่ต้องจอง และกราฟคน-วันรายสัปดาห์ (แผนเทียบจริง)"""
	from consbiz.consbiz.doctype.daily_report.daily_report import get_leaf_tasks

	doc = frappe.get_doc("Construction Management", name)
	doc.check_permission("read")
	day = getdate(day or nowdate())
	holidays = doc.get_holidays() if doc.use_working_days else set()
	tasks = get_leaf_tasks(name)
	by_task = {task.name: task for task in tasks.values()}
	plans = get_plans(name)
	return {
		"date": str(day),
		"due_days": DUE_DAYS,
		"materials": material_rows(plans["material_plan"], by_task, day),
		"supply": supply_rows(plans["material_plan"]),
		"material_plan": plan_info(plans["material_plan"]),
		"resources": resource_rows(plans["resource_plan"], by_task, day, holidays),
		"resource_plan": plan_info(plans["resource_plan"]),
		"can_request": bool(
			plans["material_plan"]
			and plans["material_plan"]["exists"]
			and plans["material_plan"]["can_write"]
			and frappe.has_permission("Material Request", "create")
		),
		"chart": resource_chart(name, by_task) if plans["resource_plan"] else None,
	}


def supply_rows(plan):
	"""สรุปต่อ Item: ต้องใช้ทั้งหมด เทียบขอ/สั่งซื้อ/รับแล้ว แยกซื้อเอง/ลูกค้าจัดหา (หน่วยสต็อก)"""
	if not plan:
		return []
	need = {}
	for item in plan["items"]:
		row = need.setdefault(
			item["item_code"],
			{"item_code": item["item_code"], "item_label": item.get("item_label"), "stock_uom": item.get("stock_uom"), "need": 0.0},
		)
		row["need"] += flt(item["qty"]) * flt(item.get("factor") or 1)
	result = []
	for code, row in need.items():
		supply = plan["supply"].get(code) or {}
		result.append({**row, **{key: supply.get(key) for key in ("purchase", "customer", "total")}})
	return sorted(result, key=lambda r: r["item_label"] or r["item_code"])


def plan_info(plan):
	if not plan:
		return None
	return {key: plan.get(key) for key in ("exists", "can_write", "buffer_days") if key in plan}


def prep_status(target, day, done=False):
	"""สถานะของสิ่งที่ต้องเตรียม: done / late (เลยกำหนด) / due (ภายใน DUE_DAYS วัน) / later"""
	if done:
		return "done"
	if not target:
		return None
	days = date_diff(target, day)
	return "late" if days < 0 else "due" if days <= DUE_DAYS else "later"


def material_rows(plan, by_task, day):
	"""แถววัสดุพร้อมยอดที่ตัดได้ (หน่วยของแถว) coverage = {requested, ordered, received, state}"""
	from consbiz.consbiz.doctype.construction_material_plan.construction_material_plan import allocate, is_done

	if not plan:
		return []
	rows = []
	for item in plan["items"]:
		task = by_task.get(item["task"])
		start = task and task.start_date
		required_by = add_days(start, -cint(plan["buffer_days"])) if start else None
		order_by = add_days(required_by, -cint(item.get("lead_time_days"))) if required_by else None
		rows.append(
			{
				**item,
				"key": item["name"],
				"stock_qty": flt(item["qty"]) * flt(item.get("factor") or 1),
				"item_name": task.item_name if task else "",
				"start_date": start,
				"required_by": required_by,
				"order_by": order_by,
				"days_left": date_diff(order_by, day) if order_by else None,
			}
		)
	coverage = allocate(rows, plan["supply"])
	for row in rows:
		cov = coverage[row["key"]]
		factor = flt(row.get("factor") or 1)
		row["coverage"] = {**{stage: cov[stage] / factor for stage in ("requested", "ordered", "received")}, "state": cov["state"]}
		row["status"] = prep_status(row["order_by"], day, is_done(cov))
	return sorted(rows, key=lambda r: (r["status"] == "done", str(r["order_by"] or "9999"), r["wbs"] or ""))


def resource_rows(plan, by_task, day, holidays):
	"""รวมตามชนิด + ชื่อทรัพยากร: ช่วงที่ใช้, จำนวนสูงสุดต่อวัน, วันรวม และวันต้องจองของงานถัดไปที่ยังไม่เริ่ม"""
	if not plan:
		return []
	groups = {}
	for item in plan["items"]:
		task = by_task.get(item["task"])
		key = (item["resource_type"], item["resource"])
		group = groups.setdefault(
			key,
			{
				"resource_type": item["resource_type"],
				"resource": item["resource"],
				"tasks": [],
				"start_date": None,
				"end_date": None,
				"peak": 0,
				"total": 0,
				"book_by": None,
				"next_task": None,
			},
		)
		group["tasks"].append(
			{
				"wbs": item["wbs"],
				"item_name": task.item_name if task else "",
				"qty_per_day": flt(item["qty_per_day"]),
				"start_date": task and task.start_date,
				"end_date": task and task.end_date,
			}
		)
		if not task or not task.start_date or not task.end_date:
			continue
		start, end = getdate(task.start_date), getdate(task.end_date)
		group["start_date"] = min(filter(None, (group["start_date"], start)))
		group["end_date"] = max(filter(None, (group["end_date"], end)))
		# งานที่ยังไม่เริ่มเท่านั้นที่ต้องจอง
		if start > day:
			book_by = add_days(start, -cint(item.get("lead_time_days")))
			if not group["book_by"] or getdate(book_by) < getdate(group["book_by"]):
				group["book_by"] = book_by
				group["next_task"] = item["wbs"]

	daily = planned_daily(plan, by_task, holidays)
	for (resource_type, resource), group in groups.items():
		days = [qty for (t, r, _d), qty in daily.items() if t == resource_type and r == resource]
		group["peak"] = max(days, default=0)
		group["total"] = sum(days)
		group["days_left"] = date_diff(group["book_by"], day) if group["book_by"] else None
		group["status"] = prep_status(group["book_by"], day)
		group["tasks"].sort(key=lambda t: str(t["start_date"] or "9999"))
	return sorted(
		groups.values(),
		key=lambda g: (g["book_by"] is None, str(g["book_by"] or ""), g["resource_type"], g["resource"]),
	)


def planned_daily(plan, by_task, holidays):
	"""{(ชนิด, ทรัพยากร, วัน): จำนวน} ตามวันทำงานของงาน (เหมือน planned_resources แต่ทุกวันของแผน)"""
	from consbiz.consbiz.doctype.construction_management.construction_management import working_days_of

	result = {}
	for item in plan["items"]:
		task = by_task.get(item["task"])
		if not task or not task.start_date or not task.end_date:
			continue
		for day in working_days_of(getdate(task.start_date), getdate(task.end_date), holidays):
			key = (item["resource_type"], item["resource"], day)
			result[key] = result.get(key, 0) + flt(item["qty_per_day"])
	return result


def resource_chart(name, by_task):
	"""คน-วัน / คัน-วัน รายสัปดาห์ตลอดแผน: แผน (แรงงาน, เครื่องจักร) เทียบใช้จริงจาก Daily Report"""
	from consbiz.consbiz.doctype.construction_management.construction_management import floor_period
	from consbiz.consbiz.doctype.construction_resource_plan.construction_resource_plan import (
		actual_resources,
		planned_resources,
	)

	days = [getdate(d) for task in by_task.values() for d in (task.start_date, task.end_date) if d]
	if not days:
		return None
	start, end = min(days), max(days)
	planned = planned_resources(name, start, end)
	actual = actual_resources(name, start, end)
	weeks = {}
	for source, values in (("planned", planned), ("actual", actual)):
		for (resource_type, _resource, day), qty in values.items():
			week = weeks.setdefault(floor_period(day, "week"), {})
			key = f"{source}_{resource_type}"
			week[key] = week.get(key, 0) + flt(qty)
	periods = sorted(weeks)
	series = (
		("planned_Labour", _("แรงงานตามแผน")),
		("actual_Labour", _("แรงงานใช้จริง")),
		("planned_Equipment", _("เครื่องจักรตามแผน")),
		("actual_Equipment", _("เครื่องจักรใช้จริง")),
	)
	return {
		"labels": [frappe.format(period, "Date") for period in periods],
		"datasets": [
			{"name": label, "key": key, "values": [flt(weeks[p].get(key, 0), 1) for p in periods]}
			for key, label in series
		],
	}
