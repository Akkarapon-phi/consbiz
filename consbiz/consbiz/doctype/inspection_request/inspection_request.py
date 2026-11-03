# Copyright (c) 2026, Siricons and contributors
# For license information, please see license.txt

# ขอตรวจงาน (Inspection Request) ของงานในแผน
# - Submit = ส่งขอตรวจ ผลตรวจ (result) วันที่ตรวจ และความเห็นผู้ตรวจแก้ได้หลัง Submit
# - ตรวจไม่ผ่าน: ปุ่ม "ขอตรวจซ้ำ" สร้างฉบับใหม่ที่อ้าง reinspection_of

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import nowdate

from consbiz.consbiz.doctype.daily_report.daily_report import get_leaf_tasks


class InspectionRequest(Document):
	def validate(self):
		set_task(self)
		self.set_result_date()

	def before_update_after_submit(self):
		self.set_result_date()

	def set_result_date(self):
		if self.result == "Pending":
			self.inspected_on = None
		elif not self.inspected_on:
			self.inspected_on = nowdate()


def set_task(doc):
	"""ผูกแถวงานจาก WBS (ต้องเป็นงานย่อยของแผน)"""
	task = get_leaf_tasks(doc.construction_management).get((doc.wbs or "").strip())
	if not task:
		frappe.throw(_("ไม่พบงานย่อย WBS {0} ใน {1}").format(doc.wbs, doc.construction_management))
	doc.task, doc.wbs, doc.item_name = task.name, task.wbs, task.item_name


@frappe.whitelist()
def make_reinspection(source_name):
	"""ฉบับขอตรวจซ้ำของฉบับที่ตรวจไม่ผ่าน"""
	source = frappe.get_doc("Inspection Request", source_name)
	source.check_permission("read")
	if source.docstatus != 1 or source.result != "Failed":
		frappe.throw(_("ขอตรวจซ้ำได้เฉพาะฉบับที่ Submit แล้วและตรวจไม่ผ่าน"))
	doc = frappe.new_doc("Inspection Request")
	for field in ("construction_management", "wbs", "item_name", "location", "inspector"):
		doc.set(field, source.get(field))
	doc.title = _("ตรวจซ้ำ: {0}").format(source.title)
	doc.reinspection_of = source.name
	return doc
