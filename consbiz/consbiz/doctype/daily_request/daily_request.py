# Copyright (c) 2026, Siricons and contributors
# For license information, please see license.txt

# ขออนุมัติปฏิบัติงานประจำวัน: วางแผนล่วงหน้าว่าวันนั้นจะทำงานไหน ปริมาณเท่าไร ใช้คนและเครื่องจักรอะไร
# ไม่คิดมูลค่าเงิน และไม่สร้าง Construction Progress Entry (ความคืบหน้าจริงมาจาก Daily Report เท่านั้น)
# - % ความคืบหน้าโครงการที่จะเพิ่มขึ้น = % ที่วางแผนของงาน × น้ำหนักงาน (weight) ในแผนงาน
# - สถานะ: Pending (Draft รออนุมัติ) -> Approved (Submit)
#   หรือ Rejected (ปุ่มไม่อนุมัติ แก้แล้วบันทึกใหม่กลับเป็น Pending)
# - ผู้อนุมัติ (approver) ที่เลือกไว้เท่านั้นที่อนุมัติ/ไม่อนุมัติได้ (System Manager ทำแทนได้)
#   บันทึกแล้วระบบมอบหมาย (ToDo) ให้ผู้อนุมัติ อนุมัติ/ไม่อนุมัติ/ยกเลิกแล้วปิดงานที่มอบหมาย
# - อนุมัติแล้วสร้าง Daily Report จากเอกสารนี้ได้ 1 ฉบับ (ดึงงาน คน และเครื่องจักรไปให้กรอกผลจริง)
#   Daily Report ที่ Submit แล้ว = Completed, Cancel Daily Report = กลับเป็น Approved สร้างใหม่ได้

import frappe
from frappe import _
from frappe.desk.form import assign_to
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from frappe.utils import flt, getdate, now_datetime

from consbiz.consbiz.doctype.construction_management.construction_management import (
	TOLERANCE,
	target_progress,
)
from consbiz.consbiz.doctype.daily_report.daily_report import (
	fit_to_remaining,
	get_leaf_tasks,
	get_task_totals,
	over_quantity_hint,
	remove_empty_resources,
)


class DailyRequest(Document):
	def validate(self):
		self.validate_approver()
		remove_empty_resources(self)
		tasks = get_leaf_tasks(self.construction_management)
		totals = get_task_totals(self.construction_management)
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
			self.set_row(row, task, totals.get(task.name, (0, 0)), tasks)

		self.planned_progress = sum(flt(row.project_percent) for row in self.items)
		self.current_progress = flt(
			frappe.db.get_value("Construction Management", self.construction_management, "actual_progress")
		)
		self.expected_progress = min(flt(self.current_progress) + flt(self.planned_progress), 100)
		self.set_plan_comparison()

		# แก้ไขฉบับที่ไม่อนุมัติแล้วบันทึกใหม่ = ส่งขออนุมัติอีกครั้ง
		if self.docstatus == 0:
			self.status = "Pending"
			self.approved_by = self.approved_on = self.rejection_reason = None

	def set_plan_comparison(self):
		"""% แผนสะสม ณ สิ้นวันปฏิบัติงาน (Baseline ถ้าตั้งไว้) และ % คาดการณ์เร็ว-ช้ากว่าแผนเท่าไร"""
		self.baseline_progress, self.plan_basis = target_progress(
			frappe.get_doc("Construction Management", self.construction_management), self.date
		)
		self.progress_variance = flt(self.expected_progress) - self.baseline_progress

	def validate_approver(self):
		if self.approver and not frappe.has_permission(self.doctype, "submit", user=self.approver):
			frappe.throw(
				_("{0} ไม่มีสิทธิ์อนุมัติ Daily Request (ต้องมีสิทธิ์ Submit เช่น Projects Manager)").format(
					self.approver
				)
			)

	def check_approver(self):
		"""ผู้ที่กดอนุมัติ/ไม่อนุมัติต้องเป็นผู้อนุมัติที่ระบุไว้"""
		if frappe.session.user != self.approver and "System Manager" not in frappe.get_roles():
			frappe.throw(
				_("เฉพาะผู้อนุมัติ {0} เท่านั้นที่อนุมัติหรือไม่อนุมัติคำขอนี้ได้").format(
					self.approver_name or self.approver
				),
				frappe.PermissionError,
			)

	def set_row(self, row, task, previous, tasks):
		row.task = task.name
		row.wbs = task.wbs
		row.item_name = task.item_name
		row.group_path = task.group_path
		row.uom = task.uom
		row.boq_qty = flt(task.quantity)
		row.weight = flt(task.weight)
		row.previous_qty, row.previous_percent = previous
		fit_to_remaining(row)
		row.in_plan = int(
			bool(
				task.start_date
				and task.end_date
				and getdate(task.start_date) <= getdate(self.date) <= getdate(task.end_date)
			)
		)

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
		row.project_percent = flt(row.percent) * row.weight / 100

		if flt(row.percent) <= 0:
			frappe.throw(_("แถว {0} ({1}): กรอกปริมาณหรือ % ที่จะทำ").format(row.idx, row.wbs))
		if flt(row.previous_percent) + flt(row.percent) > 100 + TOLERANCE:
			if row.boq_qty > 0:
				message = _("ทำไปแล้ว {0} + แผน {1} = {2} เกินปริมาณ BOQ {3} {4}").format(
					flt(row.previous_qty, 2),
					flt(row.qty, 2),
					flt(flt(row.previous_qty) + flt(row.qty), 2),
					flt(row.boq_qty, 2),
					row.uom or "",
				)
			else:
				message = _("ทำไปแล้ว {0}% + แผน {1}% เกิน 100%").format(
					flt(row.previous_percent, 2), flt(row.percent, 2)
				)
			frappe.throw(
				_("แถว {0} งาน {1} {2}: {3}").format(row.idx, row.wbs, row.item_name, message)
				+ over_quantity_hint(task, tasks)
			)

	def on_update(self):
		if self.docstatus == 0:
			self.assign_approver()

	def assign_approver(self):
		"""มอบหมายให้ผู้อนุมัติคนปัจจุบัน ถ้าเปลี่ยนผู้อนุมัติ ยกเลิกงานที่มอบหมายให้คนเดิม"""
		assigned = False
		for todo in frappe.get_all(
			"ToDo",
			filters={"reference_type": self.doctype, "reference_name": self.name, "status": "Open"},
			fields=["name", "allocated_to"],
		):
			if todo.allocated_to == self.approver:
				assigned = True
			else:
				assign_to.set_status(
					self.doctype, self.name, todo=todo.name, assign_to=todo.allocated_to, ignore_permissions=True
				)
		if not assigned:
			assign_to.add(
				{
					"assign_to": [self.approver],
					"doctype": self.doctype,
					"name": self.name,
					"description": _("ขออนุมัติปฏิบัติงานวันที่ {0} ({1})").format(
						frappe.format(self.date, "Date"), self.construction_management
					),
				}
			)

	def close_assignments(self):
		assign_to.close_all_assignments(self.doctype, self.name, ignore_permissions=True)

	def before_submit(self):
		self.check_approver()
		self.status = "Approved"
		self.approved_by = frappe.session.user
		self.approved_on = now_datetime()
		self.rejection_reason = None

	def on_submit(self):
		self.close_assignments()

	def on_cancel(self):
		self.db_set("status", "Cancelled")
		self.close_assignments()


