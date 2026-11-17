// หมวดงานของแอปหน้างาน (/conserp/<หมวด>/<หน้า>/<params...>) ตั้งค่าแอปที่ site_app.bundle.js (configure)
// สลับหมวดผ่าน SectionLauncher.vue (ตารางไอคอน เพิ่มหมวดได้ไม่จำกัด)
// เพิ่มหมวดใหม่: ใส่ใน SECTIONS + หน้าใน ROUTES + component ใน views.js + สิทธิ์ใน site_app.boot_data
// ชื่อหน้า (view) ห้ามซ้ำข้ามหมวด เพราะ go("<view>") หาหมวดจากชื่อหน้า

import { MODULE_META } from "../shared/modules.js";
import { boot } from "../shared/api.js";

// เมนูของแผนงานที่ต้องอ่าน Construction Management ได้ (ทรัพยากรเปิดได้ทุกคนที่เข้าหน้างานได้)
const view_plan = (b) => b.can.view_plan !== false;

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
		// ไม่มีสิทธิ์อ่านแผนงาน (เข้าได้เพื่อดูทรัพยากร) = เปิดหน้าทรัพยากร
		get home() {
			return view_plan(boot) ? "pm" : "resources";
		},
		// summary หนัก (ทั้งแผนงาน) โหลดเมื่อเปิดหมวดนี้เท่านั้น
		lazy: true,
		tabs: [
			{ view: "pm", label: "ภาพรวม", icon: "home", when: view_plan },
			{ view: "plan", label: "แผนงาน", icon: "gantt", when: view_plan },
			{ view: "lookahead", label: "Look-ahead", icon: "calendar", when: view_plan },
			// ทรัพยากร (เดิมเป็นหมวดแยก) ต้องสั่ง / ยอดวัสดุ / คน-เครื่อง / Gantt / รายเดือน เป็น tab ในหน้า (views/resources)
			{ view: "resources", label: "ทรัพยากร", icon: "users" },
			{ view: "resource-supply", label: "ยอดวัสดุ", icon: "package", sub: true },
			{ view: "resource-people", label: "คน/เครื่อง", icon: "users", sub: true },
			{ view: "resource-gantt", label: "Gantt ทรัพยากร", icon: "gantt", sub: true },
			{ view: "resource-monthly", label: "รายเดือน", icon: "calendar", sub: true },
			// เฉพาะผู้ที่เห็นงบต้นทุน (site_app.can_view_finance) Cash Flow / ต้นทุน / Earned Value เป็น tab ในหน้า
			{ view: "finance", label: "การเงิน", icon: "trending", when: (boot) => boot.can?.finance },
			{ view: "pm-docs", label: "เอกสาร", icon: "file", when: view_plan },
		],
	},
	// ขอซื้อ: หน้างานขอวัสดุ/สิ่งของที่ต้องการไปยังออฟฟิศ (ใบขอซื้ออย่างเดียว ไม่มีหน้าหลัก) จัดซื้อทำต่อที่หมวดจัดซื้อ
	// หน้ารายการ/ดู/ฟอร์มใบขอซื้อ (mr, buy-doc, buy-form) เป็นหน้าเดียวกับหมวดจัดซื้อ (shares → routes[].sections ใน site_app.bundle.js)
	// เปิดจากกลุ่มหน้างาน = หมวดนี้ จากกลุ่มออฟฟิศ = จัดซื้อ (section_for ใน app.js) kinds = ชนิดเอกสารที่หมวดนี้เปิด
	buy: {
		key: "buy",
		...MODULE_META.site.buy,
		docs: "buy",
		home: "mr",
		kinds: ["mr"],
		shares: ["mr", "buy-doc", "buy-form"],
		tabs: [{ view: "mr", label: "ขอซื้อ", icon: "clipboard", badge: (s) => s?.mr_todo?.count }],
		badge: (s) => s?.mr_todo?.count,
	},
	// แผนการตัด: แผนตัดเหล็ก (views/work/Rebar*.vue, API consbiz/bar_cut_app.py) เดิมเป็นเมนูในควบคุมงาน
	rebar: {
		key: "rebar",
		...MODULE_META.site.rebar,
		home: "rebar",
		tabs: [{ view: "rebar", label: "แผนการตัด", icon: "list-ordered" }],
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
	// แผนตัดเหล็ก: name = new (แผนใหม่) หรือเลขที่ tab = รายการ / ผลการตัด / ตั้งค่า
	rebar: { section: "rebar", params: [] },
	"rebar-plan": { section: "rebar", params: ["name", "tab"] },
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
	// ทรัพยากร (tab ของหน้าทรัพยากรในแผนงาน)
	resources: { section: "pm", params: [] },
	"resource-supply": { section: "pm", params: [] },
	"resource-people": { section: "pm", params: [] },
	"resource-gantt": { section: "pm", params: [] },
	"resource-monthly": { section: "pm", params: [] },
	// ขอซื้อ (หมวด buy เดิม) รวมเข้าหมวดจัดซื้อ (office_app purchase) ตอนรวม bundle 2026-11-17
};

// หน้าย่อยนับเป็นเมนูไหน (ไฮไลต์ในแถบข้างของจอใหญ่)
export const PARENT_TAB = {
	"receive-form": "receive",
	receipt: "receive",
	"concrete-form": "concrete",
	"rebar-plan": "rebar",
	"borrow-detail": "borrow",
	"borrow-new": "borrow",
	"report-form": "reports",
	"report-view": "reports",
	"plan-edit": "plan",
	"pm-doc": "pm-docs",
	"pm-doc-form": "pm-docs",
	"site-doc": "inspections",
	"site-form": "inspections",
	"resource-supply": "resources",
	"resource-people": "resources",
	"resource-gantt": "resources",
	"resource-monthly": "resources",
};

export const REPORT_KINDS = {
	dr: { doctype: "Daily Report", label: "รายงานประจำวัน", short: "รายงาน", icon: "clipboard" },
	drq: { doctype: "Daily Request", label: "ขออนุมัติปฏิบัติงาน", short: "ขออนุมัติ", icon: "send" },
};
