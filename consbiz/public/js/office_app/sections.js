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
			{ view: "mr", label: "ขอซื้อ", icon: "clipboard", badge: (s) => s?.mr_todo?.count },
			{ view: "po", label: "สั่งซื้อ", icon: "cart" },
			{
				view: "pi",
				label: "แจ้งหนี้",
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
			{ view: "qtn", label: "เสนอราคา", icon: "file", badge: (s) => s?.qtn_open?.count },
			{ view: "so", label: "สั่งขาย", icon: "clipboard-check" },
			{
				view: "si",
				label: "แจ้งหนี้",
				icon: "receive",
				alert: (s) => s?.si_overdue?.count,
				badge: (s) => s?.si_overdue?.count,
			},
		],
		badge: (s) => s?.si_overdue?.count,
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
};
