# Copyright (c) 2026, Siricons and contributors
# For license information, please see license.txt

"""ส่งออก/นำเข้าแผนงาน (หน้า Gantt) เป็น Excel

ส่งออก: ตารางงานตาม WBS (วันที่ จำนวนวัน งานก่อนหน้า Baseline % จริง) และแถบ Gantt รายสัปดาห์/รายเดือนด้านขวา
  ใช้สูตรให้แก้ใน Excel แล้วค่าอื่นตาม มี 2 แบบ (mode):
  - duration: กรอกวันเริ่ม + จำนวนวัน วันจบ = WORKDAY.INTL (วันหยุดจากชีตวันหยุด) พิมพ์วันจบทับสูตรได้
    จำนวนวันที่ไม่ตรงกับวันเริ่ม-วันจบเป็นสีส้ม
  - dates: กรอกวันเริ่ม + วันจบ จำนวนวัน = NETWORKDAYS.INTL
  นำเข้าใช้วันเริ่ม-วันจบเสมอ จำนวนวันใช้เมื่อวันจบว่าง (ดู apply_import ใน App.vue) จึงอ่านได้ทั้งสองแบบ
  วันที่ของกลุ่ม = MIN/MAX ของงานย่อย แถบ Gantt = conditional formatting จากวันเริ่ม/วันจบ
  วันที่ในไฟล์ไม่เลื่อนตามงานก่อนหน้า (คำนวณตอนนำเข้า)
นำเข้า: อ่านไฟล์แล้วคืนค่าที่อ่านได้ทีละแถว ไม่แก้แผนงาน หน้า Gantt เป็นคนนำค่าไปใส่ (Undo ได้ และเลื่อนงานตาม
งานก่อนหน้าด้วย logic เดียวกับการแก้ในหน้า) แก้ได้เฉพาะ วันเริ่ม วันจบ จำนวนวัน และงานก่อนหน้า ของงานที่มีอยู่แล้ว
"""

import datetime
import re
from io import BytesIO

import frappe
from frappe import _
from frappe.utils import cint, cstr, flt, getdate, nowdate

from consbiz.consbiz.doctype.boq.boq_excel import normalize, read_spreadsheet
from consbiz.consbiz.doctype.construction_management.construction_management import add_working_days

# (fieldname, หัวคอลัมน์, ความกว้าง, ชนิด) ชนิด: text, number, percent, date, int
COLUMNS = (
	("wbs", "WBS", 8, "text"),
	("item_name", "รายการ", 40, "text"),
	("quantity", "ปริมาณ", 10, "number"),
	("uom", "หน่วย", 8, "text"),
	("amount", "มูลค่า", 14, "number"),
	("weight", "น้ำหนัก %", 9, "percent"),
	("start_date", "วันเริ่ม", 11, "date"),
	("end_date", "วันจบ", 11, "date"),
	("duration", "จำนวนวัน", 8, "int"),
	("predecessors", "งานก่อนหน้า", 16, "text"),
	("baseline_start_date", "เริ่ม (Baseline)", 11, "date"),
	("baseline_end_date", "จบ (Baseline)", 11, "date"),
	("progress", "% จริง", 8, "percent"),
)
# คอลัมน์ที่อ่านตอนนำเข้า และชื่อหัวคอลัมน์อื่นที่รับ (เช่น ไฟล์จาก MS Project)
IMPORT_COLUMNS = {
	"wbs": ("WBS", "ลำดับที่", "ลำดับ"),
	"start_date": ("วันเริ่ม", "เริ่ม", "Start", "Start Date"),
	"end_date": ("วันจบ", "จบ", "Finish", "End", "End Date"),
	"duration": ("จำนวนวัน", "Duration", "Duration (Days)"),
	"predecessors": ("งานก่อนหน้า", "Predecessors"),
}
# วว/ดด/ปปปป (คั่นด้วย / - .) หรือ ปปปป-ดด-วว
DATE_PATTERNS = (
	(re.compile(r"^(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})$"), (3, 2, 1)),
	(re.compile(r"^(\d{4})-(\d{1,2})-(\d{1,2})$"), (1, 2, 3)),
)
# ปี พ.ศ. ในไฟล์ (เช่น 15/01/2570) ลบ 543 เป็น ค.ศ.
BUDDHIST_YEAR_FROM = 2400
HEADER_ROW = 4
# แถวซ่อนเหนือหัวตาราง: วันสุดท้ายของแต่ละช่วงเวลา (ใช้ในสูตรของแถบ Gantt)
PERIOD_END_ROW = HEADER_ROW - 1
# คอลัมน์ที่กรอกแล้วนำเข้ากลับได้ (หัวคอลัมน์สีเขียว) ตามแบบของไฟล์
EDITABLE = {
	"duration": ("start_date", "duration", "predecessors"),
	"dates": ("start_date", "end_date", "predecessors"),
}
# แถบ Gantt รายสัปดาห์ ถ้าแผนยาวเกินนี้ใช้รายเดือน และเผื่อช่วงท้ายไว้ให้เลื่อนงานออกไปได้
MAX_WEEKS = 104
EXTRA_PERIODS = 8
HOLIDAY_SHEET = "วันหยุด"
HOLIDAY_NAME = "Holidays"
# ไม่มีวันหยุดประจำสัปดาห์ (เสาร์-อาทิตย์อยู่ในปฏิทินวันหยุดแล้ว เหมือนการนับในระบบ)
NO_WEEKEND = '"0000000"'
EXCEL_EPOCH = datetime.date(1899, 12, 30)

