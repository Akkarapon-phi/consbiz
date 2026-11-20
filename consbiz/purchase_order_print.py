"""ใบสั่งซื้อแบบ HTML (Print Format standard `Purchase Order TH`, ตกลง 2026-11-18 แปลงจากแบบ Print Designer "Purchase Order")

หน้าตาเดียวกับแบบ Print Designer เดิม: หัวกระดาษ (โลโก้ บริษัท ชื่อเอกสาร เลขหน้า ผู้ขาย กล่องเลขที่/วันที่) ทุกหน้า
→ ตารางรายการ (หัวตารางซ้ำทุกหน้า) → ท้ายเอกสารหน้าสุดท้าย (ตัวอักษร สถานที่จัดส่ง QR แผนที่ ยอดรวม ช่องลงชื่อ) ชิดล่าง
แบ่งหน้าด้วย paginate.js ชุดเดียวกับสัญญาจ้าง (contract_terms.PAGINATE_SCRIPT) ตัวอย่างในแอป (iframe) จึงตรงกับ PDF ทุกหน้า
ฟอนต์ฝังเป็น data URI (Chrome PDF ของเครื่องนี้ไม่โหลด @font-face จาก URL)"""

from html import escape

import frappe
from frappe.utils import flt, fmt_money, getdate, strip_html_tags

from consbiz import contract_terms
from consbiz.utils import image_data_uri

# ขอบกระดาษ มม. (บน ขวา ล่าง ซ้าย)
MARGINS = "8 10 8 15"
MARGINS_TH_3 = "8 12 8 14"
TITLE = "ใบสั่งซื้อ"
SUBTITLE = "(Purchase Order)"
VAT_LABEL = "ภาษีมูลค่าเพิ่ม 7%"


def e(value):
	return escape(str(value)) if value not in (None, "") else ""


def be_date(value):
	"""วันที่ dd/mm/พ.ศ. แบบเดิม (ว่าง = -)"""
	if not value:
		return "-"
	d = getdate(value)
	return f"{d.day:02d}/{d.month:02d}/{d.year + 543}"


def money(value):
	return fmt_money(flt(value), precision=2)


def qty(value):
	value = flt(value)
	return fmt_money(value, precision=0) if value == int(value) else fmt_money(value, precision=2)


def joined(*parts):
	return " ".join(str(p).strip() for p in parts if p and str(p).strip())


def qr_svg(text, size_mm=25):
	"""QR เป็น SVG (pyqrcode ไม่ต้องใช้ไลบรารีรูปภาพ)"""
	if not text:
		return ""
	import io

	import pyqrcode

	buf = io.BytesIO()
	pyqrcode.create(text, error="M").svg(buf, scale=4, quiet_zone=1, xmldecl=False, svgns=True)
	svg = buf.getvalue().decode()
	# pyqrcode ไม่ใส่ viewBox: ย่อด้วย CSS แล้ว QR ถูกตัด (เห็นไม่ครบ) ต้องใส่ viewBox ขนาดเดิมก่อนย่อ
	import re

	m = re.search(r'height="(\d+)" width="(\d+)"', svg)
	box = f'viewBox="0 0 {m.group(2)} {m.group(1)}" ' if m else ""
	return svg.replace(
		"<svg ",
		f'<svg {box}preserveAspectRatio="xMidYMid meet" style="width:{size_mm}mm;height:{size_mm}mm" ',
		1,
	)


def branch_of(code):
	if code == "00000":
		return "สำนักงานใหญ่"
	return code or "-"


def header(doc, style=2):
	company = (
		frappe.db.get_value(
			"Company",
			doc.company,
			["company_logo", "custom_company_address", "tax_id", "phone_no", "email", "website"],
			as_dict=True,
		)
		or frappe._dict()
	)
	title = (
		frappe.db.get_value("Address", doc.billing_address, "address_title") if doc.billing_address else ""
	)
	supplier = (
		frappe.db.get_value(
			"Address",
			doc.supplier_address,
			["address_line1", "address_line2", "city", "county", "state", "pincode", "tax_id", "branch_code"],
			as_dict=True,
		)
		if doc.supplier_address
		else None
	) or frappe._dict()
	logo = image_data_uri(company.company_logo) if company.company_logo else ""
	logo_html = f'<img src="{logo}" alt="">' if logo else ""
	project = frappe.db.get_value("Project", doc.project, "project_name") if doc.project else ""
	contact = [
		company.tax_id and f"<span>เลขที่ภาษี : {e(company.tax_id)}</span>",
		company.phone_no and f"<span>โทร : {e(company.phone_no)}</span>",
	]
	web = [
		company.email and f"<span>Email : {e(company.email)}</span>",
		company.website and f"<span>Website : {e(company.website)}</span>",
	]
	# ชื่อฉบับ (.copy-label) paginate.js ใส่ตามฉบับที่เลือกพิมพ์ (ต้นฉบับ/สำเนา) ฉบับแก้ไข (amend) ก็เป็นต้นฉบับของฉบับใหม่
	copy = '<span class="copy-label">ต้นฉบับ</span>'
	if style == 4:
		# รูปแบบที่ 4: ชื่อฉบับเป็นป้าย (badge) พื้นกรมท่าตัวขาว เด่นกว่าตัวหนา
		copy = '<span class="po-badge copy-label">ต้นฉบับ</span>'
	rows = [
		("เลขที่ :", e(doc.name)),
		("วันที่ออก :", be_date(doc.transaction_date)),
		("ครบกำหนด :", be_date(doc.schedule_date)),
		("การชำระเงิน :", e(doc.payment_terms_template)),
		("อ้างอิง :", e(doc.get("po_no"))),
	]
	return (
		'<div class="po-head">'
		'<div class="po-top">'
		f'<div class="po-logo">{logo_html}</div>'
		'<div class="po-company">'
		f"<b>{e(title or doc.company)}</b>"
		f"<span>{e(' '.join(str(company.custom_company_address or '').split()))}</span>"
		f'<span class="po-inline">{"".join(x for x in contact if x)}</span>'
		f'<span class="po-inline">{"".join(x for x in web if x)}</span>'
		"</div>"
		'<div class="po-title">'
		f"<h1>{TITLE}</h1>"
		f'<div class="po-sub">{SUBTITLE}<b>{copy}</b></div>'
		'<div class="po-pageno">หน้า <span class="page"></span> / <span class="topage"></span></div>'
		+ (f'<div class="po-pageno">แก้ไขจาก {e(doc.amended_from)}</div>' if doc.amended_from else "")
		+ "</div></div>"
		'<div class="po-parties">'
		+ (party4(doc, supplier, project) if style == 4 else party2(doc, supplier, project))
		+ '<dl class="po-box">'
		+ "".join(f"<dt>{label}</dt><dd>{value or '&nbsp;'}</dd>" for label, value in rows)
		+ "</dl></div></div>"
	)


