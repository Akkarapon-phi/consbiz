<!-- หน้า "แผนงาน" = หน้าแก้แผนแบบดูอย่างเดียว ใช้หน้าจอชุดเดียวกัน (PlanEdit.vue) -->
<template>
	<PlanEdit readonly :params="params" />
</template>

<script setup>
import PlanEdit from "./PlanEdit.vue";

defineProps({ params: { type: Object, default: () => ({}) } });
</script>
