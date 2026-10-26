// Copyright (c) 2026, Siricons and contributors
// For license information, please see license.txt

// ขออนุมัติปฏิบัติงานประจำวัน: เลือก Construction Management แล้วเลือกงานที่จะทำด้วย WBS
// กรอกปริมาณ (หรือ %) ที่วางแผน ระบบคิด % ความคืบหน้าโครงการที่จะเพิ่มขึ้นจากน้ำหนักงานให้
// ผู้อนุมัติที่เลือกไว้กด Submit = อนุมัติ (ปุ่มไม่อนุมัติ ต้องใส่เหตุผล) อนุมัติแล้วสร้าง Daily Report ต่อได้

const DRQ_API = "consbiz.consbiz.doctype.daily_request.daily_request";
const DR_API = "consbiz.consbiz.doctype.daily_report.daily_report";

frappe.ui.form.on("Daily Request", {
	setup(frm) {
		frm.set_query("construction_management", () => ({ filters: { status: "Active" } }));
		frm.set_query("approver", () => ({ filters: { enabled: 1, user_type: "System User" } }));
	},

	onload(frm) {
		if (!frm.is_new()) return;
		if (!frm.doc.requested_by) frm.set_value("requested_by", frappe.session.user_fullname);
		// ขออนุมัติล่วงหน้า ตั้งต้นเป็นวันพรุ่งนี้
		if (!frm.doc.date) frm.set_value("date", frappe.datetime.add_days(frappe.datetime.get_today(), 1));
		consbiz.fill_default_resources(frm);
		set_last_approver(frm);
	},

	refresh(frm) {
		load_tasks(frm);
		setup_buttons(frm);
		if (frm.doc.docstatus === 0 && frm.doc.status === "Rejected") {
			frm.set_intro(
				__("ไม่อนุมัติ: {0} แก้ไขแล้วบันทึกเพื่อส่งขออนุมัติใหม่", [frm.doc.rejection_reason]),
				"red"
			);
		}
	},

	construction_management(frm) {
		frm.clear_table("items");
		frm.refresh_field("items");
		load_tasks(frm);
		setup_buttons(frm);
		consbiz.fill_default_resources(frm);
		set_last_approver(frm);
	},

	date(frm) {
		load_tasks(frm);
	},

	hide_completed(frm) {
		set_wbs_options(frm);
	},
});

frappe.ui.form.on("Daily Request Item", {
	wbs(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		const task = frm._tasks?.[row.wbs];
		if (!task) return;
		Object.assign(row, task_values(task));
		update_row(frm, row, "qty");
	},
	qty(frm, cdt, cdn) {
		update_row(frm, locals[cdt][cdn], "qty");
	},
	percent(frm, cdt, cdn) {
		update_row(frm, locals[cdt][cdn], "percent");
	},
	items_remove(frm) {
		update_total(frm);
	},
});

function setup_buttons(frm) {
	frm.clear_custom_buttons();
	if (!frm.doc.construction_management) return;
	if (frm.doc.docstatus === 0) {
		frm.add_custom_button(__("ดึงงานตามแผนของวันนั้น"), () => add_planned_tasks(frm));
		if (!frm.is_new() && frm.doc.status !== "Rejected" && is_approver(frm)) {
			frm.add_custom_button(__("ไม่อนุมัติ"), () => reject(frm));
		}
	}
	if (frm.doc.docstatus === 1) add_report_button(frm);
	frm.add_custom_button(__("เปิด Gantt"), () =>
		frappe.set_route("construction-gantt", frm.doc.construction_management)
	);
}

// ผู้อนุมัติที่ระบุ หรือ System Manager (ต้องตรงกับ check_approver ฝั่ง Python)
function is_approver(frm) {
	return frappe.session.user === frm.doc.approver || frappe.user.has_role("System Manager");
}

// คำขอใหม่: ตั้งผู้อนุมัติเป็นคนเดียวกับคำขอล่าสุดของแผนงานนี้
function set_last_approver(frm) {
	if (!frm.is_new() || frm.doc.approver || !frm.doc.construction_management) return;
	frappe
		.call(`${DRQ_API}.get_last_approver`, {
			construction_management: frm.doc.construction_management,
		})
		.then(({ message }) => message && !frm.doc.approver && frm.set_value("approver", message));
}

// 1 คำขอมี Daily Report ได้ฉบับเดียว: มีแล้ว (Draft/Submit) = ปุ่มเปิด, ยังไม่มีหรือยกเลิกแล้ว = ปุ่มสร้าง
function add_report_button(frm) {
	frappe.call(`${DRQ_API}.get_daily_report`, { name: frm.doc.name }).then(({ message: report }) => {
		if (report) {
			frm.add_custom_button(__("เปิด Daily Report"), () =>
				frappe.set_route("Form", "Daily Report", report)
			);
		} else if (frappe.model.can_create("Daily Report")) {
			frm.add_custom_button(__("สร้าง Daily Report"), () =>
				frappe.model.open_mapped_doc({ method: `${DRQ_API}.make_daily_report`, frm })
			);
		}
	});
}

