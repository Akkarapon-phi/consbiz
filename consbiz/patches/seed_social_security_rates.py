# อัตราประกันสังคม (มาตรา 33) ตั้งแต่ 1 ม.ค. 2569: 5% ฐาน 1,650-17,500 (สูงสุด 875 บาท/เดือน)
# ปี 2572 เพดานขึ้นเป็น 20,000 ให้เพิ่มแถวใหม่ในหน้าตั้งค่าเมื่อประกาศมีผล

import frappe

RATES = (
	{
		"description": "อัตราปกติ (เพดาน 17,500 ตั้งแต่ 2569)",
		"from_date": "2026-01-01",
		"employee_rate": 5,
		"employer_rate": 5,
		"min_base": 1650,
		"max_base": 17500,
	},
)


def execute():
	for rate in RATES:
		if frappe.db.exists("Social Security Rate", {"from_date": rate["from_date"]}):
			continue
		frappe.get_doc({"doctype": "Social Security Rate", **rate}).insert(ignore_permissions=True)
