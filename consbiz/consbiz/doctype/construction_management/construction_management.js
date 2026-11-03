// Copyright (c) 2026, Siricons and contributors
// For license information, please see license.txt

// Tab "ภาพรวม", "Gantt", "ทรัพยากร", "Look-ahead" และ "เอกสารโครงการ" เป็น Vue โหลดเมื่อเปิด Tab ครั้งแรก
// - ภาพรวม / ทรัพยากร / Look-ahead / เอกสารโครงการ: public/js/project_dashboard โหลดข้อมูลใหม่ทุกครั้งที่ฟอร์ม refresh
// - Gantt: public/js/construction_management แบบฝัง (embedded) ดูอย่างเดียว แก้แผนที่หน้าเต็มจอ (ปุ่มแก้ไขแผนงาน)
//   ซิงก์กับฐานข้อมูลเอง ฟอร์ม refresh แล้วโหลดใหม่เฉพาะเมื่อแผนเปลี่ยน (activate) ตำแหน่งที่เลื่อนไว้จึงไม่หาย
//   เปิด Tab ที่ wide (Gantt, Look-ahead) แล้วซ่อนแผงข้างขวาของฟอร์มให้กว้างเต็มที่ (class consbiz-wide-form ใน style.css)
// ปุ่มสร้างเอกสารอยู่ใน Tab เอกสารโครงการ Header ของฟอร์มจึงไม่มีปุ่มเพิ่ม
const PROJECT_TABS = [
	{
		tab: "dashboard_tab",
		field: "dashboard_html",
		bundle: "project_dashboard.bundle.js",
		make: (frm, wrapper) => new consbiz.ProjectDashboard({ wrapper, name: frm.doc.name }),
	},
	{
		tab: "gantt_tab",
		field: "gantt_html",
		bundle: "construction_management.bundle.js",
		wide: true,
		self_sync: true,
		make: (frm, wrapper) =>
			new consbiz.ConstructionGantt({
				wrapper,
				schedule: frm.doc.name,
				embedded: true,
				// มองเห็นอยู่ = Tab Gantt เปิดอยู่และหน้าฟอร์มนี้แสดงอยู่
				is_active: () => wrapper.offsetParent !== null,
				on_saved: () => !frm.is_dirty() && frm.reload_doc(),
			}),
	},
	{
		tab: "resources_tab",
		field: "resources_html",
		bundle: "project_dashboard.bundle.js",
		make: (frm, wrapper) => new consbiz.ProjectResources({ wrapper, name: frm.doc.name }),
	},
	{
		tab: "lookahead_tab",
		field: "lookahead_html",
		bundle: "project_dashboard.bundle.js",
		wide: true,
		make: (frm, wrapper) => new consbiz.ProjectLookAhead({ wrapper, name: frm.doc.name }),
	},
	{
		tab: "finance_tab",
		field: "finance_html",
		bundle: "project_dashboard.bundle.js",
		make: (frm, wrapper) => new consbiz.ProjectFinance({ wrapper, name: frm.doc.name }),
	},
	{
		tab: "documents_tab",
		field: "documents_html",
		bundle: "project_dashboard.bundle.js",
		make: (frm, wrapper) => new consbiz.ProjectDocuments({ wrapper, name: frm.doc.name }),
	},
];

frappe.ui.form.on("Construction Management", {
	refresh(frm) {
		if (!frm.is_new()) {
			setup_project_tabs(frm);
		}
		frm.set_df_property("tasks", "cannot_add_rows", true);
	},

	boq(frm) {
		// boq แก้ได้เฉพาะตอนสร้าง (set_only_once) เลือกแล้วดึงงานทั้งหมดมาแทนตารางเดิม
		if (!frm.is_new()) return;
		if (!frm.doc.boq) {
			frm.clear_table("tasks");
			frm.refresh_field("tasks");
			return;
		}
		frappe
			.call({
				method: "consbiz.consbiz.doctype.construction_management.construction_management.get_boq_plan",
				args: { boq: frm.doc.boq },
				freeze: true,
			})
			.then(({ message: plan }) => {
				const start_date = frm.doc.start_date || plan.start_date;
				for (const key of ["project", "start_date", "holiday_list"]) {
					if (!frm.doc[key] && plan[key]) frm.set_value(key, plan[key]);
				}
				frm.clear_table("tasks");
				plan.tasks.forEach((task) => frm.add_child("tasks", { ...task, start_date }));
				frm.refresh_field("tasks");
			});
	},
});

frappe.ui.form.on("Construction Management Task", {
	duration(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (!row.start_date || row.is_group) return;
		// นับแบบปฏิทินคำนวณวันจบได้เลย ถ้านับวันทำงานให้ server คำนวณตอนบันทึก (ต้องใช้วันหยุด)
		const end_date = frm.doc.use_working_days
			? null
			: frappe.datetime.add_days(row.start_date, Math.max(row.duration || 1, 1) - 1);
		frappe.model.set_value(cdt, cdn, "end_date", end_date);
	},
});

function setup_project_tabs(frm) {
	const find_tab = (fieldname) => frm.layout.tabs.find((t) => t.df.fieldname === fieldname);
	for (const config of PROJECT_TABS) {
		const tab = find_tab(config.tab);
		if (!tab) continue;
		tab.tab_link
			.find(".nav-link")
			.off("click.consbiz")
			.on("click.consbiz", () => mount_project_view(frm, config));
		// เปิดอยู่แล้ว (เช่น บันทึกเอกสารขณะอยู่ใน Tab) หรือเคยเปิดแล้ว: โหลดข้อมูลใหม่
		if (tab.is_active() || frm._consbiz_views?.[config.field]) mount_project_view(frm, config);
	}
	// Tab ที่ต้องการพื้นที่กว้าง (Gantt): ซ่อนแผงข้างขวาของฟอร์มเฉพาะตอนเปิด Tab นั้น
	const set_wide = () =>
		frm.page.wrapper.toggleClass(
			"consbiz-wide-form",
			PROJECT_TABS.some((config) => config.wide && find_tab(config.tab)?.is_active())
		);
	for (const tab of frm.layout.tabs) {
		tab.tab_link
			.find(".nav-link")
			.off("click.consbiz-wide")
			.on("click.consbiz-wide", () => setTimeout(set_wide));
	}
	set_wide();
}

function mount_project_view(frm, config) {
	frappe.require(config.bundle).then(() => {
		frm._consbiz_views = frm._consbiz_views || {};
		const view = frm._consbiz_views[config.field];
		if (view?.name === frm.doc.name) {
			if (config.self_sync) setTimeout(() => view.activate());
			else view.reload();
			return;
		}
		view?.destroy();
		frm._consbiz_views[config.field] = config.make(frm, frm.fields_dict[config.field].$wrapper.get(0));
	});
}
