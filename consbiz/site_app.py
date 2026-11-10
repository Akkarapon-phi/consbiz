# Copyright (c) 2026, Siricons and contributors
# For license information, please see license.txt

"""แอปหน้างาน (/site, www/site.html + public/js/site_app/) แอปเดียวแบ่งเป็นหมวดงาน สลับในแอป

- store (สโตร์): รับของ / เบิก / ยืม-คืน / คลัง  API อยู่ที่ consbiz/store_app.py
- buy (ขอซื้อ): ใบขอซื้อ + ติดตามสถานะ (consbiz/site_docs.py) สั่งซื้อ/แจ้งหนี้/ขายอยู่แอปออฟฟิศ (/office)
- pm (แผนงาน): ภาพรวมสัญญา/ความล่าช้า, แผนงาน (Gantt ดูอย่างเดียว), Look-ahead, เอกสารโครงการ,
  การเงิน (Cash Flow, ต้นทุนตามหมวด, Earned Value) เฉพาะผู้ที่เห็นงบต้นทุน (budget_cost permlevel 1)
  ข้อมูลชุดเดียวกับ Tab ของ Construction Management (dashboard.py / lookahead.py) แก้แผนที่หน้า Gantt ในระบบเต็ม
- work (ควบคุมงาน): โฟร์แมน/วิศวกร ความคืบหน้า + S-Curve, ปฏิทินรายงานประจำวัน, บันทึกคอนกรีต (API ที่ store_app.py),
  กรอก/ส่ง Daily Report และขอ/อนุมัติ Daily Request ในแอป (ทีละขั้น), ดูขอตรวจงาน / Punch List
  API อยู่ในไฟล์นี้ (ฟอร์มขอตรวจงาน / Punch List / งานลด-เพิ่ม / EOT อยู่ project_docs.py)
- resources (ทรัพยากร): วัสดุที่ต้องสั่ง/ยอดวัสดุ/คนและเครื่องจักร ทุกคนที่เข้าหมวดหน้างานได้ ไม่มีมูลค่างาน
หมวดที่ผู้ใช้เห็น = หมวดที่มีสิทธิ์อ่าน/สร้างเอกสารอย่างน้อย 1 ชนิด (SECTIONS) ทุก API ยังตรวจสิทธิ์ของเอกสารเอง
"""

import frappe
from frappe import _
from frappe.utils import cint, flt, getdate, nowdate

from consbiz import app_settings, store_app
from consbiz.site_stock import construction_management_of

LIST_LIMIT = 60
WORK_DOCTYPES = ("Daily Report", "Daily Request", "Inspection Request", "Punch List")


# แอปหน้าจอของ consbiz (ตัวสลับแอป) ลำดับตามที่แสดง เพิ่มแอปใหม่ที่นี่ + ฟังก์ชันหมวดของแอปนั้นใน APP_SECTIONS
APPS = (
	{"key": "site", "title": "ConsERP", "label": "หน้างาน", "url": "/conserp", "icon": "hardhat"},
	{"key": "office", "title": "ConsOffice", "label": "ออฟฟิศ", "url": "/conserp", "icon": "briefcase"},
)
BUY_DOCTYPES = ("Material Request", "Purchase Order", "Purchase Invoice")
SELL_DOCTYPES = ("Quotation", "Sales Order", "Sales Invoice")


def readable_any(doctypes):
	return any(frappe.has_permission(doctype, "read") for doctype in doctypes)


def office_sections():
	"""หมวดของแอปออฟฟิศ (/conserp/purchase, /conserp/sales) ที่ผู้ใช้มีสิทธิ์
	ชื่อหมวดต้องตรงกับ website_route_rules ใน hooks.py (server เลือก bundle ออฟฟิศตามชื่อหมวด)"""
	sections = []
	if readable_any(BUY_DOCTYPES):
		sections.append("purchase")
	if readable_any(SELL_DOCTYPES):
		sections.append("sales")
	if frappe.has_permission("BOQ", "read"):
		sections.append("boq")
	return sections


def can_view_finance():
	"""เมนูการเงินของหมวดแผนงานใช้เกณฑ์เดียวกับ EVM/งบต้นทุน: ต้องเห็นช่อง budget_cost (permlevel 1 ของ Construction Management)"""
	if not frappe.has_permission("Construction Management", "read"):
		return False
	meta = frappe.get_meta("Construction Management")
	return meta.get_field("budget_cost").permlevel in meta.get_permlevel_access("read")


