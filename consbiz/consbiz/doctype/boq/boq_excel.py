# Copyright (c) 2026, Siricons and contributors
# For license information, please see license.txt

"""นำเข้า/ส่งออกตาราง BOQ เป็น Excel ตามแบบฟอร์ม BOQ ของบริษัท

ไฟล์มี 2 ส่วน: หัวเอกสาร (บริษัท โครงการ ลูกค้า สถานที่ เลขที่ วันที่) และตารางรายการ
หัวตารางมี 2 ชั้น (ค่าวัสดุ/ค่าแรง แยกเป็น ราคาต่อหน่วย กับ จำนวนเงิน)
ตอนนำเข้าจะหาแถวหัวตารางจากชื่อคอลัมน์ แล้วอ่านหัวเอกสารจากแถวที่อยู่ก่อนหน้า
"""

import base64
import binascii
import re
import zipfile
from difflib import SequenceMatcher
from io import BytesIO

import frappe
from frappe import _
from frappe.utils import cstr, flt, getdate, strip_html

from consbiz.consbiz.doctype.boq.boq import calculate_row, round_down_amount

# (fieldname, หัวคอลัมน์, ความกว้าง, ชนิด) ตามลำดับในไฟล์
# หัวคอลัมน์แบบ tuple คือ (หัวชั้นบน, หัวชั้นล่าง) คอลัมน์ติดกันที่หัวชั้นบนเหมือนกันจะรวมเซลล์
# ชนิด: text, qty, money, amount (amount คำนวณใหม่ตอนนำเข้า ไม่อ่านจากไฟล์)
COLUMNS = (
	("wbs", "ลำดับที่\n(WBS)", 8.8, "text"),
	("item_name", "รายการ", 38.7, "text"),
	("quantity", "จำนวน", 8.2, "qty"),
	("uom", "หน่วย", 8.8, "text"),
	("material_rate", ("ค่าวัสดุ", "ราคาต่อหน่วย"), 10.7, "money"),
	("material_amount", ("ค่าวัสดุ", "จำนวนเงิน"), 10.7, "amount"),
	("labour_rate", ("ค่าแรง", "ราคาต่อหน่วย"), 10.7, "money"),
	("labour_amount", ("ค่าแรง", "จำนวนเงิน"), 10.7, "amount"),
	("total_amount", "รวมค่าวัสดุและค่าแรง", 16.7, "amount"),
	# คอลัมน์สำหรับระบบ อยู่นอกพื้นที่พิมพ์
	("description", "หมายเหตุ", 30, "text"),
	("item_code", "รหัสรายการ", 12, "text"),
	("item_group", "กลุ่มงาน", 16, "text"),
	("combined_rate", "ไม่แยกค่าวัสดุ/ค่าแรง", 12, "check"),
)
PRINT_COLUMNS = 9  # พิมพ์เฉพาะคอลัมน์ A-I ตามแบบฟอร์ม
IMPORT_FIELDS = tuple(fieldname for fieldname, _label, _width, kind in COLUMNS if kind != "amount")
# ชื่อหัวคอลัมน์อื่นที่รับตอนนำเข้า (รวมแม่แบบรุ่นก่อน)
COLUMN_ALIASES = {
	"wbs": ("WBS", "ลำดับที่", "ลำดับ"),
	"quantity": ("ปริมาณ",),
	"material_rate": ("ค่าวัสดุ/หน่วย",),
	"labour_rate": ("ค่าแรง/หน่วย",),
}
# คอลัมน์ที่อ่านตอนนำเข้าอย่างเดียว สำหรับไฟล์ที่ไม่แยกค่าวัสดุ/ค่าแรง (ดู combine_rates)
COMBINED_COLUMNS = {
	"unit_rate": ("ราคาต่อหน่วย", "ราคา/หน่วย", "หน่วยละ", "ราคารวมต่อหน่วย", "Unit Rate", "Rate"),
	"line_amount": ("รวมค่าวัสดุและค่าแรง", "จำนวนเงิน", "รวมเป็นเงิน", "ราคารวม", "Amount", "Total Amount"),
}
NUMBER_FIELDS = ("quantity", "material_rate", "labour_rate")
RATE_FIELDS = ("material_rate", "labour_rate")
# ค่าที่ดึงจาก BOQ Item เมื่อช่องในไฟล์ว่าง
ITEM_DEFAULTS = ("item_name", "uom", "item_group", "material_rate", "labour_rate")
# หัวเอกสาร: fieldname ของ BOQ -> ป้ายในไฟล์
INFO_FIELDS = {
	"company": ("บริษัท", "Company"),
	"customer": ("ลูกค้า", "Customer"),
	"project": ("โครงการ", "Project"),
	"location": ("สถานที่", "ที่อยู่", "Location"),
	"date": ("วันที่", "Date"),
}
# ป้ายอื่นในหัวเอกสาร กันไม่ให้ถูกอ่านเป็นค่าเมื่อช่องค่าว่าง
OTHER_LABELS = ("เลขที่", "เลขที่ BOQ")
TOTAL_LABEL = "รวมทั้งสิ้น"
ITEM_SHEET = "รายการมาตรฐาน"
BLANK_ROWS = {"template": 50, "export": 20}
MAX_FILE_SIZE = 10 * 1024 * 1024

