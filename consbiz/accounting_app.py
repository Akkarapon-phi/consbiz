# Copyright (c) 2026, Siricons and contributors
# For license information, please see license.txt

"""หมวดบัญชีของแอปออฟฟิศ (/conserp/accounting): รับชำระ / จ่ายชำระ, หนังสือรับรองหัก ณ ที่จ่าย, ภาษีขาย / ภาษีซื้อ,
รายงานภาษีซื้อ-ขาย และ ภ.ง.ด.3 / 53 (เงินประกันผลงานอยู่ consbiz/retention_app.py)

รับ/จ่ายชำระ = Payment Entry ของ ERPNext ต่อจากใบแจ้งหนี้ขาย/ซื้อ (`get_payment_entry`) หักตามตาราง
custom_payment_entry_deduction ของใบแจ้งหนี้ (หัก ณ ที่จ่าย, เงินประกันผลงาน) แบบเดียวกับ payment_entry_deduction.js
แถวหัก ณ ที่จ่ายใส่ withholding_tax_type / withholding_tax_base ให้ erpnext_thailand ออกหนังสือรับรองได้
ภาษีขาย / ภาษีซื้อ (Sales / Purchase Tax Invoice) erpnext_thailand สร้างเองจาก GL ภาษี (ภาษีรอเรียกเก็บล้างตอนรับ/จ่ายชำระ)
หนังสือรับรองหัก ณ ที่จ่าย (Withholding Tax Cert) = ที่เราออกให้ผู้ขาย/ผรม. จากการจ่ายชำระ (ฝั่งที่ลูกค้าหักเรา ลูกค้าเป็นผู้ออก)
รายงาน = Script Report ของ erpnext_thailand (Sales Tax Report, Purchase Tax Report, PND3, PND53) กรองบริษัทเพิ่มในแอป"""

import json

import frappe
from frappe import _
from frappe.utils import cint, flt, get_last_day, getdate, nowdate

from consbiz import retention_app, row_social, store_app

LIST_LIMIT = 500
INVOICES = {"si": "Sales Invoice", "pi": "Purchase Invoice"}
CHEQUE_SIDES = {"acc-cheques-in": "Receive", "acc-cheques-out": "Pay"}
# หน้ารายการ (view ใน sections.js) → DocType + เงื่อนไข
LISTS = {
	**{view: frappe._dict(doctype="Payment Entry", filters={"payment_type": side}) for view, side in CHEQUE_SIDES.items()},
	"acc-receipts": frappe._dict(doctype="Payment Entry", filters={"payment_type": "Receive"}),
	"acc-payments": frappe._dict(doctype="Payment Entry", filters={"payment_type": "Pay"}),
	"acc-wht": frappe._dict(doctype="Withholding Tax Cert", filters={}),
	"acc-sales-tax": frappe._dict(doctype="Sales Tax Invoice", filters={}),
	"acc-purchase-tax": frappe._dict(doctype="Purchase Tax Invoice", filters={}),
}
TAX_TYPES = {"sales": "Sales Tax Invoice", "purchase": "Purchase Tax Invoice"}
# ช่องของใบกำกับภาษีที่แก้หลัง Submit ได้ (Allow on Submit ของ erpnext_thailand) ในแอป
TAX_EDIT = {
	"Sales Tax Invoice": ("months_delayed",),
	"Purchase Tax Invoice": ("number", "date", "months_delayed"),
}
# รายงานภาษี (key ในแอป → Script Report, module, DocType ที่ต้องอ่านได้)
REPORTS = {
	"sales": (
		"Sales Tax Report",
		"erpnext_thailand.thai_tax.report.sales_tax_report.sales_tax_report",
		"Sales Tax Invoice",
	),
	"purchase": (
		"Purchase Tax Report",
		"erpnext_thailand.thai_tax.report.purchase_tax_report.purchase_tax_report",
		"Purchase Tax Invoice",
	),
	"pnd3": ("PND3", "erpnext_thailand.thai_tax.report.pnd3.pnd3", "Withholding Tax Cert"),
	"pnd53": ("PND53", "erpnext_thailand.thai_tax.report.pnd53.pnd53", "Withholding Tax Cert"),
}
STATUS = {
	0: (_("ร่าง"), "gray"),
	1: (_("ยืนยันแล้ว"), "green"),
	2: (_("ยกเลิก"), "rose"),
}
FORMS = ("PND3", "PND53")
TAX_PAYERS = (
	("Withholding", _("หัก ณ ที่จ่าย")),
	("Paid One Time", _("ออกให้ครั้งเดียว")),
	("Paid Continuously", _("ออกให้ตลอดไป")),
)
DEFAULT_INCOME = "5"


def can_read(doctype):
	return bool(frappe.has_permission(doctype, "read"))


def readable_lists():
	return [view for view, config in LISTS.items() if can_read(config.doctype)]


def readable_reports():
	out = []
	for key, (report, _module, doctype) in REPORTS.items():
		if not can_read(doctype) or not frappe.db.exists("Report", report):
			continue
		# สิทธิ์ของรายงาน = Role ในตาราง roles ของ Report (แบบเดียวกับเปิดรายงานในระบบเต็ม)
		if frappe.get_cached_doc("Report", report).is_permitted():
			out.append(key)
	return out


def can_account():
	"""เห็นหมวดบัญชี: เงินประกันผลงาน (retention_app) หรือเมนูใดเมนูหนึ่งของไฟล์นี้"""
	return can_read("Sales Invoice") or can_read("Purchase Invoice") or (can_read("Account") and can_read("GL Entry")) or can_read("Bank Account") or retention_app.can_account() or bool(readable_lists()) or bool(readable_reports())


def boot_permissions():
	"""boot.accounting: <หน้ารายการ> = สิทธิ์อ่าน, reports = รายงานที่เปิดได้, pay = รับ/จ่ายชำระจากใบแจ้งหนี้ได้"""
	out = {view: {"read": True, "create": False} for view in readable_lists()}
	if can_read("Bank Account"):
		out["acc-bank-accounts"] = {"read": True, "create": bool(frappe.has_permission("Bank Account", "create"))}
	out["acc-general-ledger"] = can_read("Account") and can_read("GL Entry")
	out["acc-wht-received"] = can_read("Payment Entry")
	out["reports"] = readable_reports()
	out["pay"] = bool(frappe.has_permission("Payment Entry", "create"))
	return out


def status_of(docstatus):
	return STATUS.get(cint(docstatus), STATUS[0])


def company_of(doctype, name):
	return frappe.db.get_value(doctype, name, "company")


def wht_accounts(company):
	"""บัญชีหัก ณ ที่จ่ายของบริษัท (ตั้งใน Company: ฝั่งจ่าย = ภาษีหัก ณ ที่จ่ายรอนำส่ง, ฝั่งรับ = ถูกหัก ณ ที่จ่าย)"""
	values = frappe.db.get_value(
		"Company", company, ["custom_wht_payable", "custom_wht_receivable"], as_dict=True
	)
	return {"Pay": values and values.custom_wht_payable, "Receive": values and values.custom_wht_receivable}


