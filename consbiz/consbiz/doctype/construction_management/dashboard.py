# Copyright (c) 2026, Siricons and contributors
# For license information, please see license.txt

# ข้อมูล Tab "ภาพรวม" และ "เอกสารโครงการ" ในฟอร์ม Construction Management (Vue: public/js/project_dashboard)
# ภาพรวม: ความคืบหน้า/ล่าช้า (delay.py), S-Curve รายเดือน, EVM (evm.py เฉพาะผู้ที่เห็นงบต้นทุน),
#   VO, EOT, QC, วัสดุ, เงินประกันผลงาน และปฏิทินหน้างาน (Daily Report / Daily Request รายวัน)
# เอกสารโครงการ: เอกสารที่อ้างแผนงานนี้ แยกตามกลุ่ม พร้อมจำนวน สถานะ และฉบับล่าสุด

import frappe
from frappe import _
from frappe.query_builder.functions import Count
from frappe.utils import add_days, add_months, flt, getdate, nowdate

from consbiz.consbiz.doctype.construction_management.construction_management import (
	EXTENSION_OF_TIME,
	VARIATION_ORDER,
	actual_progress_at,
	floor_period,
	get_holiday_dates,
	next_period,
	target_progress,
)
from consbiz.consbiz.doctype.construction_management.delay import STATUS, analyse, penalty_warning
from consbiz.consbiz.doctype.construction_management.evm import evm_series

MATERIAL_DUE_DAYS = 14
WORST_TASKS = 8
LATE_STATUSES = ("behind", "not_started", "overdue")


@frappe.whitelist()
def get_dashboard(name, date=None):
	doc = frappe.get_doc("Construction Management", name)
	doc.check_permission("read")
	day = getdate(date or nowdate())
	delay = analyse(doc, day)
	tasks = delay["tasks"]
	summary = delay["summary"]
	plan, basis = target_progress(doc, day)
	counts = {}
	for task in tasks:
		counts[task.status] = counts.get(task.status, 0) + 1
	show_cost = doc.has_permlevel_access_to("budget_cost")
	series = evm_series(doc, day) if show_cost and (doc.start_date or tasks) else []

	return {
		"date": day,
		"currency": frappe.db.get_value("Company", doc.company, "default_currency") if doc.company else None,
		"progress": {"plan": plan, "actual": actual_progress_at(doc, day)[1], "basis": basis},
		"schedule": {
			**summary,
			"start_date": doc.start_date,
			"finish_date": doc.finish_date,
			"extension_days": doc.extension_days,
			"penalty_per_day": doc.penalty_per_day,
			"warning": penalty_warning(summary),
		},
		"tasks": {
			"total": len(tasks),
			"counts": counts,
			"late": sum(counts.get(status, 0) for status in LATE_STATUSES),
			"critical_late": sum(1 for t in tasks if t.critical and t.status in LATE_STATUSES),
			"worst": [
				{
					"wbs": t.wbs,
					"item_name": t.item_name,
					"status": t.status,
					"status_label": _(STATUS[t.status][0]),
					"status_color": STATUS[t.status][1],
					"delay_days": t.delay_days,
					"critical": t.critical,
					"actual_pct": t.actual_pct,
					"plan_pct": t.plan_pct,
				}
				for t in sorted(
					(t for t in tasks if t.status != "done" and (t.delay_days > 0 or t.status in LATE_STATUSES)),
					key=lambda t: (-t.delay_days, t.variance),
				)[:WORST_TASKS]
			],
		},
		# S-Curve รายเดือนให้ทุกคน (แผนถึงวันจบ 100%) มูลค่า (PV/EV/AC) เฉพาะผู้ที่เห็นงบต้นทุน
		"curve": progress_curve(doc, day),
		"evm": evm_values(series) if show_cost and series else None,
		"contract": {
			"total_amount": doc.total_amount,
			"revised_amount": doc.revised_amount,
			"variation_amount": doc.variation_amount,
			**pending(VARIATION_ORDER, doc.name, "net_amount"),
		},
		"extensions": pending(EXTENSION_OF_TIME, doc.name, "requested_days"),
		"quality": quality(doc.name),
		"materials": materials(doc.name, day),
		"retention": retention(doc.project),
	}


