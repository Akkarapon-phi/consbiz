<!-- ดูเอกสาร HTML เต็มจอ (ตกลง 2026-11-18 ใช้แทน PdfViewer กับเอกสารที่สร้างเป็น HTML ในเครื่อง ตอนนี้ = แท็บพิมพ์ของแผนงาน): iframe เอกสารเดียวกับ Preview ย่อ/ขยายด้วย transform
     เบราว์เซอร์วาดตัวอักษรใหม่ทุกระดับซูม = คมเท่า Preview ต่างจาก PdfViewer ที่วาด PDF เป็นภาพ (canvas) ที่ความละเอียดจำกัด
     แถบบน: ซูม / พิมพ์ (พิมพ์ iframe นี้เอง) / แชร์ไฟล์ PDF / ดาวน์โหลด PDF
     ไฟล์ PDF (fetch_file) เริ่มสร้างเบื้องหลังตอนเปิด ไม่ต้องรอก่อนแสดง และพร้อมแล้วตอนกดแชร์
     (Web Share ต้องเรียกทันทีหลังผู้ใช้กด ถ้ารอสร้าง PDF นานเบราว์เซอร์จะไม่ยอมแชร์)
     zoom 1 = ขนาดจริง iframe ไม่รับการแตะ (pointer-events: none) ให้ซูมสองนิ้ว/เลื่อนที่กรอบนอก -->
<template>
	<Teleport to="body">
		<Transition name="ss-pdf">
			<div v-if="open" class="ss-pdf" role="dialog" aria-modal="true" :aria-label="`${title} ${name}`">
				<header class="ss-pdf-bar">
					<button type="button" class="ss-icon-btn" aria-label="ปิด" @click="$emit('close')">
						<Icon name="x" :size="22" />
					</button>
					<div class="ss-pdf-title">
						<b>{{ title }}</b>
						<small
							>{{ name }}<template v-if="pages"> · {{ pages }} หน้า</template></small
						>
					</div>
					<!-- ตัวเลือกของเอกสาร (เช่น ฉบับที่พิมพ์ ต้นฉบับ/สำเนา) -->
					<div v-if="$slots.tools" class="ss-pdf-tools"><slot name="tools" /></div>
					<button type="button" class="ss-btn ss-btn--ghost ss-html-fit" @click="toggle_fit">
						{{ mode === "page" ? "พอดีความกว้าง" : "พอดีหน้า" }}
					</button>
					<div class="ss-pdf-zoom">
						<button
							type="button"
							class="ss-icon-btn"
							aria-label="ย่อ"
							:disabled="scale <= fit_page"
							@click="set_zoom(scale / 1.25)"
						>
							<Icon name="minus" :size="18" :stroke="2.4" />
						</button>
						<span>{{ Math.round(scale * 100) }}%</span>
						<button
							type="button"
							class="ss-icon-btn"
							aria-label="ขยาย"
							:disabled="scale >= max_zoom"
							@click="set_zoom(scale * 1.25)"
						>
							<Icon name="plus" :size="18" :stroke="2.4" />
						</button>
					</div>
					<button type="button" class="ss-icon-btn" aria-label="พิมพ์" title="พิมพ์" :disabled="printing" @click="print">
						<span v-if="printing" class="ss-spinner"></span>
						<Icon v-else name="printer" :size="19" />
					</button>
					<button
						type="button"
						class="ss-icon-btn"
						v-if="fetch_file"
						:aria-label="file_label('แชร์ไฟล์ PDF ไปแอปอื่น')"
						:title="file_label('แชร์ไฟล์ PDF ไปแอปอื่น')"
						:disabled="file_state === 'loading'"
						@click="share"
					>
						<span v-if="file_state === 'loading'" class="ss-spinner"></span>
						<Icon v-else name="share" :size="19" />
					</button>
					<button
						type="button"
						class="ss-icon-btn"
						v-if="fetch_file"
						:aria-label="file_label('ดาวน์โหลด PDF')"
						:title="file_label('ดาวน์โหลด PDF')"
						:disabled="file_state === 'loading'"
						@click="download"
					>
						<span v-if="file_state === 'loading'" class="ss-spinner"></span>
						<Icon v-else name="receive" :size="20" />
					</button>
				</header>

				<div
					ref="scroller"
					class="ss-pdf-pages ss-html-pages"
					@dblclick="double_click_zoom"
					@touchstart="pinch_start"
					@touchmove="pinch_move"
					@touchend="pinch_end"
					@touchcancel="pinch_end"
				>
					<div ref="holder" class="ss-pdf-holder">
						<div
							ref="sheet"
							class="ss-html-sheet"
							:style="{ width: `${width * scale}px`, height: `${sheet_h * scale}px` }"
						>
							<iframe
								ref="frame"
								class="ss-html-frame"
								:title="title"
								tabindex="-1"
								scrolling="no"
								:style="{ width: `${width}px`, height: `${sheet_h}px`, transform: `scale(${scale})` }"
							></iframe>
						</div>
					</div>
				</div>
			</div>
		</Transition>
	</Teleport>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, ref, shallowRef, watch } from "vue";