def party2(doc, supplier, project):
	return (
		'<dl class="po-party">'
		f"<dt>ผู้ขาย :</dt><dd>{e(doc.supplier_name or doc.supplier)}</dd>"
		f"<dt>ที่อยู่ :</dt><dd>{e(joined(supplier.address_line1, supplier.address_line2))}"
		f"<br>{e(joined(supplier.city, supplier.county, supplier.state, supplier.pincode))}</dd>"
		f'<dt class="po-gap">เลขที่ภาษี :</dt><dd class="po-gap">{e(supplier.tax_id) or "-"}'
		f"&nbsp; สาขา : {e(branch_of(supplier.branch_code)) if doc.supplier_address else '-'}</dd>"
		f"<dt>โครงการ :</dt><dd>{e(joined(project, '-' if project and doc.project else '', doc.project)) or '-'}</dd>"
		"</dl>"
	)


def party4(doc, supplier, project):
	"""รูปแบบที่ 4 (ตามผู้ใช้): ผู้ขาย 1 บรรทัด (ยาวขึ้นบรรทัดใหม่) / ที่อยู่ 3 บรรทัดเสมอ (ที่อยู่ 1, ที่อยู่ 2, ต. อ. จ. รหัสไปรษณีย์)
	(ไม่มีที่อยู่ 2 = ข้ามบรรทัดนั้น) / เลขที่ภาษี 1 บรรทัด / โครงการจองไว้ 2 บรรทัด ระยะบรรทัดชิด"""
	lines = [
		supplier.address_line1,
		supplier.address_line2,
		joined(supplier.city, supplier.county, supplier.state, supplier.pincode),
	]
	# ไม่มีที่อยู่ 2 = ไม่เว้นบรรทัดว่าง (ผู้ใช้ 2026-11-19)
	address = "".join(f"<div>{e(x)}</div>" for x in lines if x) or "-"
	tax = f"{e(supplier.tax_id) or '-'}&nbsp; สาขา : {e(branch_of(supplier.branch_code)) if doc.supplier_address else '-'}"
	proj = e(joined(project, "-" if project and doc.project else "", doc.project)) or "-"
	return (
		'<dl class="po-party po-party4">'
		f"<dt>ผู้ขาย :</dt><dd>{e(doc.supplier_name or doc.supplier)}</dd>"
		f'<dt>ที่อยู่ :</dt><dd class="po-l3">{address}</dd>'
		f"<dt>เลขที่ภาษี :</dt><dd>{tax}</dd>"
		f'<dt>โครงการ :</dt><dd class="po-l2">{proj}</dd>'
		"</dl>"
	)


def items_table(doc):
	rows = []
	for row in doc.items:
		desc = " ".join(strip_html_tags(row.description or "").split())
		show_desc = desc and desc.strip() != (row.item_name or "").strip()
		rows.append(
			"<tr>"
			f'<td class="c-idx">{row.idx}</td>'
			f'<td class="c-item"><b>{e(row.item_name or row.item_code)}</b>'
			+ (f'<div class="po-desc">{e(desc)}</div>' if show_desc else "")
			+ "</td>"
			f'<td class="c-num">{qty(row.qty)}</td>'
			f'<td class="c-uom">{e(row.uom)}</td>'
			f'<td class="c-num">{money(row.rate)}</td>'
			f'<td class="c-num">{money(row.amount)}</td>'
			"</tr>"
		)
	return f'<table class="po-items">{COLS}<tbody>{"".join(rows)}</tbody></table>'


# หัวตารางอยู่ในหัวกระดาษ (ซ้ำทุกหน้าแบบเดียวกันทั้งจอและ PDF) ไม่ใช้ <thead> ในเนื้อหา:
# Chrome ซ้ำ <thead> ข้ามคอลัมน์ของ paginate เฉพาะตอนพิมพ์ แถวต่อหน้าของ PDF จึงไม่ตรงกับตัวอย่าง
COLS = (
	'<colgroup><col class="w-idx"><col><col class="w-qty"><col class="w-uom">'
	'<col class="w-rate"><col class="w-amount"></colgroup>'
)
TABLE_HEAD = (
	f'<table class="po-items po-items-head ec-hide-if-empty">{COLS}'
	'<tr><th></th><th>รายการ / รายละเอียด</th><th class="c-num">จำนวน</th>'
	'<th class="c-uom">หน่วย</th><th class="c-num">ราคาต่อหน่วย</th><th class="c-num">จำนวนเงิน</th></tr></table>'
)


