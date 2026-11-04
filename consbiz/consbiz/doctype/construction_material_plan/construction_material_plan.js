// Copyright (c) 2026, Siricons and contributors
// For license information, please see license.txt

// แผนจัดซื้อวัสดุ: เลือก WBS ของงาน วัสดุ (Item) จำนวน และ Lead Time
// วันที่ต้องการ/ต้องสั่งคำนวณตอนบันทึกและเลื่อนตามแผนงาน ปุ่ม "สร้าง Material Request" สั่งเฉพาะส่วนที่ยังขาดของแถวที่ถึงกำหนด
// สถานะคิดจากยอด MR/PO/รับของรวมของโครงการ (get_coverage) จะสร้าง MR จากแผนนี้หรือจากหน้า MR เองก็นับเหมือนกัน

const TASK_OPTIONS_API =
	"consbiz.consbiz.doctype.construction_management.construction_management.get_task_options";
const MATERIAL_PLAN_API =
	"consbiz.consbiz.doctype.construction_material_plan.construction_material_plan";

frappe.ui.form.on("Construction Material Plan", {
	setup(frm) {
		frm.set_query("construction_management", () => ({ filters: { status: "Active" } }));
		frm.set_query("warehouse", () => ({ filters: { company: frm.doc.company, is_group: 0 } }));
		// เลือก Item หลัก แล้วติ๊ก "ผู้ว่าจ้างจัดหา" ระบบเปลี่ยนเป็น Item คู่ตอนบันทึก
		frm.set_query("item_code", "items", () => ({ filters: { custom_base_item: ["is", "not set"] } }));
	},

	refresh(frm) {
		load_tasks(frm);
		show_due(frm);
		if (!frm.is_new() && frm.perm[0]?.write) {
			frm.add_custom_button(__("สร้าง Material Request"), () => make_request(frm));
		}
	},

	construction_management: load_tasks,
});

frappe.ui.form.on("Construction Material Plan Item", {
	wbs(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		const task = (frm._tasks || []).find((t) => t.value === row.wbs);
		frappe.model.set_value(cdt, cdn, "item_name", task ? task.label.slice(row.wbs.length + 1) : "");
	},
});

function load_tasks(frm) {
	if (!frm.doc.construction_management) return;
	frappe
		.call(TASK_OPTIONS_API, {
			construction_management: frm.doc.construction_management,
		})
		.then(({ message }) => {
			frm._tasks = message;
			frm.fields_dict.items.grid.update_docfield_property("wbs", "options", message);
		});
}

// เตือนวัสดุที่เลยวันต้องสั่งแล้วแต่ยังขอ (MR) ไม่ครบจำนวน
async function show_due(frm) {
	frm.set_intro("");
	if (frm.is_new()) return;
	const { message: coverage } = await frappe.call({
		method: `${MATERIAL_PLAN_API}.get_coverage`,
		args: { name: frm.doc.name },
	});
	const today = frappe.datetime.get_today();
	const late = (frm.doc.items || []).filter(
		(row) => row.order_by && row.order_by < today && ["none", "partial"].includes(coverage[row.name]?.state)
	);
	frm.set_intro(
		late.length ? __("มีวัสดุ {0} รายการเลยวันที่ต้องสั่งแล้วแต่ยังขอไม่ครบ", [late.length]) : "",
		"red"
	);
}

function make_request(frm) {
	frappe.prompt(
		{
			fieldname: "days",
			label: __("รวมวัสดุที่ต้องสั่งภายใน (วัน)"),
			fieldtype: "Int",
			default: 14,
			reqd: 1,
		},
		({ days }) =>
			frappe
				.call({
					method: `${MATERIAL_PLAN_API}.make_material_request`,
					args: { name: frm.doc.name, days },
					freeze: true,
				})
				.then(({ message }) => {
					frm.reload_doc();
					open_requests(message);
				}),
		__("สร้าง Material Request")
	);
}

// สร้างได้ 1-2 ฉบับ (ซื้อเอง / ผู้ว่าจ้างจัดหา): ฉบับเดียวเปิดเลย หลายฉบับเปิดรายการ
function open_requests(names) {
	if (names.length === 1) frappe.set_route("Form", "Material Request", names[0]);
	else frappe.set_route("List", "Material Request", { name: ["in", names] });
}
