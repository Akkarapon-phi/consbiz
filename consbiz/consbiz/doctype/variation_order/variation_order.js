// Copyright (c) 2026, Siricons and contributors
// For license information, please see license.txt

// งานลด-งานเพิ่ม: เลือก Construction Management แล้วกรอกรายการ
// งานเพิ่ม: เลือก WBS เดิมเมื่อเพิ่มปริมาณของรายการเดิม หรือเว้นว่างแล้วพิมพ์ชื่องานใหม่ งานลด: ต้องเลือก WBS เดิม
// Submit = มีผลกับแผนงาน หลัง Submit แก้ Qty / Rate / Amount ได้ (ปริมาณประมาณการ) แล้วกด Update

const VO_API = "consbiz.consbiz.doctype.variation_order.variation_order";

frappe.ui.form.on("Variation Order", {
	setup(frm) {
		frm.set_query("construction_management", () => ({ filters: { status: "Active" } }));
	},

	refresh(frm) {
		load_tasks(frm);
		if (frm.doc.construction_management && !frm.is_new()) {
			frm.add_custom_button(__("เปิด Gantt"), () =>
				frappe.set_route("construction-gantt", frm.doc.construction_management)
			);
		}
		if (frm.doc.docstatus === 1 && frm.doc.is_provisional) {
			frm.set_intro(
				__("ปริมาณยังเป็นประมาณการ แก้ Qty / Rate ในตารางแล้วกด Update ได้จนกว่าจะได้ตัวเลขจริง"),
				"orange"
			);
		}
	},

	construction_management(frm) {
		frm.clear_table("items");
		frm.refresh_field("items");
		load_tasks(frm);
	},
});

frappe.ui.form.on("Variation Order Item", {
	wbs(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		const task = frm._tasks?.[row.wbs];
		if (!task) return;
		Object.assign(row, {
			task: task.name,
			item_name: task.item_name,
			uom: task.uom,
			rate: task.rate,
			contract_qty: task.contract_quantity,
			done_qty: task.done_qty,
		});
		update_amount(frm, row);
	},
	variation_type(frm, cdt, cdn) {
		update_amount(frm, locals[cdt][cdn]);
	},
	qty(frm, cdt, cdn) {
		update_amount(frm, locals[cdt][cdn]);
	},
	rate(frm, cdt, cdn) {
		update_amount(frm, locals[cdt][cdn]);
	},
	amount(frm) {
		update_totals(frm);
	},
	items_remove(frm) {
		update_totals(frm);
	},
});

function load_tasks(frm) {
	const grid = frm.fields_dict.items.grid;
	if (!frm.doc.construction_management) {
		frm._tasks = {};
		grid.update_docfield_property("wbs", "options", []);
		return;
	}
	frappe
		.call(`${VO_API}.get_tasks`, { construction_management: frm.doc.construction_management })
		.then(({ message }) => {
			frm._tasks = Object.fromEntries(message.map((t) => [t.wbs, t]));
			grid.update_docfield_property(
				"wbs",
				"options",
				message.map((t) => ({
					value: t.wbs,
					label: `${t.wbs} ${t.item_name}`,
					description: [
						t.group_path,
						t.contract_quantity
							? __("ตามสัญญา {0} {1} · ทำแล้ว {2}", [
									format_number(t.contract_quantity, null, 2),
									t.uom || "",
									format_number(t.done_qty, null, 2),
							  ])
							: __("งานเหมา"),
					]
						.filter(Boolean)
						.join(" · "),
				}))
			);
		});
}

// งานที่มีปริมาณ: มูลค่า = Qty × Rate, งานเหมา (ไม่มี Qty): กรอกมูลค่าเอง
function update_amount(frm, row) {
	if (row.qty > 0) row.amount = flt(row.qty * (row.rate || 0), precision("amount", row));
	frm.refresh_field("items");
	update_totals(frm);
}

function update_totals(frm) {
	const sum = (type) =>
		(frm.doc.items || [])
			.filter((row) => row.variation_type === type)
			.reduce((total, row) => total + (row.amount || 0), 0);
	const addition = sum("Addition");
	const omission = sum("Omission");
	frm.doc.addition_amount = addition;
	frm.doc.omission_amount = omission;
	frm.doc.net_amount = addition - omission;
	frm.doc.revised_amount =
		(frm.doc.contract_amount || 0) + (frm.doc.previous_variation_amount || 0) + frm.doc.net_amount;
	frm.refresh_fields(["addition_amount", "omission_amount", "net_amount", "revised_amount"]);
}
