<script setup>
// ห่อ frappe.ui.Popover (espresso) ให้ใช้ใน Vue: animation, ปิดเมื่อคลิกข้างนอก/Esc/Tab ออก และตำแหน่ง ตามระบบ
// slot trigger = ปุ่มเปิด (ได้ { open } ไว้ทำสถานะกด), slot default = เนื้อหาในแผง
// เนื้อหาวาดโดย Vue ใน holder ที่ซ่อนไว้ แล้ว Popover ย้าย element นั้นไปไว้ในแผงที่ <body> ตอนเปิด
// (Vue ยังอัปเดตเนื้อหาได้ตามปกติ เพราะไม่ได้สร้างใหม่ แค่ย้ายที่)
import { onBeforeUnmount, onMounted, ref } from "vue";

const props = defineProps({
	side: { type: String, default: "bottom" },
	align: { type: String, default: "start" },
	panelClass: { type: String, default: "" }, // class เพิ่มที่แผง (เช่น กำหนดความกว้าง ค่าเริ่มต้น 288px)
});

const anchor = ref(null);
const content = ref(null);
const open = ref(false);
let popover = null;

onMounted(() => {
	popover = new frappe.ui.Popover({
		trigger: anchor.value.firstElementChild,
		content: () => content.value,
		side: props.side,
		align: props.align,
		css_class: `cs-es-popover ${props.panelClass}`,
		on_open: () => (open.value = true),
		on_close: () => (open.value = false),
	});
});
onBeforeUnmount(() => popover?.destroy());

defineExpose({ close: () => popover?.close("owner") });
</script>

<template>
	<span ref="anchor" class="cs-popover-anchor">
		<slot name="trigger" :open="open" />
		<span hidden>
			<div ref="content"><slot /></div>
		</span>
	</span>
</template>

<style scoped>
.cs-popover-anchor {
	display: inline-flex;
}
</style>

<!-- แผงอยู่ที่ <body> นอก scope ของ component: เนื้อหาจัด padding เอง -->
<style>
.es-popover.cs-es-popover {
	width: auto;
	padding: 0;
}
</style>
