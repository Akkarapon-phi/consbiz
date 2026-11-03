<script setup>
// แถบบางของ Gantt ใน Tab ของฟอร์ม (ดูอย่างเดียว): มุมมอง (แผนงาน/ทรัพยากร) | มาตราส่วน/ซูม | วันที่เลือกดู | % ... ปุ่มแก้ไขแผนงาน (ไปหน้าเต็มจอ)
// แก้ไขแผน Undo บันทึก คอลัมน์ Baseline ฯลฯ อยู่ในหน้าเต็มจอ (Toolbar.vue) ที่เดียว
// แถวเดียว จอแคบ (<= 640px ของแถบ) ขึ้นแถวที่ 2 ให้ %
import FrappeControl from "./FrappeControl.vue";
import Readout from "./Readout.vue";
import ScaleSwitch from "./ScaleSwitch.vue";
import ViewSwitch from "./ViewSwitch.vue";

defineProps({
	scales: Object,
	settings: Object,
	curves: Array,
	statusDate: String,
	readout: Object,
	canWrite: Boolean, // มีสิทธิ์แก้แผน: ปุ่มเป็น "แก้ไขแผนงาน" ไม่งั้น "เปิดเต็มจอ"
});
defineEmits(["today", "zoom", "open-full", "update:statusDate"]);

const icon = (name) => frappe.utils.icon(name, "sm");
</script>

<template>
	<div class="cs-viewbar">
		<div class="cs-vb-row">
			<ViewSwitch :settings="settings" />
			<ScaleSwitch :scales="scales" :settings="settings" @zoom="(action) => $emit('zoom', action)" />
			<div class="cs-vb-date" :title="__('ค่า % และสถานะงานคิด ณ วันที่นี้')">
				<FrappeControl
					:df="{ fieldtype: 'Date' }"
					:model-value="statusDate"
					@update:model-value="(v) => v && $emit('update:statusDate', v)"
				/>
				<button
					type="button"
					class="btn btn-default btn-sm cs-tb-btn"
					:title="__('ดูค่า ณ วันนี้ และเลื่อนไปที่วันนี้')"
					:aria-label="__('วันนี้')"
					@click="$emit('today')"
					v-html="icon('calendar-check')"
				/>
			</div>
			<div class="cs-vb-readout">
				<Readout :curves="curves" :readout="readout" />
			</div>
			<button
				type="button"
				class="btn btn-default btn-sm cs-tb-btn cs-vb-edit"
				:title="canWrite ? __('แก้ไขแผนงานในหน้าเต็มจอ') : __('เปิด Gantt เต็มจอ')"
				@click="$emit('open-full')"
			>
				<span v-html="icon(canWrite ? 'pencil' : 'maximize-2')" />
				<span class="cs-vb-edit-text">{{ canWrite ? __("แก้ไขแผนงาน") : __("เปิดเต็มจอ") }}</span>
			</button>
		</div>
	</div>
</template>

<style scoped>
.cs-viewbar {
	container-type: inline-size;
	width: 100%;
	padding: 8px 0;
}
.cs-vb-row {
	display: flex;
	flex-wrap: wrap;
	align-items: center;
	gap: 8px 12px;
}
.cs-vb-date {
	display: flex;
	align-items: center;
	gap: 4px;
}
.cs-vb-date :deep(.cs-control) {
	width: 112px;
}
.cs-vb-date :deep(.form-control) {
	height: 30px;
}
.cs-vb-edit {
	margin-left: auto;
}
@media (pointer: coarse) {
	.cs-vb-date :deep(.form-control) {
		height: 36px;
	}
}
@container (max-width: 640px) {
	.cs-vb-row {
		gap: 8px;
	}
	.cs-vb-date :deep(.cs-control) {
		width: 104px;
	}
	.cs-vb-edit-text {
		display: none;
	}
	.cs-vb-readout {
		order: 1;
		flex: 1 0 100%;
	}
}
</style>
