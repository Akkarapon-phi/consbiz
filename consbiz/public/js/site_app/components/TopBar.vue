<template>
	<header class="ss-topbar" :class="{ 'is-scrolled': scrolled, 'ss-topbar--hero': hero }">
		<button v-if="back_to" type="button" class="ss-icon-btn" aria-label="ย้อนกลับ" @click="go_back">
			<Icon name="chevron-left" :size="24" :stroke="2.4" />
		</button>
		<div class="ss-topbar-title">
			<div class="ss-topbar-main">{{ title }}</div>
			<div v-if="subtitle" class="ss-topbar-sub">{{ subtitle }}</div>
		</div>
		<slot name="actions" />
	</header>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref } from "vue";
import Icon from "./Icon.vue";
import { back } from "../api.js";

const props = defineProps({
	title: String,
	subtitle: String,
	back_to: [String, Boolean],
	back_params: { type: Object, default: () => ({}) },
	hero: Boolean,
});

const scrolled = ref(false);
const on_scroll = () => (scrolled.value = window.scrollY > 6);
onMounted(() => window.addEventListener("scroll", on_scroll, { passive: true }));
onBeforeUnmount(() => window.removeEventListener("scroll", on_scroll));

function go_back() {
	back(typeof props.back_to === "string" ? props.back_to : "home", props.back_params);
}
</script>
