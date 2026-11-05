# Copyright (c) 2026, Siricons and contributors
# For license information, please see license.txt

"""แอปหน้างาน (/site, www/site.html + public/js/site_app/) แอปเดียวแบ่งเป็นหมวดงาน สลับในแอป

- store (สโตร์): รับของ / เบิก / ยืม-คืน / คลัง  API อยู่ที่ consbiz/store_app.py
- buy (จัดซื้อ) / sell (ขาย): consbiz/site_docs.py
- pm (บริหารโครงการ): ภาพรวมสัญญา/ความล่าช้า, แผนงาน (Gantt ดูอย่างเดียว), Look-ahead, เอกสารโครงการ
  ข้อมูลชุดเดียวกับ Tab ของ Construction Management (dashboard.py / lookahead.py) แก้แผนที่หน้า Gantt ในระบบเต็ม
- work (ควบคุมงาน): โฟร์แมน/วิศวกร ความคืบหน้า + S-Curve, ปฏิทินรายงานประจำวัน, บันทึกคอนกรีต (API ที่ store_app.py),
  กรอก/ส่ง Daily Report และขอ/อนุมัติ Daily Request ในแอป (ทีละขั้น), ดูขอตรวจงาน / Punch List
  API อยู่ในไฟล์นี้ (ขอตรวจงาน / Punch List สร้างในระบบเต็ม)
หมวดที่ผู้ใช้เห็น = หมวดที่มีสิทธิ์อ่าน/สร้างเอกสารอย่างน้อย 1 ชนิด (SECTIONS) ทุก API ยังตรวจสิทธิ์ของเอกสารเอง
"""

import frappe
from frappe import _
from frappe.utils import cint, flt, getdate, nowdate

from consbiz import store_app
from consbiz.site_stock import construction_management_of

LIST_LIMIT = 60
LATE_TASKS = 6
WORK_DOCTYPES = ("Daily Report", "Daily Request", "Inspection Request", "Punch List")


def boot_data():
	boot = store_app.boot_data()
	can_work = {doctype: bool(frappe.has_permission(doctype, "read")) for doctype in WORK_DOCTYPES}
	boot["can"].update(
		{
			"daily_report": can_work["Daily Report"],
			"daily_request": can_work["Daily Request"],
			"inspection": can_work["Inspection Request"],
			"punch_list": can_work["Punch List"],
		}
	)
	sections = []
	if any(boot["can"].get(key) for key in ("receive", "receive_employer", "issue", "borrow")):
		sections.append("store")
	if any(can_work.values()) or boot["can"].get("concrete"):
		sections.append("work")
	if frappe.has_permission("Construction Management", "read"):
		sections.append("pm")
	# จัดซื้อ / ขาย (consbiz/site_docs.py)
	if any(frappe.has_permission(d, "read") for d in ("Material Request", "Purchase Order", "Purchase Invoice")):
		sections.append("buy")
	if any(frappe.has_permission(d, "read") for d in ("Quotation", "Sales Order", "Sales Invoice")):
		sections.append("sell")
	boot["sections"] = sections
	boot["desk"] = boot["desk"] or any(can_work.values())
	return boot


def check_project(project):
	info = store_app.check_project(project)
	return info, construction_management_of(project)


def readable(doctype):
	return bool(frappe.has_permission(doctype, "read"))


# ---------------------------------------------------------------- หน้าหลักของหมวดควบคุมงาน


