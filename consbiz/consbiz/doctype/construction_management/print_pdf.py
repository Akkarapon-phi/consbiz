# Copyright (c) 2026, Siricons and contributors
# For license information, please see license.txt

# PDF ของงานพิมพ์แผนงาน (แท็บพิมพ์ในแอป ConsERP) สร้างจาก HTML เดียวกับที่ Preview แสดง
# HTML มาจากเบราว์เซอร์แล้วเปิดด้วย Chromium ฝั่ง server จึงรับเฉพาะแท็ก/แอตทริบิวต์ที่ print.js สร้าง
# ไม่มีสคริปต์ และไม่โหลดอะไรจากภายนอก (ฟอนต์ฝังเป็น base64) กันการอ่านไฟล์/URL ภายในเครื่อง

import base64
import re

import frappe
from bs4 import BeautifulSoup
from frappe import _
from frappe.utils import flt

MAX_HTML = 30 * 1024 * 1024
FONT_FILE = "NotoSansThai-Variable-thai.woff2"
FONT_URL = re.compile(r'url\("[^"()]*/' + re.escape(FONT_FILE) + r'"\)')
PAGE_ROUNDING_MM = 0.5
LOCAL_CLIP = re.compile(r"^url\(#[\w-]+\)$")
BLOCKED_CSS = ("url(", "@import", "expression(", "javascript:")

ALLOWED_TAGS = {
	"html", "head", "meta", "title", "style", "body", "section", "aside", "div", "span", "b", "i", "u",
	"h1", "small", "table", "tbody", "tr", "th", "td", "hr", "svg", "defs", "clippath", "g", "rect",
	"line", "text", "path", "circle",
}  # fmt: skip
ALLOWED_ATTRS = {
	"charset", "class", "id", "style", "rowspan", "x", "y", "x1", "x2", "y1", "y2", "cx", "cy", "r", "rx",
	"width", "height", "fill", "fill-opacity", "stroke", "stroke-width", "stroke-opacity",
	"stroke-dasharray", "d", "viewbox", "preserveaspectratio", "xmlns", "font-size", "font-weight",
	"text-anchor", "paint-order", "clip-path",
}  # fmt: skip


def check_print_html(html):
	"""ตรวจ HTML ของงานพิมพ์ ไม่ผ่าน = ValidationError (HTML จาก print.js ผ่านเสมอ)"""
	if len(html) > MAX_HTML:
		frappe.throw(_("งานพิมพ์ใหญ่เกินไป ให้ลดจำนวนแถวหรือจำนวนหน้า"))
	for tag in BeautifulSoup(html, "html5lib").find_all(True):
		if tag.name.lower() not in ALLOWED_TAGS:
			frappe.throw(_("งานพิมพ์มีส่วนที่ไม่รองรับ: {0}").format(tag.name))
		if tag.name.lower() == "style":
			# get_text() ของ BeautifulSoup คืนค่าว่างสำหรับ <style> ต้องอ่านเนื้อหาตรงๆ
			check_css(FONT_URL.sub("", tag.decode_contents()))
		for attr, value in tag.attrs.items():
			check_attr(tag.name, attr.lower(), " ".join(value) if isinstance(value, list) else str(value))


def check_attr(tag, attr, value):
	if attr not in ALLOWED_ATTRS:
		frappe.throw(_("งานพิมพ์มีส่วนที่ไม่รองรับ: {0} {1}").format(tag, attr))
	if attr == "clip-path":
		if not LOCAL_CLIP.match(value):
			frappe.throw(_("งานพิมพ์มีส่วนที่ไม่รองรับ: {0} {1}").format(tag, attr))
		return
	check_css(value)


def check_css(text):
	lowered = text.lower()
	if any(word in lowered for word in BLOCKED_CSS):
		frappe.throw(_("งานพิมพ์มีการอ้างถึงไฟล์ภายนอกที่ไม่รองรับ"))


def embed_font(html):
	path = frappe.get_app_path("consbiz", "public", "fonts", "noto-sans-thai", FONT_FILE)
	with open(path, "rb") as file:
		data = base64.b64encode(file.read()).decode()
	return FONT_URL.sub(f'url("data:font/woff2;base64,{data}")', html)


@frappe.whitelist(methods=["POST"])
def get_plan_pdf(name, html, paper_w, paper_h, margin):
	"""PDF ของงานพิมพ์แผนงาน name = Construction Management"""
	frappe.has_permission("Construction Management", "read", name, throw=True)
	check_print_html(html)
	width, height = min(max(flt(paper_w), 50), 1200), min(max(flt(paper_h), 50), 1200)
	gap = min(max(flt(margin), 0), 40)
	frappe.local.response.filename = "plan.pdf"
	frappe.local.response.filecontent = render_pdf(embed_font(html), width, height, gap)
	frappe.local.response.type = "pdf"


def render_pdf(html, width, height, margin):
	"""PDF ขนาดและขอบตามที่ส่งมา ผ่าน Chromium ตัวเดียวกับ Print Format
	ไม่ใช้ frappe.utils.pdf.get_chrome_pdf เพราะเอกสารที่ไม่มีหัว/ท้ายกระดาษถูกบังคับขอบบน-ล่าง 15 มม.
	งานพิมพ์ที่ออกแบบให้สูงพอดีขอบจึงล้นเป็นหน้าว่างทุกหน้า"""
	from frappe.utils.pdf import get_host_url
	from frappe.utils.pdf_generator.cdp_connection import CDPSocketClient
	from frappe.utils.pdf_generator.chrome_pdf_generator import ChromePDFGenerator
	from frappe.utils.pdf_generator.page import Page

	inch = lambda mm: mm / 25.4  # noqa: E731
	generator = ChromePDFGenerator()
	browser_id = frappe.generate_hash(length=10)
	generator.add_browser(browser_id)
	session = page = None
	try:
		if not generator._devtools_url:
			generator._set_devtools_url()
		session = CDPSocketClient(generator._devtools_url)
		session.connect()
		context, error = session.send("Target.createBrowserContext", {"disposeOnDetach": True})
		if error:
			raise RuntimeError(f"Error creating browser context: {error}")
		page = Page(session, context["browserContextId"], "body")
		page.is_print_designer = False
		page.set_tab_url(get_host_url())
		page.wait_for_navigate()
		page.set_content(html)
		page.wait_for_set_content()
		page.options = {
			"printBackground": True,
			"transferMode": "ReturnAsStream",
			"scale": 1,
			"preferCSSPageSize": False,
			"paperWidth": inch(width),
			"paperHeight": inch(height),
			"marginTop": inch(margin),
			# Chromium ปัดขนาดเป็นนิ้วลงเล็กน้อย เนื้อหาที่สูงพอดีหน้าจึงล้นเป็นหน้าว่าง
			"marginBottom": inch(max(margin - PAGE_ROUNDING_MM, 0)),
			"marginLeft": inch(margin),
			"marginRight": inch(margin),
		}
		return page.generate_pdf(raw=True)
	finally:
		for close in (page and page.close, session and session.disconnect):
			if close:
				try:
					close()
				except Exception:
					frappe.log_error("Plan PDF: failed to close Chromium page")
		generator.remove_browser(browser_id)
		generator._close_browser()