def footer(doc):
	wh = (
		frappe.db.get_value(
			"Warehouse",
			doc.set_warehouse,
			[
				"address_line_1",
				"address_line_2",
				"city",
				"state",
				"pin",
				"mobile_no",
				"phone_no",
				"custom_map",
				"custom_receiver_primary",
				"custom_receiver_secondary",
			],
			as_dict=True,
		)
		if doc.set_warehouse
		else None
	) or frappe._dict()
	phones = [
		joined(
			f"โทร. {wh.mobile_no}" if wh.mobile_no else "",
			f"( {wh.custom_receiver_primary} )" if wh.custom_receiver_primary else "",
		),
		joined(
			f"โทร. {wh.phone_no}" if wh.phone_no else "",
			f"( {wh.custom_receiver_secondary} )" if wh.custom_receiver_secondary else "",
		),
	]
	place = [wh.address_line_1, wh.address_line_2, joined(wh.city, wh.state, wh.pin), *phones]
	issuer = frappe.db.get_value("User", frappe.session.user, "full_name") or "-"
	totals = [
		("จำนวนเงินที่ชำระ", doc.get("custom_paid_amount")),
		("มูลค่าก่อนภาษี", doc.net_total),
		(VAT_LABEL, doc.total_taxes_and_charges),
	]
	sign_blank = '<div class="po-sign-line"></div><div class="po-sign-name">(<i></i>)</div><div class="po-sign-date">วันที่ <i></i></div>'
	return (
		'<div class="po-foot">'
		f'<div class="po-words"><b>ตัวอักษร</b>( {e(doc.get("custom_in_words_th"))} )</div>'
		'<div class="po-sum">'
		'<div class="po-place"><b>สถานที่จัดส่ง</b>'
		+ "".join(f"<span>{e(x)}</span>" for x in place if x)
		+ "</div>"
		+ (
			f'<div class="po-map"><b>แผนที่</b>{qr_svg(wh.custom_map)}</div>'
			if wh.custom_map
			else '<div class="po-map"></div>'
		)
		+ '<div class="po-totals">'
		f'<div class="po-grand"><span>จำนวนเงินทั้งสิ้น</span><b>{money(doc.grand_total)}&nbsp; บาท</b></div>'
		+ "".join(
			f"<div><b>{label}</b><span>{money(value)}&nbsp; บาท</span></div>" for label, value in totals
		)
		+ "</div></div>"
		'<div class="po-signs">'
		'<div class="po-sign"><b>ผู้ออกเอกสาร</b><div class="po-sign-line"></div>'
		f'<div class="po-sign-name">({e(issuer)})</div></div>'
		f'<div class="po-sign"><b>ผู้อนุมัติ</b>{sign_blank}</div>'
		'<div class="po-sign"><b>ตราประทับ</b></div>'
		f'<div class="po-sign"><b>ผู้รับเอกสาร</b>{sign_blank}</div>'
		'<div class="po-sign"><b>ตราประทับ (ถ้ามี)</b></div>'
		"</div></div>"
	)


CSS = """
.print-format { margin-top: 0mm; margin-bottom: 0mm; margin-left: 0mm; margin-right: 0mm; padding: 0; }
.ec-doc { font-family: "EC Font", sans-serif; font-size: 12px; line-height: 1.5; color: #000;
	text-rendering: geometricPrecision; font-variant-numeric: tabular-nums; }
.ec-doc b { font-weight: 700; }
.po-head { padding-bottom: 5mm; }
.po-top { display: grid; grid-template-columns: 25mm 1fr auto; gap: 0 5mm; align-items: start; }
.po-logo img { display: block; width: 25mm; height: 25mm; object-fit: contain; object-position: left center; }
.po-company { display: flex; flex-direction: column; font-size: 11px; line-height: 1.55; }
.po-company b { font-size: 13px; }
.po-inline span + span { margin-left: 6px; }
.po-title { text-align: right; }
.po-title h1 { margin: 0; font-size: 26px; line-height: 1.55; font-weight: 700; }
.po-sub { font-size: 15px; font-weight: 600; }
.po-sub b { margin-left: 10px; }
.po-pageno { font-size: 11px; }
.po-parties { display: grid; grid-template-columns: 1fr 76mm; gap: 6mm; margin-top: 3mm; }
.po-party, .po-box { display: grid; margin: 0; row-gap: 1px; }
.po-party { grid-template-columns: 20mm 1fr; font-size: 13px; }
.po-party dt, .po-box dt { font-weight: 700; }
.po-party dd, .po-box dd { margin: 0; }
.po-party .po-gap { margin-top: 3mm; }
.po-box { grid-template-columns: 25mm 1fr; padding: 4mm 6mm; border-radius: 6px; background: #e8f0fe; font-size: 13px; align-content: start; }
.po-items { width: 100%; border-collapse: collapse; table-layout: fixed; font-size: 12px; }
.po-items .w-idx { width: 14mm; } .po-items .w-qty { width: 24mm; } .po-items .w-uom { width: 18mm; }
.po-items .w-rate { width: 28mm; } .po-items .w-amount { width: 30mm; }
.po-items th { padding: 2.5mm 2mm; background: #e8f0fe; color: #000; font-weight: 700; text-align: left; font-size: 13px; border: 0; }
.po-items td { padding: 2.5mm 2mm; border-bottom: 1px solid #bfbfbf; vertical-align: top; }
.po-items tr { break-inside: avoid; page-break-inside: avoid; }
.po-items .c-idx { text-align: center; } .po-items .c-num { text-align: right; } .po-items .c-uom { text-align: center; }
.po-items .c-item b { font-weight: 700; }
.po-desc { color: #444; font-size: 11px; white-space: pre-line; }
.po-foot { padding-top: 4mm; }
.po-words { text-align: right; font-size: 13px; margin-bottom: 2mm; }
.po-words b { margin-right: 8px; }
.po-sum { display: grid; grid-template-columns: 60mm 1fr 92mm; gap: 4mm; align-items: start; }
.po-place { display: flex; flex-direction: column; font-size: 13px; }
.po-map { display: flex; flex-direction: column; align-items: center; font-size: 12px; }
.po-map svg { display: block; margin-top: 1mm; }
.po-totals { display: flex; flex-direction: column; gap: 1px; font-size: 12px; }
.po-totals > div { display: flex; justify-content: space-between; padding: 0 4mm; }
.po-totals .po-grand { margin-bottom: 3mm; padding: 2.5mm 4mm; border-radius: 6px; background: #e8f0fe; font-size: 15px; font-weight: 700; }
.po-signs { display: grid; grid-template-columns: repeat(5, 1fr); gap: 3mm; margin-top: 5mm; padding-top: 2mm;
	border-top: 1px solid #bfbfbf; text-align: center; font-size: 12px; }
.po-sign { display: flex; flex-direction: column; align-items: center; min-height: 40mm; }
.po-sign-line { width: 100%; margin-top: 22mm; border-bottom: 1px solid #000; }
.po-sign-name { margin-top: 2mm; }
.po-sign-name i, .po-sign-date i { display: inline-block; width: 26mm; border-bottom: 1px solid #000; }
.po-sign-date { margin-top: 3mm; }
"""


COPIES = {"original": "ต้นฉบับ", "copy": "สำเนา"}


