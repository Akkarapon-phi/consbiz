// Self Service (/conserp/self) โหลดจาก consbiz/www/self.html งานของพนักงานแต่ละคน (มือถือเป็นหลัก)
// โครงแอป/ตัวช่วย/component กลางอยู่ public/js/shared/ ที่นี่ตั้งค่าเฉพาะของ Self Service
// ลงเวลา / ลา / สลิป (API consbiz/self_service.py) ไม่ผูกโครงการ: โครงการที่ประจำมาจาก Employee.custom_project
import { createApp } from "vue";
import { configure } from "../shared/app.js";
import AppShell from "../shared/AppShell.vue";
import { ROUTES, SECTIONS } from "./sections.js";
import VIEWS from "./views.js";

configure({
	key: "self",
	base: "/conserp",
	storage: "consbiz.self",
	title: "Self Service",
	sections: SECTIONS,
	routes: ROUTES,
	views: VIEWS,
	fallback: "self",
	summary_api: {
		self: () => ["consbiz.self_service.get_summary", {}],
		approve: () => ["consbiz.approvals.get_summary", {}],
	},
	// ไม่ใช้โครงการ และไม่มีตัวเลือกบริษัท (boot ไม่ส่ง companies)
	no_project: true,
	project_key: "consbiz.self.project",
});

const app = createApp(AppShell);
app.config.errorHandler = (error) => {
	// ไม่ให้หน้าค้างขาวทั้งหน้าเมื่อ component ใดพัง
	console.error(error);
};
app.mount("#self-app");
