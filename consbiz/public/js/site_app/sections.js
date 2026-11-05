// หมวดงานของแอปหน้างาน (/site/<หมวด>/<หน้า>/<params...>)
// สลับหมวดผ่าน SectionLauncher.vue (ตารางไอคอน เพิ่มหมวดได้ไม่จำกัด)
// เพิ่มหมวดใหม่: ใส่ใน SECTIONS + หน้าใน ROUTES + component ใน VIEWS ของ App.vue + สิทธิ์ใน site_app.boot_data
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

// เอกสารจัดซื้อ/ขาย (consbiz/site_docs.py DOCS) filters = ตัวกรองรายการ, project = มีช่องโครงการ
export const DOC_KINDS = {
	mr: {
		doctype: "Material Request",
		section: "buy",
		label: "ใบขอซื้อ",
		icon: "clipboard",
		tone: "teal",
		project: true,
		todo: "รอสั่งซื้อ",
		progress: [
			["per_ordered", "สั่งซื้อ"],
			["per_received", "รับของ"],
		],
	},
	po: {
		doctype: "Purchase Order",
		section: "buy",
		label: "ใบสั่งซื้อ",
		icon: "cart",
		tone: "blue",
		project: true,
		party: "ผู้ขาย",
		todo: "รอรับ/วางบิล",
		due: "กำหนดส่ง",
		progress: [
			["per_received", "รับของ"],
			["per_billed", "วางบิล"],
		],
	},
	pi: {
		doctype: "Purchase Invoice",
		section: "buy",
		label: "ใบแจ้งหนี้ซื้อ",
		icon: "file",
		tone: "violet",
		project: true,
		party: "ผู้ขาย",
		todo: "ค้างจ่าย",
		due: "ครบกำหนดจ่าย",
	},
	qtn: {
		doctype: "Quotation",
		section: "sell",
		label: "ใบเสนอราคา",
		icon: "file",
		tone: "violet",
		project: false,
		party: "ลูกค้า",
		todo: "รอตอบรับ",
		due: "ยืนราคาถึง",
	},
	so: {
		doctype: "Sales Order",
		section: "sell",
		label: "ใบสั่งขาย",
		icon: "clipboard-check",
		tone: "blue",
		project: true,
		party: "ลูกค้า",
		todo: "รอส่งมอบ/วางบิล",
		due: "กำหนดส่งมอบ",
		progress: [
			["per_delivered", "ส่งมอบ"],
			["per_billed", "วางบิล"],
		],
	},
	si: {
		doctype: "Sales Invoice",
		section: "sell",
		label: "ใบแจ้งหนี้ขาย",
		icon: "receive",
		tone: "green",
		project: true,
		party: "ลูกค้า",
		todo: "ค้างรับ",
		due: "ครบกำหนดรับ",
	},
};

export const REPORT_KINDS = {
	dr: { doctype: "Daily Report", label: "รายงานประจำวัน", short: "รายงาน", icon: "clipboard" },
	drq: { doctype: "Daily Request", label: "ขออนุมัติปฏิบัติงาน", short: "ขออนุมัติ", icon: "send" },
};

export const section_of = (view) => ROUTES[view]?.section || "store";
export const is_tab = (view) => SECTIONS[section_of(view)].tabs.some((t) => t.view === view);
