<template>
	<div class="ss-stepper" :class="[`ss-stepper--${tone}`, { 'is-zero': !Number(modelValue) }]">
		<button
			type="button"
			class="ss-stepper-btn"
			:disabled="Number(modelValue) <= min"
			aria-label="ลด"
			@click="bump(-step)"
		>
			<Icon name="minus" :size="18" :stroke="2.6" />
		</button>
		<input
			class="ss-stepper-input"
			type="number"
			inputmode="decimal"
			:value="modelValue"
			:min="min"
			:max="max"
			@focus="$event.target.select()"
			@change="set($event.target.value)"
		/>
		<button
			type="button"
			class="ss-stepper-btn"
			:disabled="max !== null && Number(modelValue) >= max"
			aria-label="เพิ่ม"
			@click="bump(step)"
		>
			<Icon name="plus" :size="18" :stroke="2.6" />
		</button>
	</div>
</template>

<script setup>
import Icon from "./Icon.vue";
import { vibrate } from "../api.js";

const props = defineProps({
	modelValue: { type: [Number, String], default: 0 },
	min: { type: Number, default: 0 },
	max: { type: Number, default: null },
	step: { type: Number, default: 1 },
	tone: { type: String, default: "brand" },
});
const emit = defineEmits(["update:modelValue"]);

function clamp(value) {
	let v = Number(value);
	if (!Number.isFinite(v)) v = 0;
	v = Math.max(props.min, v);
	if (props.max !== null) v = Math.min(props.max, v);
	return Math.round(v * 1000) / 1000;
}

function set(value) {
	emit("update:modelValue", clamp(value));
}

function bump(delta) {
	vibrate(8);
	set(Number(props.modelValue || 0) + delta);
}
</script>