@frappe.whitelist()
def get_work_summary(project):
	info, cm = check_project(project)
	day = getdate(nowdate())
	result = {
		"project": project,
		"project_name": info.project_name,
		"construction_management": cm,
		"progress": None,
		"curve": [],
		"late_tasks": [],
		"late_count": 0,
		"reports_today": 0,
		"report_drafts": 0,
		"requests_pending": 0,
		"requests_ready": [],
		"inspections_pending": 0,
		"inspections_failed": 0,
		"punch_open": 0,
	}
	if not cm:
		return result

	if frappe.has_permission("Construction Management", "read", cm):
		result.update(plan_status(cm, day))

	if readable("Daily Report"):
		result["reports_today"] = len(
			frappe.get_list(
				"Daily Report",
				filters={"construction_management": cm, "date": day, "docstatus": ("<", 2)},
				pluck="name",
				limit_page_length=0,
			)
		)
		result["report_drafts"] = len(
			frappe.get_list(
				"Daily Report",
				filters={"construction_management": cm, "docstatus": 0},
				pluck="name",
				limit_page_length=0,
			)
		)
	if readable("Daily Request"):
		# Daily Request: Draft = รออนุมัติ (Pending) / ไม่อนุมัติ (Rejected), Submit = อนุมัติ
		result["requests_pending"] = len(
			frappe.get_list(
				"Daily Request",
				filters={"construction_management": cm, "docstatus": 0, "status": "Pending"},
				pluck="name",
				limit_page_length=0,
			)
		)
		# อนุมัติแล้ว ยังไม่มี Daily Report (Daily Request สร้าง Daily Report ต่อได้ 1 ฉบับ)
		result["requests_ready"] = frappe.get_list(
			"Daily Request",
			filters={"construction_management": cm, "docstatus": 1, "status": "Approved"},
			fields=["name", "date", "requested_by", "expected_progress"],
			order_by="date asc",
			limit_page_length=5,
		)
	if readable("Inspection Request"):
		for row in frappe.get_list(
			"Inspection Request",
			filters={"construction_management": cm, "docstatus": 1, "result": ("in", ("Pending", "Failed"))},
			fields=["result"],
			limit_page_length=0,
		):
			key = "inspections_pending" if row.result == "Pending" else "inspections_failed"
			result[key] += 1
	if readable("Punch List"):
		result["punch_open"] = sum(
			cint(v)
			for v in frappe.get_list(
				"Punch List",
				filters={"construction_management": cm, "docstatus": 1, "status": "Open"},
				pluck="open_items",
				limit_page_length=0,
			)
		)
	return result


def plan_status(cm, day):
	"""% แผน/จริง ณ วันนี้ และงานที่ช้ากว่าแผน (ชุดเดียวกับ Tab ภาพรวมของ CM)"""
	from consbiz.consbiz.doctype.construction_management.construction_management import (
		actual_progress_at,
		target_progress,
	)
	from consbiz.consbiz.doctype.construction_management.dashboard import LATE_STATUSES, progress_curve
	from consbiz.consbiz.doctype.construction_management.delay import STATUS, analyse

	doc = frappe.get_doc("Construction Management", cm)
	delay = analyse(doc, day)
	plan, basis = target_progress(doc, day)
	late = sorted(
		(t for t in delay["tasks"] if t.status != "done" and (t.delay_days > 0 or t.status in LATE_STATUSES)),
		key=lambda t: (not t.critical, -t.delay_days, t.variance),
	)
	return {
		"curve": progress_curve(doc, day),
		"progress": {
			"plan": flt(plan, 2),
			"actual": flt(actual_progress_at(doc, day)[1], 2),
			"basis": basis,
			"finish_date": doc.revised_finish_date or doc.finish_date,
		},
		"late_count": len(late),
		"late_tasks": [
			{
				"wbs": t.wbs,
				"item_name": t.item_name,
				"status_label": _(STATUS[t.status][0]),
				"delay_days": t.delay_days,
				"critical": t.critical,
				"actual_pct": flt(t.actual_pct, 1),
				"plan_pct": flt(t.plan_pct, 1),
			}
			for t in late[:LATE_TASKS]
		],
	}


# ---------------------------------------------------------------- รายการเอกสาร


# สถานะของแต่ละชนิด → (ป้าย, tone ของแอป)
STATUS_LABELS = {
	"Daily Request": {
		"Pending": ("รออนุมัติ", "amber"),
		"Approved": ("อนุมัติแล้ว", "blue"),
		"Completed": ("ทำรายงานแล้ว", "green"),
		"Rejected": ("ไม่อนุมัติ", "rose"),
	},
	"Inspection Request": {
		"Pending": ("รอตรวจ", "amber"),
		"Passed": ("ผ่าน", "green"),
		"Passed with Comments": ("ผ่าน (มีข้อแนะนำ)", "teal"),
		"Failed": ("ไม่ผ่าน", "rose"),
	},
	"Punch List": {
		"Open": ("ยังแก้ไม่ครบ", "amber"),
		"Closed": ("ปิดแล้ว", "green"),
	},
}


