<!-- ดู PDF ในแอปเต็มจอ (ไม่เปิดแท็บใหม่) วาดด้วย PDF.js (public/js/lib/pdfjs) เพราะมือถือแสดง PDF ใน iframe ไม่ได้
     (Android ดาวน์โหลดแทน, iOS เห็นแค่หน้าแรก) แถบบน: ซูม / แชร์ไฟล์ / ดาวน์โหลด  url จาก site_app.pdf_url -->
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
					<div class="ss-pdf-zoom">
						<button
							type="button"
							class="ss-icon-btn"
							aria-label="ย่อ"
							:disabled="zoom <= 1"
							@click="set_zoom(zoom - 0.5)"
						>
							<Icon name="minus" :size="18" :stroke="2.4" />
						</button>
						<span>{{ Math.round(zoom * 100) }}%</span>
						<button
							type="button"
							class="ss-icon-btn"
							aria-label="ขยาย"
							:disabled="zoom >= max_zoom"
							@click="set_zoom(zoom + 0.5)"
						>
							<Icon name="plus" :size="18" :stroke="2.4" />
						</button>
					</div>
					<button
						v-if="can_share"
						type="button"
						class="ss-icon-btn"
						aria-label="แชร์ไฟล์ PDF"
						title="แชร์ไฟล์ PDF"
						:disabled="!file"
						@click="share"
					>
						<Icon name="send" :size="19" />
					</button>
					<button
						type="button"
						class="ss-icon-btn"
						aria-label="ดาวน์โหลด"
						title="ดาวน์โหลด"
						:disabled="!file"
						@click="download"
					>
						<Icon name="receive" :size="20" />
					</button>
				</header>

				<div
					ref="scroller"
					class="ss-pdf-pages"
					@dblclick="set_zoom(zoom > 1 ? 1 : 2)"
					@touchstart="pinch_start"
					@touchmove="pinch_move"
					@touchend="pinch_end"
					@touchcancel="pinch_end"
				>
					<div v-if="loading" class="ss-pdf-note">
						<span class="ss-spinner"></span> กำลังสร้าง PDF…
					</div>
					<div v-else-if="error" class="ss-pdf-note">
						<Icon name="alert" :size="28" />
						<span>{{ error }}</span>
						<a v-if="url" class="ss-btn ss-btn--soft" :href="url" target="_blank" rel="noopener"
							>เปิดในเบราว์เซอร์</a
						>
					</div>
					<div ref="holder" class="ss-pdf-holder"></div>
				</div>
			</div>
		</Transition>
	</Teleport>
</template>

<script setup>
import { nextTick, onBeforeUnmount, ref, shallowRef, watch } from "vue";
import Icon from "./Icon.vue";
import { show_error, strip_html } from "../api.js";

// fetch_file = สร้างไฟล์เอง คืน Response (ใช้แทน url), file_name = ชื่อไฟล์ตอนบันทึก/แชร์ (ไม่ใส่ = name)
const props = defineProps({
	open: Boolean,
	url: String,
	name: String,
	title: String,
	fetch_file: Function,
	file_name: String,
	max_zoom: { type: Number, default: 3 },
});
const emit = defineEmits(["close"]);

// โหลด PDF.js เมื่อเปิดครั้งแรกเท่านั้น (ไม่รวมใน bundle ของแอป)
const PDFJS = "/assets/consbiz/js/lib/pdfjs/pdf.min.js";
const WORKER = "/assets/consbiz/js/lib/pdfjs/pdf.worker.min.js";

const scroller = ref(null);
const holder = ref(null);
const loading = ref(false);
const error = ref("");
const pages = ref(0);
const zoom = ref(1);
const file = shallowRef(null);
const pdf = shallowRef(null);
const can_share = typeof navigator !== "undefined" && !!navigator.canShare;
let render_id = 0;
let pinch = null;
let pending_scroll = null;
// จำกัดขนาด canvas (Safari บนมือถือวาดเกินนี้ไม่ได้) เอกสารหลายหน้าแบ่งงบกัน
const MAX_PAGE_PIXELS = 16e6;
const MAX_TOTAL_PIXELS = 96e6;
let lib_promise = null;

function pdfjs() {
	lib_promise ||= import(/* @vite-ignore */ PDFJS).then((lib) => {
		lib.GlobalWorkerOptions.workerSrc = WORKER;
		return lib;
	});
	return lib_promise;
}

// เหตุผลจาก server (เช่น ตัวสร้าง PDF ของ Print Format ใช้ไม่ได้) แสดงต่อท้ายข้อความ
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

async function load() {
	loading.value = true;
	error.value = "";
	pages.value = 0;
	file.value = null;
	try {
		const [lib, response] = await Promise.all([
			pdfjs(),
			props.fetch_file ? props.fetch_file() : fetch(props.url, { credentials: "same-origin" }),
		]);
		if (!response.ok) throw new Error(`สร้าง PDF ไม่สำเร็จ${await server_reason(response)}`);
		const blob = await response.blob();
		file.value = new File([blob], `${props.file_name || props.name}.pdf`, { type: "application/pdf" });
		pdf.value = await lib.getDocument({ data: new Uint8Array(await blob.arrayBuffer()) }).promise;
		pages.value = pdf.value.numPages;
		loading.value = false;
		await nextTick();
		render();
	} catch (err) {
		console.error(err);
		error.value = err?.message?.startsWith("สร้าง") ? err.message : "แสดง PDF ในแอปไม่ได้";
		loading.value = false;
	}
}

