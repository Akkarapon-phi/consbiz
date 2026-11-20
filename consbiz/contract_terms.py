# Copyright (c) 2026, Siricons and contributors
# For license information, please see license.txt

"""เนื้อหาสัญญาจ้างแบบ HTML (ตกลง 2026-11-18): แม่แบบแก้ได้ (Employment Contract Template) + แก้เฉพาะคนในสัญญา (Employment Contract.terms)

ตัวแปร {{ key }} (VARIABLES) แทนค่าด้วยโค้ดนี้เท่านั้น ไม่ผ่าน Jinja (ผู้ใช้เขียนเนื้อหาเอง กันโค้ดในแม่แบบ) ค่าถูก escape เสมอ
ค่าว่าง = เส้นจุดให้เขียนด้วยมือ (.ec-blank) ไม่รู้จักตัวแปร = บันทึกไม่ได้ (unknown_variables)
หน้าเอกสาร (หัว + เนื้อหา + ช่องลงชื่อ) = render_contract ชุดเดียวทั้ง Print Format "Employment Contract TH" และตัวอย่างในแอป (preview)
"""

import json
import re
from html import escape

import frappe
from frappe import _
from frappe.utils import cint, flt, fmt_money, getdate

from consbiz.utils import name_with_title, thai_baht_text, thai_date

# key, ป้ายที่ผู้ใช้เห็น, ตัวอย่าง (แสดงในหน้าแก้แม่แบบเมื่อยังไม่เลือกพนักงาน)
VARIABLES = [
	("contract_no", "เลขที่สัญญา", "EC-XX260001"),
	("contract_date", "วันที่ทำสัญญา", "1 มกราคม 2570"),
	("company", "ชื่อนายจ้าง (บริษัท)", "บริษัท ตัวอย่าง จำกัด"),
	("company_address", "ที่อยู่นายจ้าง", "99 ถนนตัวอย่าง กรุงเทพฯ"),
	("employee_name", "ชื่อลูกจ้าง (มีคำนำหน้า)", "นายสมชาย ตัวอย่าง"),
	("id_card", "เลขบัตรประชาชนลูกจ้าง", "1-2345-67890-12-3"),
	("address", "ที่อยู่ลูกจ้าง", "1 หมู่ 1 ต.ตัวอย่าง อ.ตัวอย่าง จ.ตัวอย่าง"),
	("designation", "ตำแหน่ง", "โฟร์แมน"),
	("department", "แผนก/ฝ่าย", "ปฏิบัติการ"),
	("start_date", "วันเริ่มงาน", "1 มกราคม 2570"),
	("prob_days", "จำนวนวันทดลองงาน", "119"),
	("prob_start", "วันเริ่มทดลองงาน", "1 มกราคม 2570"),
	("prob_end", "วันสิ้นสุดทดลองงาน", "29 เมษายน 2570"),
	("base", "ค่าจ้างต่อเดือน (ตัวเลข)", "15,000.00"),
	("base_text", "ค่าจ้างต่อเดือน (ตัวอักษร)", "หนึ่งหมื่นห้าพันบาทถ้วน"),
	("employer_signer", "ผู้ลงนามฝ่ายนายจ้าง", "นายใหญ่ ตัวอย่าง"),
]
KEYS = {key for key, _label, _sample in VARIABLES}
# Quill / contenteditable อาจเปลี่ยนช่องว่างในวงเล็บเป็น &nbsp;
VAR_RE = re.compile(r"\{\{(?:\s|&nbsp;| )*([A-Za-z_][A-Za-z0-9_]*)(?:\s|&nbsp;| )*\}\}")
HEADING = "สัญญาจ้างพนักงาน"


def unknown_variables(html):
	return sorted({m.group(1) for m in VAR_RE.finditer(html or "")} - KEYS)


def render_terms(html, context):
	"""แทน {{ key }} ด้วยค่า (escape) ค่าว่าง = เส้นจุด ตัวแปรที่ไม่รู้จัก = แสดงชื่อเดิมแบบเตือน"""

	def value(match):
		key = match.group(1)
		if key not in KEYS:
			return f'<span class="ec-unknown">{escape(match.group(0))}</span>'
		text = context.get(key)
		if text in (None, ""):
			return '<span class="ec-blank"></span>'
		return f'<span class="ec-val">{escape(str(text))}</span>'

	return VAR_RE.sub(value, html or "")


