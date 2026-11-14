# Copyright (c) 2026, Siricons and contributors
# For license information, please see license.txt

# ลงเวลา + ค่าแรงคนงานรายวัน 1 ใบต่อโครงการต่อรอบ (period_of: 1-15 / 16-สิ้นเดือน)
# ธุรการลงเวลาในแอป (consbiz.labour.save_sheet) แถว days = 1 คนต่อวัน
# ตาราง pay คำนวณใหม่ทุกครั้งที่บันทึก (calculate) กรอกได้เฉพาะ other_deduction / deduction_remark
# แต่ละแถว = ชั่วโมงทำงานจริงของคนงานในวันนั้น ไม่เกิน 8 = เวลาปกติ ส่วนเกิน = OT (ot_hours)
# วันหยุดเป็นของทั้งวัน (ตาราง holidays) แถวของวันนั้นได้ holiday = 1
# ค่าแรง: อัตราของวันนั้น x ชั่วโมงปกติ ÷ 8 (ตามชั่วโมงจริง), ทำงานวันหยุด x 2
#   (ลูกจ้างรายวันไม่ได้ค่าจ้างวันหยุด ทำงานวันหยุดจึงได้ 2 เท่า, พ.ร.บ.คุ้มครองแรงงาน ม.62-63)
#   OT = ค่าแรง ÷ 8 x 1.5 ต่อชั่วโมง, วันหยุด x 3 / คนงานที่ติ๊ก ot_flat = ชั่วโมง x ot_hourly_rate
# ประกันสังคม: consbiz.social_security (สะสมรายเดือนข้ามใบ ใบที่ปิดเดือนใช้ฐานต่ำสุด) เฉพาะคนงานที่บริษัทจ่ายเอง
# เบิกล่วงหน้า (Labour Advance ที่ค้าง วันเบิกไม่เกินวันสุดท้ายของรอบ) ตัดเก่าก่อน ไม่เกินค่าแรงหลังหักประกันสังคม/หักอื่นๆ
# Submit = อนุมัติ + ลงบัญชี (Labour Settings ของบริษัท):
#   คนงานที่บริษัทจ่ายเอง = Journal Entry 1 ใบ (Dr. ค่าแรง + ประกันสังคมนายจ้าง / Cr. ประกันสังคมค้างจ่าย, เงินเบิก, หักอื่นๆ, ค่าแรงค้างจ่าย)
#   คนงานผ่าน ผรม. = ร่าง Purchase Invoice 1 ใบต่อ ผรม. (ยอด = ค่าแรง - หักอื่นๆ, หัก ณ ที่จ่ายตามตั้งค่า) บัญชีตรวจแล้ว Submit เอง
# Cancel = ยกเลิก Journal Entry, ลบร่าง PI (PI ที่ Submit แล้วยกเลิกตาม) แล้วคืนยอดเบิกล่วงหน้า

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, flt, get_first_day, get_last_day, getdate, nowdate

from consbiz.consbiz.doctype.labour_advance.labour_advance import cost_center_of
from consbiz.consbiz.doctype.labour_settings.labour_settings import require, settings_of
from consbiz.social_security import contribution, require_rate

HOURS_PER_DAY = 8
OT_RATE = 1.5
HOLIDAY_WAGE_RATE = 2
HOLIDAY_OT_RATE = 3
MAX_HOURS = 24
# ช่องของตาราง pay ที่ผู้ใช้กรอก (คงค่าไว้ตอนคำนวณใหม่)
MANUAL_PAY_FIELDS = ("other_deduction", "deduction_remark")


def period_of(day):
	"""รอบค่าแรงของวัน day: 1-15 หรือ 16-สิ้นเดือน"""
	day = getdate(day)
	if day.day <= 15:
		return day.replace(day=1), day.replace(day=15)
	return day.replace(day=16), getdate(get_last_day(day))


