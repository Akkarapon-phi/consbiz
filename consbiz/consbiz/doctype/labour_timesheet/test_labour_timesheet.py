# Copyright (c) 2026, Siricons and contributors
# For license information, please see license.txt

# ค่าแรงคนงานรายวัน: ค่าแรง/OT/วันหยุด, ประวัติค่าแรง, ประกันสังคมสะสมรายเดือน และเช็กชื่อจากแอป (consbiz.labour)

import frappe
from frappe.tests import IntegrationTestCase

from consbiz import labour
from consbiz.consbiz.doctype.labour_timesheet.labour_timesheet import period_of
from consbiz.social_security import rate_on, round_baht

IGNORE_TEST_RECORD_DEPENDENCIES = [
	"Project",
	"Company",
	"Supplier",
	"Account",
	"Item",
	"Journal Entry",
	"Purchase Invoice",
	"Labour Advance",
]

COMPANY = "_Test Company"


SETTINGS = {
	"wage_expense_account": "Miscellaneous Expenses - _TC",
	"employer_sso_expense_account": "Salary - _TC",
	"wage_payable_account": "Accrued Expenses - _TC",
	"sso_payable_account": "Employee Benefits Obligation - _TC",
	"advance_account": "Prepaid Expenses - _TC",
	"subcontract_wht_percent": 3,
}
CASH = "_Test Cash - _TC"
LABOUR_ITEM = "_Test Labour Service"


def make_settings(**values):
	# erpnext_thailand บังคับให้บริษัทมีแถวใน Thai Tax Settings ก่อนลง Journal Entry (เหมือน test_retention_receivable)
	thai = frappe.get_single("Thai Tax Settings")
	if not any(row.company == COMPANY for row in thai.company_accounts):
		thai.append("company_accounts", {"company": COMPANY})
		thai.save(ignore_permissions=True)
	# PI ของ ผรม. หัก ณ ที่จ่ายลงบัญชีของบริษัท (deductions.ACCOUNTS)
	if not frappe.db.get_value("Company", COMPANY, "custom_wht_payable"):
		frappe.db.set_value("Company", COMPANY, "custom_wht_payable", "Deferred Revenue - _TC")
	if not frappe.db.exists("Item", LABOUR_ITEM):
		frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": LABOUR_ITEM,
				"item_group": frappe.db.get_value("Item Group", {"is_group": 0}),
				"stock_uom": "Nos",
				"is_stock_item": 0,
			}
		).insert(ignore_permissions=True)
	doc = (
		frappe.get_doc("Labour Settings", COMPANY)
		if frappe.db.exists("Labour Settings", COMPANY)
		else frappe.new_doc("Labour Settings")
	)
	doc.update({"company": COMPANY, "subcontract_item": LABOUR_ITEM, **SETTINGS, **values})
	return doc.save(ignore_permissions=True)


def make_advance(worker, amount, date="2026-09-02", submit=True):
	doc = frappe.get_doc(
		{"doctype": "Labour Advance", "worker": worker, "date": date, "amount": amount, "paid_from_account": CASH}
	).insert(ignore_permissions=True)
	if submit:
		doc.submit()
	return doc


def make_project(name):
	existing = frappe.db.get_value("Project", {"project_name": name})
	if existing:
		return existing
	return (
		frappe.get_doc(
			{
				"doctype": "Project",
				"project_name": name,
				"company": COMPANY,
				"custom_warehouse_name": f"{name} WH",
			}
		)
		.insert(ignore_permissions=True)
		.name
	)


def make_worker(project, name, rate=400, **values):
	doc = frappe.get_doc(
		{
			"doctype": "Daily Worker",
			"worker_name": name,
			"company": COMPANY,
			"project": project,
			"rates": [{"from_date": "2026-01-01", "daily_rate": rate}],
			**values,
		}
	)
	return doc.insert(ignore_permissions=True)


def make_sheet(project, start, end, days, submit=False, holidays=()):
	doc = frappe.get_doc(
		{
			"doctype": "Labour Timesheet",
			"project": project,
			"company": COMPANY,
			"from_date": start,
			"to_date": end,
			"days": days,
			"holidays": [{"date": d} for d in holidays],
		}
	).insert(ignore_permissions=True)
	if submit:
		doc.submit()
	return doc


def present(worker, dates, hours=8):
	return [{"worker": worker, "date": d, "hours": hours} for d in dates]