# สถานะมีความหมายตั้งแต่ Draft (Daily Request: Draft = รออนุมัติ / ไม่อนุมัติ)
DRAFT_HAS_STATUS = ("Daily Request",)


def with_status(doctype, rows, status_field=None):
	labels = STATUS_LABELS.get(doctype, {})
	for row in rows:
		if cint(row.docstatus) == 0 and doctype not in DRAFT_HAS_STATUS:
			label, tone = "ร่าง", "gray"
		else:
			label, tone = labels.get(row.get(status_field) if status_field else None, ("ส่งแล้ว", "green"))
		row.status_label, row.status_tone = _(label), tone
	return rows


@frappe.whitelist()
def get_inspections(project, kind="inspection"):
	"""kind = inspection (Inspection Request) / punch (Punch List) ล่าสุดก่อน"""
	_info, cm = check_project(project)
	doctype = "Punch List" if kind == "punch" else "Inspection Request"
	if not cm or not readable(doctype):
		return []
	filters = {"construction_management": cm, "docstatus": ("<", 2)}
	if doctype == "Inspection Request":
		rows = frappe.get_list(
			doctype,
			filters=filters,
			fields=[
				"name",
				"title",
				"wbs",
				"item_name",
				"location",
				"request_date",
				"inspection_date",
				"inspector",
				"result",
				"docstatus",
			],
			order_by="request_date desc, creation desc",
			limit_page_length=LIST_LIMIT,
		)
		return with_status(doctype, rows, "result")
	rows = frappe.get_list(
		doctype,
		filters=filters,
		fields=["name", "title", "date", "status", "open_items", "inspection_request", "docstatus"],
		order_by="date desc, creation desc",
		limit_page_length=LIST_LIMIT,
	)
	return with_status(doctype, rows, "status")


# ---------------------------------------------------------------- ปฏิทินรายงานประจำวัน


@frappe.whitelist()
def get_calendar(project, month):
	"""Daily Report / Daily Request รายวันของเดือน (ชุดเดียวกับปฏิทินหน้างานใน Tab ภาพรวมของ CM)"""
	from consbiz.consbiz.doctype.construction_management.dashboard import get_site_calendar

	_info, cm = check_project(project)
	if not cm:
		return None
	data = get_site_calendar(cm, month)
	with_status("Daily Report", data["reports"])
	with_status("Daily Request", data["requests"], "status")
	for row in data["reports"] + data["requests"]:
		row.owner_name = frappe.utils.get_fullname(row.owner)
	data["construction_management"] = cm
	return data


# ---------------------------------------------------------------- ฟอร์มรายงาน / ขออนุมัติ (กรอกในแอป)

# ช่องที่แอปแก้ได้ (ที่เหลือระบบคำนวณใน validate ของเอกสาร)
FORM_FIELDS = {
	"Daily Report": (
		"date",
		"weather",
		"weather_impact",
		"supervisor_name",
		"problems",
		"remarks",
		"daily_request",
	),
	"Daily Request": (
		"date",
		"requested_by",
		"approver",
		"start_time",
		"end_time",
		"materials",
		"safety_measures",
		"remarks",
	),
}
ITEM_FIELDS = {
	"Daily Report": ("wbs", "qty", "percent", "location", "remarks"),
	"Daily Request": ("wbs", "qty", "percent", "location", "remarks"),
}
# ค่าที่แสดงอย่างเดียว (คำนวณแล้ว)
VIEW_FIELDS = {
	"Daily Report": ("today_progress", "cumulative_progress", "baseline_progress", "progress_variance", "plan_basis"),
	"Daily Request": (
		"status",
		"approver_name",
		"approved_by",
		"approved_on",
		"rejection_reason",
		"planned_progress",
		"current_progress",
		"expected_progress",
		"baseline_progress",
		"progress_variance",
		"plan_basis",
	),
}
ROW_VIEW_FIELDS = ("item_name", "uom", "group_path", "boq_qty", "previous_qty", "previous_percent", "remaining_qty")


