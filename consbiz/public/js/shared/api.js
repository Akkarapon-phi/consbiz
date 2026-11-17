// ตัวช่วยกลางของทุกแอป (/site, /office, ...): เรียก API, อัปโหลดรูป,
// router (<base>/<หมวด>/<หน้า>/...), สลับหมวดงาน, toast, รูปแบบตัวเลข/วันที่
// ค่าของแต่ละแอป (หมวด/หน้า/base) อยู่ใน app.js (configure ใน bundle ของแอป)
import { reactive } from "vue";
import { app, is_desktop, is_filter_section, is_tab, route_in, section_for, section_of } from "./app.js";
import { NEW_LOOK, is_company_section } from "./modules.js";

const API = "consbiz.store_app.";
const section_key = () => `${app.storage}.section`;

// ข้อมูลตั้งต้นจากหน้า www ของแอป (boot_data ฝั่ง server)
export const boot = window.APP_BOOT || window.SITE_BOOT || {};

function remembered(key, fallback) {
	try {
		return localStorage.getItem(key) || fallback;
	} catch {
		return fallback;
	}
}

// เงินแบบย่อ (ล้าน / พัน) และเต็ม
export function money(value, { short = false } = {}) {
	const n = Number(value) || 0;
	if (short && !n) return "0";
	if (short && Math.abs(n) >= 1e6)
		return `${(n / 1e6).toLocaleString("th-TH", { maximumFractionDigits: 2 })} ล้าน`;
	if (short && Math.abs(n) >= 1e4)
		return `${(n / 1e3).toLocaleString("th-TH", { maximumFractionDigits: 1 })} พัน`;
	return n.toLocaleString("th-TH", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}
export const state = reactive({
	// หน้างาน: โครงการที่ทำงาน (ต้องเลือก) / ออฟฟิศ: ตัวกรองโครงการ (null = ทุกโครงการ)
	project: null, // {name, project_name, company}
	// ออฟฟิศ: บริษัทที่เลือก ("" = ทุกบริษัท) กรองรายการ/ตัวเลข และเป็นบริษัทของเอกสารใหม่
	company: "",
	// จำนวน ProjectFilter ที่แสดงอยู่ (กลุ่มออฟฟิศใช้ตัวกรองโครงการเฉพาะหน้าที่มีตัวกรองนี้)
	project_filter_shown: 0,
	section: null, // ตั้งใน init_app()
	// summary ของแต่ละหมวด (สโตร์ = store_app.get_summary, ควบคุมงาน = site_app.get_work_summary)
	summaries: {},
	// หน้าหลักล่าสุดของแต่ละหมวด: สลับหมวดกลับมาแล้วอยู่เมนูเดิม
	last_tab: {},
	// จัดซื้อ/ขาย: project = เฉพาะโครงการที่เลือก, all = ทุกโครงการ
	route: { view: "home", params: {} },
	direction: "fade", // forward | back | fade (สลับแท็บ)
	toasts: [],
	success: null,
	busy: false,
	get summary() {
		return this.summaries.store || null;
	},
	set summary(value) {
		this.summaries.store = value;
	},
});

// ---------------------------------------------------------------- API

export class ApiError extends Error {}

// กำลังออกจากหน้า (สลับไปหมวดของอีก bundle = โหลดหน้าใหม่ / ออกจากระบบ): เบราว์เซอร์ตัดคำขอที่ค้างอยู่
// fetch จึง error แบบเดียวกับเน็ตหลุด ห้ามขึ้น "เชื่อมต่อเซิร์ฟเวอร์ไม่ได้" ให้เงียบแทน (silent)
let leaving = false;
window.addEventListener("pagehide", () => (leaving = true));
window.addEventListener("beforeunload", () => (leaving = true));
// กลับมาจาก bfcache (กดย้อนกลับ) หน้าเดิมใช้ต่อ
window.addEventListener("pageshow", () => (leaving = false));

function server_messages(data) {
	try {
		return JSON.parse(data._server_messages || "[]")
			.map((m) => {
				try {
					return JSON.parse(m).message;
				} catch {
					return m;
				}
			})
			.map(strip_html)
			.filter(Boolean);
	} catch {
		return [];
	}
}

export function strip_html(html) {
	const el = document.createElement("div");
	el.innerHTML = html || "";
	return (el.textContent || "").trim();
}

export async function call(method, args = {}, { post = false } = {}) {
	// ชื่อสั้น = ฟังก์ชันใน store_app.py, มีจุด = path เต็ม
	const url = `/api/method/${method.includes(".") ? method : API + method}`;
	const body = new URLSearchParams();
	for (const [key, value] of Object.entries(args)) {
		if (value === undefined || value === null) continue;
		body.append(key, typeof value === "object" ? JSON.stringify(value) : value);
	}
	const options = {
		method: post ? "POST" : "GET",
		headers: {
			Accept: "application/json",
			"X-Frappe-CSRF-Token": window.frappe?.csrf_token || "",
		},
		credentials: "same-origin",
	};
	let request = url;
	if (post) {
		options.body = body;
		options.headers["Content-Type"] = "application/x-www-form-urlencoded; charset=UTF-8";
	} else if ([...body].length) {
		request += `?${body.toString()}`;
	}

	let response;
	try {
		response = await fetch(request, options);
	} catch (error) {
		if (leaving || error?.name === "AbortError") throw Object.assign(new ApiError("ยกเลิกคำขอ"), { silent: true });
		throw new ApiError("เชื่อมต่อเซิร์ฟเวอร์ไม่ได้ ตรวจสอบสัญญาณอินเทอร์เน็ต");
	}
	let data = {};
	try {
		data = await response.json();
	} catch {
		// ไม่ใช่ JSON (เช่น หน้า error ของ nginx)
	}
	if (response.status === 403 && data.exc_type === "CSRFTokenError") {
		throw new ApiError("หมดเวลาการใช้งาน กรุณาโหลดหน้าใหม่");
	}
	if (!response.ok || data.exc) {
		if (response.status === 401 || data.exc_type === "SessionExpired") {
			window.location.href = `/login?redirect-to=${encodeURIComponent(location.pathname)}`;
		}
		const messages = server_messages(data);
		throw new ApiError(
			messages.join("\n") || data.exception || `เกิดข้อผิดพลาด (${response.status})`
		);
	}
	const notes = server_messages(data);
	if (notes.length) notes.forEach((m) => toast(m, "warning"));
	return data.message;
}

export const post = (method, args) => call(method, args, { post: true });

// อัปโหลดรูป (ยังไม่ผูกเอกสาร: server ผูกให้ทีหลัง หรือใช้ URL ในช่อง Attach Image)
// attach = { doctype, docname } แนบกับเอกสารทันที (แบบปุ่มแนบไฟล์ของระบบเต็ม) ไม่ระบุ = อัปโหลดไว้ก่อน
export async function upload(file, attach = null) {
	const blob = await shrink_image(file);
	const form = new FormData();
	form.append("file", blob, file.name || `photo-${Date.now()}.jpg`);
	form.append("is_private", "1");
	form.append("folder", "Home/Attachments");
	if (attach) {
		form.append("doctype", attach.doctype);
		form.append("docname", attach.docname);
	}
	const response = await fetch("/api/method/upload_file", {
		method: "POST",
		body: form,
		headers: {
			Accept: "application/json",
			"X-Frappe-CSRF-Token": window.frappe?.csrf_token || "",
		},
		credentials: "same-origin",
	});
	const data = await response.json().catch(() => ({}));
	if (!response.ok || data.exc) {
		throw new ApiError(server_messages(data).join("\n") || "อัปโหลดไฟล์ไม่สำเร็จ");
	}
	return data.message; // {name, file_url, ...}
}

// ย่อรูปจากกล้องมือถือ (หลาย MB) เหลือด้านยาว max px (ค่าเริ่มต้น 1600) เป็น JPEG
// quality ระบุ = เข้ารหัสใหม่เสมอ (เช่น เซลฟี่ลงเวลา 480px / 0.6 ให้ไฟล์เล็ก) ไม่ระบุ = ไฟล์เล็กอยู่แล้วใช้ไฟล์เดิม
export function shrink_image(file, max = 1600, quality = null) {
	if (!file.type?.startsWith("image/") || file.type === "image/gif")
		return Promise.resolve(file);
	return new Promise((resolve) => {
		const img = new Image();
		const url = URL.createObjectURL(file);
		img.onload = () => {
			URL.revokeObjectURL(url);
			const scale = Math.min(1, max / Math.max(img.width, img.height));
			if (!quality && scale === 1 && file.size < 900 * 1024) return resolve(file);
			const canvas = document.createElement("canvas");
			canvas.width = Math.round(img.width * scale);
			canvas.height = Math.round(img.height * scale);
			canvas.getContext("2d").drawImage(img, 0, 0, canvas.width, canvas.height);
			canvas.toBlob((blob) => resolve(blob || file), "image/jpeg", quality || 0.82);
		};
		img.onerror = () => resolve(file);
		img.src = url;
	});
}

// ---------------------------------------------------------------- toast / success

let toast_id = 0;
export function toast(message, type = "info", timeout = 3200) {
	const id = ++toast_id;
	state.toasts.push({ id, message, type });
	setTimeout(() => {
		const index = state.toasts.findIndex((t) => t.id === id);
		if (index >= 0) state.toasts.splice(index, 1);
	}, timeout);
}

export function show_error(error) {
	if (error?.silent) return;
	toast(error?.message || String(error), "error", 5200);
	vibrate([30, 40, 30]);
}

export function celebrate(title, subtitle = "") {
	state.success = { title, subtitle };
	vibrate(25);
	return new Promise((resolve) =>
		setTimeout(() => {
			state.success = null;
			resolve();
		}, 1500)
	);
}

export function vibrate(pattern) {
	try {
		navigator.vibrate?.(pattern);
	} catch {
		// ไม่รองรับ
	}
}

// ---------------------------------------------------------------- โครงการที่เลือก

export function remembered_project() {
	try {
		return JSON.parse(localStorage.getItem(app.project_key) || "null");
	} catch {
		return null;
	}
}

export function remember_project(project) {
	try {
		if (project) localStorage.setItem(app.project_key, JSON.stringify(project));
		else localStorage.removeItem(app.project_key);
	} catch {
		// private mode: ใช้ได้ แค่ไม่จำ
	}
}

// ---------------------------------------------------------------- หมวดงาน

export function remembered_section() {
	try {
		return localStorage.getItem(section_key());
	} catch {
		return null;
	}
}

function remember_section(section) {
	try {
		localStorage.setItem(section_key(), section);
	} catch {
		// private mode
	}
}

// หน้าแรก (Desktop) เปิดได้ทุกคน
const allowed = (section) => is_desktop(section) || boot.sections.includes(section);

function set_section(section, force = false) {
	if (state.section === section && !force) return;
	state.section = section;
	// เปิด <base> เปล่าครั้งหน้า = หมวดงานล่าสุด (ไม่ใช่หน้าแรก)
	if (!is_desktop(section)) remember_section(section);
	// สีหลักตามหมวด: ใส่ที่ <html> ด้วย (sheet ถูก Teleport ไปที่ body อยู่นอก .ss-app)
	document.documentElement.dataset.section = section;
	// หน้าตาใหม่ (NEW_LOOK) = data-look="new" สีกรมท่าทุกหมวด
	const new_look = NEW_LOOK.has(section);
	if (new_look) document.documentElement.dataset.look = "new";
	else delete document.documentElement.dataset.look;
	// สีแถบสถานะของมือถือ/แถบเบราว์เซอร์ตามหมวด
	document.getElementById("theme-color")?.setAttribute("content", new_look ? "#17233f" : app.sections[section].theme);
}

// สลับหมวด: ไปหน้าหลักล่าสุดของหมวดนั้น (ไม่สร้างประวัติ: ปุ่มย้อนกลับไม่วนสลับหมวด)
export function switch_section(section) {
	if (!allowed(section)) return;
	if (section === state.section) {
		go(app.sections[section].home, {}, { replace: true, section });
		return;
	}
	const last = state.last_tab[section] || { view: app.sections[section].home, params: {} };
	// จากหน้าแรกเพิ่มประวัติ (ย้อนกลับมาหน้าแรกได้)
	go(last.view, last.params, {
		replace: is_tab(state.route.view) && !is_desktop(state.section),
		section,
	});
}

// ---------------------------------------------------------------- เริ่มแอป

// เรียกครั้งแรกใน setup ของ AppShell (หลัง configure ก่อนวาดหน้า)
export function init_app() {
	// ไม่มีสิทธิ์หมวดไหนเลย: เปิดหมวดสำรองของแอป (แต่ละหน้าแจ้งสิทธิ์เอง)
	if (!boot.sections?.length) boot.sections = [app.fallback || Object.keys(app.sections)[0]];
	// หมวดที่แอปนี้มี (boot ของ server อาจรวมหมวดของแอปอื่น)
	boot.sections = boot.sections.filter((key) => app.sections[key]);
	if (!boot.sections.length) boot.sections = [app.fallback || Object.keys(app.sections)[0]];
	state.section = boot.sections[0];
	document.documentElement.dataset.app = app.key;
	// บริษัท: ที่จำไว้ (ยังมีสิทธิ์) > มีบริษัทเดียว = บริษัทนั้น > ทุกบริษัท
	const companies = (boot.companies || []).map((c) => c.name);
	// ConsERP รวม bundle ออฟฟิศเข้ามา (2026-11-17): ยังไม่เคยจำ = ใช้ค่าที่ออฟฟิศเดิมจำไว้
	const saved = remembered(`${app.storage}.company`, "") || remembered("consbiz.office.company", "");
	state.company = companies.includes(saved) ? saved : companies.length === 1 ? companies[0] : "";
}

export function set_company(company) {
	state.company = company || "";
	try {
		localStorage.setItem(`${app.storage}.company`, state.company);
	} catch {
		// private mode
	}
}

// ขอบเขตของรายการ/ตัวเลขเอกสารซื้อ-ขาย (site_docs.get_docs / get_summary)
// หน้างาน: โครงการที่เลือกเท่านั้น (เลือกที่แถบบน) / ออฟฟิศ: ตัวกรองโครงการ + บริษัท
// section = หมวดที่ขอ (ตัวเลขของหมวดอื่นโหลดพร้อมกัน) ไม่ระบุ = หมวดที่เปิดอยู่
export function scope_args(section = state.section) {
	if (is_filter_section(section)) {
		// กลุ่มออฟฟิศ: ทุกโครงการ เว้นหน้าที่เปิดอยู่มีตัวกรองโครงการในหัวรายการ (ตัวเลขบนเมนู = ทุกโครงการ)
		const project =
			!is_company_section(section) || (section === state.section && state.project_filter_shown)
				? state.project?.name
				: undefined;
		return {
			project,
			scope: project ? "project" : "all",
			// บริษัทเลือกได้เฉพาะกลุ่มออฟฟิศ (ปุ่มบนแถบบน) ธุรการโครงการ: บริษัทตามโครงการที่เลือก
			company: (is_company_section(section) && state.company) || undefined,
		};
	}
	return { project: state.project?.name, scope: "project" };
}
// เปลี่ยนเมื่อขอบเขตเปลี่ยน (ใช้ใน watch)
export const scope_key = () => JSON.stringify(scope_args());

// ---------------------------------------------------------------- router (<base>/<หมวด>/<หน้า>/<params...>)

// route.section = หมวดของหน้าที่อยู่หลายหมวด (section_for ตอน go / หมวดใน URL) ไม่มี = หมวดตาม routes
function to_path({ view, params, section: target }) {
	const section = target || section_of(view);
	const parts = (app.routes[view]?.params || [])
		.map((key) => params[key])
		.filter((v) => v !== undefined && v !== null && v !== "");
	return [
		app.base,
		section,
		view === app.sections[section].home ? "" : view,
		...parts.map(encodeURIComponent),
	]
		.filter((p, i) => i < 2 || p)
		.join("/");
}

export function parse_path(pathname = location.pathname) {
	const parts = pathname
		.slice(pathname.startsWith(app.base) ? app.base.length : 0)
		.split("/")
		.filter(Boolean)
		.map(decodeURIComponent);
	// <base> เปล่า = หมวดที่ใช้ล่าสุด, หมวดที่ไม่มีสิทธิ์ = หมวดแรกที่มีสิทธิ์
	let section = app.sections[parts[0]] ? parts.shift() : remembered_section();
	if (!allowed(section)) section = boot.sections[0];
	let view = parts[0];
	// หน้าหลักของหมวดไม่มีชื่อหน้าใน URL (to_path ตัดออก) params จึงเริ่มที่ส่วนแรก เช่น /conserp/hr/2026-10
	let offset = 1;
	if (!app.routes[view] || !route_in(view, section)) {
		view = app.sections[section].home;
		offset = 0;
	}
	// เมนูที่ไม่มีสิทธิ์ (tab.when) เปิดจาก URL ตรงไม่ได้
	const tab = app.sections[section].tabs.find((t) => t.view === view);
	if (tab?.when && !tab.when(boot)) {
		view = app.sections[section].home;
		offset = parts.length;
	}
	const params = {};
	app.routes[view].params.forEach((key, i) => {
		if (parts[i + offset] !== undefined) params[key] = parts[i + offset];
	});
	// หมวดที่เปิดได้เฉพาะบางชนิดเอกสาร (ขอซื้อ = ใบขอซื้อ) ชนิดอื่นใน URL = เปิดในหมวดหลักของหน้านั้น (จัดซื้อ)
	const kinds = app.sections[section].kinds;
	if (kinds && params.kind && !kinds.includes(params.kind) && allowed(app.routes[view].section))
		section = app.routes[view].section;
	return { view, params, section };
}

function apply_route(route, direction) {
	const section = route.section || section_of(route.view);
	state.direction = section !== state.section ? "section" : direction;
	set_section(section);
	if (is_tab(route.view))
		state.last_tab[section] = { view: route.view, params: { ...route.params } };
	state.route = route;
}

// ด่านก่อนออกจากหน้า (เช่น หน้าแก้แผนงาน: บันทึกงานค้างก่อน) fn() คืน Promise<boolean> (true = ออกได้)
// ใช้กับ go / back / ปุ่มย้อนกลับของเบราว์เซอร์ ส่วนการโหลดหน้าใหม่ (ข้ามแอป) หน้านั้นใช้ beforeunload เอง
let leave_guard = null;
let skip_popstate = false;
export function set_leave_guard(fn) {
	leave_guard = fn;
}
async function can_leave() {
	if (!leave_guard) return true;
	const ok = await leave_guard();
	if (ok) leave_guard = null;
	return ok;
}

// section = หมวดปลายทาง (หน้าที่อยู่หลายหมวด เช่น สลับหมวด) ไม่ระบุ = section_for
export function go(view, params = {}, { replace = false, section = null } = {}) {
	if (leave_guard) {
		can_leave().then((ok) => ok && go(view, params, { replace, section }));
		return;
	}
	const target = section && route_in(view, section) ? section : section_for(view, params);
	const route = { view, params: { ...params }, section: target };
	apply_route(route, is_tab(view) && is_tab(state.route.view) ? "fade" : "forward");
	const depth = (history.state?.depth || 0) + (replace ? 0 : 1);
	history[replace ? "replaceState" : "pushState"]({ route, depth }, "", to_path(route));
	window.scrollTo({ top: 0 });
}

export function back(fallback = "home", params = {}) {
	if (leave_guard) {
		can_leave().then((ok) => ok && back(fallback, params));
		return;
	}
	if ((history.state?.depth || 0) > 0) {
		history.back();
	} else {
		const route = { view: fallback, params: { ...params }, section: section_for(fallback, params) };
		apply_route(route, "back");
		history.replaceState({ route, depth: 0 }, "", to_path(route));
	}
}

// แท็บย่อยในหน้า: จำใน URL/history โดยไม่สร้างหน้าใหม่ (ย้อนกลับมาแล้วอยู่แท็บเดิม)
export function remember_tab(view, tab, default_tab) {
	const route = { view, params: tab === default_tab ? {} : { tab }, section: section_of(view) };
	if (is_tab(view)) state.last_tab[section_of(view)] = route;
	history.replaceState({ ...(history.state || {}), route }, "", to_path(route));
}

// เปลี่ยน params ของหน้าเดิมใน URL โดยไม่สร้างประวัติ (เช่น วันที่เลือกในปฏิทิน)
export function replace_params(view, params) {
	const route = { view, params: { ...params }, section: section_of(view) };
	if (is_tab(view)) state.last_tab[section_of(view)] = route;
	history.replaceState({ ...(history.state || {}), route }, "", to_path(route));
}

export function iso_date(date) {
	const d = new Date(date);
	return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(
		d.getDate()
	).padStart(2, "0")}`;
}

export function start_router() {
	// history.state เก็บได้เฉพาะ object ธรรมดา (Proxy ของ Vue clone ไม่ได้)
	const route = parse_path();
	set_section(route.section, true);
	apply_route(route, "fade");
	history.replaceState({ route, depth: 0 }, "", to_path(route));
	window.addEventListener("popstate", (event) => {
		if (skip_popstate) {
			skip_popstate = false;
		} else if (leave_guard) {
			// เบราว์เซอร์ย้อนไปแล้ว: ใส่หน้าเดิมคืนก่อน ผ่านด่านแล้วจึงย้อนจริง
			const route = JSON.parse(JSON.stringify(state.route));
			history.pushState({ route, depth: (event.state?.depth || 0) + 1 }, "", to_path(route));
			can_leave().then((ok) => {
				if (!ok) return;
				skip_popstate = true;
				history.back();
			});
			return;
		}
		apply_route(event.state?.route || parse_path(), "back");
	});
}

// เปิดฟอร์มในระบบเต็ม (ยังไม่มีหน้าในแอป) values = ค่าตั้งต้นของเอกสารใหม่
export function desk_new_url(doctype, values = {}) {
	const query = new URLSearchParams(
		Object.entries(values).filter(([, v]) => v !== undefined && v !== null && v !== "")
	).toString();
	return `/app/${doctype.toLowerCase().replace(/ /g, "-")}/new${query ? `?${query}` : ""}`;
}

// ---------------------------------------------------------------- รูปแบบ

const number_format = new Intl.NumberFormat("th-TH", { maximumFractionDigits: 3 });
export const num = (value) => number_format.format(Number(value) || 0);

const THAI_MONTHS = [
	"ม.ค.",
	"ก.พ.",
	"มี.ค.",
	"เม.ย.",
	"พ.ค.",
	"มิ.ย.",
	"ก.ค.",
	"ส.ค.",
	"ก.ย.",
	"ต.ค.",
	"พ.ย.",
	"ธ.ค.",
];
export function thai_date(value, { year = false } = {}) {
	if (!value) return "";
	const [y, m, d] = String(value).slice(0, 10).split("-").map(Number);
	return `${d} ${THAI_MONTHS[m - 1]}${year ? ` ${(y + 543) % 100}` : ""}`;
}

export function relative_date(value) {
	if (!value) return "";
	const today = new Date(boot.today || new Date().toISOString().slice(0, 10));
	const date = new Date(String(value).slice(0, 10));
	const days = Math.round((date - today) / 86400000);
	if (days === 0) return "วันนี้";
	if (days === -1) return "เมื่อวาน";
	if (days === 1) return "พรุ่งนี้";
	if (days < 0 && days > -7) return `${-days} วันก่อน`;
	if (days > 0 && days < 7) return `อีก ${days} วัน`;
	return thai_date(value, { year: date.getFullYear() !== today.getFullYear() });
}

export const short_time = (value) => (value ? String(value).slice(0, 5) : "");

export function today() {
	return boot.today || new Date().toISOString().slice(0, 10);
}

export function now_time() {
	const d = new Date();
	return `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
}

