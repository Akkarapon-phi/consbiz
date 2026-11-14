// หมวดงานของแอปหน้างาน (/conserp/<หมวด>/<หน้า>/<params...>) ตั้งค่าแอปที่ site_app.bundle.js (configure)
// สลับหมวดผ่าน SectionLauncher.vue (ตารางไอคอน เพิ่มหมวดได้ไม่จำกัด)
// เพิ่มหมวดใหม่: ใส่ใน SECTIONS + หน้าใน ROUTES + component ใน views.js + สิทธิ์ใน site_app.boot_data
// ชื่อหน้า (view) ห้ามซ้ำข้ามหมวด เพราะ go("<view>") หาหมวดจากชื่อหน้า

import { MODULE_META } from "../shared/modules.js";

export const SECTIONS = {
	store: {
		key: "store",
		...MODULE_META.site.store,
		home: "home",
		// badge(summary) = ตัวเลขบนเมนู, alert(summary) = แดง
		tabs: [
			{ view: "home", label: "หน้าหลัก", icon: "home" },
			{
				view: "receive",
				label: "รับของ",
				icon: "receive",
				badge: (s) => s?.pending_count,
				when: (b) => b.can.receive || b.can.receive_employer || b.can.view_receive,
			},
			{ view: "issue", label: "เบิก", icon: "issue", when: (b) => b.can.issue || b.can.view_stock },
			{
				view: "borrow",
				label: "ยืม-คืน",
				icon: "wrench",
				when: (b) => b.can.borrow || b.can.view_borrow,
				badge: (s) => s?.borrow_count,
				alert: (s) => s?.overdue_count,
			},
			{ view: "stock", label: "คลัง", icon: "warehouse", when: (b) => b.can.view_stock },
		],
		// ตัวเลขบนปุ่มสลับหมวด (งานที่รอทำในหมวดนั้น)
		badge: (s) => s?.pending_count,
	},
	work: {
		key: "work",
		...MODULE_META.site.work,
		home: "work",
		tabs: [
			{ view: "work", label: "ภาพรวม", icon: "home" },
			{
				view: "reports",
				label: "รายงาน",
				icon: "clipboard",
				badge: (s) => s?.requests_pending,
				when: (b) => b.can.view_daily_report || b.can.view_daily_request,
			},
			{ view: "concrete", label: "คอนกรีต", icon: "truck", when: (b) => b.can.concrete || b.can.view_concrete },
			{
				view: "inspections",
				label: "ตรวจงาน",
				when: (b) => b.can.inspection || b.can.punch_list,
				icon: "search-check",
				badge: (s) => (s?.inspections_pending || 0) + (s?.inspections_failed || 0),
				alert: (s) => s?.inspections_failed,
			},
		],
		badge: (s) => (s?.requests_pending || 0) + (s?.inspections_pending || 0),
	},
	pm: {
		key: "pm",
		...MODULE_META.site.pm,
		home: "pm",
		// summary หนัก (ทั้งแผนงาน) โหลดเมื่อเปิดหมวดนี้เท่านั้น
		lazy: true,
		tabs: [
			{ view: "pm", label: "ภาพรวม", icon: "home" },
			{ view: "plan", label: "แผนงาน", icon: "gantt" },
			{ view: "lookahead", label: "Look-ahead", icon: "calendar" },
			// เฉพาะผู้ที่เห็นงบต้นทุน (site_app.can_view_finance) Cash Flow / ต้นทุน / Earned Value เป็น tab ในหน้า
			{ view: "finance", label: "การเงิน", icon: "trending", when: (boot) => boot.can?.finance },
			{ view: "pm-docs", label: "เอกสาร", icon: "file" },
		],
	},
	resources: {
		key: "resources",
		...MODULE_META.site.resources,
		home: "resources",
		tabs: [
			{ view: "resources", label: "ต้องสั่ง", icon: "cart" },
			{ view: "resource-supply", label: "ยอดวัสดุ", icon: "package" },
			{ view: "resource-people", label: "คน/เครื่อง", icon: "users" },
			{ view: "resource-gantt", label: "Gantt", icon: "gantt" },
			{ view: "resource-monthly", label: "รายเดือน", icon: "calendar" },
		],
	},
	// ขอซื้อ: หน้างานสร้าง/ติดตามใบขอซื้อ สั่งซื้อ/แจ้งหนี้/ขาย ทำที่แอปออฟฟิศ (/office)
	buy: {
		key: "buy",
		...MODULE_META.site.buy,
		home: "buy",
		tabs: [
			{ view: "buy", label: "หน้าหลัก", icon: "home" },
			{ view: "mr", label: "ขอซื้อ", icon: "clipboard", badge: (s) => s?.mr_todo?.count },
		],
		badge: (s) => s?.mr_todo?.count,
	},
	// ธุรการโครงการ: ลงเวลาคนงานรายวัน (Labour Timesheet รายรอบ) + ทะเบียนคนงาน
	admin: {
		key: "admin",
		...MODULE_META.site.admin,
		home: "labour",
		tabs: [
			{ view: "labour", label: "ลงเวลาคนงาน", icon: "clock", when: (b) => b.can.view_labour },
			{ view: "advances", label: "เบิกล่วงหน้า", icon: "calculator", when: (b) => b.can.view_advances },
			{ view: "workers", label: "ทะเบียนคนงาน", icon: "users", when: (b) => b.can.view_workers },
		],
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
	reports: { section: "work", params: ["tab", "day"] },
	// kind = dr (Daily Report) / drq (Daily Request), name = new: เอกสารใหม่ (date, from = Daily Request ที่อนุมัติแล้ว)
	"report-form": { section: "work", params: ["kind", "name", "date", "from"] },
	"report-view": { section: "work", params: ["kind", "name"] },
	inspections: { section: "work", params: ["tab"] },
	"site-doc": { section: "work", params: ["kind", "name"] },
	"site-form": { section: "work", params: ["kind", "name", "source"] },
	concrete: { section: "work", params: [] },
	"concrete-form": { section: "work", params: ["name"] },
	// แผนงาน
	pm: { section: "pm", params: [] },
	plan: { section: "pm", params: [] },
	// แก้แผนงาน (Gantt ของระบบเต็มใน iframe) cm = ชื่อ Construction Management (ว่าง = ของโครงการที่เลือก)
	"plan-edit": { section: "pm", params: ["cm"] },
	lookahead: { section: "pm", params: ["week"] },
	"pm-docs": { section: "pm", params: ["tab"] },
	// งานลด-เพิ่ม / EOT (kind = vo / eot, name = new: เอกสารใหม่) ขอตรวจงาน/Punch List ใช้ site-doc / site-form ของหมวดควบคุมงาน
	"pm-doc": { section: "pm", params: ["kind", "name"] },
	"pm-doc-form": { section: "pm", params: ["kind", "name", "source"] },
	// การเงิน (tab = cost / evm ว่าง = Cash Flow)
	finance: { section: "pm", params: ["tab"] },
	// ทรัพยากร
	resources: { section: "resources", params: [] },
	"resource-supply": { section: "resources", params: [] },
	"resource-people": { section: "resources", params: [] },
	"resource-gantt": { section: "resources", params: [] },
	"resource-monthly": { section: "resources", params: [] },
	// ขอซื้อ: รายการ (filter) รายละเอียด และฟอร์ม (kind = mr เท่านั้น ชนิดอื่นเปิดในแอปออฟฟิศ)
	buy: { section: "buy", params: [] },
	mr: { section: "buy", params: ["filter"] },
	"buy-doc": { section: "buy", params: ["kind", "name"] },
	"buy-form": { section: "buy", params: ["kind", "name", "source"] },
	// ธุรการ: day = วันใดก็ได้ในรอบ (ว่าง = รอบปัจจุบัน)
	labour: { section: "admin", params: ["day"] },
	advances: { section: "admin", params: [] },
	workers: { section: "admin", params: [] },
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
	"plan-edit": "plan",
	"pm-doc": "pm-docs",
	"pm-doc-form": "pm-docs",
	"site-doc": "inspections",
	"site-form": "inspections",
};

export const REPORT_KINDS = {
	dr: { doctype: "Daily Report", label: "รายงานประจำวัน", short: "รายงาน", icon: "clipboard" },
	drq: { doctype: "Daily Request", label: "ขออนุมัติปฏิบัติงาน", short: "ขออนุมัติ", icon: "send" },
};
