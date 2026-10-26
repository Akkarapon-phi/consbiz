# Copyright (c) 2026, Siricons and contributors
# For license information, please see license.txt

# รายงานประจำวัน: กรอกงานที่ทำได้หลายงานในตารางเดียว เลือกงานด้วย WBS ของ Construction Management
# Submit แล้วสร้าง Construction Progress Entry (source = Daily Report) 1 รายการต่อแถว
# Cancel แล้วลบรายการเหล่านั้น ยอดรวมในแผนงานและ S-Curve จริงอัปเดตตาม
# ปริมาณสะสมของแต่ละงาน (ทุกแหล่งรวมกัน) ต้องไม่เกินปริมาณใน BOQ ส่วนที่เกินให้ทำ Variation Order แล้วลงในงาน (งานเพิ่ม)
# สร้างจาก Daily Request ได้ 1 ฉบับต่อคำขอ: Submit แล้วคำขอเป็น Completed, Cancel แล้วกลับเป็น Approved

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt, getdate

from consbiz.consbiz.doctype.construction_management.construction_management import (
	PROGRESS_ENTRY,
	TOLERANCE,
	update_actual_progress,
	validate_task_progress,
)

# รายการตั้งต้นของตาราง Manpower / Equipment ในเอกสารใหม่ (แถวที่ไม่กรอกจำนวนถูกลบตอนบันทึก)
DEFAULT_LABOUR = ("วิศวกร", "โฟร์แมน", "หัวหน้าคนงาน", "คนงาน")
DEFAULT_EQUIPMENT = (
	"รถขุด (แบ็คโฮ)",
	"รถบรรทุก",
	"รถเครน",
	"รถบดอัด",
	"เครื่องจี้คอนกรีต",
	"เครื่องตัด-ดัดเหล็ก",
	"เครื่องปั่นไฟ",
)


class DailyReport(Document):
	def validate(self):
		self.validate_daily_request()
		remove_empty_resources(self)
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
			self.set_row(row, task, previous.get(task.name, (0, 0)), tasks)
		self.total_amount = sum(flt(row.amount) for row in self.items)

	def before_insert(self):
		# Amend: daily_request เป็น no_copy (Duplicate ไม่ติดไป) แต่ฉบับแก้ไขต้องอ้างคำขอเดิม
		if self.amended_from and not self.daily_request:
			self.daily_request = frappe.db.get_value("Daily Report", self.amended_from, "daily_request")

	def validate_daily_request(self):
		"""คำขออนุมัติที่อ้างถึงต้องอนุมัติแล้ว เป็นแผนงานเดียวกัน และยังไม่มีรายงานฉบับอื่น (ที่ไม่ได้ยกเลิก)"""
		if not self.daily_request:
			return
		request = frappe.db.get_value(
			"Daily Request", self.daily_request, ["docstatus", "construction_management"], as_dict=True
		)
		if not request or request.docstatus != 1:
			frappe.throw(_("Daily Request {0} ยังไม่ได้รับอนุมัติ").format(self.daily_request))
		if request.construction_management != self.construction_management:
			frappe.throw(
				_("Daily Request {0} เป็นของแผนงาน {1}").format(
					self.daily_request, request.construction_management
				)
			)
		other = frappe.db.get_value(
			"Daily Report",
			{"daily_request": self.daily_request, "docstatus": ("<", 2), "name": ("!=", self.name)},
		)
		if other:
			frappe.throw(
				_("Daily Request {0} มี Daily Report แล้ว: {1}").format(
					self.daily_request, frappe.utils.get_link_to_form("Daily Report", other)
				)
			)

	def set_request_status(self, status):
		if self.daily_request:
			frappe.db.set_value("Daily Request", self.daily_request, "status", status)

	def set_row(self, row, task, previous, tasks):
		row.task = task.name
		row.wbs = task.wbs
		row.item_name = task.item_name
		row.group_path = task.group_path
		row.uom = task.uom
		row.boq_qty = flt(task.quantity)
		row.previous_qty, row.previous_percent = previous
		fit_to_remaining(row)

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
			frappe.throw(
				_("แถว {0} งาน {1} {2}: {3}").format(row.idx, row.wbs, row.item_name, message)
				+ over_quantity_hint(task, tasks)
			)

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
		self.set_request_status("Completed")

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
		self.set_request_status("Approved")


