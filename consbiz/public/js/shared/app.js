// การตั้งค่าของแต่ละแอป (/site, /office, ...) ที่ใช้โครงกลางชุดเดียวกัน (AppShell.vue + api.js)
// bundle ของแต่ละแอปเรียก configure() ก่อน mount ห้ามอ่านค่าใน app ตอนโหลดโมดูล (import ถูกประมวลผลก่อน configure)
//
// key        ชื่อแอป (data-app ที่ <html>, ตัวสลับแอป)
// base       path ของแอป เช่น "/site" (router: <base>/<หมวด>/<หน้า>/<params...>)
// storage    prefix ของค่าที่จำในเครื่อง เช่น "consbiz.site" (ห้ามเปลี่ยนของแอปเดิม ไม่งั้นค่าที่ผู้ใช้จำไว้หาย)
// title      ชื่อแอป (โลโก้ใน Dock)
// sections   หมวดงาน {key: {label, title, icon, home, theme, colors, tabs, badge, lazy}}
// routes     หน้า → {section, params} ชื่อหน้าห้ามซ้ำข้ามหมวด เพราะ go("<หน้า>") หาหมวดจากชื่อหน้า
// views      หน้า → component
// parent_tab หน้าย่อย → เมนูที่ไฮไลต์ในแถบข้าง
// kind_pages หน้าที่ไฮไลต์เมนูตาม params.kind (หน้าดู/ฟอร์มเอกสารจัดซื้อ/ขาย)
// summary_api หมวด → () => [method, args] ตัวเลขบนเมนู (เรียกพร้อม project)
// fallback   หมวดที่เปิดเมื่อผู้ใช้ไม่มีสิทธิ์หมวดไหนเลย (หน้าแจ้งสิทธิ์เอง)

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
};

export function configure(config) {
	Object.assign(app, config);
}

export const section_of = (view) => app.routes[view]?.section || app.fallback || Object.keys(app.sections)[0];
export const is_tab = (view) => app.sections[section_of(view)].tabs.some((t) => t.view === view);
