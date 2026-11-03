// Copyright (c) 2026, Siricons and contributors
// For license information, please see license.txt

// ขยายระยะเวลา: Submit = ยื่นขอ วันสิ้นสุดสัญญาของแผนงานเลื่อนเมื่อผู้ว่าจ้างอนุมัติ (วันปฏิทิน)
// หลัง Submit แก้ผลอนุมัติ วันที่อนุมัติ และจำนวนวันที่อนุมัติได้ แล้วกด Update

frappe.ui.form.on("Extension of Time", {
	setup(frm) {
		frm.set_query("construction_management", () => ({ filters: { status: "Active" } }));
		frm.set_query("variation_order", () => ({
			filters: { construction_management: frm.doc.construction_management, docstatus: 1 },
		}));
	},

	refresh(frm) {
		if (frm.doc.construction_management && !frm.is_new()) {
			frm.add_custom_button(__("เปิด Gantt"), () =>
				frappe.set_route("construction-gantt", frm.doc.construction_management)
			);
		}
		show_notice_warning(frm);
	},

	construction_management(frm) {
		frm.set_value("variation_order", null);
	},

	variation_order(frm) {
		if (!frm.doc.variation_order) return;
		frappe.db.get_value("Variation Order", frm.doc.variation_order, "extension_days").then(
			({ message }) => {
				if (message?.extension_days) frm.set_value("requested_days", message.extension_days);
			}
		);
	},

	date: show_notice_warning,
	event_end: show_notice_warning,
});

// แจ้งหลังเหตุสิ้นสุดเกินกำหนด: เตือนเท่านั้น ผู้ว่าจ้างอาจยังพิจารณาให้
// 15 วัน ตรงกับ NOTICE_DAYS ใน extension_of_time.py
function show_notice_warning(frm) {
	const { date, event_end } = frm.doc;
	if (!date || !event_end) return;
	const deadline = frappe.datetime.add_days(event_end, 15);
	if (date > deadline) {
		frm.set_intro(
			__("ยื่นหนังสือหลังกำหนด (ต้องแจ้งภายใน {0}) ผู้ว่าจ้างอาจไม่พิจารณาขยายเวลา", [
				frappe.datetime.str_to_user(deadline),
			]),
			"orange"
		);
	} else {
		frm.set_intro("");
	}
}
