// แอปผู้รับเหมาช่วง (/contractor) โหลดจาก consbiz/www/contractor.html สำหรับคนนอก (Website User ผูกกับ Supplier)
// ใช้โครงแอปกลาง (shared/) API ทั้งหมดอยู่ consbiz/contractor_app.py (ห้ามเรียก API ภายในอื่น ผู้ใช้ไม่มีสิทธิ์ DocType)
import { createApp } from "vue";
import { boot } from "../shared/api.js";
import { configure } from "../shared/app.js";
import AppShell from "../shared/AppShell.vue";
import { PARENT_TAB, ROUTES, SECTIONS } from "./sections.js";
import VIEWS from "./views.js";

configure({
	key: "contractor",
	// ลิงก์ของสัญญา: URL ทุกหน้าอยู่ใต้ /contractor/k/<token> (โหลดหน้าใหม่แล้วยังเป็นลิงก์เดิม)
	base: boot.token ? `/contractor/k/${boot.token}` : "",
	storage: "consbiz.contractor",
	title: "ผู้รับเหมา",
	sections: SECTIONS,
	routes: ROUTES,
	views: VIEWS,
	parent_tab: PARENT_TAB,
	fallback: "contractor",
	summary_api: {
		contractor: () => ["consbiz.contractor_app.get_summary", boot.token ? { token: boot.token } : {}],
	},
	no_project: true,
	project_key: "consbiz.contractor.project",
});

const app = createApp(AppShell);
app.config.errorHandler = (error) => {
	console.error(error);
};
app.mount("#contractor-app");
