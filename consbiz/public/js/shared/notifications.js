// การแจ้งเตือนของผู้ใช้ (Notification Log ของ Frappe ชุดเดียวกับกระดิ่งในระบบเต็ม) ใช้ร่วมทุกหน้า: TopBar สร้างใหม่ทุกครั้งที่เปลี่ยนหน้า
// ใช้ POST เพราะ get_notification_logs ตั้ง http_cache ไว้ (GET ได้ค่าเก่าหลังกดอ่าน)
import { reactive } from "vue";
import { boot, call, desk_url, go, post, state } from "./api.js";
import { app } from "./app.js";
import { DOC_KINDS, open_doc } from "./docs/kinds.js";

const API = "frappe.desk.doctype.notification_log.notification_log";
const REFRESH_INTERVAL = 60000;

export const notifications = reactive({ items: [], loaded: false });

export async function refresh_notifications() {
	try {
		const message = await post(`${API}.get_notification_logs`, { limit: 30 });
		notifications.items = message.notification_logs || [];
	} catch {
		// ไม่ใช่งานหลักของหน้า: ไม่แจ้ง error รอรอบถัดไป
	}
	notifications.loaded = true;
}

let started = false;
export function start_notifications() {
	if (started) return;
	started = true;
	refresh_notifications();
	setInterval(() => !document.hidden && refresh_notifications(), REFRESH_INTERVAL);
	document.addEventListener("visibilitychange", () => !document.hidden && refresh_notifications());
}

export function mark_read(item) {
	if (item.read) return;
	item.read = 1;
	post(`${API}.mark_as_read`, { docname: item.name }).catch(() => {});
}

export function mark_all_read() {
	notifications.items.forEach((item) => (item.read = 1));
	post(`${API}.mark_all_as_read`).catch(() => {});
}

// เอกสารนอก DOC_KINDS ที่มีหน้าในแอป: args เรียงตาม params ของหน้านั้นใน ROUTES (ใส่ name ต่อท้าย)
// project = หน้าผูกกับโครงการ ต้องสลับไปโครงการของเอกสารก่อน (ตรงกับ PROJECT_PAGE_DOCTYPES ใน site_app.py)
const APP_PAGES = {
	"Daily Report": { section: "work", view: "report-view", args: { kind: "dr" }, project: true },
	"Daily Request": { section: "work", view: "report-view", args: { kind: "drq" }, project: true },
	"Inspection Request": { section: "work", view: "site-doc", args: { kind: "inspection" }, project: true },
	"Punch List": { section: "work", view: "site-doc", args: { kind: "punch" }, project: true },
	"Concrete Usage": { section: "work", view: "concrete-form", args: {}, project: true },
	"Variation Order": { section: "pm", view: "pm-doc", args: { kind: "vo" }, project: true },
	"Extension of Time": { section: "pm", view: "pm-doc", args: { kind: "eot" }, project: true },
	"Equipment Borrowing": { section: "store", view: "borrow-detail", args: {}, project: true },
	"Purchase Receipt": { section: "store", view: "receipt", args: { doctype: "Purchase Receipt" } },
	BOQ: { section: "boq", view: "boq-form", args: {} },
	// งาน HR: ผู้อนุมัติ = โมดูลอนุมัติ (เปิดใบนั้น) ไม่มีสิทธิ์ = หน้าของตัวเองใน Self Service (หน้าแรกที่เข้าหมวดได้)
	"Employee Checkin": [
		{ section: "approve", view: "approve", args: {} },
		{ section: "self", view: "checkin", args: {}, no_name: true },
	],
	"Leave Application": [
		{ section: "approve", view: "approve", args: {} },
		{ section: "self", view: "leave", args: {}, no_name: true },
	],
	"Employee Advance": [
		{ section: "approve", view: "approve", args: {} },
		{ section: "self", view: "advances", args: {}, no_name: true },
	],
	"Expense Claim": [
		{ section: "approve", view: "approve", args: {} },
		{ section: "self", view: "advances", args: {}, no_name: true },
	],
};

// เปิดเอกสารจากการแจ้งเตือน: ในแอปถ้ามีหน้าและผู้ใช้เข้าหมวดนั้นได้ ที่เหลือเปิดระบบเต็มในแท็บใหม่
export async function open_document(doctype, name) {
	const kind = Object.keys(DOC_KINDS).find((key) => DOC_KINDS[key].doctype === doctype);
	if (kind) return open_doc(kind, name);

	// หลายหน้า = หน้าแรกที่ผู้ใช้เข้าหมวดนั้นได้
	const can_open = (p) => (boot.modules || []).some((m) => m.section === p.section);
	const pages = [APP_PAGES[doctype]].flat().filter(Boolean);
	const page = pages.find(can_open);
	if (!page) {
		window.open(desk_url(doctype, name), "_blank", "noopener");
		return;
	}
	let project = null;
	if (page.project) {
		project = await call("consbiz.site_app.get_doc_project", { doctype, name }).catch(() => null);
		// หลัง await เบราว์เซอร์มือถือบล็อก window.open จึงเปลี่ยนหน้าเดิม
		if (!project) {
			window.location.href = desk_url(doctype, name);
			return;
		}
	}
	const args = page.no_name ? { ...page.args } : { ...page.args, name };
	if (app.routes[page.view] && (!project || state.project?.name === project)) {
		go(page.view, args);
		return;
	}
	// คนละกลุ่มแอป หรือคนละโครงการ: โหลดหน้าใหม่ (AppShell เลือกโครงการจาก ?project=)
	const path = [app.base, page.section, page.view, ...Object.values(args).map(encodeURIComponent)].join("/");
	window.location.href = project ? `${path}?project=${encodeURIComponent(project)}` : path;
}