class LabourTimesheet(Document):
	def validate(self):
		self.check_dates()
		self.check_overlap()
		self.check_days()
		self.calculate()

	def before_submit(self):
		if not self.days:
			frappe.throw(_("ยังไม่มีการลงเวลาในรอบนี้"))
		negative = [row.worker_name for row in self.pay if flt(row.net) < 0]
		if negative:
			frappe.throw(_("ยอดหักเกินค่าแรง: {0}").format(", ".join(negative)))
		settings = settings_of(self.company)
		if any(row.payee_type == "Company" for row in self.pay):
			require(settings, "wage_expense_account", "wage_payable_account")
			if any(flt(row.sso) or flt(row.employer_sso) for row in self.pay):
				require(settings, "sso_payable_account", "employer_sso_expense_account")
			if any(flt(row.advance) for row in self.pay):
				require(settings, "advance_account")
		if any(row.payee_type == "Subcontractor" for row in self.pay):
			require(settings, "wage_expense_account", "subcontract_item")

	def on_submit(self):
		self.post_journal_entry()
		self.make_purchase_invoices()
		self.update_advances()

	def on_cancel(self):
		if self.journal_entry and frappe.db.get_value("Journal Entry", self.journal_entry, "docstatus") == 1:
			frappe.get_doc("Journal Entry", self.journal_entry).cancel()
		# ปลดลิงก์ก่อน ไม่งั้นลบ/ยกเลิก PI ไม่ได้ (ใบนี้ยังอ้างอยู่)
		invoices = sorted({row.purchase_invoice for row in self.pay if row.purchase_invoice})
		for row in self.pay:
			if row.purchase_invoice:
				row.db_set("purchase_invoice", None)
		for invoice in invoices:
			status = frappe.db.get_value("Purchase Invoice", invoice, "docstatus")
			if status == 0:
				frappe.delete_doc("Purchase Invoice", invoice, ignore_permissions=True)
			elif status == 1:
				frappe.get_doc("Purchase Invoice", invoice).cancel()
		self.update_advances()

	def update_advances(self):
		for name in sorted({row.advance for row in self.advances}):
			frappe.get_doc("Labour Advance", name).update_deduction()

	def posting_date(self):
		return min(getdate(self.to_date), getdate(nowdate()))

	def post_journal_entry(self):
		rows = [row for row in self.pay if row.payee_type == "Company"]
		if not rows:
			return
		settings = settings_of(self.company)
		total = lambda field: flt(sum(flt(row.get(field)) for row in rows), 2)  # noqa: E731
		cost_center = cost_center_of(self.project, self.company)
		lines = [
			(settings.wage_expense_account, total("gross"), 0),
			(settings.employer_sso_expense_account, total("employer_sso"), 0),
			(settings.sso_payable_account, 0, flt(total("sso") + total("employer_sso"), 2)),
			(settings.advance_account, 0, total("advance")),
			(settings.other_deduction_account or settings.wage_expense_account, 0, total("other_deduction")),
			(settings.wage_payable_account, 0, total("net")),
		]
		je = frappe.get_doc(
			{
				"doctype": "Journal Entry",
				"voucher_type": "Journal Entry",
				"company": self.company,
				"posting_date": self.posting_date(),
				"user_remark": _("ค่าแรงคนงานรายวัน {0} รอบ {1} - {2} ({3})").format(
					self.name, self.from_date, self.to_date, self.project
				),
				"accounts": [
					{
						"account": account,
						"debit_in_account_currency": debit,
						"credit_in_account_currency": credit,
						"project": self.project,
						"cost_center": cost_center,
					}
					for account, debit, credit in lines
					if account and (debit or credit)
				],
			}
		)
		je.insert(ignore_permissions=True)
		je.submit()
		self.db_set("journal_entry", je.name)

	def make_purchase_invoices(self):
		from consbiz import deductions

		groups = {}
		for row in self.pay:
			if row.payee_type == "Subcontractor" and row.supplier:
				groups.setdefault(row.supplier, []).append(row)
		if not groups:
			return
		settings = settings_of(self.company)
		cost_center = cost_center_of(self.project, self.company)
		for supplier, rows in sorted(groups.items()):
			amount = flt(sum(flt(r.gross) - flt(r.other_deduction) for r in rows), 2)
			if amount <= 0:
				continue
			names = ", ".join(r.worker_name for r in rows)
			days = sum(flt(r.days_worked) for r in rows)
			pi = frappe.new_doc("Purchase Invoice")
			pi.update(
				{
					"supplier": supplier,
					"company": self.company,
					"posting_date": self.posting_date(),
					"set_posting_time": 1,
					"project": self.project,
					"ignore_pricing_rule": 1,
					"remarks": _("ค่าแรงคนงานรายวัน {0} รอบ {1} - {2}: {3}").format(
						self.name, self.from_date, self.to_date, names
					),
				}
			)
			pi.append(
				"items",
				{
					"item_code": settings.subcontract_item,
					"qty": 1,
					"rate": amount,
					"description": _("ค่าแรงคนงานรายวัน รอบ {0} - {1} ({2} คน {3:g} แรง) {4}").format(
						self.from_date, self.to_date, len(rows), days, self.name
					),
					"expense_account": settings.wage_expense_account,
					"project": self.project,
					"cost_center": cost_center,
				}
			)
			if pi.meta.has_field("custom_subject_to_wht") and flt(settings.subcontract_wht_percent):
				pi.custom_subject_to_wht = 1
				pi.custom_wht_percent = flt(settings.subcontract_wht_percent)
			pi.flags.ignore_permissions = True
			pi.insert()
			deductions.calculate(pi)
			pi.save()
			for row in rows:
				row.db_set("purchase_invoice", pi.name)

	def check_dates(self):
		if getdate(self.to_date) < getdate(self.from_date):
			frappe.throw(_("วันที่สิ้นสุดต้องไม่ก่อนวันที่เริ่ม"))
		company = frappe.db.get_value("Project", self.project, "company")
		if company and company != self.company:
			frappe.throw(_("โครงการ {0} ไม่ได้อยู่ในบริษัท {1}").format(self.project, self.company))

	def check_overlap(self):
		other = frappe.get_all(
			"Labour Timesheet",
			filters={
				"project": self.project,
				"docstatus": ("<", 2),
				"name": ("!=", self.name or ""),
				"from_date": ("<=", self.to_date),
				"to_date": (">=", self.from_date),
			},
			pluck="name",
			limit=1,
		)
		if other:
			frappe.throw(_("ช่วงวันที่ซ้อนกับใบลงเวลา {0} ของโครงการเดียวกัน").format(other[0]))

	def check_days(self):
		start, end = getdate(self.from_date), getdate(self.to_date)
		seen = set()
		holidays = set()
		for row in self.holidays:
			day = getdate(row.date)
			if not start <= day <= end:
				frappe.throw(_("วันหยุด {0} อยู่นอกรอบของใบนี้").format(row.date))
			holidays.add(day)
		self.holidays = sorted({getdate(r.date): r for r in self.holidays}.values(), key=lambda r: getdate(r.date))
		for index, row in enumerate(self.holidays, 1):
			row.idx = index
		for row in self.days:
			day = getdate(row.date)
			if not start <= day <= end:
				frappe.throw(_("แถว {0}: วันที่ {1} อยู่นอกรอบของใบนี้").format(row.idx, row.date))
			key = (row.worker, day)
			if key in seen:
				frappe.throw(_("แถว {0}: {1} ลงเวลาวันที่ {2} ซ้ำ").format(row.idx, row.worker_name, row.date))
			seen.add(key)
			row.hours = flt(row.hours, 2)
			if not 0 < row.hours <= MAX_HOURS:
				frappe.throw(_("แถว {0}: ชั่วโมงทำงานต้องมากกว่า 0 และไม่เกิน {1}").format(row.idx, MAX_HOURS))
			row.ot_hours = max(0.0, row.hours - HOURS_PER_DAY)
			row.holiday = 1 if day in holidays else 0
		companies = dict(
			frappe.get_all(
				"Daily Worker",
				filters={"name": ("in", list({row.worker for row in self.days}))},
				fields=["name", "company"],
				as_list=True,
			)
		)
		for row in self.days:
			if companies.get(row.worker) != self.company:
				frappe.throw(_("{0} ไม่ใช่คนงานของบริษัท {1}").format(row.worker_name, self.company))
		self.days.sort(key=lambda row: (getdate(row.date), row.worker_name or "", row.worker))
		for index, row in enumerate(self.days, 1):
			row.idx = index

	def calculate(self):
		workers = {name: frappe.get_doc("Daily Worker", name) for name in {row.worker for row in self.days}}
		manual = {row.worker: {f: row.get(f) for f in MANUAL_PAY_FIELDS} for row in self.pay}
		totals = {}
		for row in self.days:
			worker = workers[row.worker]
			units = min(flt(row.hours), HOURS_PER_DAY) / HOURS_PER_DAY
			rate = worker.rate_on(row.date)
			wage = rate * units * (HOLIDAY_WAGE_RATE if row.holiday else 1)
			if worker.ot_flat:
				ot = flt(row.ot_hours) * flt(worker.ot_hourly_rate)
			else:
				ot = flt(row.ot_hours) * rate / HOURS_PER_DAY * (HOLIDAY_OT_RATE if row.holiday else OT_RATE)
			row.amount = flt(wage + ot, 2)
			t = totals.setdefault(
				row.worker,
				{"days_worked": 0.0, "holiday_days": 0.0, "ot_hours": 0.0, "wage": 0.0, "ot_amount": 0.0, "months": {}},
			)
			t["days_worked"] += units
			t["holiday_days"] += units if row.holiday else 0
			t["ot_hours"] += flt(row.ot_hours)
			t["wage"] += wage
			t["ot_amount"] += ot
			month = get_first_day(row.date)
			t["months"][month] = t["months"].get(month, 0.0) + row.amount

		self.pay = []
		self.advances = []
		for name, t in sorted(totals.items(), key=lambda item: (workers[item[0]].worker_name, item[0])):
			kept = manual.get(name, {})
			if not (t["wage"] or t["ot_amount"] or flt(kept.get("other_deduction"))):
				continue
			worker = workers[name]
			sso, employer_sso = self.social_security(worker, t["months"]) if worker.sso_registered else (0, 0)
			gross = flt(t["wage"] + t["ot_amount"], 2)
			row = self.append(
				"pay",
				{
					"worker": name,
					"worker_name": worker.worker_name,
					"payee_type": worker.payee_type,
					"supplier": worker.supplier,
					"days_worked": t["days_worked"],
					"holiday_days": t["holiday_days"],
					"ot_hours": t["ot_hours"],
					"wage": flt(t["wage"], 2),
					"ot_amount": flt(t["ot_amount"], 2),
					"gross": gross,
					"advance": 0,
					"sso": sso,
					"employer_sso": employer_sso,
					"other_deduction": flt(kept.get("other_deduction"), 2),
					"deduction_remark": kept.get("deduction_remark"),
				},
			)
			if worker.payee_type == "Company":
				available = flt(gross - flt(row.sso) - flt(row.other_deduction), 2)
				row.advance = self.allocate_advances(name, worker.worker_name, available)
			row.net = flt(gross - flt(row.advance) - flt(row.sso) - flt(row.other_deduction), 2)

		for field, source in (
			("total_gross", "gross"),
			("total_advance", "advance"),
			("total_sso", "sso"),
			("total_other_deduction", "other_deduction"),
			("total_net", "net"),
			("total_employer_sso", "employer_sso"),
		):
			self.set(field, flt(sum(flt(row.get(source)) for row in self.pay), 2))

	def allocate_advances(self, worker, worker_name, available):
		"""ตัดใบเบิกที่ค้าง (เก่าก่อน) ได้ไม่เกิน available คืนยอดที่หักรอบนี้"""
		if available <= 0:
			return 0.0
		total = 0.0
		for advance in outstanding_advances(worker, self.to_date, self.name):
			amount = flt(min(advance.outstanding, available - total), 2)
			if amount <= 0:
				break
			self.append(
				"advances", {"advance": advance.name, "worker": worker, "worker_name": worker_name, "amount": amount}
			)
			total += amount
		return flt(total, 2)

	def social_security(self, worker, months):
		"""เงินสมทบของใบนี้ (ลูกจ้าง, นายจ้าง) รวมทุกเดือนที่ใบนี้ครอบ"""
		employee_total = employer_total = 0.0
		end = getdate(self.to_date)
		for month, wage in months.items():
			rate = require_rate(month)
			before = wage_before(worker.name, month, getdate(self.from_date), self.name)
			closed = getdate(get_last_day(month)) <= end
			employee, employer = contribution(before, wage, rate, closed)
			employee_total += employee
			employer_total += employer
		return employee_total, employer_total


