# สต็อกหน้างาน (ใช้เอกสารสต็อกของ ERPNext เพิ่มเฉพาะส่วนของงานก่อสร้าง)
# - 1 คลังต่อโครงการ: สร้าง Project แล้วสร้างคลัง All Warehouses / โครงการ / <ชื่อคลัง> ให้เอง (custom_project)
#   ชื่อคลังผู้ใช้ตั้งเองในช่อง Project.custom_warehouse_name (ERPNext แก้ชื่อคลังภายหลังไม่ได้ จึงตรวจซ้ำก่อนบันทึก)
#   ฟอร์มรับของ/เบิก/MR/ใบยืมเลือกคลังนี้ให้ (get_project_warehouse) ผู้ใช้ไม่ต้องเลือกคลัง
# - วัสดุผู้ว่าจ้างจัดหาแยกด้วย Item คู่ (employer_supplied.py มูลค่า 0) ไม่ต้องแยกคลัง อยู่คลังเดียวกับของบริษัทได้
#   คลังวัสดุผู้ว่าจ้างแยก (Warehouse.custom_is_owner_warehouse) มีหรือไม่ก็ได้ ถ้ามี รับได้เฉพาะวัสดุผู้ว่าจ้างจัดหา
#   (validate_warehouses: Stock Entry / Purchase Receipt / Purchase Invoice ตัดสต็อก)
# - เบิก (Stock Entry: Material Issue) Item หลัก: แยกแถวตัด Item คู่ (คลังเดียวกันก่อน แล้วคลังผู้ว่าจ้างของโครงการ)
#   ตามลำดับใน Project.custom_issue_priority (ค่าเริ่มต้นผู้ว่าจ้างก่อน) ทำตอนบันทึกร่าง ผู้ใช้เห็นแถวที่แยกก่อน Submit
#   แถวที่ผ่านแล้ว custom_employer_checked = 1 ไม่แยกซ้ำ (ฟอร์มรีเซ็ตเมื่อแก้ Item / จำนวน / คลัง)
# - WBS ของแถว (custom_wbs) ต้องเป็นงานย่อยของแผนงานของโครงการ ชื่องานเก็บใน custom_task_name ไว้ทำรายงาน

import frappe
from frappe import _
from frappe.utils import flt

EMPLOYER_FIRST = "Employer First"
COMPANY_FIRST = "Company First"
# ปริมาณที่ถือว่าหมด (กันเศษทศนิยม)
EPSILON = 1e-9


def owner_warehouses(names):
	names = [name for name in set(names) if name]
	if not names:
		return set()
	return set(frappe.get_all("Warehouse", filters={"name": ("in", names), "custom_is_owner_warehouse": 1}, pluck="name"))


def employer_items(codes):
	codes = [code for code in set(codes) if code]
	if not codes:
		return set()
	return set(frappe.get_all("Item", filters={"name": ("in", codes), "is_customer_provided_item": 1}, pluck="name"))


# ---------- คลังวัสดุผู้ว่าจ้าง ----------


def target_warehouse(doc, row):
	return row.get("t_warehouse") if doc.doctype == "Stock Entry" else row.get("warehouse")


def validate_warehouses(doc, method=None):
	"""doc_events validate: คลังวัสดุผู้ว่าจ้าง (ถ้ามี) รับได้เฉพาะวัสดุผู้ว่าจ้างจัดหา (คลังอื่นรับได้ทั้งสองแบบ)"""
	if doc.doctype == "Purchase Invoice" and not doc.get("update_stock"):
		return
	rows = [row for row in doc.get("items") or [] if row.item_code and target_warehouse(doc, row)]
	owners = owner_warehouses(target_warehouse(doc, row) for row in rows)
	provided = employer_items(row.item_code for row in rows)
	for row in rows:
		warehouse = target_warehouse(doc, row)
		if warehouse in owners and row.item_code not in provided:
			frappe.throw(
				_("แถว {0}: {1} เป็นคลังวัสดุผู้ว่าจ้าง รับได้เฉพาะวัสดุผู้ว่าจ้างจัดหา ({2} เป็นของบริษัท)").format(
					row.idx, frappe.bold(warehouse), frappe.bold(row.item_code)
				)
			)


