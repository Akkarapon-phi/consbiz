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

import { DESKTOP } from "./modules.js";

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
};

// หน้าแรก (Desktop): หมวดพิเศษของทุกแอป /<base>/desktop (component ใส่ใน AppShell)
const DESKTOP_KEY = "desktop";

export function configure(config) {
	Object.assign(app, config);
	app.sections = { [DESKTOP_KEY]: DESKTOP, ...config.sections };
	app.routes = { [DESKTOP_KEY]: { section: DESKTOP_KEY, params: [] }, ...config.routes };
}

export const is_desktop = (section) => section === DESKTOP_KEY;

export const section_of = (view) => app.routes[view]?.section || app.fallback || Object.keys(app.sections)[0];
export const is_tab = (view) => app.sections[section_of(view)].tabs.some((t) => t.view === view);