def site_sections(can=None):
	"""หมวดของแอปหน้างาน (/site) ที่ผู้ใช้มีสิทธิ์ can = สิทธิ์สโตร์จาก store_app.boot_data"""
	can = can if can is not None else store_app.boot_data()["can"]
	sections = []
	if any(can.get(key) for key in ("receive", "receive_employer", "issue", "borrow")):
		sections.append("store")
	if readable_any(WORK_DOCTYPES) or can.get("concrete"):
		sections.append("work")
	if frappe.has_permission("Construction Management", "read"):
		sections.append("pm")
	can_buy = frappe.has_permission("Material Request", "read")
	# ทรัพยากรดูได้ทุกคนที่เข้าหมวดหน้างานได้ (API ไม่ส่งมูลค่างาน)
	if sections or can_buy:
		sections.append("resources")
	# หน้างานขอซื้อได้อย่างเดียว (สั่งซื้อ/แจ้งหนี้/ขาย ทำที่แอปออฟฟิศ)
	if can_buy:
		sections.append("buy")
	return sections


APP_SECTIONS = {"site": site_sections, "office": office_sections}


def sections_by_app(current=None):
	"""{แอป: หมวดที่ผู้ใช้มีสิทธิ์} current = (แอปที่เปิดอยู่, หมวดของแอปนั้น) ไม่ต้องคำนวณซ้ำ"""
	return {
		config["key"]: current[1] if current and current[0] == config["key"] else APP_SECTIONS[config["key"]]()
		for config in APPS
	}


def available_apps(by_app):
	"""แอปที่ผู้ใช้เปิดได้ (มีอย่างน้อย 1 หมวด)"""
	return [dict(config) for config in APPS if by_app[config["key"]]]


def app_modules(by_app):
	"""หมวดของทุกแอปเรียงตาม APPS (หน้า Desktop / Dock ของแอป ConsERP ที่ติดตั้งตัวเดียว)"""
	modules = []
	for config in APPS:
		for section in by_app[config["key"]]:
			modules.append({"app": config["key"], "section": section, "url": f"{config['url']}/{section}"})
	return modules


def add_apps(boot, current):
	from consbiz.site_docs import doc_permissions

	by_app = sections_by_app(current)
	boot["docs"] = doc_permissions()
	boot["can"]["settings"] = app_settings.can_manage()
	boot["apps"] = available_apps(by_app)
	boot["modules"] = app_modules(by_app)


PROFILE_FIELDS = (
	"first_name",
	"middle_name",
	"last_name",
	"email",
	"username",
	"language",
	"time_zone",
	"gender",
	"birth_date",
	"phone",
	"mobile_no",
	"location",
	"interest",
	"bio",
)


@frappe.whitelist()
def get_my_profile():
	"""ข้อมูลส่วนตัวของผู้ใช้ที่ล็อกอิน (popup จาก avatar) ไม่รับชื่อผู้ใช้จากภายนอก จึงอ่านได้แค่ของตัวเอง"""
	profile = frappe.db.get_value("User", frappe.session.user, PROFILE_FIELDS, as_dict=True)
	if profile.language:
		profile.language = (
			frappe.db.get_value("Language", profile.language, "language_name") or profile.language
		)
	return profile


def office_boot_data():
	"""ข้อมูลตั้งต้นของแอปออฟฟิศ (/office)"""
	boot = store_app.boot_data()
	sections = office_sections()
	boot.update(
		{
			"sections": sections,
			"desk": bool(sections),
			# ตัวเลือกบริษัท (กรองรายการ/ตัวเลข + บริษัทของเอกสารใหม่) เฉพาะบริษัทที่ผู้ใช้มีสิทธิ์
			"companies": frappe.get_list(
				"Company", fields=["name", "abbr", "company_logo"], order_by="name asc", limit_page_length=0
			),
			"default_company": frappe.defaults.get_user_default("Company"),
		}
	)
	add_apps(boot, ("office", sections))
	return boot