import Icon from "./Icon.vue";
import { show_error, strip_html, toast } from "../api.js";

// html = เอกสาร (มีขอบกระดาษ/เงาของตัวเองใน @media screen), width/height = ขนาดเอกสารเป็น px ที่ 100%
// fetch_file = สร้างไฟล์ PDF คืน Response, file_name = ชื่อไฟล์ตอนบันทึก/แชร์ (ไม่ใส่ = name)
const props = defineProps({
	open: Boolean,
	html: String,
	width: { type: Number, required: true },
	height: { type: Number, required: true },
	page_height: Number, // ความสูงหน้าเดียว เมื่อ height เป็นความสูงรวมหลายหน้า
	document_kind: { type: String, required: true },
	pages: Number,
	name: String,
	title: String,
	fetch_file: Function,
	file_name: String,
	max_zoom: { type: Number, default: 8 },
	// สูงตามเนื้อหาจริงของเอกสาร (หน้าพิมพ์ของ Frappe /printview ที่ไม่รู้ความสูงล่วงหน้า) height = ค่าเริ่มต้นก่อนวัด
	fit_height: Boolean,
	// เปลี่ยนค่า = สร้างไฟล์ PDF ใหม่ (ตัวเลือกของเอกสารเปลี่ยน เช่น ฉบับที่พิมพ์)
	file_key: String,
});
const emit = defineEmits(["close"]);

const scroller = ref(null);
const holder = ref(null);
const sheet = ref(null);
const frame = ref(null);
const preference = ref(null);
const canvas = ref({ width: 0, height: 0, phone: false });
const printing = ref(false);
const file = shallowRef(null);
// loading / ready / error (กดอีกครั้ง = ลองสร้างใหม่)
const file_state = ref("loading");
let file_error = "";
let file_job = 0;
let pinch = null;

const measured_h = ref(0);
const sheet_h = computed(() => (props.fit_height && measured_h.value) || props.height);
const storage_key = computed(() => `consbiz.print.zoom.${props.document_kind}`);
const default_mode = computed(() => (canvas.value.phone ? "width" : "page"));
const mode = computed(() => preference.value ?? default_mode.value);
const fit_width = computed(() => Math.min(1, (canvas.value.width || props.width) / props.width));
const fit_page = computed(() =>
	Math.min(fit_width.value, (canvas.value.height || props.height) / (props.page_height || props.height))
);
const scale = computed(() => {
	if (mode.value === "page") return fit_page.value;
	if (mode.value === "width") return fit_width.value;
	return Math.max(fit_page.value, Math.min(props.max_zoom, mode.value));
});
const file_label = (label) =>
	file_state.value === "loading" ? "กำลังสร้าง PDF…" : file_state.value === "error" ? `${label} (ลองใหม่)` : label;

function measure() {
	const el = scroller.value;
	if (!el) return;
	const css = getComputedStyle(el);
	canvas.value = {
		width: Math.max(1, el.clientWidth - parseFloat(css.paddingLeft) - parseFloat(css.paddingRight)),
		height: Math.max(1, el.clientHeight - parseFloat(css.paddingTop) - parseFloat(css.paddingBottom)),
		phone: window.innerWidth < 768,
	};
}

function read_zoom() {
	preference.value = null;
	try {
		const saved = JSON.parse(localStorage.getItem(storage_key.value));
		if (saved === "page" || saved === "width" || (Number.isFinite(saved) && saved > 0)) {
			preference.value = saved;
		}
	} catch {
		// ใช้ค่าเริ่มต้นเมื่อเบราว์เซอร์ปิดการเก็บข้อมูล
	}
}