def strip_abbr(value, company=None):
	"""แผนก "ปฏิบัติการ - ST" → "ปฏิบัติการ" (ตัวย่อบริษัทท้ายชื่อของ ERPNext: ของบริษัทที่ส่งมา หรือบริษัทของแผนกนั้น)"""
	if not value:
		return value
	for owner in (company, frappe.db.get_value("Department", value, "company")):
		abbr = owner and frappe.get_cached_value("Company", owner, "abbr")
		if abbr and value.endswith(f" - {abbr}"):
			return value[: -len(abbr) - 3]
	return value


def id_card(value):
	"""เลขบัตร 13 หลัก → 1-2345-67890-12-3 (รูปแบบอื่นคงเดิม)"""
	digits = re.sub(r"\D", "", value or "")
	if len(digits) != 13:
		return value
	return f"{digits[0]}-{digits[1:5]}-{digits[5:10]}-{digits[10:12]}-{digits[12]}"


def full_company_name(company):
	"""ชื่อเต็มของบริษัท (`Company.custom_company` เช่น "ห้างหุ้นส่วนจำกัด ...") ว่าง = company_name (ชื่อย่อ เช่น "หจก. ...")"""
	c = frappe.db.get_value("Company", company, ["custom_company", "company_name"], as_dict=True) or {}
	return c.get("custom_company") or c.get("company_name") or company


def context_of(doc):
	"""ค่าของตัวแปรจากสัญญา (ช่องของสัญญาก่อน ว่างแล้วใช้ของพนักงาน/บริษัท)"""
	emp = frappe._dict()
	if doc.get("employee"):
		emp = frappe.db.get_value(
			"Employee",
			doc.employee,
			["employee_name", "salutation", "custom_id_card", "permanent_address", "designation", "department", "date_of_joining"],
			as_dict=True,
		) or frappe._dict()
	company = doc.get("company")
	full_name = doc.get("full_name") or emp.employee_name
	salutation = doc.get("salutation") or emp.salutation
	if full_name and salutation and not full_name.startswith(salutation):
		thai = re.search("[฀-๿]", salutation)
		full_name = salutation + ("" if thai else " ") + full_name
	base = flt(doc.get("base"))
	return {
		"contract_no": doc.get("name") if doc.get("name") and not str(doc.name).startswith("new-") else "",
		"contract_date": thai_date(doc.get("date")),
		"company": company and full_company_name(company),
		"company_address": company and frappe.db.get_value("Company", company, "custom_company_address"),
		"employee_name": full_name,
		"id_card": id_card(emp.custom_id_card),
		"address": emp.permanent_address and " ".join(str(emp.permanent_address).split()),
		"designation": doc.get("designation") or emp.designation,
		"department": doc.get("department") or strip_abbr(emp.department, company),
		"start_date": thai_date(emp.date_of_joining or doc.get("prob_start_date")),
		"prob_days": str(cint(doc.get("prob_days"))) if cint(doc.get("prob_days")) else "",
		"prob_start": thai_date(doc.get("prob_start_date")),
		"prob_end": thai_date(doc.get("prob_end_date")),
		"base": fmt_money(base, 2) if base else "",
		"base_text": thai_baht_text(base) if base else "",
		"employer_signer": doc.get("employer_signer"),
	}


def sample_context():
	return {key: sample for key, _label, sample in VARIABLES}


