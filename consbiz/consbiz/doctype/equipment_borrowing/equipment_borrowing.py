# Copyright (c) 2026, Siricons and contributors
# For license information, please see license.txt

# ยืม-คืนอุปกรณ์ (สโตร์เป็นคนบันทึก ผู้ยืมเซ็นรับ)
# - ผู้ยืม: พนักงาน / ผู้รับเหมาช่วง (ผรม.) / คนงาน (กรอกชื่อเอง) คนงานของ ผรม. ระบุ ผรม. เป็นผู้รับผิดชอบด้วย
# - Submit = ส่งมอบ: Stock Entry (Material Transfer) จากคลังต้นทางเข้า "คลังอุปกรณ์ระหว่างยืม"
#   ยอดในคลังระหว่างยืม = ของที่อยู่กับผู้ยืม
# - รับคืนทีละครั้ง (record_return): เพิ่มแถวใน returns พร้อมผู้คืน ผู้รับคืน ลายเซ็น รูป
#   ปกติ/ชำรุด = โอนกลับคลังต้นทาง, สูญหาย = Material Issue ออกจากคลังระหว่างยืม
#   แถวคืนที่บันทึกแล้วแก้/ลบไม่ได้ (before_update_after_submit)
# - สถานะ: Draft / Borrowed / Partially Returned / Returned / Cancelled (เกินกำหนด = รายการที่ due_date ผ่านแล้ว ดูที่ list)
# - Cancel = ยกเลิก Stock Entry ของการคืนทั้งหมดแล้วของการส่งมอบ

import json

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate, nowdate

LOST = "Lost"
EPSILON = 1e-9
# ค่าที่เทียบว่าแถวคืนเดิมถูกแก้หรือไม่
RETURN_FIELDS = ("date", "item_code", "qty", "condition", "returned_by", "received_by", "stock_entry")


class EquipmentBorrowing(Document):
	def validate(self):
		self.set_borrower_name()
		if self.source_warehouse == self.loan_warehouse:
			frappe.throw(_("คลังอุปกรณ์ระหว่างยืมต้องไม่ใช่คลังเดียวกับคลังต้นทาง"))
		if self.due_date and getdate(self.due_date) < getdate(self.date):
			frappe.throw(_("กำหนดคืนต้องไม่ก่อนวันที่ยืม"))
		seen = set()
		for row in self.items:
			if row.item_code in seen:
				frappe.throw(_("แถว {0}: {1} ซ้ำกับแถวอื่น").format(row.idx, row.item_code))
			seen.add(row.item_code)
			if flt(row.qty) <= 0:
				frappe.throw(_("แถว {0}: จำนวนต้องมากกว่า 0").format(row.idx))
		self.update_quantities()

	def set_borrower_name(self):
		if self.borrower_type == "Employee":
			self.borrower_name = frappe.db.get_value("Employee", self.employee, "employee_name") if self.employee else None
			self.supplier = None
			self.worker_name = None
		elif self.borrower_type == "Subcontractor":
			self.borrower_name = frappe.db.get_value("Supplier", self.supplier, "supplier_name") if self.supplier else None
			self.employee = None
			self.worker_name = None
		else:
			self.employee = None
			supplier_name = frappe.db.get_value("Supplier", self.supplier, "supplier_name") if self.supplier else None
			self.borrower_name = f"{self.worker_name} ({supplier_name})" if supplier_name else self.worker_name

	def update_quantities(self):
		"""ยอดคืน/หายของแต่ละอุปกรณ์จากแถวคืน และสถานะ"""
		returned, lost = {}, {}
		for row in self.returns:
			target = lost if row.condition == LOST else returned
			target[row.item_code] = target.get(row.item_code, 0) + flt(row.qty)
		for row in self.items:
			row.returned_qty = returned.pop(row.item_code, 0)
			row.lost_qty = lost.pop(row.item_code, 0)
			row.outstanding_qty = flt(row.qty) - row.returned_qty - row.lost_qty
			if row.outstanding_qty < -EPSILON:
				frappe.throw(_("{0}: คืนเกินจำนวนที่ยืม ({1})").format(row.item_code, flt(row.qty)))
		if returned or lost:
			frappe.throw(_("คืนอุปกรณ์ที่ไม่ได้ยืมในใบนี้: {0}").format(", ".join({*returned, *lost})))
		self.status = status_of(self)

	def on_submit(self):
		entry = make_stock_entry(
			self,
			"Material Transfer",
			[(row.item_code, row.qty) for row in self.items],
			self.source_warehouse,
			self.loan_warehouse,
		)
		self.db_set("issue_stock_entry", entry)
		self.db_set("status", status_of(self))

	def before_update_after_submit(self):
		before = self.get_doc_before_save()
		current = {row.name: row for row in self.returns}
		for old in before.returns if before else []:
			row = current.get(old.name)
			if not row or any(str(row.get(f) or "") != str(old.get(f) or "") for f in RETURN_FIELDS):
				frappe.throw(_("แถวรับคืนที่บันทึกแล้วแก้หรือลบไม่ได้ (แถว {0})").format(old.idx))
		self.update_quantities()

	def on_cancel(self):
		for row in reversed(self.returns):
			cancel_stock_entry(row.stock_entry)
		cancel_stock_entry(self.issue_stock_entry)
		self.db_set("status", "Cancelled")


