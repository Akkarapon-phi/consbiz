<template>
	<div class="ss-list">
		<div v-for="i in rows" :key="i" class="ss-card ss-skeleton" :style="{ '--i': i }">
			<div class="ss-sk ss-sk-avatar"></div>
			<div class="ss-sk-lines">
				<div class="ss-sk ss-sk-line" style="width: 62%"></div>
				<div class="ss-sk ss-sk-line" style="width: 88%"></div>
				<div class="ss-sk ss-sk-line" style="width: 40%"></div>
			</div>
		</div>
	</div>
</template>

<script setup>
defineProps({ rows: { type: Number, default: 4 } });
</script>
