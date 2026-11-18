<!-- ดูเอกสาร HTML เต็มจอ (ตกลง 2026-11-18 ใช้แทน PdfViewer กับเอกสารที่สร้างเป็น HTML ในเครื่อง ตอนนี้ = แท็บพิมพ์ของแผนงาน): iframe เอกสารเดียวกับ Preview ย่อ/ขยายด้วย transform
     เบราว์เซอร์วาดตัวอักษรใหม่ทุกระดับซูม = คมเท่า Preview ต่างจาก PdfViewer ที่วาด PDF เป็นภาพ (canvas) ที่ความละเอียดจำกัด
     แถบบน: ซูม / พิมพ์ (พิมพ์ iframe นี้เอง) / แชร์ไฟล์ PDF / ดาวน์โหลด PDF
     ไฟล์ PDF (fetch_file) เริ่มสร้างเบื้องหลังตอนเปิด ไม่ต้องรอก่อนแสดง และพร้อมแล้วตอนกดแชร์
     (Web Share ต้องเรียกทันทีหลังผู้ใช้กด ถ้ารอสร้าง PDF นานเบราว์เซอร์จะไม่ยอมแชร์)
     zoom 1 = พอดีความกว้างจอ iframe ไม่รับการแตะ (pointer-events: none) ให้ซูมสองนิ้ว/เลื่อนที่กรอบนอก -->
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
						<button type="button" class="ss-icon-btn" aria-label="ย่อ" :disabled="zoom <= 1" @click="set_zoom(zoom - 0.5)">
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
					<button type="button" class="ss-icon-btn" aria-label="พิมพ์" title="พิมพ์" :disabled="printing" @click="print">
						<span v-if="printing" class="ss-spinner"></span>
						<Icon v-else name="printer" :size="19" />
					</button>
					<button
						type="button"
						class="ss-icon-btn"
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
					class="ss-pdf-pages"
					@dblclick="set_zoom(zoom > 1 ? 1 : 2)"
					@touchstart="pinch_start"
					@touchmove="pinch_move"
					@touchend="pinch_end"
					@touchcancel="pinch_end"
				>
					<div ref="holder" class="ss-pdf-holder">
						<div class="ss-html-sheet" :style="{ width: `${width * scale}px`, height: `${height * scale}px` }">
							<iframe
								ref="frame"
								class="ss-html-frame"
								:title="title"
								tabindex="-1"
								scrolling="no"
								:style="{ width: `${width}px`, height: `${height}px`, transform: `scale(${scale})` }"
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
	pages: Number,
	name: String,
	title: String,
	fetch_file: Function,
	file_name: String,
	max_zoom: { type: Number, default: 8 },
});
const emit = defineEmits(["close"]);

const scroller = ref(null);
const holder = ref(null);
const frame = ref(null);
const zoom = ref(1);
const view_w = ref(0);
const printing = ref(false);
const file = shallowRef(null);
// loading / ready / error (กดอีกครั้ง = ลองสร้างใหม่)
const file_state = ref("loading");
let file_error = "";
let file_job = 0;
let pinch = null;
let pending_scroll = null;

const scale = computed(() => (view_w.value ? (view_w.value / props.width) * zoom.value : 0.3));
const file_label = (label) =>
	file_state.value === "loading" ? "กำลังสร้าง PDF…" : file_state.value === "error" ? `${label} (ลองใหม่)` : label;

function measure() {
	if (scroller.value) view_w.value = scroller.value.clientWidth - 24;
}

function write() {
	const doc = frame.value?.contentDocument;
	if (!doc || !props.html) return;
	doc.open();
	doc.write(props.html);
	doc.close();
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

// ซูมด้วยปุ่ม: คงจุดกลางจอไว้
function set_zoom(value) {
	const next = Math.max(1, Math.min(props.max_zoom, value));
	if (next === zoom.value) return;
	const el = scroller.value;
	if (el && !pending_scroll) {
		const k = next / zoom.value;
		pending_scroll = {
			left: (el.scrollLeft + el.clientWidth / 2) * k - el.clientWidth / 2,
			top: (el.scrollTop + el.clientHeight / 2) * k - el.clientHeight / 2,
		};
	}
	zoom.value = next;
}
watch(zoom, async () => {
	await nextTick();
	if (pending_scroll && scroller.value) scroller.value.scrollTo(pending_scroll);
	pending_scroll = null;
});

// ซูมสองนิ้ว: ระหว่างขยับใช้ transform ทั้งกรอบ ปล่อยนิ้วแล้วตั้ง scale ใหม่ (ตัวอักษรวาดใหม่ คม)
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

const on_key = (event) => event.key === "Escape" && emit("close");
let observer = null;

watch(
	() => props.open,
	async (open) => {
		document.body.classList.toggle("ss-locked", open);
		window[open ? "addEventListener" : "removeEventListener"]("keydown", on_key);
		if (open) {
			zoom.value = 1;
			if (props.fetch_file) make_file();
			await nextTick();
			measure();
			write();
			observer = new ResizeObserver(measure);
			observer.observe(scroller.value);
		} else {
			file_job++;
			file.value = null;
			observer?.disconnect();
			observer = null;
		}
	}
);
watch(
	() => props.html,
	() => props.open && write()
);

onBeforeUnmount(() => {
	document.body.classList.remove("ss-locked");
	window.removeEventListener("keydown", on_key);
	observer?.disconnect();
});
</script>
