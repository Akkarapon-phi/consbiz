# เงินสมทบประกันสังคม (มาตรา 33) จากตาราง Social Security Rate
# อัตราตามเดือนของวันทำงาน (ไม่ใช่เดือนที่จ่าย) ช่วงที่แคบกว่าชนะ (ใช้ใส่การลดอัตราชั่วคราวทับอัตราปกติ)
# เพดาน/ฐานต่ำสุดเป็นรายเดือน จ่ายหลายงวดต่อเดือนจึงคิดสะสม:
#   หักงวดนี้ = ยอดที่ควรหักถึงงวดนี้ - ยอดที่ควรหักถึงงวดก่อน (ตัดกันเป็นทอดๆ ได้ยอดทั้งเดือนตรงกับคิดทีเดียว)
#   ฐานต่ำสุดใช้เฉพาะงวดที่ปิดเดือน (ยังไม่รู้ว่าทั้งเดือนจะได้เท่าไร)

from decimal import ROUND_HALF_UP, Decimal

import frappe
from frappe import _
from frappe.utils import flt, get_first_day, getdate


def round_baht(value):
	"""ปัดเป็นบาท เศษ 0.50 ขึ้นปัดขึ้น (แบบที่ สปส. ใช้)"""
	return float(Decimal(str(flt(value, 6))).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def rate_on(day):
	"""อัตราที่ใช้กับเดือนของ day (ดูที่วันที่ 1 ของเดือน) None = ยังไม่ได้ตั้ง"""
	month = get_first_day(getdate(day))
	rows = frappe.get_all(
		"Social Security Rate",
		filters={"from_date": ("<=", month)},
		or_filters=[["to_date", "is", "not set"], ["to_date", ">=", month]],
		fields=["name", "from_date", "to_date", "employee_rate", "employer_rate", "min_base", "max_base"],
	)
	if not rows:
		return None

	# ช่วงที่มีวันสิ้นสุดและแคบกว่ามาก่อน ช่วงเปิดท้ายเรียงตามวันเริ่มล่าสุด
	def width(row):
		if row.to_date:
			return (0, (getdate(row.to_date) - getdate(row.from_date)).days)
		return (1, -getdate(row.from_date).toordinal())

	return sorted(rows, key=width)[0]


def require_rate(day):
	rate = rate_on(day)
	if not rate:
		frappe.throw(
			_("ยังไม่ได้ตั้งอัตราประกันสังคมของเดือน {0} (Social Security Rate)").format(
				getdate(day).strftime("%m/%Y")
			)
		)
	return rate


def due(wage, rate, percent_field="employee_rate", month_closed=False):
	"""เงินสมทบที่ควรหักจากค่าจ้างสะสม wage ของเดือน (ปัดเป็นบาท)"""
	wage = flt(wage)
	if wage <= 0:
		return 0.0
	base = min(wage, flt(rate.max_base))
	if month_closed:
		base = max(base, flt(rate.min_base))
	return round_baht(base * flt(rate.get(percent_field)) / 100)


def contribution(before, wage, rate, month_closed):
	"""เงินสมทบของงวดนี้ (ลูกจ้าง, นายจ้าง) before = ค่าจ้างงวดก่อนในเดือนเดียวกัน wage = ค่าจ้างงวดนี้"""
	result = []
	for field in ("employee_rate", "employer_rate"):
		total = due(before + wage, rate, field, month_closed)
		result.append(max(0.0, total - due(before, rate, field)))
	return tuple(result)
