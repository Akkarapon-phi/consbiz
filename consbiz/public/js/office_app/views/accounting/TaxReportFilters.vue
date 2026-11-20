<template>
	<div class="report-filters">
		<span class="acc-month">
			<button
				type="button"
				class="ss-icon-btn"
				aria-label="เดือนก่อน"
				@click="$emit('shift', -1)"
			>
				<Icon name="chevron-left" :size="17" />
			</button>
			<DateInput
				:model-value="month"
				@update:model-value="$emit('update:month', $event)"
				picker="month"
				variant="tool"
				label="เลือกเดือน"
			/>
			<button
				type="button"
				class="ss-icon-btn"
				aria-label="เดือนถัดไป"
				@click="$emit('shift', 1)"
			>
				<Icon name="chevron-right" :size="17" />
			</button>
		</span>
		<SelectBox
			v-if="addresses.length > 1"
			:model-value="address"
			@update:model-value="$emit('update:address', $event)"
			:options="addresses"
			label="ที่อยู่บริษัท (สาขา)"
			variant="tool"
		/>
	</div>
</template>

<script setup>
import Icon from "../../../shared/components/Icon.vue";
import DateInput from "../../../shared/components/DateInput.vue";
import SelectBox from "../../../shared/components/SelectBox.vue";

defineProps({
	month: String,
	address: String,
	addresses: Array,
});
defineEmits(["shift", "update:month", "update:address"]);
</script>

<style scoped>
.report-filters,
.acc-month {
	display: flex;
	align-items: center;
	gap: 4px;
}
.report-filters {
	flex-wrap: wrap;
}
.report-filters :deep(.ss-select) {
	max-width: 100%;
}
</style>
