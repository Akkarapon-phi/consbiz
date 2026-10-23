# Copyright (c) 2026, Siricons and contributors
# For license information, please see license.txt

# แผนงานก่อสร้างจาก BOQ: 1 แถว BOQ = 1 งาน
# - indent มาจากจำนวนจุดใน WBS ("2" = 0, "2.1" = 1) แถวที่มีแถวลึกกว่าตามหลังคือกลุ่ม
# - น้ำหนัก (%) = มูลค่างาน / มูลค่ารวมของงานย่อยทั้งหมด กลุ่มรวมค่าจากงานย่อย
# - วันที่ของกลุ่ม = วันเริ่มแรกสุดและวันจบหลังสุดของงานย่อย
# - %แผนกระจายเท่าๆ กันทุกวันทำงาน หรือตาม plan_distribution ที่กำหนดเองรายช่วง (คำนวณในหน้า Gantt: schedule.js)
# - ความคืบหน้าจริงเก็บเป็นรายวันใน Construction Progress Entry ส่วน actual_qty/progress ในตารางเป็นยอดรวม
# หน้า Gantt อยู่ที่ consbiz/consbiz/page/construction_gantt

import datetime
import json

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt, getdate, nowdate

PROGRESS_ENTRY = "Construction Progress Entry"
DISTRIBUTION_UNITS = ("day", "week", "mweek", "month", "quarter")
# เผื่อเศษทศนิยมตอนรวม % จากหลายวัน
TOLERANCE = 0.0001


class ConstructionManagement(Document):
	def validate(self):
		if self.is_new() and self.boq and not self.tasks:
			self.set_from_boq()
		self.validate_single_active()
		self.set_duration()
		holidays = self.get_holidays() if self.use_working_days else set()
		self.set_structure()
		self.set_task_dates(holidays)
		self.roll_up_groups(holidays)
		self.set_weights()
		self.validate_distributions()
		if not self.is_new():
			apply_actual_totals(self, get_progress_entries(self.name))

	def set_from_boq(self):
		"""งานทั้งหมดจาก BOQ ค่าหัวเอกสารที่กรอกไว้แล้วไม่ทับ"""
		plan = get_boq_plan(self.boq)
		for key in ("project", "start_date", "holiday_list"):
			if not self.get(key):
				self.set(key, plan[key])
		self.set("tasks", [{**task, "start_date": self.start_date} for task in plan["tasks"]])

	def on_trash(self):
		frappe.db.delete(PROGRESS_ENTRY, {"construction_management": self.name})

	def validate_single_active(self):
		if self.status != "Active":
			return
		other = frappe.db.get_value(
			"Construction Management",
			{"boq": self.boq, "status": "Active", "name": ("!=", self.name)},
		)
		if other:
			frappe.throw(
				_("BOQ {0} มีแผนงานที่ใช้งานอยู่แล้ว ({1}) ให้เปลี่ยนสถานะฉบับเดิมเป็น Inactive ก่อน").format(
					self.boq, frappe.utils.get_link_to_form("Construction Management", other)
				)
			)

	def set_duration(self):
		"""ระยะเวลาสัญญา (วัน) นับรวมวันแรก"""
		if self.start_date and self.finish_date:
			if getdate(self.finish_date) < getdate(self.start_date):
				frappe.throw(_("วันที่สิ้นสุดสัญญาต้องไม่ก่อนวันที่เริ่มสัญญา"))
			self.duration = (getdate(self.finish_date) - getdate(self.start_date)).days + 1
		else:
			self.duration = 0

	def get_holidays(self):
		return {getdate(d) for d in get_holiday_dates(self.holiday_list)}

	def set_structure(self):
		# Daily Report เลือกงานด้วย WBS จึงห้ามซ้ำ
		seen = set()
		for row in self.tasks:
			wbs = (row.wbs or "").strip()
			if wbs in seen:
				frappe.throw(_("WBS {0} ซ้ำกันในแผนงาน (แถว {1})").format(wbs, row.idx))
			seen.add(wbs)
			row.indent = wbs.strip(".").count(".")
		for i, row in enumerate(self.tasks):
			next_row = self.tasks[i + 1] if i + 1 < len(self.tasks) else None
			row.is_group = 1 if next_row and next_row.indent > row.indent else 0

	def set_task_dates(self, holidays):
		for row in self.tasks:
			if row.is_group:
				continue
			if not row.start_date:
				if row.end_date:
					frappe.throw(_("แถว {0}: ใส่วันจบแล้วต้องใส่วันเริ่มด้วย").format(row.idx))
				row.duration = 0
				continue

			if not row.end_date:
				row.end_date = add_working_days(row.start_date, max(cint(row.duration), 1), holidays)
			if getdate(row.end_date) < getdate(row.start_date):
				frappe.throw(_("แถว {0} ({1}): วันจบต้องไม่ก่อนวันเริ่ม").format(row.idx, row.wbs))
			row.duration = count_working_days(row.start_date, row.end_date, holidays)

	def roll_up_groups(self, holidays):
		for i, row in enumerate(self.tasks):
			if not row.is_group:
				continue
			leaves = [r for r in self.get_descendants(i) if not r.is_group]
			row.amount = sum(flt(r.amount) for r in leaves)
			for start_field, end_field in (
				("start_date", "end_date"),
				("baseline_start_date", "baseline_end_date"),
			):
				starts = [getdate(r.get(start_field)) for r in leaves if r.get(start_field)]
				ends = [getdate(r.get(end_field)) for r in leaves if r.get(end_field)]
				row.set(start_field, min(starts) if starts else None)
				row.set(end_field, max(ends) if ends else None)
			row.duration = count_working_days(row.start_date, row.end_date, holidays) if row.start_date else 0

	def set_weights(self):
		leaves = [r for r in self.tasks if not r.is_group]
		self.total_amount = sum(flt(r.amount) for r in leaves)
		for row in leaves:
			row.weight = flt(row.amount) / self.total_amount * 100 if self.total_amount else 0
		for i, row in enumerate(self.tasks):
			if row.is_group:
				row.weight = sum(flt(r.weight) for r in self.get_descendants(i) if not r.is_group)

	def validate_distributions(self):
		for row in self.tasks:
			if row.is_group:
				row.plan_distribution = None
			elif row.plan_distribution:
				row.plan_distribution = normalize_distribution(row.plan_distribution, row)

	def get_descendants(self, index):
		indent = self.tasks[index].indent
		descendants = []
		for row in self.tasks[index + 1 :]:
			if row.indent <= indent:
				break
			descendants.append(row)
		return descendants


