# Copyright (c) 2026, Siricons and Contributors
# See license.txt

"""ตัวช่วยร่วมของเทสต์"""

import frappe
from frappe.utils import flt


def insert_boq(boq):
	"""บันทึก BOQ ของเทสต์ที่ระบุยอดแถวด้วย total_amount ตรงๆ

	BOQ คำนวณ total_amount = ปริมาณ x (ค่าวัสดุ + ค่าแรง) ทุกครั้งที่บันทึก (boq.calculate_row) จึง
	- แถวที่มีปริมาณ: แปลงเป็นค่าวัสดุต่อหน่วย (total_amount / ปริมาณ) ได้ยอดเท่าเดิมผ่านการคำนวณจริง
	- แถวงานเหมา (ไม่มีปริมาณ): BOQ คิดได้ 0 ใส่ยอดลงฐานข้อมูลหลังบันทึก (แบบงานเหมาที่แก้ยอดในแผนงาน)
	"""
	lump = {}
	for row in boq.boq_details:
		total = flt(row.get("total_amount"))
		if not total:
			continue
		if flt(row.quantity):
			if not flt(row.get("material_rate")) and not flt(row.get("labour_rate")):
				row.material_rate = total / flt(row.quantity)
		else:
			lump[row.idx] = total
	boq.insert()
	for row in boq.boq_details:
		if row.idx in lump:
			row.db_set(
				{"total_amount": lump[row.idx], "material_amount": lump[row.idx]}, update_modified=False
			)
	if lump:
		boq.db_set("grand_total", sum(flt(r.total_amount) for r in boq.boq_details), update_modified=False)
	return boq
