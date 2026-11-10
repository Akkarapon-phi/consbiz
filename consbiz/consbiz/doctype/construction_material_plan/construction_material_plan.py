# Copyright (c) 2026, Siricons and contributors
# For license information, please see license.txt

# แผนจัดซื้อวัสดุของแผนงาน 1 ฉบับต่อ Construction Management
# - 1 แถว = วัสดุ (Item) ที่งานหนึ่งต้องใช้ ต้องการภายใน = วันเริ่มงานตามแผนปัจจุบัน - buffer_days (วันปฏิทิน)
#   ต้องสั่งภายใน = ต้องการภายใน - Lead Time
# - แผนงานเลื่อน (บันทึก Construction Management) วันที่ทั้งสองเลื่อนตาม (refresh_dates)
# - สถานะการสั่งไม่ผูกกับเอกสารทีละแถว แต่เทียบปริมาณรวมต่อ (โครงการ + Item) ในหน่วยสต็อก (get_supply)
#   ขอแล้ว = Material Request (ซื้อเอง: Purchase / ผู้ว่าจ้างจัดหา: Customer Provided) ที่ไม่ยกเลิก รวมฉบับร่าง
#   สั่งซื้อแล้ว = Purchase Order, รับแล้ว = Purchase Receipt / Purchase Invoice (อัปเดตสต็อก) / Stock Entry (Material Receipt)
#   โครงการของเอกสาร = custom_project ของ MR หรือ project ของหัว/รายการ หรือรายการที่อ้าง MR ของโครงการนั้น
#   แล้วตัดยอดให้แถวที่ต้องการก่อนก่อน (allocate) MR จะสร้างจากแผนหรือจากหน้า MR เอง สั่งเป็นล็อตใหญ่ก็ได้
#   ต้องตรงกับ allocate_materials ใน public/js/construction_management/schedule.js
# - สร้าง Material Request เฉพาะส่วนที่ยังขาดของแถวที่ถึงกำหนดสั่งภายใน N วัน รวม 1 บรรทัดต่อ Item
#   Item ที่เป็น Customer Provided แยกเป็น MR ประเภท Customer Provided (ลูกค้า = ลูกค้าของแผนงาน)
# - แถวที่ติ๊กผู้ว่าจ้างจัดหา (employer_supplied) เก็บ Item คู่ของ Item ที่เลือก (consbiz/employer_supplied.py)
#   ยอดของซื้อเองกับผู้ว่าจ้างจัดหาจึงแยกกันตาม Item โดยไม่ต้องแก้ get_supply / allocate

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, cint, flt, getdate, nowdate

from consbiz.consbiz.doctype.daily_report.daily_report import get_leaf_tasks
from consbiz.employer_supplied import base_item, employer_item

MATERIAL_PLAN = "Construction Material Plan"


class ConstructionMaterialPlan(Document):
	def validate(self):
		tasks = get_leaf_tasks(self.construction_management)
		for row in self.items:
			task = tasks.get((row.wbs or "").strip())
			if not task:
				frappe.throw(
					_("แถว {0}: ไม่พบงานย่อย WBS {1} ใน {2}").format(row.idx, row.wbs, self.construction_management)
				)
			if flt(row.qty) <= 0:
				frappe.throw(_("แถว {0} ({1}): จำนวนต้องมากกว่า 0").format(row.idx, row.item_code))
			row.task, row.wbs, row.item_name = task.name, task.wbs, task.item_name
			set_dates(row, task.start_date, self.buffer_days)
		self.set_employer_items()

	def set_employer_items(self):
		"""ติ๊กผู้ว่าจ้างจัดหา = ใช้ Item คู่, เอาติ๊กออกจากแถวเดิม = กลับเป็น Item หลัก
		ช่องติ๊กตามประเภทของ Item เสมอ (แถวใหม่ที่เลือก Item คู่มาเลยจึงเป็นผู้ว่าจ้างจัดหา)"""
		before = self.get_doc_before_save()
		was_supplied = {row.name: row.employer_supplied for row in before.items} if before else {}
		for row in self.items:
			if row.employer_supplied:
				row.item_code = employer_item(row.item_code)
			elif was_supplied.get(row.name):
				row.item_code = base_item(row.item_code)
			row.employer_supplied = frappe.db.get_value("Item", row.item_code, "is_customer_provided_item") or 0


