# Copyright (c) 2026, Siricons and Contributors
# See license.txt

# แก้โครงสร้างงานของแผน: เพิ่มงาน / เพิ่มงานย่อย / Indent / Outdent / ลบ (หน้าแก้แผนงานของ ConsERP)
#
# - งานจาก BOQ / VO = มูลค่าสัญญา ลบไม่ได้และเป็นหัวกลุ่มแทนไม่ได้ (มูลค่าของกลุ่มคิดจากงานลูก มูลค่าเดิมจะหาย)
# - งานที่เพิ่มในแผน (boq_detail ว่าง) มูลค่า 0: ใช้จัดลำดับเวลาหรือเป็นหัวกลุ่ม ไม่มีผลต่อ % รวม
# - ระดับงานคิดจากจุดในเลข WBS (set_structure) และเอกสารอื่นอ้างงานด้วยเลข WBS เป็นข้อความ:
#   ยังไม่มีเอกสารอ้าง = รันเลขใหม่ทั้งแผน
#   มีเอกสารอ้างแล้ว = งานที่ถูกใช้ย้าย/ลบไม่ได้ งานอื่นคงเลขเดิม งานใหม่/งานที่ย้ายได้เลขถัดไปที่ว่างท้ายกลุ่ม
# - บันทึก Baseline ชุดแรก = ยืนยันแผน: ปิดการแก้โครงสร้างทั้งหมด WBS มาจาก BOQ / VO เท่านั้น
#   ยกเลิกการยืนยันได้จนกว่าแผนจะถูกใช้งาน (unconfirm_plan)

import frappe
from frappe import _
from frappe.query_builder import DocType
from frappe.utils import cint, flt

from consbiz.consbiz.doctype.construction_management.construction_management import (
	BASELINE,
	PROGRESS_ENTRY,
	get_doc_for_update,
	get_schedule_data,
)

# เอกสารที่อ้างงานด้วยเลข WBS: (ตารางลูก, เอกสารแม่, ช่องที่ผูกแผน, ช่อง WBS)
CHILD_REFERENCES = (
	("Daily Report Item", "Daily Report", "construction_management", "wbs"),
	("Daily Request Item", "Daily Request", "construction_management", "wbs"),
	("Punch List Item", "Punch List", "construction_management", "wbs"),
	("Variation Order Item", "Variation Order", "construction_management", "wbs"),
)
HEADER_REFERENCES = ("Concrete Usage", "Inspection Request")
# (ตารางลูก, เอกสารแม่, ช่องที่ผูกโครงการ, ช่อง WBS)
PROJECT_REFERENCES = (
	("Stock Entry Detail", "Stock Entry", "project", "custom_wbs"),
	("Material Request Item", "Material Request", "custom_project", "custom_wbs"),
)
PLAN_ITEMS = ("Construction Resource Plan Item", "Construction Material Plan Item")


def child_wbs(child, parent, link_field, wbs_field, value):
	if not frappe.get_meta(child).has_field(wbs_field):
		return []
	item, doc = DocType(child), DocType(parent)
	return (
		frappe.qb.from_(item)
		.join(doc)
		.on(doc.name == item.parent)
		.select(item[wbs_field])
		.where(doc[link_field] == value)
		.where(doc.docstatus < 2)
		.where(item[wbs_field].isnotnull())
		.distinct()
	).run(pluck=True)


def referenced_wbs(doc):
	"""เลข WBS ที่มีเอกสาร (ไม่นับใบที่ยกเลิก) อ้างถึง"""
	used = set()
	for child, parent, link_field, wbs_field in CHILD_REFERENCES:
		used.update(child_wbs(child, parent, link_field, wbs_field, doc.name))
	for doctype in HEADER_REFERENCES:
		used.update(
			frappe.get_all(
				doctype, filters={"construction_management": doc.name, "docstatus": ("<", 2)}, pluck="wbs"
			)
		)
	if doc.project:
		for child, parent, link_field, wbs_field in PROJECT_REFERENCES:
			used.update(child_wbs(child, parent, link_field, wbs_field, doc.project))
	return {str(wbs).strip() for wbs in used if wbs}


def used_tasks(doc):
	"""ชื่อแถวที่ถูกใช้แล้ว (มีเอกสารอ้าง WBS หรือมีรายการความคืบหน้า)"""
	wbs = referenced_wbs(doc)
	used = {row.name for row in doc.tasks if (row.wbs or "").strip() in wbs}
	used.update(frappe.get_all(PROGRESS_ENTRY, filters={"construction_management": doc.name}, pluck="task"))
	return used


