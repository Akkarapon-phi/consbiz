# Copyright (c) 2026, Siricons and contributors
# For license information, please see license.txt

# ไอคอนแอปหน้างานบน Desktop เปลี่ยนชื่อจาก "Site App" เป็น "ConsERP" (consbiz/desktop_icon/conserp.json)
# - ลบ Desktop Icon "Site App" เดิม (ถ้ามี)
# - Desktop Layout ที่ผู้ใช้บันทึกไว้เห็นเฉพาะไอคอนใน layout: แทนที่ "Site App" ด้วย ConsERP
#   ไม่มีทั้งสองตัว = ใส่ต่อจาก ConsBiz (ไม่มี ConsBiz = ต่อท้าย)

import json

import frappe

ICON = "ConsERP"
OLD = "Site App"
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
	if frappe.db.exists("Desktop Icon", OLD):
		frappe.delete_doc("Desktop Icon", OLD, ignore_permissions=True, force=True)
	if not frappe.db.exists("Desktop Icon", ICON):
		return
	item = {**frappe.db.get_value("Desktop Icon", ICON, FIELDS, as_dict=True), "child_icons": []}
	for name, layout in frappe.get_all("Desktop Layout", fields=["name", "layout"], as_list=True):
		try:
			items = json.loads(layout or "[]")
		except ValueError:
			continue
		if not isinstance(items, list) or any(i.get("name") == ICON for i in items):
			continue
		old = next((n for n, i in enumerate(items) if i.get("name") == OLD), None)
		if old is not None:
			items[old] = item
		else:
			after = next((n + 1 for n, i in enumerate(items) if i.get("name") == "ConsBiz"), len(items))
			items.insert(after, item)
		frappe.db.set_value("Desktop Layout", name, "layout", json.dumps(items), update_modified=False)
	frappe.cache.delete_key("desktop_icons")