def boot_data():
	boot = store_app.boot_data()
	can_work = {doctype: bool(frappe.has_permission(doctype, "read")) for doctype in WORK_DOCTYPES}
	boot["can"].update(
		{
			"daily_report": bool(frappe.has_permission("Daily Report", "create")),
			"daily_request": bool(frappe.has_permission("Daily Request", "create")),
			"view_daily_report": can_work["Daily Report"],
			"view_daily_request": can_work["Daily Request"],
			"inspection": can_work["Inspection Request"],
			"punch_list": can_work["Punch List"],
			"finance": can_view_finance(),
			"create_inspection": bool(frappe.has_permission("Inspection Request", "create")),
			"create_punch_list": bool(frappe.has_permission("Punch List", "create")),
		}
	)
	sections = site_sections(boot["can"])
	boot["sections"] = sections
	add_apps(boot, ("site", sections))
	boot["desk"] = boot["desk"] or any(can_work.values())
	return boot


def check_project(project):
	info = store_app.check_project(project)
	return info, construction_management_of(project)


def readable(doctype):
	return bool(frappe.has_permission(doctype, "read"))


# เอกสารที่หน้าในแอปผูกกับโครงการ (ตรงกับ APP_PAGES ที่ project = true ใน shared/notifications.js)
PROJECT_PAGE_DOCTYPES = (
	"Daily Report",
	"Daily Request",
	"Variation Order",
	"Extension of Time",
	"Inspection Request",
	"Punch List",
	"Concrete Usage",
	"Equipment Borrowing",
)


@frappe.whitelist()
def get_doc_project(doctype, name):
	"""โครงการของเอกสาร ให้แอปสลับไปโครงการนั้นก่อนเปิด (กดการแจ้งเตือน)
	None = แอปเลือกโครงการนั้นไม่ได้ (ไม่อยู่ในรายการของ get_projects) ให้เปิดระบบเต็มแทน"""
	if doctype not in PROJECT_PAGE_DOCTYPES:
		frappe.throw(_("ไม่รองรับ {0}").format(doctype))
	frappe.has_permission(doctype, "read", name, throw=True)
	project = frappe.db.get_value(doctype, name, "project")
	if not project:
		return None
	names = frappe.get_list("Project", filters={"name": project, "status": "Open"}, pluck="name", limit_page_length=1)
	return names[0] if names else None


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
		"categories": [],
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
	from consbiz.consbiz.doctype.construction_management.dashboard import (
		category_progress,
		late_tasks,
		progress_curve,
	)
	from consbiz.consbiz.doctype.construction_management.delay import analyse

	doc = frappe.get_doc("Construction Management", cm)
	delay = analyse(doc, day)
	plan, basis = target_progress(doc, day)
	late = late_tasks(delay["tasks"])
	return {
		"curve": progress_curve(doc, day),
		"progress": {
			"plan": flt(plan, 2),
			"actual": flt(actual_progress_at(doc, day)[1], 2),
			"basis": basis,
			"finish_date": doc.revised_finish_date or doc.finish_date,
		},
		"categories": category_progress(doc, day),
		"late_count": len(late),
		"late_tasks": late,
	}


# ---------------------------------------------------------------- รายการเอกสาร


EMPLOYER_STATUS = {
	"Pending": ("รออนุมัติ", "amber"),
	"Approved": ("อนุมัติแล้ว", "green"),
	"Rejected": ("ไม่อนุมัติ", "rose"),
}
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
	"Variation Order": EMPLOYER_STATUS,
	"Extension of Time": EMPLOYER_STATUS,
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


# ชนิดเอกสารที่แสดงเป็นรายการ -> (ช่องของรายการ, ช่องสถานะ, ช่องวันที่ที่ใช้เรียง)
DOCUMENT_LISTS = {
	"Variation Order": (("title", "reference_no", "date", "extension_days", "employer_status"), "employer_status", "date"),
	"Extension of Time": (
		("title", "cause", "date", "requested_days", "approved_days", "revised_finish_date", "employer_status"),
		"employer_status",
		"date",
	),
	"Inspection Request": (
		("title", "wbs", "item_name", "location", "request_date", "inspection_date", "inspector", "result"),
		"result",
		"request_date",
	),
	"Punch List": (("title", "date", "status", "open_items", "inspection_request"), "status", "date"),
	"Daily Report": (("date", "supervisor_name", "today_progress", "cumulative_progress"), None, "date"),
	"Daily Request": (("date", "requested_by", "status"), "status", "date"),
	"Construction Baseline": (("title", "baseline_date"), None, "baseline_date"),
}