def normalize_distribution(value, row):
	"""ตรวจ % แผนที่กำหนดเอง { unit, weights } ต้องไม่ติดลบและรวมได้ 100"""
	data = frappe.parse_json(value) if isinstance(value, str) else value
	if not data:
		return None
	weights = [flt(w, 6) for w in data.get("weights") or []]
	if data.get("unit") not in DISTRIBUTION_UNITS or not weights or any(w < 0 for w in weights):
		frappe.throw(_("แถว {0} ({1}): รูปแบบ % แผนที่กำหนดเองไม่ถูกต้อง").format(row.idx, row.wbs))
	if abs(sum(weights) - 100) > 0.01:
		frappe.throw(
			_("แถว {0} ({1}): % แผนที่กำหนดเองรวมได้ {2}% ต้องรวมได้ 100%").format(
				row.idx, row.wbs, flt(sum(weights), 2)
			)
		)
	return json.dumps({"unit": data["unit"], "weights": weights})


def get_holiday_dates(holiday_list):
	if not holiday_list:
		return []
	return frappe.get_all(
		"Holiday",
		filters={"parenttype": "Holiday List", "parent": holiday_list},
		pluck="holiday_date",
		order_by="holiday_date",
	)


def count_working_days(start_date, end_date, holidays):
	"""จำนวนวันรวมวันเริ่มและวันจบ ไม่นับวันใน holidays"""
	start, end = getdate(start_date), getdate(end_date)
	days = (end - start).days + 1
	if not holidays or days <= 0:
		return max(days, 0)
	return sum(1 for n in range(days) if start + datetime.timedelta(days=n) not in holidays)


def add_working_days(start_date, duration, holidays):
	"""วันจบของงานที่เริ่ม start_date และใช้เวลา duration วัน (นับเฉพาะวันที่ไม่อยู่ใน holidays)"""
	day = getdate(start_date)
	remaining = duration
	while True:
		if day not in holidays:
			remaining -= 1
			if remaining <= 0:
				return day
		day += datetime.timedelta(days=1)


# ---------- ความคืบหน้าจริง ----------


def get_progress_entries(name, tasks=None):
	filters = {"construction_management": name}
	if tasks is not None:
		filters["task"] = ("in", list(tasks))
	return frappe.get_all(
		PROGRESS_ENTRY,
		filters=filters,
		fields=["name", "task", "date", "qty", "percent", "source"],
		order_by="date asc, creation asc",
	)


