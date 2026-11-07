<!-- หน้าแรกของ ConsERP (/<base>/desktop, start_url ของ PWA): เลือกหมวดงานของทุกแอปที่มีสิทธิ์
     ไม่ต้องเลือกโครงการ (หมวดของหน้างานถามโครงการเมื่อเปิดหมวด) -->
<template>
	<div class="ss-desktop">
		<header class="ss-desktop-head">
			<img class="ss-desktop-logo" :src="LOGO" alt="" />
			<div class="ss-desktop-hello">
				<div class="ss-desktop-greet">{{ greeting }}</div>
				<div class="ss-desktop-name">{{ boot.full_name }}</div>
			</div>
		</header>
		<div class="ss-content">
			<ModuleGrid @choose="switch_section" />
		</div>
	</div>
</template>

<script setup>
import ModuleGrid from "./ModuleGrid.vue";
import { boot, switch_section } from "../api.js";

const LOGO = "/assets/consbiz/site_app/conserp-round-192.png";

const h = new Date().getHours();
const greeting = h < 11 ? "อรุณสวัสดิ์" : h < 16 ? "สวัสดีตอนบ่าย" : "สวัสดีตอนเย็น";
</script>
