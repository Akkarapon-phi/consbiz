// แอปออฟฟิศ (/office) โหลดจาก consbiz/www/office.html งานออฟฟิศบนจอใหญ่ แบ่งหมวด (sections.js)
// โครงแอป/ตัวช่วย/component กลางอยู่ public/js/shared/ (ชุดเดียวกับแอปหน้างาน) ที่นี่ตั้งค่าเฉพาะของ /office
// จัดซื้อ/ขาย (shared/docs, API consbiz/site_docs.py)
import { createApp } from "vue";
import { configure } from "../shared/app.js";
import { scope_args } from "../shared/api.js";
import AppShell from "../shared/AppShell.vue";
import { ROUTES, SECTIONS } from "./sections.js";
import VIEWS from "./views.js";

configure({
	key: "office",
	// ทุกหมวดอยู่ระดับเดียวกับหมวดของหน้างาน (/conserp/<หมวด>) server เลือก bundle ตามชื่อหมวด (website_route_rules)
	base: "/conserp",
	storage: "consbiz.office",
	title: "ConsOffice",
	sections: SECTIONS,
	routes: ROUTES,
	views: VIEWS,
	parent_tab: { "boq-form": "boq" },
	kind_pages: ["buy-doc", "sell-doc", "buy-form", "sell-form"],
	summary_api: {
		purchase: () => ["consbiz.site_docs.get_summary", { section: "buy", ...scope_args() }],
		sales: () => ["consbiz.site_docs.get_summary", { section: "sell", ...scope_args() }],
		hr: () => ["consbiz.hr_attendance.get_summary", scope_args()],
	},
	fallback: "purchase",
	doc_kinds: ["mr", "po", "pi", "qtn", "so", "si"],
	// งานออฟฟิศดูหลายโครงการ: โครงการเป็นตัวกรอง + ตัวเลือกบริษัท + คีย์ลัด
	project_filter: true,
	project_key: "consbiz.office.project",
	shortcuts: true,
});

const app = createApp(AppShell);
app.config.errorHandler = (error) => {
	// ไม่ให้หน้าค้างขาวทั้งหน้าเมื่อ component ใดพัง
	console.error(error);
};
app.mount("#office-app");
