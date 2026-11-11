app_name = "consbiz"
app_title = "ConsBiz"
app_publisher = "Siricons"
app_description = "Construction Business ERP"
app_email = "info@siricons.com"
app_license = "mit"
app_logo_url = "/assets/consbiz/images/logo.png"

add_to_apps_screen = [
    {
        "name": "consbiz",
        "logo": "/assets/consbiz/images/logo.png",
        "title": "ConsBiz",
        "route": "/app/consbiz"
    }
]

# ของที่สร้างผ่านหน้าเว็บ ให้ตั้ง Module = ConsBiz แล้วรัน
# bench --site <site> export-fixtures --app consbiz
# (ไม่กรอง is_system_generated เพราะ Property Setter ที่ระบบสร้างแทนเรา เช่น default_print_format ก็ต้องตามไปด้วย)
fixtures = [
    {"doctype": "Custom Field", "filters": [["module", "=", "ConsBiz"]]},
    {"doctype": "Property Setter", "filters": [["module", "=", "ConsBiz"]]},
    {"doctype": "Client Script", "filters": [["module", "=", "ConsBiz"]]},
    {"doctype": "Print Format", "filters": [["module", "=", "ConsBiz"], ["standard", "=", "No"]]},
    {"doctype": "Report", "filters": [["name", "in", ["Salary Slip Report"]]]},
    # หน้าแรก (Workspace ConsBiz) มีแค่ตัวเรียก consbiz.render_home ใน public/js/home.js
    {"doctype": "Custom HTML Block", "filters": [["name", "in", ["ConsBiz Home"]]]},
    # ผู้บริหาร: อนุมัติเบิกเงินเดือนล่วงหน้าที่เกินวงเงิน (consbiz/self_advance.py)
    {"doctype": "Role", "filters": [["name", "in", ["Executive Approver"]]]},
]


app_include_css = "/assets/consbiz/css/style.css"
app_include_js = [
    "/assets/consbiz/js/utils.js",
    "/assets/consbiz/js/company_switcher.js",
    "/assets/consbiz/js/home.js",
    "/assets/consbiz/js/retention.js",
    "/assets/consbiz/js/transmittal.js"
]


# แอป ConsERP: ทุกหมวดอยู่ระดับเดียวกันใต้ /conserp/<หมวด> (PWA ตัวเดียว scope /conserp)
# หมวดจัดซื้อ/ขาย = bundle ออฟฟิศ (www/office.html, ชื่อหมวดตรงกับ site_app.office_sections) ที่เหลือ = bundle หน้างาน (www/site.html)
_OFFICE_SECTIONS = ("purchase", "sales", "boq", "hr")
# bundle self_app (www/self.html): Self Service ของพนักงานทุกคน (consbiz/self_service.py) + โมดูลอนุมัติ (consbiz/approvals.py)
_SELF_SECTIONS = ("self", "approve")
website_route_rules = [
	*(
		rule
		for section in _SELF_SECTIONS
		for rule in (
			{"from_route": f"/conserp/{section}", "to_route": "self"},
			{"from_route": f"/conserp/{section}/<path:app_path>", "to_route": "self"},
		)
	),
	*(
		rule
		for section in _OFFICE_SECTIONS
		for rule in (
			{"from_route": f"/conserp/{section}", "to_route": "office"},
			{"from_route": f"/conserp/{section}/<path:app_path>", "to_route": "office"},
		)
	),
	{"from_route": "/conserp", "to_route": "site"},
	{"from_route": "/conserp/<path:app_path>", "to_route": "site"},
]


def _redirect(source, target):
	return {"source": source, "target": target, "redirect_http_status": 302, "forward_query_parameters": True}


# URL เดิมยังใช้ได้ (ข้อแรกที่ตรงชนะ เรียงเฉพาะเจาะจงก่อน)
# /office/... และ /conserp/office/... (ออฟฟิศเดิม: buy/sell, ภาพรวมเลิกใช้แล้ว)
# /site/sell, /site/buy/(po|pi) (เคยอยู่แอปหน้างาน), /site/..., /store/... (แอปสโตร์เดิม)
website_redirects = [
	_redirect(r"(?:conserp/)?office/buy(/.*)?", r"/conserp/purchase\1"),
	_redirect(r"(?:conserp/)?office/sell(/.*)?", r"/conserp/sales\1"),
	_redirect(r"(?:conserp/)?office(/.*)?", r"/conserp/purchase"),
	# การเงินเคยเป็นหมวดของตัวเอง ย้ายเป็นเมนูในแผนงาน (ต้นทุน/EV เป็น tab)
	_redirect(r"(?:conserp|site)/finance/finance-cost", r"/conserp/pm/finance/cost"),
	_redirect(r"(?:conserp|site)/finance/finance-evm", r"/conserp/pm/finance/evm"),
	_redirect(r"(?:conserp|site)/finance(/.*)?", r"/conserp/pm/finance"),
	_redirect(r"site/sell(/.*)?", r"/conserp/sales\1"),
	_redirect(r"site/buy/(po|pi)(/.*)?", r"/conserp/purchase/\1\2"),
	_redirect(r"site/buy/(buy-doc|buy-form)/(po|pi)(/.*)?", r"/conserp/purchase/\1/\2\3"),
	_redirect(r"site(/.*)?", r"/conserp\1"),
	_redirect(r"store(/.*)?", r"/conserp/store\1"),
]