# ---------- เบิก: ตัดคลังผู้ว่าจ้างก่อน ----------


def split_qty(qty, sources, fallback):
	"""แบ่ง qty ตามลำดับ sources [(key, available)] ส่วนที่เหลือลง fallback
	คืน [(key, qty)] เรียงตาม sources (ไม่รวม key ที่ได้ 0) fallback อยู่ใน sources ได้ (ได้ทั้งส่วนของตัวเองและส่วนที่เหลือ)"""
	parts = {}
	left = flt(qty)
	for key, available in sources:
		take = min(left, max(flt(available), 0))
		if take > EPSILON:
			parts[key] = parts.get(key, 0) + take
			left -= take
	if left > EPSILON:
		parts[fallback] = parts.get(fallback, 0) + left
	order = [key for key, _available in sources]
	if fallback not in order:
		order.append(fallback)
	return [(key, parts[key]) for key in order if key in parts]


def row_project(doc, row):
	return row.get("project") or doc.get("project") or frappe.db.get_value("Warehouse", row.s_warehouse, "custom_project")


def split_employer_stock(doc, method=None):
	"""Stock Entry.before_validate: แถวเบิก Item หลัก แยกส่วนที่ตัดวัสดุผู้ว่าจ้างจัดหาเป็นแถว Item คู่
	(คลังของแถวก่อน แล้วคลังวัสดุผู้ว่าจ้างของโครงการ)"""
	from consbiz.employer_supplied import employer_item

	if doc.purpose != "Material Issue" or doc.docstatus != 0:
		return
	rows = [row for row in doc.items if row.item_code and row.s_warehouse and not row.get("custom_employer_checked")]
	for row in rows:
		row.custom_employer_checked = 1
	provided = employer_items(row.item_code for row in rows)
	owners_of_source = owner_warehouses(row.s_warehouse for row in rows)
	# ยอดที่แถวอื่นในเอกสารนี้ตัดไปแล้ว {(item_code, warehouse): stock_qty}
	used = {}
	for row in doc.items:
		key = (row.item_code, row.s_warehouse)
		used[key] = used.get(key, 0) + flt(row.transfer_qty or flt(row.qty) * flt(row.conversion_factor or 1))

	result = []
	notes = []
	for row in list(doc.items):
		if row not in rows or row.item_code in provided or row.s_warehouse in owners_of_source:
			result.append(row)
			continue
		project = row_project(doc, row)
		owners = [row.s_warehouse] + [wh for wh in project_owner_warehouses(project, doc.company) if wh != row.s_warehouse]
		twin = frappe.db.get_value("Item", {"custom_base_item": row.item_code}, "name")
		if not twin:
			result.append(row)
			continue
		factor = flt(row.conversion_factor) or 1
		stock_qty = flt(row.qty) * factor
		own_key = (row.item_code, row.s_warehouse)
		used[own_key] -= stock_qty
		owner_sources = [((twin, wh), actual_qty(twin, wh) - used.get((twin, wh), 0)) for wh in owners]
		company_source = (own_key, actual_qty(*own_key) - used.get(own_key, 0))
		sources = [company_source, *owner_sources] if issue_priority(project) == COMPANY_FIRST else owner_sources
		parts = split_qty(stock_qty, sources, own_key)
		for key, part in parts:
			used[key] = used.get(key, 0) + part
			if key == own_key:
				row.qty = flt(part / factor, 9)
				row.transfer_qty = part
				result.append(row)
				continue
			employer_row = row.as_dict(no_default_fields=True)
			employer_row.update(
				{
					# ERPNext ให้แถวที่อ้าง MR ต้องเป็น Item เดียวกับใน MR แถว Item คู่จึงไม่อ้าง MR
					"material_request": None,
					"material_request_item": None,
					"serial_and_batch_bundle": None,
					"item_code": key[0],
					"item_name": frappe.db.get_value("Item", key[0], "item_name"),
					"s_warehouse": key[1],
					"qty": flt(part / factor, 9),
					"transfer_qty": part,
					"basic_rate": 0,
					"allow_zero_valuation_rate": 1,
					"custom_employer_checked": 1,
				}
			)
			result.append(employer_row)
			notes.append(_("{0} {1} จาก {2}").format(flt(part / factor, 3), row.uom or row.stock_uom, key[1]))

	if notes:
		doc.set("items", result)
		for index, row in enumerate(doc.items, 1):
			row.idx = index
		frappe.msgprint(
			_("ตัดวัสดุผู้ว่าจ้างจัดหาก่อน: {0}").format(", ".join(notes)), indicator="blue", alert=True
		)