def copies_of(value=None):
	"""ฉบับที่พิมพ์จาก ?copies=original,copy (หน้าพิมพ์ /printview และ download_pdf ส่งต่อ query มาที่ form_dict) ไม่ระบุ = ต้นฉบับ"""
	value = value if value is not None else (frappe.form_dict.get("copies") if frappe.form_dict else None)
	keys = [k.strip() for k in str(value or "").split(",") if k.strip() in COPIES]
	return [COPIES[k] for k in dict.fromkeys(keys)] or [COPIES["original"]]


def render_purchase_order(doc, copies=None, style=2):
	"""หน้าเอกสาร (ไม่รวม <html>) สำหรับ Print Format `Purchase Order TH` (style 2) / `TH 3` (style 3) / `TH 4` (style 4) (jinja method)"""
	if isinstance(doc, str):
		doc = frappe.get_doc("Purchase Order", doc)
	labels = "|".join(copies_of(copies))
	fonts = contract_terms.font_css("Noto Sans Thai", True)
	if int(style or 2) == 4:
		d = data_of(doc)
		return (
			f"<style>{fonts}\n{CSS}\n{CSS3}\n{CSS4}\n{contract_terms.SHEET_CSS}</style>"
			f'<div id="ec-src" data-page="210 297" data-margins="{MARGINS}" data-copies="{e(labels)}">'
			f'<div class="ec-src-head">{header(doc, 4)}<div class="po3">{TABLE_HEAD4}</div></div>'
			f'<div class="ec-src-foot-last">{footer4(doc, d)}</div>'
			f'<div class="ec-main">{items3(doc)}</div></div>'
			'<div id="ec-pages"></div>' + contract_terms.PAGINATE_SCRIPT()
		)
	if int(style or 2) == 3:
		d = data_of(doc)
		return (
			f"<style>{fonts}\n{CSS3}\n{contract_terms.SHEET_CSS}</style>"
			f'<div id="ec-src" data-page="210 297" data-margins="{MARGINS_TH_3}" data-copies="{e(labels)}">'
			f'<div class="ec-src-head">{header3(doc, d)}</div>'
			f'<div class="ec-src-foot-last">{footer3(doc, d)}</div>'
			f'<div class="ec-main">{items3(doc)}</div></div>'
			'<div id="ec-pages"></div>' + contract_terms.PAGINATE_SCRIPT()
		)
	return (
		f"<style>{fonts}\n{CSS}\n{contract_terms.SHEET_CSS}</style>"
		f'<div id="ec-src" data-page="210 297" data-margins="{MARGINS}" data-copies="{e(labels)}">'
		f'<div class="ec-src-head">{header(doc)}{TABLE_HEAD}</div>'
		f'<div class="ec-src-foot-last">{footer(doc)}</div>'
		f'<div class="ec-main">{items_table(doc)}</div></div>'
		'<div id="ec-pages"></div>' + contract_terms.PAGINATE_SCRIPT()
	)


# ---------------------------------------------------------------- รูปแบบที่ 3 (2026-11-19 ปรับให้สวยขึ้น ข้อมูลเดียวกับรูปแบบที่ 2)
# แนวทาง: ลำดับชั้นตัวอักษรชัด (ชื่อบริษัท/ชื่อเอกสารเด่น รายละเอียดเทาเล็ก) สีหลักกรมท่าสีเดียว + เทาอ่อน
# ข้อมูลจัดเป็นกล่อง 2 กล่องที่หัวกระดาษ (ผู้ขาย | รายละเอียดเอกสาร) ป้ายชื่อเล็กสีเทาเหนือค่า อ่านง่ายกว่าป้าย:ค่าในบรรทัดเดียว
# ตาราง: หัวกรมท่าตัวขาว แถวสลับสีจาง ตัวเลขชิดขวาแบบตัวเลขกว้างเท่ากัน / ท้ายเอกสาร: ยอดรวมแถบกรมท่า ตัวอักษรในกล่อง
# ช่องลงชื่อ 3 คน (ผู้ออก ผู้อนุมัติ ผู้รับ) + กรอบตราประทับเส้นประ 2 ช่อง ท้ายกระดาษมีเลขที่เอกสาร + เลขหน้า

NAVY = "#17233f"


def data_of(doc):
	company = (
		frappe.db.get_value(
			"Company",
			doc.company,
			["company_logo", "custom_company_address", "tax_id", "phone_no", "email", "website"],
			as_dict=True,
		)
		or frappe._dict()
	)
	supplier = (
		frappe.db.get_value(
			"Address",
			doc.supplier_address,
			["address_line1", "address_line2", "city", "county", "state", "pincode", "tax_id", "branch_code"],
			as_dict=True,
		)
		if doc.supplier_address
		else None
	) or frappe._dict()
	wh = (
		frappe.db.get_value(
			"Warehouse",
			doc.set_warehouse,
			[
				"warehouse_name",
				"address_line_1",
				"address_line_2",
				"city",
				"state",
				"pin",
				"mobile_no",
				"phone_no",
				"custom_map",
				"custom_receiver_primary",
				"custom_receiver_secondary",
			],
			as_dict=True,
		)
		if doc.set_warehouse
		else None
	) or frappe._dict()
	return frappe._dict(
		company=company,
		title=(
			frappe.db.get_value("Address", doc.billing_address, "address_title")
			if doc.billing_address
			else ""
		)
		or doc.company,
		logo=image_data_uri(company.company_logo) if company.company_logo else "",
		supplier=supplier,
		project=frappe.db.get_value("Project", doc.project, "project_name") if doc.project else "",
		wh=wh,
		issuer=frappe.db.get_value("User", frappe.session.user, "full_name") or "",
	)


def field3(label, value, cls=""):
	return f'<div class="f {cls}"><span>{label}</span><b>{value or "-"}</b></div>'


