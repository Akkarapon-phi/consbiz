<template>
	<!-- ดู PDF ในแอปเต็มจอ (ไม่เปิดแท็บใหม่) วาดด้วย PDF.js (public/js/lib/pdfjs) เพราะมือถือแสดง PDF ใน iframe ไม่ได้
	     (Android ดาวน์โหลดแทน, iOS เห็นแค่หน้าแรก) แถบบน: ซูม / แชร์ไฟล์ / ดาวน์โหลด  url จาก site_app.pdf_url -->
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
							:disabled="zoom >= 3"
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

				<div ref="scroller" class="ss-pdf-pages" @dblclick="set_zoom(zoom > 1 ? 1 : 2)">
					<div v-if="loading" class="ss-pdf-note">
						<span class="ss-spinner"></span> กำลังสร้าง PDF…
					</div>
					<div v-else-if="error" class="ss-pdf-note">
						<Icon name="alert" :size="28" />
						<span>{{ error }}</span>
						<a class="ss-btn ss-btn--soft" :href="url" target="_blank" rel="noopener"
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

const props = defineProps({ open: Boolean, url: String, name: String, title: String });
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
			fetch(props.url, { credentials: "same-origin" }),
		]);
		if (!response.ok) throw new Error(`สร้าง PDF ไม่สำเร็จ${await server_reason(response)}`);
		const blob = await response.blob();
		file.value = new File([blob], `${props.name}.pdf`, { type: "application/pdf" });
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
	const ratio = Math.min(window.devicePixelRatio || 1, 3);
	for (let n = 1; n <= doc.numPages; n++) {
		const page = await doc.getPage(n);
		if (id !== render_id) return;
		const base = page.getViewport({ scale: 1 });
		const scale = (Math.min(width, 900) / base.width) * zoom.value;
		const viewport = page.getViewport({ scale: scale * ratio });
		const canvas = document.createElement("canvas");
		canvas.className = "ss-pdf-page";
		canvas.width = Math.floor(viewport.width);
		canvas.height = Math.floor(viewport.height);
		canvas.style.width = `${Math.floor(viewport.width / ratio)}px`;
		canvas.style.height = `${Math.floor(viewport.height / ratio)}px`;
		await page.render({ canvasContext: canvas.getContext("2d"), viewport }).promise;
		if (id !== render_id) return;
		// หน้าแรกขึ้นทันที ไม่ต้องรอทุกหน้า
		if (n === 1) box.replaceChildren(canvas);
		else box.appendChild(canvas);
	}
}

function set_zoom(value) {
	zoom.value = Math.max(1, Math.min(3, value));
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
