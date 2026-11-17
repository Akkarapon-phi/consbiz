// การตั้งค่าของแต่ละแอป (/site, /office, ...) ที่ใช้โครงกลางชุดเดียวกัน (AppShell.vue + api.js)
// bundle ของแต่ละแอปเรียก configure() ก่อน mount ห้ามอ่านค่าใน app ตอนโหลดโมดูล (import ถูกประมวลผลก่อน configure)
//
// key        ชื่อแอป (data-app ที่ <html>, ตัวสลับแอป)
// base       path ของแอป เช่น "/conserp", "/conserp/office" (router: <base>/<หมวด>/<หน้า>/<params...>)
// storage    prefix ของค่าที่จำในเครื่อง เช่น "consbiz.site" (ห้ามเปลี่ยนของแอปเดิม ไม่งั้นค่าที่ผู้ใช้จำไว้หาย)
// title      ชื่อแอป (โลโก้ใน Dock)
// sections   หมวดงาน {key: {label, title, icon, home, theme, colors, tabs, badge, lazy}}
// routes     หน้า → {section, params} ชื่อหน้าห้ามซ้ำข้ามหมวด เพราะ go("<หน้า>") หาหมวดจากชื่อหน้า
// views      หน้า → component
// parent_tab หน้าย่อย → เมนูที่ไฮไลต์ในแถบข้าง
// kind_pages หน้าที่ไฮไลต์เมนูตาม params.kind (หน้าดู/ฟอร์มเอกสารจัดซื้อ/ขาย)
// summary_api หมวด → () => [method, args] ตัวเลขบนเมนู (เรียกพร้อม project)
// fallback   หมวดที่เปิดเมื่อผู้ใช้ไม่มีสิทธิ์หมวดไหนเลย (หน้าแจ้งสิทธิ์เอง)
// project_filter  true = โครงการเป็นแค่ตัวกรอง (ไม่บังคับเลือก, ว่าง = ทุกโครงการ) + ตัวเลือกบริษัท (แอปออฟฟิศ)
//            false = ต้องเลือกโครงการก่อนใช้งาน (แอปหน้างาน)
// no_project true = แอปไม่ใช้โครงการเลย (Self Service) ไม่โหลดรายชื่อโครงการ ไม่มีปุ่มโครงการ
// project_key  key ที่จำโครงการที่เลือกในเครื่อง
// side_default sidebar เริ่มต้น "collapsed" (ไอคอน) / "expanded" (กาง) ผู้ใช้ปักหมุด/พับเองแล้วจำในเครื่อง
// shortcuts  คีย์ลัดของรายการ/หน้าดูเอกสาร (จอใช้คีย์บอร์ด)
// doc_kinds  ชนิดเอกสารซื้อ-ขาย (shared/docs/kinds.js) ที่แอปนี้ดูแล ชนิดอื่นเปิดในแอปที่ดูแล (DOC_APP)
// section_apps  bundle ที่รวมหลายแอป (ConsERP = หน้างาน + ออฟฟิศ, 2026-11-17): หมวด → แอป (site/office) ใช้หา MODULE_META/กลุ่ม
//            ไม่ระบุ = ทุกหมวดเป็นของ key
// filter_sections  หมวดที่โครงการเป็นแค่ตัวกรอง (หมวดของออฟฟิศ) ระบุแล้ว project_filter = ค่าของหมวดที่เปิดอยู่ (getter)
//            หมวดอื่นต้องเลือกโครงการ ทุกหมวดใช้โครงการที่เลือกชุดเดียวกัน

import { DESKTOP, group_of } from "./modules.js";
import { boot, state } from "./api.js";

export const app = {
	key: "",
	base: "",
	storage: "",
	title: "",
	sections: {},
	routes: {},
	views: {},
	parent_tab: {},
	kind_pages: [],
	summary_api: {},
	fallback: null,
	doc_kinds: [],
	project_filter: false,
	no_project: false,
	project_key: "consbiz.store.project",
	side_default: "collapsed",
	shortcuts: false,
	section_apps: {},
	filter_sections: null,
};

// หน้าแรก (Desktop): หมวดพิเศษของทุกแอป /<base>/desktop (component ใส่ใน AppShell)
const DESKTOP_KEY = "desktop";

export function configure(config) {
	Object.assign(app, config);
	app.sections = { [DESKTOP_KEY]: DESKTOP, ...config.sections };
	app.routes = { [DESKTOP_KEY]: { section: DESKTOP_KEY, params: [] }, ...config.routes };
	if (config.filter_sections) {
		// อ่านตอนใช้งาน (state.section เป็น reactive: computed/template ที่อ่านค่านี้อัปเดตเมื่อสลับหมวด)
		Object.defineProperty(app, "project_filter", {
			get: () => is_filter_section(state.section),
			configurable: true,
		});
	}
}

// หมวดนี้ใช้โครงการเป็นตัวกรอง (ไม่บังคับเลือก) ไหม
export const is_filter_section = (section) =>
	app.filter_sections ? app.filter_sections.includes(section) : !!app.project_filter;
// แอป (site/office/self) ที่เป็นเจ้าของหมวด (MODULE_META[แอป][หมวด])
export const app_of = (section) => app.section_apps?.[section] || app.key;
// แอปที่อยู่ใน bundle นี้ (หมวดของแอปเหล่านี้สลับในหน้าเดียว)
export const local_apps = () => [app.key, ...Object.values(app.section_apps || {})];

export const is_desktop = (section) => section === DESKTOP_KEY;

// หน้าที่อยู่หลายหมวดได้ (routes[view].sections เช่น ใบขอซื้อ: หมวดขอซื้อของหน้างาน + จัดซื้อของออฟฟิศ)
// = หมวดที่เปิดอยู่ถ้าหน้านั้นอยู่ในหมวดนี้ ไม่งั้นหมวดหลัก (section)
export function section_of(view) {
	const route = app.routes[view];
	if (!route) return app.fallback || Object.keys(app.sections)[0];
	if (route.sections?.includes(state.section)) return state.section;
	return route.section;
}
// หน้านี้อยู่ในหมวดนี้ไหม (URL /<หมวด>/<หน้า>)
export const route_in = (view, section) =>
	app.routes[view]?.section === section || !!app.routes[view]?.sections?.includes(section);
// หมวดปลายทางตอนเปิดหน้า (go): หน้าที่อยู่หลายหมวด เลือกหมวดที่ผู้ใช้เข้าได้ + รับชนิดเอกสารนั้น (sections[].kinds)
// ลำดับ: หมวดที่เปิดอยู่ > หมวดในกลุ่มเดียวกัน (หน้างานไปขอซื้อ, ออฟฟิศไปจัดซื้อ) > หมวดแรกที่เข้าได้
export function section_for(view, params = {}) {
	const route = app.routes[view];
	if (!route?.sections) return section_of(view);
	const ok = route.sections.filter(
		(key) =>
			boot.sections?.includes(key) &&
			(!app.sections[key]?.kinds || !params.kind || app.sections[key].kinds.includes(params.kind))
	);
	if (ok.includes(state.section)) return state.section;
	const group = group_of(state.section);
	return ok.find((key) => group_of(key) === group) || ok[0] || route.section;
}
export const is_tab = (view) => app.sections[section_of(view)].tabs.some((t) => t.view === view);