def wht_type_of(company, account, rate, payment_type):
	"""Withholding Tax Type ของบัญชี + อัตรา (ไม่พบ = None, หนังสือรับรองใช้อัตราจากแถวเอง)"""
	rows = frappe.get_all(
		"Withholding Tax Type Account",
		filters={"company": company, "account": account, "parenttype": "Withholding Tax Type"},
		pluck="parent",
	)
	for name in rows:
		wht = frappe.get_cached_value(
			"Withholding Tax Type", name, ["percent", "for_payment_type"], as_dict=True
		)
		if (
			wht
			and abs(flt(wht.percent) - flt(rate)) < 0.001
			and wht.for_payment_type
			in (
				payment_type,
				"Pay and Receive",
			)
		):
			return name
	return None


# ---------------------------------------------------------------- รับ/จ่ายชำระจากใบแจ้งหนี้


def load_invoice(kind, name):
	if kind not in INVOICES:
		frappe.throw(_("รับ/จ่ายชำระได้เฉพาะใบแจ้งหนี้"))
	doc = frappe.get_doc(INVOICES[kind], name)
	doc.check_permission("read")
	return doc


def can_pay(doc):
	return (
		doc.docstatus == 1
		and flt(doc.outstanding_amount) > 0.005
		and not cint(doc.get("is_return"))
		and bool(frappe.has_permission("Payment Entry", "create"))
	)


def payment_type_of(doc):
	return "Receive" if doc.doctype == "Sales Invoice" else "Pay"


def paid_before(doc):
	"""มีการรับ/จ่ายชำระใบนี้ไปแล้ว (Submit หรือร่าง) = ไม่เติมรายการหักให้อีก"""
	return bool(
		frappe.get_all(
			"Payment Entry Reference",
			filters={"reference_doctype": doc.doctype, "reference_name": doc.name, "docstatus": ("<", 2)},
			limit=1,
		)
	)


def invoice_deductions(doc):
	"""รายการหักจากใบแจ้งหนี้ (ตาราง custom_payment_entry_deduction) ยอดเป็นบวก แถวหัก ณ ที่จ่ายมีฐาน/อัตรา"""
	payment_type = payment_type_of(doc)
	wht_account = wht_accounts(doc.company)[payment_type]
	rows = []
	for row in doc.get("custom_payment_entry_deduction") or []:
		if not row.account or flt(row.amount) <= 0:
			continue
		out = {
			"account": row.account,
			"cost_center": row.get("cost_center") or doc.get("cost_center"),
			"description": row.get("description") or "",
			"amount": flt(row.amount, 2),
			"wht": False,
		}
		if row.account == wht_account:
			rate = flt(doc.get("custom_wht_percent"))
			base = flt(doc.net_total, 2) if rate else 0
			if rate and abs(flt(base * rate / 100, 2) - out["amount"]) > 0.05:
				# ยอดที่กรอกเอง (SI custom_edit_wht): ฐาน = ยอด ÷ อัตรา
				base = flt(out["amount"] * 100 / rate, 2)
			out.update(
				{
					"wht": True,
					"wht_rate": rate,
					"wht_base": base,
					"wht_type": wht_type_of(doc.company, row.account, rate, payment_type),
				}
			)
		rows.append(out)
	return rows


def undue_tax_of(doc):
	"""ภาษีซื้อ/ขายที่ยังไม่ถึงกำหนดของใบแจ้งหนี้ (ภาษีของงานบริการ) ถึงกำหนดตอนรับ/จ่ายชำระ"""
	from erpnext_thailand.custom.custom_api import get_thai_tax_settings

	try:
		setting = get_thai_tax_settings(doc.company)
	except Exception:
		return 0
	account = (
		setting.sales_tax_account_undue
		if doc.doctype == "Sales Invoice"
		else setting.purchase_tax_account_undue
	)
	if not account:
		return 0
	rows = frappe.get_all(
		"GL Entry",
		filters={"voucher_type": doc.doctype, "voucher_no": doc.name, "account": account, "is_cancelled": 0},
		fields=["debit", "credit"],
	)
	return abs(sum(flt(r.credit) - flt(r.debit) for r in rows))


def cash_accounts(company):
	return retention_app.payment_options(company)


@frappe.whitelist()
def payment_defaults(kind, name):
	"""ค่าตั้งต้นของหน้ารับ/จ่ายชำระ (sheet ในหน้าดูใบแจ้งหนี้)"""
	doc = load_invoice(kind, name)
	if not can_pay(doc):
		frappe.throw(_("{0} ไม่มียอดค้างให้รับ/จ่ายชำระ หรือคุณไม่มีสิทธิ์สร้างรายการรับ/จ่ายเงิน").format(doc.name))
	payment_type = payment_type_of(doc)
	before = paid_before(doc)
	options = cash_accounts(doc.company)
	return {
		"payment_type": payment_type,
		"company": doc.company,
		"party": doc.get("customer") or doc.get("supplier"),
		"party_name": doc.get("customer_name") or doc.get("supplier_name"),
		"grand_total": flt(doc.rounded_total or doc.grand_total),
		"outstanding": flt(doc.outstanding_amount),
		"paid_before": before,
		"deductions": [] if before else invoice_deductions(doc),
		"undue_tax": flt(undue_tax_of(doc), 2),
		# ภาษีซื้อของงานบริการ: ต้องมีใบกำกับภาษีของผู้ขายถึงจะล้างภาษีซื้อรอเรียกเก็บได้ (erpnext_thailand)
		"needs_tax_invoice": payment_type == "Pay" and undue_tax_of(doc) > 0.005,
		"accounts": options["accounts"],
		"modes": options["modes"],
		"can_submit": bool(frappe.has_permission("Payment Entry", "submit")),
		"posting_date": nowdate(),
	}


def account_currency(account):
	return frappe.get_cached_value("Account", account, "account_currency")


