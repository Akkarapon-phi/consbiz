<template>
	<span class="tax-totals">
		<span
			>รวม <b>{{ rows.length }}</b> รายการ</span
		>
		<span
			>ฐานภาษี <b>{{ money(totals.base) }}</b></span
		>
		<span
			>ภาษี <b>{{ money(totals.amount) }}</b></span
		>
	</span>
</template>

<script setup>
import { computed } from "vue";
import { money } from "../../../shared/api.js";

const props = defineProps({ rows: { type: Array, required: true } });
const totals = computed(() => {
	let base = 0;
	let amount = 0;
	for (const row of props.rows) {
		base += Number(row.tax_base) || 0;
		amount += Number(row.amount) || 0;
	}
	return { base, amount };
});
</script>

<style scoped>
.tax-totals {
	display: inline-flex;
	align-items: baseline;
	flex-wrap: wrap;
	gap: 4px 16px;
}
</style>
