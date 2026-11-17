<!-- หน้าแรกของ ConsERP (/<base>/desktop, start_url ของ PWA): เลือกหมวดงานของทุกแอปที่มีสิทธิ์
     ไม่ต้องเลือกโครงการ (หมวดของหน้างานถามโครงการเมื่อเปิดหมวด)
     แถบบนแบบเดียวกับทุกหมวด (โลโก้ ConsERP / ค้นหาทั้งระบบ / แจ้งเตือน / ผู้ใช้) คำทักทายเป็นหัวเนื้อหา -->
<template>
	<div class="ss-desktop">
		<TopBar title="หน้าแรก" no_project />
		<div class="ss-content">
			<header class="ss-desktop-head">
				<div class="ss-desktop-hello">
					<div class="ss-desktop-greet">{{ greeting }}</div>
					<div class="ss-desktop-name">{{ boot.full_name }}</div>
				</div>
			</header>
			<ModuleGrid @choose="switch_section" />
		</div>
	</div>
</template>

<script setup>
import ModuleGrid from "./ModuleGrid.vue";
import TopBar from "./TopBar.vue";
import { boot, switch_section } from "../api.js";

const h = new Date().getHours();
const greeting = h < 11 ? "อรุณสวัสดิ์" : h < 16 ? "สวัสดีตอนบ่าย" : "สวัสดีตอนเย็น";
</script>