@frappe.whitelist(methods=["POST"])
def make_payment(kind, name, data, submit=1):
	"""สร้าง Payment Entry ต่อจากใบแจ้งหนี้: ยอดตัดหนี้ (allocated) - รายการหัก = ยอดรับ/จ่ายจริง
	data: posting_date, account, mode_of_payment, reference_no, reference_date, allocated,
	deductions [{account, cost_center, description, amount (บวก), wht_type, wht_base}],
	has_tax_invoice, tax_invoice_number, tax_invoice_date (จ่ายชำระที่มีภาษีซื้อรอเรียกเก็บ)"""
	from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

	doc = load_invoice(kind, name)
	if not can_pay(doc):
		frappe.throw(_("{0} ไม่มียอดค้างให้รับ/จ่ายชำระ").format(doc.name))
	data = frappe._dict(json.loads(data) if isinstance(data, str) else data)
	if not data.account:
		frappe.throw(_("กรุณาเลือกบัญชีเงินสด/ธนาคาร"))
	account = frappe.db.get_value(
		"Account",
		data.account,
		["company", "account_type", "is_group", "disabled"],
		as_dict=True,
	)
	if not account or account.company != doc.company or account.is_group or account.disabled:
		frappe.throw(_("บัญชี {0} ใช้กับบริษัทนี้ไม่ได้").format(data.account))
	if account.account_type not in ("Bank", "Cash"):
		frappe.throw(_("บัญชี {0} ไม่ใช่บัญชีเงินสด/ธนาคาร").format(data.account))

	outstanding = flt(doc.outstanding_amount)
	allocated = flt(data.allocated) or outstanding
	if allocated <= 0 or allocated - outstanding > 0.005:
		frappe.throw(
			_("ยอดตัดหนี้ต้องมากกว่า 0 และไม่เกินยอดค้าง {0}").format(frappe.format(outstanding, "Currency"))
		)

	pe = get_payment_entry(doc.doctype, doc.name, party_amount=allocated)
	payment_type = pe.payment_type
	sign = 1 if payment_type == "Receive" else -1
	pe.posting_date = data.posting_date or nowdate()
	pe.mode_of_payment = data.mode_of_payment or None
	if payment_type == "Receive":
		pe.paid_to = data.account
		pe.paid_to_account_currency = account_currency(data.account)
	else:
		pe.paid_from = data.account
		pe.paid_from_account_currency = account_currency(data.account)
	pe.reference_no = (data.reference_no or "").strip() or ("-" if account.account_type == "Bank" else None)
	pe.reference_date = data.reference_date or pe.posting_date
	for ref in pe.references:
		if ref.reference_doctype == doc.doctype and ref.reference_name == doc.name:
			ref.allocated_amount = allocated

	total = 0
	pe.set("deductions", [])
	for row in data.get("deductions") or []:
		row = frappe._dict(row)
		amount = flt(row.amount, 2)
		if not row.account or not amount:
			continue
		if frappe.db.get_value("Account", row.account, "company") != doc.company:
			frappe.throw(_("บัญชี {0} ไม่ใช่ของบริษัทนี้").format(row.account))
		total += amount
		pe.append(
			"deductions",
			{
				"account": row.account,
				"cost_center": row.cost_center
				or doc.get("cost_center")
				or frappe.get_cached_value("Company", doc.company, "cost_center"),
				"description": row.description or None,
				"amount": sign * amount,
				"withholding_tax_type": row.wht_type or None,
				"withholding_tax_base": sign * flt(row.wht_base, 2) if row.wht_base else 0,
			},
		)
	net = flt(allocated - total, 2)
	if net < 0:
		frappe.throw(_("รายการหักมากกว่ายอดตัดหนี้"))
	pe.paid_amount = net
	pe.received_amount = net
	pe.base_paid_amount = net * flt(pe.source_exchange_rate or 1)
	pe.base_received_amount = net * flt(pe.target_exchange_rate or 1)

	# ที่อยู่บริษัทสำหรับใบกำกับภาษี/หนังสือรับรอง (รายงานภาษีกรองตามที่อยู่นี้)
	if pe.meta.has_field("company_tax_address"):
		pe.company_tax_address = (
			doc.get("company_address") if doc.doctype == "Sales Invoice" else doc.get("billing_address")
		) or pe.get("company_tax_address")
	if payment_type == "Pay" and pe.meta.has_field("has_purchase_tax_invoice"):
		if cint(data.has_tax_invoice):
			if not (data.tax_invoice_number and data.tax_invoice_date):
				frappe.throw(_("กรุณากรอกเลขที่และวันที่ใบกำกับภาษีของผู้ขาย"))
			pe.has_purchase_tax_invoice = 1
			pe.tax_invoice_number = data.tax_invoice_number.strip()
			pe.tax_invoice_date = data.tax_invoice_date
	if data.remarks:
		pe.custom_remarks = 1
		pe.remarks = data.remarks
	pe.insert()
	if cint(submit) and frappe.has_permission("Payment Entry", "submit", pe):
		pe.reload()
		pe.submit()
	return {"name": pe.name, "docstatus": pe.docstatus}


# ---------------------------------------------------------------- รายการ


def scope_filters(company=None, project=None, has_project=False):
	filters = {}
	if company:
		filters["company"] = company
	if project and has_project:
		filters["project"] = project
	return filters


def cheque_modes():
	# Bank also covers transfers, credit cards and bills of exchange on Thai sites.
	return [
		name for name in frappe.get_all("Mode of Payment", pluck="name")
		if "เช็ค" in name or "cheque" in name.casefold()
	]


def is_cheque(pe):
	return pe.payment_type in CHEQUE_SIDES.values() and pe.mode_of_payment in cheque_modes()


def cheque_rows(side, filters):
	modes = cheque_modes()
	if not modes:
		return []
	receive = side == "Receive"
	rows = row_social.get_list(
		"Payment Entry",
		filters={**filters, "payment_type": side, "mode_of_payment": ["in", modes]},
		fields=[
			"name", "docstatus", "modified", "project", "party", "party_name", "reference_no",
			"reference_date", "clearance_date", "bank_account", "bank",
			"paid_to as account" if receive else "paid_from as account",
			"received_amount as amount" if receive else "paid_amount as amount",
			"paid_to_account_currency as currency" if receive else "paid_from_account_currency as currency",
		],
		order_by="reference_date desc, modified desc",
		limit_page_length=0,
	)
	retention_app.set_project_names(rows)
	today = getdate()
	for row in rows:
		row.waiting = row.docstatus == 1 and not row.clearance_date
		row.postdated = bool(row.waiting and row.reference_date and getdate(row.reference_date) > today)
		if row.waiting:
			row.status_label, row.status_tone = (_("รอเข้าบัญชี") if receive else _("รอจ่าย")), "amber"
		elif row.docstatus == 1:
			row.status_label, row.status_tone = _("ผ่านแล้ว"), "green"
		else:
			row.status_label, row.status_tone = status_of(row.docstatus)
	return rows


def payment_rows(config, filters):
	rows = row_social.get_list(
		"Payment Entry",
		filters={**config.filters, **filters},
		fields=[
			"name",
			"docstatus",
			"modified",
			"company",
			"project",
			"posting_date",
			"party",
			"party_name",
			"paid_amount",
			"mode_of_payment",
			"reference_no",
			"wht_status",
			"tax_invoice_number",
		],
		order_by="posting_date desc, modified desc",
		limit_page_length=LIST_LIMIT,
	)
	retention_app.set_project_names(rows)
	names = [r.name for r in rows]
	refs = retention_app.child_values("Payment Entry Reference", "Payment Entry", names, "reference_name")
	wht = set()
	if names and config.filters.get("payment_type") == "Pay":
		wht = set(
			frappe.get_all(
				"Payment Entry Deduction",
				filters={
					"parenttype": "Payment Entry",
					"parent": ("in", names),
					"withholding_tax_type": ("is", "set"),
				},
				pluck="parent",
			)
		) | wht_by_account(names)
	for row in rows:
		row.refs = ", ".join(refs.get(row.name, []))
		row.amount = flt(row.paid_amount)
		row.has_wht = row.name in wht
		row.status_label, row.status_tone = status_of(row.docstatus)
		if row.docstatus == 1 and row.has_wht and row.wht_status != "Issued":
			row.status_label, row.status_tone = _("รอออกหนังสือหัก ณ ที่จ่าย"), "amber"
	return rows