# ---------------------------------------------------------------- รูปแบบหน้ากระดาษ (layout ของแม่แบบ คัดลอกลงสัญญา, ตกลง 2026-11-18)
# ฟอนต์ฝังในหน้า (data URI) ไม่โหลดจาก URL: Chrome PDF ของ Frappe บนเครื่องนี้ไม่โหลด @font-face จาก URL (ได้ฟอนต์ระบบแทน)
THAI_RANGE = "U+02D7, U+0303, U+0331, U+0E01-0E5B, U+200C-200D, U+25CC"
LATIN_RANGE = (
	"U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+02C6, U+02DA, U+02DC, U+0304, U+0308, U+0329, "
	"U+2000-206F, U+20AC, U+2122, U+2191, U+2193, U+2212, U+2215, U+FEFF, U+FFFD"
)
FONTS = {
	"Sarabun": {
		"label": "Sarabun (สารบรรณ)",
		"size": 16,
		# สระบน/วรรณยุกต์ของ Sarabun สูงเกินบรรทัดเมื่อระยะบรรทัดน้อยกว่า ~1.45 (ตัดหน้าแล้วเห็นเศษสระท้ายหน้า)
		"line": 1.5,
		"faces": [
			(weight, style, f"sarabun/sarabun-{subset}-{weight}-{style}.woff2", rng)
			for weight in (400, 700)
			for style in ("normal", "italic")
			for subset, rng in (("thai", THAI_RANGE), ("latin", LATIN_RANGE))
		],
	},
	"Noto Sans Thai": {
		"label": "Noto Sans Thai",
		"size": 11,
		"line": 1.75,
		"faces": [
			("100 900", "normal", "noto-sans-thai/NotoSansThai-Variable-thai.woff2", THAI_RANGE),
			("100 900", "normal", "noto-sans-thai/NotoSansThai-Variable-latin.woff2", LATIN_RANGE),
		],
	},
}
INDENTS = {
	"first_line": "ย่อหน้าบรรทัดแรก (บรรทัดถัดไปชิดขอบ)",
	"block": "เยื้องทั้งย่อหน้า",
	"hanging": "เยื้องแขวน (บรรทัดถัดไปตรงกับข้อความหลังเลขข้อ)",
}
# ขอบกระดาษตามระเบียบงานสารบรรณ (บน 2.5 ซม. ซ้าย 3 ซม. ขวา/ล่าง 2 ซม.)
LAYOUT = {
	"font": "Sarabun",
	"font_size": 16,
	"line_height": 1.5,
	"margin_top": 25,
	"margin_bottom": 20,
	"margin_left": 30,
	"margin_right": 20,
	"indent_style": "first_line",
	"indent_cm": 1.25,
	# หัวกระดาษ = ข้อมูลบริษัททุกหน้า / ท้ายกระดาษ = ลูกจ้างลงชื่อทุกหน้า (ตกลง 2026-11-18)
	"letterhead": 1,
	"footer_sign": 1,
}
_font_cache = {}


def layout_of(value):
	"""layout ที่ใช้ได้เสมอ (ค่าว่าง/ผิด = ค่าเริ่มต้น) ตัวเลขถูกจำกัดช่วง"""
	if isinstance(value, str):
		try:
			value = json.loads(value or "{}")
		except ValueError:
			value = {}
	value = value or {}
	out = dict(LAYOUT)
	if value.get("font") in FONTS:
		out["font"] = value["font"]
		out["font_size"], out["line_height"] = FONTS[out["font"]]["size"], FONTS[out["font"]]["line"]
	if value.get("indent_style") in INDENTS:
		out["indent_style"] = value["indent_style"]
	for key in ("letterhead", "footer_sign"):
		if key in value:
			out[key] = 1 if cint(value[key]) else 0
	limits = {"font_size": (8, 24), "line_height": (1, 2.5), "indent_cm": (0, 5)}
	limits |= {f"margin_{side}": (0, 60) for side in ("top", "bottom", "left", "right")}
	for key, (low, high) in limits.items():
		if value.get(key) not in (None, ""):
			out[key] = min(high, max(low, flt(value[key])))
	return out


def font_css(font, inline=True):
	"""@font-face ของฟอนต์ที่เลือก ชื่อ "EC Font" (ไม่ชนกับฟอนต์ของ print_style.html)"""
	out = []
	for weight, style, path, rng in FONTS[font]["faces"]:
		if inline:
			if path not in _font_cache:
				import base64

				with open(frappe.get_app_path("consbiz", "public", "fonts", path), "rb") as f:
					_font_cache[path] = "data:font/woff2;base64," + base64.b64encode(f.read()).decode()
			src = _font_cache[path]
		else:
			src = f"/assets/consbiz/fonts/{path}"
		out.append(
			f'@font-face {{ font-family: "EC Font"; font-weight: {weight}; font-style: {style}; '
			f'src: url("{src}") format("woff2"); unicode-range: {rng}; }}'
		)
	return "\n".join(out)


def indent_css(style, cm):
	"""ข้อย่อย ql-indent-1..3 ตามรูปแบบย่อหน้า (ระดับละ cm)"""
	rules = []
	for level in (1, 2, 3):
		step = round(cm * level, 2)
		if style == "block":
			rule = f"padding-left: {step}cm; text-indent: 0"
		elif style == "hanging":
			rule = f"padding-left: calc({step}cm + 2.2em); text-indent: -2.2em"
		else:
			rule = f"padding-left: 0; text-indent: {step}cm"
		rules.append(f".ec-body .ql-indent-{level} {{ {rule}; }}")
	return "\n".join(rules)


