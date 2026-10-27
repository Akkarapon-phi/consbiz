# Copyright (c) 2026, Siricons and contributors
# For license information, please see license.txt

# แผนงานก่อสร้างจาก BOQ: 1 แถว BOQ = 1 งาน
# - indent มาจากจำนวนจุดใน WBS ("2" = 0, "2.1" = 1) แถวที่มีแถวลึกกว่าตามหลังคือกลุ่ม
# - น้ำหนัก (%) = มูลค่าที่นับ (counted_amount) / มูลค่าสัญญาปรับปรุง กลุ่มรวมค่าจากงานย่อย
# - วันที่ของกลุ่ม = วันเริ่มแรกสุดและวันจบหลังสุดของงานย่อย
# - งานก่อนหน้า (predecessors): FS/SS/FF/SF + lag (วันทำงาน) งานที่มีงานก่อนหน้าเริ่มเร็วสุดที่ความสัมพันธ์ยอมเสมอ (ASAP)
#   คงจำนวนวันเดิมของงาน อยากให้เริ่มช้ากว่านั้นใช้ lag (หน้า Gantt แปลงการลาก/แก้วันเริ่มเป็น lag ให้) ผูกได้เฉพาะงานย่อย (คำนวณเหมือนกันใน schedule.js: apply_dependencies)
# - %แผนกระจายเท่าๆ กันทุกวันทำงาน หรือตาม plan_distribution ที่กำหนดเองรายช่วง (คำนวณในหน้า Gantt: schedule.js)
# - ความคืบหน้าจริงเก็บเป็นรายวันใน Construction Progress Entry ส่วน actual_qty/progress ในตารางเป็นยอดรวม
# - งานลด-งานเพิ่มมาจาก Variation Order ที่ Submit แล้ว (apply_variations):
#   Submit แล้วงานลดลดปริมาณงานเดิม (DR ลงเกินไม่ได้) และงานเพิ่มเป็นแถวใต้กลุ่ม VO ท้ายตาราง (DR ลงได้)
#   แต่นับในมูลค่าสัญญาและ % ความคืบหน้าเมื่อผู้ว่าจ้างอนุมัติแล้วเท่านั้น (นับตั้งแต่วันที่อนุมัติ counted_from)
# - Baseline เก็บได้หลายชุด (Construction Baseline) ชุดที่ใช้เทียบ (active_baseline) ถูกคัดลอกลงช่อง baseline_* ของแถวงาน
# - % ความคืบหน้า (actual_progress) = มูลค่างานที่ทำแล้ว / มูลค่าสัญญาปรับปรุง (Earned Value)
#   contract_progress = % ตามสัญญาเดิม (ถ่วงด้วยมูลค่าตามสัญญาของงานเดิม ไม่รวมงานเพิ่ม) ไว้อ้างอิง
# หน้า Gantt อยู่ที่ consbiz/consbiz/page/construction_gantt

import datetime
import json

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_months, cint, flt, getdate, nowdate

PROGRESS_ENTRY = "Construction Progress Entry"
BASELINE = "Construction Baseline"
VARIATION_ORDER = "Variation Order"
# WBS ของกลุ่มงานเพิ่มท้ายตาราง งานเพิ่มแต่ละแถวเป็น VO.1, VO.2, ...
VARIATION_GROUP_WBS = "VO"
DISTRIBUTION_UNITS = ("day", "week", "mweek", "month", "quarter")
DEPENDENCY_TYPES = ("FS", "SS", "FF", "SF")
# เผื่อเศษทศนิยมตอนรวม % จากหลายวัน
TOLERANCE = 0.0001


