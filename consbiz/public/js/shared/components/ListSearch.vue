<!-- ช่องค้นหาของหน้ารายการ ในแถวตัวกรองของหัวรายการ (.ss-list-filterbar, หน้าตาใหม่) ซ้ายสุดของแถว ตัวกรองแบบเลือกต่อท้าย
     มีคำค้น = ปุ่ม X ท้ายช่องล้างคำค้น (Esc ในช่องที่มีคำค้น = ล้าง, ว่างแล้ว = ออกจากช่อง)
     ListHead.vue ใช้ตัวนี้ (v-model, placeholder, focus()) -->
<template>
	<label class="ss-toolbar-search ss-list-search" :class="{ 'has-value': modelValue }">
		<Icon name="search" :size="16" />
		<input
			ref="input"
			:value="modelValue"
			type="search"
			:placeholder="placeholder"
			@input="$emit('update:modelValue', $event.target.value)"
			@keydown.esc="esc"
		/>
		<button
			v-if="modelValue"
			type="button"
			class="ss-list-search-clear"
			aria-label="ล้างคำค้น"
			title="ล้างคำค้น"
			@mousedown.prevent
			@click="clear"
		>
			<Icon name="x" :size="14" :stroke="2.4" />
		</button>
	</label>
</template>

<script setup>
import { ref } from "vue";
import Icon from "./Icon.vue";

const props = defineProps({
	modelValue: String,
	placeholder: String,
});
const emit = defineEmits(["update:modelValue"]);

const input = ref(null);

function clear() {
	emit("update:modelValue", "");
	input.value?.focus();
}

function esc() {
	if (props.modelValue) emit("update:modelValue", "");
	else input.value?.blur();
}

defineExpose({ focus: () => input.value?.focus() });
</script>
