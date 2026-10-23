// Copyright (c) 2026, Siricons and contributors
// For license information, please see license.txt

// รายงานประจำวัน: เลือก Construction Management แล้วเลือกงานในตารางด้วย WBS (ค้นด้วยชื่องานได้)
// กรอก Qty ที่ทำได้วันนี้ ระบบคิด % และปริมาณคงเหลือให้ (งานเหมากรอก % ตรงๆ)

const DR_API = "consbiz.consbiz.doctype.daily_report.daily_report";

frappe.ui.form.on("Daily Report", {
	setup(frm) {
		frm.set_query("construction_management", () => ({ filters: { status: "Active" } }));
	},

	onload(frm) {
		if (frm.is_new() && !frm.doc.supervisor_name) {
			frm.set_value("supervisor_name", frappe.session.user_fullname);
		}
	},

	refresh(frm) {
		load_tasks(frm);
		setup_buttons(frm);
	},

	construction_management(frm) {
		frm.clear_table("items");
		frm.refresh_field("items");
		load_tasks(frm);
		setup_buttons(frm);
	},

	date(frm) {
		load_tasks(frm);
	},

	hide_completed(frm) {
		set_wbs_options(frm);
	},
});

frappe.ui.form.on("Daily Report Item", {
	wbs(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		const task = frm._tasks?.[row.wbs];
		if (!task) return;
		Object.assign(row, {
			task: task.name,
			item_name: task.item_name,
			group_path: task.group_path,
			uom: task.uom,
			boq_qty: task.quantity,
			previous_qty: task.previous_qty,
			previous_percent: task.previous_percent,
		});
		update_amounts(frm, row, "qty");
	},
	qty(frm, cdt, cdn) {
		update_amounts(frm, locals[cdt][cdn], "qty");
	},
	percent(frm, cdt, cdn) {
		update_amounts(frm, locals[cdt][cdn], "percent");
	},
});

function setup_buttons(frm) {
	frm.clear_custom_buttons();
	if (!frm.doc.construction_management) return;
	if (frm.doc.docstatus === 0) {
		frm.add_custom_button(__("ดึงงานตามแผนของวันนี้"), () => add_planned_tasks(frm));
	}
	frm.add_custom_button(__("เปิด Gantt"), () =>
		frappe.set_route("construction-gantt", frm.doc.construction_management)
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
			report: frm.is_new() ? null : frm.doc.name,
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
			]
				.filter(Boolean)
				.join(" · "),
		}))
	);
}

// งานที่มีปริมาณ: qty <-> % แปลงกันตามปริมาณ BOQ, งานเหมา: ใช้ % อย่างเดียว
function update_amounts(frm, row, source) {
	if (row.boq_qty > 0) {
		if (source === "qty") row.percent = ((row.qty || 0) / row.boq_qty) * 100;
		else row.qty = ((row.percent || 0) * row.boq_qty) / 100;
		row.remaining_qty = flt(row.boq_qty - (row.previous_qty || 0) - (row.qty || 0), 6);
	} else {
		row.qty = 0;
		row.remaining_qty = 0;
	}
	const task = frm._tasks?.[row.wbs];
	if (task) {
		row.rate = task.rate;
		row.amount = ((task.amount || 0) * (row.percent || 0)) / 100;
	}
	frm.set_value(
		"total_amount",
		(frm.doc.items || []).reduce((sum, item) => sum + (item.amount || 0), 0)
	);
	frm.refresh_field("items");
}

// เพิ่มงานที่อยู่ในช่วงแผนของวันที่รายงานและยังทำไม่ครบ (ข้ามงานที่มีในตารางแล้ว)
function add_planned_tasks(frm) {
	const existing = new Set((frm.doc.items || []).map((row) => row.wbs));
	const tasks = Object.values(frm._tasks || {}).filter(
		(t) => t.in_plan && t.previous_percent < 100 && !existing.has(t.wbs)
	);
	if (!tasks.length) {
		frappe.show_alert({
			message: __("ไม่มีงานตามแผนที่ยังไม่ครบในวันนี้"),
			indicator: "orange",
		});
		return;
	}
	// ตารางว่างที่มีแถวเปล่าอยู่ 1 แถวให้ลบทิ้งก่อน
	frm.doc.items = (frm.doc.items || []).filter((row) => row.wbs);
	for (const task of tasks) {
		frm.add_child("items", {
			wbs: task.wbs,
			task: task.name,
			item_name: task.item_name,
			group_path: task.group_path,
			uom: task.uom,
			boq_qty: task.quantity,
			rate: task.rate,
			previous_qty: task.previous_qty,
			previous_percent: task.previous_percent,
			remaining_qty: task.quantity ? flt(task.quantity - task.previous_qty, 6) : 0,
		});
	}
	frm.refresh_field("items");
	frappe.show_alert({
		message: __("เพิ่ม {0} งาน กรอกปริมาณที่ทำได้ แถวที่ไม่ได้ทำให้ลบออก", [tasks.length]),
		indicator: "green",
	});
}
