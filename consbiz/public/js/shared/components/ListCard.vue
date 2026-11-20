<!-- การ์ดเนื้อหาต่อจากหัวรายการ (ตกลง 2026-11-18): ListHead + ListCard ติดกันเป็นการ์ดเดียว สูงถึงล่างจอ (แบบ DocList)
     ใส่ Skeleton / Empty (อยู่กลางการ์ด) / DataTable / ตารางของหน้า (.ss-list-scroll = เลื่อนในการ์ด) / .ss-list-foot (ท้ายการ์ด)
     ต้องวางถัดจาก ListHead ทันที (ป้ายเตือน/ตัวเลขสรุปวางเหนือ ListHead) on = false (มือถือ) = แสดงเนื้อหาตรง ไม่มีการ์ด
     slot side = ช่องขวาของการ์ด (แผงตัวอย่าง .ss-preview) -->
<template>
	<div v-if="on" class="ss-list-card">
		<div class="ss-list-main"><slot /></div>
		<slot name="side" />
	</div>
	<slot v-else />
</template>

<script setup>
defineProps({ on: { type: Boolean, default: true } });
</script>