def set_dates(row, start_date, buffer_days):
	row.required_by = add_days(start_date, -cint(buffer_days)) if start_date else None
	row.order_by = add_days(row.required_by, -cint(row.lead_time_days)) if row.required_by else None


def refresh_dates(construction_management):
	"""เลื่อนวันที่ต้องการ/ต้องสั่งตามวันเริ่มงานปัจจุบัน (เรียกจาก Construction Management.on_update)"""
	if not frappe.db.exists(MATERIAL_PLAN, construction_management):
		return
	plan = frappe.get_doc(MATERIAL_PLAN, construction_management)
	starts = {task.name: task.start_date for task in get_leaf_tasks(construction_management).values()}
	for row in plan.items:
		before = (str(row.required_by or ""), str(row.order_by or ""))
		set_dates(row, starts.get(row.task), plan.buffer_days)
		if (str(row.required_by or ""), str(row.order_by or "")) != before:
			row.db_update()


# ---------- ยอดที่ขอ/สั่ง/รับแล้วของโครงการ ----------

STAGES = ("requested", "ordered", "received")
SOURCES = ("purchase", "customer")
# ปริมาณที่ถือว่าครบ (กันเศษทศนิยม)
EPSILON = 1e-6


def empty_supply():
	return {source: {"requested": 0.0, "draft": 0.0, "ordered": 0.0, "received": 0.0} for source in SOURCES}


def get_supply(project, item_codes):
	"""{item_code: {purchase|customer: {requested, draft, ordered, received}, total: {requested, ordered, received}}}
	หน่วยสต็อก แต่ละขั้นนับรวมขั้นที่ตามมา (สั่งซื้อตรงโดยไม่มี MR ก็นับว่าขอแล้ว)"""
	item_codes = sorted({code for code in item_codes if code})
	result = {code: empty_supply() for code in item_codes}
	if not project or not item_codes:
		return {code: with_totals(supply) for code, supply in result.items()}

	mr = frappe.qb.DocType("Material Request")
	mri = frappe.qb.DocType("Material Request Item")
	requests = (
		frappe.qb.from_(mri)
		.join(mr)
		.on(mri.parent == mr.name)
		.select(mr.name, mr.material_request_type, mr.docstatus, mr.status, mri.item_code, mri.stock_qty, mri.ordered_qty)
		.where(
			(mr.docstatus < 2)
			& mr.material_request_type.isin(("Purchase", "Customer Provided"))
			& ((mr.custom_project == project) | (mri.project == project))
			& mri.item_code.isin(item_codes)
		)
		.run(as_dict=True)
	)
	customer_requests = set()
	project_requests = set()
	for row in requests:
		source = "customer" if row.material_request_type == "Customer Provided" else "purchase"
		project_requests.add(row.name)
		if source == "customer":
			customer_requests.add(row.name)
		# MR ที่หยุด (Stopped) นับเท่าที่สั่ง/รับไปแล้ว
		qty = flt(row.ordered_qty) if row.status == "Stopped" else flt(row.stock_qty)
		supply = result[row.item_code][source]
		supply["requested"] += qty
		if row.docstatus == 0:
			supply["draft"] += qty

	def linked(parent, child):
		condition = (parent.project == project) | (child.project == project)
		if project_requests:
			condition = condition | child.material_request.isin(list(project_requests))
		return condition

	for doctype, child_doctype, extra in (
		("Purchase Order", "Purchase Order Item", None),
		("Purchase Receipt", "Purchase Receipt Item", None),
		("Purchase Invoice", "Purchase Invoice Item", "update_stock"),
	):
		parent = frappe.qb.DocType(doctype)
		child = frappe.qb.DocType(child_doctype)
		query = (
			frappe.qb.from_(child)
			.join(parent)
			.on(child.parent == parent.name)
			.select(child.item_code, child.stock_qty)
			.where((parent.docstatus == 1) & child.item_code.isin(item_codes) & linked(parent, child))
		)
		if extra:
			query = query.where(parent[extra] == 1)
		stage = "ordered" if doctype == "Purchase Order" else "received"
		for row in query.run(as_dict=True):
			result[row.item_code]["purchase"][stage] += flt(row.stock_qty)

	# รับของเข้า (Material Receipt): ของผู้ว่าจ้างจัดหา = อ้าง MR แบบ Customer Provided หรือ Item เป็น Customer Provided
	se = frappe.qb.DocType("Stock Entry")
	sed = frappe.qb.DocType("Stock Entry Detail")
	receipts = (
		frappe.qb.from_(sed)
		.join(se)
		.on(sed.parent == se.name)
		.select(sed.item_code, sed.transfer_qty, sed.material_request)
		.where(
			(se.docstatus == 1)
			& (se.purpose == "Material Receipt")
			& sed.item_code.isin(item_codes)
			& linked(se, sed)
		)
		.run(as_dict=True)
	)
	provided = set(
		frappe.get_all("Item", filters={"name": ("in", item_codes), "is_customer_provided_item": 1}, pluck="name")
	)
	for row in receipts:
		customer = row.material_request in customer_requests or row.item_code in provided
		result[row.item_code]["customer" if customer else "purchase"]["received"] += flt(row.transfer_qty)

	return {code: with_totals(supply) for code, supply in result.items()}


