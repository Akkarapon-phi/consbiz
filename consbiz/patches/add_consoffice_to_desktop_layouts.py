# Copyright (c) 2026, Siricons and contributors
# For license information, please see license.txt

# ไอคอนแอปออฟฟิศ (/office) บน Desktop (consbiz/desktop_icon/consoffice.json)
# Desktop Layout ที่ผู้ใช้บันทึกไว้เห็นเฉพาะไอคอนใน layout: ใส่ต่อจาก ConsERP (ไม่มี = ต่อจาก ConsBiz, ไม่มีทั้งคู่ = ต่อท้าย)

import json

import frappe

from consbiz.patches.add_conserp_to_desktop_layouts import FIELDS

ICON = "ConsOffice"
AFTER = ("ConsERP", "ConsBiz")


def execute():
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
		names = [i.get("name") for i in items]
		after = next((names.index(n) + 1 for n in AFTER if n in names), len(items))
		items.insert(after, item)
		frappe.db.set_value("Desktop Layout", name, "layout", json.dumps(items), update_modified=False)
	frappe.cache.delete_key("desktop_icons")
