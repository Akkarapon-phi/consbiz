# Copyright (c) 2026, Siricons and contributors
# For license information, please see license.txt

# แผนตัดเหล็ก: รายการเหล็กที่ต้องตัด (รูปทรง + ขนาดด้าน + จำนวน) -> ความยาวตัด -> จัดตัดจากเหล็กที่มี
# - ความยาวตัด = ผลรวมด้าน (สูตรของ Bar Shape) - ระยะหักที่จุดดัด (ถ้าติ๊ก) + ระยะขอ แล้วปัดขึ้น
# - จัดตัดแยกตามประเภทเหล็กด้วย optimizer.py ทุกครั้งที่บันทึก ผลจึงตรงกับรายการเสมอ
# - เศษที่ยาวตั้งแต่ min_reusable นับเป็นเศษเก็บ ที่สั้นกว่านับเป็นเศษทิ้ง Loss % = เศษทิ้ง / เหล็กที่ใช้

import json
import math
import re

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt

from consbiz.consbiz.doctype.bar_cut_plan.optimizer import NotEnoughStock, plan_cuts
from consbiz.consbiz.doctype.bar_shape.bar_shape import DIMENSIONS
from consbiz.consbiz.doctype.rebar_type.rebar_type import nominal_mass
SETTINGS = {
	"use_bend_deduction": 1,
	"bend_45": 1,
	"bend_90": 2,
	"bend_135": 3,
	"bend_180": 4,
	"hook_90": 6,
	"hook_135": 10,
	"hook_180": 10,
	"round_up": 10,
}


class BarCutPlan(Document):
	def validate(self):
		self.set_cut_lengths()
		self.optimize()

	def set_cut_lengths(self):
		settings = {key: self.get(key) for key in SETTINGS}
		for row in self.items:
			if cint(row.qty) <= 0:
				frappe.throw(_("แถว {0}: จำนวนต้องมากกว่า 0").format(row.idx))
			row.cut_length = get_cut_length(row.shape, row.rebar_type, row, settings, row.idx)
			row.total_length = row.cut_length * cint(row.qty) / 1000
			row.weight = row.total_length * get_unit_weight(row.rebar_type)

	def optimize(self):
		self.patterns = []
		self.summary = []
		min_reusable = flt(self.min_reusable) * 1000
		for rebar_type in dict.fromkeys(row.rebar_type for row in self.items):
			pieces = [
				(int(row.cut_length), row.mark or f"#{row.idx}")
				for row in self.items
				if row.rebar_type == rebar_type
				for _ in range(cint(row.qty))
			]
			stocks = self.get_stocks(rebar_type)
			try:
				patterns = plan_cuts(pieces, stocks, int(flt(self.kerf)))
			except ValueError as e:
				frappe.throw(
					_("{0}: ชิ้นยาว {1} มม. ยาวกว่าเหล็กที่มีทุกความยาว (ยาวสุด {2} ม.)").format(
						rebar_type,
						", ".join(f"{length:,}" for length in e.args[0]),
						max(s[0] for s in stocks) / 1000,
					)
				)
			except NotEnoughStock as e:
				missing = ", ".join(f"{length:,} มม. x {count}" for length, count in e.args[0].items())
				frappe.throw(_("{0}: เหล็กที่มีไม่พอ ยังตัดไม่ได้ {1}").format(rebar_type, missing))
			self.add_results(rebar_type, patterns, min_reusable)
		self.set_totals()

	def get_stocks(self, rebar_type):
		"""เหล็กที่มีของประเภทนี้ [(ความยาว มม., จำนวน หรือ None)] ไม่ได้ระบุ = ความยาวมาตรฐานไม่จำกัด"""
		rows = [row for row in self.stock if row.rebar_type == rebar_type and flt(row.length) > 0]
		if rows:
			return [(round(flt(row.length) * 1000), cint(row.qty) or None) for row in rows]
		lengths = frappe.db.get_value("Rebar Type", rebar_type, "standard_lengths") or "10"
		return [(round(length * 1000), None) for length in parse_lengths(lengths)]

	def add_results(self, rebar_type, patterns, min_reusable):
		unit_weight = get_unit_weight(rebar_type)
		totals = {}
		for pattern in patterns:
			stock, bars, offcut = pattern["stock"], pattern["bars"], pattern["offcut"]
			reusable = min_reusable > 0 and offcut >= min_reusable
			self.append(
				"patterns",
				{
					"rebar_type": rebar_type,
					"stock_length": stock / 1000,
					"bars": bars,
					"cuts": "\n".join(
						f"{format_m(length)} ม. x {count}  ({', '.join(marks)})"
						for length, count, marks in pattern["cuts"]
					),
					"offcut": offcut / 1000,
					"offcut_type": "Reusable" if reusable else "Scrap",
					"total_offcut": offcut * bars / 1000,
					"pieces": json.dumps(
						[
							{"length": length, "count": count, "marks": marks}
							for length, count, marks in pattern["cuts"]
						],
						ensure_ascii=False,
					),
				},
			)
			total = totals.setdefault(stock, {"bars": 0, "required": 0, "reusable": 0, "scrap": 0})
			total["bars"] += bars
			total["required"] += sum(length * count for length, count, _ in pattern["cuts"]) * bars
			total["reusable" if reusable else "scrap"] += offcut * bars

		for stock, total in sorted(totals.items()):
			stock_length = stock * total["bars"] / 1000
			self.append(
				"summary",
				{
					"rebar_type": rebar_type,
					"stock_length": stock / 1000,
					"bars": total["bars"],
					"stock_weight": stock_length * unit_weight,
					"required_length": total["required"] / 1000,
					"reusable_offcut": total["reusable"] / 1000,
					"scrap": total["scrap"] / 1000,
					"loss_percent": total["scrap"] / 10 / stock_length if stock_length else 0,
				},
			)

	def set_totals(self):
		self.total_stock_length = sum(row.stock_length * row.bars for row in self.summary)
		self.total_required_length = sum(flt(row.required_length) for row in self.summary)
		self.reusable_offcut = sum(flt(row.reusable_offcut) for row in self.summary)
		self.scrap = sum(flt(row.scrap) for row in self.summary)
		self.total_weight = sum(flt(row.stock_weight) for row in self.summary)
		self.loss_percent = self.scrap / self.total_stock_length * 100 if self.total_stock_length else 0