def with_totals(supply):
	"""ขั้นหลังนับรวมในขั้นก่อน: ขอแล้ว >= สั่งซื้อแล้ว >= รับแล้ว (ผู้ว่าจ้างจัดหาไม่มีขั้นสั่งซื้อ = เท่าที่ขอ)"""
	purchase, customer = supply["purchase"], supply["customer"]
	purchase["ordered"] = max(purchase["ordered"], purchase["received"])
	purchase["requested"] = max(purchase["requested"], purchase["ordered"])
	customer["requested"] = max(customer["requested"], customer["received"])
	customer["ordered"] = customer["requested"]
	supply["total"] = {stage: purchase[stage] + customer[stage] for stage in STAGES}
	return supply


def conversion_factors(rows):
	"""{(item_code, uom): ตัวคูณเป็นหน่วยสต็อก} ไม่มีหน่วย/หน่วยสต็อก/ไม่พบ = 1"""
	codes = {row.get("item_code") for row in rows if row.get("item_code")}
	if not codes:
		return {}
	stock_uom = dict(frappe.get_all("Item", filters={"name": ("in", list(codes))}, fields=["name", "stock_uom"], as_list=True))
	factors = {
		(r.parent, r.uom): flt(r.conversion_factor)
		for r in frappe.get_all(
			"UOM Conversion Detail",
			filters={"parenttype": "Item", "parent": ("in", list(codes))},
			fields=["parent", "uom", "conversion_factor"],
		)
	}
	result = {}
	for row in rows:
		key = (row.get("item_code"), row.get("uom"))
		uom = row.get("uom")
		result[key] = 1.0 if not uom or uom == stock_uom.get(key[0]) else factors.get(key) or 1.0
	return result


def allocate(rows, supply):
	"""ตัดยอดของแต่ละขั้นให้แถวที่ต้องการก่อนก่อน (required_by ว่าง = ท้ายสุด, เท่ากัน = ตามลำดับแถว)
	rows: [{key, item_code, stock_qty, required_by}] คืน {key: {requested, ordered, received, state}} หน่วยสต็อก
	state: received / ordered / requested (ขอครบ) / partial (ขอแล้วบางส่วน) / none"""
	result = {}
	by_item = {}
	for index, row in enumerate(rows):
		by_item.setdefault(row["item_code"], []).append((index, row))
	for item_code, items in by_item.items():
		items.sort(key=lambda pair: (str(pair[1].get("required_by") or "9999-12-31"), pair[0]))
		left = dict((supply.get(item_code) or with_totals(empty_supply()))["total"])
		for _index, row in items:
			need = flt(row["stock_qty"])
			covered = {}
			for stage in STAGES:
				covered[stage] = min(need, max(left[stage], 0))
				left[stage] -= covered[stage]
			covered["state"] = state_of(need, covered)
			result[row["key"]] = covered
	return result


def state_of(need, covered):
	for stage in ("received", "ordered", "requested"):
		if covered[stage] >= need - EPSILON:
			return stage
	return "partial" if covered["requested"] > EPSILON else "none"