def progress_curve(doc, day):
	"""S-Curve ของ Tab ภาพรวม: % แผน (Baseline ถ้ามี) ตั้งแต่วันเริ่มถึงวันจบของแผน (ครบ 100%)
	และ % จริงถึงวันที่ดู (หลังจากนั้น None) จุด = วันเริ่ม + สิ้นเดือน + วันที่ดู + วันจบของแผน"""
	tasks = [row for row in doc.tasks if not row.is_group]
	starts = [getdate(d) for row in tasks for d in (row.start_date, row.baseline_start_date) if d]
	ends = [getdate(d) for row in tasks for d in (row.end_date, row.baseline_end_date) if d]
	start = getdate(doc.start_date) if doc.start_date else min(starts, default=None)
	if not start:
		return []
	finishes = [getdate(d) for d in (doc.finish_date, doc.revised_finish_date) if d]
	# วันที่ดูเลยวันจบของแผน (งานล่าช้า) ขยายแกนถึงวันที่ดู ให้เห็นเส้นจริงจนถึงวันนั้น
	end = max([*ends, *finishes, start, day])
	points = {start, day} if day >= start else {start}
	period = floor_period(start, "month")
	while period <= end:
		points.add(max(min(getdate(add_days(next_period(period, "month"), -1)), end), start))
		period = next_period(period, "month")
	return [
		{
			"date": point,
			"plan": target_progress(doc, point)[0],
			"actual": actual_progress_at(doc, point)[1] if point <= day else None,
		}
		for point in sorted(points)
	]


def evm_values(series):
	last = series[-1]
	return {
		**{k: last[k] for k in ("bac", "pv", "ev", "ac", "spi", "cpi", "eac", "vac")},
		"series": [{"date": row.date, "pv": row.pv, "ev": row.ev, "ac": row.ac} for row in series],
	}


def pending(doctype, name, field):
	"""จำนวนเอกสารที่ Submit แล้วแต่ผู้ว่าจ้างยังไม่อนุมัติ และผลรวมของ field"""
	rows = frappe.get_all(
		doctype,
		filters={"construction_management": name, "docstatus": 1, "employer_status": "Pending"},
		pluck=field,
	)
	return {"pending_count": len(rows), "pending_total": sum(flt(v) for v in rows)}


def quality(name):
	inspection = frappe.qb.DocType("Inspection Request")
	by_result = dict(
		frappe.qb.from_(inspection)
		.select(inspection.result, Count("*"))
		.where((inspection.construction_management == name) & (inspection.docstatus == 1))
		.groupby(inspection.result)
		.run()
	)
	open_items = sum(
		flt(v)
		for v in frappe.get_all(
			"Punch List",
			filters={"construction_management": name, "docstatus": 1, "status": "Open"},
			pluck="open_items",
		)
	)
	return {
		"pending": by_result.get("Pending", 0),
		"failed": by_result.get("Failed", 0),
		"passed": by_result.get("Passed", 0) + by_result.get("Passed with Comments", 0),
		"punch_open": int(open_items),
	}


def materials(name, day):
	"""วัสดุที่ยังขอซื้อ/ขอลูกค้าไม่ครบ (เทียบปริมาณรวมของโครงการ): เลยวันที่ต้องสั่งแล้ว และต้องสั่งภายใน MATERIAL_DUE_DAYS วัน"""
	from consbiz.consbiz.doctype.construction_material_plan.construction_material_plan import is_done, plan_coverage

	if not frappe.db.exists("Construction Material Plan", name):
		return None
	plan = frappe.get_doc("Construction Material Plan", name)
	limit = getdate(add_days(day, MATERIAL_DUE_DAYS))
	coverage, _supply = plan_coverage(plan)
	rows = [
		getdate(row.order_by)
		for row in plan.items
		if row.order_by and getdate(row.order_by) <= limit and not is_done(coverage[row.name])
	]
	late = sum(1 for order_by in rows if order_by < day)
	return {"late": late, "due": len(rows) - late, "days": MATERIAL_DUE_DAYS}


