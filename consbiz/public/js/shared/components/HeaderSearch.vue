<!-- ช่องค้นหาของหน้ารายการบนแถบบน (จอ ≥768)
     จอ < 1180 พื้นที่แถบบนไม่พอ: เป็นปุ่มแว่นขยาย กดแล้วกางทับแถบบน ออกจากช่องแล้วพับ (มีคำค้นอยู่ = ปุ่มมีจุด) -->
<template>
	<div class="ss-header-search" :class="{ 'is-open': open, 'has-value': modelValue }">
		<button
			type="button"
			class="ss-icon-btn ss-header-search-toggle"
			aria-label="ค้นหา"
			title="ค้นหา"
			@mousedown.prevent
			@click="toggle"
		>
			<Icon name="search" :size="20" />
		</button>
		<label class="ss-toolbar-search ss-header-search-box">
			<Icon name="search" :size="17" />
			<input
				ref="input"
				:value="modelValue"
				type="search"
				:placeholder="placeholder"
				@input="$emit('update:modelValue', $event.target.value)"
				@blur="open = false"
				@keydown.esc="input.blur()"
			/>
		</label>
	</div>
</template>

<script setup>
import { nextTick, ref } from "vue";
import Icon from "./Icon.vue";

defineProps({
	modelValue: String,
	placeholder: String,
});
defineEmits(["update:modelValue"]);

const open = ref(false);
const input = ref(null);

async function focus() {
	open.value = true;
	await nextTick();
	input.value?.focus();
}

function toggle() {
	if (open.value) input.value?.blur();
	else focus();
}

defineExpose({ focus });
</script>