function reject(frm) {
	frappe.prompt(
		{ fieldname: "reason", fieldtype: "Small Text", label: __("เหตุผลที่ไม่อนุมัติ"), reqd: 1 },
		({ reason }) =>
			frappe
				.call({ method: `${DRQ_API}.reject`, args: { name: frm.doc.name, reason }, freeze: true })
				.then(() => frm.reload_doc()),
		__("ไม่อนุมัติ"),
		__("ไม่อนุมัติ")
	);
}

function load_tasks(frm) {
	const grid = frm.fields_dict.items.grid;
	if (!frm.doc.construction_management) {
		frm._tasks = {};
		grid.update_docfield_property("wbs", "options", []);
		return;
	}
	frappe
		.call(`${DR_API}.get_tasks`, {
			construction_management: frm.doc.construction_management,
			date: frm.doc.date,
		})
		.then(({ message }) => {
			frm._tasks = Object.fromEntries(message.map((t) => [t.wbs, t]));
			set_wbs_options(frm);
		});
}

// ตัวเลือก WBS: ค้นได้ทั้ง WBS ชื่องาน และหัวข้อหลัก ติ๊ก "ซ่อน WBS ที่ทำครบแล้ว" จะไม่แสดงงานที่ครบ 100%
function set_wbs_options(frm) {
	const tasks = Object.values(frm._tasks || {}).filter(
		(t) => !frm.doc.hide_completed || t.previous_percent < 100
	);
	frm.fields_dict.items.grid.update_docfield_property(
		"wbs",
		"options",
		tasks.map((t) => ({
			value: t.wbs,
			label: `${t.wbs} ${t.item_name}`,
			description: [
				t.group_path,
				t.quantity
					? __("คงเหลือ {0} {1}", [
							format_number(flt(t.quantity - t.previous_qty, 6), null, 2),
							t.uom || "",
					  ])
					: __("ทำแล้ว {0}%", [format_number(t.previous_percent, null, 2)]),
				t.in_plan ? __("อยู่ในแผน") : null,
			]
				.filter(Boolean)
				.join(" · "),
		}))
	);
}

function task_values(task) {
	return {
		task: task.name,
		item_name: task.item_name,
		group_path: task.group_path,
		uom: task.uom,
		boq_qty: task.quantity,
		weight: task.weight,
		previous_qty: task.previous_qty,
		previous_percent: task.previous_percent,
		in_plan: task.in_plan ? 1 : 0,
	};
}

// งานที่มีปริมาณ: qty <-> % แปลงกันตามปริมาณ BOQ, งานเหมา: ใช้ % อย่างเดียว (ต้องตรงกับ set_row ฝั่ง Python)
function update_row(frm, row, source) {
	consbiz.fit_to_remaining(row, source);
	if (row.boq_qty > 0) {
		if (source === "qty") row.percent = ((row.qty || 0) / row.boq_qty) * 100;
		else row.qty = ((row.percent || 0) * row.boq_qty) / 100;
		row.remaining_qty = flt(row.boq_qty - (row.previous_qty || 0) - (row.qty || 0), 6);
	} else {
		row.qty = 0;
		row.remaining_qty = 0;
	}
	row.project_percent = ((row.percent || 0) * (row.weight || 0)) / 100;
	update_total(frm);
	frm.refresh_field("items");
}

function update_total(frm) {
	const planned = (frm.doc.items || []).reduce((sum, row) => sum + (row.project_percent || 0), 0);
	frm.set_value("planned_progress", planned);
	frm.set_value("expected_progress", Math.min((frm.doc.current_progress || 0) + planned, 100));
}

// เพิ่มงานที่อยู่ในช่วงแผนของวันที่ขออนุมัติและยังทำไม่ครบ (ข้ามงานที่มีในตารางแล้ว)
function add_planned_tasks(frm) {
	const existing = new Set((frm.doc.items || []).map((row) => row.wbs));
	const tasks = Object.values(frm._tasks || {}).filter(
		(t) => t.in_plan && t.previous_percent < 100 && !existing.has(t.wbs)
	);
	if (!tasks.length) {
		frappe.show_alert({
			message: __("ไม่มีงานตามแผนที่ยังไม่ครบในวันนั้น"),
			indicator: "orange",
		});
		return;
	}
	// ตารางว่างที่มีแถวเปล่าอยู่ 1 แถวให้ลบทิ้งก่อน
	frm.doc.items = (frm.doc.items || []).filter((row) => row.wbs);
	for (const task of tasks) {
		frm.add_child("items", {
			wbs: task.wbs,
			...task_values(task),
			remaining_qty: task.quantity ? flt(task.quantity - task.previous_qty, 6) : 0,
		});
	}
	frm.refresh_field("items");
	frappe.show_alert({
		message: __("เพิ่ม {0} งาน กรอกปริมาณที่จะทำ แถวที่ไม่ได้ทำให้ลบออก", [tasks.length]),
		indicator: "green",
	});
}