FONT = "Cordia New"
COLOR_HEADER = "#DCEAF7"
COLOR_SYSTEM = "#F2F2F2"  # หัวคอลัมน์สำหรับระบบ (นอกพื้นที่พิมพ์)
# Accounting ไม่มีสัญลักษณ์เงิน (0 แสดง "-") ช่องที่ยังคำนวณไม่ได้สูตรจะคืน "" จึงว่าง
NUMBER_FORMAT = '_-* #,##0.00_-;-* #,##0.00_-;_-* "-"??_-;_-@_-'


# ---------------------------------------------------------------- นำเข้า


@frappe.whitelist()
def import_boq_items(filename: str, content: str) -> dict:
	"""อ่านไฟล์ Excel/CSV ที่ส่งมาเป็น base64 แล้วคืน {"info": หัวเอกสาร, "items": [...], "warnings": [...]}

	อ่านในหน่วยความจำอย่างเดียว ไม่สร้าง File และไม่เขียนลงดิสก์ (ไฟล์มีราคาทุน)
	"""
	frappe.has_permission("BOQ", "write", throw=True)
	return parse_boq_rows(read_spreadsheet(filename, content))


def read_spreadsheet(filename: str, content: str) -> list[list]:
	"""แถวของชีตแรก (ชีตที่ active) จากไฟล์ .xlsx/.csv ที่ส่งมาเป็น base64 อ่านในหน่วยความจำ
	ใช้ร่วมกับการนำเข้าแผนงาน (schedule_excel.py)"""
	try:
		data = base64.b64decode(content, validate=True)
	except binascii.Error, ValueError:
		frappe.throw(_("อ่านไฟล์ไม่ได้"))
	if len(data) > MAX_FILE_SIZE:
		frappe.throw(_("ไฟล์ใหญ่เกิน {0} MB").format(MAX_FILE_SIZE // (1024 * 1024)))

	extension = cstr(filename).rsplit(".", 1)[-1].lower()
	if extension == "xlsx":
		from frappe.utils.xlsxutils import read_xlsx_file_from_attached_file

		try:
			return read_xlsx_file_from_attached_file(fcontent=data)
		except zipfile.BadZipFile, KeyError, ValueError:
			frappe.throw(_("ไฟล์ {0} ไม่ใช่ Excel (.xlsx) หรือไฟล์เสียหาย").format(filename))
	elif extension == "csv":
		from frappe.utils.csvutils import read_csv_content

		return read_csv_content(data)
	frappe.throw(_("รองรับเฉพาะไฟล์ .xlsx หรือ .csv"))


def parse_boq_rows(rows: list[list]) -> dict:
	"""อ่านตารางจากไฟล์ ยังไม่เติมค่าจาก BOQ Item (รอผู้ใช้ยืนยันการจับคู่ แล้วเรียก apply_boq_matches)

	แต่ละรายการคือ {"row_no", "row": ค่าจากไฟล์, "missing": ช่องที่ไฟล์ว่าง, "match", "item_code", "suggestions", "note"}
	"""
	header_index, columns, data_start = find_header(rows)
	info, warnings = parse_info(rows[:header_index])
	matcher = ItemMatcher()
	uoms = UomMatcher()

	items = []
	combined_rows = 0
	amount_checks = []  # (แถว, จำนวน x ราคา, จำนวนเงินในไฟล์)
	for row_no, cells in enumerate(rows[data_start:], start=data_start + 1):
		if any(is_label(cell, (TOTAL_LABEL, "Grand Total")) for cell in cells):
			break

		values = {}
		for index, fieldname in columns.items():
			value = cells[index] if index < len(cells) else None
			if cstr(value).strip() != "":
				values[fieldname] = value if fieldname in NUMBER_FIELDS else cstr(value).strip()
		if not values:
			continue

		if values.get("uom"):
			if uom := uoms.match(values["uom"]):
				values["uom"] = uom
			else:  # ไม่มีสิทธิ์สร้าง UOM
				warnings.append(_("แถว {0}: ไม่พบหน่วย {1} จึงเว้นว่างไว้").format(row_no, values.pop("uom")))

		amount = flt(values.get("line_amount"))
		source = combine_rates(values)
		if source:
			combined_rows += 1
		missing = [fieldname for fieldname in ITEM_DEFAULTS if fieldname not in values]
		for fieldname in NUMBER_FIELDS:
			values[fieldname] = flt(values.get(fieldname))
		# ราคาที่คิดจากจำนวนเงินตรงกับไฟล์อยู่แล้ว / ไม่มีราคา (รอเติมจาก BOQ Item) เทียบไม่ได้
		if amount and source != "amount" and any(values[f] for f in RATE_FIELDS):
			raw = values["quantity"] * (values["material_rate"] + values["labour_rate"])
			amount_checks.append((row_no, raw, amount))
		items.append({"row_no": row_no, "row": values, "missing": missing, **matcher.match(values)})

	if combined_rows:
		warnings.append(
			_('{0} แถวไม่แยกค่าวัสดุและค่าแรง ระบบใส่ราคารวมที่ค่าวัสดุและติ๊ก "ราคารวมวัสดุและค่าแรง" ไว้').format(
				combined_rows
			)
		)
	warnings.extend(uoms.warnings())

	round_down, mismatched = check_amounts(amount_checks)
	if round_down:
		info["round_down_total"] = 1
		warnings.append(_('ไฟล์ตัดเศษสตางค์ของยอดรวมแต่ละแถว ระบบติ๊ก "ปัดเศษสตางค์ยอดรวมลง" ให้'))
	if mismatched:
		rows_text = ", ".join(str(row_no) for row_no in mismatched[:10]) + (
			" ..." if len(mismatched) > 10 else ""
		)
		warnings.append(
			_("แถว {0}: จำนวนเงินในไฟล์ไม่ตรงกับ จำนวน x ราคาต่อหน่วย ระบบใช้ยอดที่คำนวณใหม่").format(rows_text)
		)
	return {"info": info, "items": items, "warnings": warnings}


def check_amounts(checks: list[tuple]) -> tuple[bool, list[int]]:
	"""เทียบจำนวนเงินในไฟล์กับ จำนวน x ราคา: ไฟล์ตัดสตางค์ยอดรวม (ROUNDDOWN) หรือไม่ และแถวที่ไม่ตรง
	ถือว่าตัดสตางค์เมื่อแบบตัดสตางค์ตรงมากกว่าแบบไม่ปัด (แถวที่ยอดลงตัวเป็นบาทตรงทั้งสองแบบ ไม่ชี้ขาด)
	"""

	def same(a, b):
		return abs(a - b) < 0.005

	exact = [same(raw, amount) for _row, raw, amount in checks]
	floored = [same(round_down_amount(raw), amount) for _row, raw, amount in checks]
	round_down = sum(floored) > sum(exact)
	matched = floored if round_down else exact
	return round_down, [row_no for (row_no, _raw, _amount), ok in zip(checks, matched, strict=True) if not ok]


def combine_rates(values: dict) -> str | None:
	"""แถวที่ไม่มีค่าวัสดุ/ค่าแรง แต่มีราคาต่อหน่วยหรือจำนวนเงินรวม = ราคารวม: ใส่ราคาที่ค่าวัสดุและติ๊ก combined_rate
	มีแต่จำนวนเงิน (เช่น งานเหมา) ราคาต่อหน่วย = จำนวนเงิน ÷ จำนวน ถ้าไม่มีจำนวนถือเป็น 1 หน่วย
	คืนที่มาของราคาเมื่อแปลงจากราคารวม: "rate" (ราคาต่อหน่วย) หรือ "amount" (จำนวนเงิน)
	ไม่ได้แปลง (มีค่าวัสดุ/ค่าแรงแยก หรือแถวที่ติ๊กมาในไฟล์แล้ว) คืน None
	"""
	unit_rate = flt(values.pop("unit_rate", None))
	amount = flt(values.pop("line_amount", None))
	values["combined_rate"] = int(is_checked(values.get("combined_rate")))
	if any(flt(values.get(f)) for f in RATE_FIELDS) or not (unit_rate or amount):
		return None

	source = "rate" if unit_rate else "amount"
	if not unit_rate:
		if not flt(values.get("quantity")):
			values["quantity"] = 1
		unit_rate = amount / flt(values["quantity"])
	values["material_rate"] = unit_rate
	values["combined_rate"] = 1
	return source


def is_checked(value) -> bool:
	if isinstance(value, int | float):
		return bool(value)
	return cstr(value).strip().lower() not in ("", "0", "no", "false", "ไม่")


@frappe.whitelist()
def apply_boq_matches(items: list[dict] | str) -> list[dict]:
	"""สร้างแถว boq_details จากผลจับคู่ที่ผู้ใช้ยืนยัน: item_code ที่เลือก หรือ create=1 เพื่อสร้าง BOQ Item ใหม่

	ค่าใน Excel เป็นหลัก ค่าจาก BOQ Item (ราคามาตรฐาน) เติมเฉพาะช่องที่ไฟล์ว่าง
	"""
	frappe.has_permission("BOQ", "write", throw=True)
	created = {}  # ชื่อเดียวกันหลายแถว สร้าง BOQ Item ครั้งเดียว
	rows = []
	for entry in frappe.parse_json(items):
		row = frappe._dict({k: v for k, v in (entry.get("row") or {}).items() if k in IMPORT_FIELDS})
		if row.uom:
			row.uom = ensure_uom(row.uom)
		code = entry.get("item_code")
		if entry.get("create") and row.item_name:
			key = name_key(row.item_name)
			if key not in created:
				created[key] = create_boq_item(row)
			code = created[key]
		elif code:
			item = frappe.db.get_value("BOQ Item", code, ITEM_DEFAULTS, as_dict=True)
			if not item:
				frappe.throw(_("ไม่พบ BOQ Item {0}").format(code))
			missing = entry.get("missing") or ()
			for fieldname in missing:
				# ราคารวม: ไม่เติมค่าวัสดุ/ค่าแรงแยก ถ้าไฟล์ไม่มีราคาเลยใช้ราคามาตรฐานรวมกัน
				if not (row.combined_rate and fieldname in RATE_FIELDS):
					row[fieldname] = item[fieldname]
			if row.combined_rate and set(RATE_FIELDS) <= set(missing):
				row.material_rate = flt(item.material_rate) + flt(item.labour_rate)

		row.item_code = code or None
		for fieldname in NUMBER_FIELDS:
			row[fieldname] = flt(row.get(fieldname))
		calculate_row(row)
		rows.append(row)
	return rows


def create_boq_item(row) -> str:
	"""ราคาในไฟล์เป็นราคามาตรฐาน ยกเว้นแถวราคารวม (แยกค่าวัสดุ/ค่าแรงไม่ได้) สร้างโดยไม่ใส่ราคา"""
	rates = {} if row.combined_rate else {f: flt(row.get(f)) for f in RATE_FIELDS}
	item = frappe.get_doc(
		{
			"doctype": "BOQ Item",
			"item_name": row.item_name,
			"uom": row.uom,
			"item_group": row.item_group if frappe.db.exists("BOQ Item Group", row.item_group) else None,
			**rates,
		}
	)
	item.insert()  # ตรวจสิทธิ์สร้าง BOQ Item ของผู้ใช้
	return item.name


# ---------------------------------------------------------------- หน่วย

# ชื่อเรียกหน่วยเดียวกัน เทียบด้วย uom_key ตัวแรกที่มีในระบบเป็นหน่วยที่ใช้ (ไทยก่อน)
UOM_ALIASES = (
	("ตร.ม.", "ตารางเมตร", "ม2", "ม.2", "m2", "sq.m", "sqm", "Square Meter"),
	("ลบ.ม.", "ลูกบาศก์เมตร", "ม3", "ม.3", "m3", "cu.m", "cum", "Cubic Meter"),
	("เมตร", "ม.", "m", "Meter", "Metre"),
	("กก.", "กิโลกรัม", "kg", "kgs", "Kilogram"),
	("ตัน", "ton", "tons", "Tonne"),
	("ลิตร", "ล.", "l", "lt", "Litre", "Liter"),
	("เหมา", "ls", "l.s.", "lump sum", "Lot"),
	("ชุด", "set", "sets"),
	("ชิ้น", "pc", "pcs", "piece", "pieces"),
)


def uom_key(name) -> str:
	"""ไม่สนตัวพิมพ์ ช่องว่าง จุด และขีด ("ตร.ม." = "ตรม" = "ตร. ม")"""
	return re.sub(r"[\s.\-_]", "", cstr(name).lower())


class UomMatcher:
	"""หาหน่วยในระบบที่ตรงกับหน่วยในไฟล์: ชื่อตรงกัน (ไม่นับตัวพิมพ์/จุด/ช่องว่าง) หรือเป็นชื่อเรียกอื่นใน UOM_ALIASES
	ไม่พบ: คืนชื่อเดิมไว้สร้างหน่วยใหม่ตอนนำเข้า (ensure_uom) ถ้าผู้ใช้ไม่มีสิทธิ์สร้าง UOM คืน None
	ไม่ใช้ความใกล้เคียงของชื่อ เพราะชื่อหน่วยสั้น "ม." กับ "มม." ต่างกันตัวเดียวแต่คนละหน่วย
	"""

	def __init__(self):
		self.by_key = {}
		for uom in frappe.get_all("UOM", fields=["name", "enabled"], order_by="enabled desc, name asc"):
			self.by_key.setdefault(uom_key(uom.name), uom.name)
		self.can_create = frappe.has_permission("UOM", "create")
		self.mapped = {}  # ชื่อในไฟล์ -> หน่วยในระบบที่ใช้แทน
		self.new = []

	def match(self, name) -> str | None:
		name = " ".join(cstr(name).split())
		key = uom_key(name)
		if found := self.by_key.get(key):
			if found != name:
				self.mapped.setdefault(name, found)
			return found
		for aliases in UOM_ALIASES:
			if key in {uom_key(alias) for alias in aliases}:
				found = next((self.by_key[uom_key(a)] for a in aliases if uom_key(a) in self.by_key), None)
				if found:
					self.mapped.setdefault(name, found)
					return found
		if not self.can_create:
			return None
		if name not in self.new:
			self.new.append(name)
		return name

	def warnings(self) -> list[str]:
		messages = []
		if self.mapped:
			pairs = ", ".join(f"{src} → {uom}" for src, uom in self.mapped.items())
			messages.append(_("ใช้หน่วยที่มีในระบบแทน: {0}").format(pairs))
		if self.new:
			messages.append(_("หน่วยที่ยังไม่มีในระบบ จะสร้างใหม่ตอนนำเข้า: {0}").format(", ".join(self.new)))
		return messages


def ensure_uom(name) -> str:
	"""สร้าง UOM ที่ยังไม่มี (ชื่อตามที่ UomMatcher คืนไว้) insert ตรวจสิทธิ์สร้าง UOM ของผู้ใช้"""
	name = " ".join(cstr(name).split())
	if existing := frappe.db.exists("UOM", name):
		return existing
	return frappe.get_doc({"doctype": "UOM", "uom_name": name}).insert().name


# ---------------------------------------------------------------- จับคู่รายการ

SUGGEST_LIMIT = 5
SUGGEST_MIN_SCORE = 0.5
PRESELECT_SCORE = 0.8


def name_key(name) -> str:
	"""ชื่อสำหรับเทียบ: ไม่สนตัวพิมพ์และช่องว่าง ("คอนกรีต 240ksc" = "คอนกรีต  240 KSC")"""
	return "".join(cstr(name).lower().split())


def similarity_key(name) -> str:
	"""ใช้ให้คะแนนความใกล้เคียง: ตัดคำขึ้นต้น "งาน" ที่แทบทุกรายการมี ไม่ให้ชื่อดูใกล้กันเกินจริง"""
	key = name_key(name)
	return key[3:] if key.startswith("งาน") and len(key) > 3 else key


def name_numbers(name) -> set[str]:
	return set(re.findall(r"\d+(?:\.\d+)?", cstr(name)))


class ItemMatcher:
	"""จับคู่แถวจาก Excel กับ BOQ Item

	exact: รหัสในไฟล์มีในระบบ หรือชื่อตรงกันพอดี (ไม่นับตัวพิมพ์/ช่องว่าง) และมีรายการเดียว
	suggest: มีชื่อใกล้เคียงให้เลือก เลือกตัวแรกไว้ให้เมื่อคะแนนสูงและตัวเลขในชื่อตรงกัน
	  (ชื่อต่างแค่ตัวเลข เช่น 240 ksc กับ 280 ksc เป็นคนละรายการ จึงไม่เลือกให้)
	none: ไม่พบ / heading: หัวข้องาน (ไม่มีรหัส จำนวน และราคา) ไม่ต้องจับคู่
	"""

	def __init__(self):
		self.items = frappe.get_all("BOQ Item", fields=["name", "item_name", "uom"])
		self.codes = {item.name for item in self.items}
		self.by_key = {}
		for item in self.items:
			item.key = name_key(item.item_name)
			item.similarity_key = similarity_key(item.item_name)
			item.numbers = name_numbers(item.item_name)
			self.by_key.setdefault(item.key, []).append(item)

	def match(self, values: dict) -> dict:
		result = {"match": "none", "item_code": None, "suggestions": [], "note": None}
		code = values.pop("item_code", None)
		if code in self.codes:
			return {**result, "match": "exact", "item_code": code}
		if code:
			result["note"] = _("รหัส {0} ไม่มีในระบบ").format(code)

		name = values.get("item_name")
		if not code and not any(values.get(f) for f in NUMBER_FIELDS):
			return {**result, "match": "heading"}
		if not name:
			return result

		same = self.by_key.get(name_key(name), [])
		if len(same) == 1:
			return {**result, "match": "exact", "item_code": same[0].name}

		suggestions = self.suggest(name)
		if suggestions:
			result["match"] = "suggest"
			result["suggestions"] = suggestions
			top = suggestions[0]
			runner_up = suggestions[1]["score"] if len(suggestions) > 1 else 0
			if top["score"] >= PRESELECT_SCORE and not top["number_conflict"] and top["score"] > runner_up:
				result["item_code"] = top["item_code"]
		return result

	def suggest(self, name: str) -> list[dict]:
		key, numbers = similarity_key(name), name_numbers(name)
		scored = []
		for item in self.items:
			if not item.similarity_key:
				continue
			contains = key in item.similarity_key or item.similarity_key in key
			matcher = SequenceMatcher(None, key, item.similarity_key)
			if not contains and matcher.quick_ratio() < SUGGEST_MIN_SCORE:
				continue
			score = matcher.ratio()
			if contains:  # ชื่อหนึ่งอยู่ในอีกชื่อ เช่น "เทคอนกรีต" กับ "งานเทคอนกรีตพื้น"
				score = max(score, 0.75)
			conflict = bool(numbers and item.numbers and numbers != item.numbers)
			if conflict:
				score *= 0.8
			if score >= SUGGEST_MIN_SCORE:
				scored.append(
					{
						"item_code": item.name,
						"item_name": item.item_name,
						"uom": item.uom,
						"score": round(score, 2),
						"number_conflict": conflict,
					}
				)
		scored.sort(key=lambda s: -s["score"])
		return scored[:SUGGEST_LIMIT]


def find_header(rows: list[list]) -> tuple[int, dict[int, str], int]:
	"""แถวแรกที่มีคอลัมน์ รายการ หรือ รหัสรายการ คือแถวหัวตาราง
	ถ้าแถวถัดไปเป็นหัวชั้นล่าง (เช่น ราคาต่อหน่วย) จะอ่านรวมกัน และข้อมูลเริ่มหลังแถวนั้น
	คืน (index แถวหัวตาราง, {index คอลัมน์: fieldname}, index แถวแรกของข้อมูล)
	"""
	names = get_column_names()
	for index, cells in enumerate(rows):
		columns = map_columns(cells, None, names)
		if not {"item_code", "item_name"} & set(columns.values()):
			continue
		if index + 1 < len(rows):
			with_sub = map_columns(cells, rows[index + 1], names)
			if len(with_sub) > len(columns):
				return index, with_sub, index + 2
		return index, columns, index + 1
	frappe.throw(_("ไม่พบแถวหัวตารางที่มีคอลัมน์ รายการ หรือ รหัสรายการ"))


def map_columns(top: list, sub: list | None, names: dict[str, str]) -> dict[int, str]:
	"""หัวชั้นบนที่รวมเซลล์ไว้จะอ่านได้แค่ช่องแรก จึงใช้หัวชั้นบนล่าสุดทางซ้ายกับหัวชั้นล่าง"""
	columns, group = {}, ""
	for i in range(max(len(top), len(sub or []))):
		head = top[i] if i < len(top) else None
		subhead = sub[i] if sub and i < len(sub) else None
		if cstr(head).strip():
			group = head
		candidates = [f"{group} {subhead}"] if cstr(subhead).strip() else []
		candidates.append(head)
		for candidate in candidates:
			if (key := normalize(candidate)) in names:
				columns[i] = names[key]
				break
	return columns


def get_column_names() -> dict[str, str]:
	"""ชื่อหัวคอลัมน์ที่รับได้: หัวในแม่แบบ, ชื่อเดิม, fieldname, label อังกฤษ และคำแปลของ label"""
	meta = frappe.get_meta("BOQ Item Detail")
	names = {}
	for fieldname, label, _width, kind in COLUMNS:
		if kind == "amount":
			continue
		meta_label = meta.get_label(fieldname)
		label = " ".join(label) if isinstance(label, tuple) else label
		aliases = COLUMN_ALIASES.get(fieldname, ())
		for name in (fieldname, meta_label, _(meta_label), label, _(label), *aliases):
			names[normalize(name)] = fieldname
	for fieldname, aliases in COMBINED_COLUMNS.items():
		for name in aliases:
			names.setdefault(normalize(name), fieldname)
			names.setdefault(normalize(_(name)), fieldname)
	return names


def parse_info(rows: list[list]) -> tuple[dict, list[str]]:
	"""อ่านหัวเอกสาร: ช่องป้าย (เช่น "ลูกค้า :") แล้วค่าอยู่ในช่องถัดไปทางขวาที่ไม่ว่าง"""
	all_labels = [label for labels in INFO_FIELDS.values() for label in labels] + list(OTHER_LABELS)
	info = {}
	for cells in rows:
		for index, cell in enumerate(cells):
			fieldname = next((field for field, labels in INFO_FIELDS.items() if is_label(cell, labels)), None)
			if not fieldname or fieldname in info:
				continue
			value = next((v for v in cells[index + 1 :] if cstr(v).strip() != ""), None)
			if value is not None and not is_label(value, all_labels):
				info[fieldname] = value

	warnings = []
	if info.get("company"):
		company = cstr(info["company"]).strip()
		info["company"] = frappe.db.exists("Company", company) or frappe.db.get_value(
			"Company", {"company_name": company}
		)
		if not info["company"]:
			warnings.append(_("ไม่พบบริษัท {0} ในระบบ จึงไม่ได้ใส่ช่องบริษัท").format(company))
			del info["company"]
	if info.get("customer"):
		customer = cstr(info["customer"]).strip()
		info["customer"] = frappe.db.exists("Customer", customer) or frappe.db.get_value(
			"Customer", {"customer_name": customer}
		)
		if not info["customer"]:
			warnings.append(_("ไม่พบลูกค้า {0} ในระบบ จึงไม่ได้ใส่ช่องลูกค้า").format(customer))
			del info["customer"]
	if info.get("date"):
		try:
			info["date"] = getdate(info["date"])
		except Exception:
			warnings.append(_("อ่านวันที่ {0} ไม่ได้").format(info["date"]))
			del info["date"]
	for fieldname in ("project", "location"):
		if fieldname in info:
			info[fieldname] = cstr(info[fieldname]).strip()
	return info, warnings


def normalize(value) -> str:
	"""ตัดช่องว่าง/ขึ้นบรรทัดใหม่ซ้ำ และ ":" ท้ายป้าย เช่น "โครงการ :" -> "โครงการ" """
	return " ".join(cstr(value).split()).rstrip(":").strip().lower()


def is_label(value, labels) -> bool:
	key = normalize(value)
	return bool(key) and any(key in (normalize(label), normalize(_(label))) for label in labels)


# ---------------------------------------------------------------- ส่งออก


@frappe.whitelist()
def export_boq_items(boq: str | None = None):
	"""ดาวน์โหลด BOQ เป็น Excel ถ้าไม่ส่ง boq จะได้แม่แบบเปล่า"""
	from frappe.desk.utils import provide_binary_file

	if boq:
		doc = frappe.get_doc("BOQ", boq)
		doc.check_permission("read")
	else:
		frappe.has_permission("BOQ", "read", throw=True)
		doc = None

	filename = doc.name if doc else "BOQ Template"
	provide_binary_file(filename, "xlsx", build_workbook(doc))


def build_workbook(doc=None) -> bytes:
	import xlsxwriter

	output = BytesIO()
	wb = xlsxwriter.Workbook(output, {"in_memory": True})
	fmt = make_formats(wb)
	ws = wb.add_worksheet("BOQ")
	for col, (_f, _l, width, _k) in enumerate(COLUMNS):
		ws.set_column(col, col, width)

	write_document_header(ws, fmt, doc)
	header_row = 4
	write_table_header(ws, fmt, header_row)

	rows = doc.boq_details if doc else []
	round_down = bool(doc and doc.round_down_total)
	first_row = header_row + 2
	write_item_sheet(wb, fmt)
	for i, row in enumerate(rows):
		write_item_row(ws, fmt, first_row + i, row, round_down)
	blank_rows = BLANK_ROWS["export" if doc else "template"]
	for i in range(blank_rows):
		write_item_row(ws, fmt, first_row + len(rows) + i, round_down=round_down)
	last_row = first_row + len(rows) + blank_rows - 1

	total_row = last_row + 1
	write_total_row(ws, fmt, total_row, first_row, last_row, rows)

	ws.freeze_panes(first_row, 0)
	ws.set_landscape()
	ws.set_paper(9)  # A4
	ws.fit_to_pages(1, 0)
	ws.center_horizontally()
	ws.set_margins(left=0.25, right=0.25, top=0.5, bottom=0.5)
	ws.print_area(0, 0, total_row, PRINT_COLUMNS - 1)
	ws.repeat_rows(header_row, header_row + 1)
	ws.set_footer("&C&P / &N")
	ws.activate()

	wb.close()
	return output.getvalue()


def write_document_header(ws, fmt, doc):
	company = doc.company if doc else frappe.defaults.get_user_default("Company")
	customer = ""
	if doc and doc.customer:
		customer = frappe.db.get_value("Customer", doc.customer, "customer_name") or doc.customer

	ws.set_row(0, 23.4)
	ws.write(0, 0, "BILL OF QUANTITIES", fmt["title"])
	ws.write(1, 0, _("ใบแสดงปริมาณงานและราคา (BOQ)"), fmt["subtitle"])
	ws.write(1, 5, _("บริษัท"), fmt["label_right"])
	ws.merge_range(1, 6, 1, 8, company or "", fmt["value"])

	ws.write(2, 0, _("โครงการ") + " :", fmt["label"])
	ws.merge_range(2, 1, 2, 2, doc.project if doc else "", fmt["value"])
	ws.write(3, 0, _("สถานที่") + " :", fmt["label"])
	ws.merge_range(3, 1, 3, 2, doc.location if doc else "", fmt["input"])

	ws.write(2, 3, _("ลูกค้า") + " :", fmt["label"])
	ws.merge_range(2, 4, 3, 6, customer, fmt["input_wrap"])

	ws.write(2, 7, _("เลขที่") + " :", fmt["label"])
	ws.write(2, 8, doc.name if doc and not doc.is_new() else "", fmt["value"])
	ws.write(3, 7, _("วันที่") + " :", fmt["label"])
	if doc and doc.date:
		ws.write_datetime(3, 8, getdate(doc.date), fmt["input_date"])
	else:
		ws.write_blank(3, 8, None, fmt["input_date"])


def write_table_header(ws, fmt, row):
	"""หัวตาราง 2 แถว: คอลัมน์เดี่ยวรวมเซลล์แนวตั้ง กลุ่ม (ค่าวัสดุ/ค่าแรง) รวมเซลล์แนวนอน"""
	ws.set_row(row, 21)
	ws.set_row(row + 1, 21)
	col = 0
	while col < len(COLUMNS):
		label = COLUMNS[col][1]
		cell_fmt = fmt["header"] if col < PRINT_COLUMNS else fmt["header_system"]
		if isinstance(label, tuple):
			span = 1
			while col + span < len(COLUMNS) and isinstance(COLUMNS[col + span][1], tuple):
				if COLUMNS[col + span][1][0] != label[0]:
					break
				span += 1
			ws.merge_range(row, col, row, col + span - 1, _(label[0]), cell_fmt)
			for i in range(span):
				ws.write(row + 1, col + i, _(COLUMNS[col + i][1][1]), cell_fmt)
			col += span
		else:
			ws.merge_range(row, col, row + 1, col, _(label), cell_fmt)
			col += 1


def write_item_row(ws, fmt, r, row=None, round_down=False):
	"""row=None คือแถวว่างเตรียมกรอก (มีแต่สูตรยอดเงิน) ชื่อรายการพิมพ์อิสระ ระบบจับคู่กับ BOQ Item ตอนนำเข้า
	round_down: ช่องรวมค่าวัสดุและค่าแรงใช้ ROUNDDOWN ตัดสตางค์ (ตาม round_down_total ของ BOQ)"""
	excel_row = r + 1
	ref = lambda name: f"${col_letter(column_index(name))}{excel_row}"  # noqa: E731
	# ช่องที่ยังคำนวณไม่ได้ (ไม่มีจำนวนหรือราคา) คืน "" ไม่ให้ขึ้น #VALUE!
	total = f"N({ref('material_amount')})+N({ref('labour_amount')})"
	if round_down:
		total = f"ROUNDDOWN({total},0)"
	amount_formula = {
		"material_amount": (
			f"=IF(AND(ISNUMBER({ref('quantity')}),ISNUMBER({ref('material_rate')})),"
			f'{ref("quantity")}*{ref("material_rate")},"")'
		),
		"labour_amount": (
			f"=IF(AND(ISNUMBER({ref('quantity')}),ISNUMBER({ref('labour_rate')})),"
			f'{ref("quantity")}*{ref("labour_rate")},"")'
		),
		"total_amount": (f'=IF(AND({ref("material_amount")}="",{ref("labour_amount")}=""),"",{total})'),
	}
	# แถวหัวข้องาน (ไม่มีจำนวนและราคา) ใช้ตัวหนาและเว้นช่องตัวเลข
	is_heading = row and not (flt(row.quantity) or flt(row.material_rate) or flt(row.labour_rate))

	for col, (fieldname, _label, _width, kind) in enumerate(COLUMNS):
		if fieldname in ("item_name", "description"):
			cell_fmt = fmt["text_wrap_bold" if is_heading else "text_wrap"]
		elif fieldname in ("wbs", "uom", "item_code", "combined_rate"):
			cell_fmt = fmt["center_bold" if is_heading else "center"]
		else:
			cell_fmt = fmt[kind]

		if kind == "amount":
			value = "" if not row or is_heading else flt(row.get(fieldname))
			ws.write_formula(r, col, amount_formula[fieldname], cell_fmt, value)
		elif row:
			value = row.get(fieldname)
			if fieldname == "description":
				value = strip_html(cstr(value)).strip()
			if kind in ("qty", "money"):
				value = None if is_heading else flt(value)
			elif kind == "check":
				value = 1 if value else None
			ws.write(r, col, value if value not in (None, "") else None, cell_fmt)
		else:
			ws.write_blank(r, col, None, cell_fmt)


def write_total_row(ws, fmt, r, first_row, last_row, rows):
	ws.set_row(r, 21)
	ws.merge_range(r, 0, r, column_index("material_rate"), _(TOTAL_LABEL), fmt["total_label"])
	for col in range(column_index("material_amount"), PRINT_COLUMNS):
		fieldname = COLUMNS[col][0]
		if COLUMNS[col][3] != "amount":
			ws.write_blank(r, col, None, fmt["total"])
			continue
		letter = col_letter(col)
		ws.write_formula(
			r,
			col,
			f"=SUM({letter}{first_row + 1}:{letter}{last_row + 1})",
			fmt["total"],
			sum(flt(row.get(fieldname)) for row in rows),
		)


def write_item_sheet(wb, fmt):
	"""แผ่นงานรายการมาตรฐานจาก BOQ Item ไว้ดูอ้างอิงชื่อและราคามาตรฐานตอนกรอก"""
	if not frappe.has_permission("BOQ Item", "read"):
		return
	items = frappe.get_all(
		"BOQ Item",
		fields=["name", "item_name", "uom", "item_group", "material_rate", "labour_rate"],
		order_by="name asc",
	)
	ws = wb.add_worksheet(ITEM_SHEET)
	headers = (
		(_("รหัสรายการ"), 12),
		(_("รายการ"), 38.7),
		(_("หน่วย"), 8.8),
		(_("กลุ่มงาน"), 16),
		(_("ค่าวัสดุต่อหน่วย"), 12),
		(_("ค่าแรงต่อหน่วย"), 12),
	)
	for col, (label, width) in enumerate(headers):
		ws.set_column(col, col, width)
		ws.write(0, col, label, fmt["header"])
	for r, item in enumerate(items, start=1):
		ws.write(r, 0, item.name, fmt["center"])
		ws.write(r, 1, cstr(item.item_name).strip(), fmt["text_wrap"])
		ws.write(r, 2, item.uom, fmt["center"])
		ws.write(r, 3, item.item_group, fmt["text"])
		ws.write(r, 4, flt(item.material_rate), fmt["money"])
		ws.write(r, 5, flt(item.labour_rate), fmt["money"])
	ws.freeze_panes(1, 0)


def make_formats(wb) -> dict:
	base = {"font_name": FONT, "font_size": 14, "valign": "vcenter"}
	cell = {**base, "border": 1}

	def add(style=base, **props):
		return wb.add_format({**style, **props})

	return {
		"title": add(bold=True, font_size=16),
		"subtitle": add(),
		"label": add(bold=True),
		"label_right": add(bold=True, align="right"),
		"value": add(),
		"input": add(bottom=1),
		"input_wrap": add(bottom=1, valign="top", text_wrap=True),
		"input_date": add(bottom=1, num_format="dd/mm/yyyy", align="left"),
		"header": add(cell, bold=True, bg_color=COLOR_HEADER, align="center", text_wrap=True),
		"header_system": add(cell, bold=True, bg_color=COLOR_SYSTEM, align="center", text_wrap=True),
		"text": add(cell),
		"text_wrap": add(cell, text_wrap=True),
		"text_wrap_bold": add(cell, text_wrap=True, bold=True),
		"center": add(cell, align="center"),
		"center_bold": add(cell, align="center", bold=True),
		"qty": add(cell, num_format=NUMBER_FORMAT),
		"money": add(cell, num_format=NUMBER_FORMAT),
		"amount": add(cell, num_format=NUMBER_FORMAT),
		"total_label": add(cell, bold=True, align="center", bg_color=COLOR_HEADER),
		"total": add(cell, bold=True, num_format=NUMBER_FORMAT, bg_color=COLOR_HEADER),
	}


def column_index(fieldname: str) -> int:
	return next(i for i, column in enumerate(COLUMNS) if column[0] == fieldname)


def col_letter(col: int) -> str:
	from xlsxwriter.utility import xl_col_to_name

	return xl_col_to_name(col)
