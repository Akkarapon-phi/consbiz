// ข้อมูลหลัก (API consbiz/master_data.py) key = ชื่อหน้ารายการ = KINDS ใน master_data.py
// หน้าข้อมูล = md-doc/<kind>/<name> (MasterPage.vue) ฟอร์มสร้างจาก sections ที่ server ส่งมา

export const API = "consbiz.master_data";

const on = (r) => !Number(r.disabled);
const off = (r) => !!Number(r.disabled);
const all = () => true;
const PARTY_TYPES = {
	Company: "นิติบุคคล",
	Individual: "บุคคลธรรมดา",
	Partnership: "ห้างหุ้นส่วน",
};
const base = (kind, label, icon) => ({
	api: API,
	boot: "master",
	label,
	icon,
	open: (r) => ["md-doc", { kind, name: r.name }],
	create: () => ["md-doc", { kind, name: "new" }],
});
const party = (r) =>
	[PARTY_TYPES[r.customer_type || r.supplier_type], r.tax_id && `เลขภาษี ${r.tax_id}`]
		.filter(Boolean)
		.join(" · ");
const active_filters = [
	{ value: "active", label: "ใช้งาน", test: on },
	{ value: "disabled", label: "ปิดใช้งาน", test: off },
	{ value: "all", label: "ทั้งหมด", test: all },
];

export const MASTER_KINDS = {
	"md-employees": {
		...base("md-employees", "พนักงาน", "users"),
		create_label: "พนักงานใหม่",
		title: (r) => r.employee_name,
		title_label: "ชื่อ-นามสกุล",
		party: (r) => [r.designation, r.department].filter(Boolean).join(" · "),
		party_label: "ตำแหน่ง / แผนก",
		date: "date_of_joining",
		date_label: "เริ่มงาน",
		search: ["name", "employee_name", "designation", "department", "project"],
		filters: [
			{ value: "active", label: "ทำงานอยู่", test: (r) => r.status === "Active" },
			{ value: "left", label: "ลาออก", test: (r) => r.status === "Left" },
			{ value: "all", label: "ทั้งหมด", test: all },
		],
	},
	"md-items": {
		...base("md-items", "สินค้า/วัสดุ", "package"),
		create_label: "สินค้าใหม่",
		title: (r) => r.item_name,
		title_label: "ชื่อสินค้า/วัสดุ",
		party: (r) => [r.item_group, r.stock_uom].filter(Boolean).join(" · "),
		party_label: "กลุ่ม · หน่วย",
		date: "creation",
		date_label: "สร้างเมื่อ",
		search: ["name", "item_name", "item_group"],
		filters: active_filters,
	},
	"md-customers": {
		...base("md-customers", "ลูกค้า", "building"),
		create_label: "ลูกค้าใหม่",
		title: (r) => r.customer_name,
		title_label: "ชื่อลูกค้า",
		party,
		party_label: "ประเภท / เลขภาษี",
		date: "creation",
		date_label: "สร้างเมื่อ",
		search: ["name", "customer_name", "tax_id", "customer_group"],
		filters: active_filters,
	},
	"md-suppliers": {
		...base("md-suppliers", "ผู้ขาย", "truck"),
		create_label: "ผู้ขายใหม่",
		title: (r) => r.supplier_name,
		title_label: "ชื่อผู้ขาย",
		party,
		party_label: "ประเภท / เลขภาษี",
		date: "creation",
		date_label: "สร้างเมื่อ",
		search: ["name", "supplier_name", "tax_id", "supplier_group"],
		filters: active_filters,
	},
	"md-projects": {
		...base("md-projects", "โครงการ", "briefcase"),
		create_label: "โครงการใหม่",
		title: (r) => r.project_name,
		title_label: "ชื่อโครงการ",
		party: (r) => r.customer_name,
		party_label: "ผู้ว่าจ้าง",
		date: "expected_start_date",
		date_label: "เริ่มสัญญา",
		search: ["name", "project_name", "customer_name", "custom_abbr"],
		filters: [
			{ value: "open", label: "ดำเนินการ", test: (r) => r.status === "Open" },
			{ value: "done", label: "เสร็จสิ้น", test: (r) => r.status === "Completed" },
			{ value: "all", label: "ทั้งหมด", test: all },
		],
	},
};
