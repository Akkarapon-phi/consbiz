// ConsERP (/conserp/<หมวด>) bundle เดียวของหน้างาน + ออฟฟิศ (รวม 2026-11-17: สลับหมวดข้ามกลุ่มไม่โหลดหน้าใหม่)
// โหลดจาก consbiz/www/site.html (ทุกหมวดของสองแอปนี้ website_route_rules ไปหน้าเดียวกัน) boot = consbiz.site_app.boot_data
// หน้างาน (site_app/: สโตร์ ควบคุมงาน แผนงาน แผนการตัด) ต้องเลือกโครงการ
// ออฟฟิศ (office_app/: จัดซื้อ ขาย บัญชี บุคคล BOQ สารบรรณ ผู้รับเหมา คนงาน ข้อมูลหลัก) โครงการเป็นตัวกรอง (filter_sections) + ตัวเลือกบริษัท
// โครงกลาง/component อยู่ public/js/shared/ Self Service (self_app) และแอปผู้รับเหมา (contractor_app) ยังแยก bundle
import { createApp } from "vue";
import { configure } from "../shared/app.js";
import { boot, scope_args } from "../shared/api.js";
import AppShell from "../shared/AppShell.vue";
import { PARENT_TAB, ROUTES, SECTIONS } from "./sections.js";
import VIEWS from "./views.js";
import {
	KIND_PAGES as OFFICE_KIND_PAGES,
	PARENT_TAB as OFFICE_PARENT_TAB,
	ROUTES as OFFICE_ROUTES,
	SECTIONS as OFFICE_SECTIONS,
	SUMMARY_API as OFFICE_SUMMARY_API,
} from "../office_app/sections.js";
import OFFICE_VIEWS from "../office_app/views.js";

// หน้าที่หมวดของหน้างานใช้ร่วมกับหมวดของออฟฟิศ (ใบขอซื้อ: ขอซื้อ + จัดซื้อ) อยู่ได้ทั้งสองหมวด
const routes = { ...ROUTES, ...OFFICE_ROUTES };
for (const [key, section] of Object.entries(SECTIONS))
	for (const view of section.shares || []) routes[view] = { ...routes[view], sections: [routes[view].section, key] };

configure({
	key: "site",
	base: "/conserp",
	// ค่าที่ผู้ใช้จำไว้ในเครื่อง (หมวดล่าสุด, sidebar) ใช้ชื่อเดิม ห้ามเปลี่ยน
	storage: "consbiz.site",
	title: "ConsERP",
	sections: { ...SECTIONS, ...OFFICE_SECTIONS },
	routes,
	views: { ...VIEWS, ...OFFICE_VIEWS },
	parent_tab: { ...PARENT_TAB, ...OFFICE_PARENT_TAB },
	kind_pages: OFFICE_KIND_PAGES,
	section_apps: Object.fromEntries(Object.keys(OFFICE_SECTIONS).map((key) => [key, "office"])),
	filter_sections: Object.keys(OFFICE_SECTIONS),
	summary_api: {
		store: () => ["get_summary", {}],
		work: () => ["consbiz.site_app.get_work_summary", {}],
		pm: () => (boot.can.view_plan === false ? null : ["consbiz.site_app.get_pm_summary", {}]),
		buy: () => ["consbiz.site_docs.get_summary", { section: "buy", ...scope_args("buy") }],
		...OFFICE_SUMMARY_API,
	},
	// ไม่มีสิทธิ์หมวดไหนเลย: เปิดหมวดสโตร์ (แต่ละหน้าแจ้งสิทธิ์เอง)
	fallback: "store",
	doc_kinds: ["mr", "po", "pi", "qtn", "so", "si"],
	shortcuts: true,
});

const app = createApp(AppShell);
app.config.errorHandler = (error) => {
	// ไม่ให้หน้าค้างขาวทั้งหน้าเมื่อ component ใดพัง
	console.error(error);
};
app.mount("#site-app");
