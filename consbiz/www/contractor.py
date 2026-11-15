# Copyright (c) 2026, Siricons and contributors
# For license information, please see license.txt

# แอปผู้รับเหมาช่วง (/contractor): หน้าเปล่าที่โหลด Vue (public/js/contractor_app/ + public/js/shared/)
# ผู้ใช้ = Website User ที่ผูกกับ Supplier (Portal Users) ข้อมูลจาก consbiz/contractor_app.py (website_route_rules ใน hooks.py)

# เปิดจากลิงก์ของสัญญา /contractor/k/<token>/... ไม่ต้อง login (ตรวจ token ใน contractor_app ทุกคำขอ)

import json
import re
from urllib.parse import quote

import frappe

from consbiz.contractor_app import boot_data

no_cache = 1
TOKEN_PATH = re.compile(r"^/contractor/k/([^/]+)")


def get_context(context):
	match = TOKEN_PATH.match(frappe.request.path)
	token = match.group(1) if match else None
	if not token and frappe.session.user == "Guest":
		frappe.local.flags.redirect_location = "/login?redirect-to=" + quote(frappe.request.path)
		raise frappe.Redirect

	context.no_cache = 1
	context.boot = json.dumps(boot_data(token), default=str).replace("</", "<\\/")
	context.lang = frappe.local.lang or "th"
	return context
