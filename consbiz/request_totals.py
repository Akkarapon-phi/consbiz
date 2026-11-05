# Copyright (c) 2026, Siricons and contributors
# For license information, please see license.txt

"""ยอดเงินของใบขอซื้อ (Material Request) ช่อง custom_* (ERPNext ไม่คิดภาษีให้ MR)

สูตรเดียวกับ calculate_totals ใน public/js/material_request.js (ฟอร์มระบบเต็ม) ห้ามให้ต่างกัน:
- แถวติ๊ก custom_vat_nocal = ไม่คิดภาษี (custom_net_total_novat)
- custom_included_vat = ราคารวมภาษีแล้ว ถอดยอดก่อนภาษี, custom_vat_override = ใช้ภาษีที่กรอกเอง
- ผู้ว่าจ้างจัดหา (Customer Provided) ไม่มีภาษี
เรียกตอน validate (doc_events) ระบบเต็มและแอปหน้างานจึงได้ยอดเดียวกันเสมอ
"""

from frappe.utils import cint, flt

from consbiz.utils import thai_baht_text

VAT_RATE = 7
CUSTOMER_PROVIDED = "Customer Provided"


def calculate(doc, method=None):
	sum_vat = sum_novat = 0
	for row in doc.get("items") or []:
		amount = flt(row.qty) * flt(row.rate) if flt(row.rate) else flt(row.amount)
		if cint(row.get("custom_vat_nocal")):
			sum_novat += amount
		else:
			sum_vat += amount

	if doc.get("material_request_type") == CUSTOMER_PROVIDED:
		net_total, vat = sum_vat, 0
	elif cint(doc.get("custom_vat_override")):
		vat = flt(doc.get("custom_vat"), 2)
		net_total = sum_vat - vat if cint(doc.get("custom_included_vat")) else sum_vat
	elif cint(doc.get("custom_included_vat")):
		net_total = sum_vat * 100 / (100 + VAT_RATE)
		vat = sum_vat - net_total
	else:
		net_total = sum_vat
		vat = sum_vat * VAT_RATE / 100

	net_total, vat, sum_novat = flt(net_total, 2), flt(vat, 2), flt(sum_novat, 2)
	grand_total = flt(net_total + vat + sum_novat, 2)
	doc.custom_net_total = net_total
	doc.custom_net_total_novat = sum_novat
	doc.custom_grand_total = grand_total
	doc.custom_in_words = thai_baht_text(grand_total)
	if not cint(doc.get("custom_vat_override")) or doc.get("material_request_type") == CUSTOMER_PROVIDED:
		doc.custom_vat = vat