@frappe.whitelist(methods=["POST"])
def reject(name, reason):
	"""ไม่อนุมัติ: ใช้สิทธิ์ Submit เหมือนการอนุมัติ เอกสารยังเป็น Draft ให้ผู้ขอแก้แล้วบันทึกใหม่"""
	doc = frappe.get_doc("Daily Request", name)
	doc.check_permission("submit")
	doc.check_approver()
	if doc.docstatus != 0:
		frappe.throw(_("ไม่อนุมัติได้เฉพาะเอกสารที่รออนุมัติ"))
	reason = (reason or "").strip()
	if not reason:
		frappe.throw(_("กรุณาระบุเหตุผลที่ไม่อนุมัติ"))
	doc.db_set(
		{
			"status": "Rejected",
			"approved_by": frappe.session.user,
			"approved_on": now_datetime(),
			"rejection_reason": reason,
		}
	)
	doc.add_comment("Comment", _("ไม่อนุมัติ: {0}").format(reason))
	doc.close_assignments()


@frappe.whitelist()
def make_daily_report(source_name, target_doc=None):
	"""Daily Report จากคำขอที่อนุมัติแล้ว ปริมาณตั้งต้นตามแผน ให้แก้เป็นปริมาณที่ทำได้จริงก่อน Submit"""
	existing = get_daily_report(source_name)
	if existing:
		frappe.throw(
			_("คำขอนี้สร้าง Daily Report ไปแล้ว: {0}").format(
				frappe.utils.get_link_to_form("Daily Report", existing)
			)
		)
	return get_mapped_doc(
		"Daily Request",
		source_name,
		{
			"Daily Request": {
				"doctype": "Daily Report",
				"validation": {"docstatus": ["=", 1]},
				"field_map": {"name": "daily_request", "requested_by": "supervisor_name"},
				# naming_series ชื่อ field ตรงกันแต่คนละ series (DRQ- / DR-) ห้ามคัดลอก
				"field_no_map": ["naming_series", "remarks"],
			},
			"Daily Request Item": {
				"doctype": "Daily Report Item",
				"field_no_map": ["remarks"],
			},
			"Daily Report Labour": {"doctype": "Daily Report Labour"},
			"Daily Report Equipment": {"doctype": "Daily Report Equipment"},
		},
		target_doc,
	)


@frappe.whitelist()
def get_daily_report(name):
	"""Daily Report ที่ยังไม่ยกเลิกของคำขอนี้ (ปุ่มในฟอร์มเลือกระหว่าง สร้าง / เปิด)"""
	frappe.get_doc("Daily Request", name).check_permission("read")
	return frappe.db.get_value("Daily Report", {"daily_request": name, "docstatus": ("<", 2)})


@frappe.whitelist()
def get_last_approver(construction_management):
	"""ผู้อนุมัติของคำขอล่าสุดในแผนงานเดียวกัน ใช้เป็นค่าตั้งต้นของคำขอใหม่"""
	last = frappe.get_list(
		"Daily Request",
		filters={"construction_management": construction_management, "docstatus": ("<", 2)},
		fields=["approver"],
		order_by="creation desc",
		limit=1,
	)
	return last[0].approver if last else None