def issue_priority(project):
	return frappe.db.get_value("Project", project, "custom_issue_priority") or EMPLOYER_FIRST


def project_owner_warehouses(project, company):
	if not project:
		return []
	return frappe.get_all(
		"Warehouse",
		filters={"custom_is_owner_warehouse": 1, "custom_project": project, "company": company, "is_group": 0},
		pluck="name",
		order_by="name",
	)


def actual_qty(item_code, warehouse):
	return flt(frappe.db.get_value("Bin", {"item_code": item_code, "warehouse": warehouse}, "actual_qty"))


# ---------- WBS ของแถว ----------


def construction_management_of(project):
	if not project:
		return None
	return frappe.db.get_value(
		"Construction Management", {"project": project, "status": "Active"}, "name"
	) or frappe.db.get_value("Construction Management", {"project": project}, "name")


def validate_wbs(doc, method=None):
	"""Stock Entry / Material Request validate: WBS ต้องเป็นงานย่อยของแผนงานของโครงการ"""
	from consbiz.consbiz.doctype.daily_report.daily_report import get_leaf_tasks

	tasks_of = {}
	for row in doc.items:
		wbs = (row.get("custom_wbs") or "").strip()
		if not wbs:
			row.custom_task_name = None
			continue
		project = row.get("project") or doc.get("project") or doc.get("custom_project")
		cm = construction_management_of(project)
		if not cm:
			frappe.throw(_("แถว {0}: ระบุ WBS ได้เมื่อโครงการมีแผนงาน (Construction Management)").format(row.idx))
		if cm not in tasks_of:
			tasks_of[cm] = get_leaf_tasks(cm)
		task = tasks_of[cm].get(wbs)
		if not task:
			frappe.throw(_("แถว {0}: ไม่พบงานย่อย WBS {1} ใน {2}").format(row.idx, wbs, cm))
		row.custom_wbs, row.custom_task_name = task.wbs, task.item_name


@frappe.whitelist()
def get_wbs_options(project):
	"""ตัวเลือก WBS ของแผนงานของโครงการ (ช่อง custom_wbs ในรายการของ Stock Entry / Material Request)"""
	from consbiz.consbiz.doctype.construction_management.construction_management import get_task_options

	cm = construction_management_of(project)
	return get_task_options(cm) if cm else []


# ---------- คลังของโครงการ ----------

# ชื่อกลุ่มคลังของโครงการที่ใช้ได้ (มีอยู่แล้วใช้ตัวเดิม ไม่มีสร้าง "โครงการ")
PROJECT_GROUPS = ("โครงการ", "Project", "Projects")
# ความยาวชื่อโครงการในชื่อคลัง (ชื่อโครงการราชการยาวมาก)
NAME_LENGTH = 60


def project_warehouse(project):
	"""คลังของโครงการ (คลังที่ไม่ใช่คลังผู้ว่าจ้างก่อน) ไม่มี = None"""
	if not project:
		return None
	rows = frappe.get_all(
		"Warehouse",
		filters={"custom_project": project, "is_group": 0, "disabled": 0},
		fields=["name"],
		order_by="custom_is_owner_warehouse asc, creation asc",
		limit=1,
	)
	return rows[0].name if rows else None