FONT = "Cordia New"
COLOR_HEADER = "#DCEAF7"
COLOR_INPUT = "#E2EFDA"
COLOR_MISMATCH = "#F8CBAD"
COLOR_BAR = "#5B9BD5"
COLOR_GROUP_BAR = "#404040"
COLOR_DONE = "#70AD47"


# ---------------------------------------------------------------- ส่งออก


@frappe.whitelist()
def export_schedule(name: str, mode: str = "duration"):
	"""mode: duration = กำหนดวันเริ่ม + จำนวนวัน, dates = กำหนดวันเริ่ม-วันจบ"""
	from frappe.desk.utils import provide_binary_file

	doc = frappe.get_doc("Construction Management", name)
	doc.check_permission("read")
	project_name = frappe.db.get_value("Project", doc.project, "project_name") if doc.project else None
	title = re.sub(r'[\\/:*?"<>|]', " ", project_name or doc.name)
	if mode not in EDITABLE:
		frappe.throw(_("แบบไฟล์ {0} ไม่ถูกต้อง").format(mode))
	provide_binary_file(f"{title} - แผนงาน", "xlsx", build_workbook(doc, project_name, mode))


def build_workbook(doc, project_name=None, mode="duration") -> bytes:
	import xlsxwriter

	output = BytesIO()
	wb = xlsxwriter.Workbook(output, {"in_memory": True})
	fmt = make_formats(wb)
	ws = wb.add_worksheet(_("แผนงาน"))
	for col, (_f, _l, width, _k) in enumerate(COLUMNS):
		ws.set_column(col, col, width)

	ws.write(0, 0, _("แผนงานก่อสร้าง {0}").format(project_name or doc.name), fmt["title"])
	ws.write(1, 0, _("สัญญา"), fmt["label"])
	ws.write(1, 1, contract_text(doc), fmt["value"])
	ws.write(
		1,
		3,
		_("กรอกได้เฉพาะคอลัมน์หัวสีเขียว แล้วนำเข้ากลับ ช่องที่เว้นว่าง = ไม่เปลี่ยน")
		+ " "
		+ (_("(แบบกำหนดวันเริ่ม-จบ: จำนวนวันนับให้)") if mode == "dates" else _("(แบบกำหนดจำนวนวัน: วันจบคำนวณให้)")),
		fmt["note"],
	)
	ws.write(2, 0, _("ส่งออกเมื่อ"), fmt["label"])
	ws.write_datetime(2, 1, excel_datetime(nowdate()), fmt["value_date"])
	ws.write(
		2,
		3,
		_("นำเข้าใช้วันเริ่ม-วันจบเสมอ จำนวนวันใช้เฉพาะแถวที่วันจบว่าง งานที่มีงานก่อนหน้าเลื่อนตามตอนนำเข้า"),
		fmt["note"],
	)

	for col, (fieldname, label, _w, _k) in enumerate(COLUMNS):
		ws.write(HEADER_ROW, col, _(label), fmt["header_input" if fieldname in EDITABLE[mode] else "header"])

	holidays = doc.get_holidays() if doc.use_working_days else set()
	if doc.use_working_days:
		write_holiday_sheet(wb, fmt, holidays)

	first = len(COLUMNS)
	periods = gantt_periods(doc.tasks)
	for i, period in enumerate(periods):
		ws.set_column(first + i, first + i, 3.2)
		ws.write_datetime(HEADER_ROW, first + i, excel_datetime(period["start"]), fmt["period"])
		ws.write_datetime(PERIOD_END_ROW, first + i, excel_datetime(period["end"]), fmt["value_date"])
	ws.set_row(PERIOD_END_ROW, None, None, {"hidden": True})

	rows = {row.name: row for row in doc.tasks}
	first_row = HEADER_ROW + 1
	for i, row in enumerate(doc.tasks):
		r = first_row + i
		values = {**row.as_dict(), "predecessors": format_predecessors(row.predecessors, rows)}
		for col, (fieldname, _l, _w, kind) in enumerate(COLUMNS):
			write_cell(ws, fmt, r, col, values.get(fieldname), kind, row.is_group)
		if row.is_group:
			write_group_dates(ws, fmt, r, first_row + last_descendant(doc.tasks, i), row, holidays)
		else:
			if mode == "dates":
				write_duration(ws, fmt, r, row, holidays)
			else:
				write_end_date(ws, fmt, r, row, holidays)

	last_row = first_row + len(doc.tasks) - 1
	if doc.tasks and mode == "duration":
		write_duration_rule(ws, fmt, first_row, last_row, holidays)
	if periods and doc.tasks:
		write_bar_rules(ws, fmt, doc.tasks, first_row, last_row, first, first + len(periods) - 1)

	ws.freeze_panes(HEADER_ROW + 1, 2)
	ws.set_row(HEADER_ROW, 48)
	ws.set_landscape()
	ws.set_paper(9)  # A4
	ws.fit_to_pages(1, 0)
	ws.repeat_rows(HEADER_ROW)
	ws.activate()
	wb.close()
	return output.getvalue()


