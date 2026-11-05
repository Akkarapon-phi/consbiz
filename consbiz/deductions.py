# Copyright (c) 2026, Siricons and contributors
# For license information, please see license.txt

"""หัก ณ ที่จ่าย / เงินประกันผลงาน / ยอดชำระสุทธิ ของเอกสารซื้อ-ขาย สำหรับแอปหน้างาน (site_docs.apply_form)

สูตรเดียวกับสคริปต์ฟอร์มของระบบเต็ม ห้ามให้ต่างกัน (ระบบเต็มคำนวณในหน้าเว็บ ไม่ได้เรียกไฟล์นี้):
- Quotation / Sales Order / Purchase Order: quotation_cal.js, sales_order_cal.js, purchase_order.js
  ยอดหัก = net_total x % (ปัด 2 ตำแหน่ง) ยอดสุทธิ = grand_total - หัก ณ ที่จ่าย - เงินประกัน + rounding_adjustment
- Purchase Invoice / Sales Invoice: purchase_invoice.js, sales_invoice_cal.js
  ยอดหักลงตาราง custom_payment_entry_deduction (1 แถวต่อบัญชี) ยอดสุทธิ = grand_total - ยอดตาราง - total_advance + rounding_adjustment
  Sales Invoice ติ๊ก custom_edit_wht / custom_edit_retention = ใช้ยอดที่กรอกเอง (ถ้ากรอก > 0)
"""

import frappe
from frappe.utils import cint, flt

from consbiz.utils import thai_baht_text

# DocType → (บัญชีหัก ณ ที่จ่ายใน Company, ชื่อบัญชีสำรอง, บัญชีเงินประกันใน Company, ชื่อบัญชีสำรอง)
ACCOUNTS = {
	"Purchase Invoice": ("custom_wht_payable", "ภาษีหัก ณ ที่จ่ายรอจ่าย", "custom_retention_payable", "เจ้าหนี้เงินประกันผลงาน"),
	"Sales Invoice": ("custom_wht_receivable", "ถูกหัก ณ ที่จ่าย", "custom_retention_receivable", "เงินประกันผลงาน"),
}
TABLE = "custom_payment_entry_deduction"


def baht_words(amount):
	if not amount:
		return "ศูนย์บาทถ้วน"
	return thai_baht_text(amount) if amount > 0 else "ติดลบ" + thai_baht_text(abs(amount))


def percent_of(doc, subject, percent):
	if cint(doc.get(subject)) and flt(doc.get(percent)) > 0:
		return flt(flt(doc.net_total) * flt(doc.get(percent)) / 100, 2)
	return 0


def calculate(doc):
	if not doc.meta.has_field("custom_subject_to_wht"):
		return
	wht = percent_of(doc, "custom_subject_to_wht", "custom_wht_percent")
	ret = percent_of(doc, "custom_subject_to_retention", "custom_retention_percent")
	grand = flt(doc.grand_total)

	if doc.doctype in ACCOUNTS:
		# ใบแจ้งหนี้ขาย: ยอดที่กรอกเองแทนค่าคำนวณ (ค่าคำนวณต้อง > 0 แบบสคริปต์ระบบเต็ม)
		if cint(doc.get("custom_edit_wht")) and wht > 0 and flt(doc.get("custom_wht_amount")) > 0:
			wht = flt(doc.custom_wht_amount, 2)
		if cint(doc.get("custom_edit_retention")) and ret > 0 and flt(doc.get("custom_retention_amount")) > 0:
			ret = flt(doc.custom_retention_amount, 2)
		doc.custom_wht_amount = wht
		doc.custom_retention_amount = ret
		sync_table(doc, wht, ret)
		total = flt(sum(flt(row.amount) for row in doc.get(TABLE) or []), 2)
		doc.custom_total_deductions = total
		net = flt(grand - flt(doc.get("total_advance")) - total + flt(doc.get("rounding_adjustment")), 2)
		doc.custom_net_paid_amount = net
	else:
		doc.custom_wht_amount = wht
		doc.custom_retention_amount = ret
		net = flt(grand - wht - ret + flt(doc.get("rounding_adjustment")), 2)
		doc.custom_paid_amount = net

	if doc.meta.has_field("custom_paid_amount_in_words"):
		doc.custom_paid_amount_in_words = baht_words(net)
	if doc.meta.has_field("custom_in_words_th"):
		doc.custom_in_words_th = baht_words(grand)


def sync_table(doc, wht, ret):
	"""1 แถวต่อบัญชี: ยอด > 0 = เพิ่ม/แก้แถว, ยอด 0 = ลบแถวของบัญชีนั้น (แถวบัญชีอื่นที่ผู้ใช้เพิ่มเองไม่แตะ)"""
	wht_field, wht_default, ret_field, ret_default = ACCOUNTS[doc.doctype]
	company = frappe.get_cached_value(
		"Company", doc.company, ["abbr", wht_field, ret_field, "cost_center"], as_dict=True
	)
	if not company:
		return
	wht_account = company.get(wht_field) or f"{wht_default} - {company.abbr}"
	ret_account = company.get(ret_field) or f"{ret_default} - {company.abbr}"
	company_cc = company.cost_center
	for account, amount, description, cost_center in (
		(wht_account, wht, "ภาษีหัก ณ ที่จ่าย", company_cc),
		(ret_account, ret, "เงินประกันผลงาน", doc.get("cost_center") or company_cc),
	):
		rows = [row for row in doc.get(TABLE) or [] if row.account == account]
		if amount > 0:
			if not cost_center:
				continue
			if rows:
				rows[0].amount = flt(amount, 2)
				rows[0].cost_center = cost_center
			else:
				doc.append(
					TABLE,
					{"account": account, "amount": flt(amount, 2), "description": description, "cost_center": cost_center},
				)
		elif rows:
			doc.set(TABLE, [row for row in doc.get(TABLE) if row.account != account])
