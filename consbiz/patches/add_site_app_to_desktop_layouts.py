# Copyright (c) 2026, Siricons and contributors
# For license information, please see license.txt

# ไอคอนแอปหน้างาน (Desktop Icon "Site App" -> /site, consbiz/desktop_icon/site_app.json)
# ผู้ใช้ที่เคยจัดหน้า Desktop เอง (Desktop Layout) เห็นเฉพาะไอคอนใน layout ที่บันทึกไว้
# ใส่ไอคอนนี้ต่อจาก ConsBiz ใน layout ของทุกคน (ไม่มี ConsBiz = ต่อท้าย) คนที่มีอยู่แล้วข้าม

import json

import frappe

ICON = "Site App"
FIELDS = (
	"label",
	"bg_color",
	"link",
	"link_type",
	"app",
	"icon_type",
	"parent_icon",
	"icon",
	"link_to",
	"idx",
	"standard",
	"logo_url",
	"hidden",
	"name",
	"restrict_removal",
	"icon_image",
)


def execute():
	if not frappe.db.exists("Desktop Icon", ICON):
		return
	icon = frappe.db.get_value("Desktop Icon", ICON, FIELDS, as_dict=True)
	item = {**icon, "child_icons": []}
	for name, layout in frappe.get_all("Desktop Layout", fields=["name", "layout"], as_list=True):
		try:
			items = json.loads(layout or "[]")
		except ValueError:
			continue
		if not isinstance(items, list) or any(i.get("name") == ICON for i in items):
			continue
		after = next((n + 1 for n, i in enumerate(items) if i.get("name") == "ConsBiz"), len(items))
		items.insert(after, item)
		frappe.db.set_value("Desktop Layout", name, "layout", json.dumps(items), update_modified=False)
	frappe.cache.delete_key("desktop_icons")
