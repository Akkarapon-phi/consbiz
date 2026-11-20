"""Customer withholding on receipts and the corresponding private 50 ทวิ attachments."""

from collections import defaultdict
import re

import frappe
from frappe.utils import flt, get_last_day, getdate
from frappe.utils.xlsxutils import make_xlsx

from consbiz import accounting_app, retention_app, row_social

TITLE = "รายงานภาษีถูกหัก ณ ที่จ่าย"


def receivable_accounts(company):
	"""Company account and Thailand's receipt-enabled tax type mappings, else ledger name."""
	configured = accounting_app.wht_accounts(company)["Receive"]
	mappings = frappe.get_all(
		"Withholding Tax Type",
		filters={"accounts.company": company, "for_payment_type": ["in", ["Receive", "Pay and Receive"]]},
		fields=["accounts.account as account"],
	)
	accounts = {row.account for row in mappings if row.account}
	if configured:
		accounts.add(configured)
	return accounts or set(frappe.get_all("Account", filters={
		"company": company, "account_name": ["like", "%ถูกหัก%"], "is_group": 0,
	}, pluck="name"))


def certificate_files(names):
	# Callers have already checked read access to each parent Payment Entry.
	if not names:
		return {}
	files = frappe.get_all("File", filters={
		"attached_to_doctype": "Payment Entry", "attached_to_name": ["in", names],
		"is_folder": 0, "file_name": ["like", "%50%ทวิ%"],
	}, fields=["attached_to_name", "file_name", "file_url"], order_by="creation desc")
	result = {}
	for file in files:
		if re.search(r"50[\s_-]*ทวิ", file.file_name):
			result.setdefault(file.attached_to_name, file.file_url)
	return result


def payment_certificate(pe):
	if pe.payment_type != "Receive" or pe.party_type != "Customer" or pe.docstatus != 1:
		return None
	accounts = receivable_accounts(pe.company)
	if not any(d.account in accounts and d.amount for d in pe.deductions):
		return None
	return {
		"url": certificate_files([pe.name]).get(pe.name),
		"can_attach": bool(pe.has_permission("write") and frappe.has_permission("File", "create")),
	}


def month_range(month):
	if not re.fullmatch(r"[1-9]\d{3}-(0[1-9]|1[0-2])", month or ""):
		frappe.throw("กรุณาเลือกเดือน")
	start = getdate(month + "-01")
	return [start, get_last_day(start)]


@frappe.whitelist()
def receipts(company=None, project=None, month=None, company_address=None, status=None):
	filters = dict(retention_app.scope_filters(company, project), payment_type="Receive", party_type="Customer",
		docstatus={"submitted": 1, "cancelled": 2, "all": ["in", [1, 2]]}.get(
			status, 1 if month else ["in", [1, 2]]))
	if month:
		filters["posting_date"] = ["between", month_range(month)]
	if company_address:
		filters["company_tax_address"] = company_address
	rows = row_social.get_list("Payment Entry", filters=filters,
		fields=["name", "company", "party", "party_name", "project", "posting_date", "docstatus", "modified"],
		order_by="posting_date desc, name desc", limit_page_length=0)
	if not rows:
		return []
	by_company = {c: receivable_accounts(c) for c in {r.company for r in rows}}
	parents = {r.name: r for r in rows}
	child_filters = {"parenttype": "Payment Entry", "parent": ["in", list(parents)]}
	deductions = defaultdict(list)
	for d in frappe.get_all("Payment Entry Deduction", filters=child_filters,
		fields=["parent", "account", "amount", "withholding_tax_base"]):
		if d.amount and d.account in by_company[parents[d.parent].company]:
			deductions[d.parent].append(d)
	rows = [r for r in rows if r.name in deductions]
	invoices = defaultdict(list)
	full_refs = defaultdict(list)
	for ref in frappe.get_all("Payment Entry Reference", filters={**child_filters, "reference_doctype": "Sales Invoice"},
		fields=["parent", "reference_name", "allocated_amount", "total_amount"], order_by="idx"):
		invoices[ref.parent].append(ref.reference_name)
		if ref.allocated_amount > 0 and flt(ref.allocated_amount - ref.total_amount, 2) == 0:
			full_refs[ref.parent].append(ref.reference_name)
	names = {n for refs in full_refs.values() for n in refs}
	invoice_bases = {i.name: i for i in frappe.get_list("Sales Invoice", filters={"name": ["in", list(names)]},
		fields=["name", "base_net_total", "custom_wht_percent"], limit_page_length=0)} if names and accounting_app.can_read("Sales Invoice") else {}
	files = certificate_files(list(deductions))
	retention_app.set_project_names(rows)
	for r in rows:
		lines = deductions[r.name]
		r.amount = sum(d.amount for d in lines)
		# Never assume that a partial or multi-invoice receipt taxes the entire invoice.
		r.tax_base = sum(abs(d.withholding_tax_base) for d in lines) if all(d.withholding_tax_base for d in lines) else None
		refs = invoices[r.name]
		if r.tax_base is None and refs and refs == full_refs[r.name] and all(n in invoice_bases for n in refs):
			bases = [invoice_bases[n] for n in refs]
			expected = sum(flt(i.base_net_total * i.custom_wht_percent / 100, 2) for i in bases)
			if all(i.custom_wht_percent for i in bases) and flt(expected - r.amount, 2) == 0:
				r.tax_base = sum(i.base_net_total for i in bases)
		r.refs = ", ".join(dict.fromkeys(invoices[r.name]))
		r.received = r.name in files
		r.status_label, r.status_tone = (
			("ยกเลิก", "rose") if r.docstatus == 2 else
			("ได้รับหนังสือแล้ว", "green") if r.received else ("ยังไม่ได้รับ", "amber")
		)
	return rows


def download(title, sheet):
	frappe.response.update(filename=title + ".xlsx", filecontent=make_xlsx(sheet, title[:31]).getvalue(), type="binary")


@frappe.whitelist()
def export_month(month: str, company=None, project=None, company_address=None, status="submitted"):
	rows = receipts(company, project, month, company_address, status)
	base = any(r.tax_base is not None for r in rows)
	sheet = [["เลขที่", "สถานะ", "ลูกค้า", "โครงการ", "ใบแจ้งหนี้", "วันที่รับ",
		*(["ฐานภาษี"] if base else []), "ภาษีถูกหัก"]]
	for r in rows:
		sheet.append([r.name, r.status_label, r.party_name or r.party, r.project_name or r.project, r.refs,
			r.posting_date, *([r.tax_base] if base else []), r.amount])
	sheet.append(["รวม", "", "", "", "", "", *([""] if base else []), flt(sum(r.amount for r in rows), 2)])
	download(f"{TITLE} {month}", sheet)
