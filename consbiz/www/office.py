# Copyright (c) 2026, Siricons and contributors
# For license information, please see license.txt

# แอปออฟฟิศ (/office): หน้าเปล่าที่โหลด Vue (public/js/office_app/ + public/js/shared/)
# จัดซื้อ/ขาย (ต่อไป: บัญชี ประกันผลงาน แอดมิน) ข้อมูลจาก consbiz/site_docs.py
# หมวดจัดซื้อ/ขาย /conserp/purchase, /conserp/sales (website_route_rules), /office และ /site/buy/(po|pi), /site/sell เดิมเด้งมาที่นี่ (website_redirects)

import json
from urllib.parse import quote

import frappe

from consbiz.site_app import office_boot_data

no_cache = 1


def get_context(context):
	if frappe.session.user == "Guest":
		frappe.local.flags.redirect_location = "/login?redirect-to=" + quote(frappe.request.path)
		raise frappe.Redirect

	context.no_cache = 1
	# ใส่ใน <script> ได้ปลอดภัย (ชื่อผู้ใช้มี "</" ไม่ปิดแท็ก)
	context.boot = json.dumps(office_boot_data(), default=str).replace("</", "<\\/")
	context.lang = frappe.local.lang or "th"
	return context