def wage_before(worker, month, before, exclude=None):
	"""ค่าแรงที่อนุมัติแล้ว (ใบที่ Submit) ของคนงานในเดือน month ก่อนวันที่ before"""
	day = frappe.qb.DocType("Labour Timesheet Day")
	sheet = frappe.qb.DocType("Labour Timesheet")
	query = (
		frappe.qb.from_(day)
		.join(sheet)
		.on(sheet.name == day.parent)
		.select(frappe.query_builder.functions.Sum(day.amount))
		.where(
			(day.parenttype == "Labour Timesheet")
			& (sheet.docstatus == 1)
			& (day.worker == worker)
			& (day.date >= month)
			& (day.date <= add_days(before, -1))
		)
	)
	if exclude:
		query = query.where(sheet.name != exclude)
	result = query.run()
	return flt(result[0][0]) if result else 0.0


def outstanding_advances(worker, until, exclude=None):
	"""ใบเบิกที่ Submit แล้วและยังหักไม่ครบ (ไม่นับใบลงเวลา exclude) เรียงเก่าก่อน"""
	advances = frappe.get_all(
		"Labour Advance",
		filters={"worker": worker, "docstatus": 1, "date": ("<=", until)},
		fields=["name", "amount", "date"],
		order_by="date asc, creation asc",
	)
	if not advances:
		return []
	used = {}
	row = frappe.qb.DocType("Labour Timesheet Advance")
	sheet = frappe.qb.DocType("Labour Timesheet")
	query = (
		frappe.qb.from_(row)
		.join(sheet)
		.on(sheet.name == row.parent)
		.select(row.advance, frappe.query_builder.functions.Sum(row.amount))
		.where((row.advance.isin([a.name for a in advances])) & (sheet.docstatus == 1))
		.groupby(row.advance)
	)
	if exclude:
		query = query.where(sheet.name != exclude)
	for name, amount in query.run():
		used[name] = flt(amount)
	result = []
	for advance in advances:
		advance.outstanding = flt(flt(advance.amount) - used.get(advance.name, 0), 2)
		if advance.outstanding > 0:
			result.append(advance)
	return result
