// Script for DocType: Project

// คลังของโครงการ (consbiz/site_stock.py): โครงการใหม่ระบบสร้างคลังให้ตอนบันทึก ชื่อตามช่อง Warehouse Name
// ERPNext แก้ชื่อคลังภายหลังไม่ได้ จึงให้ตั้งตอนสร้าง (ตั้งต้นจากชื่อโครงการ แก้ได้ก่อนบันทึก)
// โครงการเดิมที่ยังไม่มีคลัง กดปุ่ม "สร้างคลังโครงการ" แล้วตั้งชื่อใน dialog

// ความยาวชื่อตั้งต้น (ชื่อโครงการราชการยาวมาก ชื่อคลังยาวเลือกยากบนมือถือ)
const WAREHOUSE_NAME_LENGTH = 40;

frappe.ui.form.on("Project", {
	project_name(frm) {
		if (!frm.is_new()) return;
		const suggestion = (frm.doc.project_name || "").trim().slice(0, WAREHOUSE_NAME_LENGTH);
		// ยังไม่ได้แก้เอง (ว่าง หรือเท่ากับค่าที่ตั้งให้ครั้งก่อน) ตามชื่อโครงการ
		if (!frm.doc.custom_warehouse_name || frm.doc.custom_warehouse_name === frm._warehouse_suggestion) {
			frm.set_value("custom_warehouse_name", suggestion);
		}
		frm._warehouse_suggestion = suggestion;
	},

	async refresh(frm) {
		if (frm.is_new() || !frm.perm[0]?.write) return;
		const count = await frappe.db.count("Warehouse", { filters: { custom_project: frm.doc.name, is_group: 0 } });
		if (count) return;
		frm.add_custom_button(__("สร้างคลังโครงการ"), () => {
			frappe.prompt(
				{
					fieldname: "warehouse_name",
					fieldtype: "Data",
					label: __("ชื่อคลัง"),
					description: __("ตั้งชื่อให้ถูกก่อนสร้าง แก้ภายหลังไม่ได้"),
					default: (frm.doc.custom_warehouse_name || frm.doc.project_name || "").slice(0, WAREHOUSE_NAME_LENGTH),
					reqd: 1,
				},
				async ({ warehouse_name }) => {
					const { message } = await frappe.call({
						method: "consbiz.site_stock.make_project_warehouse",
						args: { project: frm.doc.name, warehouse_name },
						freeze: true,
					});
					frappe.show_alert({ message: __("สร้างคลัง {0} แล้ว", [message]), indicator: "green" });
					frm.reload_doc();
				},
				__("สร้างคลังโครงการ")
			);
		});
	},
});
