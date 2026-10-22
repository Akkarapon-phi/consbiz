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
]


app_include_css = "/assets/consbiz/css/style.css"
app_include_js = [
    "/assets/consbiz/js/utils.js",
    "/assets/consbiz/js/company_switcher.js"
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
    "Payment Entry": "public/js/payment_entry_deduction.js"
}

# ----------------------------------------
# Auto Cancel Exemption (สำคัญมาก)
# ----------------------------------------
# บอกระบบว่าไม่ต้อง Block ถ้ามีเอกสารเหล่านี้ Link อยู่ (เราจะจัดการ Cancel เองใน Code)
auto_cancel_exempted_doctypes = ["Retention Receivable"]


doc_events = {
    "Payment Entry": {
        "on_submit": "consbiz.api.update_si_tax" 
    },

    "Journal Entry": {
        "on_submit": "consbiz.api.update_retention_on_payment_submit",
        "on_cancel": "consbiz.api.update_retention_on_payment_cancel"
    },

    "Retention Invoice": {
        "on_submit": "consbiz.api.create_transmittal_from_retention",
        "before_cancel": "consbiz.api.cancel_transmittal_from_retention"
    },

    "Purchase Invoice": {
        "on_submit": "consbiz.api.create_transmittal_entry_for_pi",
        # ใช้ฟังก์ชัน cancel เดียวกันกับ SI ได้ เพราะค้นหาจาก document_no
        "before_cancel": "consbiz.api.cancel_transmittal_entry"
    },

    "Sales Invoice": {
        "on_submit": [
            "consbiz.api.create_retention_receivable",
            "consbiz.api.create_transmittal_entry"
        ],

        "before_cancel": [
            "consbiz.api.cancel_linked_retention_receivable",
            "consbiz.api.cancel_transmittal_entry"
        ]
    }
}

scheduler_events = {
    "daily": [
        # สั่งให้รันฟังก์ชันนี้ทุกวัน (เปลี่ยน path.to.your.app เป็น path จริงของคุณ)
        "consbiz.doctype.retention_receivable.retention_receivable.update_overdue_status_all"
    ]
}


#doc_events = {
#  "Sales Invoice": {
#       "on_submit": "consbiz.api.create_retention_receivable"
#   }
#}
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
	]
}
# jinja = {
# 	"methods": "consbiz.utils.jinja_methods",
# 	"filters": "consbiz.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "consbiz.install.before_install"
# after_install = "consbiz.install.after_install"

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