// ตัวย่อของโครงการในกล่องสี: Project.custom_abbr ไม่ได้ตั้ง = ตัวย่อจากชื่อ
export function project_abbr(project) {
	return project.custom_abbr || initials(project.project_name || project.name);
}

export function initials(text) {
	const clean = String(text || "?").replace(
		/^(บริษัท|บจก\.|หจก\.|ห้างหุ้นส่วนจำกัด|นาย|นาง|นางสาว)\s*/u,
		""
	);
	return [...clean.trim()].slice(0, 2).join("");
}

// สีพื้นของ avatar จากข้อความ (คงที่ต่อชื่อ)
export function tone(text) {
	let hash = 0;
	for (const ch of String(text || "")) hash = (hash * 31 + ch.codePointAt(0)) | 0;
	const tones = ["blue", "violet", "teal", "amber", "rose", "green", "indigo", "orange"];
	return tones[Math.abs(hash) % tones.length];
}

export const desk_url = (doctype, name) =>
	`/app/${doctype.toLowerCase().replace(/ /g, "-")}/${encodeURIComponent(name)}`;

// เวลาที่ผ่านมาแบบสั้น (แก้ไขล่าสุดในรายการ): เมื่อสักครู่ / 5 นาที / 3 ชม. / 2 วัน / วันที่
export function time_ago(value) {
	if (!value) return "";
	const then = new Date(String(value).replace(" ", "T"));
	const minutes = Math.round((Date.now() - then) / 60000);
	if (minutes < 1) return "เมื่อสักครู่";
	if (minutes < 60) return `${minutes} นาที`;
	if (minutes < 60 * 24) return `${Math.round(minutes / 60)} ชม.`;
	if (minutes < 60 * 24 * 30) return `${Math.round(minutes / 1440)} วัน`;
	return thai_date(value, { year: then.getFullYear() !== new Date().getFullYear() });
}

