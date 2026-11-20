<!-- ตัวอย่างงานพิมพ์ของเอกสาร HTML ที่สร้างในหน้า (ไม่ใช่ PDF จากเซิร์ฟเวอร์ ซึ่งใช้ PdfViewer)
     กดพิมพ์จากปุ่มในหน้าแล้วเห็นตัวอย่างก่อนเสมอ แถบบนเหมือน PdfViewer: ปิด / ชื่อ / พิมพ์ (บันทึก PDF จากหน้าต่างพิมพ์ของเบราว์เซอร์)
     html = เอกสารทั้งหน้า (<!doctype html>...) ใส่ @page ของเอกสารเอง -->
<template>
	<Teleport to="body">
		<Transition name="ss-pdf">
			<div v-if="open" class="ss-pdf" role="dialog" aria-modal="true" :aria-label="title">
				<header class="ss-pdf-bar">
					<button type="button" class="ss-icon-btn" aria-label="ปิด" @click="$emit('close')">
						<Icon name="x" :size="22" />
					</button>
					<div class="ss-pdf-title">
						<b>{{ title }}</b>
						<small v-if="subtitle">{{ subtitle }}</small>
					</div>
					<button
						type="button"
						class="ss-icon-btn"
						aria-label="พิมพ์ / บันทึก PDF"
						title="พิมพ์ / บันทึก PDF"
						:disabled="!ready"
						@click="print"
					>
						<Icon name="printer" :size="19" />
					</button>
				</header>
				<div class="ss-pdf-pages">
					<div class="ss-html-preview" :style="{ width: `${width}px` }">
						<iframe
							ref="frame"
							:srcdoc="html"
							:title="`ตัวอย่างงานพิมพ์ ${title}`"
							:style="{ height: `${height}px` }"
							@load="on_load"
						></iframe>
					</div>
				</div>
			</div>
		</Transition>
	</Teleport>
</template>

<script setup>
import { ref, watch } from "vue";
import Icon from "./Icon.vue";

// width = ความกว้างหน้ากระดาษบนจอ (px) ค่าเริ่มต้น A4 แนวนอน
const props = defineProps({
	open: Boolean,
	html: String,
	title: String,
	subtitle: String,
	width: { type: Number, default: 1123 },
});
const emit = defineEmits(["close"]);

const frame = ref(null);
const ready = ref(false);
const height = ref(600);

function on_load() {
	const doc = frame.value?.contentDocument;
	if (!doc) return;
	// รอฟอนต์ก่อนวัดความสูง/เปิดให้พิมพ์ ไม่งั้นพิมพ์ด้วยฟอนต์สำรอง
	(doc.fonts?.ready || Promise.resolve()).then(() => {
		height.value = Math.max(400, doc.documentElement.scrollHeight + 32);
		ready.value = true;
	});
}

function print() {
	const win = frame.value?.contentWindow;
	if (!win) return;
	win.focus();
	win.print();
}

const on_key = (event) => event.key === "Escape" && emit("close");
watch(
	() => props.open,
	(open) => {
		ready.value = false;
		document.body.classList.toggle("ss-locked", open);
		window[open ? "addEventListener" : "removeEventListener"]("keydown", on_key);
	}
);
</script>
