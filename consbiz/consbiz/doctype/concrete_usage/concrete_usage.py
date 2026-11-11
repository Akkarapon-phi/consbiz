# Copyright (c) 2026, Siricons and contributors
# For license information, please see license.txt

# บันทึกการใช้คอนกรีต: 1 ใบต่อการเท 1 จุด (งาน WBS + ตำแหน่ง) ตั๋วรถ 1 แถวต่อคัน
# - คอนกรีตไม่ผ่านสต็อก (เก็บไม่ได้ รับแล้วเทเลย) เอกสารนี้เป็นบันทึกหลักของปริมาณที่ใช้จริง
# - ตั๋วที่ติ๊กผู้ว่าจ้างจัดหา = หักค่าวัสดุจากงวดงานตามปริมาณนี้ ไม่ติ๊ก = ซื้อเอง ใช้ตรวจกับใบแจ้งหนี้ผู้ขาย
#   ช่องติ๊กที่หัวเอกสารเป็นค่าตั้งต้นของตั๋วที่เพิ่มใหม่ (ฟอร์ม) ยอดคิดจากรายตั๋วเท่านั้น
# - เศษที่เหลือนำไปเทที่อื่นเขียนในหมายเหตุของตั๋ว ยอดของจุดนี้นับเต็มตามตั๋ว
# - เลขตั๋วซ้ำกับใบอื่นของผู้ขายเดียวกันเตือน (อาจบันทึกซ้ำ) ไม่ห้าม
# - ชนิดคอนกรีต = Item ในกลุ่ม CONCRETE_GROUP (รวมกลุ่มย่อย) ชื่อ Item บอกกำลังอัดอยู่แล้ว จึงไม่มีช่องกำลังอัดแยก

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

from consbiz.consbiz.doctype.daily_report.daily_report import get_leaf_tasks
from consbiz.employer_supplied import base_item

CONCRETE_GROUP = "คอนกรีตผสมเสร็จ"


def concrete_item_filters():
	"""ตัวกรอง Item ที่เลือกเป็นชนิดคอนกรีตได้ (ใช้ทั้งค้นหาในแอปและตรวจตอนบันทึก)"""
	return {
		"item_group": ("descendants of (inclusive)", CONCRETE_GROUP),
		"custom_base_item": ("is", "not set"),
		"disabled": 0,
		"has_variants": 0,
	}


class ConcreteUsage(Document):
	def validate(self):
		task = get_leaf_tasks(self.construction_management).get((self.wbs or "").strip())
		if not task:
			frappe.throw(_("ไม่พบงานย่อย WBS {0} ใน {1}").format(self.wbs, self.construction_management))
		self.wbs, self.task_name = task.wbs, task.item_name
		# เก็บ Item หลักเสมอ ของผู้ว่าจ้างจัดหาดูจากช่องติ๊กของตั๋ว
		self.concrete_item = base_item(self.concrete_item)
		self.validate_concrete_item()
		self.validate_tickets()
		self.set_totals()
		self.warn_duplicate_tickets()

	def validate_concrete_item(self):
		# ตรวจเฉพาะตอนเลือกใหม่ ใบเดิมที่เลือก Item ไว้ก่อนมีกลุ่มยังแก้ช่องอื่นได้
		if not (self.is_new() or self.has_value_changed("concrete_item")):
			return
		if not frappe.db.exists("Item Group", CONCRETE_GROUP):
			frappe.throw(_("ยังไม่มีกลุ่ม Item \"{0}\" สร้างกลุ่มแล้วย้าย Item คอนกรีตเข้ากลุ่มก่อน").format(CONCRETE_GROUP))
		if not frappe.get_all("Item", filters={"name": self.concrete_item, **concrete_item_filters()}, limit=1):
			frappe.throw(
				_("{0} ไม่ใช่คอนกรีต: เลือกได้เฉพาะ Item ในกลุ่ม \"{1}\"").format(self.concrete_item, CONCRETE_GROUP)
			)

	def validate_tickets(self):
		seen = set()
		for row in self.tickets:
			row.ticket_no = (row.ticket_no or "").strip()
			if row.ticket_no in seen:
				frappe.throw(_("แถว {0}: เลขตั๋ว {1} ซ้ำกับแถวอื่น").format(row.idx, row.ticket_no))
			seen.add(row.ticket_no)
			if flt(row.qty) <= 0:
				frappe.throw(_("แถว {0}: ปริมาณต้องมากกว่า 0").format(row.idx))

	def set_totals(self):
		self.total_qty = sum(flt(row.qty) for row in self.tickets)
		self.employer_qty = sum(flt(row.qty) for row in self.tickets if row.employer_supplied)
		self.company_qty = self.total_qty - self.employer_qty
		self.ticket_count = len(self.tickets)
		self.variance = self.total_qty - flt(self.planned_qty) if flt(self.planned_qty) else 0

	def warn_duplicate_tickets(self):
		numbers = [row.ticket_no for row in self.tickets if row.ticket_no]
		if not numbers or not self.supplier:
			return
		parent = frappe.qb.DocType("Concrete Usage")
		child = frappe.qb.DocType("Concrete Usage Ticket")
		duplicates = (
			frappe.qb.from_(child)
			.join(parent)
			.on(child.parent == parent.name)
			.select(child.ticket_no, parent.name)
			.where(
				(parent.docstatus < 2)
				& (parent.name != (self.name or ""))
				& (parent.supplier == self.supplier)
				& child.ticket_no.isin(numbers)
			)
			.run(as_dict=True)
		)
		if duplicates:
			frappe.msgprint(
				_("เลขตั๋วซ้ำกับใบอื่นของผู้ขายเดียวกัน: {0}").format(
					", ".join(f"{row.ticket_no} ({row.name})" for row in duplicates)
				),
				indicator="orange",
				alert=True,
			)