// วาดทุกหน้าเต็มความกว้างจอ × ซูม ที่ความละเอียดของจอ (devicePixelRatio)
async function render() {
	const id = ++render_id;
	const doc = pdf.value;
	const box = holder.value;
	if (!doc || !box) return;
	const width = (scroller.value?.clientWidth || window.innerWidth) - 24;
	const budget = Math.min(MAX_PAGE_PIXELS, MAX_TOTAL_PIXELS / doc.numPages);
	const sheets = [];
	// จองขนาดทุกหน้าก่อนวาด ความสูงรวมถูกต้องทันที เลื่อนไปจุดที่ซูมได้
	for (let n = 1; n <= doc.numPages; n++) {
		const page = await doc.getPage(n);
		if (id !== render_id) return;
		const base = page.getViewport({ scale: 1 });
		const css = (Math.min(width, 900) / base.width) * zoom.value;
		const area = base.width * base.height * css * css;
		const ratio = Math.min(window.devicePixelRatio || 1, 3, Math.sqrt(budget / area));
		const viewport = page.getViewport({ scale: css * ratio });
		const canvas = document.createElement("canvas");
		canvas.className = "ss-pdf-page";
		canvas.width = Math.floor(viewport.width);
		canvas.height = Math.floor(viewport.height);
		canvas.style.width = `${Math.floor(viewport.width / ratio)}px`;
		canvas.style.height = `${Math.floor(viewport.height / ratio)}px`;
		sheets.push({ page, viewport, canvas });
	}
	box.replaceChildren(...sheets.map((sheet) => sheet.canvas));
	if (pending_scroll) {
		scroller.value.scrollTo(pending_scroll);
		pending_scroll = null;
	}
	for (const { page, viewport, canvas } of sheets) {
		try {
			await page.render({ canvasContext: canvas.getContext("2d"), viewport }).promise;
		} catch (err) {
			// ปิดหน้าต่างหรือซูมต่อระหว่างวาด
			if (err?.name === "RenderingCancelledException" || id !== render_id) return;
			throw err;
		}
		if (id !== render_id) return;
	}
}

function set_zoom(value) {
	zoom.value = Math.max(1, Math.min(props.max_zoom, value));
}

// ซูมสองนิ้ว: ระหว่างนิ้วขยับใช้ transform (ลื่น) ปล่อยนิ้วแล้ววาดใหม่ให้คมตามจุดที่ซูม
const finger_gap = ([a, b]) => Math.hypot(a.clientX - b.clientX, a.clientY - b.clientY);
function pinch_start(event) {
	if (event.touches.length !== 2) return;
	const [a, b] = event.touches;
	const x = (a.clientX + b.clientX) / 2;
	const y = (a.clientY + b.clientY) / 2;
	const box = holder.value.getBoundingClientRect();
	pinch = { gap: finger_gap(event.touches), x, y, ox: x - box.left, oy: y - box.top, k: 1 };
	holder.value.style.transformOrigin = `${pinch.ox}px ${pinch.oy}px`;
}
function pinch_move(event) {
	if (!pinch || event.touches.length !== 2) return;
	event.preventDefault();
	pinch.k = Math.min(props.max_zoom / zoom.value, Math.max(1 / zoom.value, finger_gap(event.touches) / pinch.gap));
	holder.value.style.transform = `scale(${pinch.k})`;
}
function pinch_end() {
	if (!pinch) return;
	const { k, x, y, ox, oy } = pinch;
	pinch = null;
	holder.value.style.transform = "";
	if (Math.abs(k - 1) < 0.02) return;
	const view = scroller.value.getBoundingClientRect();
	const box = holder.value.getBoundingClientRect();
	pending_scroll = {
		left: scroller.value.scrollLeft + box.left - view.left + ox * k - (x - view.left),
		top: scroller.value.scrollTop + box.top - view.top + oy * k - (y - view.top),
	};
	set_zoom(zoom.value * k);
}

function save_file(f) {
	const href = URL.createObjectURL(f);
	const link = Object.assign(document.createElement("a"), { href, download: f.name });
	document.body.appendChild(link);
	link.click();
	link.remove();
	setTimeout(() => URL.revokeObjectURL(href), 2000);
}

async function share() {
	try {
		if (navigator.canShare?.({ files: [file.value] })) {
			await navigator.share({ files: [file.value], title: `${props.title} ${props.name}` });
		} else {
			save_file(file.value);
		}
	} catch (err) {
		// ผู้ใช้ปิดหน้าต่างแชร์เอง ไม่ใช่ข้อผิดพลาด
		if (err?.name !== "AbortError") show_error(err);
	}
}

function download() {
	save_file(file.value);
}

const on_key = (event) => event.key === "Escape" && emit("close");
let resize_timer = null;
const on_resize = () => {
	clearTimeout(resize_timer);
	resize_timer = setTimeout(render, 200);
};

watch(
	() => props.open,
	(open) => {
		document.body.classList.toggle("ss-locked", open);
		window[open ? "addEventListener" : "removeEventListener"]("keydown", on_key);
		window[open ? "addEventListener" : "removeEventListener"]("resize", on_resize);
		if (open) {
			zoom.value = 1;
			load();
		} else {
			render_id++;
			pdf.value?.destroy();
			pdf.value = null;
		}
	}
);
watch(zoom, () => render());

onBeforeUnmount(() => {
	document.body.classList.remove("ss-locked");
	window.removeEventListener("keydown", on_key);
	window.removeEventListener("resize", on_resize);
	pdf.value?.destroy();
});
</script>
