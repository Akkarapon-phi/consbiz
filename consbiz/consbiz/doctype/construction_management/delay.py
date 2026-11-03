# Copyright (c) 2026, Siricons and contributors
# For license information, please see license.txt

# วิเคราะห์ความล่าช้าของแผนงาน ณ วันที่หนึ่ง (ใช้ในรายงาน Construction Delay Analysis และหัวหน้า Gantt)
# - % แผนของงาน: Baseline ถ้าตั้งไว้แล้ว ไม่งั้นแผนปัจจุบัน (เหมือน target_progress)
# - คาดการณ์วันเสร็จ (forecast) จากความคืบหน้าจริง:
#   เสร็จแล้ว = วันที่ลงความคืบหน้าครั้งสุดท้าย, กำลังทำ = งานที่เหลือใช้เวลาตามอัตราในแผน นับจากวันถัดไป
#   ยังไม่เริ่ม = เริ่มตามแผนหรือวันถัดไปถ้าเลยวันเริ่มแล้ว และไม่ก่อนที่งานก่อนหน้า (forecast) ยอม
# - ล่าช้า (วัน) = วันเสร็จที่คาด - วันจบตามแผนที่ใช้เทียบ (วันปฏิทิน)
# - ค่าปรับ = วันที่เลยวันสิ้นสุดสัญญาปรับปรุง (รวม EOT) × ค่าปรับรายวัน ส่งมอบแล้วใช้วันส่งมอบจริง

import math

import frappe
from frappe import _
from frappe.utils import cint, date_diff, flt, getdate

from consbiz.consbiz.doctype.construction_management.construction_management import (
	PROGRESS_ENTRY,
	TOLERANCE,
	add_working_days,
	dependency_order,
	link_start,
	shift_working_days,
	task_daily,
	total_float,
)

# สถานะ -> (ข้อความ, สี indicator)
STATUS = {
	"done": ("เสร็จแล้ว", "green"),
	"not_due": ("ยังไม่ถึงกำหนด", "gray"),
	"on_track": ("ตามแผนหรือเร็วกว่าแผน", "blue"),
	"behind": ("ช้ากว่าแผน", "orange"),
	"not_started": ("ควรเริ่มแล้วแต่ยังไม่เริ่ม", "red"),
	"overdue": ("ควรเสร็จแล้วแต่ยังไม่เสร็จ", "red"),
}


def analyse(doc, date):
	"""คืน {"tasks": [แถวงานย่อยที่มีวันที่], "summary": {...}} ณ สิ้นวัน date"""
	day = getdate(date)
	holidays = doc.get_holidays() if doc.use_working_days else set()
	baseline = any(row.baseline_start_date for row in doc.tasks)
	progress = actual_by_task(doc.name, day)
	floats = total_float(doc.tasks, holidays)
	forecast = forecast_dates(doc, day, progress, holidays)

	tasks = []
	for row in doc.tasks:
		if row.is_group or row.name not in forecast:
			continue
		start, end = target_dates(row, baseline)
		actual = progress.get(row.name, {}).get("percent", 0)
		plan = task_plan_percent(row, day, holidays, baseline)
		forecast_end = forecast[row.name][1]
		tasks.append(
			frappe._dict(
				name=row.name,
				wbs=row.wbs,
				item_name=row.item_name,
				start_date=start,
				end_date=end,
				plan_pct=plan,
				actual_pct=actual,
				variance=actual - plan,
				total_float=floats.get(row.name),
				critical=floats.get(row.name, 1) <= 0,
				status=task_status(start, end, day, plan, actual),
				forecast_end=forecast_end,
				delay_days=max(date_diff(forecast_end, end), 0) if end else 0,
			)
		)
	return {"tasks": tasks, "summary": summarize(doc, day, forecast)}


def target_dates(row, baseline):
	if baseline and row.baseline_start_date:
		return getdate(row.baseline_start_date), getdate(row.baseline_end_date)
	return getdate(row.start_date), getdate(row.end_date)


def task_plan_percent(row, day, holidays, baseline):
	"""% แผนสะสมของงาน ณ สิ้นวัน day (ตรงกับ plan_percent ใน schedule.js)"""
	if baseline and row.baseline_start_date:
		start, end, distribution = row.baseline_start_date, row.baseline_end_date, row.baseline_distribution
	else:
		start, end, distribution = row.start_date, row.end_date, row.plan_distribution
	distribution = frappe.parse_json(distribution) if distribution else None
	return 100 * sum(
		fraction for d, fraction in task_daily(getdate(start), getdate(end), distribution, holidays) if d <= day
	)


