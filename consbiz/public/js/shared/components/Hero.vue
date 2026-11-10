<!-- หัวหน้าหลักของทุกหมวด = แถบบนแถวเดียวแบบเดียวกับทุกหน้า (TopBar.vue) ปุ่มจึงอยู่ที่เดิมเมื่อเปลี่ยนหน้า -->
<template>
	<TopBar :title="section.title" />
	<div v-if="state.project" class="ss-home-project">
		<Icon name="building" :size="14" />
		<b :title="state.project.project_name">{{
			state.project.project_name || state.project.name
		}}</b>
		<span>{{ state.project.name }}</span>
	</div>
</template>

<script setup>
import { computed } from "vue";
import Icon from "./Icon.vue";
import TopBar from "./TopBar.vue";
import { app } from "../app.js";
import { state } from "../api.js";

const section = computed(() => app.sections[state.section]);
</script>
