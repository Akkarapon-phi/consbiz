"""Permission-filtered accounting balances and aging in company currency."""

from collections import defaultdict

import frappe
from frappe.utils import get_first_day, get_last_day, getdate

from consbiz import accounting_app as acc, row_social
from consbiz import bank_app, retention_app


def aging(rows, today, currency):
	buckets = [0] * 5
	overdue = 0
	for r in rows:
		days = (today - getdate(r.due_date)).days if r.due_date else 0
		amount = r.outstanding_amount
		if r.party_account_currency and r.party_account_currency != currency:
			amount *= r.conversion_rate
		bucket = sum(days > limit for limit in (0, 30, 60, 90))
		buckets[bucket] += amount
		overdue += int(days > 0 and amount > 0)
	return dict(amount=sum(buckets), count=len(rows), overdue=overdue, buckets=buckets)


def month_vat(dt, companies, project, today):
	rows = frappe.get_list(dt, filters={"company": ["in", companies], "docstatus": 1,
		"report_date": ["between", [get_first_day(today), get_last_day(today)]]},
		fields=["tax_amount", "voucher_type", "voucher_no"], limit_page_length=0)
	if project:
		visible = set()
		for voucher in {r.voucher_type for r in rows}:
			if voucher and frappe.get_meta(voucher).has_field("project") and acc.can_read(voucher):
				names = [r.voucher_no for r in rows if r.voucher_type == voucher]
				visible.update((voucher, n) for n in frappe.get_list(voucher,
					filters={"name": ["in", names], "project": project}, pluck="name", limit_page_length=0))
		rows = [r for r in rows if (r.voucher_type, r.voucher_no) in visible]
	return sum(round(r.tax_amount, 2) for r in rows)


def currency_summary(companies, currency, project, today):
	company = ["in", companies]
	scope = retention_app.scope_filters(company, project)
	submitted = {**scope, "docstatus": 1}
	out = {"currency": currency}
	for key, dt in acc.INVOICES.items():
		if acc.can_read(dt):
			rows = frappe.get_list(dt, filters={**submitted, "outstanding_amount": ["!=", 0]},
				fields=["due_date", "outstanding_amount", "party_account_currency", "conversion_rate"], limit_page_length=0)
			out[key] = aging(rows, today, currency)
	if acc.can_read("Bank Account") and acc.can_read("GL Entry"):
		accounts = frappe.get_list("Bank Account", filters={"company": company, "is_company_account": 1},
			pluck="account", limit_page_length=0)
		out["bank"] = sum(bank_app._balances([a for a in set(accounts) if a], ["<=", today], project).values())
	if acc.can_read("Payment Entry"):
		modes = acc.cheque_modes()
		for side, key, field in (("Receive", "receipts", "base_received_amount"), ("Pay", "payments", "base_paid_amount")):
			filters = {**submitted, "payment_type": side}
			rows = row_social.get_list("Payment Entry", filters=filters,
				fields=["name", "posting_date", "party_name", "party", "modified", f"{field} as amount"],
				order_by="posting_date desc, modified desc, name desc", limit_page_length=5)
			out[key] = rows
			amounts = frappe.get_list("Payment Entry", filters={**filters, "mode_of_payment": ["in", modes],
				"clearance_date": ["is", "not set"]}, pluck=field, limit_page_length=0) if modes else []
			out[key + "_waiting"] = {"count": len(amounts), "amount": sum(amounts)}
		if acc.can_read("Withholding Tax Cert"):
			out["to_issue"] = acc.to_issue_count(company, project)
	for side, spec in retention_app.SIDES.items():
		if acc.can_read(spec.source):
			rows = frappe.get_list(spec.source, filters=submitted, fields=["grand_total", "paid_amount"], limit_page_length=0)
			out["retention_" + side] = sum(r.grand_total - r.paid_amount for r in rows)
	if all(acc.can_read(dt) for dt in acc.TAX_TYPES.values()):
		out["vat"] = month_vat(acc.TAX_TYPES["sales"], companies, project, today) - month_vat(acc.TAX_TYPES["purchase"], companies, project, today)
	return out


@frappe.whitelist()
def dashboard(company: str | None = None, project: str | None = None):
	# Currency is metadata for the scoped documents. Each amount query enforces its own row permissions.
	groups = defaultdict(list)
	for c in frappe.get_all("Company", filters={"name": company} if company else {}, fields=["name", "default_currency"]):
		groups[c.default_currency].append(c.name)
	return [currency_summary(names, currency, project, getdate()) for currency, names in groups.items()]
