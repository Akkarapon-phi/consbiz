# Copyright (c) 2026, Siricons and contributors
# For license information, please see license.txt

# แผนทรัพยากร (แรงงาน / เครื่องจักร) ของแผนงาน 1 ฉบับต่อ Construction Management
# - 1 แถว = งาน × ทรัพยากร × จำนวนต่อวัน ใช้ทุกวันทำงานของงานตามแผนปัจจุบัน (เลื่อนงานในหน้า Gantt แผนทรัพยากรเลื่อนตาม)
# - ชื่อทรัพยากรต้องตรงกับที่หน้างานลงใน Daily Report (ตาราง Manpower / Equipment) จึงเทียบกับที่ใช้จริงได้
# - lead_time_days = จองล่วงหน้ากี่วันก่อนวันเริ่มงาน (แสดงในหน้า Gantt และ Tab ทรัพยากรของ CM)
# - แก้ได้ทั้งในฟอร์มนี้และแผงด้านขวาของงานในหน้า Gantt (construction_management/resources.py)
# รายงาน: Construction Resource Histogram

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt, getdate

from consbiz.consbiz.doctype.construction_management.construction_management import (
	get_task_options,
	working_days_of,
)
from consbiz.consbiz.doctype.daily_report.daily_report import get_default_resources, get_leaf_tasks

RESOURCE_TABLES = (("Labour", "Daily Report Labour", "role"), ("Equipment", "Daily Report Equipment", "equipment"))


class ConstructionResourcePlan(Document):
	def validate(self):
		tasks = get_leaf_tasks(self.construction_management)
		seen = set()
		for row in self.items:
			task = tasks.get((row.wbs or "").strip())
			if not task:
				frappe.throw(
					_("แถว {0}: ไม่พบงานย่อย WBS {1} ใน {2}").format(row.idx, row.wbs, self.construction_management)
				)
			row.task, row.wbs, row.item_name = task.name, task.wbs, task.item_name
			row.resource = (row.resource or "").strip()
			if flt(row.qty_per_day) <= 0:
				frappe.throw(_("แถว {0} ({1}): จำนวนต่อวันต้องมากกว่า 0").format(row.idx, row.wbs))
			if cint(row.lead_time_days) < 0:
				frappe.throw(_("แถว {0} ({1}): จำนวนวันจองล่วงหน้าต้องไม่ติดลบ").format(row.idx, row.wbs))
			key = (row.task, row.resource_type, row.resource)
			if key in seen:
				frappe.throw(_("แถว {0}: {1} ของงาน {2} ซ้ำกับแถวอื่น").format(row.idx, row.resource, row.wbs))
			seen.add(key)


def planned_resources(construction_management, from_date, to_date):
	"""{(ชนิด, ทรัพยากร, วัน): จำนวน} ตามแผนทรัพยากรและวันทำงานของงานในแผนปัจจุบัน"""
	if not frappe.db.exists("Construction Resource Plan", construction_management):
		return {}
	plan = frappe.get_doc("Construction Resource Plan", construction_management)
	doc = frappe.get_doc("Construction Management", construction_management)
	holidays = doc.get_holidays() if doc.use_working_days else set()
	tasks = {row.name: row for row in doc.tasks if not row.is_group}
	start, end = getdate(from_date), getdate(to_date)
	result = {}
	for item in plan.items:
		task = tasks.get(item.task)
		if not task or not task.start_date or not task.end_date:
			continue
		for day in working_days_of(getdate(task.start_date), getdate(task.end_date), holidays):
			if start <= day <= end:
				key = (item.resource_type, item.resource, day)
				result[key] = result.get(key, 0) + flt(item.qty_per_day)
	return result


def actual_resources(construction_management, from_date, to_date):
	"""{(ชนิด, ทรัพยากร, วัน): จำนวน} จาก Daily Report ที่ Submit แล้ว"""
	report = frappe.qb.DocType("Daily Report")
	result = {}
	for resource_type, table, field in RESOURCE_TABLES:
		child = frappe.qb.DocType(table)
		rows = (
			frappe.qb.from_(child)
			.join(report)
			.on(child.parent == report.name)
			.select(child[field], report.date, child.qty)
			.where(
				(child.parenttype == "Daily Report")
				& (report.construction_management == construction_management)
				& (report.docstatus == 1)
				& (report.date[getdate(from_date) : getdate(to_date)])
			)
		).run()
		for resource, date, qty in rows:
			key = (resource_type, (resource or "").strip(), getdate(date))
			result[key] = result.get(key, 0) + cint(qty)
	return result


@frappe.whitelist()
def get_options(construction_management):
	"""ตัวเลือก WBS ของงานย่อยและชื่อทรัพยากรที่เคยลงใน Daily Report (รวมรายการมาตรฐาน)"""
	return {
		"tasks": get_task_options(construction_management),
		**get_default_resources("Daily Report", construction_management),
	}
