# Copyright (c) 2026, Siricons and Contributors
# See license.txt

# อัปเดตแผนงานจาก BOQ ฉบับร่าง (ทำแผนไปพร้อมกับ BOQ ได้): ปุ่ม "อัปเดตแผนงาน" ในฟอร์ม BOQ ของแอปและระบบเต็ม
#
# - จับคู่แถวด้วย boq_detail (รหัสแถว BOQ) ไม่เจอใช้ชื่องาน + หน่วย (นำเข้า Excel แบบแทนที่ รหัสแถวใหม่ทั้งหมด)
# - แถวเดิมคงวันที่ งานก่อนหน้า % แผน ส่วนชื่อ/ปริมาณ/หน่วย/ราคา และลำดับ/เลข WBS ตาม BOQ
# - งานที่เพิ่มเองในแผน (boq_detail ว่าง) คงไว้ ติดกับแถว BOQ ที่อยู่ก่อนหน้า หัวข้อที่เพิ่มเองติดกับแถวแรกในกลุ่ม
# - งานเหมา (BOQ ไม่มีปริมาณและยอด) คงมูลค่าที่แก้ในแผน
# - ใช้ได้เมื่อ BOQ ยังเป็นร่างและแผนยังไม่ยืนยัน แถวที่ถูกใช้แล้ว (เอกสารอ้าง WBS / ความคืบหน้า) ห้ามลบ เปลี่ยนเลข หรือกลายเป็นหัวกลุ่ม

import json
from collections import defaultdict

import frappe
from frappe import _
from frappe.utils import flt

from consbiz.consbiz.doctype.construction_management.construction_management import (
	VARIATION_ORDER,
	boq_task_rows,
	get_doc_for_update,
)
from consbiz.consbiz.doctype.construction_management.structure import (
	is_confirmed,
	planned_tasks,
	renumber_nodes,
	update_plan_item_wbs,
	used_tasks,
)

TEXT_FIELDS = (("item_name", "ชื่องาน"), ("uom", "หน่วย"))
VALUE_FIELDS = (("quantity", "ปริมาณ"), ("rate", "ราคาต่อหน่วย"), ("amount", "มูลค่า"))
TOLERANCE = 0.001


def level_of(wbs):
	return (wbs or "").strip(".").count(".")


def name_key(item_name, uom):
	return ((item_name or "").strip(), (uom or "").strip())


def active_plan_of(boq):
	return frappe.db.get_value("Construction Management", {"boq": boq, "status": "Active"}, "name")


def match_rows(rows, source):
	"""{ลำดับแถวใน BOQ: แถวของแผน} เทียบรหัสแถวก่อน แล้วค่อยเทียบชื่องาน + หน่วยกับแถวที่เหลือ"""
	by_detail = {row.boq_detail: row for row in rows if row.boq_detail}
	matched = {}
	for i, task in enumerate(source):
		row = by_detail.get(task["boq_detail"]) if task["boq_detail"] else None
		if row:
			matched[i] = row
	taken = {id(row) for row in matched.values()}
	spare = defaultdict(list)
	for row in rows:
		if row.boq_detail and id(row) not in taken:
			spare[name_key(row.item_name, row.uom)].append(row)
	for i, task in enumerate(source):
		pool = spare.get(name_key(task["item_name"], task["uom"]))
		if i not in matched and pool:
			matched[i] = pool.pop(0)
	return matched


def added_ancestors(rows):
	"""{ชื่อแถว: จำนวนหัวข้อที่เพิ่มเองในแผนที่ครอบแถวนี้}"""
	result, stack = {}, []
	for row in rows:
		level = level_of(row.wbs)
		while stack and stack[-1][0] >= level:
			stack.pop()
		result[row.name] = sum(1 for _level, is_added in stack if is_added)
		stack.append((level, not row.boq_detail))
	return result


def is_ancestor(run, i, next_row):
	level = level_of(run[i].wbs)
	return level < level_of(next_row.wbs) and all(level_of(row.wbs) > level for row in run[i + 1 :])


def glue_added_rows(rows):
	"""งานที่เพิ่มเองติดกับแถว BOQ ไหน: (ต้นตาราง, {แถว: ก่อนแถวนี้}, {แถว: หลังแถวนี้})"""
	head, before, after = [], defaultdict(list), defaultdict(list)
	previous, run = None, []

	def flush(next_row):
		split = len(run)
		if next_row:
			split = next((i for i in range(len(run)) if is_ancestor(run, i, next_row)), len(run))
		(after[previous.name] if previous else head).extend(run[:split])
		if next_row:
			before[next_row.name].extend(run[split:])
		run.clear()

	for row in rows:
		if row.boq_detail:
			flush(row)
			previous = row
		else:
			run.append(row)
	flush(None)
	return head, before, after


