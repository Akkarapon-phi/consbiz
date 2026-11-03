// page จำลองเมื่อ Gantt ฝังใน Tab ของฟอร์ม Construction Management (ดูอย่างเดียว)
// มีเมธอดเท่าที่ App.vue เรียกกับ frappe.ui.Page แต่ไม่ทำอะไร: ไม่แตะ Header ของฟอร์ม
// ปุ่มบันทึก/พิมพ์/คำสั่ง/สถานะอยู่ในหน้าเต็มจอ ส่วน Tab มีแค่ ViewBar
export function make_embedded_page() {
	const noop = () => {};
	return {
		set_title: noop,
		clear_actions: noop,
		clear_menu: noop,
		clear_icons: noop,
		set_primary_action: noop,
		add_action_icon: noop,
		add_menu_item: noop,
		set_indicator: noop,
		clear_indicator: noop,
	};
}