class ConstructionManagement(Document):
	def validate(self):
		if self.is_new() and self.boq and not self.tasks:
			self.set_from_boq()
		self.validate_single_active()
		self.apply_variations()
		self.set_duration()
		holidays = self.get_holidays() if self.use_working_days else set()
		self.set_structure()
		self.set_task_dates(holidays)
		self.apply_dependencies(holidays)
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

	def on_update(self):
		# ปริมาณเปลี่ยน (งานลด/แก้ปริมาณงานเพิ่ม) % ของรายการความคืบหน้าเดิมต้องคิดใหม่จาก qty
		before = self.get_doc_before_save()
		if not before:
			return
		old = {row.name: flt(row.quantity) for row in before.tasks}
		changed = [
			row.name
			for row in self.tasks
			if not row.is_group and flt(row.quantity) > 0 and old.get(row.name, flt(row.quantity)) != flt(row.quantity)
		]
		if changed:
			refresh_entry_percents(self, changed)
			validate_task_progress(self.name, changed)
			update_actual_progress(self.name)

	def on_trash(self):
		frappe.db.delete(PROGRESS_ENTRY, {"construction_management": self.name})
		frappe.db.delete(BASELINE, {"construction_management": self.name})

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

	def apply_variations(self):
		"""ปริมาณ/มูลค่าของงานเดิม = ตามสัญญา - งานลด และแถวงานเพิ่มใต้กลุ่ม VO ท้ายตาราง
		ตาม Variation Order ที่ Submit แล้ว (เรียกซ้ำได้ ผลเหมือนเดิม)"""
		items = [] if self.is_new() else get_variation_items(self.name)
		omitted, approved_omitted = {}, {}
		for item in items:
			item.approved = item.employer_status == "Approved"
			if item.variation_type == "Omission":
				omitted[item.task] = omitted.get(item.task, 0) + flt(item.qty)
				if item.approved:
					approved_omitted[item.task] = approved_omitted.get(item.task, 0) + flt(item.qty)

		main = [row for row in self.tasks if not row.is_variation]
		for row in main:
			if row.is_group:
				continue
			# แผนเดิมก่อนมีงานลด: ค่าปัจจุบันคือค่าตามสัญญา
			if not flt(row.contract_quantity) and not flt(row.contract_amount):
				row.contract_quantity, row.contract_amount = flt(row.quantity), flt(row.amount)
			cut = omitted.get(row.name, 0)
			row.quantity = flt(row.contract_quantity) - cut
			row.amount = flt(row.contract_amount) - cut * flt(row.rate)
			row.counted_amount = flt(row.contract_amount) - approved_omitted.get(row.name, 0) * flt(row.rate)

		current = {row.variation_item: row for row in self.tasks if row.is_variation and row.variation_item}
		group = next((row for row in self.tasks if row.is_variation and not row.variation_item), None)
		leaves = []
		for item in items:
			if item.variation_type != "Addition" or not item.variation_wbs:
				continue
			values = {
				"wbs": item.variation_wbs,
				"item_name": _("(งานเพิ่ม) {0}").format(item.item_name),
				"is_variation": 1,
				"variation_order": item.parent,
				"variation_item": item.name,
				"source_wbs": item.wbs,
				"quantity": flt(item.qty),
				"uom": item.uom,
				"rate": flt(item.rate),
				"amount": flt(item.amount),
				"contract_quantity": 0,
				"contract_amount": 0,
				"counted_amount": flt(item.amount) if item.approved else 0,
				"counted_from": item.employer_approved_on if item.approved else None,
			}
			row = current.pop(item.name, None)
			if row:
				row.update(values)
			else:
				row = self.append("tasks", values)
			leaves.append(row)

		# แถวงานเพิ่มที่จะหายไป (Variation Order ถูกยกเลิก หรือลบแถวเองในฟอร์ม) ต้องยังไม่มีความคืบหน้า
		removed = set(
			frappe.get_all(
				"Construction Management Task",
				filters={"parent": self.name, "parenttype": self.doctype, "is_variation": 1},
				pluck="name",
			)
		) - {row.name for row in leaves}
		if removed and frappe.db.exists(PROGRESS_ENTRY, {"construction_management": self.name, "task": ("in", list(removed))}):
			frappe.throw(_("งานเพิ่มที่มีความคืบหน้าแล้ว ลบออกจากแผนหรือยกเลิก Variation Order ไม่ได้"))

		ordered = [row for row in main]
		if leaves:
			group = group or self.append("tasks", {})
			group.update(
				{
					"wbs": VARIATION_GROUP_WBS,
					"item_name": _("งานเพิ่ม-ลด (Variation Order)"),
					"is_variation": 1,
					"variation_order": None,
					"variation_item": None,
				}
			)
			leaves.sort(key=lambda row: cint(row.wbs.rsplit(".", 1)[-1]))
			ordered += [group, *leaves]
		self.tasks = ordered
		for idx, row in enumerate(self.tasks, 1):
			row.idx = idx

		self.variation_amount = sum(
			flt(item.amount) * (-1 if item.variation_type == "Omission" else 1)
			for item in items
			if item.approved
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

	def apply_dependencies(self, holidays):
		"""งานที่มีงานก่อนหน้าเริ่มวันเร็วสุดที่ความสัมพันธ์ยอม (คงจำนวนวันเดิม) เรียงตามลำดับความสัมพันธ์"""
		rows = {row.name: row for row in self.tasks if row.name}
		links = {}
		for row in self.tasks:
			if row.is_group:
				row.predecessors = None
				continue
			# แถวใหม่ที่ยังไม่ได้บันทึกยังไม่มีชื่อ จึงยังไม่มีงานไหนอ้างถึงได้
			if not row.name:
				continue
			links[row.name] = normalize_predecessors(row, rows)
			row.predecessors = json.dumps(links[row.name]) if links[row.name] else None

		for row in dependency_order(self.tasks, links):
			required = earliest_start(row, links.get(row.name), rows, holidays)
			if required is None or (row.start_date and getdate(row.start_date) == required):
				continue
			duration = max(cint(row.duration), 1)
			row.start_date = required
			row.end_date = add_working_days(required, duration, holidays)
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
		"""total_amount = มูลค่าตามสัญญาเดิม, revised_amount = รวมงานเพิ่ม-ลดที่ผู้ว่าจ้างอนุมัติแล้ว
		น้ำหนัก = มูลค่าที่นับของงาน / มูลค่าสัญญาปรับปรุง (งานเพิ่มที่ยังไม่อนุมัติ = 0)"""
		leaves = [r for r in self.tasks if not r.is_group]
		self.total_amount = sum(flt(r.contract_amount) for r in leaves if not r.is_variation)
		self.revised_amount = flt(self.total_amount) + flt(self.variation_amount)
		for row in leaves:
			row.weight = flt(row.counted_amount) / self.revised_amount * 100 if self.revised_amount else 0
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


def normalize_predecessors(row, rows):
	"""งานก่อนหน้าของแถว [{task, type, lag}] ตัดลิงก์ที่ชี้ไปงานที่ไม่มีแล้ว (เช่น ยกเลิก Variation Order) หรือชี้ตัวเอง
	ลิงก์ซ้ำงานเดียวกันใช้อันหลัง"""
	value = frappe.parse_json(row.predecessors) if isinstance(row.predecessors, str) else row.predecessors
	result = {}
	for link in value or []:
		predecessor = rows.get(link.get("task"))
		if not predecessor or predecessor.name == row.name:
			continue
		if predecessor.is_group:
			frappe.throw(
				_("แถว {0} ({1}): งานก่อนหน้า {2} เป็นหัวข้อกลุ่ม ให้ผูกกับงานย่อยแทน").format(
					row.idx, row.wbs, predecessor.wbs
				)
			)
		link_type = (link.get("type") or "FS").upper()
		if link_type not in DEPENDENCY_TYPES:
			frappe.throw(_("แถว {0} ({1}): ชนิดความสัมพันธ์ {2} ไม่ถูกต้อง").format(row.idx, row.wbs, link_type))
		result[predecessor.name] = {"task": predecessor.name, "type": link_type, "lag": cint(link.get("lag"))}
	return list(result.values())


def dependency_order(tasks, links):
	"""งานย่อยเรียงให้งานก่อนหน้ามาก่อนเสมอ ผูกกันเป็นวง = error
	(ลำดับของงานที่ไม่ขึ้นต่อกันไม่มีผลกับวันที่ จึงไม่ต้องตรงกับ dependency_order ใน schedule.js)"""
	rows = {row.name: row for row in tasks if row.name in links}
	waiting = {name: len(task_links) for name, task_links in links.items()}
	successors = {}
	for name, task_links in links.items():
		for link in task_links:
			successors.setdefault(link["task"], []).append(name)

	ordered = [row for name, row in rows.items() if not waiting[name]]
	for row in ordered:  # ต่อท้ายระหว่างวน: งานที่งานก่อนหน้าครบแล้ว
		for name in successors.get(row.name, []):
			waiting[name] -= 1
			if not waiting[name]:
				ordered.append(rows[name])

	if len(ordered) < len(links):
		stuck = [row.wbs or "" for row in tasks if waiting.get(row.name)]
		frappe.throw(
			_("งานก่อนหน้าผูกกันเป็นวง ตรวจงาน: {0}").format(", ".join(stuck)),
			title=_("ความสัมพันธ์ของงานไม่ถูกต้อง"),
		)
	return ordered


def earliest_start(row, links, rows, holidays):
	"""วันเริ่มเร็วสุดของงานตามงานก่อนหน้าทุกงาน (None = ไม่มีความสัมพันธ์ที่ใช้ได้)"""
	days = [link_start(row, link, rows, holidays) for link in links or []]
	days = [day for day in days if day]
	return max(days) if days else None


def link_start(row, link, rows, holidays):
	"""วันเริ่มเร็วสุดของงานตามลิงก์เดียว (None = งานก่อนหน้ายังไม่มีวันที่)
	FS: เริ่มวันทำงานถัดจากวันจบ, SS: เริ่มวันเดียวกัน, FF: จบวันเดียวกัน, SF: จบวันทำงานก่อนวันเริ่ม
	แล้วเลื่อนอีก lag วันทำงาน (ติดลบ = ซ้อนกันได้)"""
	predecessor = rows[link["task"]]
	if not predecessor.start_date or not predecessor.end_date:
		return None
	start, end, lag = getdate(predecessor.start_date), getdate(predecessor.end_date), link["lag"]
	if link["type"] == "FS":
		return shift_working_days(end, lag + 1, holidays)
	if link["type"] == "SS":
		return shift_working_days(start, lag, holidays)
	if link["type"] == "FF":
		finish = shift_working_days(end, lag, holidays)
	else:
		finish = shift_working_days(start, lag - 1, holidays)
	return shift_working_days(finish, 1 - max(cint(row.duration), 1), holidays)


def shift_working_days(day, days, holidays):
	"""เลื่อนวันไป days วันทำงาน (ติดลบ = ย้อนหลัง) ข้ามวันใน holidays 0 = วันเดิม"""
	day = getdate(day)
	step = datetime.timedelta(days=1 if days > 0 else -1)
	for _i in range(abs(days)):
		day += step
		while day in holidays:
			day += step
	return day


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


def get_variation_items(name):
	"""รายการของ Variation Order ที่ Submit แล้วของแผนงาน เรียงตามวันที่เอกสาร"""
	order = frappe.qb.DocType(VARIATION_ORDER)
	item = frappe.qb.DocType("Variation Order Item")
	return (
		frappe.qb.from_(item)
		.join(order)
		.on(item.parent == order.name)
		.select(
			item.name,
			item.parent,
			order.employer_status,
			order.employer_approved_on,
			item.variation_type,
			item.task,
			item.wbs,
			item.item_name,
			item.uom,
			item.qty,
			item.rate,
			item.amount,
			item.variation_wbs,
		)
		.where(
			(order.construction_management == name)
			& (order.docstatus == 1)
			& (item.parenttype == VARIATION_ORDER)
		)
		.orderby(order.date)
		.orderby(order.name)
		.orderby(item.idx)
		.run(as_dict=True)
	)


# ---------- % แผน (ตรงกับ curve_of / task_daily / segments ใน schedule.js) ----------


def plan_progress(doc, date, baseline=False):
	"""% แผนสะสมของทั้งโครงการ ณ สิ้นวัน date (เส้น plan หรือ baseline ของ S-Curve ในหน้า Gantt)
	baseline ใช้น้ำหนักที่เก็บไว้ตอนตั้ง baseline (baseline ที่ตั้งก่อนมีการเก็บน้ำหนักใช้น้ำหนักปัจจุบัน)"""
	if baseline:
		weight_key = "baseline_weight" if any(flt(r.baseline_weight) for r in doc.tasks) else "weight"
		keys = ("baseline_start_date", "baseline_end_date", "baseline_distribution", weight_key)
	else:
		keys = ("start_date", "end_date", "plan_distribution", "weight")
	start_key, end_key, distribution_key, weight_key = keys
	day = getdate(date)
	holidays = doc.get_holidays() if doc.use_working_days else set()
	total = 0
	for row in doc.tasks:
		if row.is_group or not row.get(start_key) or not row.get(end_key) or not flt(row.get(weight_key)):
			continue
		distribution = frappe.parse_json(row.get(distribution_key)) if row.get(distribution_key) else None
		done = sum(
			fraction
			for d, fraction in task_daily(
				getdate(row.get(start_key)), getdate(row.get(end_key)), distribution, holidays
			)
			if d <= day
		)
		total += flt(row.get(weight_key)) * done
	return total


def target_progress(doc, date):
	"""% แผนที่ใช้เทียบกับ % จริง ณ สิ้นวัน date: Baseline ถ้าตั้งไว้แล้ว ไม่งั้นแผนปัจจุบัน
	คืน (% แผน, "Baseline" หรือ "Current Plan") ตรงกับตัวเลขเร็ว-ช้ากว่าแผนในหน้า Gantt"""
	if any(row.baseline_start_date for row in doc.tasks):
		return plan_progress(doc, date, baseline=True), "Baseline"
	return plan_progress(doc, date), "Current Plan"


def task_daily(start, end, distribution, holidays):
	"""สัดส่วนงานรายวัน [(วัน, สัดส่วน)] รวมกันได้ 1 ไม่ได้กำหนดเอง (หรือจำนวนช่วงไม่ตรง) = เท่ากันทุกวันทำงาน"""
	parts = segments(start, end, distribution.get("unit")) if distribution else None
	weights = (distribution or {}).get("weights") or []
	if not parts or len(parts) != len(weights):
		days = working_days_of(start, end, holidays)
		return [(d, 1 / len(days)) for d in days]
	result = []
	for (part_start, part_end), weight in zip(parts, weights, strict=True):
		days = working_days_of(part_start, part_end, holidays)
		result.extend((d, flt(weight) / 100 / len(days)) for d in days)
	return result


def working_days_of(start, end, holidays):
	"""วันทำงานของช่วง ถ้าทั้งช่วงเป็นวันหยุดให้นับวันปฏิทินแทน"""
	all_days = [start + datetime.timedelta(days=n) for n in range((end - start).days + 1)]
	return [d for d in all_days if d not in holidays] or all_days


def segments(start, end, unit):
	"""ตัดช่วงงานตามขอบของ unit เช่นงาน 5-20 แบ่งสัปดาห์ได้ [5-7], [8-14], [15-20]"""
	result = []
	day = start
	while day <= end:
		to = min(next_period(floor_period(day, unit), unit) - datetime.timedelta(days=1), end)
		result.append((day, to))
		day = to + datetime.timedelta(days=1)
	return result


def floor_period(day, unit):
	if unit == "week":
		return day - datetime.timedelta(days=day.weekday())
	if unit == "mweek":
		return day.replace(day=min((day.day - 1) // 7, 3) * 7 + 1)
	if unit == "month":
		return day.replace(day=1)
	if unit == "quarter":
		return day.replace(month=day.month - (day.month - 1) % 3, day=1)
	if unit == "year":
		return day.replace(month=1, day=1)
	return day


def next_period(day, unit):
	"""วันแรกของช่วงถัดไป (day ต้องเป็นวันแรกของช่วงจาก floor_period)"""
	if unit == "week":
		return day + datetime.timedelta(days=7)
	if unit == "mweek":
		# ช่วงสุดท้ายของเดือน (เริ่มวันที่ 22) ยาวถึงสิ้นเดือน
		if day.day >= 22:
			return getdate(add_months(day.replace(day=1), 1))
		return day + datetime.timedelta(days=7)
	if unit == "month":
		return getdate(add_months(day, 1))
	if unit == "quarter":
		return getdate(add_months(day, 3))
	if unit == "year":
		return day.replace(year=day.year + 1)
	return day + datetime.timedelta(days=1)


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
			row.actual_qty = 0
			row.progress = weighted_progress([r for r in doc.get_descendants(i) if not r.is_group])
	leaves = [r for r in doc.tasks if not r.is_group]
	# มูลค่างานที่ทำแล้ว (งานเพิ่มนับเมื่อผู้ว่าจ้างอนุมัติแล้ว) / มูลค่าสัญญาปรับปรุง
	earned = sum(flt(r.amount) * r.progress / 100 for r in leaves if is_counted(r))
	revised = flt(doc.revised_amount) or flt(doc.total_amount)
	doc.actual_progress = earned / revised * 100 if revised else 0
	contract = sum(flt(r.contract_amount) for r in leaves if not r.is_variation)
	doc.contract_progress = (
		sum(flt(r.contract_amount) * r.progress for r in leaves if not r.is_variation) / contract
		if contract
		else 0
	)


def actual_progress_at(doc, date, rows=(), exclude_report=None):
	"""% จริงของทั้งโครงการ ณ สิ้นวัน date (ตรงกับ actual_curve ใน schedule.js)
	rows: รายการ [{task, percent}] ของวันที่ date ที่ยังไม่ได้เป็น Progress Entry (เช่น Daily Report ที่ยังไม่ Submit)
	exclude_report: ไม่นับ Progress Entry ของเอกสารนี้ (ใช้ rows แทน)
	คืน (% ของ rows, % สะสมรวม rows) ตัวหาร = มูลค่าสัญญาเดิม + งานเพิ่ม-ลดที่อนุมัติแล้ว ณ วันนั้น
	งานเพิ่มนับตั้งแต่วันที่ผู้ว่าจ้างอนุมัติ (counted_from)"""
	day = getdate(date)
	leaves = {
		row.name: row
		for row in doc.tasks
		if not row.is_group and is_counted(row) and (not row.counted_from or getdate(row.counted_from) <= day)
	}
	entries = frappe.get_all(
		PROGRESS_ENTRY,
		filters={"construction_management": doc.name, "date": ("<=", day)},
		fields=["task", "percent", "reference_name"],
	)

	def earned(items):
		return sum(
			flt(leaves[item.task].amount) * flt(item.percent) / 100 for item in items if item.task in leaves
		)

	contract = flt(doc.total_amount) + sum(
		flt(step.amount) for step in get_variation_steps(doc.name) if step.date and getdate(step.date) <= day
	)
	if not contract:
		return 0, 0
	previous = earned([e for e in entries if not exclude_report or e.reference_name != exclude_report])
	today = earned(rows)
	return today / contract * 100, (previous + today) / contract * 100


def is_counted(row):
	"""งานเดิมนับเสมอ งานเพิ่มนับเมื่อผู้ว่าจ้างอนุมัติแล้ว (ต้องตรงกับ is_counted ใน schedule.js)"""
	return not row.is_variation or bool(row.counted_from)


def weighted_progress(leaves):
	"""% เฉลี่ยถ่วงน้ำหนักของงานย่อย กลุ่มงานเพิ่มที่ยังไม่อนุมัติ (น้ำหนัก 0) ถ่วงด้วยมูลค่าแทน"""
	key = "weight" if sum(flt(r.weight) for r in leaves) else "amount"
	total = sum(flt(r.get(key)) for r in leaves)
	return sum(flt(r.get(key)) * flt(r.progress) for r in leaves) / total if total else 0


def refresh_entry_percents(doc, tasks):
	"""% ของรายการความคืบหน้า = qty / ปริมาณปัจจุบันของงาน (เมื่อปริมาณงานเปลี่ยนจากงานลด-งานเพิ่ม)"""
	entry = frappe.qb.DocType(PROGRESS_ENTRY)
	quantities = {row.name: flt(row.quantity) for row in doc.tasks}
	for task in tasks:
		(
			frappe.qb.update(entry)
			.set(entry.percent, entry.qty * (100 / quantities[task]))
			.where((entry.construction_management == doc.name) & (entry.task == task))
		).run()


def update_actual_progress(name):
	"""คำนวณยอดรวมความคืบหน้าใหม่แล้วเขียนตรงลงฐานข้อมูล (ไม่เปลี่ยน modified ของแผนงาน)"""
	doc = frappe.get_doc("Construction Management", name)
	apply_actual_totals(doc, get_progress_entries(name))
	for row in doc.tasks:
		row.db_set({"actual_qty": row.actual_qty, "progress": row.progress}, update_modified=False)
	doc.db_set(
		{"actual_progress": doc.actual_progress, "contract_progress": doc.contract_progress},
		update_modified=False,
	)


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
		"predecessors",
		"baseline_distribution",
		"baseline_weight",
		"is_variation",
		"counted_from",
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
		"variation_amount": doc.variation_amount,
		"revised_amount": doc.revised_amount,
		"contract_progress": doc.contract_progress,
		"variation_steps": get_variation_steps(doc.name),
		"baseline_date": doc.baseline_date,
		"active_baseline": doc.active_baseline,
		"baselines": get_baselines(doc.name),
		"use_working_days": doc.use_working_days,
		"holiday_list": doc.holiday_list,
		"week_by_month": doc.week_by_month,
		"modified": str(doc.modified),
		"version": schedule_version(doc.name),
		"can_write": doc.has_permission("write"),
		"tasks": [{f: row.get(f) for f in fields} for row in doc.tasks],
		"progress_entries": get_progress_entries(doc.name),
		# ส่งวันหยุดเสมอเพื่อแรเงาใน timeline แม้จะนับวันแบบปฏิทิน
		"holidays": get_holiday_dates(doc.holiday_list),
	}


def get_variation_steps(name):
	"""มูลค่าสัญญาที่เปลี่ยน ณ วันที่ผู้ว่าจ้างอนุมัติ Variation Order แต่ละฉบับ (ตัวหารของ S-Curve จริง)"""
	return frappe.get_all(
		VARIATION_ORDER,
		filters={"construction_management": name, "docstatus": 1, "employer_status": "Approved"},
		fields=["employer_approved_on as date", "net_amount as amount"],
		order_by="employer_approved_on asc",
	)


@frappe.whitelist()
def get_schedule_version(name):
	"""ค่าที่เปลี่ยนเมื่อแผนงานหรือความคืบหน้าถูกแก้จากที่อื่น หน้า Gantt ใช้ตรวจว่าต้องโหลดใหม่ไหม"""
	frappe.get_doc("Construction Management", name).check_permission("read")
	return schedule_version(name)


def schedule_version(name):
	entry = frappe.qb.DocType(PROGRESS_ENTRY)
	count, last = (
		frappe.qb.from_(entry)
		.select(frappe.query_builder.functions.Count("*"), frappe.query_builder.functions.Max(entry.modified))
		.where(entry.construction_management == name)
	).run()[0]
	return f"{frappe.db.get_value('Construction Management', name, 'modified')}|{count}|{last}"


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
		if "predecessors" in task:
			row.predecessors = task.get("predecessors") or None
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


def get_baselines(name):
	"""Baseline ทุกชุดของแผนงาน เรียงจากเก่าไปใหม่ (tasks: ดู baseline_snapshot)"""
	return frappe.get_all(
		BASELINE,
		filters={"construction_management": name},
		fields=["name", "title", "baseline_date", "reason", "tasks"],
		order_by="creation asc",
	)


def baseline_snapshot(doc):
	"""แผนปัจจุบันของทุกแถว {ชื่อแถว: [วันเริ่ม, วันจบ, % แผนที่กำหนดเอง, น้ำหนัก]}"""
	return {
		row.name: [
			str(row.start_date) if row.start_date else None,
			str(row.end_date) if row.end_date else None,
			row.plan_distribution or None,
			flt(row.weight),
		]
		for row in doc.tasks
	}


def apply_baseline(doc, baseline):
	"""ใช้ Baseline ชุดนี้เทียบกับความคืบหน้าจริง: คัดลอกลงช่อง baseline_* ของแถวงาน (ในหน่วยความจำ)
	งานที่ไม่มีในชุดนี้ (เช่นงานเพิ่มที่มาทีหลัง) ไม่มี Baseline"""
	rows = frappe.parse_json(baseline.tasks) or {}
	for row in doc.tasks:
		start, end, distribution, weight = rows.get(row.name) or (None, None, None, 0)
		row.baseline_start_date = start
		row.baseline_end_date = end
		row.baseline_distribution = distribution
		row.baseline_weight = weight
	doc.active_baseline = baseline.name
	doc.baseline_date = baseline.baseline_date


def get_baseline(name, baseline):
	doc = frappe.get_doc(BASELINE, baseline)
	if doc.construction_management != name:
		frappe.throw(_("Baseline {0} ไม่ใช่ของแผนงาน {1}").format(doc.title, name))
	return doc


@frappe.whitelist(methods=["POST"])
def save_baseline(name, modified, title, reason=None, activate=1):
	"""บันทึกแผนปัจจุบันเป็น Baseline ชุดใหม่ activate = ใช้ชุดนี้เทียบกับความคืบหน้าจริงด้วย"""
	doc = get_doc_for_update(name, modified)
	baseline = frappe.get_doc(
		{
			"doctype": BASELINE,
			"construction_management": name,
			"title": title,
			"reason": reason,
			"baseline_date": nowdate(),
			"tasks": frappe.as_json(baseline_snapshot(doc), indent=None),
		}
	).insert()
	if cint(activate):
		apply_baseline(doc, baseline)
		doc.save()
	return get_schedule_data(name)


@frappe.whitelist(methods=["POST"])
def activate_baseline(name, modified, baseline):
	"""ใช้ Baseline ชุดนี้เทียบกับความคืบหน้าจริง (Daily Report / Daily Request ที่บันทึกแล้วไม่เปลี่ยน)"""
	doc = get_doc_for_update(name, modified)
	apply_baseline(doc, get_baseline(name, baseline))
	doc.save()
	return get_schedule_data(name)


@frappe.whitelist(methods=["POST"])
def delete_baseline(name, baseline):
	"""ลบ Baseline ชุดที่ไม่ได้ใช้เทียบ คืนรายการ Baseline ที่เหลือ"""
	frappe.get_doc("Construction Management", name).check_permission("write")
	get_baseline(name, baseline).delete()
	return get_baselines(name)