class BoqSync:
	"""คำนวณแผนใหม่จาก BOQ บน doc ในหน่วยความจำ บันทึกเมื่อเรียก finish() แล้ว doc.save()"""

	def __init__(self, doc, boq):
		self.doc = doc
		self.source = boq_task_rows(boq)
		self.reason = self.block_reason()
		self.used = used_tasks(doc)
		self.planned = planned_tasks(doc)
		self.tail = [row for row in doc.tasks if row.is_variation]
		self.old = [row for row in doc.tasks if not row.is_variation]
		self.old_wbs = {row.name: row.wbs for row in self.old}
		self.old_groups = {row.name for row in self.old if row.is_group}
		self.matched = match_rows(self.old, self.source)
		kept = {id(row) for row in self.matched.values()}
		self.removed = [row for row in self.old if row.boq_detail and id(row) not in kept]
		self.added, self.changed = [], []
		self.nodes = self.build(kept)
		renumber_nodes(self.nodes)
		self.groups = self.find_groups()
		self.update_matched()
		self.moved = [
			node["row"]
			for node in self.nodes
			if node["row"].name and self.old_wbs[node["row"].name] != node["row"].wbs
		]
		self.blockers = self.find_blockers()

	def block_reason(self):
		if is_confirmed(self.doc):
			return _("แผนงานยืนยันแล้ว (มีแผนสัญญา) อัปเดตจาก BOQ ไม่ได้")
		if frappe.db.exists(VARIATION_ORDER, {"construction_management": self.doc.name, "docstatus": 1}):
			return _("แผนงานมี Variation Order แล้ว อัปเดตจาก BOQ ไม่ได้")
		return None

	@property
	def in_sync(self):
		return not (self.added or self.removed or self.changed or self.moved)

	def build(self, kept):
		survivors = [row for row in self.old if not row.boq_detail or id(row) in kept]
		offsets = added_ancestors(survivors)
		head, before, after = glue_added_rows(survivors)
		nodes = []

		def place(rows, reference, reference_level):
			delta = reference_level - level_of(reference.wbs) if reference else 0
			nodes.extend({"row": row, "level": level_of(row.wbs) + delta} for row in rows)

		place(head, None, 0)
		last_offset, last_level = 0, 0
		for i, task in enumerate(self.source):
			row = self.matched.get(i)
			boq_level = level_of(task["wbs"])
			if row:
				offset = offsets[row.name]
			else:
				# แถวใหม่อยู่ในหัวข้อที่เพิ่มเองเดียวกับแถวก่อนหน้า ถ้าไม่ได้ขึ้นระดับบนกว่า
				offset = last_offset if boq_level >= last_level else 0
			level = boq_level + offset
			if row:
				place(before[row.name], row, level)
				nodes.append({"row": row, "level": level})
				place(after[row.name], row, level)
			else:
				nodes.append({"row": self.new_row(task), "level": level})
			last_offset, last_level = offset, boq_level

		previous = -1
		for node in nodes:
			node["level"] = max(0, min(node["level"], previous + 1))
			previous = node["level"]
		return nodes

	def new_row(self, task):
		start = self.doc.start_date
		row = self.doc.append("tasks", {**task, "start_date": start, "end_date": start, "duration": 1})
		self.added.append(row)
		return row

	def find_groups(self):
		groups = set()
		for i, node in enumerate(self.nodes):
			if i + 1 < len(self.nodes) and self.nodes[i + 1]["level"] > node["level"]:
				groups.add(id(node["row"]))
		return groups

	def update_matched(self):
		for i, task in enumerate(self.source):
			row = self.matched.get(i)
			if row:
				self.update_row(row, task)

	def update_row(self, row, task):
		changes = []
		if row.boq_detail != task["boq_detail"]:
			row.boq_detail = task["boq_detail"]
			changes.append(_("ผูกแถว BOQ ใหม่"))
		for field, label in TEXT_FIELDS:
			if (row.get(field) or "") != (task[field] or ""):
				row.set(field, task[field])
				changes.append(_(label))
		# หัวกลุ่มคิดมูลค่าจากงานย่อย งานเหมาคงมูลค่าที่แก้ในแผน (BOQ ไม่มีปริมาณและยอด)
		is_lump = not flt(task["quantity"]) and not flt(task["amount"])
		if id(row) not in self.groups and not is_lump:
			for field, label in VALUE_FIELDS:
				if abs(flt(row.get(field)) - flt(task[field])) > TOLERANCE:
					row.set(field, flt(task[field]))
					changes.append(_(label))
			# apply_variations คิดปริมาณ/มูลค่าใหม่จากค่าตามสัญญา
			row.contract_quantity = flt(task["quantity"])
			row.contract_amount = flt(task["amount"])
		if changes:
			self.changed.append({"wbs": row.wbs, "item_name": row.item_name, "fields": changes})

	def find_blockers(self):
		blockers = []
		for row in self.removed:
			if row.name in self.used:
				blockers.append(_("{0} {1}: ถูกใช้ในเอกสารแล้ว ลบไม่ได้").format(row.wbs, row.item_name))
			elif row.name in self.planned:
				blockers.append(_("{0} {1}: มีแผนคน-เครื่องจักรหรือวัสดุ ลบรายการเหล่านั้นก่อน").format(row.wbs, row.item_name))
		for row in self.moved:
			if row.name in self.used:
				blockers.append(
					_("{0} {1}: ถูกใช้ในเอกสารแล้ว เลข WBS จะเปลี่ยนเป็น {2} ไม่ได้").format(
						self.old_wbs[row.name], row.item_name, row.wbs
					)
				)
		for node in self.nodes:
			row = node["row"]
			if (
				row.name
				and id(row) in self.groups
				and row.name not in self.old_groups
				and (row.name in self.used or row.name in self.planned)
			):
				blockers.append(_("{0} {1}: ถูกใช้แล้ว เป็นหัวกลุ่มไม่ได้").format(row.wbs, row.item_name))
		return blockers

	def finish(self):
		"""ตัดลิงก์งานก่อนหน้าที่ชี้ไปแถวที่กลายเป็นหัวกลุ่ม (แถวที่ถูกลบ normalize_predecessors ตัดให้) แล้วจัดลำดับแถว"""
		groups = {node["row"].name for node in self.nodes if id(node["row"]) in self.groups}
		for node in self.nodes:
			row = node["row"]
			if row.predecessors:
				links = [link for link in frappe.parse_json(row.predecessors) if link.get("task") not in groups]
				row.predecessors = json.dumps(links) if links else None
		self.doc.tasks = [node["row"] for node in self.nodes] + self.tail
		for idx, row in enumerate(self.doc.tasks, 1):
			row.idx = idx

	def summary(self):
		return {
			"plan": self.doc.name,
			"modified": str(self.doc.modified),
			"reason": self.reason,
			"blockers": self.blockers,
			"in_sync": self.in_sync,
			"can_apply": not self.reason and not self.blockers and not self.in_sync,
			"added": [{"wbs": row.wbs, "item_name": row.item_name} for row in self.added],
			"removed": [{"wbs": self.old_wbs[row.name], "item_name": row.item_name} for row in self.removed],
			"changed": self.changed,
			"moved": len(self.moved),
		}