def contract_text(doc) -> str:
	if not doc.start_date or not doc.finish_date:
		return ""
	fmt = "%d/%m/%Y"
	return _("{0} - {1} ({2} วัน)").format(
		getdate(doc.start_date).strftime(fmt), getdate(doc.finish_date).strftime(fmt), doc.duration
	)


def write_cell(ws, fmt, r, col, value, kind, is_group):
	suffix = "_bold" if is_group else ""
	if value in (None, "") or (kind in ("number", "int") and not flt(value)):
		ws.write_blank(r, col, None, fmt["text" + suffix])
	elif kind == "date":
		ws.write_datetime(r, col, excel_datetime(value), fmt["date" + suffix])
	elif kind in ("number", "percent", "int"):
		ws.write_number(r, col, flt(value), fmt[kind + suffix])
	else:
		# เขียนเป็นข้อความเสมอ WBS เช่น 1.10 จะไม่กลายเป็นตัวเลข 1.1
		ws.write_string(r, col, cstr(value), fmt["text" + suffix])


def write_holiday_sheet(wb, fmt, holidays):
	sheet = wb.add_worksheet(_(HOLIDAY_SHEET))
	sheet.set_column(0, 0, 14)
	sheet.write(0, 0, _("วันหยุด (ใช้คำนวณวันจบ)"), fmt["label"])
	for i, day in enumerate(sorted(holidays), start=1):
		sheet.write_datetime(i, 0, excel_datetime(day), fmt["date"])
	wb.define_name(HOLIDAY_NAME, f"='{_(HOLIDAY_SHEET)}'!$A$2:$A${max(len(holidays), 1) + 1}")