STYLE = """
/* .print-format { margin-* } มีไว้ให้ Frappe อ่านเป็นขอบกระดาษ PDF เท่านั้น: ยกเลิกในหน้าจริง (div.print-format parser ของ Frappe ไม่อ่าน) */
div.print-format { margin: 0 !important; padding: 0 !important; max-width: none !important; width: auto !important; }
/* geometricPrecision: Chrome PDF ใช้ font hinting ปัดความกว้างตัวอักษร (Sarabun 11pt: "Safet y", "Mast er" มีช่องว่างกลางคำ)
   ไม่ hint = ระยะตัวอักษรเท่าตัวอย่างบนจอ ตั้งที่ .ec-doc ให้ทั้งตัวอย่างและ PDF วัด/ตัดบรรทัดแบบเดียวกัน */
.ec-doc { color: #111; font-family: "EC Font", "Noto Sans Thai", InterVariable, system-ui, sans-serif; text-rendering: geometricPrecision; }
.ec-doc h1 { margin: 0 0 0.9em; text-align: center; font-size: 1.35em; font-weight: 700; }
.ec-meta { display: flex; justify-content: space-between; gap: 16px; margin-bottom: 0.9em; }
.ec-body p { margin: 0 0 0.2em; }
.ec-body p:empty, .ec-body p:has(> br:only-child) { min-height: 1em; }
.ec-body .ql-align-center { text-align: center; }
.ec-body .ql-align-right { text-align: right; }
.ec-body .ql-align-justify { text-align: justify; }
.ec-body ol, .ec-body ul { margin: 0 0 0.2em; padding-left: 2.2em; }
.ec-val { font-weight: 600; }
.ec-blank { display: inline-block; min-width: 9em; border-bottom: 1px dotted #555; height: 1.1em; vertical-align: baseline; }
.ec-unknown { color: #c0262d; background: #fde8e8; }
.ec-sign { display: grid; grid-template-columns: 1fr 1fr; gap: 2.4em 2.6em; margin-top: 3em; break-inside: avoid; page-break-inside: avoid; }
.ec-sign-box { text-align: center; }
/* ช่องลงชื่อต้องไม่กว้างเกินพื้นที่พิมพ์: Chrome PDF ย่อทั้งหน้าให้พอดีส่วนที่กว้างที่สุด (ตัวอย่างกับ PDF จะตัดหน้าไม่ตรงกัน) */
.ec-sign-line { display: flex; align-items: baseline; gap: 6px; min-width: 0; }
.ec-sign-line i { flex: 1; min-width: 3em; border-bottom: 1px dotted #555; }
.ec-sign-name { margin-top: 0.4em; overflow-wrap: anywhere; }
.ec-sign-name span { display: inline-block; min-width: 60%; }
/* หัว/ท้ายกระดาษ: paginate.js วางในแผ่นเอง (ขอบบน → หัวกระดาษ → เนื้อหา → ท้ายกระดาษ → ขอบล่าง)
   ลำดับในหน้า: ขอบบน → หัวกระดาษ → เนื้อหา → ท้ายกระดาษ → ขอบล่าง (ตัวอย่างในแอปจัดแบบเดียวกัน) */
/* Frappe คัด <head> ของหน้าเนื้อหาไปหน้าหัว/ท้ายกระดาษ ซึ่งมี @media print .wrapper { padding: 17mm 0 1mm !important }
   (เลียนแบบ wkhtmltopdf) ทำให้วัดหัว/ท้ายกระดาษสูงเกิน 18 มม. และท้ายกระดาษเลื่อนลง = เนื้อหาเว้นว่างก่อนท้ายกระดาษทุกหน้า */
@media print { div.print-format > div.wrapper { padding: 0 !important; } }
.ec-head { display: flex; align-items: center; gap: 4mm; padding-bottom: 2.5mm; margin-bottom: 0; border-bottom: 1.5px solid #333; font-size: 0.68em; line-height: 1.35; }
/* สูงคงที่: วัดความสูงหัวกระดาษได้ถูกแม้รูปยังโหลดไม่เสร็จ (ตัวอย่างในแอป / Frappe วัดก่อนรูปโหลด = เนื้อหาทับหัวกระดาษ) */
.ec-head img { flex: none; height: 16mm; width: auto; max-width: 32mm; object-fit: contain; }
/* ระยะหัวกระดาษถึงเนื้อหา = padding (Frappe วัดความสูงหัวกระดาษไม่นับ margin ของลูก) */
.ec-head-wrap { padding-bottom: 8mm; }
.ec-head b { display: block; font-size: 1.45em; line-height: 1.3; }
.ec-head span { display: block; color: #333; }
/* ท้ายกระดาษ: เว้นบน 6 มม. กันเนื้อหาชิดช่องเซ็น 3 คอลัมน์ (เลขหน้า | นายจ้าง/พยาน | ลูกจ้าง/พยาน) ลูกจ้างขวาสุดทุกหน้า */
.ec-foot { padding-top: 6mm; font-size: 10pt; line-height: 1.35; }
/* ช่องเซ็นไม่ชิดขอบขวา (padding-right) และห่างกันพอ (gap 12 มม.) ช่องเซ็นหดได้ (minmax 0) ห้ามกว้างเกินพื้นที่พิมพ์:
   Chrome PDF จะย่อทั้งหน้าแล้วตัดหน้าไม่ตรงตัวอย่าง */
.ec-foot-grid { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 56mm) minmax(0, 56mm); gap: 3mm 12mm; padding-right: 8mm; align-items: end; }
.ec-foot-no { color: #8c8c8c; font-size: 0.85em; white-space: nowrap; }

.ec-doc { max-width: 100%; overflow-wrap: break-word; }
"""