def plan_coverage(plan, rows=None):
	"""สถานะของทุกแถวในแผน {row.name: {..., stock_qty, shortfall, factor}} คิดจากวันที่ required_by ที่เก็บไว้"""
	rows = rows if rows is not None else plan.items
	factors = conversion_factors([row.as_dict() for row in rows])
	project = plan.project or frappe.db.get_value("Construction Management", plan.construction_management, "project")
	supply = get_supply(project, [row.item_code for row in rows])
	lines = []
	for row in rows:
		factor = factors.get((row.item_code, row.uom), 1.0)
		lines.append(
			{"key": row.name, "item_code": row.item_code, "stock_qty": flt(row.qty) * factor, "required_by": row.required_by, "factor": factor}
		)
	coverage = allocate(lines, supply)
	for line in lines:
		cov = coverage[line["key"]]
		cov.update(stock_qty=line["stock_qty"], factor=line["factor"], shortfall=max(line["stock_qty"] - cov["requested"], 0))
	return coverage, supply


def is_done(coverage):
	return coverage["state"] in ("requested", "ordered", "received")


# ---------- สร้าง Material Request ----------


def set_item_project(doc, method=None):
	"""doc_events Material Request.validate: รายการที่ยังไม่ระบุโครงการ ใช้ custom_project ของหัวเอกสาร"""
	project = doc.get("custom_project")
	if not project:
		return
	for row in doc.items:
		if not row.project:
			row.project = project


def shortfall_lines(plan, include):
	"""ส่วนที่ยังขาดของแถวที่ include(row) เป็นจริง รวมตาม Item
	[{item_code, stock_qty, required_by (เร็วสุด), rows}]"""
	coverage, _supply = plan_coverage(plan)
	lines = {}
	for row in plan.items:
		shortfall = coverage[row.name]["shortfall"]
		if shortfall <= EPSILON or not include(row):
			continue
		line = lines.setdefault(row.item_code, {"item_code": row.item_code, "stock_qty": 0.0, "required_by": row.required_by, "rows": []})
		line["stock_qty"] += shortfall
		line["required_by"] = min(getdate(line["required_by"]), getdate(row.required_by))
		line["rows"].append(row)
	return list(lines.values())


def due_lines(plan, days):
	"""ส่วนที่ยังขาดของแถวที่ต้องสั่งภายใน days วันนับจากวันนี้"""
	limit = getdate(add_days(nowdate(), cint(days)))
	return shortfall_lines(plan, lambda row: row.order_by and getdate(row.order_by) <= limit)


def selected_lines(plan, row_names):
	"""ส่วนที่ยังขาดของแถวที่ผู้ใช้ติ๊กเลือก แถวของแผนอื่นไม่นับ"""
	names = set(row_names)
	return shortfall_lines(plan, lambda row: row.name in names and row.required_by)


def clear_missing_user_links(doc):
	"""ล้างช่อง Link ที่ค่าเริ่มต้นเป็นผู้ใช้ปัจจุบัน (__user) แต่ไม่มีเอกสารปลายทาง
	เช่น Custom Field "Request By" ของ Material Request ลิงก์ไป Signature ซึ่งตั้งชื่อตามผู้ใช้
	ผู้ใช้ที่ยังไม่มี Signature (เช่น Administrator) จะบันทึกไม่ผ่าน "Could not find Request By" """
	for df in doc.meta.get_link_fields():
		if df.default == "__user" and doc.get(df.fieldname) and not frappe.db.exists(df.options, doc.get(df.fieldname)):
			doc.set(df.fieldname, None)


def item_info(codes):
	return {
		r.name: r
		for r in frappe.get_all(
			"Item", filters={"name": ("in", list(codes))}, fields=["name", "stock_uom", "is_customer_provided_item"]
		)
	}


def customer_of(plan):
	"""ลูกค้าของ MR แบบ Customer Provided = ลูกค้าของแผนงาน"""
	return frappe.db.get_value("Construction Management", plan.construction_management, "customer")