def task_status(start, end, day, plan, actual):
	if actual >= 100 - TOLERANCE:
		return "done"
	if start > day:
		return "not_due"
	if actual <= TOLERANCE and plan > TOLERANCE:
		return "overdue" if end < day else "not_started"
	if end < day:
		return "overdue"
	return "on_track" if actual >= plan - TOLERANCE else "behind"


def actual_by_task(name, day):
	"""{task: {"percent", "first", "last"}} จาก Progress Entry ถึงสิ้นวัน day"""
	result = {}
	for entry in frappe.get_all(
		PROGRESS_ENTRY,
		filters={"construction_management": name, "date": ("<=", day)},
		fields=["task", "date", "percent"],
		order_by="date asc",
	):
		item = result.setdefault(entry.task, {"percent": 0, "first": getdate(entry.date), "last": None})
		item["percent"] += flt(entry.percent)
		item["last"] = getdate(entry.date)
	for item in result.values():
		item["percent"] = min(max(item["percent"], 0), 100)
	return result


def forecast_dates(doc, day, progress, holidays):
	"""{task: (วันเริ่ม, วันจบ)} ที่คาดการณ์ ณ สิ้นวัน day ของงานย่อยที่มีวันที่"""
	rows = {row.name: row for row in doc.tasks if not row.is_group and row.name}
	links = {
		name: [
			{"task": link.get("task"), "type": (link.get("type") or "FS").upper(), "lag": cint(link.get("lag"))}
			for link in frappe.parse_json(row.predecessors or "[]") or []
			if link.get("task") in rows
		]
		for name, row in rows.items()
	}
	next_day = shift_working_days(day, 1, holidays)
	forecast = {}
	# แถวสำเนาที่มีวันที่ forecast ให้ link_start คำนวณจากงานก่อนหน้า
	shadow = {}
	for row in dependency_order(doc.tasks, links):
		if not row.start_date or not row.end_date:
			continue
		duration = max(cint(row.duration), 1)
		done = progress.get(row.name)
		percent = done["percent"] if done else 0
		if percent >= 100 - TOLERANCE:
			start, end = done["first"], done["last"]
		elif percent > TOLERANCE:
			start = done["first"]
			end = add_working_days(next_day, math.ceil(duration * (100 - percent) / 100 - TOLERANCE), holidays)
		else:
			start = max(getdate(row.start_date), next_day)
			required = [
				link_start(row, link, shadow, holidays) for link in links[row.name] if link["task"] in shadow
			]
			required = [d for d in required if d]
			if required:
				start = max(start, *required)
			end = add_working_days(start, duration, holidays)
		forecast[row.name] = (start, end)
		shadow[row.name] = frappe._dict(start_date=start, end_date=end, duration=duration)
	return forecast


def summarize(doc, day, forecast):
	contract_finish = getdate(doc.revised_finish_date or doc.finish_date) if doc.finish_date else None
	forecast_finish = max((end for _start, end in forecast.values()), default=None)
	finish = getdate(doc.handover_date) if doc.handover_date else forecast_finish
	overrun = max(date_diff(finish, contract_finish), 0) if finish and contract_finish else 0
	penalty = overrun * flt(doc.penalty_per_day)
	contract = flt(doc.revised_amount) or flt(doc.total_amount)
	return frappe._dict(
		date=day,
		contract_finish=contract_finish,
		forecast_finish=forecast_finish,
		handover_date=getdate(doc.handover_date) if doc.handover_date else None,
		overrun_days=overrun,
		penalty=penalty,
		penalty_percent=penalty / contract * 100 if contract else 0,
		penalty_limit_percent=flt(doc.penalty_limit_percent),
	)


def penalty_warning(summary):
	"""ข้อความเตือนเมื่อค่าปรับเกินเพดาน (สัญญาภาครัฐ: เกิน 10% ต้องพิจารณาบอกเลิกสัญญา)"""
	limit = summary.penalty_limit_percent
	if limit and summary.penalty_percent > limit:
		return _("ค่าปรับคาดการณ์ {0}% เกินเพดาน {1}% ของมูลค่าสัญญา").format(
			flt(summary.penalty_percent, 2), flt(limit, 2)
		)
	return None


def forecast_finish(doc, date=None):
	"""วันเสร็จที่คาดการณ์ของโครงการ ณ วันที่ date (ค่าเริ่มต้นวันนี้) สำหรับหน้า Gantt"""
	day = getdate(date)
	holidays = doc.get_holidays() if doc.use_working_days else set()
	forecast = forecast_dates(doc, day, actual_by_task(doc.name, day), holidays)
	return max((end for _start, end in forecast.values()), default=None)