def write_end_date(ws, fmt, r, row, holidays):
	"""วันจบของงานย่อย = สูตรจากวันเริ่ม + จำนวนวัน (ตรงกับ add_working_days)
	งานที่วันจบตกวันหยุด (สูตรจะได้วันทำงานก่อนหน้า) เขียนเป็นค่าตรงๆ เพื่อไม่ให้แผนเปลี่ยนเอง"""
	start, duration, end = (cell(r, f) for f in ("start_date", "duration", "end_date"))
	if holidays:
		formula = f"WORKDAY.INTL({start}-1,MAX({duration},1),{NO_WEEKEND},{HOLIDAY_NAME})"
	else:
		formula = f"{start}+MAX({duration},1)-1"
	if not row.start_date:
		ws.write_formula(end, f'=IF(ISNUMBER({start}),{formula},"")', fmt["date"], "")
		return
	computed = add_working_days(row.start_date, max(cint(row.duration), 1), holidays)
	if row.end_date and computed != getdate(row.end_date):
		return  # write_cell เขียนค่าไว้แล้ว
	ws.write_formula(end, f'=IF(ISNUMBER({start}),{formula},"")', fmt["date"], excel_serial(computed))


def write_duration(ws, fmt, r, row, holidays):
	"""จำนวนวันของงานย่อย = วันทำงานจากวันเริ่มถึงวันจบ (แบบกำหนดวันเริ่ม-จบ)"""
	start, end, duration = (cell(r, f) for f in ("start_date", "end_date", "duration"))
	ws.write_formula(
		duration,
		f'=IF(AND(ISNUMBER({start}),ISNUMBER({end})),{working_days(start, end, holidays)},"")',
		fmt["int"],
		cint(row.duration) if row.start_date and row.end_date else "",
	)


def working_days(start, end, holidays) -> str:
	"""สูตรนับวันรวมวันเริ่มและวันจบ ไม่นับวันหยุด (ตรงกับ count_working_days)"""
	if holidays:
		return f"NETWORKDAYS.INTL({start},{end},{NO_WEEKEND},{HOLIDAY_NAME})"
	return f"{end}-{start}+1"


def write_group_dates(ws, fmt, r, last, row, holidays):
	"""วันเริ่ม/จบของกลุ่ม = MIN/MAX ของแถวลูกหลาน จำนวนวัน = วันทำงานในช่วงนั้น"""
	start, end, duration = (cell(r, f) for f in ("start_date", "end_date", "duration"))
	starts = f"{cell(r + 1, 'start_date')}:{cell(last, 'start_date')}"
	ends = f"{cell(r + 1, 'end_date')}:{cell(last, 'end_date')}"
	has_dates = bool(row.start_date and row.end_date)
	ws.write_formula(
		start,
		f'=IF(COUNT({starts})=0,"",MIN({starts}))',
		fmt["date_bold"],
		excel_serial(row.start_date) if has_dates else "",
	)
	ws.write_formula(
		end,
		f'=IF(COUNT({ends})=0,"",MAX({ends}))',
		fmt["date_bold"],
		excel_serial(row.end_date) if has_dates else "",
	)
	ws.write_formula(
		duration,
		f'=IF(ISNUMBER({start}),{working_days(start, end, holidays)},"")',
		fmt["int_bold"],
		cint(row.duration) if has_dates else "",
	)