def build_material_requests(plan, lines):
	"""MR ฉบับร่าง: ซื้อเอง (Purchase) 1 ฉบับ และผู้ว่าจ้างจัดหา (Customer Provided) 1 ฉบับ ตามประเภทของ Item"""
	items = item_info([line["item_code"] for line in lines])
	groups = {}
	for line in lines:
		item = items.get(line["item_code"]) or frappe._dict(stock_uom=None, is_customer_provided_item=0)
		groups.setdefault("Customer Provided" if item.is_customer_provided_item else "Purchase", []).append((line, item))

	from consbiz.site_stock import project_warehouse

	# ไม่ได้ตั้งคลังในแผน ใช้คลังของโครงการ
	warehouse = plan.warehouse or project_warehouse(plan.project)
	requests = []
	for request_type in ("Purchase", "Customer Provided"):
		if request_type not in groups:
			continue
		request = frappe.new_doc("Material Request")
		clear_missing_user_links(request)
		request.material_request_type = request_type
		request.company = plan.company
		request.transaction_date = nowdate()
		request.custom_project = plan.project
		if request_type == "Customer Provided":
			request.customer = customer_of(plan)
			if not request.customer:
				frappe.throw(
					_("วัสดุที่ผู้ว่าจ้างจัดหา (Customer Provided) ต้องมีลูกค้าใน {0}").format(plan.construction_management)
				)
		if warehouse:
			request.set_warehouse = warehouse
		dates = []
		for line, item in groups[request_type]:
			# ของที่ต้องการก่อนวันนี้ ให้เร็วที่สุดเท่าที่ระบบยอม
			schedule_date = max(getdate(line["required_by"]), getdate(nowdate()))
			dates.append(schedule_date)
			request.append(
				"items",
				{
					"item_code": line["item_code"],
					"qty": flt(line["stock_qty"], 6),
					"uom": item.stock_uom,
					"conversion_factor": 1,
					"schedule_date": schedule_date,
					"warehouse": warehouse,
					"project": plan.project,
					"description": ", ".join(f"{row.wbs} {row.item_name}" for row in line["rows"]),
				},
			)
		request.schedule_date = min(dates)
		requests.append(request)
	return requests


@frappe.whitelist(methods=["POST"])
def make_material_request(name, days=14):
	"""สร้าง Material Request ฉบับร่างเฉพาะส่วนที่ยังขาดของวัสดุที่ถึงกำหนดสั่ง คืนรายชื่อ MR ที่สร้าง
	แถวที่รวมไว้เก็บเลข MR ล่าสุดไว้อ้างอิง (สถานะคิดจากปริมาณ ไม่ได้ใช้ช่องนี้)"""
	plan = frappe.get_doc(MATERIAL_PLAN, name)
	plan.check_permission("write")
	lines = due_lines(plan, days)
	if not lines:
		frappe.throw(_("ไม่มีวัสดุที่ต้องสั่งเพิ่มภายใน {0} วัน").format(cint(days)))
	return create_requests(plan, lines)


def create_requests(plan, lines):
	"""บันทึก MR ฉบับร่าง และเก็บเลข MR ล่าสุดไว้ที่แถวของแผน"""
	names = []
	for request in build_material_requests(plan, lines):
		request.insert()
		names.append(request.name)
		link_request_rows(request, lines)
	return names


def link_request_rows(request, lines):
	"""เก็บเลข MR ล่าสุดไว้ที่แถวของแผน (เฉพาะรายการที่อยู่ใน MR นั้นจริง)"""
	codes = {row.item_code for row in request.items}
	for line in lines:
		if line["item_code"] in codes:
			for row in line["rows"]:
				row.db_set("material_request", request.name)


def requests_for_rows(plan, row_names):
	"""MR ที่ยังไม่บันทึกของแถวที่เลือก (หมวดทรัพยากรเปิดเป็นฟอร์มให้ผู้ใช้ตรวจแล้วกดบันทึกเอง) คืน (requests, lines)"""
	lines = selected_lines(plan, row_names)
	if not lines:
		frappe.throw(_("รายการที่เลือกขอครบแล้ว"))
	return build_material_requests(plan, lines), lines



@frappe.whitelist()
def get_coverage(name):
	"""สถานะของแถวในฟอร์มแผนวัสดุ {row.name: {requested, ordered, received, state, shortfall}} หน่วยของแถว"""
	plan = frappe.get_doc(MATERIAL_PLAN, name)
	plan.check_permission("read")
	coverage, _supply = plan_coverage(plan)
	result = {}
	for row_name, cov in coverage.items():
		factor = cov["factor"] or 1
		result[row_name] = {
			**{key: flt(cov[key] / factor, 6) for key in ("requested", "ordered", "received", "shortfall")},
			"state": cov["state"],
		}
	return result