def layout_css(layout, inline=True):
	m = layout
	return (
		font_css(m["font"], inline)
		+ STYLE
		+ f".ec-doc {{ font-size: {m['font_size']}pt; line-height: {m['line_height']}; }}\n"
		+ indent_css(m["indent_style"], m["indent_cm"])
	)


def signature(role, name):
	shown = escape(name) if name else "&nbsp;"
	return (
		f'<div class="ec-sign-box"><div class="ec-sign-line">ลงชื่อ<i></i>{escape(role)}</div>'
		f'<div class="ec-sign-name">(<span>{shown}</span>)</div></div>'
	)


def render_contract(doc, context=None, inline_fonts=True, script=True):
	"""หน้าเอกสารสัญญาจ้าง (HTML ไม่รวม <html>) ใช้ทั้ง Print Format และตัวอย่าง (ตกลง 2026-11-18)
	ต้นฉบับอยู่ #ec-src แล้วแบ่งเป็นแผ่น A4 ด้วย public/js/shared/components/contract/paginate.js ชุดเดียวกับตัวอย่างในแอป
	(ฝังสคริปต์ในหน้า ทำงานตอน load ก่อน Chrome พิมพ์ = PDF ตรงกับตัวอย่าง) หัว/ท้ายกระดาษจึงกำหนดต่างกันต่อหน้าได้:
	ท้ายกระดาษทุกหน้า = เลขหน้า + ลูกจ้าง / หน้าสุดท้าย = + นายจ้าง (+ พยาน แถวที่ 2)
	ขอบกระดาษอยู่ในแผ่นเอง: Frappe พิมพ์ขอบ 0 (.print-format { margin-* : 0 })"""
	context = context or context_of(doc)
	layout = layout_of(doc.get("layout"))
	margins = " ".join(str(layout[f"margin_{side}"]) for side in ("top", "right", "bottom", "left"))
	heading = doc.get("heading") or HEADING
	no = context.get("contract_no")
	date = context.get("contract_date")
	blank = '<span class="ec-blank"></span>'
	employee = signature(_("ลูกจ้าง"), context.get("employee_name"))
	employer = signature(_("นายจ้าง"), context.get("employer_signer"))
	witnesses = [signature(_("พยาน"), ""), signature(_("พยาน"), "")] if cint(doc.get("witnesses")) else []
	page_no = '<span class="ec-foot-no">หน้า <span class="page"></span>/<span class="topage"></span></span>'
	empty = "<span></span>"
	if layout["footer_sign"]:
		# ลูกจ้างคอลัมน์ขวาสุดทุกหน้า หน้าสุดท้ายนายจ้างข้างซ้าย พยานแถวล่าง เลขหน้าซ้ายล่าง
		foot = page_no + empty + employee
		foot_last = (empty + employer + employee + page_no + "".join(witnesses)) if witnesses else (page_no + employer + employee)
		signs = []
	else:
		foot = foot_last = page_no + empty + empty
		signs = [employee, employer, *witnesses]
	grid = lambda cells: f'<div class="ec-foot"><div class="ec-foot-grid">{cells}</div></div>'
	head = letterhead(doc.get("company")) if layout["letterhead"] else ""
	body = (
		f"<h1>{escape(heading)}</h1>"
		f'<div class="ec-meta"><span>สัญญาเลขที่ {escape(no) if no else blank}</span>'
		f"<span>วันที่ {escape(date) if date else blank}</span></div>"
		f'<div class="ec-body">{render_terms(doc.get("terms"), context)}</div>'
		+ (f'<div class="ec-sign">{"".join(signs)}</div>' if signs else "")
	)
	return (
		"<style>.print-format { margin-top: 0mm; margin-bottom: 0mm; margin-left: 0mm; margin-right: 0mm; padding: 0; }\n"
		f"{layout_css(layout, inline_fonts)}\n{SHEET_CSS}</style>"
		f'<div id="ec-src" data-page="210 297" data-margins="{margins}">'
		+ (f'<div class="ec-src-head"><div class="ec-head-wrap">{head}</div></div>' if head else "")
		+ f'<div class="ec-src-foot">{grid(foot)}</div>'
		+ f'<div class="ec-src-foot-last">{grid(foot_last)}</div>'
		+ f'<div class="ec-main">{body}</div></div>'
		+ '<div id="ec-pages"></div>'
		+ (PAGINATE_SCRIPT() if script else "")
	)