def apply_actual_totals(doc, entries):
	"""ใส่ยอดรวม actual_qty / progress ให้แถวงาน กลุ่ม และหัวเอกสาร (ในหน่วยความจำ)"""
	qty, percent = {}, {}
	for entry in entries:
		qty[entry.task] = qty.get(entry.task, 0) + flt(entry.qty)
		percent[entry.task] = percent.get(entry.task, 0) + flt(entry.percent)

	for row in doc.tasks:
		if not row.is_group:
			row.actual_qty = qty.get(row.name, 0)
			row.progress = min(max(percent.get(row.name, 0), 0), 100)
	for i, row in enumerate(doc.tasks):
		if row.is_group:
			leaves = [r for r in doc.get_descendants(i) if not r.is_group]
			weight = sum(flt(r.weight) for r in leaves)
			row.actual_qty = 0
			row.progress = sum(flt(r.weight) * r.progress for r in leaves) / weight if weight else 0
	doc.actual_progress = sum(flt(r.weight) * r.progress / 100 for r in doc.tasks if not r.is_group)


def update_actual_progress(name):
	"""คำนวณยอดรวมความคืบหน้าใหม่แล้วเขียนตรงลงฐานข้อมูล (ไม่เปลี่ยน modified ของแผนงาน)"""
	doc = frappe.get_doc("Construction Management", name)
	apply_actual_totals(doc, get_progress_entries(name))
	for row in doc.tasks:
		row.db_set({"actual_qty": row.actual_qty, "progress": row.progress}, update_modified=False)
	doc.db_set("actual_progress", doc.actual_progress, update_modified=False)


def validate_task_progress(name, tasks):
	"""ยอดสะสมของแต่ละงานต้องอยู่ระหว่าง 0-100% ทุกวัน (ปริมาณรวมไม่เกินปริมาณใน BOQ)"""
	running = {}
	for entry in get_progress_entries(name, tasks):
		running[entry.task] = running.get(entry.task, 0) + flt(entry.percent)
		if running[entry.task] > 100 + TOLERANCE or running[entry.task] < -TOLERANCE:
			wbs = frappe.db.get_value("Construction Management Task", entry.task, "wbs")
			frappe.throw(
				_("งาน {0}: ความคืบหน้าสะสม ณ วันที่ {1} เป็น {2}% ต้องอยู่ระหว่าง 0-100%").format(
					wbs, frappe.format(entry.date, "Date"), flt(running[entry.task], 2)
				)
			)


# ---------- API ของหน้า Gantt และฟอร์ม BOQ ----------


@frappe.whitelist()
def create_from_boq(boq):
	doc = frappe.new_doc("Construction Management")
	doc.boq = boq
	doc.set_from_boq()
	doc.insert()
	return doc.name


@frappe.whitelist()
def get_boq_plan(boq):
	"""ค่าตั้งต้นของแผนจาก BOQ: โครงการ วันเริ่ม ปฏิทินวันหยุด และงาน 1 แถวต่อ 1 แถว BOQ (ยังไม่มีวันเริ่มงาน)"""
	boq_doc = frappe.get_doc("BOQ", boq)
	boq_doc.check_permission("read")
	if boq_doc.docstatus == 2:
		frappe.throw(_("BOQ {0} ถูกยกเลิกแล้ว").format(boq))

	return {
		"project": find_project(boq_doc.project),
		"start_date": boq_doc.date or nowdate(),
		"holiday_list": boq_doc.company
		and frappe.get_cached_value("Company", boq_doc.company, "default_holiday_list"),
		"tasks": [
			{
				"wbs": row.wbs,
				"item_name": row.item_name,
				"boq_detail": row.name,
				"quantity": row.quantity,
				"uom": row.uom,
				"rate": flt(row.material_rate) + flt(row.labour_rate),
				"amount": row.total_amount,
				"duration": 1,
			}
			for row in boq_doc.boq_details
		],
	}


def find_project(value):
	"""Project ที่ตรงกับข้อความ project ใน BOQ (ตรงกับเลขที่หรือชื่อโครงการ) ไม่เจอ = None"""
	if not value:
		return None
	if frappe.db.exists("Project", value):
		return value
	return frappe.db.get_value("Project", {"project_name": value})


