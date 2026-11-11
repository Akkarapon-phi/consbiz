# Copyright (c) 2026, Siricons and contributors
# For license information, please see license.txt

# Self Service (/conserp/self): หน้าเปล่าที่โหลด Vue (public/js/self_app/ + public/js/shared/)
# งานของพนักงานแต่ละคน: ลงเวลา ลา สลิป ข้อมูลจาก consbiz/self_service.py (website_route_rules ใน hooks.py)

import json
from urllib.parse import quote

import frappe

from consbiz.self_service import boot_data

no_cache = 1


def get_context(context):
	if frappe.session.user == "Guest":
		frappe.local.flags.redirect_location = "/login?redirect-to=" + quote(frappe.request.path)
		raise frappe.Redirect

	context.no_cache = 1
	# ใส่ใน <script> ได้ปลอดภัย (ชื่อผู้ใช้มี "</" ไม่ปิดแท็ก)
	context.boot = json.dumps(boot_data(), default=str).replace("</", "<\\/")
	context.lang = frappe.local.lang or "th"
	return context
