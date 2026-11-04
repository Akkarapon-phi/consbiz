# โครงสร้างเงินประกันผลงานใหม่ (consbiz/retention.py)
# 1. แถวของ Retention Invoice / Release ย้ายจาก `Retention Items` ไป `Retention Claim Item`
#    (เดิมเก็บชื่อ RR / RP ไว้ใน reference_no หรือ retention_no แบบ Data)
# 2. ยอดรวมของ RR / RP คำนวณใหม่จากรายการ (RR ที่ระบบสร้างจาก Sales Invoice เดิมไม่ได้ใส่ grand_total)
# 3. JE ที่เคยผูกด้วยข้อความ "Retention Payment for <RI>" ผูกเข้าช่อง journal_entry
# 4. ยอดวางบิล / รับแล้ว / คงเหลือ และสถานะของทุกใบคำนวณใหม่

import frappe
from frappe.query_builder import Order
from frappe.query_builder.functions import Sum
from frappe.utils import flt

from consbiz import retention
from consbiz.utils import thai_baht_text

OLD = frappe.qb.DocType("Retention Items")


def execute():
	move_claim_rows()
	set_source_totals()
	link_journal_entries()
	for claim in retention.SOURCE_OF_CLAIM:
		for name in frappe.get_all(claim, filters={"docstatus": ("in", (1, 2))}, pluck="name"):
			retention.update_claim(claim, name, sources=False)
	for source in retention.SIDES:
		for name in frappe.get_all(source, pluck="name"):
			retention.update_source(source, name)


def move_claim_rows():
	has_retention_no = frappe.db.has_column("Retention Items", "retention_no")
	fields = [OLD.name, OLD.parent, OLD.parenttype, OLD.idx, OLD.reference_no, OLD.description, OLD.amount]
	fields += [OLD.sales_invoice_no, OLD.purchase_invoice_no, OLD.posting_date, OLD.due_date]
	if has_retention_no:
		fields.append(OLD.retention_no)

	for claim, source in retention.SOURCE_OF_CLAIM.items():
		rows = (
			frappe.qb.from_(OLD).select(*fields).where(OLD.parenttype == claim).orderby(OLD.parent, OLD.idx)
		).run(as_dict=True)
		for row in rows:
			candidates = [row.reference_no, row.get("retention_no")]
			ref = next((c for c in candidates if c and frappe.db.exists(source, c)), None)
			if not ref:
				frappe.log_error(
					f"{claim} {row.parent} แถว {row.idx}: ไม่พบ {source} จาก {candidates}",
					"restructure_retention",
				)
				continue
			details = retention.source_details(source, ref)
			frappe.get_doc(
				{
					"doctype": "Retention Claim Item",
					"parent": row.parent,
					"parenttype": claim,
					"parentfield": "retention_items",
					"idx": row.idx,
					"retention_doctype": source,
					"retention_reference": ref,
					"invoice_no": row.sales_invoice_no or row.purchase_invoice_no or details.invoice_no,
					"description": row.description,
					"posting_date": row.posting_date or details.posting_date,
					"due_date": row.due_date or details.due_date,
					"retention_amount": details.grand_total,
					"outstanding_amount": row.amount,
					"amount": row.amount,
				}
			).db_insert()
			frappe.qb.from_(OLD).delete().where(OLD.name == row.name).run()


def set_source_totals():
	for source in retention.SIDES:
		table = frappe.qb.DocType(source)
		totals = (
			frappe.qb.from_(OLD)
			.select(OLD.parent, Sum(OLD.amount))
			.where(OLD.parenttype == source)
			.groupby(OLD.parent)
		).run()
		for name, total in totals:
			total = flt(total, 2)
			(
				frappe.qb.update(table)
				.set(table.grand_total, total)
				.set(table.in_words, thai_baht_text(total))
				.where(table.name == name)
			).run()


def link_journal_entries():
	account = frappe.qb.DocType("Journal Entry Account")
	je = frappe.qb.DocType("Journal Entry")
	for claim in retention.SOURCE_OF_CLAIM:
		for name in frappe.get_all(claim, filters={"journal_entry": ("is", "not set")}, pluck="name"):
			found = (
				frappe.qb.from_(account)
				.join(je)
				.on(account.parent == je.name)
				.select(je.name)
				.where(account.user_remark.like(f"%Retention Payment for {name}%"))
				.where(je.docstatus < 2)
				.orderby(je.docstatus, order=Order.desc)
				.limit(1)
			).run(pluck=True)
			if found:
				frappe.db.set_value(claim, name, "journal_entry", found[0], update_modified=False)
