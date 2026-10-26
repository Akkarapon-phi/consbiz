# Copyright (c) 2026, Siricons and contributors
# For license information, please see license.txt

# งานลด-งานเพิ่ม (Variation Order) ของแผนงาน Construction Management
# - Submit = มีผลกับแผนงาน (สิทธิ์ Projects Manager): งานลดลดปริมาณงานเดิม งานเพิ่มเป็นแถวในแผนให้ DR ลงได้
#   หน้างานทำก่อนได้: Submit ด้วยปริมาณประมาณการ (is_provisional) แล้วแก้ Qty/Rate/Amount ภายหลังด้วย Update after Submit
# - นับในมูลค่าสัญญาปรับปรุงและ % ความคืบหน้าเมื่อ employer_status = Approved ตั้งแต่วันที่ employer_approved_on
# - งานเพิ่ม: 1 แถว = 1 งานใหม่ใต้กลุ่ม VO ท้ายแผนงาน (WBS VO.1, VO.2, ... ตั้งตอน Submit ไม่เปลี่ยนภายหลัง)
#   รวมถึงการเพิ่มปริมาณของรายการเดิม (อ้าง WBS เดิม) เพื่อไม่ให้ปนกับ % หลัก
# - งานลด: ลดปริมาณงานเดิมที่มีปริมาณ ลดได้ไม่ต่ำกว่าที่ทำไปแล้ว
# - Cancel ได้เมื่องานเพิ่มของเอกสารนี้ยังไม่มีความคืบหน้า
# การปรับแผนงานอยู่ใน Construction Management.apply_variations (คำนวณจาก Variation Order ที่ Submit แล้วทุกฉบับ)

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt, nowdate

from consbiz.consbiz.doctype.construction_management.construction_management import (
	TOLERANCE,
	VARIATION_GROUP_WBS,
	VARIATION_ORDER,
)
from consbiz.consbiz.doctype.daily_report.daily_report import get_leaf_tasks, get_task_totals


class VariationOrder(Document):
	def validate(self):
		self.set_approval_date()
		self.set_items()
		self.set_totals()

	def before_update_after_submit(self):
		self.set_approval_date()
		self.set_items()
		self.set_totals()

	def set_approval_date(self):
		if self.employer_status == "Pending":
			self.employer_approved_on = None
		elif not self.employer_approved_on:
			self.employer_approved_on = nowdate()

	def on_submit(self):
		self.set_variation_wbs()
		update_plan(self.construction_management)

	def on_update_after_submit(self):
		update_plan(self.construction_management)

	def on_cancel(self):
		update_plan(self.construction_management)

	def set_items(self):
		tasks = get_leaf_tasks(self.construction_management)
		done = get_task_totals(self.construction_management)
		omitted = get_omitted_qty(self.construction_management, exclude=self.name)
		seen = set()
		for row in self.items:
			task = None
			if (row.wbs or "").strip():
				task = tasks.get(row.wbs.strip())
				if not task or task.is_variation:
					frappe.throw(
						_("แถว {0}: ไม่พบงาน WBS {1} ใน {2} (เลือกได้เฉพาะงานย่อยของแผนเดิม)").format(
							row.idx, row.wbs, self.construction_management
						)
					)
			if row.variation_type == "Omission":
				if task and task.name in seen:
					frappe.throw(_("แถว {0}: งานลดของงาน {1} ซ้ำกับแถวอื่น").format(row.idx, row.wbs))
				self.set_omission(row, task, omitted.get(task.name, 0) if task else 0, done)
				seen.add(task.name)
			else:
				self.set_addition(row, task, tasks.get(row.variation_wbs), done)

	def set_omission(self, row, task, other_omitted, done):
		if not task:
			frappe.throw(_("แถว {0}: งานลดต้องเลือก WBS ของงานเดิม").format(row.idx))
		contract = flt(task.contract_quantity) or flt(task.quantity)
		if contract <= 0:
			frappe.throw(
				_("แถว {0} ({1}): งานเหมา (ไม่มีปริมาณ) ลดปริมาณไม่ได้").format(row.idx, task.wbs)
			)
		set_task_values(row, task)
		row.contract_qty = contract
		row.rate = flt(task.rate)
		row.done_qty = done.get(task.name, (0, 0))[0]
		if flt(row.qty) <= 0:
			frappe.throw(_("แถว {0} ({1}): กรอกปริมาณที่ลด").format(row.idx, task.wbs))
		limit = contract - other_omitted - row.done_qty
		if flt(row.qty) > limit + TOLERANCE:
			frappe.throw(
				_(
					"แถว {0} ({1}): ลดได้ไม่เกิน {2} {3} (ตามสัญญา {4} ลดไปแล้ว {5} ทำไปแล้ว {6})"
				).format(
					row.idx,
					task.wbs,
					flt(max(limit, 0), 2),
					task.uom or "",
					flt(contract, 2),
					flt(other_omitted, 2),
					flt(row.done_qty, 2),
				)
			)
		row.amount = flt(row.qty) * flt(row.rate)

	def set_addition(self, row, task, variation_task, done):
		if task:
			set_task_values(row, task, overwrite=False)
			row.contract_qty = flt(task.contract_quantity) or flt(task.quantity)
			if not flt(row.rate):
				row.rate = flt(task.rate)
		else:
			row.task = None
			row.contract_qty = 0
		if not (row.item_name or "").strip():
			frappe.throw(_("แถว {0}: กรอกชื่องานเพิ่ม").format(row.idx))
		if flt(row.qty) < 0 or flt(row.rate) < 0:
			frappe.throw(_("แถว {0}: ปริมาณและราคาต่อหน่วยต้องไม่ติดลบ").format(row.idx))
		if flt(row.qty) > 0:
			row.amount = flt(row.qty) * flt(row.rate)
		if flt(row.amount) <= 0:
			frappe.throw(
				_("แถว {0} ({1}): กรอกปริมาณและราคาต่อหน่วย หรือมูลค่า (งานเหมา)").format(
					row.idx, row.item_name
				)
			)

		# แก้หลัง Submit: ปริมาณใหม่ต้องไม่น้อยกว่าที่ทำในแถวงานเพิ่มไปแล้ว
		row.done_qty = done.get(variation_task.name, (0, 0))[0] if variation_task else 0
		if variation_task and flt(row.qty) < row.done_qty - TOLERANCE:
			frappe.throw(
				_("แถว {0} ({1}): ทำไปแล้ว {2} {3} ปริมาณต้องไม่น้อยกว่านี้").format(
					row.idx, row.variation_wbs, flt(row.done_qty, 2), row.uom or ""
				)
			)
		if variation_task and flt(variation_task.quantity) > 0 and not flt(row.qty) and row.done_qty:
			frappe.throw(
				_("แถว {0} ({1}): มีความคืบหน้าตามปริมาณแล้ว เปลี่ยนเป็นงานเหมาไม่ได้").format(
					row.idx, row.variation_wbs
				)
			)

	def set_totals(self):
		self.addition_amount = sum(flt(r.amount) for r in self.items if r.variation_type == "Addition")
		self.omission_amount = sum(flt(r.amount) for r in self.items if r.variation_type == "Omission")
		self.net_amount = flt(self.addition_amount) - flt(self.omission_amount)
		self.contract_amount = flt(
			frappe.db.get_value("Construction Management", self.construction_management, "total_amount")
		)
		# ฉบับอื่นที่ผู้ว่าจ้างอนุมัติแล้ว (ตรงกับ revised_amount ของแผนงาน)
		self.previous_variation_amount = sum(
			flt(amount)
			for amount in frappe.get_all(
				VARIATION_ORDER,
				filters={
					"construction_management": self.construction_management,
					"docstatus": 1,
					"employer_status": "Approved",
					"name": ("!=", self.name),
				},
				pluck="net_amount",
			)
		)
		self.revised_amount = self.contract_amount + self.previous_variation_amount + self.net_amount

	def set_variation_wbs(self):
		"""WBS ของงานเพิ่ม = VO.<ลำดับถัดไป> ไม่ใช้เลขซ้ำกับฉบับที่ยกเลิกไปแล้ว"""
		prefix = f"{VARIATION_GROUP_WBS}."
		used = frappe.get_all(
			"Variation Order Item",
			filters={
				"parenttype": VARIATION_ORDER,
				"parent": (
					"in",
					frappe.get_all(
						VARIATION_ORDER,
						filters={"construction_management": self.construction_management},
						pluck="name",
					),
				),
				"variation_wbs": ("like", f"{prefix}%"),
			},
			pluck="variation_wbs",
		) + frappe.get_all(
			"Construction Management Task",
			filters={
				"parent": self.construction_management,
				"parenttype": "Construction Management",
				"wbs": ("like", f"{prefix}%"),
			},
			pluck="wbs",
		)
		number = max((cint(wbs[len(prefix) :]) for wbs in used), default=0)
		for row in self.items:
			if row.variation_type == "Addition" and not row.variation_wbs:
				number += 1
				row.db_set("variation_wbs", f"{prefix}{number}")