# แผ่นกระดาษของ paginate.js ตอนพิมพ์: 1 แผ่น = 1 หน้า (ขอบหน้า 0) ต้นฉบับซ่อนเมื่อแบ่งหน้าแล้ว (สคริปต์ไม่ทำงาน = พิมพ์ต้นฉบับแทน)
SHEET_CSS = """
@page { size: A4; margin: 0; }
html.ec-paged #ec-src { display: none; }
.ec-sheet { position: relative; box-sizing: border-box; width: 210mm; height: 297mm; overflow: hidden; background: #fff;
	break-after: page; page-break-after: always; break-inside: avoid; }
.ec-sheet:last-child { break-after: auto; page-break-after: auto; }
@media print { body, .print-format-gutter { margin: 0 !important; padding: 0 !important; background: #fff !important; } .action-banner { display: none !important; } }
/* Frappe: @media print .print-format p { margin: 0 1px } = ย่อหน้าแคบลงตอนพิมพ์ ข้อความไหลต่างจากที่แบ่งหน้าไว้ (ตัวอย่างไม่ตรง PDF) */
@media print { .print-format .ec-doc p { margin-left: 0; margin-right: 0; } }
/* Bootstrap ของ Frappe ตั้ง @media print p { orphans: 3; widows: 3 } (จอ = 2) ตัดหน้าต่างจากที่แบ่งไว้: ใช้ค่าเดียวกันทุกสื่อ */
.ec-doc p, .ec-doc li, .ec-doc h1 { orphans: 2; widows: 2; }
"""


# ฟอนต์ @font-face (data URI) โหลดแบบ async: Frappe สั่งพิมพ์ทันทีหลัง load ซึ่งฟอนต์ยังไม่เสร็จ (วัดด้วยฟอนต์สำรอง = ตัดหน้าไม่ตรงตัวอย่าง)
# สร้าง FontFace จาก binary ของ data URI เดียวกัน = ใช้ได้ทันที (synchronous) แล้วค่อยแบ่งหน้า
SYNC_FONTS = """function ec_sync_fonts() {
	if (!window.FontFace || !document.fonts) return;
	for (var i = 0; i < document.styleSheets.length; i++) {
		var rules;
		try { rules = document.styleSheets[i].cssRules; } catch (e) { continue; }
		for (var j = 0; j < rules.length; j++) {
			var r = rules[j];
			if (r.type !== 5 || r.style.getPropertyValue("font-family").replace(/["']/g, "") !== "EC Font") continue;
			var m = /url\\(["']?data:font\\/woff2;base64,([^"')]+)/.exec(r.style.getPropertyValue("src"));
			if (!m) continue;
			var bin = atob(m[1]), buf = new Uint8Array(bin.length);
			for (var k = 0; k < bin.length; k++) buf[k] = bin.charCodeAt(k);
			var face = new FontFace("EC Font", buf.buffer, {
				weight: r.style.getPropertyValue("font-weight") || "400",
				style: r.style.getPropertyValue("font-style") || "normal",
				unicodeRange: r.style.getPropertyValue("unicode-range") || "U+0-10FFFF"
			});
			document.fonts.add(face);
		}
	}
}"""