def document_rows(cm, doctype):
	"""รายการเอกสารของแผนงาน ล่าสุดก่อน มูลค่างานเพิ่ม-ลดเฉพาะผู้ที่เห็นงบต้นทุน (เกณฑ์เดียวกับเมนูการเงิน)"""
	fields, status_field, date_field = DOCUMENT_LISTS[doctype]
	fields = ["name", "docstatus", *fields]
	if doctype == "Variation Order" and can_view_finance():
		fields.append("net_amount")
	rows = frappe.get_list(
		doctype,
		filters={"construction_management": cm, "docstatus": ("<", 2)},
		fields=fields,
		order_by=f"{date_field} desc, creation desc",
		limit_page_length=LIST_LIMIT,
	)
	return with_status(doctype, rows, status_field) if frappe.get_meta(doctype).is_submittable else rows


@frappe.whitelist()
def get_pm_document_rows(project, doctype):
	"""tab ของเมนูเอกสาร (หมวดแผนงาน) 1 tab = 1 ชนิดเอกสาร"""
	if doctype not in DOCUMENT_LISTS:
		frappe.throw(_("ไม่รองรับเอกสารชนิดนี้"), frappe.PermissionError)
	_info, cm = check_project(project)
	if not cm or not readable(doctype):
		return []
	return document_rows(cm, doctype)


@frappe.whitelist()
def get_inspections(project, kind="inspection"):
	"""kind = inspection (Inspection Request) / punch (Punch List) ล่าสุดก่อน"""
	_info, cm = check_project(project)
	doctype = "Punch List" if kind == "punch" else "Inspection Request"
	if not cm or not readable(doctype):
		return []
	return document_rows(cm, doctype)


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


REPORT_KINDS = {"dr": "Daily Report", "drq": "Daily Request"}
REPORT_LIST_FIELDS = {
	"Daily Report": ("today_progress", "cumulative_progress", "weather", "problems"),
	"Daily Request": ("status", "expected_progress", "requested_by"),
}
# ไฟล์เดียวสร้างในคำขอเดียว ต้องเสร็จก่อน web worker หมดเวลา
BULK_PRINT_LIMIT = 50


def bulk_print_limit():
	from frappe.utils.print_format import get_max_bulk_print_docs

	return min(BULK_PRINT_LIMIT, get_max_bulk_print_docs())


@frappe.whitelist()
def get_report_list(project, kind):
	"""ตารางรายงานประจำวัน / ขออนุมัติปฏิบัติงานของโครงการ (ครบทุกฉบับ แอปแบ่งหน้าและกรองในเครื่อง)"""
	_info, cm = check_project(project)
	if not cm:
		return None
	doctype = REPORT_KINDS.get(kind)
	if not doctype:
		frappe.throw(_("ไม่รองรับ {0}").format(kind))
	rows = []
	if readable(doctype):
		rows = frappe.get_list(
			doctype,
			filters={"construction_management": cm, "docstatus": ("<", 2)},
			fields=["name", "date", "docstatus", "owner", *REPORT_LIST_FIELDS[doctype]],
			order_by="date desc, creation desc",
			limit_page_length=0,
		)
	with_status(doctype, rows, "status" if doctype == "Daily Request" else None)
	for row in rows:
		row.owner_name = frappe.utils.get_fullname(row.owner)
	return {
		"rows": rows,
		"can_print_draft": bool(cint(frappe.db.get_single_value("Print Settings", "allow_print_for_draft"))),
		"print_limit": bulk_print_limit(),
	}


@frappe.whitelist()
def reports_pdf(doctype, names):
	"""รวมเอกสารหลายฉบับเป็น PDF ไฟล์เดียว ใช้ Print Format และตัวสร้าง PDF ชุดเดียวกับ pdf_url
	(download_multi_pdf ของ Frappe ไม่รับตัวสร้าง PDF จึงไม่ตรงกับปุ่มพิมพ์ทีละฉบับ)"""
	from io import BytesIO

	from frappe.utils.print_format import validate_print_permission
	from pypdf import PdfWriter

	check_doctype(doctype)
	names = frappe.parse_json(names)
	if not isinstance(names, list) or not names:
		frappe.throw(_("กรุณาเลือกเอกสาร"))
	limit = bulk_print_limit()
	if len(names) > limit:
		frappe.throw(_("พิมพ์ได้ครั้งละไม่เกิน {0} รายการ").format(limit))
	print_format, generator = print_options(doctype)
	writer = PdfWriter()
	for name in names:
		doc = frappe.get_doc(doctype, name)
		validate_print_permission(doc)
		frappe.get_print(
			doctype, name, print_format, doc=doc, as_pdf=True, output=writer, pdf_generator=generator
		)
	frappe.local.response.filename = f"{doctype.replace(' ', '-')}.pdf"
	output = BytesIO()
	writer.write(output)
	frappe.local.response.filecontent = output.getvalue()
	frappe.local.response.type = "pdf"


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
	"Daily Report": (
		"today_progress",
		"cumulative_progress",
		"baseline_progress",
		"progress_variance",
		"plan_basis",
	),
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
ROW_VIEW_FIELDS = (
	"item_name",
	"uom",
	"group_path",
	"boq_qty",
	"previous_qty",
	"previous_percent",
	"remaining_qty",
)


