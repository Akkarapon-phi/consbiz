# Copyright (c) 2026, Siricons and contributors
# For license information, please see license.txt

# บัญชีค่าแรงคนงานรายวันของแต่ละบริษัท (ตั้งในแอป: ตั้งค่า > ค่าแรงคนงาน) ใช้ตอนอนุมัติใบลงเวลา/จ่ายเงินเบิก

import frappe
from frappe import _
from frappe.model.document import Document

# ช่อง → (root_type ที่ต้องเป็น, ชื่อที่ผู้ใช้เห็น) บัญชีค้างจ่าย/ลูกหนี้ห้ามเป็น Payable/Receivable (Journal Entry จะบังคับคู่ค้า)
ACCOUNT_RULES = {
	"wage_expense_account": (("Expense",), _("ค่าแรงทางตรง")),
	"employer_sso_expense_account": (("Expense",), _("ประกันสังคมส่วนนายจ้าง")),
	"wage_payable_account": (("Liability",), _("ค่าแรงค้างจ่าย")),
	"sso_payable_account": (("Liability",), _("ประกันสังคมค้างจ่าย")),
	"advance_account": (("Asset",), _("เงินเบิกล่วงหน้าคนงาน")),
	"other_deduction_account": (("Income", "Expense", "Liability"), _("หักอื่นๆ")),
}
NO_PARTY = ("Payable", "Receivable")


class LabourSettings(Document):
	def validate(self):
		for field, (root_types, label) in ACCOUNT_RULES.items():
			account = self.get(field)
			if not account:
				continue
			info = frappe.db.get_value(
				"Account", account, ["company", "root_type", "account_type", "is_group"], as_dict=True
			)
			if not info or info.company != self.company:
				frappe.throw(_("{0}: บัญชี {1} ไม่ได้อยู่ในบริษัท {2}").format(label, account, self.company))
			if info.is_group:
				frappe.throw(_("{0}: {1} เป็นบัญชีกลุ่ม เลือกบัญชีย่อย").format(label, account))
			if info.root_type not in root_types:
				frappe.throw(_("{0}: {1} ต้องเป็นบัญชีประเภท {2}").format(label, account, " / ".join(root_types)))
			if info.account_type in NO_PARTY:
				frappe.throw(_("{0}: {1} เป็นบัญชี {2} (ต้องระบุคู่ค้า) เลือกบัญชีอื่น").format(label, account, info.account_type))
		if self.subcontract_item and frappe.db.get_value("Item", self.subcontract_item, "is_stock_item"):
			frappe.throw(_("รายการค่าแรง ผรม. ต้องเป็น Item ที่ไม่ใช่สต็อก"))


def settings_of(company):
	if not frappe.db.exists("Labour Settings", company):
		frappe.throw(_("ยังไม่ได้ตั้งบัญชีค่าแรงของบริษัท {0} (แอป ConsERP: ตั้งค่า > ค่าแรงคนงาน)").format(company))
	return frappe.get_cached_doc("Labour Settings", company)


def require(settings, *fields):
	missing = [ACCOUNT_RULES[f][1] if f in ACCOUNT_RULES else settings.meta.get_label(f) for f in fields if not settings.get(f)]
	if missing:
		frappe.throw(
			_("ตั้งค่าค่าแรงของบริษัท {0} ยังไม่ครบ: {1} (แอป ConsERP: ตั้งค่า > ค่าแรงคนงาน)").format(
				settings.company, ", ".join(missing)
			)
		)
