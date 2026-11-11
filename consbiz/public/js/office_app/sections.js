// หมวดงานของแอปออฟฟิศ (/conserp/purchase, /conserp/sales: /conserp/<หมวด>/<หน้า>/<params...>) ตั้งค่าแอปที่ office_app.bundle.js (configure)
// งานออฟฟิศบนจอใหญ่: จัดซื้อ (ขอซื้อ → สั่งซื้อ → แจ้งหนี้) / ขาย (เสนอราคา → สั่งขาย → แจ้งหนี้)
// ต่อไป: บัญชี ประกันผลงาน แอดมิน เพิ่มหมวดใหม่: SECTIONS + ROUTES + views.js + สิทธิ์ใน site_app.office_sections
// ชื่อหน้า (view) ห้ามซ้ำข้ามหมวด เพราะ go("<view>") หาหมวดจากชื่อหน้า

import { MODULE_META } from "../shared/modules.js";

export const SECTIONS = {
	// docs = ชุดเอกสาร (DOC_KINDS[].section) ของหมวด เมื่อชื่อหมวดใน URL ต่างจากชุดเอกสาร
	purchase: {
		key: "purchase",
		...MODULE_META.office.purchase,
		docs: "buy",
		home: "buy",
		tabs: [
			{ view: "buy", label: "หน้าหลัก", icon: "home" },
			{ view: "mr", label: "ขอซื้อ", icon: "clipboard", badge: (s) => s?.mr_todo?.count, when: (b) => b.docs?.mr?.read },
			{ view: "po", label: "สั่งซื้อ", icon: "cart", when: (b) => b.docs?.po?.read },
			{
				view: "pi",
				label: "แจ้งหนี้",
				when: (b) => b.docs?.pi?.read,
				icon: "file",
				alert: (s) => s?.pi_overdue?.count,
				badge: (s) => s?.pi_overdue?.count,
			},
		],
		badge: (s) => s?.mr_todo?.count,
	},
	sales: {
		key: "sales",
		...MODULE_META.office.sales,
		docs: "sell",
		home: "sell",
		tabs: [
			{ view: "sell", label: "หน้าหลัก", icon: "home" },
			{ view: "qtn", label: "เสนอราคา", icon: "file", badge: (s) => s?.qtn_open?.count, when: (b) => b.docs?.qtn?.read },
			{ view: "so", label: "สั่งขาย", icon: "clipboard-check", when: (b) => b.docs?.so?.read },
			{
				view: "si",
				label: "แจ้งหนี้",
				when: (b) => b.docs?.si?.read,
				icon: "receive",
				alert: (s) => s?.si_overdue?.count,
				badge: (s) => s?.si_overdue?.count,
			},
		],
		badge: (s) => s?.si_overdue?.count,
	},
	boq: {
		key: "boq",
		...MODULE_META.office.boq,
		home: "boq",
		tabs: [{ view: "boq", label: "BOQ", icon: "calculator" }],
	},
	hr: {
		key: "hr",
		...MODULE_META.office.hr,
		home: "hr-attendance",
		tabs: [
			{
				view: "hr-attendance",
				label: "สรุปวันทำงาน",
				icon: "calendar",
				badge: (s) => s?.flag,
				alert: (s) => s?.flag,
			},
			{ view: "hr-adjustments", label: "เพิ่ม/หัก", icon: "list", when: (b) => b.can?.payroll },
			{ view: "hr-payroll", label: "เงินเดือน", icon: "receive", when: (b) => b.can?.payroll },
			{ view: "hr-salaries", label: "ค่าจ้างพนักงาน", icon: "users", when: (b) => b.can?.payroll },
			{ view: "hr-advances", label: "เบิกเงิน", icon: "swap" },
			{ view: "hr-setup", label: "ตั้งค่า HR", icon: "sliders" },
		],
		badge: (s) => s?.flag,
	},
};

// view → หมวด + ชื่อ params ตามลำดับใน URL
export const ROUTES = {
	// จัดซื้อ / ขาย: รายการ (filter) และรายละเอียด (kind = mr/po/pi/qtn/so/si)
	buy: { section: "purchase", params: [] },
	mr: { section: "purchase", params: ["filter"] },
	po: { section: "purchase", params: ["filter"] },
	pi: { section: "purchase", params: ["filter"] },
	"buy-doc": { section: "purchase", params: ["kind", "name"] },
	// สร้าง/แก้ไขร่าง: name = new (ใหม่) หรือเลขที่ร่าง, source = เอกสารต้นทาง (สร้างเอกสารถัดไป)
	"buy-form": { section: "purchase", params: ["kind", "name", "source"] },
	sell: { section: "sales", params: [] },
	qtn: { section: "sales", params: ["filter"] },
	so: { section: "sales", params: ["filter"] },
	si: { section: "sales", params: ["filter"] },
	"sell-doc": { section: "sales", params: ["kind", "name"] },
	"sell-form": { section: "sales", params: ["kind", "name", "source"] },
	boq: { section: "boq", params: ["filter"] },
	"boq-form": { section: "boq", params: ["name"] },
	// month = YYYY-MM (ว่าง = เดือนนี้)
	"hr-attendance": { section: "hr", params: ["month"] },
	"hr-payroll": { section: "hr", params: ["month"] },
	"hr-setup": { section: "hr", params: [] },
	"hr-adjustments": { section: "hr", params: ["month"] },
	"hr-salaries": { section: "hr", params: ["filter"] },
	"hr-advances": { section: "hr", params: ["filter"] },
};