def pdf_url(doctype, name):
	"""PDF ของ Print Format ชื่อเดียวกับ DocType ตัวสร้าง PDF เลือกแบบเดียวกับปุ่ม PDF ของหน้าพิมพ์ในระบบเต็ม
	(ของ Print Format ถ้าตั้งไว้ ไม่งั้นของ Print Settings)"""
	from urllib.parse import urlencode

	print_format = doctype if frappe.db.exists("Print Format", doctype) else None
	generator = (
		(print_format and frappe.db.get_value("Print Format", print_format, "pdf_generator"))
		or frappe.db.get_single_value("Print Settings", "pdf_generator")
		or "wkhtmltopdf"
	)
	params = {"doctype": doctype, "name": name, "no_letterhead": 0, "pdf_generator": generator}
	if print_format:
		params["format"] = print_format
	return "/api/method/frappe.utils.print_format.download_pdf?" + urlencode(params)


def check_doctype(doctype):
	if doctype not in FORM_FIELDS:
		frappe.throw(_("ไม่รองรับ {0}").format(doctype))


def hhmmss(value):
	return store_app.hhmm(value) if value else None


def serialize(doc, defaults=None):
	"""เอกสารเป็น dict ของแอป ร่าง: เติมรายชื่อคน/เครื่องจักรตั้งต้นที่ยังไม่มี (จำนวน 0) ให้กรอกแค่จำนวน"""
	data = {"name": doc.name if not doc.is_new() else None, "docstatus": doc.docstatus}
	for field in FORM_FIELDS[doc.doctype] + VIEW_FIELDS[doc.doctype]:
		data[field] = doc.get(field)
	for field in ("start_time", "end_time"):
		if field in data:
			data[field] = hhmmss(data[field])
	data["items"] = [
		{field: row.get(field) for field in ITEM_FIELDS[doc.doctype] + ROW_VIEW_FIELDS + ("project_percent",)}
		for row in doc.items
	]
	labour = [{"role": r.role, "qty": cint(r.qty), "remarks": r.remarks} for r in doc.labour]
	equipment = [
		{"equipment": r.equipment, "qty": cint(r.qty), "hours": flt(r.hours), "remarks": r.remarks}
		for r in doc.equipment
	]
	if doc.docstatus == 0 and defaults:
		have = {r["role"] for r in labour}
		labour += [{"role": role, "qty": 0} for role in defaults["labour"] if role not in have]
		have = {r["equipment"] for r in equipment}
		equipment += [{"equipment": e, "qty": 0, "hours": 0} for e in defaults["equipment"] if e not in have]
	data["labour"], data["equipment"] = labour, equipment
	return data


def get_approvers():
	"""ผู้ที่อนุมัติ Daily Request ได้ (สิทธิ์ Submit) ต้องตรงกับ DailyRequest.validate_approver"""
	from frappe.permissions import get_doctype_roles

	roles = [r for r in get_doctype_roles("Daily Request", "submit") if r not in ("Administrator", "All")]
	if not roles:
		return []
	users = frappe.get_all("Has Role", filters={"role": ("in", roles), "parenttype": "User"}, pluck="parent")
	return frappe.get_all(
		"User",
		filters={"name": ("in", list(set(users)) or [""]), "enabled": 1, "user_type": "System User"},
		fields=["name as value", "full_name as label"],
		order_by="full_name asc",
	)