def PAGINATE_SCRIPT():
	"""paginate.js ฝังในหน้า (ไฟล์เดียวกับที่ ContractPreview.vue import) เรียกตอน load และเมื่อฟอนต์โหลดเสร็จ"""
	if "paginate" not in _font_cache:
		path = frappe.get_app_path("consbiz", "public", "js", "shared", "components", "contract", "paginate.js")
		with open(path, encoding="utf-8") as f:
			_font_cache["paginate"] = f.read().replace("export function", "function")
	return (
		"<script>" + _font_cache["paginate"] + "\n" + SYNC_FONTS + "\n(function () {"
		"var run = function () { try { if (ec_paginate(document)) document.documentElement.classList.add('ec-paged'); } catch (e) {} };"
		"ec_sync_fonts(); run(); window.addEventListener('load', run);"
		"})();</script>"
	)


def format_tax_id(value):
	return id_card(value) if value else value


def letterhead(company):
	"""หัวกระดาษ: โลโก้ + ชื่อบริษัท ที่อยู่ เลขประจำตัวผู้เสียภาษี โทร อีเมล (ข้อมูลจาก Company)"""
	if not company:
		return ""
	from consbiz.utils import image_data_uri

	c = frappe.db.get_value(
		"Company", company, ["company_name", "custom_company", "company_logo", "custom_company_address", "tax_id", "phone_no", "email"], as_dict=True
	) or frappe._dict()
	logo = image_data_uri(c.company_logo) if c.company_logo else ""
	contact = "  ".join(
		x for x in (
			c.tax_id and f"เลขประจำตัวผู้เสียภาษี {format_tax_id(c.tax_id)}",
			c.phone_no and f"โทร {c.phone_no}",
			c.email and f"อีเมล {c.email}",
		) if x
	)
	address = " ".join(str(c.custom_company_address or "").split())
	return (
		'<div class="ec-head">'
		+ (f'<img src="{logo}" alt="">' if logo else "")
		+ f"<div><b>{escape(c.custom_company or c.company_name or company)}</b>"
		+ (f"<span>{escape(address)}</span>" if address else "")
		+ (f"<span>{escape(contact)}</span>" if contact else "")
		+ "</div></div>"
	)


def page_html(body, layout=None):
	"""ตัวอย่างในแอป (iframe ไม่มีสคริปต์): ContractPreview.vue เรียก paginate.js เอง แผ่นมีเงา/ระยะห่างแบบหน้าจอ"""
	return (
		'<!doctype html><html lang="th" class="ec-paged"><head><meta charset="utf-8">'
		'<meta name="viewport" content="width=device-width, initial-scale=1">'
		"<style>"
		"html { background: #e9ebef; color-scheme: light; }"
		"body { margin: 0; padding: 16px 0 24px; }"
		".ec-sheet { margin: 0 auto 16px; box-shadow: 0 2px 10px rgba(0,0,0,.15); }"
		".ec-sheet-guide { border: 1px dashed rgba(59,130,246,.35); }"
		f"</style></head><body>{body}</body></html>"
	)


# ---------------------------------------------------------------- API (หน้าแอป)


def require(ptype="read", doctype="Employment Contract Template"):
	if not frappe.has_permission(doctype, ptype):
		frappe.throw(_("ไม่มีสิทธิ์"), frappe.PermissionError)


TEMPLATE_FIELDS = ["name", "title", "company", "is_default", "disabled", "heading", "employer_signer", "witnesses", "description", "terms", "layout", "modified"]


@frappe.whitelist()
def get_templates(company=None, with_terms=0):
	"""แม่แบบที่ใช้ได้ (ของบริษัทนั้น + ของทุกบริษัท) + ตัวแปร + สิทธิ์แก้"""
	require("read")
	fields = TEMPLATE_FIELDS if cint(with_terms) else [f for f in TEMPLATE_FIELDS if f != "terms"]
	rows = frappe.get_all("Employment Contract Template", fields=fields, order_by="is_default desc, title asc")
	if company:
		rows = [r for r in rows if not r.company or r.company == company]
	return {
		"templates": rows,
		"variables": [{"key": k, "label": label, "sample": s} for k, label, s in VARIABLES],
		"fonts": [{"value": k, "label": f["label"], "size": f["size"], "line": f["line"]} for k, f in FONTS.items()],
		"indents": [{"value": k, "label": label} for k, label in INDENTS.items()],
		"layout_default": LAYOUT,
		"can_write": bool(frappe.has_permission("Employment Contract Template", "write")),
	}