// ---------------------------------------------------------------- ข้อความแบบ Text Editor ของระบบเต็ม (Quill 2)
// เช่น description ของรายการ: <div class="ql-editor read-mode"><ol><li data-list="bullet"><span class="ql-ui"></span>…
// เก็บเฉพาะแท็ก/แอตทริบิวต์ที่ปลอดภัย ตัด span.ql-ui และกรอบ ql-editor ออก (ใช้กับ v-html เท่านั้นผ่านฟังก์ชันนี้)
const RICH_TAGS = new Set(
	"P BR B STRONG I EM U S STRIKE SUB SUP OL UL LI SPAN DIV A H1 H2 H3 H4 BLOCKQUOTE PRE CODE TABLE THEAD TBODY TR TD TH".split(
		" "
	)
);
const DROP_TAGS = new Set(
	"SCRIPT STYLE IFRAME OBJECT EMBED LINK META svg MATH TEMPLATE".split(" ")
);

function clean_node(node) {
	for (const child of [...node.childNodes]) {
		if (child.nodeType === Node.COMMENT_NODE) {
			child.remove();
			continue;
		}
		if (child.nodeType !== Node.ELEMENT_NODE) continue;
		const tag = child.tagName.toUpperCase();
		if (
			DROP_TAGS.has(child.tagName) ||
			DROP_TAGS.has(tag) ||
			child.classList.contains("ql-ui")
		) {
			child.remove();
			continue;
		}
		clean_node(child);
		if (!RICH_TAGS.has(tag)) {
			child.replaceWith(...child.childNodes);
			continue;
		}
		for (const attr of [...child.attributes]) {
			const name = attr.name.toLowerCase();
			const keep =
				(name === "data-list" && tag === "LI") ||
				(name === "class" && /^(ql-(align|indent)-[\w-]+\s*)+$/.test(attr.value)) ||
				(name === "href" &&
					tag === "A" &&
					/^(https?:|mailto:|tel:)/i.test(attr.value.trim()));
			if (!keep) child.removeAttribute(attr.name);
		}
		if (tag === "A") {
			child.setAttribute("target", "_blank");
			child.setAttribute("rel", "noopener noreferrer");
		}
	}
}