@frappe.whitelist()
def get_schedule_data(name):
	doc = frappe.get_doc("Construction Management", name)
	doc.check_permission("read")
	fields = (
		"name",
		"idx",
		"wbs",
		"item_name",
		"is_group",
		"indent",
		"quantity",
		"uom",
		"amount",
		"weight",
		"start_date",
		"end_date",
		"duration",
		"baseline_start_date",
		"baseline_end_date",
		"actual_qty",
		"progress",
		"plan_distribution",
		"baseline_distribution",
	)
	return {
		"name": doc.name,
		"boq": doc.boq,
		"project": doc.project,
		"project_name": frappe.db.get_value("Project", doc.project, "project_name") if doc.project else None,
		"customer": doc.customer,
		"start_date": doc.start_date,
		"finish_date": doc.finish_date,
		"duration": doc.duration,
		"employer": doc.employer,
		"contractor": doc.contractor,
		"supervisor": doc.supervisor,
		"total_amount": doc.total_amount,
		"actual_progress": doc.actual_progress,
		"baseline_date": doc.baseline_date,
		"use_working_days": doc.use_working_days,
		"holiday_list": doc.holiday_list,
		"week_by_month": doc.week_by_month,
		"modified": str(doc.modified),
		"can_write": doc.has_permission("write"),
		"tasks": [{f: row.get(f) for f in fields} for row in doc.tasks],
		"progress_entries": get_progress_entries(doc.name),
		# ส่งวันหยุดเสมอเพื่อแรเงาใน timeline แม้จะนับวันแบบปฏิทิน
		"holidays": get_holiday_dates(doc.holiday_list),
	}


def get_doc_for_update(name, modified):
	doc = frappe.get_doc("Construction Management", name)
	doc.check_permission("write")
	if str(doc.modified) != modified:
		frappe.throw(_("แผนงานนี้ถูกแก้ไขหลังจากที่คุณเปิด กรุณาโหลดหน้าใหม่"), frappe.TimestampMismatchError)
	return doc


@frappe.whitelist(methods=["POST"])
def save_tasks(name, tasks, modified, progress=None):
	"""บันทึกจากหน้า Gantt
	tasks: วันเริ่ม/วันจบ/% แผนที่กำหนดเองของงานย่อย (แถวกลุ่มคำนวณใหม่ใน validate)
	progress: ยอดที่กรอกเอง [{task, date, qty, percent}] 1 รายการต่องานต่อวัน ค่า 0 = ลบรายการนั้น"""
	doc = get_doc_for_update(name, modified)

	rows = {row.name: row for row in doc.tasks}
	for task in frappe.parse_json(tasks):
		row = rows.get(task.get("name"))
		if not row or row.is_group:
			continue
		row.start_date = task.get("start_date") or None
		row.end_date = task.get("end_date") or None
		if "plan_distribution" in task:
			row.plan_distribution = task.get("plan_distribution") or None
	doc.save()

	touched = set()
	for item in frappe.parse_json(progress or "[]"):
		row = rows.get(item.get("task"))
		if not row or row.is_group:
			continue
		touched.add(row.name)
		save_manual_progress(doc.name, row, getdate(item.get("date")), item.get("qty"), item.get("percent"))
	if touched:
		validate_task_progress(doc.name, touched)
		update_actual_progress(doc.name)

	return get_schedule_data(name)


def save_manual_progress(name, row, date, qty, percent):
	existing = frappe.db.get_value(
		PROGRESS_ENTRY,
		{"construction_management": name, "task": row.name, "date": date, "source": "Manual"},
	)
	if not flt(qty) and not flt(percent):
		if existing:
			entry = frappe.get_doc(PROGRESS_ENTRY, existing)
			entry.flags.skip_totals = True
			entry.delete()
		return

	entry = frappe.get_doc(PROGRESS_ENTRY, existing) if existing else frappe.new_doc(PROGRESS_ENTRY)
	entry.update(
		{
			"construction_management": name,
			"task": row.name,
			"date": date,
			"qty": flt(qty),
			"percent": flt(percent),
			"source": "Manual",
		}
	)
	entry.flags.skip_totals = True
	entry.save()


@frappe.whitelist(methods=["POST"])
def set_baseline(name, modified):
	"""เก็บวันเริ่ม/วันจบปัจจุบันของทุกงานเป็น Baseline (ทับของเดิม)"""
	doc = get_doc_for_update(name, modified)
	for row in doc.tasks:
		row.baseline_start_date = row.start_date
		row.baseline_end_date = row.end_date
		row.baseline_distribution = row.plan_distribution
	doc.baseline_date = nowdate()
	doc.save()
	return get_schedule_data(name)