def retention(project):
	"""เงินประกันผลงานที่ยังไม่ได้รับคืน (Retention Receivable สถานะ Active / Overdue) ของ Project"""
	if not project or not frappe.has_permission("Retention Receivable", "read"):
		return None
	rows = frappe.get_all(
		"Retention Receivable",
		filters={"project": project, "docstatus": 1, "status": ("in", ("Active", "Overdue"))},
		fields=["grand_total", "status"],
	)
	return {
		"outstanding": sum(flt(r.grand_total) for r in rows),
		"overdue": sum(flt(r.grand_total) for r in rows if r.status == "Overdue"),
	}


# ---------- ปฏิทินหน้างาน ----------


@frappe.whitelist()
def get_site_calendar(name, month):
	"""Daily Report / Daily Request รายวันของเดือน (month = วันใดก็ได้ในเดือน) พร้อมวันหยุดและสรุปของเดือน
	วันที่ขาดรายงาน = วันทำงาน (ไม่ใช่วันหยุด) ตั้งแต่วันเริ่มสัญญาถึงวันนี้ที่ยังไม่มี Daily Report ที่ Submit แล้ว"""
	doc = frappe.get_doc("Construction Management", name)
	doc.check_permission("read")
	start = getdate(month).replace(day=1)
	end = getdate(add_days(add_months(start, 1), -1))
	between = ("between", (start, end))
	reports = frappe.get_all(
		"Daily Report",
		filters={"construction_management": name, "date": between, "docstatus": ("<", 2)},
		fields=[
			"name",
			"date",
			"docstatus",
			"today_progress",
			"cumulative_progress",
			"progress_variance",
			"weather",
			"problems",
			"daily_request",
			"owner",
		],
		order_by="date asc, creation asc",
	)
	requests = frappe.get_all(
		"Daily Request",
		filters={"construction_management": name, "date": between, "docstatus": ("<", 2)},
		fields=["name", "date", "docstatus", "status", "expected_progress", "requested_by", "owner"],
		order_by="date asc, creation asc",
	)
	holidays = {getdate(d) for d in get_holiday_dates(doc.holiday_list)}
	today = getdate(nowdate())
	submitted = {getdate(r.date) for r in reports if r.docstatus == 1}
	first = max(start, getdate(doc.start_date)) if doc.start_date else start
	last = min(end, today)
	days = (getdate(add_days(first, n)) for n in range((last - first).days + 1))
	missing = [day for day in days if day not in holidays and day not in submitted]
	return {
		"start": start,
		"end": end,
		"today": today,
		"contract_start": doc.start_date,
		"contract_finish": doc.revised_finish_date or doc.finish_date,
		"holidays": sorted(d for d in holidays if start <= d <= end),
		"reports": reports,
		"requests": requests,
		"summary": {
			"report_days": len(submitted),
			"missing_days": len(missing),
			"progress": sum(flt(r.today_progress) for r in reports if r.docstatus == 1),
			"requests": len(requests),
		},
		"can_create_report": frappe.has_permission("Daily Report", "create"),
		"can_create_request": frappe.has_permission("Daily Request", "create"),
	}


# ---------- เอกสารโครงการ ----------