def wht_by_account(names):
	"""จ่ายชำระที่มีแถวหักบัญชีหัก ณ ที่จ่าย (บัญชีจาก Company) แม้ไม่ได้ระบุประเภท"""
	if not names:
		return set()
	accounts = [a for a in frappe.get_all("Company", pluck="custom_wht_payable") if a]
	if not accounts:
		return set()
	return set(
		frappe.get_all(
			"Payment Entry Deduction",
			filters={"parenttype": "Payment Entry", "parent": ("in", names), "account": ("in", accounts)},
			pluck="parent",
		)
	)


def wht_rows(filters, limit=LIST_LIMIT):
	rows = row_social.get_list(
		"Withholding Tax Cert",
		filters=filters,
		fields=[
			"name",
			"docstatus",
			"modified",
			"company",
			"date",
			"supplier as party",
			"supplier_name as party_name",
			"income_tax_form",
			"voucher_no",
		],
		order_by="date desc, modified desc",
		limit_page_length=limit,
	)
	totals = {}
	names = [r.name for r in rows]
	if names:
		for parent, base, amount in frappe.get_all(
			"Withholding Tax Items",
			filters={"parenttype": "Withholding Tax Cert", "parent": ("in", names)},
			fields=["parent", "tax_base", "tax_amount"],
			as_list=True,
		):
			t = totals.setdefault(parent, [0, 0])
			t[0] += flt(base)
			t[1] += flt(amount)
	for row in rows:
		base, amount = totals.get(row.name, (0, 0))
		row.tax_base = base
		row.amount = amount
		row.refs = row.voucher_no or ""
		row.status_label, row.status_tone = status_of(row.docstatus)
	return rows


def tax_rows(doctype, filters, limit=LIST_LIMIT):
	fields = [
		"name",
		"docstatus",
		"modified",
		"company",
		"date",
		"report_date",
		"party",
		"party_name",
		"tax_id",
		"tax_base",
		"tax_amount",
		"voucher_type",
		"voucher_no",
	]
	if doctype == "Purchase Tax Invoice":
		fields.append("number")
	rows = row_social.get_list(
		doctype,
		filters={**filters, "docstatus": ("<", 2)} if "docstatus" not in filters else filters,
		fields=fields,
		order_by="report_date desc, name desc",
		limit_page_length=limit,
	)
	for row in rows:
		row.amount = flt(row.tax_amount)
		row.refs = row.get("number") or row.voucher_no or ""
		row.status_label, row.status_tone = status_of(row.docstatus)
		if row.docstatus == 1 and getdate(row.report_date) != getdate(row.date):
			row.status_label, row.status_tone = (
				_("ยื่นเดือน {0}").format(getdate(row.report_date).strftime("%m/%Y")),
				"blue",
			)
	return rows


def report_month(year, month):
	year, month = cint(year), cint(month)
	if not (2000 <= year <= 2700 and 1 <= month <= 12):
		frappe.throw(_("กรุณาเลือกเดือนและปี"))
	start = getdate(f"{year}-{month:02d}-01")
	return start, get_last_day(start)


@frappe.whitelist()
def get_list(kind, company=None, project=None, year=None, month=None, company_address=None):
	if kind not in LISTS:
		frappe.throw(_("ไม่รองรับ"), frappe.PermissionError)
	config = LISTS[kind]
	if not can_read(config.doctype):
		frappe.throw(_("ไม่มีสิทธิ์ดู {0}").format(_(config.doctype)), frappe.PermissionError)
	if kind in CHEQUE_SIDES:
		return cheque_rows(CHEQUE_SIDES[kind], scope_filters(company, project, has_project=True))
	if config.doctype == "Payment Entry":
		return payment_rows(config, scope_filters(company, project, has_project=True))
	filters = scope_filters(company)
	is_wht = config.doctype == "Withholding Tax Cert"
	limit = LIST_LIMIT
	if year is not None or month is not None:
		filters["date" if is_wht else "report_date"] = ["between", report_month(year, month)]
		filters["docstatus"] = ["in", [0, 1, 2]]
		limit = 0
	if company_address:
		filters["company_address" if is_wht else "company_tax_address"] = company_address
	return wht_rows(filters, limit) if is_wht else tax_rows(config.doctype, filters, limit)


def to_issue_count(company=None, project=None):
	"""จ่ายชำระที่ Submit แล้ว มีหัก ณ ที่จ่าย แต่ยังไม่ออกหนังสือรับรอง"""
	if not (can_read("Payment Entry") and can_read("Withholding Tax Cert")):
		return 0
	filters = {"payment_type": "Pay", "docstatus": 1, "wht_status": ("!=", "Issued")}
	if company:
		filters["company"] = company
	if project:
		filters["project"] = project
	names = frappe.get_list("Payment Entry", filters=filters, pluck="name", limit_page_length=0)
	if not names:
		return 0
	typed = set(
		frappe.get_all(
			"Payment Entry Deduction",
			filters={
				"parenttype": "Payment Entry",
				"parent": ("in", names),
				"withholding_tax_type": ("is", "set"),
			},
			pluck="parent",
		)
	)
	return len(typed | wht_by_account(names))


@frappe.whitelist()
def get_summary(company=None, project=None, **_kwargs):
	"""ตัวเลขเมนูของหมวดบัญชี: เงินประกันผลงาน + ร่างรับ/จ่ายชำระ + รอออกหนังสือหัก ณ ที่จ่าย"""
	out = retention_app.sides_summary(company, project)
	if can_read("Payment Entry"):
		base = scope_filters(company, project, has_project=True)
		modes = cheque_modes()
		if modes:
			counts = frappe.get_list(
				"Payment Entry",
				filters={
					**base,
					"mode_of_payment": ["in", modes],
					"payment_type": ["in", list(CHEQUE_SIDES.values())],
					"docstatus": 1,
					"clearance_date": ["is", "not set"],
				},
				fields=["payment_type", {"COUNT": "name", "as": "count"}],
				group_by="payment_type",
				order_by="payment_type",
			)
		else:
			counts = []
		waiting = {r.payment_type: r.count for r in counts}
		for view, side in CHEQUE_SIDES.items():
			out[view] = {"count": waiting.get(side, 0)}
		out["receipts_draft"] = {
			"count": frappe.db.count("Payment Entry", {**base, "payment_type": "Receive", "docstatus": 0})
		}
		out["payments_draft"] = {
			"count": frappe.db.count("Payment Entry", {**base, "payment_type": "Pay", "docstatus": 0})
		}
	out["wht_to_issue"] = {"count": to_issue_count(company, project)}
	return out


# ---------------------------------------------------------------- หน้ารับ/จ่ายชำระ


