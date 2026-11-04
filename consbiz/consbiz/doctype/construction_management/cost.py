# Copyright (c) 2026, Siricons and contributors
# For license information, please see license.txt

# Cost Control แบบไม่กรอกเพิ่ม: งบ / ผูกพัน / ใช้จริง แยกตามหมวดต้นทุน (Cost Category) ต่อโครงการ
# แสดงในตาราง "ต้นทุนตามหมวด" ของ Tab การเงิน (Finance.vue) เฉพาะผู้ที่เห็นงบต้นทุน (permlevel 1)
# - หมวดของรายการ: Item Group ของบรรทัด (custom_cost_category ของกลุ่ม หรือกลุ่มแม่ที่ใกล้สุด)
#   เอกสารที่ไม่มี Item (Journal Entry, Expense Claim ฯลฯ) ใช้หมวดของบัญชี (หรือบัญชีแม่) ไม่พบ = ไม่ระบุหมวด
# - ใช้จริง = GL Entry บัญชีค่าใช้จ่ายที่ผูก Project (ยอดรวมเท่ากับ AC ของ EVM) แยกหมวดตามบรรทัดของเอกสารนั้น
#   วัสดุที่เข้าสต็อกนับเป็นต้นทุนตอนเบิก (Stock Entry ที่ใส่ Project) เหมือน EVM
# - ผูกพัน = Purchase Order ที่ Submit แล้วและยังไม่ปิด ส่วนที่ยังไม่ตั้งหนี้ (Purchase Invoice)
# - งบ = ตาราง cost_budgets ของ CM ปุ่ม "เติมงบวัสดุจากแผน" คำนวณจากแผนวัสดุ x ราคาซื้อล่าสุด

import frappe
from frappe import _
from frappe.utils import flt, getdate

from consbiz.consbiz.doctype.construction_management.construction_management import actual_progress_at

# เอกสารที่มีบรรทัดสินค้า: (ตารางบรรทัด, ช่องมูลค่า)
ITEM_TABLES = {
	"Purchase Invoice": ("Purchase Invoice Item", "base_net_amount"),
	"Purchase Receipt": ("Purchase Receipt Item", "base_net_amount"),
	"Stock Entry": ("Stock Entry Detail", "amount"),
}
# ใช้งบเกินความคืบหน้างานเกินกี่ % ถึงเตือน
WARN_MARGIN = 10


def category_resolver(doctype, parent_field):
	"""{ชื่อ Item Group/Account: หมวด} ไม่ได้ตั้งหมวดเองใช้หมวดของกลุ่มแม่ที่ใกล้สุด"""
	rows = {
		r.name: r
		for r in frappe.get_all(doctype, fields=["name", f"{parent_field} as parent", "custom_cost_category as category"])
	}
	memo = {}

	def resolve(name, depth=0):
		if not name or name not in rows or depth > 50:
			return None
		if name not in memo:
			row = rows[name]
			memo[name] = row.category or resolve(row.parent, depth + 1)
		return memo[name]

	return resolve


def gl_costs(doc, day):
	"""[(voucher_type, voucher_no, account, ยอด)] บัญชีค่าใช้จ่ายที่ผูก Project ถึงวัน day (เงื่อนไขเดียวกับ evm.actual_cost)"""
	if not doc.project:
		return []
	gl = frappe.qb.DocType("GL Entry")
	account = frappe.qb.DocType("Account")
	query = (
		frappe.qb.from_(gl)
		.join(account)
		.on(gl.account == account.name)
		.select(gl.voucher_type, gl.voucher_no, gl.account, frappe.query_builder.functions.Sum(gl.debit - gl.credit))
		.where(
			(gl.project == doc.project)
			& (gl.is_cancelled == 0)
			& (account.root_type == "Expense")
			& (gl.posting_date <= getdate(day))
		)
		.groupby(gl.voucher_type, gl.voucher_no, gl.account)
	)
	if doc.company:
		query = query.where(gl.company == doc.company)
	return [tuple(row) for row in query.run()]


def item_lines(entries, project):
	"""{(voucher_no, expense_account): [(item_group, มูลค่า)]} บรรทัดของเอกสารใน entries ที่เป็นของโครงการนี้ (หรือไม่ระบุ)"""
	result = {}
	for voucher_type, (table, amount_field) in ITEM_TABLES.items():
		names = list({e[1] for e in entries if e[0] == voucher_type})
		if not names:
			continue
		for line in frappe.get_all(
			table,
			filters={"parenttype": voucher_type, "parent": ("in", names)},
			fields=["parent", "expense_account", "item_group", "project", f"{amount_field} as amount"],
		):
			if line.project and line.project != project:
				continue
			result.setdefault((line.parent, line.expense_account), []).append((line.item_group, flt(line.amount)))
	return result


def split_actual(entries, lines, group_category, account_category):
	"""{หมวด (None = ไม่ระบุ): ยอด} แบ่งยอด GL ตามสัดส่วนมูลค่าบรรทัด บรรทัดไม่มีหมวดใช้หมวดของบัญชี"""
	result = {}

	def add(category, value):
		result[category] = result.get(category, 0) + value

	for _voucher_type, voucher_no, account, value in entries:
		value = flt(value)
		matched = lines.get((voucher_no, account)) or []
		total = sum(abs(amount) for _group, amount in matched)
		if not total:
			add(account_category(account), value)
			continue
		for group, amount in matched:
			add(group_category(group) or account_category(account), value * abs(amount) / total)
	return result


