# Copyright (c) 2026, Siricons and contributors
# For license information, please see license.txt

# ข้อมูล Tab "Look-ahead" ของ Construction Management (Vue: public/js/project_dashboard/LookAhead.vue)
# - ช่วงเวลา: เริ่มวันจันทร์ของสัปดาห์ที่มีวันที่เลือก (รวมสัปดาห์ที่แล้วได้) ยาว weeks สัปดาห์
# - งานที่แสดง: งานย่อยที่มีวันทำงานตามแผนปัจจุบันในช่วงนั้น และงานที่ควรเสร็จก่อนช่วงแต่ยังไม่เสร็จ
# - วันที่มีแผน = วันทำงานของงาน (ไม่นับวันหยุดเมื่อแผนนับวันทำงาน) วันที่ทำจริง = วันที่มี Construction Progress Entry
#   work = ปริมาณ/% ที่ทำต่อวันพร้อมเอกสารอ้างอิง, finished_on = วันที่ความคืบหน้าสะสมครบ 100%
#   หน้าจอแบ่งเป็นกล่องรายวันแล้วใส่สีตามสถานะของวัน (ทำแล้ว / ไม่ได้ทำตามแผน / วันนี้ / แผนข้างหน้า / ทำนอกแผน / เสร็จแล้ว)
# - สถานะ/% แผน เทียบกับแผนปัจจุบัน (Look-ahead ใช้วางงานข้างหน้าตามแผนล่าสุด ไม่ใช่ Baseline)
# - หมายเหตุ: ทรัพยากรจาก Construction Resource Plan และขอตรวจงานที่ยังรอผลหรือไม่ผ่าน

import datetime

import frappe
from frappe import _
from frappe.utils import add_days, cint, flt, getdate, nowdate

from consbiz.consbiz.doctype.construction_management.construction_management import (
	PROGRESS_ENTRY,
	TOLERANCE,
	get_holiday_dates,
	total_float,
	working_days_of,
)
from consbiz.consbiz.doctype.construction_management.delay import (
	STATUS,
	actual_by_task,
	task_plan_percent,
	task_status,
)

MAX_WEEKS = 8


@frappe.whitelist()
def get_lookahead(name, date=None, weeks=3, include_last_week=1):
	doc = frappe.get_doc("Construction Management", name)
	doc.check_permission("read")
	day = getdate(date or nowdate())
	weeks = min(max(cint(weeks), 1), MAX_WEEKS)
	monday = day - datetime.timedelta(days=day.weekday())
	start = add_days(monday, -7) if cint(include_last_week) else monday
	start = getdate(start)
	end = getdate(add_days(monday, weeks * 7 - 1))

	all_holidays = {getdate(d) for d in get_holiday_dates(doc.holiday_list)}
	holidays = all_holidays if doc.use_working_days else set()
	progress = actual_by_task(doc.name, day)
	done_days, work, finished = work_days(doc.name, start, end)
	floats = total_float(doc.tasks, holidays)
	resources = task_resources(doc.name)
	inspections = open_inspections(doc.name)

	groups, current = [], None
	for row in doc.tasks:
		if row.is_group:
			if not row.indent:
				current = {"wbs": row.wbs, "label": row.item_name, "tasks": []}
				groups.append(current)
			continue
		if not row.start_date or not row.end_date:
			continue
		task_start, task_end = getdate(row.start_date), getdate(row.end_date)
		actual = progress.get(row.name, {}).get("percent", 0)
		overdue = task_end < start and actual < 100 - TOLERANCE
		if not overdue and (task_end < start or task_start > end):
			continue
		plan = task_plan_percent(row, day, holidays, baseline=False)
		status = task_status(task_start, task_end, day, plan, actual)
		if current is None:
			current = {"wbs": "", "label": _("งานอื่นๆ"), "tasks": []}
			groups.append(current)
		current["tasks"].append(
			{
				"name": row.name,
				"wbs": row.wbs,
				"item_name": row.item_name,
				"start_date": task_start,
				"end_date": task_end,
				"days": [d for d in working_days_of(task_start, task_end, holidays) if start <= d <= end],
				"uom": row.uom,
				"done_days": sorted(done_days.get(row.name, ())),
				"work": work.get(row.name, {}),
				"finished_on": finished.get(row.name),
				"plan_pct": plan,
				"actual_pct": actual,
				"status": status,
				"status_label": _(STATUS[status][0]),
				"status_color": STATUS[status][1],
				"overdue": overdue,
				"critical": floats.get(row.name, 1) <= 0,
				"resources": resources.get(row.name, []),
				"inspections": inspections.get(row.name, []),
			}
		)

	return {
		"date": day,
		"today": getdate(nowdate()),
		"start": start,
		"end": end,
		"this_week": monday,
		"holidays": sorted(d for d in all_holidays if start <= d <= end),
		"groups": [group for group in groups if group["tasks"]],
	}


def work_days(name, start, end):
	"""ความคืบหน้าจริงของแต่ละงาน (ทุกรายการถึงวัน end)
	คืน ({task: {วันที่ในช่วง}}, {task: {"YYYY-MM-DD": {qty, percent, refs}}} ในช่วง, {task: วันที่สะสมครบ 100%})"""
	days, work, finished, totals = {}, {}, {}, {}
	for entry in frappe.get_all(
		PROGRESS_ENTRY,
		filters={"construction_management": name, "date": ("<=", end)},
		fields=["task", "date", "qty", "percent", "reference_name"],
		order_by="date asc, creation asc",
	):
		day = getdate(entry.date)
		totals[entry.task] = totals.get(entry.task, 0) + flt(entry.percent)
		if entry.task not in finished and totals[entry.task] >= 100 - TOLERANCE:
			finished[entry.task] = day
		if day < start:
			continue
		days.setdefault(entry.task, set()).add(day)
		cell = work.setdefault(entry.task, {}).setdefault(str(day), {"qty": 0, "percent": 0, "refs": []})
		cell["qty"] += flt(entry.qty)
		cell["percent"] += flt(entry.percent)
		if entry.reference_name and entry.reference_name not in cell["refs"]:
			cell["refs"].append(entry.reference_name)
	return days, work, finished


def task_resources(name):
	"""{task: ["คนงาน 4", ...]} จากแผนทรัพยากร (จำนวนต่อวัน)"""
	if not frappe.db.exists("Construction Resource Plan", name):
		return {}
	result = {}
	for item in frappe.get_all(
		"Construction Resource Plan Item",
		filters={"parent": name, "parenttype": "Construction Resource Plan"},
		fields=["task", "resource", "qty_per_day"],
		order_by="idx",
	):
		qty = item.qty_per_day
		result.setdefault(item.task, []).append(f"{item.resource} {int(qty) if qty == int(qty) else qty}")
	return result


def open_inspections(name):
	"""{task: [{name, result}]} ขอตรวจงานที่ยังรอผลหรือตรวจไม่ผ่าน"""
	result = {}
	for row in frappe.get_all(
		"Inspection Request",
		filters={"construction_management": name, "docstatus": 1, "result": ("in", ("Pending", "Failed"))},
		fields=["name", "task", "result"],
	):
		result.setdefault(row.task, []).append({"name": row.name, "result": row.result})
	return result