def linked_tax_invoices(pe_name):
	out = []
	for doctype, key in (("Sales Tax Invoice", "sales"), ("Purchase Tax Invoice", "purchase")):
		if not can_read(doctype):
			continue
		for row in frappe.get_all(
			doctype,
			filters={"voucher_type": "Payment Entry", "voucher_no": pe_name, "docstatus": ("<", 2)},
			fields=["name", "docstatus", "date", "tax_base", "tax_amount"]
			+ (["number"] if doctype == "Purchase Tax Invoice" else []),
		):
			row.type = key
			row.status_label, row.status_tone = status_of(row.docstatus)
			out.append(row)
	return out


def linked_certs(pe_name):
	if not can_read("Withholding Tax Cert"):
		return []
	rows = frappe.get_all(
		"Withholding Tax Cert",
		filters={"voucher_type": "Payment Entry", "voucher_no": pe_name, "docstatus": ("<", 2)},
		fields=["name", "docstatus", "date", "income_tax_form"],
		order_by="creation asc",
	)
	for row in rows:
		row.status_label, row.status_tone = status_of(row.docstatus)
	return rows


def wht_deductions(pe):
	account = wht_accounts(pe.company)[pe.payment_type]
	return [d for d in pe.deductions if d.get("withholding_tax_type") or (account and d.account == account)]


def payment_view(pe):
	from consbiz.received_wht import payment_certificate

	from consbiz.site_app import pdf_url

	label, tone = status_of(pe.docstatus)
	deductions = [
		{
			"account": d.account,
			"description": d.description,
			"amount": abs(flt(d.amount)),
			"wht_type": d.get("withholding_tax_type"),
			"wht_base": abs(flt(d.get("withholding_tax_base"))),
		}
		for d in pe.deductions
	]
	references = []
	for r in pe.references:
		kind = {"Sales Invoice": "si", "Purchase Invoice": "pi"}.get(r.reference_doctype)
		references.append(
			{
				"doctype": r.reference_doctype,
				"name": r.reference_name,
				"kind": kind,
				"total_amount": flt(r.total_amount),
				"outstanding_amount": flt(r.outstanding_amount),
				"allocated_amount": flt(r.allocated_amount),
				"modified": r.modified,
			}
		)
	row_social.attach(references)
	cash = pe.paid_to if pe.payment_type == "Receive" else pe.paid_from
	cheque = is_cheque(pe)
	certs = linked_certs(pe.name) if pe.payment_type == "Pay" else []
	has_wht = pe.payment_type == "Pay" and bool(wht_deductions(pe))
	can_cert = (
		has_wht
		and pe.docstatus == 1
		and not any(c.docstatus < 2 for c in certs)
		and bool(frappe.has_permission("Withholding Tax Cert", "create"))
	)
	return {
		"doc": {
			"name": pe.name,
			"doctype": pe.doctype,
			"docstatus": pe.docstatus,
			"modified": str(pe.modified),
			"status_label": label,
			"status_tone": tone,
			"payment_type": pe.payment_type,
			"company": pe.company,
			"party_type": pe.party_type,
			"party": pe.party,
			"party_name": pe.party_name,
			"project": pe.get("project"),
			"posting_date": pe.posting_date,
			"mode_of_payment": pe.mode_of_payment,
			"account": cash,
			"account_name": frappe.get_cached_value("Account", cash, "account_name") if cash else None,
			"reference_no": pe.reference_no,
			"reference_date": pe.reference_date,
			"is_cheque": cheque,
			"clearance_date": pe.clearance_date,
			"paid_amount": flt(pe.paid_amount),
			"total_allocated": flt(pe.total_allocated_amount),
			"unallocated": flt(pe.unallocated_amount),
			"total_deductions": sum(d["amount"] for d in deductions),
			"remarks": pe.remarks,
			"tax_invoice_number": pe.get("tax_invoice_number"),
			"tax_invoice_date": pe.get("tax_invoice_date"),
			"wht_status": pe.get("wht_status"),
			"references": references,
			"deductions": deductions,
			"taxes": [
				{"account": t.account_head, "description": t.description, "amount": flt(t.tax_amount)}
				for t in pe.get("taxes") or []
			],
		},
		"tax_invoices": linked_tax_invoices(pe.name),
		"certs": certs,
		"has_wht": has_wht,
		"received_certificate": payment_certificate(pe),
		"pdf_url": pdf_url(pe.doctype, pe.name),
		"can_submit": pe.docstatus == 0 and bool(pe.has_permission("submit")),
		"can_cancel": pe.docstatus == 1 and bool(pe.has_permission("cancel")),
		"can_delete": store_app.can_delete(pe),
		"can_cert": can_cert,
		"can_clear": bool(
			cheque
			and pe.docstatus == 1
			and pe.has_permission("write")
			and frappe.has_permission("Bank Clearance", "write")
			and cash
			and frappe.has_permission("Account", "read", doc=cash)
		),
	}


def load_payment(name):
	pe = frappe.get_doc("Payment Entry", name)
	pe.check_permission("read")
	return pe


@frappe.whitelist()
def get_payment(name):
	return payment_view(load_payment(name))


@frappe.whitelist(methods=["POST"])
def set_cheque_clearance(name: str, clearance_date: str | None, previous_date: str | None):
	from erpnext.accounts.doctype.bank_reconciliation_tool.bank_reconciliation_tool import update_clearance_date

	pe = frappe.get_doc("Payment Entry", name, for_update=True)
	pe.check_permission("read")
	pe.check_permission("write")
	if pe.docstatus != 1 or not is_cheque(pe):
		frappe.throw(_("บันทึกวันที่เช็คผ่านได้เฉพาะเช็ครับหรือเช็คจ่ายที่ยืนยันแล้ว"))
	if str(pe.clearance_date or "") != (previous_date or ""):
		frappe.throw(_("วันที่เช็คผ่านมีการเปลี่ยนแปลง กรุณาโหลดข้อมูลใหม่"))
	account = pe.paid_to if pe.payment_type == "Receive" else pe.paid_from
	update_clearance_date(pe.doctype, pe.name, account, clearance_date or None)
	pe.reload()
	return payment_view(pe)


@frappe.whitelist(methods=["POST"])
def submit_payment(name):
	pe = load_payment(name)
	pe.submit()
	return payment_view(pe)


@frappe.whitelist(methods=["POST"])
def cancel_payment(name):
	"""ยกเลิกรับ/จ่ายชำระ: ยกเลิกหนังสือรับรองหัก ณ ที่จ่าย และใบกำกับภาษีที่อ้างใบนี้ก่อน (อ้างอยู่ = ยกเลิกไม่ได้)"""
	pe = load_payment(name)
	pe.check_permission("cancel")
	for doctype in ("Withholding Tax Cert", "Sales Tax Invoice", "Purchase Tax Invoice"):
		for linked in frappe.get_all(
			doctype,
			filters={"voucher_type": "Payment Entry", "voucher_no": pe.name, "docstatus": 1},
			pluck="name",
		):
			frappe.get_doc(doctype, linked).cancel()
		for draft in frappe.get_all(
			doctype,
			filters={"voucher_type": "Payment Entry", "voucher_no": pe.name, "docstatus": 0},
			pluck="name",
		):
			frappe.delete_doc(doctype, draft)
	pe.reload()
	pe.cancel()
	return payment_view(frappe.get_doc("Payment Entry", pe.name))


