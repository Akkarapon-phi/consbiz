# Copyright (c) 2026, Siricons and Contributors
# See license.txt

# PDF ของงานพิมพ์แผนงาน: รับเฉพาะ HTML แบบที่ print.js สร้าง ไม่ให้ Chromium ฝั่ง server โหลดไฟล์/URL อื่น

import frappe
from frappe.tests import IntegrationTestCase

from consbiz.consbiz.doctype.construction_management.print_pdf import FONT_FILE, check_print_html, embed_font

FONT = f'url("https://evil.example/x/{FONT_FILE}")'
PAGE = f"""<!doctype html><html><head><meta charset="utf-8"><title>แผน</title>
<style>@font-face {{ src: {FONT} format("woff2"); }} @page {{ size: 420mm 297mm; }}</style></head>
<body><section class="page"><div class="head head-app"><h1>แผน</h1></div>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10" preserveAspectRatio="xMidYMin meet">
<defs><clipPath id="a"><rect width="5" height="5" rx="1"/></clipPath></defs>
<g clip-path="url(#a)"><text x="1" y="1" font-size="7" text-anchor="middle" fill="#fff">1%</text></g></svg>
</section></body></html>"""


class IntegrationTestPlanPrintPdf(IntegrationTestCase):
	def test_generated_html_passes(self):
		check_print_html(PAGE)

	def test_blocks_anything_that_loads_or_runs(self):
		for bad in (
			'<script>fetch("file:///etc/passwd")</script>',
			'<iframe src="file:///etc/passwd"></iframe>',
			'<img src="http://169.254.169.254/">',
			'<link rel="stylesheet" href="http://internal/">',
			'<object data="file:///etc/passwd"></object>',
			'<div onclick="x()">a</div>',
			'<svg><image href="file:///etc/passwd"/></svg>',
			'<svg><use href="http://internal/#a"/></svg>',
			'<div style="background:url(http://internal/)">a</div>',
			"<style>@import 'http://internal/a.css';</style>",
			'<style>body { background: url("http://internal/"); }</style>',
			'<svg><g clip-path="url(http://internal/#a)"></g></svg>',
		):
			with self.subTest(bad=bad):
				self.assertRaises(frappe.ValidationError, check_print_html, PAGE.replace("</section>", f"{bad}</section>"))

	def test_font_is_embedded(self):
		html = embed_font(PAGE)
		self.assertNotIn("evil.example", html)
		self.assertIn("data:font/woff2;base64,", html)