def header3(doc, d):
	c = d.company
	contact = " · ".join(
		x
		for x in (
			c.tax_id and f"เลขประจำตัวผู้เสียภาษี {e(c.tax_id)}",
			c.phone_no and f"โทร {e(c.phone_no)}",
		)
		if x
	)
	web = " · ".join(x for x in (e(c.email), e(c.website)) if x)
	s = d.supplier
	project = joined(d.project, f"({doc.project})" if doc.project else "")
	return (
		'<div class="po3"><div class="h3-top">'
		+ (f'<img class="h3-logo" src="{d.logo}" alt="">' if d.logo else "")
		+ '<div class="h3-co">'
		f"<b>{e(d.title)}</b>"
		f"<span>{e(' '.join(str(c.custom_company_address or '').split()))}</span>"
		+ (f"<span>{contact}</span>" if contact else "")
		+ (f"<span>{web}</span>" if web else "")
		+ "</div>"
		'<div class="h3-doc">'
		'<span class="h3-copy copy-label">ต้นฉบับ</span>'
		f"<h1>{TITLE}</h1>"
		'<div class="h3-en">PURCHASE ORDER</div>'
		"</div></div>"
		'<div class="h3-cards">'
		'<div class="h3-card"><div class="h3-cap">ผู้ขาย</div>'
		f'<div class="h3-name">{e(doc.supplier_name or doc.supplier)}</div>'
		f"<div>{e(joined(s.address_line1, s.address_line2))}</div>"
		f"<div>{e(joined(s.city, s.county, s.state, s.pincode))}</div>"
		f'<div class="h3-muted">เลขประจำตัวผู้เสียภาษี {e(s.tax_id) or "-"}'
		f"{' · ' + e(branch_of(s.branch_code)) if doc.supplier_address else ''}</div>"
		"</div>"
		'<div class="h3-card h3-meta">'
		+ field3("เลขที่", f'<span class="h3-no">{e(doc.name)}</span>')
		+ field3("วันที่", be_date(doc.transaction_date))
		+ field3("กำหนดส่ง", be_date(doc.schedule_date))
		+ field3("การชำระเงิน", e(doc.payment_terms_template))
		+ field3("อ้างอิง", e(doc.get("po_no") or doc.get("amended_from")))
		+ field3("หน้า", '<span class="page"></span> / <span class="topage"></span>')
		+ field3("โครงการ", e(project), "is-wide")
		+ "</div></div>"
		f'<table class="t3 t3-head ec-hide-if-empty">{COLS3}<tr><th class="c-idx">#</th><th>รายการ</th><th class="c-num">จำนวน</th>'
		'<th class="c-uom">หน่วย</th><th class="c-num">ราคา/หน่วย</th><th class="c-num">จำนวนเงิน</th></tr></table>'
		"</div>"
	)


COLS3 = (
	'<colgroup><col style="width:10mm"><col><col style="width:22mm"><col style="width:17mm">'
	'<col style="width:25mm"><col style="width:29mm"></colgroup>'
)


def items3(doc):
	rows = []
	for row in doc.items:
		desc = " ".join(strip_html_tags(row.description or "").split())
		show_desc = desc and desc.strip() != (row.item_name or "").strip()
		rows.append(
			"<tr>"
			f'<td class="c-idx">{row.idx}</td>'
			f'<td><div class="t3-item">{e(row.item_name or row.item_code)}</div>'
			f'<div class="t3-code">{e(row.item_code)}{" · " + e(desc) if show_desc else ""}</div></td>'
			f'<td class="c-num">{qty(row.qty)}</td>'
			f'<td class="c-uom">{e(row.uom)}</td>'
			f'<td class="c-num">{money(row.rate)}</td>'
			f'<td class="c-num c-amt">{money(row.amount)}</td>'
			"</tr>"
		)
	return f'<div class="po3"><table class="t3">{COLS3}<tbody>{"".join(rows)}</tbody></table></div>'


def footer3(doc, d):
	wh = d.wh
	phones = [
		joined(wh.mobile_no, f"({wh.custom_receiver_primary})" if wh.custom_receiver_primary else ""),
		joined(wh.phone_no, f"({wh.custom_receiver_secondary})" if wh.custom_receiver_secondary else ""),
	]
	place = [wh.address_line_1, wh.address_line_2, joined(wh.city, wh.state, wh.pin)]
	phone = " · ".join(p for p in phones if p)
	totals = [
		("มูลค่าก่อนภาษี", doc.net_total),
		(VAT_LABEL, doc.total_taxes_and_charges),
		("จำนวนเงินที่ชำระ", doc.get("custom_paid_amount")),
	]
	sign = lambda role, name="": (
		f'<div class="s3"><div class="s3-line"></div><b>{role}</b>'
		f"<span>({e(name) if name else '<i></i>'})</span><span>วันที่ <i></i></span></div>"
	)
	return (
		'<div class="po3"><div class="f3">'
		'<div class="f3-left">'
		f'<div class="f3-words"><span>จำนวนเงิน (ตัวอักษร)</span><b>{e(doc.get("custom_in_words_th")) or "-"}</b></div>'
		'<div class="f3-ship">'
		'<div><div class="h3-cap">สถานที่จัดส่ง</div>'
		+ (f'<div class="h3-name">{e(wh.warehouse_name)}</div>' if wh.warehouse_name else "")
		+ "".join(f"<div>{e(x)}</div>" for x in place if x)
		+ (f'<div class="h3-muted">โทร {e(phone)}</div>' if phone else "")
		+ "</div>"
		+ (f'<div class="f3-qr">{qr_svg(wh.custom_map, 20)}<span>แผนที่</span></div>' if wh.custom_map else "")
		+ "</div></div>"
		'<div class="f3-totals">'
		+ "".join(f"<div><span>{label}</span><b>{money(value)}</b></div>" for label, value in totals)
		+ f'<div class="f3-grand"><span>จำนวนเงินทั้งสิ้น</span><b>{money(doc.grand_total)} <small>บาท</small></b></div>'
		"</div></div>"
		'<div class="s3-row">'
		+ sign("ผู้ออกเอกสาร", d.issuer)
		+ sign("ผู้อนุมัติ")
		+ '<div class="s3 s3-stamp"><div>ตราประทับบริษัท</div></div>'
		+ sign("ผู้รับเอกสาร (ผู้ขาย)")
		+ '<div class="s3 s3-stamp"><div>ตราประทับผู้ขาย</div></div>'
		+ "</div>"
		f'<div class="f3-meta"><span>{e(doc.name)}</span><span>หน้า <span class="page"></span> / <span class="topage"></span></span></div>'
		"</div>"
	)