def is_confirmed(doc):
	"""แผนยืนยันแล้ว = มี Baseline อย่างน้อย 1 ชุด"""
	return bool(frappe.db.exists(BASELINE, {"construction_management": doc.name}))


def is_in_use(doc):
	"""แผนถูกใช้งานแล้ว: มีเอกสารอ้างงาน มีความคืบหน้า หรือมีงานจาก VO ที่ Submit แล้ว"""
	return any(row.is_variation for row in doc.tasks) or bool(used_tasks(doc))


def can_unconfirm(doc):
	return (
		is_confirmed(doc)
		and doc.has_permission("write")
		and frappe.has_permission(BASELINE, "delete")
		and not is_in_use(doc)
	)


def update_plan_item_wbs(name, rows):
	"""แผนคน-เครื่องจักร/วัสดุเก็บเลข WBS ไว้ด้วย"""
	for row in rows:
		for doctype in PLAN_ITEMS:
			frappe.db.set_value(doctype, {"parent": name, "task": row.name}, "wbs", row.wbs, update_modified=False)


def renumber_nodes(nodes):
	"""ตั้งเลข WBS ใหม่ตามลำดับและระดับของ {row, level}"""
	counters = []
	for node in nodes:
		level = node["level"]
		counters = counters[: level + 1]
		if len(counters) == level + 1:
			counters[level] += 1
		else:
			counters.append(1)
		node["row"].wbs = ".".join(str(n) for n in counters)


def planned_tasks(doc):
	"""แถวที่มีแผนคน-เครื่องจักร/วัสดุ (ยังย้ายได้ แต่เป็นหัวกลุ่มหรือถูกลบไม่ได้)"""
	planned = set()
	for doctype in PLAN_ITEMS:
		planned.update(frappe.get_all(doctype, filters={"parent": doc.name}, pluck="task"))
	return planned


