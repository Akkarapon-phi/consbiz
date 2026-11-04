<template>
	<div class="ss-segmented" :style="{ '--count': options.length, '--index': index }">
		<span class="ss-segmented-thumb"></span>
		<button
			v-for="option in options"
			:key="option.value"
			type="button"
			:class="{ 'is-active': option.value === modelValue }"
			@click="$emit('update:modelValue', option.value)"
		>
			{{ option.label }}
			<span v-if="option.count" class="ss-count">{{ option.count }}</span>
		</button>
	</div>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
	modelValue: String,
	options: { type: Array, required: true },
});
defineEmits(["update:modelValue"]);
const index = computed(() =>
	Math.max(
		0,
		props.options.findIndex((o) => o.value === props.modelValue)
	)
);
</script>
