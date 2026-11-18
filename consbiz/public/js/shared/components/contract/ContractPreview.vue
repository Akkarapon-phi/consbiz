<!-- ตัวอย่างสัญญาจ้างแบบ real-time (ตกลง 2026-11-18): ส่งข้อมูลที่ยังไม่บันทึกไป contract_terms.preview (หน้าเดียวกับ PDF)
     ข้อมูลเปลี่ยน = รอ 500ms แล้วโหลดใหม่ แทนเนื้อหาใน iframe เดิม (ตำแหน่งเลื่อนไม่หาย) ย่อกระดาษ A4 ให้พอดีความกว้างกรอบ
     แบ่งหน้าจริง (paginate, ตกลง 2026-11-18): เนื้อหาไหลเป็นคอลัมน์กว้าง/สูงเท่าพื้นที่พิมพ์ 1 หน้า (Chrome ตัดย่อหน้า/break-inside แบบเดียวกับตอนพิมพ์)
     แล้วแสดงคอลัมน์ที่ i ในกระดาษหน้าที่ i พร้อมขอบตามแม่แบบ เส้นประ = ขอบพื้นที่พิมพ์ เลขหน้ามุมล่าง
     iframe sandbox ไม่มี allow-scripts (เนื้อหามาจากผู้ใช้) allow-same-origin ให้หน้าแม่ย่อ/แทนเนื้อหาได้ -->
<template>
	<div ref="box" class="ec-preview" :class="{ 'is-busy': busy }">
		<iframe ref="frame" title="ตัวอย่างสัญญา" sandbox="allow-same-origin" @load="on_load"></iframe>
		<span v-if="busy" class="ec-preview-busy"><span class="ss-spinner"></span></span>
		<p v-if="error" class="ec-preview-error">{{ error }}</p>
	</div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref, watch } from "vue";
import { post } from "../../api.js";
import { ec_paginate } from "./paginate.js";

const props = defineProps({
	// ช่องของสัญญา หรือของแม่แบบ (+ sample: true = ค่าตัวอย่าง, employee = พนักงานตัวอย่าง)
	data: { type: Object, required: true },
});

const box = ref(null);
const frame = ref(null);
const busy = ref(false);
const error = ref("");
let timer = null;
let seq = 0;
let loaded = false;
// กระดาษ A4 กว้าง 210mm (~794px) + ระยะขอบ
const PAPER = 830;

// แบ่งหน้าด้วย paginate.js ชุดเดียวกับที่ฝังใน PDF (contract_terms.render_contract) = ตัวอย่างตรงกับ PDF
const paginate = () => {
	const doc = frame.value?.contentDocument;
	if (!doc) return;
	// แบ่งหน้าใหม่ = ลบแผ่นเดิมก่อน ตำแหน่งเลื่อนจะหลุด: จำแล้วคืนค่า
	const top = doc.scrollingElement?.scrollTop || 0;
	ec_paginate(doc, { guides: true });
	if (doc.scrollingElement) doc.scrollingElement.scrollTop = top;
};

// ฟอนต์ + รูป (โลโก้หัวกระดาษ) โหลดเสร็จแล้วค่อยวัดใหม่ (ความสูงเปลี่ยน)
async function settled(doc) {
	await doc.fonts?.ready;
	await Promise.all([...doc.images].map((img) => (img.complete ? null : img.decode().catch(() => null))));
}

async function on_load() {
	const doc = frame.value?.contentDocument;
	if (!doc) return;
	fit();
	paginate();
	await settled(doc);
	paginate();
}

function fit() {
	const doc = frame.value?.contentDocument;
	if (!doc?.documentElement || !box.value) return;
	const zoom = Math.min(1, box.value.clientWidth / PAPER);
	doc.documentElement.style.zoom = String(zoom);
}

async function render() {
	const mine = ++seq;
	busy.value = true;
	try {
		const html = await post("consbiz.contract_terms.preview", { data: JSON.stringify(props.data) });
		if (mine !== seq || !frame.value) return;
		error.value = "";
		const doc = frame.value.contentDocument;
		if (loaded && doc?.body) {
			const next = new DOMParser().parseFromString(html, "text/html");
			const top = doc.scrollingElement?.scrollTop || 0;
			doc.body.innerHTML = next.body.innerHTML;
			if (doc.scrollingElement) doc.scrollingElement.scrollTop = top;
			paginate();
			await settled(doc);
			if (mine === seq) paginate();
		} else {
			frame.value.srcdoc = html;
			loaded = true;
		}
	} catch (e) {
		if (mine === seq) error.value = e?.message || "แสดงตัวอย่างไม่ได้";
	} finally {
		if (mine === seq) busy.value = false;
	}
}

watch(
	() => JSON.stringify(props.data),
	() => {
		clearTimeout(timer);
		timer = setTimeout(render, 500);
	}
);

let observer = null;
onMounted(() => {
	render();
	observer = new ResizeObserver(fit);
	observer.observe(box.value);
});
onBeforeUnmount(() => {
	clearTimeout(timer);
	observer?.disconnect();
});
</script>
