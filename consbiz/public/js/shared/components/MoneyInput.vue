<!-- ช่องกรอกจำนวนเงิน: ไม่ได้โฟกัส = 1,234.50 (จุลภาค + ทศนิยม 2 ตำแหน่ง), โฟกัส = ตัวเลขดิบให้แก้ง่าย
     attrs อื่น (class, aria-label, data-col, @keydown) ส่งต่อให้ <input> -->
<template>
	<input
		:value="focused ? raw : format_money_input(modelValue)"
		type="text"
		inputmode="decimal"
		autocomplete="off"
		@focus="on_focus"
		@blur="on_blur"
		@input="on_input"
	/>
</template>

<script setup>
import { ref } from "vue";
import { format_money_input, parse_money_input } from "../api.js";

const props = defineProps({ modelValue: { type: [Number, String], default: null } });
const emit = defineEmits(["update:modelValue"]);

const focused = ref(false);
const raw = ref("");

function on_focus(event) {
	focused.value = true;
	const value = props.modelValue;
	raw.value = value === null || value === undefined || value === "" ? "" : String(Number(value));
	requestAnimationFrame(() => event.target.select());
}

function on_input(event) {
	// รับเฉพาะตัวเลข จุด จุลภาค และเครื่องหมายลบ
	raw.value = event.target.value.replace(/[^\d.,-]/g, "");
	if (raw.value !== event.target.value) event.target.value = raw.value;
	emit("update:modelValue", parse_money_input(raw.value) ?? 0);
}

function on_blur() {
	focused.value = false;
}
</script>