def status_of(doc):
	if doc.docstatus == 0:
		return "Draft"
	if doc.docstatus == 2:
		return "Cancelled"
	outstanding = sum(flt(row.outstanding_qty) for row in doc.items)
	if outstanding <= EPSILON:
		return "Returned"
	return "Partially Returned" if doc.returns else "Borrowed"


def make_stock_entry(doc, purpose, lines, source, target=None):
	"""Stock Entry ที่ Submit แล้วของรายการ [(item_code, qty)] คืนชื่อเอกสาร"""
	entry = frappe.new_doc("Stock Entry")
	entry.purpose = purpose
	entry.stock_entry_type = purpose
	entry.company = doc.company
	entry.project = doc.project
	entry.remarks = _("{0} {1}: {2}").format(_("Equipment Borrowing"), doc.name, doc.borrower_name or "")
	for item_code, qty in lines:
		# อุปกรณ์ไม่แยกตัดคลังผู้ว่าจ้าง (site_stock.split_employer_stock)
		entry.append(
			"items",
			{"item_code": item_code, "qty": qty, "s_warehouse": source, "t_warehouse": target, "custom_employer_checked": 1},
		)
	entry.insert()
	entry.submit()
	return entry.name


def cancel_stock_entry(name):
	if name and frappe.db.get_value("Stock Entry", name, "docstatus") == 1:
		frappe.get_doc("Stock Entry", name).cancel()


@frappe.whitelist(methods=["POST"])
def record_return(name, items, returned_by=None, signature=None, photo=None, remarks=None, date=None):
	"""รับคืน 1 ครั้ง items: [{item_code, qty, condition}] สร้าง Stock Entry ให้แล้วเพิ่มแถวคืน"""
	doc = frappe.get_doc("Equipment Borrowing", name)
	doc.check_permission("write")
	if doc.docstatus != 1:
		frappe.throw(_("รับคืนได้เฉพาะใบที่ส่งมอบแล้ว (Submit)"))
	items = json.loads(items) if isinstance(items, str) else items
	items = [row for row in items or [] if flt(row.get("qty")) > 0]
	if not items:
		frappe.throw(_("กรอกจำนวนที่คืนอย่างน้อย 1 รายการ"))

	outstanding = {row.item_code: flt(row.outstanding_qty) for row in doc.items}
	for row in items:
		if flt(row["qty"]) > outstanding.get(row["item_code"], 0) + EPSILON:
			frappe.throw(_("{0}: คืนได้ไม่เกิน {1}").format(row["item_code"], outstanding.get(row["item_code"], 0)))

	back = [(row["item_code"], flt(row["qty"])) for row in items if row.get("condition") != LOST]
	gone = [(row["item_code"], flt(row["qty"])) for row in items if row.get("condition") == LOST]
	entries = {
		"back": make_stock_entry(doc, "Material Transfer", back, doc.loan_warehouse, doc.source_warehouse) if back else None,
		"gone": make_stock_entry(doc, "Material Issue", gone, doc.loan_warehouse) if gone else None,
	}
	for row in items:
		doc.append(
			"returns",
			{
				"date": date or nowdate(),
				"item_code": row["item_code"],
				"qty": flt(row["qty"]),
				"condition": row.get("condition") or "Good",
				"returned_by": returned_by,
				"received_by": frappe.session.user,
				"signature": signature,
				"photo": photo,
				"remarks": remarks,
				"stock_entry": entries["gone" if row.get("condition") == LOST else "back"],
			},
		)
	doc.save()
	return doc.status


@frappe.whitelist()
def get_outstanding(project=None):
	"""ใบยืมที่ยังคืนไม่ครบ (หน้าสโตร์หน้างาน) พร้อมรายการค้างคืน"""
	filters = {"docstatus": 1, "status": ("in", ("Borrowed", "Partially Returned"))}
	if project:
		filters["project"] = project
	docs = frappe.get_list(
		"Equipment Borrowing",
		filters=filters,
		fields=["name", "borrower_name", "date", "due_date", "status"],
		order_by="due_date asc, date asc",
		limit_page_length=100,
	)
	if not docs:
		return []
	rows = frappe.get_all(
		"Equipment Borrowing Item",
		filters={"parent": ("in", [doc.name for doc in docs]), "parenttype": "Equipment Borrowing", "outstanding_qty": (">", 0)},
		fields=["parent", "item_code", "item_name", "uom", "outstanding_qty"],
		order_by="idx",
	)
	today = getdate(nowdate())
	for doc in docs:
		doc["items"] = [row for row in rows if row.parent == doc.name]
		doc["overdue"] = bool(doc.due_date and getdate(doc.due_date) < today)
	return docs
