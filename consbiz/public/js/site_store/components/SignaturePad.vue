<template>
	<div class="ss-sign" :class="{ 'is-signed': signed }">
		<canvas
			ref="canvas"
			@pointerdown="start"
			@pointermove="draw"
			@pointerup="end"
			@pointercancel="end"
			@pointerleave="end"
		></canvas>
		<div v-if="!signed" class="ss-sign-hint">
			<Icon name="pen" :size="18" />
			{{ hint }}
		</div>
		<button v-if="signed" type="button" class="ss-sign-clear" @click="clear">
			<Icon name="undo" :size="16" /> ล้าง
		</button>
	</div>
</template>

<script setup>
// ลายเซ็น: เก็บเป็น data URL (PNG) ตรงกับช่อง Signature ของ Frappe
import { onMounted, onBeforeUnmount, ref } from "vue";
import Icon from "./Icon.vue";

defineProps({ hint: { type: String, default: "เซ็นชื่อในกรอบนี้" } });
const emit = defineEmits(["update:modelValue"]);

const canvas = ref(null);
const signed = ref(false);
let ctx = null;
let drawing = false;
let last = null;

function resize() {
	const el = canvas.value;
	if (!el) return;
	const ratio = window.devicePixelRatio || 1;
	const rect = el.getBoundingClientRect();
	el.width = rect.width * ratio;
	el.height = rect.height * ratio;
	ctx = el.getContext("2d");
	ctx.scale(ratio, ratio);
	ctx.lineCap = "round";
	ctx.lineJoin = "round";
	ctx.strokeStyle = getComputedStyle(el).color || "#111";
	signed.value = false;
	emit("update:modelValue", null);
}

function point(e) {
	const rect = canvas.value.getBoundingClientRect();
	return { x: e.clientX - rect.left, y: e.clientY - rect.top, p: e.pressure || 0.5 };
}

function start(e) {
	e.preventDefault();
	canvas.value.setPointerCapture?.(e.pointerId);
	drawing = true;
	last = point(e);
}

function draw(e) {
	if (!drawing) return;
	const p = point(e);
	ctx.lineWidth = 1.6 + p.p * 2.2;
	ctx.beginPath();
	ctx.moveTo(last.x, last.y);
	ctx.quadraticCurveTo(last.x, last.y, (last.x + p.x) / 2, (last.y + p.y) / 2);
	ctx.lineTo(p.x, p.y);
	ctx.stroke();
	last = p;
	signed.value = true;
}

function end() {
	if (!drawing) return;
	drawing = false;
	if (signed.value) emit("update:modelValue", export_png());
}

// ลายเซ็นสีเข้มบนพื้นโปร่งใส (โหมดมืดก็พิมพ์ออกมาเป็นเส้นดำ)
function export_png() {
	const src = canvas.value;
	const out = document.createElement("canvas");
	out.width = src.width;
	out.height = src.height;
	const o = out.getContext("2d");
	o.drawImage(src, 0, 0);
	o.globalCompositeOperation = "source-in";
	o.fillStyle = "#111";
	o.fillRect(0, 0, out.width, out.height);
	return out.toDataURL("image/png");
}

function clear() {
	resize();
}

onMounted(() => {
	resize();
	window.addEventListener("resize", resize);
});
onBeforeUnmount(() => window.removeEventListener("resize", resize));
</script>
