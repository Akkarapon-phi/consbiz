// Script for DocType: Stock Entry

// สต็อกหน้างาน (consbiz/site_stock.py)
// - เลือกโครงการแล้วระบบใส่คลังของโครงการให้ (รับของ = คลังปลายทาง, เบิก = คลังต้นทาง)
// - WBS ของรายการเลือกจากงานย่อยของแผนงานของโครงการ
// - เบิก (Material Issue) Item หลัก: บันทึกร่างแล้วระบบแยกแถวตัดคลังวัสดุผู้ว่าจ้างก่อน แถวที่แยกแล้วไม่แยกซ้ำ
//   แก้ Item / จำนวน / คลังของแถว = ให้ระบบคิดแถวนั้นใหม่ตอนบันทึก
// - รับของ (Material Receipt): เลขที่ใบส่งของ / ผู้ส่ง / ทะเบียนรถ ไว้ทำรายงานสรุปใบส่งของ

frappe.ui.form.on("Stock Entry", {
	refresh(frm) {
		consbiz.set_wbs_options(frm, frm.doc.project);
		set_project_warehouse(frm);
	},
	project(frm) {
		consbiz.set_wbs_options(frm, frm.doc.project);
		set_project_warehouse(frm);
	},
	purpose(frm) {
		set_project_warehouse(frm);
	},
});

// เอกสารใหม่: ใช้คลังของโครงการ (รับของ = คลังปลายทาง, เบิก/โอน = คลังต้นทาง) ผู้ใช้ไม่ต้องเลือกเอง
function set_project_warehouse(frm) {
	const field = frm.doc.purpose === "Material Receipt" ? "to_warehouse" : "from_warehouse";
	consbiz.set_project_warehouse(frm, frm.doc.project, [field]);
}

function recheck_employer_stock(frm, cdt, cdn) {
	if (locals[cdt][cdn].custom_employer_checked) frappe.model.set_value(cdt, cdn, "custom_employer_checked", 0);
}

frappe.ui.form.on("Stock Entry Detail", {
	item_code: recheck_employer_stock,
	qty: recheck_employer_stock,
	uom: recheck_employer_stock,
	s_warehouse: recheck_employer_stock,
});