def access_reason(doc, boq):
	if boq.docstatus != 0:
		return _("BOQ Submit แล้ว งานเพิ่ม-ลดต่อจากนี้ให้ทำผ่าน Variation Order")
	if not doc.has_permission("write") or not doc.has_permlevel_access_to("budget_cost"):
		return _("ไม่มีสิทธิ์แก้มูลค่าในแผนงาน")
	return None


def load(boq):
	boq_doc = frappe.get_doc("BOQ", boq)
	boq_doc.check_permission("read")
	plan = active_plan_of(boq)
	if not plan:
		frappe.throw(_("BOQ นี้ยังไม่มีแผนงาน"))
	return boq_doc, plan


@frappe.whitelist()
def preview_boq_sync(boq):
	"""สรุปสิ่งที่จะเปลี่ยนในแผนงาน (ไม่บันทึก)"""
	boq_doc, plan = load(boq)
	doc = frappe.get_doc("Construction Management", plan)
	doc.check_permission("read")
	result = BoqSync(doc, boq_doc).summary()
	reason = access_reason(doc, boq_doc)
	if reason:
		result.update({"reason": reason, "can_apply": False})
	return result


@frappe.whitelist(methods=["POST"])
def apply_boq_sync(boq, modified):
	boq_doc, plan = load(boq)
	doc = get_doc_for_update(plan, modified)
	sync = BoqSync(doc, boq_doc)
	reason = access_reason(doc, boq_doc) or sync.reason
	if reason:
		frappe.throw(reason)
	if sync.blockers:
		frappe.throw("<br>".join(frappe.utils.escape_html(text) for text in sync.blockers), title=_("อัปเดตแผนงานไม่ได้"))
	sync.finish()
	doc.save()
	update_plan_item_wbs(doc.name, [row for row in sync.moved if row.name])
	return sync.summary()


def check_plan_in_sync(boq):
	"""ก่อน Submit BOQ: แผนที่ยังอัปเดตได้ต้องตรงกับ BOQ ไม่อย่างนั้นแผนจะต่างจาก BOQ ถาวร"""
	plan = active_plan_of(boq.name)
	if not plan:
		return
	sync = BoqSync(frappe.get_doc("Construction Management", plan), boq)
	if not sync.reason and not sync.in_sync:
		frappe.throw(_("แผนงาน {0} ยังไม่ตรงกับ BOQ กดอัปเดตแผนงานก่อน Submit").format(plan))