CSS3 = """
.print-format { margin-top: 0mm; margin-bottom: 0mm; margin-left: 0mm; margin-right: 0mm; padding: 0; }
.ec-doc { font-family: "EC Font", sans-serif; font-size: 11.5px; line-height: 1.5; color: #1f2937;
	text-rendering: geometricPrecision; font-variant-numeric: tabular-nums; }
.po3 b { font-weight: 700; color: #111827; }
.po3 .h3-muted { color: #6b7280; }
.po3 .h3-cap { margin-bottom: 1mm; font-size: 10px; font-weight: 700; letter-spacing: .06em; color: #6b7280; }
.po3 .h3-name { font-size: 13px; font-weight: 700; color: #111827; }
.h3-top { display: flex; align-items: flex-start; gap: 5mm; padding-bottom: 4mm; border-bottom: 2px solid #17233f; }
.h3-logo { flex: none; width: 20mm; height: 20mm; object-fit: contain; object-position: left top; }
.h3-co { flex: 1; min-width: 0; display: flex; flex-direction: column; font-size: 10.5px; line-height: 1.55; color: #4b5563; }
.h3-co b { font-size: 15px; line-height: 1.35; margin-bottom: .5mm; color: #17233f; }
.h3-doc { flex: none; text-align: right; }
.h3-doc h1 { margin: 1mm 0 0; font-size: 28px; line-height: 1.15; font-weight: 700; color: #17233f; }
.h3-en { margin-top: .5mm; font-size: 10px; font-weight: 600; letter-spacing: .28em; color: #6b7280; }
.h3-copy { display: inline-block; padding: .6mm 3.5mm; border: 1px solid #17233f; border-radius: 99px;
	font-size: 10.5px; font-weight: 700; color: #17233f; }
.h3-cards { display: grid; grid-template-columns: 1fr 1fr; gap: 4mm; margin: 4mm 0; }
.h3-card { padding: 3mm 4mm; border: 1px solid #e5e7eb; border-radius: 3mm; background: #f8fafc; line-height: 1.55; }
.h3-meta { display: grid; grid-template-columns: 1.55fr 1fr 1fr; gap: 2mm 4mm; align-content: start; }
.h3-meta .f { display: flex; flex-direction: column; min-width: 0; }
.h3-meta .f > span { font-size: 10px; font-weight: 700; letter-spacing: .04em; color: #6b7280; }
.h3-meta .f > b { font-size: 12px; overflow-wrap: anywhere; }
.h3-meta .is-wide { grid-column: 1 / -1; }
.h3-no { color: #17233f; white-space: nowrap; }
.t3 { width: 100%; border-collapse: collapse; table-layout: fixed; }
/* สีกรมท่าที่ตัวตารางหัว ไม่ใช่ที่ช่อง: เส้นขอบช่องของ CSS พิมพ์ Frappe ทำให้เห็นรอยขาวระหว่างช่อง */
.t3-head { background: #17233f; border-radius: 2mm 2mm 0 0; overflow: hidden; }
.t3 th { padding: 2.2mm 2mm; background: transparent !important; color: #fff !important; font-size: 11px; font-weight: 700;
	text-align: left; border: 0 !important; box-shadow: none !important; }
.t3, .t3 tr, .t3 td { border-left: 0 !important; border-right: 0 !important; }
.t3 td { padding: 2mm; border-bottom: 1px solid #e5e7eb; vertical-align: top; }
.t3 tbody tr:nth-child(even) td { background: #f8fafc; }
.t3 tr { break-inside: avoid; page-break-inside: avoid; }
.t3 .c-idx { text-align: center; color: #6b7280; }
.t3 .c-num { text-align: right; white-space: nowrap; }
.t3 .c-uom { text-align: center; }
.t3 .c-amt { font-weight: 700; color: #111827; }
.t3-item { font-weight: 600; color: #111827; }
.t3-code { font-size: 9.5px; color: #6b7280; }
.f3 { display: grid; grid-template-columns: 1fr 72mm; gap: 5mm; padding-top: 4mm; border-top: 1px solid #e5e7eb; }
.f3-left { display: flex; flex-direction: column; gap: 3mm; min-width: 0; }
.f3-words { padding: 2.5mm 4mm; border-radius: 3mm; background: #f1f5f9; }
.f3-words span { display: block; font-size: 10px; font-weight: 700; letter-spacing: .04em; color: #6b7280; }
.f3-ship { display: flex; justify-content: space-between; gap: 4mm; line-height: 1.55; }
.f3-qr { flex: none; display: flex; flex-direction: column; align-items: center; font-size: 9.5px; color: #6b7280; }
.f3-qr svg { display: block; }
.f3-totals { display: flex; flex-direction: column; }
.f3-totals > div { display: flex; justify-content: space-between; gap: 4mm; padding: 1.3mm 3mm; border-bottom: 1px solid #f1f5f9; }
.f3-totals > div > span { color: #4b5563; }
.f3-totals .f3-grand { margin-top: 2mm; padding: 3mm; border: 0; border-radius: 2.5mm; background: #17233f; color: #fff; }
.f3-totals .f3-grand span, .f3-totals .f3-grand b { color: #fff; font-weight: 700; }
.f3-totals .f3-grand b { font-size: 15px; }
.f3-totals .f3-grand small { font-size: 10.5px; font-weight: 600; }
.s3-row { display: grid; grid-template-columns: 1fr 1fr 24mm 1fr 24mm; gap: 4mm; margin-top: 7mm; text-align: center; font-size: 10.5px; }
.s3 { display: flex; flex-direction: column; align-items: center; gap: .8mm; color: #4b5563; }
.s3-line { width: 100%; height: 14mm; border-bottom: 1px solid #9ca3af; }
.s3 b { margin-top: 1mm; font-size: 11px; }
.s3 i { display: inline-block; width: 22mm; border-bottom: 1px dotted #9ca3af; }
.s3-stamp > div { display: flex; align-items: center; justify-content: center; width: 24mm; height: 24mm;
	border: 1px dashed #cbd5e1; border-radius: 50%; font-size: 9px; color: #9ca3af; line-height: 1.3; }
.f3-meta { display: flex; justify-content: space-between; margin-top: 4mm; padding-top: 1.5mm; border-top: 1px solid #e5e7eb;
	font-size: 9px; color: #9ca3af; }
"""