def request_flags(doc):
	"""ปุ่มของ Daily Request: อนุมัติ/ไม่อนุมัติ (ผู้อนุมัติ) และทำรายงานต่อ (อนุมัติแล้ว)"""
	from consbiz.consbiz.doctype.daily_request.daily_request import get_daily_report

	is_approver = frappe.session.user == doc.approver or "System Manager" in frappe.get_roles()
	report = get_daily_report(doc.name) if doc.docstatus == 1 else None
	return {
		"can_approve": bool(
			doc.docstatus == 0
			and doc.status == "Pending"
			and is_approver
			and frappe.has_permission(doc.doctype, "submit", doc)
		),
		"report": report,
		"can_make_report": bool(
			doc.docstatus == 1
			and doc.status == "Approved"
			and not report
			and frappe.has_permission("Daily Report", "create")
		),
	}


@frappe.whitelist()
def get_report_form(project, doctype, name=None, date=None, from_request=None, view=0):
	"""ข้อมูลของฟอร์มกรอกในแอป: เอกสาร (ใหม่ / ร่างเดิม / จากคำขอที่อนุมัติแล้ว) งานให้เลือก ผู้อนุมัติ ฯลฯ
	view = 1: ดูอย่างเดียว ไม่ต้องโหลดรายการงาน"""
	from consbiz.consbiz.doctype.daily_report.daily_report import (
		get_default_resources,
		get_same_day_documents,
		get_tasks,
	)

	check_doctype(doctype)
	_info, cm = check_project(project)
	if not cm:
		frappe.throw(_("โครงการนี้ยังไม่มีแผนงานก่อสร้าง"))

	if name:
		doc = frappe.get_doc(doctype, name)
		doc.check_permission("read")
		if doc.construction_management != cm:
			frappe.throw(_("{0} ไม่ใช่เอกสารของโครงการนี้").format(name))
	elif from_request:
		from consbiz.consbiz.doctype.daily_request.daily_request import make_daily_report

		frappe.has_permission("Daily Report", "create", throw=True)
		doc = make_daily_report(from_request)
		doc.date = doc.date or nowdate()
	else:
		frappe.has_permission(doctype, "create", throw=True)
		doc = frappe.new_doc(doctype)
		doc.construction_management = cm
		doc.date = getdate(date or nowdate())
		fullname = frappe.utils.get_fullname(frappe.session.user)
		if doctype == "Daily Report":
			doc.supervisor_name = fullname
		else:
			from consbiz.consbiz.doctype.daily_request.daily_request import get_last_approver

			doc.requested_by = fullname
			doc.approver = get_last_approver(cm)

	editable = doc.docstatus == 0 and (doc.is_new() or doc.has_permission("write"))
	result = {
		"doctype": doctype,
		"construction_management": cm,
		"doc": serialize(doc, get_default_resources(doctype, cm) if editable and not cint(view) else None),
		"editable": editable,
		"can_submit": bool(
			doctype == "Daily Report" and doc.docstatus == 0 and frappe.has_permission(doctype, "submit")
		),
		"owner_name": frappe.utils.get_fullname(doc.owner) if not doc.is_new() else None,
		"current_progress": flt(frappe.db.get_value("Construction Management", cm, "actual_progress")),
	}
	if not doc.is_new():
		result["pdf_url"] = pdf_url(doctype, doc.name)
	if doctype == "Daily Request" and not doc.is_new():
		result.update(request_flags(doc))
	if cint(view):
		return result

	result["tasks"] = [
		{
			"wbs": t["wbs"],
			"item_name": t["item_name"],
			"group_path": t["group_path"],
			"uom": t["uom"],
			"quantity": flt(t["quantity"]),
			"weight": flt(t["weight"]),
			"previous_qty": flt(t["previous_qty"]),
			"previous_percent": flt(t["previous_percent"]),
			"in_plan": t["in_plan"],
		}
		for t in get_tasks(cm, doc.date, report=doc.name if doctype == "Daily Report" and not doc.is_new() else None)
	]
	result["weather_options"] = [
		o for o in (frappe.get_meta("Daily Report").get_field("weather").options or "").split("\n") if o
	]
	result["same_day"] = get_same_day_documents(cm, doc.date, exclude=None if doc.is_new() else doc.name)
	if doctype == "Daily Request":
		result["approvers"] = get_approvers()
	return result


