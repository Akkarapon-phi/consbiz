// แอปหน้างาน (/site) โหลดจาก consbiz/www/site.html แบ่งหมวดงาน (sections.js) สลับในแอป
// โครงแอป/ตัวช่วย/component กลางอยู่ public/js/shared/ (ใช้ร่วมกับแอปอื่น) ที่นี่ตั้งค่าเฉพาะของ /site
// สโตร์ (views/store, API consbiz/store_app.py) / ควบคุมงาน + บริหารโครงการ (views/work, views/pm, API consbiz/site_app.py)
// ขอซื้อ (shared/docs เฉพาะใบขอซื้อ, API consbiz/site_docs.py) สั่งซื้อ/แจ้งหนี้/ขายอยู่แอปออฟฟิศ (/office)
import { createApp } from "vue";
import { configure } from "../shared/app.js";
import { scope_args } from "../shared/api.js";
import AppShell from "../shared/AppShell.vue";
import { PARENT_TAB, ROUTES, SECTIONS } from "./sections.js";
import VIEWS from "./views.js";

configure({
	key: "site",
	base: "/conserp",
	// ค่าที่ผู้ใช้จำไว้ในเครื่อง (หมวดล่าสุด, sidebar) ใช้ชื่อเดิม ห้ามเปลี่ยน
	storage: "consbiz.site",
	title: "ConsERP",
	sections: SECTIONS,
	routes: ROUTES,
	views: VIEWS,
	parent_tab: PARENT_TAB,
	kind_pages: ["buy-doc", "buy-form"],
	summary_api: {
		store: () => ["get_summary", {}],
		work: () => ["consbiz.site_app.get_work_summary", {}],
		pm: () => ["consbiz.site_app.get_pm_summary", {}],
		buy: () => ["consbiz.site_docs.get_summary", { section: "buy", ...scope_args() }],
	},
	// ไม่มีสิทธิ์หมวดไหนเลย: เปิดหมวดสโตร์ (แต่ละหน้าแจ้งสิทธิ์เองเหมือนแอปสโตร์เดิม)
	fallback: "store",
	doc_kinds: ["mr"],
});

const app = createApp(AppShell);
app.config.errorHandler = (error) => {
	// ไม่ให้หน้าค้างขาวทั้งหน้าเมื่อ component ใดพัง
	console.error(error);
};
app.mount("#site-app");
