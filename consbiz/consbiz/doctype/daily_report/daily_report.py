# Copyright (c) 2026, Siricons and contributors
# For license information, please see license.txt

# รายงานประจำวัน: กรอกงานที่ทำได้หลายงานในตารางเดียว เลือกงานด้วย WBS ของ Construction Management
# Submit แล้วสร้าง Construction Progress Entry (source = Daily Report) 1 รายการต่อแถว
# Cancel แล้วลบรายการเหล่านั้น ยอดรวมในแผนงานและ S-Curve จริงอัปเดตตาม
# ปริมาณสะสมของแต่ละงาน (ทุกแหล่งรวมกัน) ต้องไม่เกินปริมาณใน BOQ

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate

from consbiz.consbiz.doctype.construction_management.construction_management import (
	PROGRESS_ENTRY,
	TOLERANCE,
	update_actual_progress,
	validate_task_progress,
)


class DailyReport(Document):
	def validate(self):
		tasks = get_leaf_tasks(self.construction_management)
		previous = get_task_totals(self.construction_management, exclude_report=self.name)
		seen = set()
		for row in self.items:
			task = tasks.get((row.wbs or "").strip())
			if not task:
				frappe.throw(
					_("แถว {0}: ไม่พบงาน WBS {1} ใน {2} (เลือกได้เฉพาะงานย่อย ไม่ใช่หัวข้อกลุ่ม)").format(
						row.idx, row.wbs, self.construction_management
					)
				)
			if task.name in seen:
				frappe.throw(_("แถว {0}: งาน {1} ซ้ำกับแถวอื่น").format(row.idx, row.wbs))
			seen.add(task.name)
			self.set_row(row, task, previous.get(task.name, (0, 0)))
		self.total_amount = sum(flt(row.amount) for row in self.items)

	def set_row(self, row, task, previous):
		row.task = task.name
		row.wbs = task.wbs
		row.item_name = task.item_name
		row.group_path = task.group_path
		row.uom = task.uom
		row.boq_qty = flt(task.quantity)
		row.previous_qty, row.previous_percent = previous

		# งานที่มีปริมาณ: qty เป็นหลัก (กรอก % มาอย่างเดียวก็แปลงเป็น qty ให้) งานเหมา: ใช้ %
		if row.boq_qty > 0:
			if flt(row.qty):
				row.percent = flt(row.qty) / row.boq_qty * 100
			else:
				row.qty = flt(row.percent) * row.boq_qty / 100
			row.remaining_qty = flt(row.boq_qty - flt(row.previous_qty) - flt(row.qty), 6)
		else:
			row.qty = 0
			row.remaining_qty = 0

		# มูลค่าตาม % ของมูลค่างาน (งานเหมาไม่มีปริมาณก็คิดได้)
		row.rate = flt(task.rate)
		row.amount = flt(task.amount) * flt(row.percent) / 100

		if flt(row.percent) <= 0:
			frappe.throw(_("แถว {0} ({1}): กรอกปริมาณหรือ % ที่ทำได้").format(row.idx, row.wbs))
		if flt(row.previous_percent) + flt(row.percent) > 100 + TOLERANCE:
			if row.boq_qty > 0:
				message = _("ทำไปแล้ว {0} + วันนี้ {1} = {2} เกินปริมาณ BOQ {3} {4}").format(
					flt(row.previous_qty, 2),
					flt(row.qty, 2),
					flt(flt(row.previous_qty) + flt(row.qty), 2),
					flt(row.boq_qty, 2),
					row.uom or "",
				)
			else:
				message = _("ทำไปแล้ว {0}% + วันนี้ {1}% เกิน 100%").format(
					flt(row.previous_percent, 2), flt(row.percent, 2)
				)
			frappe.throw(_("แถว {0} งาน {1} {2}: {3}").format(row.idx, row.wbs, row.item_name, message))

	def on_submit(self):
		for row in self.items:
			entry = frappe.new_doc(PROGRESS_ENTRY)
			entry.update(
				{
					"construction_management": self.construction_management,
					"task": row.task,
					"date": self.date,
					"qty": row.qty,
					"percent": row.percent,
					"source": "Daily Report",
					"reference_doctype": self.doctype,
					"reference_name": self.name,
				}
			)
			entry.flags.skip_totals = True
			entry.insert(ignore_permissions=True)
		validate_task_progress(self.construction_management, [row.task for row in self.items])
		update_actual_progress(self.construction_management)

	def on_cancel(self):
		for name in frappe.get_all(
			PROGRESS_ENTRY,
			filters={"reference_doctype": self.doctype, "reference_name": self.name},
			pluck="name",
		):
			entry = frappe.get_doc(PROGRESS_ENTRY, name)
			entry.flags.skip_totals = True
			entry.flags.from_reference = True
			entry.delete(ignore_permissions=True)
		update_actual_progress(self.construction_management)


def get_leaf_tasks(construction_management):
	"""งานย่อยของแผน จับคู่ด้วย WBS พร้อม group_path = หัวข้อหลักที่งานนั้นอยู่
	เช่น 1.1.1 ได้ 1 งานเตรียมการ > 1.1 งานสำนักงานสนาม"""
	rows = frappe.get_all(
		"Construction Management Task",
		filters={"parent": construction_management, "parenttype": "Construction Management"},
		fields=[
			"name",
			"wbs",
			"item_name",
			"uom",
			"quantity",
			"rate",
			"amount",
			"start_date",
			"end_date",
			"is_group",
			"indent",
		],
		order_by="idx",
	)
	leaves = {}
	groups = []  # หัวข้อที่ครอบแถวปัจจุบัน เรียงจากบนลงล่าง
	for row in rows:
		while groups and groups[-1].indent >= row.indent:
			groups.pop()
		if row.is_group:
			groups.append(row)
			continue
		row.group_path = " > ".join(f"{g.wbs} {g.item_name}" for g in groups)
		leaves[row.wbs] = row
	return leaves


def get_task_totals(construction_management, exclude_report=None):
	"""ยอดสะสม (qty, %) ของแต่ละงานจากทุกแหล่ง ไม่นับรายการของ Daily Report ฉบับที่ระบุ"""
	entry = frappe.qb.DocType(PROGRESS_ENTRY)
	query = (
		frappe.qb.from_(entry)
		.select(
			entry.task,
			frappe.query_builder.functions.Sum(entry.qty),
			frappe.query_builder.functions.Sum(entry.percent),
		)
		.where(entry.construction_management == construction_management)
		.groupby(entry.task)
	)
	if exclude_report:
		query = query.where((entry.reference_name.isnull()) | (entry.reference_name != exclude_report))
	return {task: (flt(qty), flt(percent)) for task, qty, percent in query.run()}


@frappe.whitelist()
def get_tasks(construction_management, date=None, report=None):
	"""งานย่อยสำหรับเลือกในตาราง พร้อมยอดสะสมและว่าอยู่ในช่วงแผนของวันที่ date หรือไม่"""
	frappe.get_doc("Construction Management", construction_management).check_permission("read")
	day = getdate(date) if date else None
	totals = get_task_totals(construction_management, exclude_report=report)
	tasks = []
	for task in get_leaf_tasks(construction_management).values():
		previous_qty, previous_percent = totals.get(task.name, (0, 0))
		tasks.append(
			{
				**task,
				"previous_qty": previous_qty,
				"previous_percent": previous_percent,
				"in_plan": bool(
					day and task.start_date and getdate(task.start_date) <= day <= getdate(task.end_date)
				),
			}
		)
	return tasks