export function sanitize_html(html) {
	if (!html) return "";
	const text = String(html);
	// ข้อความธรรมดา (ไม่มีแท็ก): แปลงขึ้นบรรทัดใหม่เป็น <br>
	if (!/<[a-z][\s\S]*>/i.test(text)) {
		const div = document.createElement("div");
		div.textContent = text;
		return div.innerHTML.replace(/\n/g, "<br>");
	}
	const doc = new DOMParser().parseFromString(text, "text/html");
	const body = doc.body;
	clean_node(body);
	// ตัดกรอบ <div class="ql-editor"> ที่ห่อทั้งหมด (คลาสถูกลบแล้ว เหลือ div เปล่าชั้นเดียว)
	let root = body;
	while (
		root.childNodes.length === 1 &&
		root.firstChild.nodeType === 1 &&
		root.firstChild.tagName === "DIV"
	) {
		root = root.firstChild;
	}
	return html_text(root.innerHTML) ? root.innerHTML : "";
}

// ข้อความล้วนของ HTML (ค้นหา / ตัดสั้น / เทียบกับชื่อรายการ)
export function html_text(html) {
	if (!html) return "";
	const div = document.createElement("div");
	div.innerHTML = String(html).replace(/<(br|\/p|\/li|\/div)[^>]*>/gi, " ");
	return div.textContent.replace(/\s+/g, " ").trim();
}

// ตัวเลขเงิน 2 ตำแหน่งมีจุลภาค (ช่องกรอกเงิน)
const money_input_format = new Intl.NumberFormat("en-US", {
	minimumFractionDigits: 2,
	maximumFractionDigits: 2,
});
export const format_money_input = (value) =>
	value === null || value === undefined || value === ""
		? ""
		: money_input_format.format(Number(value) || 0);
export function parse_money_input(text) {
	const clean = String(text ?? "").replace(/[,\s฿]/g, "");
	if (clean === "" || clean === "-" || clean === ".") return null;
	const value = Number(clean);
	return Number.isFinite(value) ? value : null;
}
