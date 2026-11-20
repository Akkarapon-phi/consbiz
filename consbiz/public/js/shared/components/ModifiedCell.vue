<template>
	<td class="col-modified">
		<span class="ss-row-modified" :title="modified_title(value)">{{ short_ago(value) }}</span>
		<RowSocial v-if="row" :row="row" />
	</td>
</template>

<script setup>
import { modified_title, short_ago } from "../api.js";
import RowSocial from "./RowSocial.vue";

defineProps({ value: String, row: Object });
</script>

<style scoped>
.ss-row-modified { margin-inline-end: 4px; vertical-align: middle; }
.col-modified :deep(.ss-row-social) { vertical-align: middle; }
</style>