naming_series_variables = {
    "ABBR": "consbiz.utils.parse_naming_series_variable"
}

doctype_js = {
    "Quotation": "public/js/quotation_cal.js",
    "Sales Order": "public/js/sales_order_cal.js",
    "Sales Invoice": "public/js/sales_invoice_cal.js",
    "Purchase Order": "public/js/purchase_order.js",
    "Purchase Invoice": "public/js/purchase_invoice.js",
    "Payment Entry": "public/js/payment_entry_deduction.js",
    "Material Request": "public/js/material_request.js",
    "Employee": "public/js/employee.js",
    "Item": "public/js/item.js",
    "Stock Entry": "public/js/stock_entry.js",
    "Project": "public/js/project.js"
}

# ----------------------------------------
# Auto Cancel Exemption (สำคัญมาก)
# ----------------------------------------
# บอกระบบว่าไม่ต้อง Block ถ้ามีเอกสารเหล่านี้ Link อยู่ (เราจะจัดการ Cancel เองใน Code)
auto_cancel_exempted_doctypes = ["Retention Receivable", "Retention Payable"]


doc_events = {
    "Payment Entry": {
        "on_submit": [
            "consbiz.api.update_si_tax",
            # จ่ายใบเบิกจากแอป Self Service: หักเงินเดือนล่วงหน้าเป็นงวด / ตั้งกำหนดเคลียร์เงินสำรองจ่าย
            "consbiz.self_advance.on_payment_entry_submit"
        ]
    },

    # ใบเบิกจากแอปต้องผ่านผู้อนุมัติ (Expense Approver) เกินวงเงินต้องผู้บริหาร (consbiz/self_advance.py)
    "Employee Advance": {
        "before_submit": "consbiz.self_advance.guard_advance_submit"
    },

    # เงินประกันผลงาน (consbiz/retention.py): JE ที่ผูกกับ Retention Invoice / Release (ช่อง journal_entry)
    "Journal Entry": {
        "on_submit": "consbiz.retention.on_journal_entry_change",
        "before_cancel": "consbiz.retention.before_journal_entry_cancel",
        "on_cancel": "consbiz.retention.on_journal_entry_change",
        "on_trash": "consbiz.retention.on_journal_entry_trash"
    },

    "Purchase Invoice": {
        # ตัดสต็อกในใบเดียว (update_stock): คลังวัสดุผู้ว่าจ้างรับของบริษัทไม่ได้ (consbiz/site_stock.py)
        "validate": "consbiz.site_stock.validate_warehouses",
        "on_submit": "consbiz.retention.create_from_invoice",
        "before_cancel": "consbiz.retention.cancel_from_invoice"
    },

    # โครงการที่หัวเอกสาร (custom_project) ลงทุกรายการ ให้ PO / PR ที่สร้างต่อได้โครงการไปด้วย (แผนวัสดุนับยอดตามโครงการ)
    # ผู้ว่าจ้างจัดหา (Customer Provided): เลขชุด OPO- และสลับรายการเป็น Item คู่ (consbiz/employer_supplied.py)
    "Material Request": {
        "before_insert": "consbiz.employer_supplied.set_request_series",
        "before_validate": "consbiz.employer_supplied.swap_request_items",
        "validate": [
            "consbiz.consbiz.doctype.construction_material_plan.construction_material_plan.set_item_project",
            "consbiz.site_stock.validate_wbs",
            # ยอดเงิน/ภาษีของ MR สูตรเดียวกับ material_request.js (แอปหน้างานใช้ค่าจากที่นี่)
            "consbiz.request_totals.calculate"
        ]
    },

    # สต็อกหน้างาน (consbiz/site_stock.py): คลังวัสดุผู้ว่าจ้างแยกจากคลังบริษัท, เบิกตัดคลังผู้ว่าจ้างก่อน, WBS ของรายการ
    "Stock Entry": {
        "before_validate": "consbiz.site_stock.split_employer_stock",
        "validate": [
            "consbiz.site_stock.validate_warehouses",
            "consbiz.site_stock.validate_wbs"
        ]
    },

    "Purchase Receipt": {
        "validate": "consbiz.site_stock.validate_warehouses"
    },

    # ทุกโครงการมีคลังของตัวเอง: All Warehouses / โครงการ / <โครงการ>
    "Project": {
        "validate": "consbiz.site_stock.validate_project_warehouse_name",
        "after_insert": "consbiz.site_stock.create_project_warehouse"
    },

    # Item คู่ของวัสดุผู้ว่าจ้างจัดหา ใช้ค่าจาก Item หลักเสมอ และตาม Item หลักเมื่อแก้/merge
    "Item": {
        "before_validate": "consbiz.employer_supplied.enforce_base_values",
        "on_update": "consbiz.employer_supplied.sync_employer_item",
        "before_rename": "consbiz.employer_supplied.merge_employer_items",
        "after_rename": "consbiz.employer_supplied.sync_after_rename"
    },

    "Sales Invoice": {
        "on_submit": "consbiz.retention.create_from_invoice",
        "before_cancel": "consbiz.retention.cancel_from_invoice"
    },

    # พนักงานลงเวลาเองได้ผ่านแอป Self Service เท่านั้น (GPS + เซลฟี่) HR แก้ได้ตามปกติ (consbiz/self_service.py)
    "Employee Checkin": {
        "validate": "consbiz.self_service.guard_checkin"
    }
}

