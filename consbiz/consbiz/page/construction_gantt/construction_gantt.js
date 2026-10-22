// เปิดที่ /app/construction-gantt/<ชื่อ Construction Management>
// ตัวหน้าจอเป็น Vue อยู่ที่ public/js/construction_management/

frappe.pages["construction-gantt"].on_page_load = (wrapper) => {
	frappe.ui.make_app_page({
		parent: wrapper,
		title: __("แผนงานก่อสร้าง"),
		single_column: true,
	});

	if (frappe.boot.developer_mode) {
		frappe.hot_update = frappe.hot_update || [];
		frappe.hot_update.push(() => load_gantt(wrapper, true));
	}
};

frappe.pages["construction-gantt"].on_page_show = (wrapper) => load_gantt(wrapper);

function load_gantt(wrapper, force) {
	const schedule = frappe.get_route()[1];
	if (!schedule) {
		frappe.set_route("List", "Construction Management");
		return;
	}
	if (!force && wrapper.gantt && wrapper.gantt_schedule === schedule) return;

	frappe.require("construction_management.bundle.js").then(() => {
		wrapper.gantt?.destroy();
		const $parent = $(wrapper).find(".layout-main-section").empty();
		wrapper.gantt_schedule = schedule;
		wrapper.gantt = new consbiz.ConstructionGantt({
			wrapper: $parent.get(0),
			page: wrapper.page,
			schedule,
		});
	});
}
