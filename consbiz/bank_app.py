"""Company bank accounts and their company-currency GL movements for ConsERP."""

import re
from decimal import Decimal

import frappe
from frappe import _
from frappe.utils import add_months, cint, get_first_day, get_last_day, getdate

from consbiz import row_social

FIELDS = [
	"name",
	"account_name",
	"bank",
	"bank_account_no",
	"branch_code",
	"iban",
	"account",
	"company",
	"is_default",
	"disabled",
	"modified",
]


def _amount(value):
	return Decimal(str(value or 0))


def _net(row):
	return _amount(row.debit) - _amount(row.credit)


def _balances(accounts, date_filter, project=None):
	if not accounts:
		return {}
	rows = frappe.get_list(
		"GL Entry",
		filters={"account": ["in", accounts], "posting_date": date_filter, "is_cancelled": 0, **({"project": project} if project else {})},
		fields=["account", {"SUM": "debit", "as": "debit"}, {"SUM": "credit", "as": "credit"}],
		group_by="account",
		order_by="account",
		limit_page_length=0,
	)
	return {row.account: _net(row) for row in rows}


def _currencies(companies):
	if not frappe.has_permission("Company", "read"):
		return {}
	return dict(
		frappe.get_list(
			"Company",
			filters={"name": ["in", list(companies)]},
			fields=["name", "default_currency"],
			as_list=True,
			limit_page_length=0,
		)
	)


def _company_account(name, permission="read"):
	doc = frappe.get_doc("Bank Account", name)
	doc.check_permission(permission)
	if not doc.is_company_account:
		frappe.throw(_("เฉพาะบัญชีธนาคารของบริษัท"), frappe.PermissionError)
	return doc


@frappe.whitelist()
def list_accounts(company: str | None = None, project: str | None = None):
	filters = {"is_company_account": 1}
	if company:
		filters["company"] = company
	rows = row_social.get_list(
		"Bank Account",
		filters=filters,
		fields=FIELDS,
		order_by="account_name, name",
		limit_page_length=0,
	)
	can_gl = bool(frappe.has_permission("GL Entry", "read"))
	if can_gl and rows:
		balances = _balances([r.account for r in rows if r.account], ["<=", getdate()], project)
		currencies = _currencies({r.company for r in rows})
		for row in rows:
			row.balance = balances.get(row.account, 0) if row.account else None
			row.currency = currencies.get(row.company)
	return {"rows": rows, "can_gl": can_gl}


@frappe.whitelist()
def get_account(name: str, month: str | None = None, company: str | None = None, project: str | None = None):
	doc = _company_account(name)
	if company and company != doc.company:
		frappe.throw(_("บัญชีนี้อยู่นอกบริษัทที่เลือก"), frappe.PermissionError)
	result = {
		"doc": {field: doc.get(field) for field in FIELDS},
		"can_write": bool(doc.has_permission("write")),
		"can_gl": bool(doc.account and frappe.has_permission("GL Entry", "read")),
	}
	if not result["can_gl"]:
		return result

	today = getdate()
	if month:
		if not re.fullmatch(r"[1-9]\d{3}-(0[1-9]|1[0-2])", month):
			frappe.throw(_("กรุณาเลือกเดือน"))
		start = getdate(f"{month}-01")
		if start > today:
			frappe.throw(_("กรุณาเลือกเดือนที่ไม่เกินเดือนปัจจุบัน"))
		end = min(get_last_day(start), today)
	else:
		start, end = get_first_day(add_months(today, -2)), today

	account = doc.account
	opening = _balances([account], ["<", start], project).get(account, 0)
	rows = frappe.get_list(
		"GL Entry",
		filters={
			"account": account,
			"company": doc.company,
			**({"project": project} if project else {}),
			"is_cancelled": 0,
			"posting_date": ["between", [start, end]],
		},
		fields=["name", "posting_date", "voucher_type", "voucher_no", "party", "remarks", "debit", "credit", "modified"],
		order_by="posting_date asc, creation asc, name asc",
		limit_page_length=0,
	)
	fill_vouchers(rows)
	row_social.attach(rows, doctype_field="voucher_type", name_field="voucher_no")
	running = opening
	for row in rows:
		running += _net(row)
		row.balance = running
	result.update(
		rows=rows,
		opening=opening,
		closing=running,
		from_date=start,
		to_date=end,
		balance=running if end == today else _balances([account], ["<=", today], project).get(account, 0),
		currency=_currencies([doc.company]).get(doc.company),
	)
	return result