scheduler_events = {
    "daily": [
        # เงินประกันผลงาน: Active → Overdue เมื่อเลยวันครบกำหนด
        "consbiz.retention.update_overdue",
        # ลบรูปเซลฟี่ของการลงเวลาเมื่อ Salary Slip ของงวดนั้นผ่านไป 90 วัน (ยกเว้นติ๊กเก็บหลักฐาน)
        "consbiz.self_service.purge_selfies",
        # เงินสำรองจ่ายเลยกำหนดเคลียร์: แจ้งเตือนพนักงาน
        "consbiz.self_advance.remind_overdue_clearing"
    ]
}

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "consbiz",
# 		"logo": "/assets/consbiz/logo.png",
# 		"title": "ConsBiz",
# 		"route": "/consbiz",
# 		"has_permission": "consbiz.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/consbiz/css/consbiz.css"
# app_include_js = "/assets/consbiz/js/consbiz.js"

# include js, css files in header of web template
# web_include_css = "/assets/consbiz/css/consbiz.css"
# web_include_js = "/assets/consbiz/js/consbiz.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "consbiz/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "consbiz/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# automatically load and sync documents of this doctype from downstream apps
# importable_doctypes = [doctype_1]

# Jinja
# ----------

# add methods and filters to jinja environment
jinja = {
	"methods": [
		"consbiz.utils.thai_date",
		"consbiz.consbiz.doctype.bar_cut_plan.bar_cut_plan.shape_svg",
		"consbiz.utils.name_with_title",
		"consbiz.utils.thai_baht_text",
		"consbiz.utils.image_data_uri",
	]
}
# jinja = {
# 	"methods": "consbiz.utils.jinja_methods",
# 	"filters": "consbiz.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "consbiz.install.before_install"
after_install = "consbiz.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "consbiz.uninstall.before_uninstall"
# after_uninstall = "consbiz.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "consbiz.utils.before_app_install"
# after_app_install = "consbiz.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "consbiz.utils.before_app_uninstall"
# after_app_uninstall = "consbiz.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "consbiz.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"consbiz.tasks.all"
# 	],
# 	"daily": [
# 		"consbiz.tasks.daily"
# 	],
# 	"hourly": [
# 		"consbiz.tasks.hourly"
# 	],
# 	"weekly": [
# 		"consbiz.tasks.weekly"
# 	],
# 	"monthly": [
# 		"consbiz.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "consbiz.install.before_tests"

# Extend DocType Class
# ------------------------------
#
# Specify custom mixins to extend the standard doctype controller.
# extend_doctype_class = {
# 	"Task": "consbiz.custom.task.CustomTaskMixin"
# }

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "consbiz.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "consbiz.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["consbiz.utils.before_request"]
# after_request = ["consbiz.utils.after_request"]

# Job Events
# ----------
# before_job = ["consbiz.utils.before_job"]
# after_job = ["consbiz.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"consbiz.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
# ignore_translatable_strings_from = []