@frappe.whitelist(methods=["POST"])
def save_report(project, doctype, data, submit=0):
	"""บันทึกจากฟอร์มในแอป (ใหม่หรือร่างเดิม) Daily Report submit=1 = ส่งรายงาน
	Daily Request บันทึก = ส่งขออนุมัติ (ระบบมอบหมายให้ผู้อนุมัติ)"""
	check_doctype(doctype)
	data = store_app.parse(data)
	_info, cm = check_project(project)
	if data.get("name"):
		doc = frappe.get_doc(doctype, data["name"])
		if doc.docstatus != 0:
			frappe.throw(_("{0} ส่งแล้ว แก้ไขไม่ได้").format(doc.name))
		if doc.construction_management != cm:
			frappe.throw(_("{0} ไม่ใช่เอกสารของโครงการนี้").format(doc.name))
	else:
		doc = frappe.new_doc(doctype)
		doc.construction_management = cm

	for field in FORM_FIELDS[doctype]:
		if field in data:
			doc.set(field, data[field] or None)
	doc.set(
		"items",
		[{f: row.get(f) for f in ITEM_FIELDS[doctype]} for row in data.get("items") or [] if row.get("wbs")],
	)
	# แถวที่ไม่ได้กรอกจำนวนถูกตัดใน validate ของเอกสาร (remove_empty_resources)
	doc.set(
		"labour",
		[
			{"role": r.get("role"), "qty": cint(r.get("qty")), "remarks": r.get("remarks")}
			for r in data.get("labour") or []
			if r.get("role")
		],
	)
	doc.set(
		"equipment",
		[
			{
				"equipment": r.get("equipment"),
				"qty": cint(r.get("qty")),
				"hours": flt(r.get("hours")),
				"remarks": r.get("remarks"),
			}
			for r in data.get("equipment") or []
			if r.get("equipment")
		],
	)
	doc.save()
	if cint(submit) and doctype == "Daily Report":
		doc.submit()
	return {"name": doc.name, "docstatus": doc.docstatus, "status": doc.get("status")}


@frappe.whitelist(methods=["POST"])
def submit_report(name):
	doc = frappe.get_doc("Daily Report", name)
	doc.submit()
	return {"name": doc.name, "docstatus": doc.docstatus}


@frappe.whitelist(methods=["POST"])
def approve_request(name):
	"""อนุมัติ = Submit (DailyRequest.before_submit ตรวจว่าเป็นผู้อนุมัติที่ระบุ)"""
	doc = frappe.get_doc("Daily Request", name)
	doc.submit()
	return {"name": doc.name, "status": doc.status}


@frappe.whitelist(methods=["POST"])
def reject_request(name, reason):
	from consbiz.consbiz.doctype.daily_request.daily_request import reject

	reject(name, reason)
	return {"name": name, "status": "Rejected"}


# ---------------------------------------------------------------- บริหารโครงการ (ดูอย่างเดียว)


def plan_of(project):
	_info, cm = check_project(project)
	if not cm:
		return None
	frappe.has_permission("Construction Management", "read", cm, throw=True)
	return cm


@frappe.whitelist()
def get_pm_summary(project):
	"""ภาพรวม = Tab ภาพรวมของ CM (dashboard.get_dashboard)"""
	from consbiz.consbiz.doctype.construction_management.dashboard import get_dashboard

	cm = plan_of(project)
	if not cm:
		return None
	data = get_dashboard(cm)
	data["construction_management"] = cm
	data["can_edit_plan"] = bool(frappe.has_permission("Construction Management", "write", cm))
	return data


