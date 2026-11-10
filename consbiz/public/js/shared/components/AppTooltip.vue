<!-- tooltip กลางของทุกหมวด (วางครั้งเดียวใน AppShell) แทน tooltip ของเบราว์เซอร์ที่แต่ง CSS ไม่ได้ หน้าจอยังเขียน title="..." ตามปกติ
     ตอนชี้: ย้าย title ไปเก็บที่ data-tip (เบราว์เซอร์จึงไม่แสดงซ้อน) แล้วแสดงกล่องของแอปใกล้เมาส์ บรรทัดแรกของข้อความหลายบรรทัดเป็นตัวหนา
     จอสัมผัสไม่แสดง ปิดเมื่อกด/เลื่อน/พิมพ์ -->
<template>
	<Teleport to="body">
		<div v-if="text" ref="box" class="ss-tip" :class="{ 'is-multi': text.includes('\n') }" role="tooltip" :style="position">
			{{ text }}
		</div>
	</Teleport>
</template>

<script setup>
import { nextTick, onBeforeUnmount, onMounted, ref } from "vue";

const SHOW_DELAY = 350;
// เพิ่งปิดไปไม่นาน (ไล่ชี้ปุ่มในแถบเครื่องมือ) แสดงทันที
const WARM_TIME = 300;
const MARGIN = 8;
const GAP = 16;

const box = ref(null);
const text = ref("");
const position = ref({});
let anchor = null;
let timer = null;
let hidden_at = 0;
let pointer = { x: 0, y: 0 };

function tip_of(element) {
	if (element.hasAttribute("title")) {
		element.dataset.tip = element.getAttribute("title");
		element.removeAttribute("title");
	}
	return element.dataset.tip;
}

function hide() {
	clearTimeout(timer);
	anchor = null;
	if (text.value) hidden_at = performance.now();
	text.value = "";
}

async function show(tip) {
	text.value = tip;
	position.value = { left: `${pointer.x}px`, top: `${pointer.y + GAP}px` };
	await nextTick();
	const rect = box.value?.getBoundingClientRect();
	if (!rect) return;
	const below = pointer.y + GAP + rect.height <= window.innerHeight - MARGIN;
	position.value = {
		left: `${Math.max(MARGIN, Math.min(pointer.x + 4, window.innerWidth - rect.width - MARGIN))}px`,
		top: `${below ? pointer.y + GAP : Math.max(MARGIN, pointer.y - rect.height - MARGIN)}px`,
	};
}

function on_over(event) {
	if (event.pointerType === "touch" || event.buttons) return;
	const element = event.target.closest?.("[title], [data-tip]") || null;
	if (element === anchor) return;
	hide();
	if (!element) return;
	const tip = tip_of(element);
	if (!tip) return;
	anchor = element;
	pointer = { x: event.clientX, y: event.clientY };
	const warm = performance.now() - hidden_at < WARM_TIME;
	timer = setTimeout(() => show(tip), warm ? 0 : SHOW_DELAY);
}
function on_move(event) {
	if (!text.value) pointer = { x: event.clientX, y: event.clientY };
}

onMounted(() => {
	document.addEventListener("pointerover", on_over);
	document.addEventListener("pointermove", on_move, { passive: true });
	document.addEventListener("pointerdown", hide, true);
	document.addEventListener("keydown", hide, true);
	window.addEventListener("scroll", hide, true);
	window.addEventListener("blur", hide);
});
onBeforeUnmount(() => {
	clearTimeout(timer);
	document.removeEventListener("pointerover", on_over);
	document.removeEventListener("pointermove", on_move);
	document.removeEventListener("pointerdown", hide, true);
	document.removeEventListener("keydown", hide, true);
	window.removeEventListener("scroll", hide, true);
	window.removeEventListener("blur", hide);
});
</script>
