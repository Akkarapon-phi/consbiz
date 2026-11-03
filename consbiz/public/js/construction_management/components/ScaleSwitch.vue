<script setup>
// มาตราส่วนเวลา (วัน/สัปดาห์/เดือน/ปี) + ซูม ใช้ใน Toolbar และ ViewBar
// พื้นที่แคบ (<= 640px ของแถบ): มาตราส่วนเป็นเมนู (frappe.ui.Dropdown) ซูมเหลือปุ่มพอดีจอ
import { computed } from "vue";
import EsDropdown from "./EsDropdown.vue";

const props = defineProps({
	scales: Object, // SCALES ของ App { key: { label, short } }
	settings: Object, // reactive ของ App แก้ settings.scale ตรงได้
});
defineEmits(["zoom"]);

const scale_options = computed(() =>
	Object.entries(props.scales).map(([key, scale]) => ({
		label: scale.label,
		selected: props.settings.scale === key,
		onclick: () => (props.settings.scale = key),
	}))
);

const icon = (name) => frappe.utils.icon(name, "sm");
</script>

<template>
	<div class="cs-scale">
		<div class="cs-segment cs-scale-seg" role="group" :aria-label="__('มาตราส่วนเวลา')">
			<button
				v-for="(scale, key) in scales"
				:key="key"
				type="button"
				class="cs-seg-btn cs-seg-text"
				:class="{ active: settings.scale === key }"
				:aria-pressed="settings.scale === key"
				:title="scale.label"
				@click="settings.scale = key"
			>
				{{ scale.short }}
			</button>
		</div>
		<EsDropdown class="cs-scale-menu" :options="scale_options">
			<template #trigger>
				<button type="button" class="btn btn-default btn-sm cs-tb-btn" :title="__('มาตราส่วนเวลา')">
					{{ scales[settings.scale]?.label }}
					<span class="cs-caret" v-html="icon('chevron-down')" />
				</button>
			</template>
		</EsDropdown>
		<div class="cs-segment">
			<button
				type="button"
				class="cs-seg-btn cs-zoom-step"
				:title="__('ย่อ timeline')"
				:aria-label="__('ย่อ timeline')"
				@click="$emit('zoom', 'out')"
				v-html="icon('minus')"
			/>
			<button
				type="button"
				class="cs-seg-btn cs-zoom-step"
				:title="__('ขยาย timeline')"
				:aria-label="__('ขยาย timeline')"
				@click="$emit('zoom', 'in')"
				v-html="icon('plus')"
			/>
			<button
				type="button"
				class="cs-seg-btn"
				:title="__('ย่อให้เห็นทั้งโครงการในหน้าจอ')"
				:aria-label="__('ย่อให้เห็นทั้งโครงการ')"
				@click="$emit('zoom', 'fit')"
				v-html="icon('move-horizontal')"
			/>
		</div>
	</div>
</template>

<style scoped>
.cs-scale {
	display: flex;
	align-items: center;
	gap: 4px;
}
.cs-seg-text {
	padding: 0 10px;
}
.cs-scale-menu {
	display: none;
}
@container (max-width: 640px) {
	.cs-scale-seg,
	.cs-zoom-step {
		display: none;
	}
	.cs-scale-menu {
		display: inline-flex;
	}
}
</style>