@frappe.whitelist(methods=["POST"])
def delete_payment(name):
	store_app.delete_document(load_payment(name))


# ---------------------------------------------------------------- หนังสือรับรองหัก ณ ที่จ่าย


def company_addresses(company):
	return frappe.get_all(
		"Address",
		filters=[
			["Dynamic Link", "link_doctype", "=", "Company"],
			["Dynamic Link", "link_name", "=", company],
			["disabled", "=", 0],
		],
		fields=["name", "address_title", "address_type", "branch_code"],
		order_by="address_type asc, name asc",
	)


def party_addresses(doctype, party):
	if not party:
		return []
	return frappe.get_all(
		"Address",
		filters=[
			["Dynamic Link", "link_doctype", "=", doctype],
			["Dynamic Link", "link_name", "=", party],
			["disabled", "=", 0],
		],
		fields=["name", "address_title", "address_type", "branch_code"],
		order_by="address_type asc, name asc",
	)


def address_options(rows):
	return [
		{
			"value": r.name,
			"label": r.name,
			"description": " · ".join(
				x for x in (r.address_type, _("สาขา {0}").format(r.branch_code) if r.branch_code else "") if x
			),
		}
		for r in rows
	]


def income_types():
	return [
		{"value": r.name, "label": f"{r.name}. {r.description or ''}".strip()}
		for r in frappe.get_all(
			"Withholding Tax Type Of Income", fields=["name", "description"], order_by="name asc"
		)
	]


def cert_from_payment(pe_name):
	"""ร่างหนังสือรับรองจากการจ่ายชำระ (แบบ erpnext_thailand make_withholding_tax_cert) แถวละรายการหัก ณ ที่จ่าย"""
	pe = load_payment(pe_name)
	if pe.payment_type != "Pay" or pe.party_type != "Supplier":
		frappe.throw(_("ออกหนังสือรับรองหัก ณ ที่จ่ายได้เฉพาะการจ่ายชำระผู้ขาย/ผรม."))
	if pe.docstatus != 1:
		frappe.throw(_("ยืนยันการจ่ายชำระ {0} ก่อน").format(pe.name))
	rows = wht_deductions(pe)
	if not rows:
		frappe.throw(_("{0} ไม่มีรายการหัก ณ ที่จ่าย").format(pe.name))
	cert = frappe.new_doc("Withholding Tax Cert")
	cert.check_permission("create")
	supplier = frappe.get_cached_doc("Supplier", pe.party)
	cert.company = pe.company
	cert.supplier = pe.party
	cert.supplier_name = supplier.supplier_name
	cert.supplier_tax_id = supplier.tax_id
	cert.supplier_address = supplier.supplier_primary_address or (
		(party_addresses("Supplier", pe.party) or [frappe._dict(name=None)])[0].name
	)
	cert.company_tax_id = frappe.get_cached_value("Company", pe.company, "tax_id")
	cert.company_address = pe.get("company_tax_address") or (
		(company_addresses(pe.company) or [frappe._dict(name=None)])[0].name
	)
	cert.voucher_type = "Payment Entry"
	cert.voucher_no = pe.name
	cert.date = pe.posting_date
	# บุคคลธรรมดา = ภ.ง.ด.3, นิติบุคคล = ภ.ง.ด.53
	cert.income_tax_form = "PND3" if supplier.supplier_type == "Individual" else "PND53"
	cert.tax_payer = "Withholding"
	income = dict(
		frappe.get_all("Withholding Tax Type Of Income", fields=["name", "description"], as_list=True)
	)
	for d in rows:
		amount = abs(flt(d.amount))
		base = abs(flt(d.get("withholding_tax_base")))
		rate = (
			flt(frappe.get_cached_value("Withholding Tax Type", d.withholding_tax_type, "percent"))
			if d.get("withholding_tax_type")
			else 0
		)
		if not base and rate:
			base = flt(amount * 100 / rate, 2)
		if base and not rate:
			rate = flt(amount / base * 100, 2)
		cert.append(
			"withholding_tax_items",
			{
				"type_of_income": DEFAULT_INCOME if DEFAULT_INCOME in income else None,
				# รายงาน ภ.ง.ด. ใช้ช่องนี้เป็น "ประเภทเงินได้" = คำอธิบายของประเภทเงินได้
				"description": income.get(DEFAULT_INCOME) or d.description,
				"tax_base": base,
				"tax_rate": rate,
				"tax_amount": amount,
			},
		)
	return cert


def cert_view(cert):
	from consbiz.site_app import pdf_url

	label, tone = status_of(cert.docstatus)
	saved = not cert.is_new()
	can_submit = saved and bool(cert.has_permission("submit"))
	return {
		"doc": {
			"name": cert.name if saved else None,
			"doctype": cert.doctype,
			"docstatus": cert.docstatus,
			"modified": str(cert.modified) if saved else None,
			"status_label": label,
			"status_tone": tone,
			"company": cert.company,
			"company_tax_id": cert.company_tax_id,
			"company_address": cert.company_address,
			"supplier": cert.supplier,
			"supplier_name": cert.supplier_name,
			"supplier_tax_id": cert.supplier_tax_id,
			"supplier_address": cert.supplier_address,
			"income_tax_form": cert.income_tax_form,
			"tax_payer": cert.tax_payer,
			"date": cert.date,
			"voucher_type": cert.voucher_type,
			"voucher_no": cert.voucher_no,
			"items": [
				{
					"type_of_income": r.type_of_income,
					"description": r.description,
					"tax_base": flt(r.tax_base),
					"tax_rate": flt(r.tax_rate),
					"tax_amount": flt(r.tax_amount),
				}
				for r in cert.withholding_tax_items
			],
		},
		"options": {
			"company_addresses": address_options(company_addresses(cert.company)) if cert.company else [],
			"supplier_addresses": address_options(party_addresses("Supplier", cert.supplier)),
			"income_types": income_types(),
			"forms": [{"value": f, "label": {"PND3": "ภ.ง.ด.3", "PND53": "ภ.ง.ด.53"}[f]} for f in FORMS],
			"tax_payers": [{"value": v, "label": label} for v, label in TAX_PAYERS],
		},
		"pdf_url": pdf_url(cert.doctype, cert.name) if saved else None,
		"can_edit": cert.docstatus == 0 and (not saved or bool(cert.has_permission("write"))),
		"can_submit": cert.docstatus == 0 and can_submit,
		"can_cancel": cert.docstatus == 1 and bool(cert.has_permission("cancel")),
		"can_delete": saved and store_app.can_delete(cert),
	}