function remember_zoom(value) {
	preference.value = value;
	try {
		localStorage.setItem(storage_key.value, JSON.stringify(value));
	} catch {
		// ยังใช้ค่าที่เลือกได้ในหน้าต่างนี้
	}
}

function write() {
	const doc = frame.value?.contentDocument;
	if (!doc || !props.html) return;
	doc.open();
	doc.write(props.html);
	doc.close();
	if (props.fit_height) {
		measured_h.value = 0;
		const win = frame.value.contentWindow;
		const fit = () => {
			const d = frame.value?.contentDocument;
			if (d?.documentElement) measured_h.value = Math.max(d.documentElement.scrollHeight, d.body?.scrollHeight || 0);
		};
		win.addEventListener("load", fit);
		win.document.fonts?.ready.then(fit);
		setTimeout(fit, 600);
		setTimeout(fit, 1500);
	}
}

async function server_reason(response) {
	try {
		const data = await response.json();
		const messages = JSON.parse(data._server_messages || "[]").map((m) => JSON.parse(m).message);
		const text = strip_html(messages.join(" ") || data.exception || "");
		return text ? `: ${text.slice(0, 200)}` : "";
	} catch {
		return "";
	}
}

async function make_file() {
	const job = ++file_job;
	file_state.value = "loading";
	file.value = null;
	try {
		const response = await props.fetch_file();
		if (!response.ok) throw new Error(`สร้าง PDF ไม่สำเร็จ${await server_reason(response)}`);
		const blob = await response.blob();
		if (job !== file_job) return;
		file.value = new File([blob], `${props.file_name || props.name}.pdf`, { type: "application/pdf" });
		file_state.value = "ready";
	} catch (err) {
		if (job !== file_job) return;
		console.error(err);
		file_error = err?.message?.startsWith("สร้าง") ? err.message : "สร้าง PDF ไม่สำเร็จ";
		file_state.value = "error";
	}
}

// ยังไม่พร้อม/ล้มเหลว: แจ้งแล้วสร้างใหม่ คืน false
function need_file() {
	if (file_state.value === "ready") return true;
	if (file_state.value === "error") {
		toast(`${file_error} กำลังลองใหม่`, "info", 4000);
		make_file();
	}
	return false;
}

function save_file(f) {
	const href = URL.createObjectURL(f);
	const link = Object.assign(document.createElement("a"), { href, download: f.name });
	document.body.appendChild(link);
	link.click();
	link.remove();
	setTimeout(() => URL.revokeObjectURL(href), 2000);
}

function download() {
	if (need_file()) save_file(file.value);
}

// Web Share API ใช้ได้เฉพาะ https ใช้ไม่ได้ = ดาวน์โหลดแทน (แบบเดียวกับ PdfViewer)
async function share() {
	if (!need_file()) return;
	const data = { files: [file.value], title: `${props.title} ${props.name}` };
	try {
		if (navigator.canShare?.(data)) {
			await navigator.share(data);
		} else {
			save_file(file.value);
			toast(
				window.isSecureContext
					? "เบราว์เซอร์นี้แชร์ไฟล์ไม่ได้ ดาวน์โหลดไฟล์ให้แทน"
					: "แชร์ไฟล์ได้เมื่อเปิดเว็บผ่าน https ดาวน์โหลดไฟล์ให้แทน",
				"info",
				4500
			);
		}
	} catch (err) {
		if (err?.name !== "AbortError") show_error(err);
	}
}

// พิมพ์ iframe ของหน้าต่างนี้ (เหมือนปุ่มพิมพ์ในแท็บพิมพ์) รอฟอนต์ไทยก่อน ชื่อหน้า = ชื่อไฟล์ "บันทึกเป็น PDF"
function print() {
	const win = frame.value?.contentWindow;
	if (!win || printing.value) return;
	printing.value = true;
	win.document.fonts
		.load('10px "ConsBiz Print"', "ก0")
		.catch(() => null)
		.finally(() => {
			printing.value = false;
			const page_title = document.title;
			document.title = props.file_name || props.name || page_title;
			win.focus();
			win.print();
			setTimeout(() => (document.title = page_title), 3000);
		});
}

function toggle_fit() {
	remember_zoom(mode.value === "page" ? "width" : "page");
	scroller.value?.scrollTo(0, 0);
}

