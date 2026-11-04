// Script for DocType: Item

// Item คู่ของวัสดุผู้ว่าจ้างจัดหา (custom_base_item): ชื่อ กลุ่ม หน่วย และคำอธิบายมาจาก Item หลักเสมอ
// (consbiz/employer_supplied.py ทับค่าตอนบันทึก) จึงล็อกช่องไว้ แก้ที่ Item หลักแทน

const BASE_ITEM_FIELDS = [
	"item_name",
	"item_group",
	"stock_uom",
	"description",
	"image",
	"brand",
	"uoms",
	"is_customer_provided_item",
	"is_purchase_item",
	"is_sales_item",
];

frappe.ui.form.on("Item", {
	refresh(frm) {
		frm.set_intro("");
		if (!frm.doc.custom_base_item) return;
		// ตั้งต่อเอกสาร (docname) ไม่งั้นเปิด Item อื่นในฟอร์มเดิมแล้วช่องยังถูกล็อก
		BASE_ITEM_FIELDS.forEach((field) => frm.set_df_property(field, "read_only", 1, frm.doc.name));
		frm.set_intro(
			__("วัสดุผู้ว่าจ้างจัดหาของ {0}: ชื่อ กลุ่ม และหน่วยตาม Item หลัก ให้แก้ที่ Item หลัก", [
				frm.doc.custom_base_item.bold(),
			]),
			"blue"
		);
	},
});
