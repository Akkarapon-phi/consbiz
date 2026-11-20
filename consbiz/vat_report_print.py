"""Standalone print preview for the ConsBiz sales and purchase VAT reports."""

from collections import defaultdict
from decimal import Decimal

import frappe
from frappe import _
from frappe.utils import cint, getdate

from consbiz import accounting_app, contract_terms

TITLES = {"sales": "รายงานภาษีขาย", "purchase": "รายงานภาษีซื้อ"}
MONTHS = (
	"มกราคม",
	"กุมภาพันธ์",
	"มีนาคม",
	"เมษายน",
	"พฤษภาคม",
	"มิถุนายน",
	"กรกฎาคม",
	"สิงหาคม",
	"กันยายน",
	"ตุลาคม",
	"พฤศจิกายน",
	"ธันวาคม",
)
ADDRESS_FIELDS = ("address_line1", "address_line2", "city", "county", "state", "pincode")
CENT = Decimal("0.01")


@frappe.whitelist(methods=["GET", "POST"])
def render_vat_report(key, year, month, company=None, company_address=None):
	"""Render the same permitted rows as the accounting report, with its branch filter."""
	if key not in TITLES:
		frappe.throw(_("ไม่รองรับรายงานนี้"), frappe.PermissionError)
	_report, rows, _totals = accounting_app.run_report(key, year, month, company, company_address)
	fields = ["company_name"]
	if frappe.get_meta("Company").has_field("custom_company"):
		fields.append("custom_company")
	company_names = {r.company_name for r in rows if r.company_name}
	companies = frappe.get_all(
		"Company", filters={"company_name": ["in", list(company_names)]}, fields=fields
	) if company_names else []
	names = {c.company_name: (c.get("custom_company") or "").strip() or c.company_name for c in companies}
	headers = empty_report_headers(company, company_address, fields) if not rows else ()
	return {"html": render_report(key, cint(year), cint(month), rows, names, empty_headers=headers)}


def branch_code(value):
	value = str(value or "").strip()
	return "00000" if value in ("", "-", "00000") else value


def report_header(operator, tax_id=None, code=None, address=""):
	branch = _("ทุกสาขา")
	if code:
		branch = _("สำนักงานใหญ่") if code == "00000" else _("สาขาที่ {0}").format(code)
	return {
		"operator": operator,
		"tax_id": tax_id,
		"branch": branch,
		"address": " ".join(address.split()),
	}


def empty_report_headers(company, company_address, fields):
	if not frappe.has_permission("Company", "read"):
		return []
	if frappe.get_meta("Company").has_field("custom_company_address"):
		fields = [*fields, "custom_company_address"]
	companies = frappe.get_list(
		"Company",
		filters={"name": company} if company else {},
		fields=["name", "tax_id", *fields],
		order_by="name asc",
		limit_page_length=0,
	)
	headers = []
	for record in companies:
		filters = [
			["Dynamic Link", "link_doctype", "=", "Company"],
			["Dynamic Link", "link_name", "=", record.name],
			["disabled", "=", 0],
		]
		if company_address:
			filters.append(["name", "=", company_address])
		addresses = frappe.get_all(
			"Address",
			filters=filters,
			fields=["branch_code", *ADDRESS_FIELDS],
			order_by="is_your_company_address desc, is_primary_address desc, address_type asc, name asc",
			limit_page_length=1,
		)
		if company_address and not addresses:
			continue
		address = addresses[0] if addresses else None
		headers.append(
			report_header(
				(record.get("custom_company") or "").strip() or record.company_name,
				record.tax_id,
				branch_code(address.branch_code) if address else None,
				" ".join(str(address.get(field) or "") for field in ADDRESS_FIELDS)
				if address else record.get("custom_company_address") or "",
			)
		)
	return headers


def render_report(key, year, month, rows, company_names, *, synthetic=False, empty_headers=()):
	"""Render one report section per company and filing branch."""
	groups = defaultdict(list)
	for row in rows:
		groups[row.get("company_name"), branch_code(row.get("company_branch_code"))].append(row)

	sections = []
	for (company, code), entries in groups.items():
		first = entries[0]
		address = " ".join(str(first.get(f"company_{field}") or "") for field in ADDRESS_FIELDS)
		sections.append(
			{
				**report_header(company_names.get(company) or company, first.get("company_tax_id"), code, address),
				**table_data(entries, key == "sales"),
			}
		)
	if not sections:
		sections = [
			{**header, **table_data([], key == "sales")}
			for header in empty_headers or [report_header(_("ทุกบริษัท"))]
		]

	return frappe.render_template(
		"consbiz/templates/print/vat_report.html",
		{
			"title": TITLES[key],
			"period": f"{MONTHS[month - 1]} {year + 543}",
			"sales": key == "sales",
			"sections": sections,
			"synthetic": synthetic,
			"font_css": contract_terms.font_css("Noto Sans Thai"),
			"sync_fonts": contract_terms.SYNC_FONTS,
		},
	)


def table_data(entries, sales):
	rows = []
	tax_base = tax_amount = Decimal("0")
	rate_bases = defaultdict(Decimal)
	for entry in entries:
		base = Decimal(str(entry.get("tax_base") or 0)).quantize(CENT)
		vat = Decimal(str(entry.get("tax_amount") or 0)).quantize(CENT)
		tax_base += base
		tax_amount += vat
		rate = entry.get("tax_percent")
		rate = Decimal(str(rate)) if rate not in (None, "") else None
		if sales and rate is not None:
			rate_bases[rate] += base
		date = getdate(entry["date"]) if entry.get("date") else None
		rows.append(
			{
				"date": f"{date:%d/%m}/{date.year + 543}" if date else "",
				"invoice": entry.get("name"),
				"party": entry.get("party_name"),
				"tax_id": entry.get("tax_id"),
				"branch": branch_code(entry.get("branch_code")),
				"rate": f"{rate:g}" if rate is not None else "",
				"amounts": [f"{amount:,.2f}" for amount in (base, vat, base + vat)],
			}
		)
	if len(rate_bases) == 1 and all(row["rate"] for row in rows):
		rate_bases.clear()
	return {
		"rows": rows,
		"totals": [f"{amount:,.2f}" for amount in (tax_base, tax_amount, tax_base + tax_amount)],
		"rate_bases": [(f"{rate:g}", f"{base:,.2f}") for rate, base in sorted(rate_bases.items())],
	}