def write_duration_rule(ws, fmt, first_row, last_row, holidays):
	"""จำนวนวันที่ไม่ตรงกับวันเริ่ม-วันจบ (พิมพ์วันจบทับสูตร) เป็นสีส้ม ให้รู้ว่าตอนนำเข้าจะใช้วันที่แทน"""
	start, end, duration = (cell(first_row, f) for f in ("start_date", "end_date", "duration"))
	days = working_days(start, end, holidays)
	col = next(i for i, column in enumerate(COLUMNS) if column[0] == "duration")
	ws.conditional_format(
		first_row,
		col,
		last_row,
		col,
		{
			"type": "formula",
			"criteria": f"=AND(ISNUMBER({start}),ISNUMBER({end}),{duration}<>{days})",
			"format": fmt["mismatch"],
		},
	)


def write_bar_rules(ws, fmt, tasks, first_row, last_row, first_col, last_col):
	"""แถบ Gantt: ช่องที่ช่วงเวลา (หัวคอลัมน์ ถึงแถวซ่อนเหนือหัว) ซ้อนกับวันเริ่ม-วันจบของแถว
	กลุ่ม = สีเข้ม, งานที่ % จริงครบ 100 = เขียว, งานอื่น = ฟ้า"""
	from xlsxwriter.utility import xl_col_to_name, xl_rowcol_to_cell

	period = xl_col_to_name(first_col)

	def overlaps(r):
		start = cell(r, "start_date", lock_column=True)
		end = cell(r, "end_date", lock_column=True)
		return (
			f"ISNUMBER({start}),ISNUMBER({end}),"
			f"{start}<={period}${PERIOD_END_ROW + 1},{end}>={period}${HEADER_ROW + 1}"
		)

	def span(r):
		return f"{xl_rowcol_to_cell(r, first_col)}:{xl_rowcol_to_cell(r, last_col)}"

	groups = [first_row + i for i, row in enumerate(tasks) if row.is_group]
	if groups:
		ws.conditional_format(
			groups[0],
			first_col,
			groups[0],
			last_col,
			{
				"type": "formula",
				"criteria": f"=AND({overlaps(groups[0])})",
				"format": fmt["bar_group"],
				"stop_if_true": True,
				"multi_range": " ".join(span(r) for r in groups),
			},
		)
	progress = cell(first_row, "progress", lock_column=True)
	for criteria, style in (
		(f"=AND({overlaps(first_row)},{progress}>=100)", "bar_done"),
		(f"=AND({overlaps(first_row)})", "bar"),
	):
		ws.conditional_format(
			first_row,
			first_col,
			last_row,
			last_col,
			{"type": "formula", "criteria": criteria, "format": fmt[style], "stop_if_true": True},
		)


def last_descendant(tasks, index) -> int:
	"""index ของแถวสุดท้ายที่อยู่ใต้กลุ่ม tasks[index] (แถวลูกหลานอยู่ติดกันตาม WBS)"""
	last = index
	while last + 1 < len(tasks) and cint(tasks[last + 1].indent) > cint(tasks[index].indent):
		last += 1
	return last


def cell(r, fieldname, lock_column=False) -> str:
	"""ตำแหน่งช่องของคอลัมน์ fieldname เช่น G6 หรือ $G6 (lock_column ใช้ในสูตรของแถบที่ใช้ทุกคอลัมน์ช่วงเวลา)"""
	from xlsxwriter.utility import xl_rowcol_to_cell

	col = next(i for i, column in enumerate(COLUMNS) if column[0] == fieldname)
	return xl_rowcol_to_cell(r, col, col_abs=lock_column)


def excel_datetime(value) -> datetime.datetime:
	return datetime.datetime.combine(getdate(value), datetime.time())


def excel_serial(value) -> int:
	"""เลขวันที่ของ Excel ใช้เป็นค่าที่คำนวณไว้แล้วของสูตร (โปรแกรมที่ไม่คำนวณสูตรจะเห็นค่านี้)"""
	return (getdate(value) - EXCEL_EPOCH).days