def fit_to_remaining(row):
	"""จอแสดงทศนิยมตาม precision (เช่น 2 ตำแหน่ง) คงเหลือจริง 0.5488 แสดงเป็น 0.55
	ผู้ใช้กรอกตามที่เห็นแล้วเกินไม่ถึงครึ่งหน่วยของทศนิยมที่แสดง = ทำครบพอดี ปรับเป็นคงเหลือจริง
	(ต้องตรงกับ consbiz.fit_to_remaining ใน public/js/utils.js)"""
	if flt(row.boq_qty) > 0 and flt(row.qty):
		field, total, previous = "qty", flt(row.boq_qty), flt(row.previous_qty)
	elif flt(row.boq_qty) <= 0 and flt(row.percent):
		field, total, previous = "percent", 100, flt(row.previous_percent)
	else:
		return
	over = previous + flt(row.get(field)) - total
	if 0 < over < 0.5 / 10 ** cint(row.precision(field) or 3):
		row.set(field, total - previous)


def over_quantity_hint(task, tasks):
	"""คำแนะนำต่อท้าย error ปริมาณเกิน: ส่วนที่เกินของงานเดิมให้ลงในงานเพิ่ม (VO) ที่อ้างงานนั้น"""
	if task.is_variation:
		return ""
	variations = [t.wbs for t in tasks.values() if t.source_wbs == task.wbs]
	if variations:
		return "<br>" + _("ส่วนที่เกินให้ลงในงานเพิ่ม {0}").format(", ".join(variations))
	return "<br>" + _("ถ้าเป็นงานเพิ่ม ให้ทำ Variation Order (งานลด-งานเพิ่ม) แล้วลงส่วนที่เกินในงานเพิ่มนั้น")


def remove_empty_resources(doc):
	"""ตัดแถว Manpower / Equipment ที่ไม่ได้กรอกจำนวน (แถวตั้งต้นที่ไม่ได้ใช้)"""
	doc.labour = [row for row in doc.labour if cint(row.qty) > 0]
	doc.equipment = [row for row in doc.equipment if cint(row.qty) > 0 or flt(row.hours) > 0]
	for table in (doc.labour, doc.equipment):
		for idx, row in enumerate(table, 1):
			row.idx = idx


@frappe.whitelist()
def get_default_resources(doctype, construction_management=None):
	"""รายชื่อตั้งต้นของ Manpower / Equipment: รายการจากเอกสารล่าสุดของแผนงานเดียวกัน (ไม่เอาจำนวน)
	ตามด้วยรายการมาตรฐานที่ยังไม่มี ผู้ใช้กรอกแค่จำนวน"""
	if doctype not in ("Daily Report", "Daily Request"):
		frappe.throw(_("ไม่รองรับ {0}").format(doctype))
	labour, equipment = [], []
	last = construction_management and frappe.get_all(
		doctype,
		filters={"construction_management": construction_management, "docstatus": ("<", 2)},
		order_by="date desc, creation desc",
		limit=1,
		pluck="name",
	)
	if last:
		last = frappe.get_doc(doctype, last[0])
		last.check_permission("read")
		labour = [row.role for row in last.labour]
		equipment = [row.equipment for row in last.equipment]
	return {
		"labour": labour + [role for role in DEFAULT_LABOUR if role not in labour],
		"equipment": equipment + [item for item in DEFAULT_EQUIPMENT if item not in equipment],
	}


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
			"weight",
			"start_date",
			"end_date",
			"is_group",
			"indent",
			"is_variation",
			"source_wbs",
			"contract_quantity",
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
