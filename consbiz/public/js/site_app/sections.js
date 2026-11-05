// หมวดงานของแอปหน้างาน (/site/<หมวด>/<หน้า>/<params...>) ตั้งค่าแอปที่ site_app.bundle.js (configure)
// สลับหมวดผ่าน SectionLauncher.vue (ตารางไอคอน เพิ่มหมวดได้ไม่จำกัด)
// เพิ่มหมวดใหม่: ใส่ใน SECTIONS + หน้าใน ROUTES + component ใน views.js + สิทธิ์ใน site_app.boot_data
// ชื่อหน้า (view) ห้ามซ้ำข้ามหมวด เพราะ go("<view>") หาหมวดจากชื่อหน้า

export const SECTIONS = {
	store: {
		key: "store",
		label: "สโตร์",
		title: "สโตร์หน้างาน",
		note: "รับของ เบิก ยืม-คืน คลัง",
		icon: "package",
		home: "home",
		theme: "#1f6feb",
		colors: ["#1f6feb", "#5b3df5"],
		// badge(summary) = ตัวเลขบนเมนู, alert(summary) = แดง
		tabs: [
			{ view: "home", label: "หน้าหลัก", icon: "home" },
			{ view: "receive", label: "รับของ", icon: "receive", badge: (s) => s?.pending_count },
			{ view: "issue", label: "เบิก", icon: "issue" },
			{
				view: "borrow",
				label: "ยืม-คืน",
				icon: "wrench",
				badge: (s) => s?.borrow_count,
				alert: (s) => s?.overdue_count,
			},
			{ view: "stock", label: "คลัง", icon: "warehouse" },
		],
		// ตัวเลขบนปุ่มสลับหมวด (งานที่รอทำในหมวดนั้น)
		badge: (s) => s?.pending_count,
	},
	work: {
		key: "work",
		label: "ควบคุมงาน",
		title: "ควบคุมงาน",
		note: "ความคืบหน้า รายงานประจำวัน คอนกรีต ตรวจงาน",
		icon: "hardhat",
		home: "work",
		theme: "#e8590c",
		colors: ["#e8590c", "#d6336c"],
		tabs: [
			{ view: "work", label: "หน้าหลัก", icon: "home" },
			{ view: "reports", label: "รายงาน", icon: "clipboard", badge: (s) => s?.requests_pending },
			{ view: "concrete", label: "คอนกรีต", icon: "concrete" },
			{
				view: "inspections",
				label: "ตรวจงาน",
				icon: "search-check",
				badge: (s) => (s?.inspections_pending || 0) + (s?.inspections_failed || 0),
				alert: (s) => s?.inspections_failed,
			},
		],
		badge: (s) => (s?.requests_pending || 0) + (s?.inspections_pending || 0),
	},
	pm: {
		key: "pm",
		label: "บริหารโครงการ",
		title: "บริหารโครงการ",
		note: "ภาพรวม แผนงาน Look-ahead ทรัพยากร แผนจัดซื้อวัสดุ เอกสาร",
		icon: "gantt",
		home: "pm",
		theme: "#6d4cf6",
		colors: ["#6d4cf6", "#2563eb"],
		// summary หนัก (ทั้งแผนงาน) โหลดเมื่อเปิดหมวดนี้เท่านั้น
		lazy: true,
		tabs: [
			{ view: "pm", label: "ภาพรวม", icon: "home" },
			{ view: "plan", label: "แผนงาน", icon: "gantt" },
			{ view: "lookahead", label: "Look-ahead", icon: "calendar" },
			{ view: "resources", label: "ทรัพยากร", icon: "users" },
			{ view: "pm-docs", label: "เอกสาร", icon: "file", wide_only: true },
		],
	},
	// ขอซื้อ: หน้างานสร้าง/ติดตามใบขอซื้อ สั่งซื้อ/แจ้งหนี้/ขาย ทำที่แอปออฟฟิศ (/office)
	buy: {
		key: "buy",
		label: "ขอซื้อ",
		title: "ขอซื้อ",
		note: "ขอซื้อวัสดุ ติดตามการสั่งซื้อ/รับของ",
		icon: "cart",
		home: "buy",
		theme: "#0d9488",
		colors: ["#0d9488", "#0284c7"],
		tabs: [
			{ view: "buy", label: "หน้าหลัก", icon: "home" },
			{ view: "mr", label: "ขอซื้อ", icon: "clipboard", badge: (s) => s?.mr_todo?.count },
		],
		badge: (s) => s?.mr_todo?.count,
	},
};

// view → หมวด + ชื่อ params ตามลำดับใน URL
export const ROUTES = {
	// สโตร์
	home: { section: "store", params: [] },
	receive: { section: "store", params: ["tab"] },
	"receive-form": { section: "store", params: ["doctype", "name"] },
	receipt: { section: "store", params: ["doctype", "name"] },
	issue: { section: "store", params: ["tab"] },

	borrow: { section: "store", params: ["tab"] },
	"borrow-detail": { section: "store", params: ["name"] },
	"borrow-new": { section: "store", params: [] },
	stock: { section: "store", params: [] },
	// ควบคุมงาน
	work: { section: "work", params: [] },
	reports: { section: "work", params: ["day"] },
	// kind = dr (Daily Report) / drq (Daily Request), name = new: เอกสารใหม่ (date, from = Daily Request ที่อนุมัติแล้ว)
	"report-form": { section: "work", params: ["kind", "name", "date", "from"] },
	"report-view": { section: "work", params: ["kind", "name"] },
	inspections: { section: "work", params: ["tab"] },
	concrete: { section: "work", params: [] },
	"concrete-form": { section: "work", params: ["name"] },
	// บริหารโครงการ
	pm: { section: "pm", params: [] },
	plan: { section: "pm", params: [] },
	lookahead: { section: "pm", params: ["week"] },
	"pm-docs": { section: "pm", params: [] },
	// tab = labour (คน/เครื่องจักร) / material (แผนจัดซื้อวัสดุ)
	resources: { section: "pm", params: ["tab"] },
	// ขอซื้อ: รายการ (filter) รายละเอียด และฟอร์ม (kind = mr เท่านั้น ชนิดอื่นเปิดในแอปออฟฟิศ)
	buy: { section: "buy", params: [] },
	mr: { section: "buy", params: ["filter"] },
	"buy-doc": { section: "buy", params: ["kind", "name"] },
	"buy-form": { section: "buy", params: ["kind", "name", "source"] },
};

// หน้าย่อยนับเป็นเมนูไหน (ไฮไลต์ในแถบข้างของจอใหญ่)
export const PARENT_TAB = {
	"receive-form": "receive",
	receipt: "receive",
	"concrete-form": "concrete",
	"borrow-detail": "borrow",
	"borrow-new": "borrow",
	"report-form": "reports",
	"report-view": "reports",
};

export const REPORT_KINDS = {
	dr: { doctype: "Daily Report", label: "รายงานประจำวัน", short: "รายงาน", icon: "clipboard" },
	drq: { doctype: "Daily Request", label: "ขออนุมัติปฏิบัติงาน", short: "ขออนุมัติ", icon: "send" },
};
