<!-- เมนูของหมวดเป็นแท็บบนแถบบน (จอ ≥768): หน้ารายการ = ใน TopBar แทนชื่อหน้า, หน้าหลักหมวด = ใน Hero (variant hero)
     ข้อมูลเมนู/ตัวเลข/เมนูที่เลือกจาก AppShell (provide "section_nav") มือถือใช้แถบเมนูล่างของ AppShell แทน -->
<template>
	<nav
		v-if="nav && nav.tabs.value.length > 1"
		class="ss-sectabs"
		:class="`ss-sectabs--${variant}`"
		aria-label="เมนูของหมวด"
	>
		<button
			v-for="tab in nav.tabs.value"
			:key="tab.view"
			type="button"
			class="ss-sectab"
			:class="{ 'is-active': tab.view === nav.active_view.value }"
			:aria-current="tab.view === nav.active_view.value ? 'page' : undefined"
			:title="tab.label"
			@click="nav.open_tab(tab.view)"
		>
			<Icon :name="tab.icon" :size="16" :stroke="tab.view === nav.active_view.value ? 2.4 : 2" />
			<span class="ss-sectab-label">{{ tab.label }}</span>
			<span v-if="tab.badge" class="ss-sectab-badge" :class="tab.badge_tone">{{ tab.badge }}</span>
		</button>
	</nav>
</template>

<script setup>
import { inject } from "vue";
import Icon from "./Icon.vue";

defineProps({ variant: { type: String, default: "bar" } });
const nav = inject("section_nav", null);
</script>