class StructureEditor:
	"""ทำงานบนรายการ {row, level} ของงานหลัก แถว VO อยู่ท้ายตารางเสมอและแก้จากที่นี่ไม่ได้"""

	def __init__(self, doc, used=None, planned=None, confirmed=False):
		self.doc = doc
		self.used = used or set()
		self.planned = planned or set()
		self.confirmed = confirmed
		self.tail = [row for row in doc.tasks if row.is_variation]
		self.nodes = [
			{"row": row, "level": (row.wbs or "").strip(".").count(".")}
			for row in doc.tasks
			if not row.is_variation
		]
		self.was_group = {id(node["row"]): bool(node["row"].is_group) for node in self.nodes}
		self.before_wbs = {id(node["row"]): node["row"].wbs for node in self.nodes}

	# ---------- ตำแหน่ง ----------

	def index_of(self, name):
		for i, node in enumerate(self.nodes):
			if node["row"].name == name:
				return i
		frappe.throw(_("งานเพิ่ม-ลด (VO) หรืองานที่ไม่พบในแผน แก้โครงสร้างจากที่นี่ไม่ได้"))

	def subtree_end(self, i):
		"""ตำแหน่งถัดจากงานลูกตัวสุดท้ายของแถว i"""
		level = self.nodes[i]["level"]
		end = i + 1
		while end < len(self.nodes) and self.nodes[end]["level"] > level:
			end += 1
		return end

	def parent_of(self, i):
		level = self.nodes[i]["level"]
		for j in range(i - 1, -1, -1):
			if self.nodes[j]["level"] < level:
				return j
		return None

	def top_rows(self, names):
		"""แถวที่เลือกโดยไม่นับแถวที่แม่ถูกเลือกด้วย (งานลูกย้ายตามแม่อยู่แล้ว)"""
		if not names:
			frappe.throw(_("เลือกงานก่อน"))
		selected = sorted(self.index_of(name) for name in names)
		tops, end = [], -1
		for i in selected:
			if i >= end:
				tops.append(self.nodes[i]["row"])
				end = self.subtree_end(i)
		return tops

	def position(self, row):
		return next(i for i, node in enumerate(self.nodes) if node["row"] is row)

	def block(self, i):
		return self.nodes[i : self.subtree_end(i)]

	# ---------- คำสั่ง ----------

	def check_movable(self, i):
		for node in self.block(i):
			if node["row"].name in self.used:
				frappe.throw(_("งาน {0} ถูกใช้ในเอกสารแล้ว ย้ายไม่ได้").format(node["row"].wbs))

	def new_row(self, item_name, source):
		item_name = (item_name or "").strip()
		if not item_name:
			frappe.throw(_("กรอกชื่องาน"))
		start = (source and source.start_date) or self.doc.start_date
		return self.doc.append(
			"tasks", {"wbs": "", "item_name": item_name, "start_date": start, "end_date": start, "duration": 1}
		)

	def insert(self, at, row, level):
		self.nodes.insert(at, {"row": row, "level": level})
		self.after_change(row)

	def add(self, names, item_name):
		if not names:
			self.insert(len(self.nodes), self.new_row(item_name, None), 0)
			return
		i = self.index_of(names[-1])
		level = self.nodes[i]["level"]
		at = self.subtree_end(i)
		if self.confirmed:
			parent = self.parent_of(i)
			at = len(self.nodes) if parent is None else self.subtree_end(parent)
		self.insert(at, self.new_row(item_name, self.nodes[i]["row"]), level)

	def add_child(self, names, item_name):
		if len(names or []) != 1:
			frappe.throw(_("เลือกงานแม่ 1 งาน"))
		i = self.index_of(names[0])
		self.insert(
			self.subtree_end(i), self.new_row(item_name, self.nodes[i]["row"]), self.nodes[i]["level"] + 1
		)

	def indent(self, names):
		for row in self.top_rows(names):
			i = self.position(row)
			self.check_movable(i)
			if i == 0 or self.nodes[i - 1]["level"] < self.nodes[i]["level"]:
				frappe.throw(_("งาน {0} ไม่มีงานก่อนหน้าในระดับเดียวกัน Indent ไม่ได้").format(row.wbs))
			for node in self.block(i):
				node["level"] += 1
			self.after_change(row)

	def outdent(self, names):
		tops = self.top_rows(names)
		# ช่วงวางแผนแทรกต่อจากกลุ่มแม่: ทำจากล่างขึ้นบนให้ลำดับคงเดิม
		for row in tops if self.confirmed else reversed(tops):
			i = self.position(row)
			self.check_movable(i)
			if self.nodes[i]["level"] == 0:
				frappe.throw(_("งาน {0} อยู่ระดับบนสุดแล้ว").format(row.wbs))
			parent = self.nodes[self.parent_of(i)]["row"]
			block = self.block(i)
			del self.nodes[i : i + len(block)]
			for node in block:
				node["level"] -= 1
			parent_i = self.position(parent)
			at = self.subtree_end(parent_i)
			if self.confirmed:
				grand = self.parent_of(parent_i)
				at = len(self.nodes) if grand is None else self.subtree_end(grand)
			self.nodes[at:at] = block
			self.after_change(row)

	def delete(self, names):
		selected = set(names or [])
		for row in self.top_rows(names):
			i = self.position(row)
			block = self.block(i)
			for node in block:
				item = node["row"]
				if item.boq_detail:
					frappe.throw(_("งาน {0} มาจาก BOQ ลบไม่ได้ ถ้าจะลดงานให้ใช้ Variation Order").format(item.wbs))
				if item.name in self.used:
					frappe.throw(_("งาน {0} ถูกใช้ในเอกสารแล้ว ลบไม่ได้").format(item.wbs))
				if item.name in self.planned:
					frappe.throw(_("งาน {0} มีแผนคน-เครื่องจักรหรือวัสดุ ลบรายการเหล่านั้นก่อน").format(item.wbs))
				if item.name not in selected and item is not row:
					frappe.throw(_("กลุ่ม {0} ยังมีงานย่อย {1} ย้ายออกหรือเลือกลบด้วยก่อน").format(row.wbs, item.wbs))
			del self.nodes[i : i + len(block)]

	# ---------- เลข WBS ----------

	def after_change(self, row):
		if self.confirmed:
			self.next_free_number(row)

	def next_free_number(self, row):
		"""เลขถัดไปที่ว่างในกลุ่มแม่ งานลูกเปลี่ยน prefix ตาม"""
		i = self.position(row)
		parent = self.parent_of(i)
		prefix = f"{self.nodes[parent]['row'].wbs}." if parent is not None else ""
		level = self.nodes[i]["level"]
		moved = {id(node["row"]) for node in self.block(i)}
		numbers = [
			cint(node["row"].wbs.rsplit(".", 1)[-1])
			for node in self.nodes
			if node["level"] == level
			and id(node["row"]) not in moved
			and node["row"].wbs
			and (node["row"].wbs.rsplit(".", 1)[0] + "." if "." in node["row"].wbs else "") == prefix
		]
		old = row.wbs or ""
		new = f"{prefix}{max(numbers, default=0) + 1}"
		for node in self.block(i):
			item = node["row"]
			item.wbs = new + (item.wbs or "")[len(old) :] if item is not row else new

	def renumber(self):
		renumber_nodes(self.nodes)

	# ---------- จบคำสั่ง ----------

	def check_groups(self):
		for i, node in enumerate(self.nodes):
			row = node["row"]
			is_group = self.subtree_end(i) > i + 1
			was_group = self.was_group.get(id(row), False)
			if is_group and not was_group:
				if row.boq_detail or flt(row.amount):
					frappe.throw(_("งาน {0} มีมูลค่าจาก BOQ เป็นหัวกลุ่มไม่ได้").format(row.wbs))
				if row.name in self.used or row.name in self.planned:
					frappe.throw(_("งาน {0} ถูกใช้แล้ว เป็นหัวกลุ่มไม่ได้").format(row.wbs))
			if was_group and not is_group and row.boq_detail:
				frappe.throw(_("กลุ่ม {0} จาก BOQ ต้องมีงานย่อยอย่างน้อย 1 งาน").format(row.wbs))

	def finish(self):
		self.check_groups()
		if not self.confirmed:
			self.renumber()
		self.doc.tasks = [node["row"] for node in self.nodes] + self.tail
		for idx, row in enumerate(self.doc.tasks, 1):
			row.idx = idx

	def changed_wbs(self):
		return [
			node["row"]
			for node in self.nodes
			if node["row"].name and self.before_wbs.get(id(node["row"])) != node["row"].wbs
		]