def committed_rows(doc, day):
	"""[(item_group, ยอดที่ยังไม่ตั้งหนี้)] บรรทัด PO ของโครงการที่ Submit แล้วและยังไม่ปิด"""
	if not doc.project:
		return []
	po = frappe.qb.DocType("Purchase Order")
	item = frappe.qb.DocType("Purchase Order Item")
	query = (
		frappe.qb.from_(item)
		.join(po)
		.on(item.parent == po.name)
		.select(item.item_group, item.base_net_amount, item.amount, item.billed_amt)
		.where(
			(item.project == doc.project)
			& (po.docstatus == 1)
			& (po.status.notin(["Closed", "Cancelled"]))
			& (po.transaction_date <= getdate(day))
		)
	)
	if doc.company:
		query = query.where(po.company == doc.company)
	result = []
	for group, base_amount, amount, billed in query.run():
		share = max(0, 1 - flt(billed) / flt(amount)) if flt(amount) else 0
		if share:
			result.append((group, flt(base_amount) * share))
	return result


def cost_control(doc, day):
	"""ตารางต้นทุนตามหมวด ณ วัน day
	{progress, rows: [{category, label, budget, committed, actual, remaining, used, tone}], total}"""
	day = getdate(day)
	group_category = category_resolver("Item Group", "parent_item_group")
	account_category = category_resolver("Account", "parent_account")

	entries = gl_costs(doc, day)
	actual = split_actual(entries, item_lines(entries, doc.project), group_category, account_category)
	committed = {}
	for group, value in committed_rows(doc, day):
		category = group_category(group)
		committed[category] = committed.get(category, 0) + value
	budget = {}
	for row in doc.get("cost_budgets") or []:
		budget[row.cost_category] = budget.get(row.cost_category, 0) + flt(row.amount)

	progress = flt(actual_progress_at(doc, day)[1])
	categories = frappe.get_all("Cost Category", order_by="sequence asc, name asc", pluck="name")
	keys = categories + [k for k in {*actual, *committed, *budget} if k and k not in categories]
	if any(abs(flt(d.get(None))) >= 0.005 for d in (actual, committed)):
		keys.append(None)

	rows = [make_row(key, budget.get(key, 0), committed.get(key, 0), actual.get(key, 0), progress) for key in keys]
	total = make_row(
		"total",
		sum(r["budget"] for r in rows),
		sum(r["committed"] for r in rows),
		sum(r["actual"] for r in rows),
		progress,
	)
	return {"progress": progress, "rows": rows, "total": total}


def make_row(category, budget, committed, actual, progress):
	used = (actual + committed) / budget * 100 if budget else None
	if not budget:
		tone = "gray"
	elif actual + committed > budget:
		tone = "red"
	elif actual / budget * 100 > progress + WARN_MARGIN:
		tone = "orange"
	else:
		tone = "green"
	return {
		"category": category,
		"label": _("ไม่ระบุหมวด") if category is None else _("รวม") if category == "total" else category,
		"budget": budget,
		"committed": committed,
		"actual": actual,
		"remaining": budget - actual - committed if budget else None,
		"used": used,
		"actual_pct": actual / budget * 100 if budget else None,
		"tone": tone,
	}


def item_rate(item):
	"""ราคาต่อหน่วยสต็อก: ราคาซื้อล่าสุด > ราคาประเมินสต็อก > ราคามาตรฐาน"""
	return flt(item.last_purchase_rate) or flt(item.valuation_rate) or flt(item.standard_rate)


def material_budget(rows, items, factors, group_category):
	"""{หมวด: งบ} จากแถวแผนวัสดุ (ข้ามของลูกค้าจัดหา) และรายการ Item ที่ไม่มีราคา"""
	result, missing = {}, []
	for row in rows:
		item = items.get(row.get("item_code"))
		if not item or item.is_customer_provided_item:
			continue
		rate = item_rate(item)
		if not rate:
			missing.append(item.name)
			continue
		qty = flt(row.get("qty")) * factors.get((row.get("item_code"), row.get("uom")), 1)
		category = group_category(item.item_group)
		result[category] = result.get(category, 0) + qty * rate
	return result, sorted(set(missing))


@frappe.whitelist()
def suggest_material_budget(name):
	"""งบวัสดุแนะนำต่อหมวดจาก Construction Material Plan ของ CM (ปุ่ม เติมงบวัสดุจากแผน)"""
	from consbiz.consbiz.doctype.construction_material_plan.construction_material_plan import conversion_factors

	doc = frappe.get_doc("Construction Management", name)
	doc.check_permission("read")
	if not doc.has_permlevel_access_to("cost_budgets"):
		frappe.throw(_("ไม่มีสิทธิ์ดูงบต้นทุน"), frappe.PermissionError)
	if not frappe.db.exists("Construction Material Plan", name):
		return {"rows": [], "unassigned": 0, "missing_rate": []}
	rows = frappe.get_all(
		"Construction Material Plan Item",
		filters={"parent": name, "parenttype": "Construction Material Plan"},
		fields=["item_code", "qty", "uom"],
	)
	codes = list({r.item_code for r in rows if r.item_code})
	items = {
		r.name: r
		for r in frappe.get_all(
			"Item",
			filters={"name": ("in", codes or [""])},
			fields=[
				"name",
				"item_group",
				"is_customer_provided_item",
				"last_purchase_rate",
				"valuation_rate",
				"standard_rate",
			],
		)
	}
	budget, missing = material_budget(rows, items, conversion_factors(rows), category_resolver("Item Group", "parent_item_group"))
	return {
		"rows": [{"cost_category": k, "amount": v} for k, v in budget.items() if k],
		"unassigned": budget.get(None, 0),
		"missing_rate": missing,
	}
