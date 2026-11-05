<!-- แสดงข้อความจาก Text Editor ของระบบเต็ม (HTML) ผ่าน sanitize_html เท่านั้น
     lines = จำนวนบรรทัดก่อนตัด (0 = แสดงทั้งหมด) -->
<template>
	<div
		v-if="clean"
		class="ss-rich"
		:class="{ 'is-clamp': lines }"
		:style="lines ? { '--lines': lines } : null"
		v-html="clean"
	></div>
</template>

<script setup>
import { computed } from "vue";
import { sanitize_html } from "../api.js";

const props = defineProps({ html: String, lines: { type: Number, default: 0 } });
const clean = computed(() => sanitize_html(props.html));
</script>