class IntegrationTestLabourTimesheet(IntegrationTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		self.project = make_project("_Test Labour Project")
		frappe.db.delete("Labour Timesheet", {"project": self.project})
		frappe.db.delete("Labour Advance", {"project": self.project})
		frappe.db.delete("Daily Worker", {"project": self.project})
		make_settings()

	def test_period_of(self):
		self.assertEqual([str(d) for d in period_of("2026-02-10")], ["2026-02-01", "2026-02-15"])
		self.assertEqual([str(d) for d in period_of("2026-02-16")], ["2026-02-16", "2026-02-28"])

	def test_wage_ot_and_holiday(self):
		worker = make_worker(self.project, "_Test Worker A", 400).name
		sheet = make_sheet(
			self.project,
			"2026-09-01",
			"2026-09-15",
			[
				{"worker": worker, "date": "2026-09-01", "hours": 10},
				{"worker": worker, "date": "2026-09-02", "hours": 4},
				{"worker": worker, "date": "2026-09-03", "hours": 6},
				{"worker": worker, "date": "2026-09-06", "hours": 10},
			],
			holidays=["2026-09-06"],
		)
		pay = sheet.pay[0]
		# ค่าแรง 400 + 200 + 300 (ตามชั่วโมง) + 800 (วันหยุด x2), OT 2 x 50 x 1.5 + 2 x 50 x 3
		self.assertEqual(pay.days_worked, 3.25)
		self.assertEqual(pay.holiday_days, 1)
		self.assertEqual(pay.ot_hours, 4)
		self.assertEqual(pay.wage, 1700)
		self.assertEqual(pay.ot_amount, 450)
		self.assertEqual(pay.gross, 2150)
		self.assertEqual(pay.sso, 0)
		self.assertEqual(sheet.total_net, 2150)
		self.assertEqual([row.amount for row in sheet.days], [550, 200, 300, 1100])
		self.assertEqual([row.holiday for row in sheet.days], [0, 0, 0, 1])

	def test_flat_ot_and_rate_history(self):
		doc = make_worker(self.project, "_Test Worker B", 400, ot_flat=1, ot_hourly_rate=60)
		doc.append("rates", {"from_date": "2026-09-05", "daily_rate": 450})
		doc.save()
		sheet = make_sheet(
			self.project,
			"2026-09-01",
			"2026-09-15",
			present(doc.name, ["2026-09-04", "2026-09-05"], hours=11),
		)
		self.assertEqual(sheet.pay[0].wage, 850)
		self.assertEqual(sheet.pay[0].ot_amount, 360)

	def test_manual_deduction_kept_on_recalculate(self):
		worker = make_worker(self.project, "_Test Worker C", 500).name
		sheet = make_sheet(self.project, "2026-09-01", "2026-09-15", present(worker, ["2026-09-01"]))
		sheet.pay[0].other_deduction = 120
		sheet.pay[0].deduction_remark = "ค่าอุปกรณ์"
		sheet.append("days", {"worker": worker, "date": "2026-09-02", "hours": 8})
		sheet.save()
		self.assertEqual(sheet.pay[0].gross, 1000)
		self.assertEqual(sheet.pay[0].other_deduction, 120)
		self.assertEqual(sheet.pay[0].deduction_remark, "ค่าอุปกรณ์")
		self.assertEqual(sheet.pay[0].net, 880)

	def test_social_security_monthly_ceiling(self):
		worker = make_worker(self.project, "_Test Worker D", 1000, sso_registered=1).name
		days = [f"2026-09-{d:02d}" for d in range(1, 11)]
		first = make_sheet(self.project, "2026-09-01", "2026-09-15", present(worker, days), submit=True)
		self.assertEqual(first.pay[0].sso, 500)
		self.assertEqual(first.pay[0].employer_sso, 500)
		days = [f"2026-09-{d:02d}" for d in range(16, 26)]
		second = make_sheet(self.project, "2026-09-16", "2026-09-30", present(worker, days))
		# ทั้งเดือน 20,000 เกินเพดาน 17,500: ทั้งเดือนหัก 875 งวดแรกหักไปแล้ว 500
		self.assertEqual(second.pay[0].sso, 375)
		self.assertEqual(second.pay[0].net, 10000 - 375)

	def test_social_security_minimum_base_on_month_close(self):
		worker = make_worker(self.project, "_Test Worker E", 100, sso_registered=1).name
		sheet = make_sheet(self.project, "2026-09-16", "2026-09-30", present(worker, ["2026-09-20"]))
		# ทั้งเดือน 100 บาท ต่ำกว่าฐาน 1,650: 1,650 x 5% = 82.5 ปัดเป็น 83
		self.assertEqual(sheet.pay[0].sso, 83)
		first_half = make_sheet(self.project, "2026-10-01", "2026-10-15", present(worker, ["2026-10-01"]))
		self.assertEqual(first_half.pay[0].sso, 5)

	def test_temporary_reduced_rate_wins(self):
		reduced = frappe.get_doc(
			{
				"doctype": "Social Security Rate",
				"description": "_Test ลดชั่วคราว",
				"from_date": "2026-08-01",
				"to_date": "2026-08-31",
				"employee_rate": 3,
				"employer_rate": 5,
				"min_base": 1650,
				"max_base": 17500,
			}
		).insert()
		self.assertEqual(rate_on("2026-08-20").name, reduced.name)
		self.assertNotEqual(rate_on("2026-09-01").name, reduced.name)
		worker = make_worker(self.project, "_Test Worker F", 1000, sso_registered=1).name
		sheet = make_sheet(self.project, "2026-08-01", "2026-08-15", present(worker, ["2026-08-03", "2026-08-04"]))
		self.assertEqual(sheet.pay[0].sso, 60)
		self.assertEqual(sheet.pay[0].employer_sso, 100)

	def test_round_half_up(self):
		self.assertEqual(round_baht(82.5), 83)
		self.assertEqual(round_baht(82.49), 82)

	def test_invalid_hours(self):
		worker = make_worker(self.project, "_Test Worker K").name
		self.assertRaises(
			frappe.ValidationError, make_sheet, self.project, "2026-09-01", "2026-09-15", present(worker, ["2026-09-01"], 25)
		)

	def test_overlap_and_duplicate_day(self):
		worker = make_worker(self.project, "_Test Worker G").name
		make_sheet(self.project, "2026-09-01", "2026-09-15", present(worker, ["2026-09-01"]))
		self.assertRaises(
			frappe.ValidationError, make_sheet, self.project, "2026-09-10", "2026-09-20", []
		)
		self.assertRaises(
			frappe.ValidationError,
			make_sheet,
			self.project,
			"2026-10-01",
			"2026-10-15",
			present(worker, ["2026-10-01", "2026-10-01"]),
		)

	def test_sheet_api(self):
		a = make_worker(self.project, "_Test Worker H").name
		b = make_worker(self.project, "_Test Worker I").name
		labour.save_sheet(self.project, "2026-10-05", [{"worker": a, "date": "2026-10-05", "hours": 10}])
		# อีกคนลงช่องอื่น + ตั้งวันหยุด ไม่ทับช่องของคนแรก
		result = labour.save_sheet(
			self.project,
			"2026-10-10",
			[{"worker": b, "date": "2026-10-05", "hours": 4}, {"worker": b, "date": "2026-10-06", "hours": 8}],
			holidays=["2026-10-05"],
		)
		self.assertEqual(result["from_date"], "2026-10-01")
		self.assertEqual(result["to_date"], "2026-10-15")
		self.assertEqual(result["holidays"], ["2026-10-05"])
		rows = {row["worker"]: row for row in result["workers"]}
		self.assertEqual(rows[a]["hours"], {"2026-10-05": 10})
		self.assertEqual(rows[b]["hours"], {"2026-10-05": 4, "2026-10-06": 8})
		# วันหยุด: 400 x 2 + OT 2 x 50 x 3
		self.assertEqual(rows[a]["pay"]["gross"], 1100)

		# ว่าง = ลบช่อง, ไม่ส่งวันหยุด = คงเดิม
		result = labour.save_sheet(self.project, "2026-10-05", [{"worker": b, "date": "2026-10-05", "hours": None}])
		rows = {row["worker"]: row for row in result["workers"]}
		self.assertEqual(rows[b]["hours"], {"2026-10-06": 8})
		self.assertEqual(result["holidays"], ["2026-10-05"])

		self.assertRaises(
			frappe.ValidationError,
			labour.save_sheet,
			self.project,
			"2026-10-05",
			[{"worker": a, "date": "2026-10-20", "hours": 8}],
		)
		self.assertRaises(
			frappe.ValidationError,
			labour.save_sheet,
			self.project,
			"2099-01-01",
			[{"worker": a, "date": "2099-01-01", "hours": 8}],
		)

		result = labour.submit_sheet(result["timesheet"])
		self.assertEqual(result["docstatus"], 1)
		self.assertFalse(result["can_edit"])
		self.assertRaises(
			frappe.ValidationError,
			labour.save_sheet,
			self.project,
			"2026-10-05",
			[{"worker": a, "date": "2026-10-05", "hours": 8}],
		)

	def test_get_workers(self):
		make_worker(self.project, "_Test Worker L", sso_registered=1)
		rows = labour.get_workers(self.project)["rows"]
		self.assertEqual([r.worker_name for r in rows], ["_Test Worker L"])

	def test_add_worker(self):
		result = labour.add_worker(self.project, " _Test Worker J ", 420, position="ช่างไม้")
		doc = frappe.get_doc("Daily Worker", result["name"])
		self.assertEqual(doc.worker_name, "_Test Worker J")
		self.assertEqual(doc.daily_rate, 420)
		self.assertEqual(doc.company, COMPANY)

	def test_journal_entry_on_submit(self):
		worker = make_worker(self.project, "_Test Worker M", 1000, sso_registered=1).name
		sheet = make_sheet(self.project, "2026-09-01", "2026-09-15", present(worker, ["2026-09-01", "2026-09-02"]))
		sheet.pay[0].other_deduction = 100
		sheet.save()
		sheet.submit()
		je = frappe.get_doc("Journal Entry", sheet.journal_entry)
		self.assertEqual(je.docstatus, 1)
		lines = {(a.account, a.debit, a.credit) for a in je.accounts}
		# ค่าแรง 2,000 ประกันสังคม 100 + นายจ้าง 100 หักอื่นๆ 100 (ไม่ตั้งบัญชี = ลดค่าแรง) สุทธิ 1,800
		self.assertEqual(
			lines,
			{
				("Miscellaneous Expenses - _TC", 2000, 0),
				("Salary - _TC", 100, 0),
				("Employee Benefits Obligation - _TC", 0, 200),
				("Miscellaneous Expenses - _TC", 0, 100),
				("Accrued Expenses - _TC", 0, 1800),
			},
		)
		self.assertTrue(all(a.project == self.project for a in je.accounts))
		sheet.cancel()
		self.assertEqual(frappe.db.get_value("Journal Entry", je.name, "docstatus"), 2)

	def test_purchase_invoice_for_subcontractor(self):
		supplier = "_Test Supplier"
		worker = make_worker(
			self.project, "_Test Worker N", 500, payee_type="Subcontractor", supplier=supplier, sso_registered=1
		)
		self.assertEqual(worker.sso_registered, 0)
		sheet = make_sheet(self.project, "2026-09-01", "2026-09-15", present(worker.name, ["2026-09-01", "2026-09-02"]))
		sheet.pay[0].other_deduction = 200
		sheet.save()
		sheet.submit()
		self.assertFalse(sheet.journal_entry)
		invoice = frappe.db.get_value("Labour Timesheet Pay", {"parent": sheet.name}, "purchase_invoice")
		pi = frappe.get_doc("Purchase Invoice", invoice)
		self.assertEqual(pi.docstatus, 0)
		self.assertEqual(pi.supplier, supplier)
		self.assertEqual(pi.items[0].amount, 800)
		self.assertEqual(pi.items[0].expense_account, "Miscellaneous Expenses - _TC")
		if pi.meta.has_field("custom_wht_amount"):
			self.assertEqual(pi.custom_wht_amount, 24)
		sheet.cancel()
		self.assertFalse(frappe.db.exists("Purchase Invoice", invoice))

	def test_submit_needs_settings(self):
		frappe.delete_doc("Labour Settings", COMPANY, ignore_permissions=True, force=True)
		worker = make_worker(self.project, "_Test Worker O").name
		sheet = make_sheet(self.project, "2026-09-01", "2026-09-15", present(worker, ["2026-09-01"]))
		self.assertRaises(frappe.ValidationError, sheet.submit)

	def test_advances_deducted_oldest_first(self):
		worker = make_worker(self.project, "_Test Worker P", 500).name
		first = make_advance(worker, 600, "2026-09-01")
		second = make_advance(worker, 2000, "2026-09-03")
		self.assertEqual(frappe.db.get_value("Journal Entry", first.journal_entry, "docstatus"), 1)
		# ค่าแรง 4 วัน = 2,000 หักได้ 600 + 1,400 ใบที่สองค้าง 600
		sheet = make_sheet(self.project, "2026-09-01", "2026-09-15", present(worker, [f"2026-09-0{d}" for d in range(1, 5)]))
		self.assertEqual(sheet.pay[0].advance, 2000)
		self.assertEqual(sheet.pay[0].net, 0)
		self.assertEqual([(a.advance, a.amount) for a in sheet.advances], [(first.name, 600), (second.name, 1400)])
		sheet.submit()
		first.reload()
		second.reload()
		self.assertEqual(first.status, "Deducted")
		self.assertEqual((second.status, second.outstanding_amount), ("Partly Deducted", 600))
		# เบิกที่หักคืนแล้วยกเลิกไม่ได้
		self.assertRaises(frappe.ValidationError, first.cancel)
		# รอบถัดไปหักส่วนที่ค้าง
		later = make_sheet(self.project, "2026-09-16", "2026-09-30", present(worker, ["2026-09-16", "2026-09-17"]))
		self.assertEqual(later.pay[0].advance, 600)
		sheet.cancel()
		second.reload()
		self.assertEqual((second.status, second.outstanding_amount), ("Unpaid", 2000))

	def test_advance_only_for_company_paid(self):
		worker = make_worker(self.project, "_Test Worker Q", payee_type="Subcontractor", supplier="_Test Supplier").name
		self.assertRaises(frappe.ValidationError, make_advance, worker, 100)

	def test_settings_reject_payable(self):
		payable = frappe.db.get_value("Account", {"company": COMPANY, "account_type": "Payable", "is_group": 0})
		self.assertRaises(frappe.ValidationError, make_settings, wage_payable_account=payable)

	def test_review_api(self):
		worker = make_worker(self.project, "_Test Worker R", 400, position="ช่างไม้")
		result = labour.save_sheet(self.project, "2026-10-05", [{"worker": worker.name, "date": "2026-10-05", "hours": 8}])
		result = labour.set_deduction(result["timesheet"], worker.name, 50, "ค่าเสื้อ")
		pay = next(w for w in result["workers"] if w["worker"] == worker.name)["pay"]
		self.assertEqual((pay["other_deduction"], pay["deduction_remark"], pay["net"]), (50, "ค่าเสื้อ", 350))
		self.assertEqual(result["totals"]["other_deduction"], 50)
		self.assertRaises(frappe.ValidationError, labour.set_deduction, result["timesheet"], worker.name, -1)
		# รายงานประจำวันดึงจำนวนคนตามตำแหน่ง
		self.assertEqual(labour.labour_on(self.project, "2026-10-05"), [{"role": "ช่างไม้", "qty": 1}])
		self.assertEqual(labour.labour_on(self.project, "2026-10-06"), [])
		self.assertIn("Labour+Timesheet", labour.get_print_url(result["timesheet"]))

	def test_advance_api(self):
		worker = make_worker(self.project, "_Test Worker S", 500).name
		data = labour.get_advances(self.project)
		self.assertIn(worker, [w.name for w in data["workers"]])
		self.assertIn(CASH, [a.value for a in data["cash_accounts"]])
		created = labour.create_advance(worker, 300, CASH, "2026-10-02", "ค่ารถ")
		self.assertEqual(created["docstatus"], 1)
		result = labour.save_sheet(self.project, "2026-10-05", [{"worker": worker, "date": "2026-10-05", "hours": 8}])
		pay = next(w for w in result["workers"] if w["worker"] == worker)["pay"]
		self.assertEqual((pay["advance"], pay["net"]), (300, 200))
		labour.cancel_advance(created["name"])
		self.assertEqual(frappe.db.get_value("Labour Advance", created["name"], "docstatus"), 2)

	def test_settings_api(self):
		data = labour.get_settings(COMPANY)
		self.assertEqual(data["values"]["wage_expense_account"], SETTINGS["wage_expense_account"])
		self.assertTrue(all(c["ok"] for c in data["checks"]))
		data = labour.save_settings(COMPANY, {"other_deduction_account": "Write Off - _TC"})
		self.assertEqual(data["values"]["other_deduction_account"], "Write Off - _TC")
		accounts = [a["value"] for a in labour.search_accounts(COMPANY, "wage_payable_account")]
		self.assertIn("Accrued Expenses - _TC", accounts)
		self.assertNotIn(
			frappe.db.get_value("Account", {"company": COMPANY, "account_type": "Payable", "is_group": 0}), accounts
		)

	def test_create_account_and_item(self):
		suggestion = labour.suggest_account(COMPANY, "wage_payable_account")
		self.assertEqual(suggestion["account_name"], "ค่าแรงค้างจ่าย")
		self.assertIn(suggestion["parent_account"], [p["value"] for p in suggestion["parents"]])
		created = labour.create_account(
			COMPANY, "wage_payable_account", "_Test ค่าแรงค้างจ่าย", suggestion["parent_account"]
		)
		account = frappe.db.get_value("Account", created["value"], ["root_type", "is_group"], as_dict=True)
		self.assertEqual((account.root_type, account.is_group), ("Liability", 0))
		self.assertIn(created["value"], [a["value"] for a in labour.search_accounts(COMPANY, "wage_payable_account", "_Test ค่าแรง")])
		# กลุ่มผิดประเภท
		expense_group = frappe.db.get_value("Account", {"company": COMPANY, "is_group": 1, "root_type": "Expense"})
		self.assertRaises(
			frappe.ValidationError, labour.create_account, COMPANY, "wage_payable_account", "_Test ผิดกลุ่ม", expense_group
		)
		item = labour.create_service_item("_Test ค่าแรงผู้รับเหมาช่วง")
		self.assertEqual(frappe.db.get_value("Item", item["value"], "is_stock_item"), 0)
		self.assertEqual(labour.create_service_item("_Test ค่าแรงผู้รับเหมาช่วง")["value"], item["value"])

	def test_teams(self):
		a = make_worker(self.project, "_Test Worker T", team="ชุดไม้").name
		b = make_worker(self.project, "_Test Worker U", payee_type="Subcontractor", supplier="_Test Supplier").name
		c = make_worker(self.project, "_Test Worker V").name
		rows = {r["worker"]: r for r in labour.get_sheet(self.project, "2026-10-05")["workers"]}
		self.assertEqual(rows[a]["team"], "ชุดไม้")
		self.assertEqual(rows[b]["team"], frappe.db.get_value("Supplier", "_Test Supplier", "supplier_name"))
		self.assertEqual(rows[c]["team"], labour.NO_TEAM)
		# ไม่ระบุทีมอยู่ท้าย
		self.assertEqual(labour.get_sheet(self.project, "2026-10-05")["workers"][-1]["worker"], c)
		labour.set_team([b, c], "ชุดไม้")
		self.assertEqual(labour.get_teams(self.project), ["ชุดไม้"])
		self.assertEqual(frappe.db.get_value("Daily Worker", c, "team"), "ชุดไม้")
		added = labour.add_worker(self.project, "_Test Worker W", 400, team="ชุดเหล็ก")
		self.assertEqual(added["team"], "ชุดเหล็ก")

	def test_worker_form_and_bank(self):
		created = labour.save_worker(
			{"worker_name": "_Test Worker X", "daily_rate": 450, "team": "ชุดไม้", "bank_name": "กสิกรไทย", "bank_account": "123-4-56789-0"},
			project=self.project,
		)
		doc = frappe.get_doc("Daily Worker", created["name"])
		self.assertEqual(doc.bank_account, "1234567890")
		self.assertEqual(doc.daily_rate, 450)
		# บัญชีผู้อื่นต้องมีชื่อเจ้าของ
		self.assertRaises(
			frappe.ValidationError, labour.save_worker, {"account_holder_other": 1}, created["name"]
		)
		labour.save_worker(
			{"account_holder_other": 1, "account_holder": "นางสมศรี", "account_holder_relation": "ภรรยา", "daily_rate": 480, "rate_from": "2026-11-10"},
			created["name"],
		)
		doc.reload()
		self.assertEqual(doc.account_holder, "นางสมศรี")
		self.assertEqual([(str(r.from_date), r.daily_rate) for r in doc.rates][-1], ("2026-11-10", 480))
		self.assertEqual(doc.rate_on("2026-11-09"), 450)
		data = labour.get_worker(created["name"])
		self.assertEqual(len(data["rates"]), 2)
		self.assertRaises(frappe.ValidationError, labour.save_worker, {"bank_account": "123"}, created["name"])
