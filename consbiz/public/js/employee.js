// Script for DocType: Employee

// ---- ย้ายจาก Client Script "Employee Year of Joining" ----

frappe.ui.form.on("Employee", {
	date_of_joining: function (frm) {
		if (frm.doc.date_of_joining) {
			// ดึงวันที่จากฟิลด์ date_of_joining
			let joining_date = new Date(frm.doc.date_of_joining);

			// ดึงปี ค.ศ. (เช่น 2026) แล้วเอาเฉพาะ 2 ตัวท้าย (เช่น 26)
			let year_ce_short = joining_date.getFullYear().toString().slice(-2);

			// ใส่ค่าลงในฟิลด์ custom_year_of_joining
			frm.set_value("custom_year_of_joining", year_ce_short);
		} else {
			// ถ้าลบวันที่ออก ให้ล้างค่าในฟิลด์ปีด้วย
			frm.set_value("custom_year_of_joining", "");
		}
	},
});