def project_group(company):
	"""กลุ่มคลัง "โครงการ" ใต้คลังรากของบริษัท"""
	existing = frappe.db.get_value(
		"Warehouse", {"company": company, "is_group": 1, "warehouse_name": ("in", PROJECT_GROUPS)}, "name"
	)
	if existing:
		return existing
	root = frappe.db.get_value("Warehouse", {"company": company, "is_group": 1, "parent_warehouse": ("is", "not set")}, "name")
	group = frappe.get_doc(
		{"doctype": "Warehouse", "warehouse_name": PROJECT_GROUPS[0], "company": company, "is_group": 1, "parent_warehouse": root}
	)
	group.flags.ignore_permissions = True
	return group.insert().name


def warehouse_name_of(project, name=None):
	"""ชื่อคลัง (warehouse_name ไม่รวมตัวย่อบริษัท): ที่ผู้ใช้ตั้ง (custom_warehouse_name) ไม่ตั้ง = ชื่อโครงการ"""
	name = (name or project.get("custom_warehouse_name") or "").strip()
	return name or (project.project_name or project.name or "").strip()[:NAME_LENGTH]


def check_warehouse_name(company, name):
	"""ERPNext แก้ชื่อคลังภายหลังไม่ได้ ชื่อต้องไม่ซ้ำกับคลังที่มีอยู่ของบริษัท"""
	if frappe.db.exists("Warehouse", {"company": company, "warehouse_name": name}):
		frappe.throw(_("มีคลังชื่อ {0} อยู่แล้ว ตั้งชื่อคลังของโครงการใหม่").format(frappe.bold(name)))


def validate_project_warehouse_name(doc, method=None):
	"""Project.validate: โครงการใหม่ ตรวจชื่อคลังก่อนบันทึก (ตั้งชื่อเองได้ในช่อง Warehouse Name)"""
	if doc.is_new() and doc.company:
		doc.custom_warehouse_name = warehouse_name_of(doc)
		check_warehouse_name(doc.company, doc.custom_warehouse_name)


def ensure_project_warehouse(project, name=None):
	"""คลังของโครงการ สร้างใหม่ถ้ายังไม่มี (คืนชื่อคลัง ไม่มีบริษัท = None)"""
	existing = project_warehouse(project.name)
	if existing or not project.company:
		return existing
	name = warehouse_name_of(project, name)
	check_warehouse_name(project.company, name)
	warehouse = frappe.get_doc(
		{
			"doctype": "Warehouse",
			"warehouse_name": name,
			"company": project.company,
			"parent_warehouse": project_group(project.company),
			"custom_project": project.name,
		}
	)
	warehouse.flags.ignore_permissions = True
	warehouse.insert()
	if project.get("custom_warehouse_name") != name:
		project.db_set("custom_warehouse_name", name)
	return warehouse.name


def create_project_warehouse(doc, method=None):
	"""Project.after_insert: สร้างคลังของโครงการให้เลย (ทุกโครงการต้องมีอยู่แล้ว)"""
	ensure_project_warehouse(doc)


@frappe.whitelist(methods=["POST"])
def make_project_warehouse(project, warehouse_name=None):
	"""ปุ่มในฟอร์ม Project สำหรับโครงการเดิมที่ยังไม่มีคลัง (ผู้ใช้ตั้งชื่อคลังใน dialog)"""
	doc = frappe.get_doc("Project", project)
	doc.check_permission("write")
	return ensure_project_warehouse(doc, warehouse_name)


@frappe.whitelist()
def get_project_warehouse(project):
	"""คลังของโครงการ สำหรับตั้งค่าในฟอร์มรับของ/เบิก/MR/ใบยืม"""
	frappe.has_permission("Project", "read", project, throw=True)
	return project_warehouse(project)
