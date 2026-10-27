# Copyright (c) 2026, Siricons and contributors
# For license information, please see license.txt

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
			calculate_row(row)
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


def calculate_row(row):
	"""ราคารวม (combined_rate): ราคาทั้งหมดอยู่ที่ค่าวัสดุ ค่าแรงที่กรอกไว้ย้ายมารวม (ต้องตรงกับ merge_combined_rate() ใน boq.js)"""
	if row.combined_rate and flt(row.labour_rate):
		row.material_rate = flt(row.material_rate) + flt(row.labour_rate)
		row.labour_rate = 0
	row.material_amount = flt(row.quantity) * flt(row.material_rate)
	row.labour_amount = flt(row.quantity) * flt(row.labour_rate)
	row.total_amount = row.material_amount + row.labour_amount