# ---------------------------------------------------------------- รูปแบบที่ 4 (2026-11-19 ตามผู้ใช้)
# หัวกระดาษ = รูปแบบที่ 2 (ประหยัดที่ รองรับชื่อยาว) กล่องเลขที่เปลี่ยนเป็นเทาอ่อนมีขอบ ข้อมูลผู้ขายไม่มีพื้น
# ตาราง = รูปแบบที่ 3 แต่หัวตารางเทาอ่อน ตัวอักษรดำทั้งหมด (ประหยัดหมึก) / ท้ายเอกสาร: ยอดรวมทั้งสิ้นระดับเดียวกับตัวอักษร
# ใต้ยอดรวม = รายละเอียด (ก่อนภาษี ภาษี ที่ชำระ) ไม่มีเส้นคั่น ใต้ตัวอักษร = สถานที่จัดส่ง + QR / ช่องลงชื่อเตี้ยลง ไม่มีแถวท้ายกระดาษ

TABLE_HEAD4 = (
	f'<table class="t3 t4 t3-head ec-hide-if-empty">{COLS3}<tr><th class="c-idx">#</th><th>รายการ / รายละเอียด</th>'
	'<th class="c-num">จำนวน</th><th class="c-uom">หน่วย</th><th class="c-num">ราคาต่อหน่วย</th>'
	'<th class="c-num">จำนวนเงิน</th></tr></table>'
)


def footer4(doc, d):
	wh = d.wh
	phones = [
		joined(wh.mobile_no, f"({wh.custom_receiver_primary})" if wh.custom_receiver_primary else ""),
		joined(wh.phone_no, f"({wh.custom_receiver_secondary})" if wh.custom_receiver_secondary else ""),
	]
	place = [wh.address_line_1, wh.address_line_2, joined(wh.city, wh.state, wh.pin)]
	phone = " · ".join(p for p in phones if p)
	details = [
		("มูลค่าก่อนภาษี", doc.net_total),
		(VAT_LABEL, doc.total_taxes_and_charges),
		("จำนวนเงินที่ชำระ", doc.get("custom_paid_amount")),
	]
	issuer, approver = signers(doc)

	def sign(role, person=None, blank_date=True):
		person = person or {}
		img = f'<img class="s4-sig" src="{person["sig"]}" alt="">' if person.get("sig") else ""
		name = f"({e(person['name'])})" if person.get("name") else "(<i></i>)"
		date = person.get("date")
		return (
			f'<div class="s3"><div class="s3-line">{img}</div><b>{role}</b>'
			f"<span>{name}</span><span>วันที่ {e(date) if date else '<i></i>'}</span></div>"
		)

	return (
		'<div class="po3 po4"><div class="f4">'
		f'<div class="f4-words"><span>จำนวนเงิน (ตัวอักษร)</span><b>{e(doc.get("custom_in_words_th")) or "-"}</b></div>'
		f'<div class="f4-grand"><span>จำนวนเงินทั้งสิ้น</span><b>{money(doc.grand_total)} <small>บาท</small></b></div>'
		'<div class="f4-ship"><div><div class="f4-cap">สถานที่จัดส่ง</div>'
		+ (f"<b>{e(wh.warehouse_name)}</b>" if wh.warehouse_name else "")
		+ "".join(f"<div>{e(x)}</div>" for x in place if x)
		+ (f"<div>โทร {e(phone)}</div>" if phone else "")
		+ "</div>"
		+ (f'<div class="f3-qr">{qr_svg(wh.custom_map, 18)}<span>แผนที่</span></div>' if wh.custom_map else "")
		+ "</div>"
		'<div class="f4-detail">'
		+ "".join(f"<div><span>{label}</span><b>{money(value)}</b></div>" for label, value in details)
		+ "</div></div>"
		'<div class="s3-row">'
		+ sign("ผู้ออกเอกสาร", issuer)
		+ sign("ผู้อนุมัติ", approver)
		+ '<div class="s3 s3-stamp"><div>ตราประทับบริษัท</div></div>'
		+ sign("ผู้รับเอกสาร (ผู้ขาย)")
		+ '<div class="s3 s3-stamp"><div>ตราประทับผู้ขาย</div></div>'
		+ "</div></div>"
	)


def person_of(user):
	"""ชื่อ + รูปลายเซ็นของผู้ใช้ (DocType Signature ชื่อ = User ชุดเดียวกับผู้จัดทำ/ผู้อนุมัติของใบขอซื้อ) ไม่มี Signature = ชื่อจาก User"""
	if not user:
		return {}
	sig = frappe.db.get_value("Signature", user, ["full_name", "signature"], as_dict=True) or frappe._dict()
	name = sig.full_name or frappe.db.get_value("User", user, "full_name") or user
	return {"name": name, "sig": image_data_uri(sig.signature) if sig.signature else ""}


def submitted(doc):
	"""ผู้ยืนยัน (Submit) + เวลา จากประวัติ (Version ที่ docstatus 0 → 1) ไม่พบ = ผู้แก้ไขล่าสุด"""
	import json

	for v in frappe.get_all(
		"Version",
		filters={"ref_doctype": doc.doctype, "docname": doc.name},
		fields=["owner", "creation", "data"],
		order_by="creation asc",
	):
		try:
			changed = json.loads(v.data or "{}").get("changed") or []
		except ValueError:
			continue
		if any(c[0] == "docstatus" and c[2] == 1 for c in changed if len(c) == 3):
			return v.owner, v.creation
	return doc.modified_by, doc.modified


def signers(doc):
	"""ช่องลงชื่อ (ตกลง 2026-11-19): ผู้ออกเอกสาร = ผู้ส่งลงนาม (ไม่มี = ผู้สร้าง) ลงวันที่ตามวันที่เอกสาร
	ลายเซ็นผู้ออกแสดงตั้งแต่ส่งลงนาม (รอลงนาม) / ผู้อนุมัติ = ผู้ลงนาม (consbiz/doc_approval.py, รวมบันทึกการลงนามแทน)
	ลงวันที่ที่ลงนาม แสดงเมื่อยืนยันแล้ว ใบเก่าที่ไม่มีผู้ลงนาม = ผู้ Submit จากประวัติ"""
	issuer = person_of(doc.get("custom_sent_by") or doc.owner)
	issuer["date"] = be_date(doc.transaction_date)
	sent = doc.get("custom_approval_status") in ("Pending", "Approved")
	if doc.docstatus != 1:
		if not sent:
			issuer["sig"] = ""
		return issuer, {}
	if doc.get("custom_signed_by"):
		user, when = doc.custom_signed_by, doc.get("custom_signed_on") or doc.modified
	else:
		user, when = submitted(doc)
	approver = person_of(user)
	approver["date"] = be_date(when)
	return issuer, approver


