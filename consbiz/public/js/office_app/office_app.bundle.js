// แอปออฟฟิศ (/office) โหลดจาก consbiz/www/office.html งานออฟฟิศบนจอใหญ่ แบ่งหมวด (sections.js)
// โครงแอป/ตัวช่วย/component กลางอยู่ public/js/shared/ (ชุดเดียวกับแอปหน้างาน) ที่นี่ตั้งค่าเฉพาะของ /office
// จัดซื้อ/ขาย (shared/docs, API consbiz/site_docs.py)
import { createApp } from "vue";
import { configure } from "../shared/app.js";
import { state } from "../shared/api.js";
import AppShell from "../shared/AppShell.vue";
import { ROUTES, SECTIONS } from "./sections.js";
import VIEWS from "./views.js";

configure({
	key: "office",
	base: "/office",
	storage: "consbiz.office",
	title: "ConsOffice",
	sections: SECTIONS,
	routes: ROUTES,
	views: VIEWS,
	parent_tab: {},
	kind_pages: ["buy-doc", "sell-doc", "buy-form", "sell-form"],
	summary_api: {
		buy: () => ["consbiz.site_docs.get_summary", { section: "buy", scope: state.doc_scope }],
		sell: () => ["consbiz.site_docs.get_summary", { section: "sell", scope: state.doc_scope }],
	},
	fallback: "buy",
	doc_kinds: ["mr", "po", "pi", "qtn", "so", "si"],
});

const app = createApp(AppShell);
app.config.errorHandler = (error) => {
	// ไม่ให้หน้าค้างขาวทั้งหน้าเมื่อ component ใดพัง
	console.error(error);
};
app.mount("#office-app");
