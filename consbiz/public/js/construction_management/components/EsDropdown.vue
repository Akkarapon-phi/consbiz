<script setup>
// ห่อ frappe.ui.Dropdown (espresso) ให้ใช้ใน Vue: เมนูคำสั่งธรรมดาที่หน้าตา/animation/คีย์บอร์ดเหมือนเมนูอื่นของระบบ
// slot trigger = ปุ่มเปิด, options = รายการตามรูปแบบ MenuItem/MenuGroup ของ Frappe ({ label, icon, onclick, selected }
// หรือ { group, hide_label, options }) อ่านค่าล่าสุดทุกครั้งที่เปิด
import { onBeforeUnmount, onMounted, ref } from "vue";

const props = defineProps({
	options: { type: Array, required: true },
	side: { type: String, default: "bottom" },
	align: { type: String, default: "start" },
});

const anchor = ref(null);
let dropdown = null;

onMounted(() => {
	dropdown = new frappe.ui.Dropdown({
		trigger: anchor.value.firstElementChild,
		options: () => props.options,
		side: props.side,
		align: props.align,
	});
});
onBeforeUnmount(() => dropdown?.destroy());
</script>

<template>
	<span ref="anchor" class="cs-dropdown-anchor"><slot name="trigger" /></span>
</template>

<style scoped>
.cs-dropdown-anchor {
	display: inline-flex;
}
</style>