CSS4 = """
/* 2026-11-19 รอบ 3 (ตามผู้ใช้): ตัวอักษรขนาดเท่าแบบเดิม (~11px) ระยะบรรทัด/ตัวอักษรห่างขึ้น ข้อมูลตัวดำ ไม่มีสีตกแต่งอื่น
   หัวตาราง + ยอดรวมทั้งสิ้น = พื้นกรมท่าเข้มตัวขาว (แบบรูปแบบที่ 3) กล่องเลขที่พื้นเทาอ่อนไม่มีเส้นขอบ เส้นช่องเซ็นเทากลาง */
.ec-doc { font-size: 11px; line-height: 1.6; letter-spacing: .012em; color: #000; }
.po-head { padding-bottom: 3.5mm; }
.po-logo img { width: 22mm; height: 22mm; }
.po-company { font-size: 10.5px; line-height: 1.6; }
.po-company b { font-size: 12.5px; }
/* ระยะบรรทัดสูงพอให้วรรณยุกต์/สระบน (สั่ง) ไม่เลยขอบบนของพื้นที่พิมพ์ที่ตัดส่วนเกิน */
.po-title h1 { font-size: 24px; line-height: 1.55; }
.po-sub { font-size: 13.5px; }
.po-pageno { font-size: 10.5px; }
.po-parties { margin-top: 3mm; gap: 5mm; }
.po-party { font-size: 11.5px; row-gap: .5mm; }
.po-party .po-gap { margin-top: 2mm; }
.po-box { font-size: 11.5px; row-gap: .5mm; padding: 3mm 5mm; background: #f3f4f6; border: 0; border-radius: 2.5mm; }
.po3 b, .t3 td, .t3-item, .t3 .c-amt { color: #000; }
.t3.t3-head, .t4.t3-head { background: #17233f; border-radius: 2mm 2mm 0 0; }
.t3 th { padding: 2mm; color: #fff !important; font-size: 11px; }
.t3 td { padding: 1.8mm 2mm; border-bottom-color: #e3e6eb; font-size: 11px; }
.t3 tbody tr:nth-child(even) td { background: #f8f9fb; }
.t3 .c-idx { color: #000; }
.t3-item { font-weight: 600; }
.t3-code { font-size: 9.5px; color: #555; }
.f4 { display: grid; grid-template-columns: 1fr 70mm; gap: 3mm 5mm; padding-top: 3.5mm; }
.f4-words { display: flex; flex-direction: column; justify-content: center; padding: 2mm 4mm; border-radius: 2mm; background: #f3f4f6; }
.f4-words b { font-size: 11.5px; }
.f4-words span, .f4-cap { font-size: 9.5px; font-weight: 700; letter-spacing: .05em; color: #555; }
.f4-grand { display: flex; align-items: center; justify-content: space-between; gap: 4mm; padding: 2.5mm 3.5mm;
	border: 0; border-radius: 2mm; background: #17233f; }
.f4-grand span, .f4-grand b, .f4-grand small { font-weight: 700; color: #fff; }
.f4-grand b { font-size: 15px; }
.f4-grand small { font-size: 10.5px; font-weight: 600; }
.f4-ship { display: flex; justify-content: space-between; gap: 4mm; line-height: 1.55; }
.f4-detail { display: flex; flex-direction: column; gap: .4mm; padding: 0 3.5mm; }
.f4-detail > div { display: flex; justify-content: space-between; gap: 4mm; }
.f3-qr { color: #555; }
/* ช่องตราประทับกว้าง 32 มม. (ตราบริษัททั่วไป 3-4.5 ซม. ไม่ทับช่องชื่อ) ช่องชื่อ ~36 มม. */
.s3-row { margin-top: 4mm; font-size: 10.5px; grid-template-columns: 1fr 1fr 32mm 1fr 32mm; gap: 3mm; align-items: end; }
.s3 { color: #000; gap: .3mm; }
/* เส้นเซ็นเทากลาง (อ่อนกว่าตัวอักษร แต่ถ่ายเอกสารแล้วยังเห็น) */
.s3-line { position: relative; height: 9mm; border-bottom: 1px solid #8a8f98; }
/* ลายเซ็นวางทับเส้น (ล้นขึ้นบนได้ ไม่ดันแถว) */
.s4-sig { position: absolute; left: 50%; bottom: -1.5mm; transform: translateX(-50%); max-width: 100%; height: 13mm; object-fit: contain; }
.s3 b { margin-top: .6mm; font-size: 11px; }
.s3 i { display: inline-block; width: 30mm; border-bottom: 1px dotted #8a8f98; }
/* วงรีบอกตำแหน่งตราประทับ กว้าง 32 สูง 22 มม. = สูงเท่าช่องลงชื่อ แถวไม่สูงเกิน (ตราจริงกลมประทับเลยขอบบน-ล่างได้) */
.s3-stamp > div { width: 32mm; height: 22mm; border-color: #c3c8d0; color: #8a8f98; }
.s3-stamp { align-self: center; }
/* ป้ายฉบับ (ต้นฉบับ/สำเนา) */
.po-sub .po-badge { display: inline-block; margin-left: 8px; padding: .4mm 3.5mm; border-radius: 99px;
	background: #17233f; color: #fff; font-size: 12px; font-weight: 700; line-height: 1.5; vertical-align: 1px; }
/* ข้อมูลผู้ขาย: บรรทัดชิด ที่อยู่จอง 3 บรรทัด โครงการจอง 2 บรรทัด (ความสูงหัวกระดาษคงที่ทุกใบ) */
.po-party4 { line-height: 1.4; row-gap: .6mm; align-content: start; }
.po-party4 .po-l2 { min-height: calc(2 * 1.4em); }
"""
