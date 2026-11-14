<!-- แท็บสถานะของหัวรายการ (.ss-list-head แท็บเล็ต/จอใหญ่) หน้าตาเดียวกับแท็บของหน้าแก้แผนงาน (.pl-tabs) -->
<template>
	<div class="ss-list-tabs" role="tablist" aria-label="สถานะ">
		<button
			v-for="o in options"
			:key="o.value"
			type="button"
			role="tab"
			class="ss-list-tab"
			:class="{ 'is-active': o.value === modelValue }"
			:aria-selected="o.value === modelValue"
			@click="$emit('update:modelValue', o.value)"
		>
			{{ o.label }}
			<span v-if="o.count != null" class="ss-tab-count">{{ o.count }}</span>
			<span v-if="o.alert" class="ss-tab-dot" :title="o.alert === true ? '' : o.alert"></span>
		</button>
	</div>
</template>

<script setup>
defineProps({
	modelValue: String,
	options: { type: Array, required: true }, // [{value, label, count?, alert? (จุดแดง: true หรือข้อความ tooltip)}]
});
defineEmits(["update:modelValue"]);
</script>