def get_cut_length(shape, rebar_type, dimensions, settings, idx=None):
	"""ความยาวตัด (มม.) ของเหล็ก 1 ชิ้น dimensions: dict/row ที่มีค่าด้านเป็นตัวพิมพ์เล็ก (a b c ...)"""
	shape_doc = frappe.get_cached_doc("Bar Shape", shape)
	diameter = flt(frappe.get_cached_value("Rebar Type", rebar_type, "diameter"))
	settings = {**SETTINGS, **{k: v for k, v in (settings or {}).items() if v is not None}}
	values = {dim: flt(dimensions.get(dim.lower())) for dim in DIMENSIONS}

	row = _("แถว {0}: ").format(idx) if idx else ""
	for dim in shape_doc.get_dimensions():
		if values[dim] <= 0:
			frappe.throw(_("{0}รูปทรง {1} ต้องกรอกด้าน {2}").format(row, shape_doc.shape_name, dim))

	length = shape_doc.sum_of_sides(values, diameter)
	if cint(settings["use_bend_deduction"]):
		length -= diameter * sum(
			cint(shape_doc.get(f"bends_{angle}")) * flt(settings[f"bend_{angle}"])
			for angle in (45, 90, 135, 180)
		)
	length += diameter * sum(
		cint(shape_doc.get(f"hooks_{angle}")) * flt(settings[f"hook_{angle}"])
		for angle in (90, 135, 180)
	)
	step = cint(settings["round_up"])
	if step > 0:
		length = math.ceil(round(length, 6) / step) * step
	return round(length)


def get_unit_weight(rebar_type):
	weight, diameter = frappe.get_cached_value("Rebar Type", rebar_type, ["unit_weight", "diameter"])
	return flt(weight) or nominal_mass(diameter)


def parse_lengths(value):
	return [flt(part) for part in str(value).replace(";", ",").split(",") if flt(part) > 0]


def format_m(length_mm):
	"""ความยาว มม. เป็นเมตร 2 ตำแหน่ง (3 ตำแหน่งถ้าไม่ลงตัว 10 มม.)"""
	return f"{length_mm / 1000:.2f}" if length_mm % 10 == 0 else f"{length_mm / 1000:.3f}"


def shape_svg(shape, row=None):
	"""รูป SVG ของรูปทรงที่แทนป้ายด้านด้วยค่าจริง เช่น A=1,200 T=45° (ใช้ใน Print Format ผ่าน jinja)
	ป้ายที่อยู่ซ้าย/ขวาของรูปชิดออกนอกรูป ไม่ให้ทับเส้น (เหมือน shape_svg ใน bar_cut_plan.js)"""
	svg = frappe.get_cached_value("Bar Shape", shape, "svg") or ""

	def replace(match):
		attrs, dim = match.group(1), match.group(2)
		value = flt((row or {}).get(dim.lower()))
		if not value:
			return match.group(0)
		x = flt(re.search(r'\bx="([\d.]+)"', attrs).group(1))
		if x < 40:
			attrs = attrs.replace('text-anchor="middle"', 'text-anchor="end"').replace(
				f'x="{x:g}"', f'x="{x + 8:g}"'
			)
		elif x > 120:
			attrs = attrs.replace('text-anchor="middle"', 'text-anchor="start"').replace(
				f'x="{x:g}"', f'x="{x - 8:g}"'
			)
		return f"<text{attrs}>{dim_label(dim, value)}</text>"

	return re.sub(r'<text([^>]*data-dim="([A-Z])"[^>]*)>[A-Z]</text>', replace, svg)


def dim_label(dim, value):
	"""ป้ายด้านบนรูป: มุมมีหน่วยองศา จำนวนรอบไม่มีทศนิยมถ้าลงตัว (เหมือน dim_label ใน bar_cut_plan.js)"""
	if dim == "T":
		return f"{value:g}°"
	if dim == "N":
		return f"N={value:g}"
	return f"{dim}={value:,.0f}"


@frappe.whitelist()
def preview_cut_length(shape, rebar_type, dimensions, settings=None):
	"""ความยาวตัดสำหรับแสดงในหน้าต่างเพิ่มรายการ (ยังไม่บันทึก)"""
	frappe.has_permission("Bar Cut Plan", "read", throw=True)
	dimensions = frappe.parse_json(dimensions) or {}
	settings = frappe.parse_json(settings) or {}
	try:
		length = get_cut_length(shape, rebar_type, dimensions, settings)
	except frappe.ValidationError:
		frappe.clear_messages()
		return None
	return {"cut_length": length, "unit_weight": get_unit_weight(rebar_type)}