def set_task_values(row, task, overwrite=True):
	row.task = task.name
	row.wbs = task.wbs
	for field in ("item_name", "uom"):
		if overwrite or not row.get(field):
			row.set(field, task.get(field))


def get_omitted_qty(construction_management, exclude=None):
	"""ปริมาณที่ลดไปแล้วของแต่ละงาน จาก Variation Order ที่ Submit แล้ว (ไม่นับฉบับ exclude)"""
	order = frappe.qb.DocType(VARIATION_ORDER)
	item = frappe.qb.DocType("Variation Order Item")
	query = (
		frappe.qb.from_(item)
		.join(order)
		.on(item.parent == order.name)
		.select(item.task, frappe.query_builder.functions.Sum(item.qty))
		.where(
			(order.construction_management == construction_management)
			& (order.docstatus == 1)
			& (item.parenttype == VARIATION_ORDER)
			& (item.variation_type == "Omission")
		)
		.groupby(item.task)
	)
	if exclude:
		query = query.where(order.name != exclude)
	return {task: flt(qty) for task, qty in query.run()}


def update_plan(construction_management):
	"""คำนวณงานลด-งานเพิ่มในแผนงานใหม่จาก Variation Order ที่ Submit แล้วทุกฉบับ"""
	plan = frappe.get_doc("Construction Management", construction_management)
	plan.flags.ignore_permissions = True
	plan.save()


@frappe.whitelist()
def get_tasks(construction_management):
	"""งานย่อยของแผนเดิม (ไม่รวมงานเพิ่ม) สำหรับเลือก WBS พร้อมปริมาณตามสัญญาและที่ทำไปแล้ว"""
	frappe.get_doc("Construction Management", construction_management).check_permission("read")
	done = get_task_totals(construction_management)
	return [
		{
			**task,
			"contract_quantity": flt(task.contract_quantity) or flt(task.quantity),
			"done_qty": done.get(task.name, (0, 0))[0],
		}
		for task in get_leaf_tasks(construction_management).values()
		if not task.is_variation
	]