def gantt_periods(tasks) -> list[dict]:
	"""ช่วงเวลาของแถบ Gantt: รายสัปดาห์ (เริ่มวันจันทร์) หรือรายเดือนถ้าแผนยาวเกิน MAX_WEEKS
	เผื่อท้าย EXTRA_PERIODS ช่วงให้เห็นแถบเมื่อเลื่อนงานออกไปใน Excel"""
	days = [getdate(row.get(f)) for row in tasks for f in ("start_date", "end_date") if row.get(f)]
	if not days:
		return []
	first, last = min(days), max(days)
	weekly = (last - first).days // 7 < MAX_WEEKS

	def next_start(day):
		return (
			day + datetime.timedelta(days=7) if weekly else (day + datetime.timedelta(days=32)).replace(day=1)
		)

	start = first - datetime.timedelta(days=first.weekday()) if weekly else first.replace(day=1)
	periods = []
	while start <= last:
		periods.append(start)
		start = next_start(start)
	for _i in range(EXTRA_PERIODS):
		periods.append(start)
		start = next_start(start)
	return [{"start": day, "end": next_start(day) - datetime.timedelta(days=1)} for day in periods]


def format_predecessors(value, rows) -> str:
	"""ข้อความงานก่อนหน้า เช่น "1.2, 1.3SS+2" (ตรงกับ format_predecessors ใน schedule.js)"""
	texts = []
	for link in frappe.parse_json(value) if value else []:
		predecessor = rows.get(link.get("task"))
		if not predecessor:
			continue
		lag = cint(link.get("lag"))
		lag_text = f"+{lag}" if lag > 0 else str(lag) if lag < 0 else ""
		link_type = link.get("type") or "FS"
		texts.append(f"{predecessor.wbs}{link_type if link_type != 'FS' or lag_text else ''}{lag_text}")
	return ", ".join(texts)


def make_formats(wb) -> dict:
	base = {"font_name": FONT, "font_size": 14, "valign": "vcenter"}
	cell = {**base, "border": 1, "border_color": "#BFBFBF"}

	def add(style=base, **props):
		return wb.add_format({**style, **props})

	formats = {
		"title": add(bold=True, font_size=16),
		"label": add(bold=True),
		"value": add(),
		"value_date": add(num_format="dd/mm/yyyy", align="left"),
		"note": add(italic=True, font_color="#7F7F7F"),
		"header": add(cell, bold=True, bg_color=COLOR_HEADER, align="center", text_wrap=True),
		"header_input": add(cell, bold=True, bg_color=COLOR_INPUT, align="center", text_wrap=True),
		"period": add(cell, bg_color=COLOR_HEADER, num_format="d mmm yy", rotation=90, font_size=10),
		"bar": add(cell, bg_color=COLOR_BAR),
		"bar_group": add(cell, bg_color=COLOR_GROUP_BAR),
		"bar_done": add(cell, bg_color=COLOR_DONE),
		"mismatch": add(cell, bg_color=COLOR_MISMATCH),
	}
	for suffix, extra in (("", {}), ("_bold", {"bold": True})):
		formats["text" + suffix] = add(cell, **extra)
		formats["date" + suffix] = add(cell, num_format="dd/mm/yyyy", align="center", **extra)
		formats["int" + suffix] = add(cell, num_format="0", **extra)
		formats["number" + suffix] = add(cell, num_format="#,##0.00", **extra)
		formats["percent" + suffix] = add(cell, num_format="0.00", **extra)
	return formats


# ---------------------------------------------------------------- นำเข้า


@frappe.whitelist()
def import_schedule(name: str, filename: str, content: str) -> dict:
	"""อ่านไฟล์ที่ส่งมาเป็น base64 คืน {"rows": [{row_no, wbs, start_date?, end_date?, duration?, predecessors?}],
	"warnings": [...]} key ที่ไม่มีในแถว = คอลัมน์ไม่มีในไฟล์หรือช่องว่าง (ไม่เปลี่ยน) ไม่แก้แผนงาน"""
	frappe.get_doc("Construction Management", name).check_permission("write")
	return parse_schedule_rows(read_spreadsheet(filename, content))