@frappe.whitelist()
def get_plan(project):
	"""แถวของ Gantt: หัวข้อ + งานย่อย พร้อม % แผน (แผนปัจจุบัน) / % จริง ณ วันนี้ และงานวิกฤต
	หัวข้อรวมจากงานย่อยตามน้ำหนัก (weight) ชุดเดียวกับ % ความคืบหน้าโครงการ"""
	from consbiz.consbiz.doctype.construction_management.construction_management import total_float
	from consbiz.consbiz.doctype.construction_management.delay import (
		STATUS,
		actual_by_task,
		task_plan_percent,
		task_status,
	)

	cm = plan_of(project)
	if not cm:
		return None
	doc = frappe.get_doc("Construction Management", cm)
	day = getdate(nowdate())
	holidays = doc.get_holidays() if doc.use_working_days else set()
	actual = actual_by_task(doc.name, day)
	floats = total_float(doc.tasks, holidays)

	rows = []
	for row in doc.tasks:
		item = {
			"name": row.name,
			"wbs": row.wbs,
			"item_name": row.item_name,
			"indent": cint(row.indent),
			"is_group": cint(row.is_group),
			"start": row.start_date,
			"end": row.end_date,
			"baseline_start": row.baseline_start_date,
			"baseline_end": row.baseline_end_date,
			"weight": flt(row.weight),
			"uom": row.uom,
			"quantity": flt(row.quantity),
			"is_variation": cint(row.is_variation),
		}
		if not row.is_group and row.start_date and row.end_date:
			done = flt(actual.get(row.name, {}).get("percent"))
			plan = task_plan_percent(row, day, holidays, baseline=False)
			status = task_status(getdate(row.start_date), getdate(row.end_date), day, plan, done)
			item.update(
				{
					"actual": flt(done, 2),
					"plan": flt(plan, 2),
					"status": status,
					"status_label": _(STATUS[status][0]),
					"critical": floats.get(row.name, 1) <= 0 and status != "done",
				}
			)
		rows.append(item)

	# หัวข้อ: วันเริ่ม-จบ และ % จากงานย่อยภายใต้หัวข้อ (แถวถัดไปที่ indent มากกว่า)
	for i, row in enumerate(rows):
		if not row["is_group"]:
			continue
		children = []
		for child in rows[i + 1 :]:
			if child["indent"] <= row["indent"]:
				break
			if not child["is_group"] and child.get("start"):
				children.append(child)
		weight = sum(c["weight"] for c in children)
		row["start"] = min((c["start"] for c in children), default=None)
		row["end"] = max((c["end"] for c in children), default=None)
		if weight:
			row["actual"] = flt(sum(c["actual"] * c["weight"] for c in children) / weight, 2)
			row["plan"] = flt(sum(c["plan"] * c["weight"] for c in children) / weight, 2)
	return {
		"construction_management": cm,
		"today": day,
		"start_date": doc.start_date,
		"finish_date": doc.finish_date,
		"revised_finish_date": doc.revised_finish_date,
		"holidays": sorted(holidays),
		"rows": rows,
		"can_edit_plan": bool(frappe.has_permission("Construction Management", "write", cm)),
	}


@frappe.whitelist()
def get_lookahead(project, date=None, weeks=3):
	from consbiz.consbiz.doctype.construction_management.lookahead import get_lookahead as lookahead

	cm = plan_of(project)
	if not cm:
		return None
	data = lookahead(cm, date=date, weeks=weeks, include_last_week=1)
	data["construction_management"] = cm
	return data


@frappe.whitelist()
def get_pm_documents(project):
	"""เอกสารโครงการแยกกลุ่ม (ชุดเดียวกับ Tab เอกสารโครงการของ CM)"""
	from consbiz.consbiz.doctype.construction_management.dashboard import get_documents

	cm = plan_of(project)
	if not cm:
		return None
	data = get_documents(cm)
	data["construction_management"] = cm
	return data


@frappe.whitelist()
def get_resources(project):
	"""แผนทรัพยากร (คน/เครื่องจักรที่ต้องจอง) และแผนจัดซื้อวัสดุ (ต้องสั่งเมื่อไร ขอ/สั่ง/รับแล้วเท่าไร)
	ชุดเดียวกับ Tab ทรัพยากรของ CM (resources.get_overview)"""
	from consbiz.consbiz.doctype.construction_management.resources import get_overview

	cm = plan_of(project)
	if not cm:
		return None
	data = get_overview(cm)
	data.pop("chart", None)
	data["construction_management"] = cm
	return data