def load_cert(name):
	cert = frappe.get_doc("Withholding Tax Cert", name)
	cert.check_permission("read")
	return cert


@frappe.whitelist()
def get_cert(name=None, source=None):
	"""หน้าหนังสือรับรอง: name = เปิดใบเดิม / source = การจ่ายชำระต้นทาง (ใบใหม่ยังไม่บันทึก)"""
	if name:
		return cert_view(load_cert(name))
	if not source:
		frappe.throw(_("หนังสือรับรองหัก ณ ที่จ่ายออกจากการจ่ายชำระเท่านั้น"))
	return cert_view(cert_from_payment(source))


@frappe.whitelist(methods=["POST"])
def save_cert(data, submit=0):
	data = frappe._dict(json.loads(data) if isinstance(data, str) else data)
	if data.name:
		cert = load_cert(data.name)
		cert.check_permission("write")
		if cert.docstatus != 0:
			frappe.throw(_("{0} ไม่ใช่ร่างแล้ว แก้ไขไม่ได้").format(cert.name))
		if data.modified and str(cert.modified) != str(data.modified):
			frappe.throw(_("มีผู้อื่นแก้ไข {0} ไปแล้ว กรุณาโหลดใหม่").format(cert.name))
	else:
		cert = cert_from_payment(data.voucher_no)
		existing = [c for c in linked_certs(cert.voucher_no) if c.docstatus < 2]
		if existing:
			frappe.throw(_("{0} มีหนังสือรับรอง {1} แล้ว").format(cert.voucher_no, existing[0].name))
	if data.income_tax_form not in FORMS:
		frappe.throw(_("กรุณาเลือกแบบ ภ.ง.ด."))
	cert.income_tax_form = data.income_tax_form
	cert.tax_payer = data.tax_payer or "Withholding"
	cert.date = data.date or cert.date
	cert.company_address = data.company_address or cert.company_address
	cert.supplier_address = data.supplier_address or cert.supplier_address
	cert.set("withholding_tax_items", [])
	for row in data.get("items") or []:
		row = frappe._dict(row)
		base = flt(row.tax_base, 2)
		rate = flt(row.tax_rate)
		cert.append(
			"withholding_tax_items",
			{
				"type_of_income": row.type_of_income,
				"description": row.description,
				"tax_base": base,
				"tax_rate": rate,
				"tax_amount": flt(row.tax_amount, 2)
				if row.tax_amount not in (None, "")
				else flt(base * rate / 100, 2),
			},
		)
	if not cert.withholding_tax_items:
		frappe.throw(_("ต้องมีรายการอย่างน้อย 1 แถว"))
	cert.save()
	if cint(submit):
		cert.submit()
	return cert_view(cert)


@frappe.whitelist(methods=["POST"])
def submit_cert(name):
	cert = load_cert(name)
	cert.submit()
	return cert_view(cert)


@frappe.whitelist(methods=["POST"])
def cancel_cert(name):
	cert = load_cert(name)
	cert.cancel()
	return cert_view(frappe.get_doc(cert.doctype, cert.name))


@frappe.whitelist(methods=["POST"])
def delete_cert(name):
	store_app.delete_document(load_cert(name))


# ---------------------------------------------------------------- ใบกำกับภาษีขาย / ซื้อ


def tax_doctype(type):
	if type not in TAX_TYPES:
		frappe.throw(_("ไม่รองรับ"), frappe.PermissionError)
	return TAX_TYPES[type]


def tax_view(tinv):
	label, tone = status_of(tinv.docstatus)
	editable = tinv.docstatus == 1 and bool(tinv.has_permission("write"))
	voucher_kind = {"Sales Invoice": "si", "Purchase Invoice": "pi"}.get(tinv.voucher_type)
	return {
		"doc": {
			"name": tinv.name,
			"doctype": tinv.doctype,
			"docstatus": tinv.docstatus,
			"modified": str(tinv.modified),
			"status_label": label,
			"status_tone": tone,
			"company": tinv.company,
			"number": tinv.get("number"),
			"date": tinv.date,
			"report_date": tinv.report_date,
			"months_delayed": cint(tinv.months_delayed),
			"party": tinv.party,
			"party_name": tinv.party_name,
			"tax_id": tinv.tax_id,
			"branch_code": tinv.branch_code,
			"tax_base": flt(tinv.tax_base),
			"tax_amount": flt(tinv.tax_amount),
			"tax_percent": flt(tinv.get("tax_percent")),
			"company_tax_address": tinv.company_tax_address,
			"voucher_type": tinv.voucher_type,
			"voucher_no": tinv.voucher_no,
			"voucher_kind": voucher_kind,
			"against_voucher_type": tinv.get("against_voucher_type"),
			"against_voucher": tinv.get("against_voucher"),
		},
		"edit": list(TAX_EDIT[tinv.doctype]) if editable else [],
	}


@frappe.whitelist()
def get_tax_invoice(type, name):
	tinv = frappe.get_doc(tax_doctype(type), name)
	tinv.check_permission("read")
	return tax_view(tinv)


@frappe.whitelist(methods=["POST"])
def save_tax_invoice(type, name, values):
	"""แก้หลัง Submit: ภาษีซื้อ = เลขที่/วันที่ใบกำกับของผู้ขาย + ยื่นล่าช้า (เดือน), ภาษีขาย = ยื่นล่าช้า"""
	doctype = tax_doctype(type)
	tinv = frappe.get_doc(doctype, name)
	tinv.check_permission("write")
	if tinv.docstatus != 1:
		frappe.throw(_("แก้ได้เฉพาะใบที่ยืนยันแล้ว"))
	values = json.loads(values) if isinstance(values, str) else values
	for field, value in (values or {}).items():
		if field not in TAX_EDIT[doctype]:
			frappe.throw(_("แก้ช่อง {0} ไม่ได้").format(field))
		if field == "months_delayed":
			value = str(min(max(cint(value), 0), 6))
		if field in ("number", "date") and not value:
			frappe.throw(_("เลขที่และวันที่ใบกำกับภาษีห้ามว่าง"))
		tinv.set(field, value)
	tinv.save()
	return tax_view(frappe.get_doc(doctype, name))


# ---------------------------------------------------------------- รายงานภาษี


def report_docname(key, row):
	# Purchase report "name" is the supplier invoice number, tax_invoice is the ERPNext document.
	return row.get("tax_invoice") if key == "purchase" else (row.get("name") or "").removesuffix(" (CANCEL)")