def parse_schedule_rows(rows: list[list]) -> dict:
	header, columns = find_header(rows)
	result, warnings = [], []
	for row_no, cells in enumerate(rows[header + 1 :], start=header + 2):
		values = {field: cells[i] for i, field in columns.items() if i < len(cells)}
		wbs = wbs_text(values.get("wbs"))
		if not wbs:
			continue
		item = {"row_no": row_no, "wbs": wbs}
		for field in ("start_date", "end_date"):
			try:
				day = parse_date(values.get(field))
			except ValueError:
				warnings.append(_("แถว {0}: อ่านวันที่ {1} ไม่ได้ ข้ามช่องนี้").format(row_no, values.get(field)))
				continue
			if day:
				item[field] = day
		# รับ "5", 5 หรือ "5 days" (MS Project)
		duration = re.match(r"\s*(\d+)", cstr(values.get("duration")))
		if duration and int(duration[1]) > 0:
			item["duration"] = int(duration[1])
		if "predecessors" in columns.values():
			# คอลัมน์งานก่อนหน้ามีในไฟล์: ช่องว่าง = ไม่มีงานก่อนหน้า (ลบลิงก์เดิม)
			item["predecessors"] = cstr(values.get("predecessors")).strip()
		result.append(item)
	if not result:
		frappe.throw(_("ไม่พบแถวงานที่มี WBS ในไฟล์"))
	return {"rows": result, "warnings": warnings}


def find_header(rows: list[list]) -> tuple[int, dict[int, str]]:
	"""แถวแรกที่มีคอลัมน์ WBS และ วันเริ่ม/วันจบ/งานก่อนหน้า อย่างน้อยหนึ่งคอลัมน์ คืน (index แถว, {index คอลัมน์: fieldname})"""
	labels = {
		normalize(label): field
		for field, aliases in IMPORT_COLUMNS.items()
		for alias in aliases
		for label in (alias, _(alias))
	}
	for index, cells in enumerate(rows):
		columns = {}
		for i, cell in enumerate(cells):
			field = labels.get(normalize(cell))
			if field and field not in columns.values():
				columns[i] = field
		if "wbs" in columns.values() and len(columns) > 1:
			return index, columns
	frappe.throw(_("ไม่พบแถวหัวตารางที่มีคอลัมน์ WBS และ วันเริ่ม/วันจบ/งานก่อนหน้า"))


def wbs_text(value) -> str:
	# Excel อาจเก็บ WBS "2" เป็นตัวเลข 2.0
	if isinstance(value, float) and value.is_integer():
		value = int(value)
	return cstr(value).strip()


def parse_date(value) -> str | None:
	"""วันที่จากช่อง Excel (datetime) หรือข้อความ วว/ดด/ปปปป (รับปี พ.ศ.) คืน "YYYY-MM-DD" ช่องว่าง = None"""
	if value in (None, ""):
		return None
	if isinstance(value, datetime.datetime):
		return value.date().isoformat()
	if isinstance(value, datetime.date):
		return value.isoformat()
	if isinstance(value, int | float) and not isinstance(value, bool) and 0 < value < 2958466:
		# ช่องวันที่ที่อ่านมาเป็นเลขวันที่ของ Excel (เช่น ค่าจากสูตรในบางโปรแกรม)
		return (EXCEL_EPOCH + datetime.timedelta(days=int(value))).isoformat()
	text = cstr(value).strip().split(" ")[0]
	for pattern, (y, m, d) in DATE_PATTERNS:
		match = pattern.match(text)
		if not match:
			continue
		year = int(match[y])
		# แปลงปีก่อนสร้างวันที่ (29 ก.พ. ต้องเช็กปีอธิกสุรทินด้วยปี ค.ศ.)
		if year > BUDDHIST_YEAR_FROM:
			year -= 543
		return datetime.date(year, int(match[m]), int(match[d])).isoformat()
	raise ValueError(text)