def fill_vouchers(rows):
	payments = {r.voucher_no for r in rows if r.voucher_type == "Payment Entry"}
	payment_details = (
		{
			payment.name: payment
			for payment in frappe.get_list(
				"Payment Entry",
				filters={"name": ["in", list(payments)]},
				fields=["name", "payment_type", "party_name", "party"],
				limit_page_length=0,
			)
		}
		if payments and frappe.has_permission("Payment Entry", "read")
		else {}
	)
	journals = {r.voucher_no for r in rows if r.voucher_type == "Journal Entry" and r.voucher_no and not r.party}
	journal_parties = {}
	if journals and frappe.has_permission("Journal Entry", "read"):
		for entry in frappe.get_list(
			"Journal Entry",
			filters={"name": ["in", list(journals)]},
			fields=["name", "accounts.party as party"],
			order_by="accounts.idx asc",
			limit_page_length=0,
		):
			if entry.party:
				journal_parties.setdefault(entry.name, entry.party)

	for row in rows:
		if row.voucher_type == "Payment Entry" and (payment := payment_details.get(row.voucher_no)):
			row.payment_view = "acc-receipts" if payment.payment_type == "Receive" else "acc-payments"
			row.party = row.party or payment.party_name or payment.party
		elif row.voucher_type == "Journal Entry" and not row.party:
			row.party = journal_parties.get(row.voucher_no)


@frappe.whitelist()
def form_options(company: str, name: str | None = None):
	if name:
		doc = _company_account(name, "write")
		if doc.company != company:
			frappe.throw(_("เปลี่ยนบริษัทของบัญชีไม่ได้"))
	else:
		frappe.has_permission("Bank Account", "create", throw=True)
	return {
		"banks": frappe.get_list("Bank", pluck="name", order_by="name", limit_page_length=0),
		"accounts": frappe.get_list(
			"Account",
			filters={"company": company, "is_group": 0, "account_type": "Bank"},
			pluck="name",
			order_by="name",
			limit_page_length=0,
		),
		"can_create_bank": bool(frappe.has_permission("Bank", "create")),
	}


@frappe.whitelist(methods=["POST"])
def save_account(
	company: str,
	account_name: str,
	bank: str,
	account: str,
	bank_account_no: str = "",
	is_default: int = 0,
	name: str | None = None,
	modified: str | None = None,
	new_bank: int = 0,
):
	if name:
		doc = _company_account(name, "write")
		if company != doc.company:
			frappe.throw(_("เปลี่ยนบริษัทของบัญชีไม่ได้"))
		if modified != str(doc.modified):
			frappe.throw(_("ข้อมูลเปลี่ยนแล้ว กรุณาโหลดใหม่"), frappe.TimestampMismatchError)
	else:
		doc = frappe.new_doc("Bank Account")
		doc.update({"company": company, "is_company_account": 1})
		doc.check_permission("create")

	frappe.has_permission("Company", "read", doc=company, throw=True)
	frappe.has_permission("Account", "read", doc=account, throw=True)
	bank = bank.strip()
	if cint(new_bank):
		bank = frappe.get_doc({"doctype": "Bank", "bank_name": bank}).insert().name
	else:
		frappe.has_permission("Bank", "read", doc=bank, throw=True)
	doc.update(
		{
			"account_name": account_name.strip(),
			"bank": bank,
			"account": account,
			"bank_account_no": bank_account_no.strip(),
			"is_default": int(bool(cint(is_default))),
		}
	)
	doc.save()
	return doc.name
