// ตัวช่วยกลางของแอปสโตร์หน้างาน: เรียก API (consbiz/store_app.py), อัปโหลดรูป, router, toast, รูปแบบตัวเลข/วันที่
import { reactive } from "vue";

const API = "consbiz.store_app.";
const PROJECT_KEY = "consbiz.store.project";

export const boot = window.STORE_BOOT || {};

export const state = reactive({
	project: null, // {name, project_name, company}
	summary: null,
	route: { view: "home", params: {} },
	direction: "fade", // forward | back | fade (สลับแท็บ)
	toasts: [],
	success: null,
	busy: false,
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

// ---------------------------------------------------------------- router (/store/<view>/<params...>)

export const TABS = ["home", "receive", "issue", "borrow", "stock"];
// view → ชื่อ params ตามลำดับใน URL
const ROUTES = {
	home: [],
	receive: ["tab"],
	"receive-form": ["doctype", "name"],
	receipt: ["doctype", "name"],
	issue: ["tab"],
	concrete: [],
	"concrete-form": ["name"],
	borrow: ["tab"],
	"borrow-detail": ["name"],
	"borrow-new": [],
	stock: [],
};

function to_path({ view, params }) {
	const parts = (ROUTES[view] || [])
		.map((key) => params[key])
		.filter((v) => v !== undefined && v !== null && v !== "");
	return ["/store", view === "home" ? "" : view, ...parts.map(encodeURIComponent)]
		.filter((p, i) => i === 0 || p)
		.join("/");
}

export function parse_path(pathname = location.pathname) {
	const parts = pathname
		.replace(/^\/store\/?/, "")
		.split("/")
		.filter(Boolean)
		.map(decodeURIComponent);
	const view = ROUTES[parts[0]] ? parts[0] : "home";
	const params = {};
	(ROUTES[view] || []).forEach((key, i) => {
		if (parts[i + 1] !== undefined) params[key] = parts[i + 1];
	});
	return { view, params };
}

export function go(view, params = {}, { replace = false } = {}) {
	const route = { view, params: { ...params } };
	const from_tab = TABS.includes(state.route.view);
	state.direction = TABS.includes(view) && from_tab ? "fade" : "forward";
	state.route = route;
	const depth = (history.state?.depth || 0) + (replace ? 0 : 1);
	history[replace ? "replaceState" : "pushState"]({ route, depth }, "", to_path(route));
	window.scrollTo({ top: 0 });
}

export function back(fallback = "home", params = {}) {
	if ((history.state?.depth || 0) > 0) {
		history.back();
	} else {
		const route = { view: fallback, params: { ...params } };
		state.direction = "back";
		state.route = route;
		history.replaceState({ route, depth: 0 }, "", to_path(route));
	}
}

// แท็บย่อยในหน้า: จำใน URL/history โดยไม่สร้างหน้าใหม่ (ย้อนกลับมาแล้วอยู่แท็บเดิม)
export function remember_tab(view, tab, default_tab) {
	const route = { view, params: tab === default_tab ? {} : { tab } };
	history.replaceState({ ...(history.state || {}), route }, "", to_path(route));
}

export function start_router() {
	// history.state เก็บได้เฉพาะ object ธรรมดา (Proxy ของ Vue clone ไม่ได้)
	const route = parse_path();
	state.route = route;
	history.replaceState({ route, depth: 0 }, "", to_path(route));
	window.addEventListener("popstate", (event) => {
		state.direction = "back";
		state.route = event.state?.route || parse_path();
	});
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
