<!-- URL เดิมของตั้งค่า HR (/conserp/hr/hr-setup/<module>): ตั้งค่าอยู่ในหน้าต่างตั้งค่าของหมวด (เมนู ⋯ ของหัวรายการ, ตกลง 2026-11-18)
     เปิดหน้าต่างนั้นที่หัวข้อของกลุ่ม แล้วพาไปหน้าแรกของหมวดบุคคล (ลิงก์จากการแจ้งเตือน/บุ๊กมาร์กเดิมยังใช้ได้) -->
<template>
	<div></div>
</template>

<script setup>
import { inject, onMounted } from "vue";
import { go, state } from "../../../shared/api.js";

const settings = inject("module_settings", null);
const MODULES = ["time", "pay", "expense", "people"];
onMounted(() => {
	const module = MODULES.includes(state.route.params.module) ? state.route.params.module : "time";
	go("hr-attendance", {}, { replace: true });
	settings?.open(`hr-${module}`);
});
</script>
