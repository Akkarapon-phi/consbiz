<template>
	<div class="ss-empty">
		<div class="ss-empty-art">
			<span class="ss-empty-ring"></span>
			<Icon :name="icon" :size="34" :stroke="1.8" />
		</div>
		<div class="ss-empty-title">{{ title }}</div>
		<div v-if="text" class="ss-empty-text">{{ text }}</div>
		<slot />
	</div>
</template>

<script setup>
import Icon from "./Icon.vue";

defineProps({
	icon: { type: String, default: "inbox" },
	title: String,
	text: String,
});
</script>