# กลุ่ม -> [(doctype, ช่องสถานะ, ช่องชื่อเรื่อง, ช่องวันที่)] ช่องสถานะ None = ใช้ docstatus
DOCUMENT_GROUPS = (
	(
		"แผนงาน",
		(
			("Construction Baseline", None, "title", "baseline_date"),
			("Construction Resource Plan", None, None, None),
			("Construction Material Plan", None, None, None),
		),
	),
	(
		"หน้างาน",
		(
			("Daily Request", "status", None, "date"),
			("Daily Report", None, None, "date"),
		),
	),
	(
		"สัญญาและการเปลี่ยนแปลง",
		(
			("Variation Order", "employer_status", "title", "date"),
			("Extension of Time", "employer_status", "title", "date"),
		),
	),
	(
		"คุณภาพ",
		(
			("Inspection Request", "result", "title", "request_date"),
			("Punch List", "status", "title", "date"),
		),
	),
)
# ชื่อที่แสดง (ตรงกับเมนู Sidebar)
DOCUMENT_LABELS = {
	"Construction Baseline": "Baseline",
	"Construction Resource Plan": "แผนทรัพยากร",
	"Construction Material Plan": "แผนจัดซื้อวัสดุ",
	"Daily Request": "ขออนุมัติปฏิบัติงาน",
	"Daily Report": "รายงานประจำวัน",
	"Variation Order": "งานลด-งานเพิ่ม",
	"Extension of Time": "ขยายระยะเวลา (EOT)",
	"Inspection Request": "ขอตรวจงาน",
	"Punch List": "Punch List",
}
# เอกสารที่มีได้ฉบับเดียวต่อแผนงาน (ชื่อเดียวกับแผนงาน)
SINGLE_DOCUMENTS = ("Construction Resource Plan", "Construction Material Plan")
# ทำเองในหน้า Gantt ไม่มีปุ่มสร้าง
NO_CREATE = ("Construction Baseline",)
RECENT_DOCUMENTS = 3

REPORTS = (
	("Construction Delay Analysis", "วิเคราะห์ความล่าช้า", "งานที่ช้ากว่าแผน งานวิกฤต วันเสร็จที่คาดการณ์ และค่าปรับ"),
	("Construction Earned Value", "Earned Value", "PV / EV / AC รายช่วง SPI CPI และต้นทุนที่คาดว่าจะใช้"),
	("Construction Resource Histogram", "แผนทรัพยากรเทียบที่ใช้จริง", "แรงงานและเครื่องจักรตามแผนเทียบกับ Daily Report"),
)


@frappe.whitelist()
def get_documents(name):
	frappe.get_doc("Construction Management", name).check_permission("read")
	groups = []
	for label, doctypes in DOCUMENT_GROUPS:
		items = [document_summary(name, *config) for config in doctypes if frappe.has_permission(config[0], "read")]
		if items:
			groups.append({"label": _(label), "items": items})
	reports = [
		{"name": report, "label": _(label), "description": _(description)}
		for report, label, description in REPORTS
		if frappe.has_permission("Report", "read") and report_allowed(report)
	]
	return {"groups": groups, "reports": reports}


def document_summary(name, doctype, status_field, title_field, date_field):
	filters = {"construction_management": name}
	meta = frappe.get_meta(doctype)
	if meta.is_submittable:
		filters["docstatus"] = ("<", 2)
	fields = ["name", "docstatus"] + [f for f in (status_field, title_field, date_field) if f]
	recent = frappe.get_all(
		doctype,
		filters=filters,
		fields=fields,
		order_by=f"{date_field or 'modified'} desc, creation desc",
		limit=RECENT_DOCUMENTS,
	)
	return {
		"doctype": doctype,
		"label": _(DOCUMENT_LABELS.get(doctype, doctype)),
		"submittable": meta.is_submittable,
		"count": frappe.db.count(doctype, filters),
		"drafts": frappe.db.count(doctype, {**filters, "docstatus": 0}) if meta.is_submittable else 0,
		"single": doctype in SINGLE_DOCUMENTS,
		"can_create": doctype not in NO_CREATE and frappe.has_permission(doctype, "create"),
		"recent": [
			{
				"name": row.name,
				"title": row.get(title_field) if title_field else None,
				"date": row.get(date_field) if date_field else None,
				"docstatus": row.docstatus,
				"status": row.get(status_field) if status_field else None,
			}
			for row in recent
		],
	}


def report_allowed(report):
	roles = set(frappe.get_roles())
	allowed = set(frappe.get_all("Has Role", filters={"parent": report, "parenttype": "Report"}, pluck="role"))
	return not allowed or bool(roles & allowed)