def default_template(company):
	for filters in ({"company": company}, {"company": ("is", "not set")}):
		name = frappe.db.get_value(
			"Employment Contract Template", {**filters, "is_default": 1, "disabled": 0}, "name"
		)
		if name:
			return name
	return frappe.db.get_value("Employment Contract Template", {"disabled": 0}, "name", order_by="modified desc")


@frappe.whitelist()
def get_template(name):
	require("read")
	return frappe.get_doc("Employment Contract Template", name).as_dict()


@frappe.whitelist(methods=["POST"])
def save_template(data):
	data = frappe._dict(json.loads(data) if isinstance(data, str) else data)
	require("write")
	if data.name and frappe.db.exists("Employment Contract Template", data.name):
		doc = frappe.get_doc("Employment Contract Template", data.name)
		if data.modified and str(doc.modified) != str(data.modified):
			frappe.throw(_("มีผู้อื่นแก้แม่แบบนี้ไปแล้ว กรุณาโหลดใหม่"))
	else:
		doc = frappe.new_doc("Employment Contract Template")
		# ไม่เลือกบริษัท = ทุกบริษัท (กัน Frappe เติมบริษัทตั้งต้นของผู้ใช้)
		doc.company = None
	if "layout" in data:
		data.layout = json.dumps(layout_of(data.layout))
	for field in ("title", "company", "is_default", "disabled", "heading", "employer_signer", "witnesses", "description", "terms", "layout"):
		if field in data:
			doc.set(field, data[field] or (None if field == "company" else data[field]))
	doc.save()
	if data.title and doc.name != data.title and not doc.is_new():
		frappe.rename_doc("Employment Contract Template", doc.name, data.title)
		doc = frappe.get_doc("Employment Contract Template", data.title)
	return {field: doc.get(field) for field in TEMPLATE_FIELDS} | {"modified": str(doc.modified)}


@frappe.whitelist(methods=["POST"])
def delete_template(name):
	require("delete")
	if frappe.db.exists("Employment Contract", {"contract_template": name}):
		frappe.throw(_("แม่แบบนี้มีสัญญาใช้อยู่ ปิดใช้งานแทนการลบ"))
	frappe.delete_doc("Employment Contract Template", name)


@frappe.whitelist(methods=["POST"])
def preview(data, employee=None):
	"""ตัวอย่างหน้าเอกสาร (real-time ในแอป) จากข้อมูลที่ยังไม่บันทึก
	data = ช่องของสัญญา (หน้าสัญญา) หรือของแม่แบบ (หน้าแก้แม่แบบ, employee = พนักงานตัวอย่าง ไม่ส่ง = ค่าตัวอย่าง)"""
	if not (
		frappe.has_permission("Employment Contract", "read")
		or frappe.has_permission("Employment Contract Template", "read")
	):
		frappe.throw(_("ไม่มีสิทธิ์"), frappe.PermissionError)
	data = frappe._dict(json.loads(data) if isinstance(data, str) else data)
	doc = frappe._dict(
		{key: data.get(key) for key in (
			"name", "company", "employee", "salutation", "full_name", "date", "base", "prob_start_date", "prob_days",
			"prob_end_date", "heading", "designation", "department", "employer_signer", "witnesses", "terms", "layout",
		)}
	)
	if doc.employee:
		frappe.has_permission("Employee", "read", doc.employee, throw=True)
		context = context_of(doc)
		if data.get("sample"):
			# หน้าแม่แบบ + เลือกพนักงาน: ช่องของสัญญาที่ยังไม่มีใช้ค่าตัวอย่าง
			context = {k: v if v not in (None, "") else sample_context()[k] for k, v in context.items()}
	elif data.get("sample"):
		context = sample_context()
		if doc.employer_signer:
			context["employer_signer"] = doc.employer_signer
	else:
		context = context_of(doc)
	return page_html(render_contract(doc, context, inline_fonts=False, script=False), doc.layout)
