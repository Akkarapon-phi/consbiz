# Copyright (c) 2026, Siricons and contributors
# For license information, please see license.txt

# เงินเบิกล่วงหน้าของคนงานรายวัน (เฉพาะคนงานที่บริษัทจ่ายเอง)
# Submit = จ่ายเงิน: Journal Entry Dr. เงินเบิกล่วงหน้าคนงาน / Cr. เงินสด-ธนาคาร
# หักคืนในใบลงเวลา (Labour Timesheet.advances) ยอดหักคืน/สถานะคำนวณใหม่เสมอ (update_deduction) ห้ามแก้ตรง

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate, nowdate

from consbiz.consbiz.doctype.labour_settings.labour_settings import require, settings_of


class LabourAdvance(Document):
	def validate(self):
		worker = frappe.db.get_value(
			"Daily Worker", self.worker, ["company", "project", "payee_type", "status"], as_dict=True
		)
		if worker.payee_type != "Company":
			frappe.throw(_("คนงานที่จ่ายผ่าน ผรม. เบิกล่วงหน้ากับ ผรม./หัวหน้าชุดโดยตรง"))
		if worker.status != "Active":
			frappe.throw(_("คนงานเลิกจ้างแล้ว"))
		self.company = worker.company
		self.project = self.project or worker.project
		if flt(self.amount) <= 0:
			frappe.throw(_("จำนวนเงินต้องมากกว่า 0"))
		if getdate(self.date) > getdate(nowdate()):
			frappe.throw(_("วันที่จ่ายต้องไม่เกินวันนี้"))
		account = frappe.db.get_value("Account", self.paid_from_account, ["company", "account_type"], as_dict=True)
		if not account or account.company != self.company or account.account_type not in ("Cash", "Bank"):
			frappe.throw(_("จ่ายจากบัญชีต้องเป็นบัญชีเงินสด/ธนาคารของบริษัท {0}").format(self.company))
		self.deducted_amount = 0
		self.outstanding_amount = flt(self.amount)
		self.status = "Draft"

	def on_submit(self):
		settings = settings_of(self.company)
		require(settings, "advance_account")
		cost_center = cost_center_of(self.project, self.company)
		je = frappe.get_doc(
			{
				"doctype": "Journal Entry",
				"voucher_type": "Journal Entry",
				"company": self.company,
				"posting_date": self.date,
				"user_remark": _("เบิกล่วงหน้า {0} {1} ({2})").format(self.worker_name, self.name, self.project),
				"accounts": [
					{
						"account": settings.advance_account,
						"debit_in_account_currency": flt(self.amount),
						"project": self.project,
						"cost_center": cost_center,
					},
					{
						"account": self.paid_from_account,
						"credit_in_account_currency": flt(self.amount),
						"project": self.project,
						"cost_center": cost_center,
					},
				],
			}
		)
		je.insert(ignore_permissions=True)
		je.submit()
		self.db_set({"journal_entry": je.name, "status": "Unpaid", "outstanding_amount": flt(self.amount)})

	def before_cancel(self):
		used = frappe.get_all(
			"Labour Timesheet Advance",
			filters={"advance": self.name, "docstatus": 1},
			pluck="parent",
		)
		if used:
			frappe.throw(_("หักคืนแล้วในใบลงเวลา {0} ยกเลิกใบลงเวลาก่อน").format(", ".join(sorted(set(used)))))

	def on_cancel(self):
		if self.journal_entry and frappe.db.get_value("Journal Entry", self.journal_entry, "docstatus") == 1:
			frappe.get_doc("Journal Entry", self.journal_entry).cancel()
		self.db_set("status", "Cancelled")

	def update_deduction(self):
		row = frappe.qb.DocType("Labour Timesheet Advance")
		sheet = frappe.qb.DocType("Labour Timesheet")
		result = (
			frappe.qb.from_(row)
			.join(sheet)
			.on(sheet.name == row.parent)
			.select(frappe.query_builder.functions.Sum(row.amount))
			.where((row.advance == self.name) & (sheet.docstatus == 1))
			.run()
		)
		deducted = flt(result[0][0]) if result else 0.0
		outstanding = flt(flt(self.amount) - deducted, 2)
		status = "Deducted" if outstanding <= 0 else "Partly Deducted" if deducted else "Unpaid"
		self.db_set({"deducted_amount": deducted, "outstanding_amount": outstanding, "status": status})


def cost_center_of(project, company):
	return (project and frappe.db.get_value("Project", project, "cost_center")) or frappe.get_cached_value(
		"Company", company, "cost_center"
	)
