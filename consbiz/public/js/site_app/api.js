// ตัวช่วยกลางของแอปหน้างาน: เรียก API (consbiz/store_app.py, consbiz/site_app.py), อัปโหลดรูป,
// router (/site/<หมวด>/<หน้า>/...), สลับหมวดงาน, toast, รูปแบบตัวเลข/วันที่
import { reactive } from "vue";
import { ROUTES, SECTIONS, is_tab, section_of } from "./sections.js";

const API = "consbiz.store_app.";
const PROJECT_KEY = "consbiz.store.project"; // ชื่อเดิมจากแอปสโตร์: ผู้ใช้เดิมไม่ต้องเลือกโครงการใหม่
const SECTION_KEY = "consbiz.site.section";

export const boot = window.SITE_BOOT || {};

function remembered(key, fallback) {
	try {
		return localStorage.getItem(key) || fallback;
	} catch {
		return fallback;
	}
}

export function set_doc_scope(scope) {
	state.doc_scope = scope;
	try {
		localStorage.setItem("consbiz.site.doc_scope", scope);
	} catch {
		// private mode
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
// ไม่มีสิทธิ์หมวดไหนเลย: เปิดหมวดสโตร์ (แต่ละหน้าแจ้งสิทธิ์เองเหมือนแอปสโตร์เดิม)
if (!boot.sections?.length) boot.sections = ["store"];

export const state = reactive({
	project: null, // {name, project_name, company}
	section: boot.sections[0],
	// summary ของแต่ละหมวด (สโตร์ = store_app.get_summary, ควบคุมงาน = site_app.get_work_summary)
	summaries: {},
	// หน้าหลักล่าสุดของแต่ละหมวด: สลับหมวดกลับมาแล้วอยู่เมนูเดิม
	last_tab: {},
	// จัดซื้อ/ขาย: project = เฉพาะโครงการที่เลือก, all = ทุกโครงการ
	doc_scope: remembered("consbiz.site.doc_scope", "project"),
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
		headers: { Accept: "application/json", "X-Frappe-CSRF-Token": window.frappe?.csrf_token || "" },
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
	} catch {
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
		throw new ApiError(messages.join("\n") || data.exception || `เกิดข้อผิดพลาด (${response.status})`);
	}
	const notes = server_messages(data);
	if (notes.length) notes.forEach((m) => toast(m, "warning"));
	return data.message;
}

export const post = (method, args) => call(method, args, { post: true });

// อัปโหลดรูป (ยังไม่ผูกเอกสาร: server ผูกให้ทีหลัง หรือใช้ URL ในช่อง Attach Image)
export async function upload(file) {
	const blob = await shrink_image(file);
	const form = new FormData();
	form.append("file", blob, file.name || `photo-${Date.now()}.jpg`);
	form.append("is_private", "1");
	form.append("folder", "Home/Attachments");
	const response = await fetch("/api/method/upload_file", {
		method: "POST",
		body: form,
		headers: { Accept: "application/json", "X-Frappe-CSRF-Token": window.frappe?.csrf_token || "" },
		credentials: "same-origin",
	});
	const data = await response.json().catch(() => ({}));
	if (!response.ok || data.exc) {
		throw new ApiError(server_messages(data).join("\n") || "อัปโหลดรูปไม่สำเร็จ");
	}
	return data.message; // {name, file_url, ...}
}

// ย่อรูปจากกล้องมือถือ (หลาย MB) เหลือด้านยาว 1600px
function shrink_image(file, max = 1600) {
	if (!file.type?.startsWith("image/") || file.type === "image/gif") return Promise.resolve(file);
	return new Promise((resolve) => {
		const img = new Image();
		const url = URL.createObjectURL(file);
		img.onload = () => {
			URL.revokeObjectURL(url);
			const scale = Math.min(1, max / Math.max(img.width, img.height));
			if (scale === 1 && file.size < 900 * 1024) return resolve(file);
			const canvas = document.createElement("canvas");
			canvas.width = Math.round(img.width * scale);
			canvas.height = Math.round(img.height * scale);
			canvas.getContext("2d").drawImage(img, 0, 0, canvas.width, canvas.height);
			canvas.toBlob((blob) => resolve(blob || file), "image/jpeg", 0.82);
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
		return JSON.parse(localStorage.getItem(PROJECT_KEY) || "null");
	} catch {
		return null;
	}
}

export function remember_project(project) {
	try {
		localStorage.setItem(PROJECT_KEY, JSON.stringify(project));
	} catch {
		// private mode: ใช้ได้ แค่ไม่จำ
	}
}

// ---------------------------------------------------------------- หมวดงาน

export function remembered_section() {
	try {
		return localStorage.getItem(SECTION_KEY);
	} catch {
		return null;
	}
}

function remember_section(section) {
	try {
		localStorage.setItem(SECTION_KEY, section);
	} catch {
		// private mode
	}
}

const allowed = (section) => boot.sections.includes(section);

function set_section(section, force = false) {
	if (state.section === section && !force) return;
	state.section = section;
	remember_section(section);
	// สีหลักตามหมวด: ใส่ที่ <html> ด้วย (sheet ถูก Teleport ไปที่ body อยู่นอก .ss-app)
	document.documentElement.dataset.section = section;
	// สีแถบสถานะของมือถือตามหมวด
	document.getElementById("theme-color")?.setAttribute("content", SECTIONS[section].theme);
}

// สลับหมวด: ไปหน้าหลักล่าสุดของหมวดนั้น (ไม่สร้างประวัติ: ปุ่มย้อนกลับไม่วนสลับหมวด)
export function switch_section(section) {
	if (!allowed(section)) return;
	if (section === state.section) {
		go(SECTIONS[section].home, {}, { replace: true });
		return;
	}
	const last = state.last_tab[section] || { view: SECTIONS[section].home, params: {} };
	go(last.view, last.params, { replace: is_tab(state.route.view) });
}

// ---------------------------------------------------------------- router (/site/<หมวด>/<หน้า>/<params...>)

function to_path({ view, params }) {
	const section = section_of(view);
	const parts = (ROUTES[view]?.params || [])
		.map((key) => params[key])
		.filter((v) => v !== undefined && v !== null && v !== "");
	return ["/site", section, view === SECTIONS[section].home ? "" : view, ...parts.map(encodeURIComponent)]
		.filter((p, i) => i < 2 || p)
		.join("/");
}

export function parse_path(pathname = location.pathname) {
	const parts = pathname
		.replace(/^\/site\/?/, "")
		.split("/")
		.filter(Boolean)
		.map(decodeURIComponent);
	// /site เปล่า = หมวดที่ใช้ล่าสุด, หมวดที่ไม่มีสิทธิ์ = หมวดแรกที่มีสิทธิ์
	let section = SECTIONS[parts[0]] ? parts.shift() : remembered_section();
	if (!allowed(section)) section = boot.sections[0];
	let view = parts[0];
	if (!ROUTES[view] || section_of(view) !== section) view = SECTIONS[section].home;
	const params = {};
	ROUTES[view].params.forEach((key, i) => {
		if (parts[i + 1] !== undefined) params[key] = parts[i + 1];
	});
	return { view, params };
}

function apply_route(route, direction) {
	const section = section_of(route.view);
	state.direction = section !== state.section ? "section" : direction;
	set_section(section);
	if (is_tab(route.view)) state.last_tab[section] = { view: route.view, params: { ...route.params } };
	state.route = route;
}

export function go(view, params = {}, { replace = false } = {}) {
	const route = { view, params: { ...params } };
	apply_route(route, is_tab(view) && is_tab(state.route.view) ? "fade" : "forward");
	const depth = (history.state?.depth || 0) + (replace ? 0 : 1);
	history[replace ? "replaceState" : "pushState"]({ route, depth }, "", to_path(route));
	window.scrollTo({ top: 0 });
}

export function back(fallback = "home", params = {}) {
	if ((history.state?.depth || 0) > 0) {
		history.back();
	} else {
		const route = { view: fallback, params: { ...params } };
		apply_route(route, "back");
		history.replaceState({ route, depth: 0 }, "", to_path(route));
	}
}

// แท็บย่อยในหน้า: จำใน URL/history โดยไม่สร้างหน้าใหม่ (ย้อนกลับมาแล้วอยู่แท็บเดิม)
export function remember_tab(view, tab, default_tab) {
	const route = { view, params: tab === default_tab ? {} : { tab } };
	if (is_tab(view)) state.last_tab[section_of(view)] = route;
	history.replaceState({ ...(history.state || {}), route }, "", to_path(route));
}

// เปลี่ยน params ของหน้าเดิมใน URL โดยไม่สร้างประวัติ (เช่น วันที่เลือกในปฏิทิน)
export function replace_params(view, params) {
	const route = { view, params: { ...params } };
	if (is_tab(view)) state.last_tab[section_of(view)] = route;
	history.replaceState({ ...(history.state || {}), route }, "", to_path(route));
}

export function iso_date(date) {
	const d = new Date(date);
	return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(
		2,
		"0"
	)}`;
}

export function start_router() {
	// history.state เก็บได้เฉพาะ object ธรรมดา (Proxy ของ Vue clone ไม่ได้)
	const route = parse_path();
	set_section(section_of(route.view), true);
	apply_route(route, "fade");
	history.replaceState({ route, depth: 0 }, "", to_path(route));
	window.addEventListener("popstate", (event) => {
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
const DROP_TAGS = new Set("SCRIPT STYLE IFRAME OBJECT EMBED LINK META svg MATH TEMPLATE".split(" "));

function clean_node(node) {
	for (const child of [...node.childNodes]) {
		if (child.nodeType === Node.COMMENT_NODE) {
			child.remove();
			continue;
		}
		if (child.nodeType !== Node.ELEMENT_NODE) continue;
		const tag = child.tagName.toUpperCase();
		if (DROP_TAGS.has(child.tagName) || DROP_TAGS.has(tag) || child.classList.contains("ql-ui")) {
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
				(name === "href" && tag === "A" && /^(https?:|mailto:|tel:)/i.test(attr.value.trim()));
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