def print_options(doctype):
	"""Print Format ชื่อเดียวกับ DocType และตัวสร้าง PDF แบบปุ่ม PDF ของหน้าพิมพ์ในระบบเต็ม
	(ของ Print Format ถ้าตั้งไว้ ไม่งั้นของ Print Settings)"""
	print_format = doctype if frappe.db.exists("Print Format", doctype) else None
	generator = (
		(print_format and frappe.db.get_value("Print Format", print_format, "pdf_generator"))
		or frappe.db.get_single_value("Print Settings", "pdf_generator")
		or "wkhtmltopdf"
	)
	return print_format, generator


def pdf_url(doctype, name):
	from urllib.parse import urlencode

	print_format, generator = print_options(doctype)
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
		result["can_delete"] = store_app.can_delete(doc)
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
		for t in get_tasks(
			cm, doc.date, report=doc.name if doctype == "Daily Report" and not doc.is_new() else None
		)
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
def delete_report(doctype, name):
	check_doctype(doctype)
	store_app.delete_document(frappe.get_doc(doctype, name))


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


# ---------------------------------------------------------------- แผนงาน (ดูอย่างเดียว)


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


BOARD_TASK_FIELDS = ("name", "wbs", "item_name", "is_group", "indent", "start_date", "end_date", "duration", "plan_distribution")


@frappe.whitelist()
def get_resource_board(project):
	"""หมวดทรัพยากร: ข้อมูลรูปแบบเดียวกับ get_schedule_data แต่มีแค่รายการและวันที่
	ผู้ใช้อาจไม่มีสิทธิ์อ่านแผนงาน จึงใช้สิทธิ์เข้าหมวดแทน และไม่ส่งมูลค่างาน/น้ำหนัก"""
	from consbiz.consbiz.doctype.construction_management.construction_management import (
		get_holiday_dates,
		schedule_version,
	)
	from consbiz.consbiz.doctype.construction_management.resources import material_plan_data, resource_plan_data

	_info, cm = check_project(project)
	if not cm:
		return None
	if "resources" not in site_sections():
		frappe.throw(_("ไม่มีสิทธิ์ดูทรัพยากร"), frappe.PermissionError)
	doc = frappe.get_doc("Construction Management", cm)
	return {
		"name": doc.name,
		"project": doc.project,
		"finish_date": doc.finish_date,
		"revised_finish_date": doc.revised_finish_date,
		"use_working_days": doc.use_working_days,
		"week_by_month": doc.week_by_month,
		"holidays": get_holiday_dates(doc.holiday_list),
		"modified": str(doc.modified),
		"version": schedule_version(doc.name),
		"can_write": False,
		# ฟอร์มขอซื้ออยู่หมวด buy ต้องเปิดหมวดนั้นได้ด้วย
		"can_request": bool(
			frappe.has_permission("Material Request", "create") and frappe.has_permission("Material Request", "read")
		),
		"baselines": [],
		"active_baseline": None,
		"progress_entries": [],
		"tasks": [{field: row.get(field) for field in BOARD_TASK_FIELDS} for row in doc.tasks],
		"resource_plan": resource_plan_data(cm, ignore_permissions=True),
		"material_plan": material_plan_data(cm, ignore_permissions=True),
	}


@frappe.whitelist()
def get_project_finance(project, date=None):
	"""เมนูการเงิน = Tab การเงินของ CM (finance.get_finance) เฉพาะผู้ที่เห็นงบต้นทุน"""
	from consbiz.consbiz.doctype.construction_management.finance import get_finance

	if not can_view_finance():
		frappe.throw(_("ไม่มีสิทธิ์ดูข้อมูลการเงินของโครงการ"), frappe.PermissionError)
	cm = plan_of(project)
	if not cm:
		return None
	data = get_finance(cm, date)
	data["construction_management"] = cm
	return data
