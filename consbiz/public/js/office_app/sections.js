// หมวดงานของแอปออฟฟิศ (/office/<หมวด>/<หน้า>/<params...>) ตั้งค่าแอปที่ office_app.bundle.js (configure)
// งานออฟฟิศบนจอใหญ่: จัดซื้อ (ขอซื้อ → สั่งซื้อ → แจ้งหนี้) / ขาย (เสนอราคา → สั่งขาย → แจ้งหนี้)
// ต่อไป: บัญชี ประกันผลงาน แอดมิน เพิ่มหมวดใหม่: SECTIONS + ROUTES + views.js + สิทธิ์ใน site_app.office_sections
// ชื่อหน้า (view) ห้ามซ้ำข้ามหมวด เพราะ go("<view>") หาหมวดจากชื่อหน้า

export const SECTIONS = {
	buy: {
		key: "buy",
		label: "จัดซื้อ",
		title: "จัดซื้อ",
		note: "ขอซื้อ สั่งซื้อ ใบแจ้งหนี้ซื้อ",
		icon: "cart",
		home: "buy",
		theme: "#0d9488",
		colors: ["#0d9488", "#0284c7"],
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
	sell: {
		key: "sell",
		label: "ขาย",
		title: "ขาย",
		note: "ใบเสนอราคา ใบสั่งขาย ใบแจ้งหนี้",
		icon: "trending",
		home: "sell",
		theme: "#c026d3",
		colors: ["#c026d3", "#7c3aed"],
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
	buy: { section: "buy", params: [] },
	mr: { section: "buy", params: ["filter"] },
	po: { section: "buy", params: ["filter"] },
	pi: { section: "buy", params: ["filter"] },
	"buy-doc": { section: "buy", params: ["kind", "name"] },
	// สร้าง/แก้ไขร่าง: name = new (ใหม่) หรือเลขที่ร่าง, source = เอกสารต้นทาง (สร้างเอกสารถัดไป)
	"buy-form": { section: "buy", params: ["kind", "name", "source"] },
	sell: { section: "sell", params: [] },
	qtn: { section: "sell", params: ["filter"] },
	so: { section: "sell", params: ["filter"] },
	si: { section: "sell", params: ["filter"] },
	"sell-doc": { section: "sell", params: ["kind", "name"] },
	"sell-form": { section: "sell", params: ["kind", "name", "source"] },
};