@frappe.whitelist(methods=["POST"])
def change_structure(name, modified, action, tasks=None, item_name=None):
	"""action: add / add_child / indent / outdent / delete tasks = ชื่อแถวที่เลือก
	บันทึกทันที (ไม่ผ่าน save_tasks เพราะเลข WBS และลำดับแถวเปลี่ยน)"""
	doc = get_doc_for_update(name, modified)
	if is_confirmed(doc):
		frappe.throw(_("แผนงานยืนยันแล้ว (มีแผนสัญญา) แก้โครงสร้างงานไม่ได้ งานเพิ่ม-ลดให้ใช้ Variation Order"))
	names = frappe.parse_json(tasks) if tasks else []
	used = used_tasks(doc)
	editor = StructureEditor(doc, used, planned_tasks(doc), bool(used))
	if action == "add":
		editor.add(names, item_name)
	elif action == "add_child":
		editor.add_child(names, item_name)
	elif action == "indent":
		editor.indent(names)
	elif action == "outdent":
		editor.outdent(names)
	elif action == "delete":
		editor.delete(names)
	else:
		frappe.throw(_("คำสั่งไม่ถูกต้อง"))
	editor.finish()
	doc.save()
	update_plan_item_wbs(doc.name, editor.changed_wbs())
	return get_schedule_data(name)


@frappe.whitelist(methods=["POST"])
def unconfirm_plan(name, modified):
	"""ยกเลิกการยืนยันแผน: ลบ Baseline ทุกชุดแล้วกลับไปแก้โครงสร้างงานได้ เฉพาะแผนที่ยังไม่ถูกใช้งาน"""
	doc = get_doc_for_update(name, modified)
	if not is_confirmed(doc):
		frappe.throw(_("แผนงานนี้ยังไม่ได้ยืนยัน"))
	if is_in_use(doc):
		frappe.throw(_("แผนงานนี้มีการรายงานความคืบหน้าหรือมีเอกสารอ้างงานแล้ว ยกเลิกการยืนยันไม่ได้"))
	frappe.has_permission(BASELINE, "delete", throw=True)
	doc.active_baseline = None
	doc.baseline_date = None
	for row in doc.tasks:
		row.baseline_start_date = None
		row.baseline_end_date = None
		row.baseline_distribution = None
		row.baseline_weight = 0
	doc.save()
	for baseline in frappe.get_all(BASELINE, filters={"construction_management": name}, pluck="name"):
		frappe.delete_doc(BASELINE, baseline)
	return get_schedule_data(name)