def report_columns(key):
	"""คอลัมน์ที่แสดงในแอป (fieldname, หัวตาราง, ชนิด)"""
	if key in ("sales", "purchase"):
		return [
			("date", _("วันที่"), "Date"),
			("name", _("เลขที่ใบกำกับ"), "Data"),
			("party_name", _("ลูกค้า") if key == "sales" else _("ผู้ขาย"), "Data"),
			("tax_id", _("เลขประจำตัวผู้เสียภาษี"), "Data"),
			("branch_code", _("สาขา"), "Data"),
			("tax_base", _("มูลค่าสินค้า/บริการ"), "Currency"),
			("tax_amount", _("ภาษีมูลค่าเพิ่ม"), "Currency"),
			("voucher_no", _("เอกสารอ้างอิง"), "Data"),
		]
	return [
		("no", _("ลำดับ"), "Int"),
		("supplier_tax_id", _("เลขประจำตัวผู้เสียภาษี"), "Data"),
		("branch", _("สาขา"), "Data"),
		("supplier_name", _("ชื่อผู้มีเงินได้"), "Data"),
		("date", _("วันที่จ่าย"), "Date"),
		("description", _("ประเภทเงินได้"), "Data"),
		("tax_rate", _("อัตรา %"), "Float"),
		("tax_base", _("จำนวนเงินที่จ่าย"), "Currency"),
		("tax_amount", _("ภาษีที่หัก"), "Currency"),
		("name", _("หนังสือรับรอง"), "Data"),
	]


def run_report(key, year, month, company=None, company_address=None):
	if key not in REPORTS:
		frappe.throw(_("ไม่รองรับรายงานนี้"), frappe.PermissionError)
	if key not in readable_reports():
		frappe.throw(_("ไม่มีสิทธิ์ดูรายงานนี้"), frappe.PermissionError)
	report, module, doctype = REPORTS[key]
	report_month(year, month)
	year, month = cint(year), cint(month)
	filters = frappe._dict(year=str(year), month=str(month), company_address=company_address or None)
	if key in ("sales", "purchase"):
		filters.update(filter_based_on="Fiscal Year", company_tax_address=company_address or None)
	_columns, data, *_rest = frappe.get_attr(f"{module}.execute")(filters)
	rows = [frappe._dict(r) for r in data or []]
	if rows:
		for row in rows:
			row.docname = report_docname(key, row)
		filters = {"name": ["in", [r.docname for r in rows]]}
		if company:
			filters["company"] = company
		visible = {r.name: r for r in row_social.get_list(
			doctype, filters=filters, fields=["name", "modified"], limit_page_length=0
		)}
		rows = [r for r in rows if r.docname in visible]
		for row in rows:
			row.update(row_social.metadata(visible[row.docname]), modified=visible[row.docname].modified)
	if key in ("pnd3", "pnd53"):
		for i, row in enumerate(rows, 1):
			row.no = i
	if key == "pnd3":
		# ภ.ง.ด.3 แยกชื่อ/นามสกุล (แบบยื่น) แอปแสดงชื่อเต็ม
		for r in rows:
			r["supplier_name"] = " ".join(x for x in (r.get("firstname"), r.get("lastname")) if x).strip()
	totals = {
		"tax_base": flt(sum(flt(r.get("tax_base")) for r in rows), 2),
		"tax_amount": flt(sum(flt(r.get("tax_amount")) for r in rows), 2),
		"count": len(rows),
	}
	return report, rows, totals


OFFICIAL_FORMS = {
	"sales": "sales_tax_report",
	"purchase": "purchase_tax_report",
	"pnd3": "pnd3",
	"pnd53": "pnd53",
}


@frappe.whitelist()
def get_official_form(key, year, month, company=None, company_address=None):
	"""แม่แบบพิมพ์ทางการของ erpnext_thailand (query-report print template) + data/filters ที่ Desk ส่งให้แม่แบบ
	data = แถวรายงานที่ผู้ใช้เห็น + แถวรวมท้ายตาราง (Desk เพิ่มเพราะรายงานตั้ง add_total_row; แม่แบบตัดแถวสุดท้ายออกเอง)"""
	folder = OFFICIAL_FORMS.get(key)
	if not folder:
		frappe.throw(_("ไม่รองรับรายงานนี้"), frappe.PermissionError)
	_report, rows, totals = run_report(key, year, month, company, company_address)
	if not rows:
		return {"empty": True}
	path = frappe.get_app_path("erpnext_thailand", "thai_tax", "report", folder, f"{folder}.html")
	with open(path, encoding="utf-8") as f:
		template = f.read()
	skip = {"docname", "modified", "doctype", "_comment_count", "_liked_by"}
	data = [{k: v for k, v in r.items() if k not in skip} for r in rows]
	data.append({"is_total_row": 1, "tax_base": totals["tax_base"], "tax_amount": totals["tax_amount"]})
	from frappe.utils.jinja_globals import bundled_asset
	from frappe.www.printview import get_print_style

	print_style = frappe.db.get_single_value("Print Settings", "print_style") or "Redesign"
	return {
		"template": template,
		"print_css": get_print_style(print_style, for_legacy=True),
		"print_bundle": bundled_asset("print.bundle.css"),
		"data": data,
		"filters": {"year": str(cint(year)), "month": str(cint(month)), "company_address": company_address or None},
	}


@frappe.whitelist()
def get_report(key, year, month, company=None, company_address=None):
	report, rows, totals = run_report(key, year, month, company, company_address)
	columns = report_columns(key)
	fields = [c[0] for c in columns] + ["voucher_type", "voucher_no", "name", "docname", "modified", "doctype", "_comment_count", "_liked_by"]
	if key == "purchase":
		fields.append("tax_invoice")
	return {
		"report": report,
		"columns": [{"fieldname": f, "label": label, "fieldtype": t} for f, label, t in columns],
		"rows": [{f: r.get(f) for f in fields} for r in rows],
		"totals": totals,
	}


@frappe.whitelist()
def report_options(company=None):
	"""ตัวเลือกของหน้ารายงานภาษี: รายงานที่เปิดได้ + ที่อยู่บริษัท (สาขาที่ยื่น)"""
	rows = (
		company_addresses(company)
		if company
		else frappe.get_all(
			"Address",
			filters={"is_your_company_address": 1, "disabled": 0},
			fields=["name", "address_title", "address_type", "branch_code"],
		)
	)
	return {"reports": readable_reports(), "addresses": address_options(rows)}


@frappe.whitelist()
def export_report(key, year, month, company=None, company_address=None):
	"""ดาวน์โหลด Excel ของรายงานภาษี (ตามที่แสดงในแอป + แถวรวม)"""
	from frappe.utils.xlsxutils import make_xlsx

	report, rows, totals = run_report(key, year, month, company, company_address)
	columns = report_columns(key)
	sheet = [[label for _f, label, _t in columns]]
	for r in rows:
		sheet.append([r.get(f) if t != "Date" or not r.get(f) else str(r.get(f)) for f, _label, t in columns])
	total_row = ["" for _c in columns]
	total_row[0] = _("รวม {0} รายการ").format(totals["count"])
	for i, (f, _label, _t) in enumerate(columns):
		if f in ("tax_base", "tax_amount"):
			total_row[i] = totals[f]
	sheet.append(total_row)
	title = f"{report} {cint(year)}-{cint(month):02d}"
	xlsx = make_xlsx(sheet, title[:31])
	frappe.response["filename"] = f"{title}.xlsx"
	frappe.response["filecontent"] = xlsx.getvalue()
	frappe.response["type"] = "binary"
