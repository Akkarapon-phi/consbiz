# Copyright (c) 2026, Siricons and contributors
# For license information, please see license.txt

# ความคืบหน้าจริงรายวันของ 1 งาน (ยอดของวันนั้น ไม่ใช่ยอดสะสม)
# ระบบสร้างให้เอง: จากการกรอกในหน้า Gantt (source = Manual) หรือเมื่อ Submit Daily Report
# งานที่มีปริมาณใน BOQ คิด % จาก qty / quantity ส่วนงานที่ไม่มีปริมาณกรอก % ตรงๆ

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

from consbiz.consbiz.doctype.construction_management.construction_management import (
	update_actual_progress,
	validate_task_progress,
)


class ConstructionProgressEntry(Document):
	def validate(self):
		task = frappe.db.get_value(
			"Construction Management Task",
			{
				"name": self.task,
				"parent": self.construction_management,
				"parenttype": "Construction Management",
			},
			["wbs", "item_name", "quantity", "is_group"],
			as_dict=True,
		)
		if not task:
			frappe.throw(_("ไม่พบงานนี้ใน {0}").format(self.construction_management))
		if task.is_group:
			frappe.throw(_("งาน {0} เป็นหัวข้อกลุ่ม บันทึกความคืบหน้าไม่ได้").format(task.wbs))

		self.wbs = task.wbs
		self.item_name = task.item_name
		quantity = flt(task.quantity)
		if quantity > 0:
			if flt(self.qty):
				self.percent = flt(self.qty) / quantity * 100
			else:
				self.qty = flt(self.percent) * quantity / 100

	def on_trash(self):
		# รายการจาก Daily Report ลบได้ด้วยการ Cancel Daily Report ฉบับนั้นเท่านั้น
		if self.reference_name and not self.flags.from_reference:
			frappe.throw(
				_("รายการนี้มาจาก {0} ให้ Cancel เอกสารนั้นแทน").format(
					frappe.utils.get_link_to_form(self.reference_doctype, self.reference_name)
				)
			)

	def on_update(self):
		self.update_totals()

	def after_delete(self):
		self.update_totals()

	def update_totals(self):
		# บันทึกหลายรายการพร้อมกัน (save_tasks) ตรวจและคำนวณรวมครั้งเดียวตอนท้าย
		if self.flags.skip_totals:
			return
		validate_task_progress(self.construction_management, [self.task])
		update_actual_progress(self.construction_management)
