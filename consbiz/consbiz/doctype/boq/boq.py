# Copyright (c) 2026, Siricons and contributors
# For license information, please see license.txt

import math

from frappe.model.document import Document
from frappe.utils import flt


class BOQ(Document):
	def validate(self):
		assign_wbs(self.boq_details)
		self.calculate_totals()

	def calculate_totals(self):
		self.total_material_cost = self.total_labour_cost = self.grand_total = 0
		for row in self.boq_details:
			if self.combined_rate:
				row.combined_rate = 1
			calculate_row(row, self.round_down_total)
			self.total_material_cost += row.material_amount
			self.total_labour_cost += row.labour_amount
			self.grand_total += row.total_amount


def assign_wbs(rows):
	"""รัน WBS ใหม่ตามลำดับแถว โดยคงระดับ (จำนวนส่วนใน WBS) ของแต่ละแถวไว้
	แถวที่ไม่มี WBS อยู่ระดับเดียวกับแถวก่อนหน้า และลึกกว่าแถวก่อนหน้าได้ไม่เกิน 1 ระดับ
	ต้องตรงกับ renumber_wbs() ใน boq.js"""
	counters = []
	for row in rows:
		level = len([part for part in (row.wbs or "").split(".") if part.strip()])
		level = max(1, min(level or len(counters) or 1, len(counters) + 1))
		counters = counters[:level]
		if len(counters) < level:
			counters.append(0)
		counters[level - 1] += 1
		row.wbs = ".".join(str(n) for n in counters)


def calculate_row(row, round_down=False):
	"""ราคารวม (combined_rate): ราคาทั้งหมดอยู่ที่ค่าวัสดุ ค่าแรงที่กรอกไว้ย้ายมารวม (ต้องตรงกับ merge_combined_rate() ใน boq.js)
	round_down: ตัดสตางค์เฉพาะช่องรวม ค่าวัสดุ/ค่าแรงไม่ปัด (ต้องตรงกับ round_boq_total() ใน boq.js)
	"""
	if row.combined_rate and flt(row.labour_rate):
		row.material_rate = flt(row.material_rate) + flt(row.labour_rate)
		row.labour_rate = 0
	row.material_amount = flt(row.quantity) * flt(row.material_rate)
	row.labour_amount = flt(row.quantity) * flt(row.labour_rate)
	row.total_amount = row.material_amount + row.labour_amount
	if round_down:
		row.total_amount = round_down_amount(row.total_amount)


def round_down_amount(amount) -> float:
	"""ตัดสตางค์ทิ้งแบบ ROUNDDOWN(x, 0) ของ Excel (ปัดเข้าหาศูนย์)
	ปัด 6 ตำแหน่งก่อน กันเศษของ float เช่น 0.29 * 100 = 28.999999999999996 ต้องได้ 29
	(ปัด 2 ตำแหน่งไม่ได้ 999.995 จะกลายเป็น 1000)"""
	return float(math.trunc(flt(amount, 6)))