// คงตำแหน่งบนกระดาษที่อยู่ใต้จุดกลางจอหรือจุดกึ่งกลางระหว่างนิ้ว
async function set_zoom(value, x, y) {
	const next = Math.max(fit_page.value, Math.min(props.max_zoom, value));
	if (next === scale.value) return;
	const el = scroller.value;
	const paper = sheet.value;
	if (!el || !paper) return;
	const view = el.getBoundingClientRect();
	const before = paper.getBoundingClientRect();
	x ??= view.left + view.width / 2;
	// เมื่อเห็นทั้งแผ่น ให้เริ่มขยายจากด้านบนของหน้า
	y ??= before.height <= view.height ? before.top : view.top + view.height / 2;
	const ratio = next / scale.value;
	remember_zoom(next === fit_page.value ? "page" : next);
	await nextTick();
	if (sheet.value !== paper) return;
	const after = paper.getBoundingClientRect();
	el.scrollBy(after.left + (x - before.left) * ratio - x, after.top + (y - before.top) * ratio - y);
}

function double_click_zoom() {
	const base = default_mode.value === "page" ? fit_page.value : fit_width.value;
	if (scale.value > base) {
		remember_zoom(default_mode.value);
		scroller.value?.scrollTo(0, 0);
	} else {
		set_zoom(base * 2);
	}
}

// ซูมสองนิ้ว: ระหว่างขยับใช้ transform ทั้งกรอบ ปล่อยนิ้วแล้วตั้ง scale ใหม่ (ตัวอักษรวาดใหม่ คม)
const finger_gap = ([a, b]) => Math.hypot(a.clientX - b.clientX, a.clientY - b.clientY);
function pinch_start(event) {
	if (event.touches.length !== 2) return;
	const [a, b] = event.touches;
	const x = (a.clientX + b.clientX) / 2;
	const y = (a.clientY + b.clientY) / 2;
	const box = holder.value.getBoundingClientRect();
	pinch = { gap: finger_gap(event.touches), x, y, k: 1 };
	holder.value.style.transformOrigin = `${x - box.left}px ${y - box.top}px`;
}
function pinch_move(event) {
	if (!pinch || event.touches.length !== 2) return;
	event.preventDefault();
	pinch.k = Math.min(
		props.max_zoom / scale.value,
		Math.max(fit_page.value / scale.value, finger_gap(event.touches) / pinch.gap)
	);
	holder.value.style.transform = `scale(${pinch.k})`;
}
function pinch_end() {
	if (!pinch) return;
	const { k, x, y } = pinch;
	pinch = null;
	holder.value.style.transform = "";
	if (Math.abs(k - 1) < 0.02) return;
	set_zoom(scale.value * k, x, y);
}

const on_key = (event) => event.key === "Escape" && emit("close");
let observer = null;

watch(
	() => props.open,
	async (open, was_open) => {
		if (!open && !was_open) return;
		document.body.classList.toggle("ss-locked", open);
		window[open ? "addEventListener" : "removeEventListener"]("keydown", on_key);
		if (open) {
			read_zoom();
			if (props.fetch_file) make_file();
			await nextTick();
			if (!props.open || !scroller.value) return;
			measure();
			observer = new ResizeObserver(measure);
			observer.observe(scroller.value);
		} else {
			file_job++;
			file.value = null;
			observer?.disconnect();
			observer = null;
			pinch = null;
		}
	},
	{ immediate: true }
);
watch(
	() => props.document_kind,
	() => props.open && read_zoom()
);
watch([frame, () => props.html], () => props.open && write(), { flush: "post" });
watch(
	() => props.file_key,
	() => props.open && props.fetch_file && make_file()
);

onBeforeUnmount(() => {
	document.body.classList.remove("ss-locked");
	window.removeEventListener("keydown", on_key);
	observer?.disconnect();
});
</script>

<style scoped>
.ss-html-pages {
	scrollbar-gutter: stable both-edges;
	padding: 24px 24px calc(24px + var(--ss-bottom));
}
.ss-html-fit {
	white-space: nowrap;
}
@media (max-width: 767px) {
	.ss-html-pages {
		scrollbar-gutter: auto;
		padding: 12px 12px calc(12px + var(--ss-bottom));
	}
	.ss-html-fit {
		display: none;
	}
}
</style>
