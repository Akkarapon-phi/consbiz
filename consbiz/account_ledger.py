"""Account tree and chronological GL, in company currency."""

import frappe
from frappe.utils import cint, get_first_day, get_last_day, getdate
from erpnext.accounts.utils import get_fiscal_year

from consbiz import bank_app, row_social
from consbiz.received_wht import download

PAGE_SIZE = 500
BALANCE_SHEET = ("Asset", "Liability", "Equity")
GL_FIELDS = ["name", "posting_date", "voucher_type", "voucher_no", "party", "remarks", "debit", "credit", "modified"]


def check_access():
	for dt in ("Account", "GL Entry"):
		frappe.has_permission(dt, "read", throw=True)


def party_conditions(company, party):
	if not party:
		return None
	conditions = [["party", "=", party]]
	for dt, fields in (("Payment Entry", ["party", "party_name"]), ("Journal Entry", ["accounts.party"]),
		("Sales Invoice", ["customer", "customer_name"]), ("Purchase Invoice", ["supplier", "supplier_name"])):
		if not frappe.has_permission(dt, "read"):
			continue
		names = frappe.get_list(dt, filters={"company": company}, or_filters={f: party for f in fields},
			pluck="name", limit_page_length=0)
		if names:
			conditions.extend(["or", [["party", "is", "not set"], "and", ["voucher_type", "=", dt],
				"and", ["voucher_no", "in", names]]])
	return conditions if len(conditions) > 1 else {"party": party}


def totals(filters, parties):
	row = frappe.get_list("GL Entry", filters=filters, or_filters=parties, fields=[
		{"SUM": "debit", "as": "debit"}, {"SUM": "credit", "as": "credit"},
	], order_by="", limit_page_length=1)[0]
	return bank_app._net(row)


@frappe.whitelist()
def chart(company=None, project=None):
	check_access()
	rows = row_social.get_list("Account", filters={"company": company} if company else {},
		fields=["name", "company", "account_name", "account_number", "parent_account", "root_type", "is_group", "modified"],
		order_by="company, lft", limit_page_length=0)
	today = getdate()
	# Like ERPNext's Trial Balance, income/expense accounts only count the current fiscal year.
	balances = bank_app._balances([r.name for r in rows if not r.is_group and r.root_type in BALANCE_SHEET], ["<=", today], project)
	for name in {r.company for r in rows}:
		fy = get_fiscal_year(today, company=name, raise_on_missing=False)
		accounts = [r.name for r in rows if r.company == name and not r.is_group and r.root_type not in BALANCE_SHEET]
		balances.update(bank_app._balances(accounts, ["between", [fy[1] if fy else get_first_day(today, 0, 0), today]], project))
	by_name = {r.name: r for r in rows}
	for row in rows:
		parent = by_name.get(row.parent_account)
		row.depth = parent.depth + 1 if parent and parent.depth is not None else 0
		row.balance = balances.get(row.name, 0)
	for row in reversed(rows):
		if parent := by_name.get(row.parent_account):
			parent.balance += row.balance
		if row.root_type in ("Liability", "Equity", "Income"):
			row.balance = -row.balance
	return rows


def ledger_data(account, company, project, party, from_date, to_date, offset, export=False):
	check_access()
	doc = frappe.get_doc("Account", account)
	doc.check_permission("read")
	if doc.is_group or (company and doc.company != company):
		frappe.throw("กรุณาเลือกบัญชีแยกประเภทของบริษัท", frappe.PermissionError)
	today = getdate()
	start, end = getdate(from_date or get_first_day(today)), getdate(to_date or get_last_day(today))
	if start > end:
		frappe.throw("วันที่สิ้นสุดต้องไม่ก่อนวันที่เริ่ม")
	base = {"company": doc.company, "account": doc.name, "is_cancelled": 0}
	if project:
		base["project"] = project
	parties = party_conditions(doc.company, party)
	opening = totals({**base, "posting_date": ["<", start]}, parties)
	period = {**base, "posting_date": ["between", [start, end]]}
	closing = opening + totals(period, parties)
	rows = frappe.get_list("GL Entry", filters=period, or_filters=parties, fields=GL_FIELDS, order_by="posting_date, creation, name",
		start=max(0, cint(offset)), limit_page_length=0 if export else PAGE_SIZE + 1)
	has_more = not export and len(rows) > PAGE_SIZE
	if has_more:
		rows.pop()
	bank_app.fill_vouchers(rows)
	if not export:
		row_social.attach(rows, doctype_field="voucher_type", name_field="voucher_no")
	for dt, field in (("Sales Invoice", "customer_name"), ("Purchase Invoice", "supplier_name")):
		names = {r.voucher_no for r in rows if r.voucher_type == dt}
		if names and frappe.has_permission(dt, "read"):
			parties = dict(frappe.get_list(dt, filters={"name": ["in", list(names)]}, fields=["name", field],
				as_list=True, limit_page_length=0))
			for r in rows:
				if r.voucher_type == dt and r.voucher_no in parties:
					r.invoice_kind = "acc-si" if dt == "Sales Invoice" else "acc-pi"
					r.party = r.party or parties[r.voucher_no]
	fy = get_fiscal_year(today, company=doc.company, raise_on_missing=False)
	return dict(account=doc.name, company=doc.company, opening=opening, closing=closing, from_date=start,
		to_date=end, fiscal_year=fy[1:3] if fy else None, rows=rows, has_more=has_more)


@frappe.whitelist()
def ledger(account: str, company=None, project=None, party=None, from_date=None, to_date=None, offset=0):
	return ledger_data(account, company, project, party, from_date, to_date, offset)


@frappe.whitelist()
def export_ledger(account: str, company=None, project=None, party=None, from_date=None, to_date=None):
	data = ledger_data(account, company, project, party, from_date, to_date, 0, export=True)
	running = data["opening"]
	sheet = [[account, data["company"]], [data["from_date"], data["to_date"]],
		["วันที่", "เอกสาร", "ประเภท", "คู่ค้า", "หมายเหตุ", "เดบิต", "เครดิต", "คงเหลือ"],
		[data["from_date"], "ยอดยกมา", "", "", "", "", "", running]]
	for r in data["rows"]:
		running += bank_app._net(r)
		sheet.append([r.posting_date, r.voucher_no, r.voucher_type, r.party, r.remarks, r.debit, r.credit, running])
	sheet.append([data["to_date"], "ยอดปลายงวด", "", "", "", "", "", data["closing"]])
	download("บัญชีแยกประเภท " + str(data["to_date"]), sheet)
