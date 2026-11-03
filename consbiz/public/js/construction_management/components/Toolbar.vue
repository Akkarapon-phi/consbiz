<script setup>
// แถบเครื่องมือของหน้า Gantt เต็มจอ (แก้ไขแผน) แบ่งเป็นกลุ่ม (ห่างกันและมีเส้นแบ่ง):
// ประวัติ (Undo/Redo) | มุมมอง (แผนงาน/ทรัพยากร) + โครงสร้าง (WBS, คอลัมน์ เฉพาะมุมมองแผนงาน) | วันที่เลือกดู + วันนี้ | % ณ วันที่เลือกดู
// มาตราส่วนเวลา + ซูม | S-Curve, มุมมอง (slot view: เนื้อหาแผงมาจาก App)
// เมนูธรรมดาใช้ frappe.ui.Dropdown แผงที่มีสวิตช์/ลากเรียงใช้ frappe.ui.Popover (ผ่าน EsDropdown/EsPopover)
// จึงเปิด-ปิด animation และปิดเมื่อคลิกข้างนอกเหมือนเมนูอื่นของระบบ
// ปรับตามความกว้างของตัวเอง (container query):
//   > 1500px: แถวเดียว / <= 1500px: 2 แถว (แถว 2 = % ... มาตราส่วน, การแสดงผล)
//   <= 1100px: ปุ่มเมนูเหลือไอคอน / <= 640px (มือถือ): 3 แถว มาตราส่วนเป็นเมนู
// settings เป็น reactive ของ App แก้ตรงได้ (App บันทึกลง User Settings เอง)
import { computed } from "vue";
import ColumnsMenu from "./ColumnsMenu.vue";
import CurvesMenu from "./CurvesMenu.vue";
import EsDropdown from "./EsDropdown.vue";
import EsPopover from "./EsPopover.vue";
import FrappeControl from "./FrappeControl.vue";
import Readout from "./Readout.vue";
import ScaleSwitch from "./ScaleSwitch.vue";
import ViewSwitch from "./ViewSwitch.vue";

const props = defineProps({
	scales: Object,
	settings: Object,
	curves: Array,
	summaryOptions: Array,
	columns: Array, // COLUMNS ทั้งหมด (เมนูคอลัมน์)
	wbsDepth: Number,
	statusDate: String,
	readout: Object,
	canWrite: Boolean,
	canUndo: Boolean,
	canRedo: Boolean,
});
const emit = defineEmits(["fit-columns", "wbs-level", "today", "zoom", "undo", "redo", "update:statusDate"]);

// ระดับ WBS: ระดับ 1 = หัวข้อหลัก (1), ระดับ 2 = 1.1, ...
const wbs_options = computed(() => [
	{
		group: "",
		hide_label: true,
		options: Array.from({ length: Math.max(props.wbsDepth, 0) }, (_, i) => ({
			label: __("ถึงระดับ {0} (เช่น {1})", [i + 1, Array.from({ length: i + 1 }, () => "1").join(".")]),
			onclick: () => emit("wbs-level", i + 1),
		})),
	},
	{ group: "", hide_label: true, options: [{ label: __("ขยายทั้งหมด"), onclick: () => emit("wbs-level", null) }] },
]);

const icon = (name) => frappe.utils.icon(name, "sm");
</script>

<template>
	<div class="cs-toolbar">
		<div class="cs-bar">
			<!-- ประวัติ -->
			<div v-if="canWrite" class="cs-group cs-g-history">
				<div class="cs-segment">
					<button
						type="button"
						class="cs-seg-btn"
						:title="__('ย้อนกลับ (Ctrl+Z)')"
						:aria-label="__('ย้อนกลับ')"
						:disabled="!canUndo"
						@click="$emit('undo')"
						v-html="icon('undo-2')"
					/>
					<button
						type="button"
						class="cs-seg-btn"
						:title="__('ทำซ้ำ (Ctrl+Y)')"
						:aria-label="__('ทำซ้ำ')"
						:disabled="!canRedo"
						@click="$emit('redo')"
						v-html="icon('redo-2')"
					/>
				</div>
			</div>

			<!-- โครงสร้างตาราง -->
			<div class="cs-group cs-g-structure">
				<ViewSwitch :settings="settings" />
				<template v-if="settings.view !== 'resources'">
				<EsDropdown :options="wbs_options">
					<template #trigger>
						<button type="button" class="btn btn-default btn-sm cs-tb-btn" :title="__('ระดับ WBS')">
							<span v-html="icon('list-tree')" />
							<span class="cs-text-lg">WBS</span>
							<span class="cs-caret" v-html="icon('chevron-down')" />
						</button>
					</template>
				</EsDropdown>
				<EsPopover>
					<template #trigger="{ open }">
						<button
							type="button"
							class="btn btn-default btn-sm cs-tb-btn"
							:class="{ 'cs-pressed': open }"
							:title="__('คอลัมน์')"
						>
							<span v-html="icon('columns-3')" />
							<span class="cs-text-lg">{{ __("คอลัมน์") }}</span>
							<span class="cs-caret" v-html="icon('chevron-down')" />
						</button>
					</template>
					<ColumnsMenu :settings="settings" :columns="columns" @fit-columns="$emit('fit-columns')" />
				</EsPopover>
				</template>
			</div>

			<!-- วันที่เลือกดู: วันนี้ = ดูค่า ณ วันนี้และเลื่อนไปที่วันนี้ -->
			<div class="cs-group cs-g-date" :title="__('ค่า % และสถานะงานคิด ณ วันที่นี้')">
				<span class="cs-date-label">{{ __("ณ วันที่") }}</span>
				<FrappeControl
					:df="{ fieldtype: 'Date' }"
					:model-value="statusDate"
					@update:model-value="(v) => v && $emit('update:statusDate', v)"
				/>
				<button
					type="button"
					class="btn btn-default btn-sm cs-tb-btn"
					:title="__('ดูค่า ณ วันนี้ และเลื่อนไปที่วันนี้')"
					@click="$emit('today')"
				>
					<span class="cs-icon-sm" v-html="icon('calendar-check')" />
					<span class="cs-text-md">{{ __("วันนี้") }}</span>
				</button>
			</div>

			<!-- % ณ วันที่เลือกดู (วันที่สัญญา มูลค่า วันเสร็จที่คาด อยู่ใน Tab ภาพรวม) -->
			<div class="cs-group cs-g-readout">
				<Readout :curves="curves" :readout="readout" />
			</div>

			<span class="cs-spacer" />

			<!-- มาตราส่วนเวลาและซูม -->
			<div class="cs-group cs-g-scale">
				<ScaleSwitch :scales="scales" :settings="settings" @zoom="(action) => $emit('zoom', action)" />
			</div>

			<!-- การแสดงผล -->
			<div class="cs-group cs-g-view">
				<EsPopover v-if="settings.view !== 'resources'" align="end">
					<template #trigger="{ open }">
						<button
							type="button"
							class="btn btn-default btn-sm cs-tb-btn"
							:class="{ 'cs-pressed': open }"
							:title="__('S-Curve และตารางสรุป')"
						>
							<span v-html="icon('chart-spline')" />
							<span class="cs-text-lg">S-Curve</span>
							<span class="cs-caret" v-html="icon('chevron-down')" />
						</button>
					</template>
					<CurvesMenu :settings="settings" :curves="curves" :summary-options="summaryOptions" />
				</EsPopover>
				<EsPopover align="end">
					<template #trigger="{ open }">
						<button
							type="button"
							class="btn btn-default btn-sm cs-tb-btn"
							:class="{ 'cs-pressed': open }"
							:title="__('มุมมอง: การแสดงผลและ Baseline')"
						>
							<span v-html="icon('sliders-horizontal')" />
							<span class="cs-text-lg">{{ __("มุมมอง") }}</span>
							<span class="cs-caret" v-html="icon('chevron-down')" />
						</button>
					</template>
					<slot name="view" />
				</EsPopover>
			</div>
		</div>
	</div>
</template>

<style scoped>
/* วัดความกว้างของตัวเอง (container query) แล้วจัดแถว/ซ่อนข้อความตามพื้นที่
   containment ทำให้กว้าง 0 ถ้าพ่อเป็น flex ที่หดตามเนื้อหา จึงกำหนดเต็มความกว้างไว้ */
.cs-toolbar {
	container-type: inline-size;
	width: 100%;
	padding-top: 10px;
	margin-bottom: 8px;
}
.cs-bar {
	display: flex;
	flex-wrap: wrap;
	align-items: center;
	gap: 8px 0;
}
.cs-group {
	display: flex;
	flex: none;
	align-items: center;
	gap: 4px;
	padding: 0 10px;
}
.cs-group:first-child {
	padding-left: 0;
}
.cs-group:last-child {
	padding-right: 0;
}
/* เส้นแบ่งกลุ่ม (เฉพาะแบบแถวเดียว) */
.cs-group + .cs-group {
	border-left: 1px solid var(--border-color);
}
.cs-spacer {
	flex: 1 1 0;
}

/* วันที่เลือกดู */
.cs-g-date {
	font-size: var(--text-sm);
	color: var(--text-muted);
}
.cs-date-label {
	white-space: nowrap;
}
.cs-g-date :deep(.cs-control) {
	width: 112px;
}
.cs-g-date :deep(.form-control) {
	height: 30px;
}
.cs-icon-sm {
	display: none;
}
@media (pointer: coarse) {
	.cs-g-date :deep(.form-control) {
		height: 36px;
	}
}

/* 2 แถว: แถว 1 = ประวัติ, โครงสร้าง, วันที่ / แถว 2 = % ... มาตราส่วน, การแสดงผล */
@container (max-width: 1500px) {
	.cs-group + .cs-group {
		border-left: 0;
	}
	.cs-group {
		padding: 0 6px;
	}
	.cs-g-history {
		padding-left: 0;
	}
	.cs-spacer {
		order: 1;
		flex: 0 0 100%;
		height: 0;
	}
	.cs-g-readout,
	.cs-g-scale,
	.cs-g-view {
		order: 2;
	}
	.cs-g-readout {
		padding-left: 0;
	}
	.cs-g-scale {
		margin-left: auto;
	}
}
@container (max-width: 1100px) {
	.cs-text-lg {
		display: none;
	}
}

/* มือถือ: 3 แถว ไอคอนอย่างเดียว
   แถว 1 = ประวัติ, วันที่ / แถว 2 = โครงสร้าง, มาตราส่วน, การแสดงผล / แถว 3 = % */
@container (max-width: 640px) {
	.cs-group {
		padding: 0 3px;
	}
	.cs-g-history,
	.cs-g-date {
		order: 0;
	}
	.cs-g-structure {
		order: 2;
		padding-left: 0;
	}
	.cs-g-scale {
		order: 2;
		margin-left: 0;
	}
	.cs-g-view {
		order: 2;
		margin-left: auto;
	}
	.cs-g-readout {
		order: 3;
		flex: 1 0 100%;
		padding: 0;
	}
	.cs-date-label,
	.cs-text-md {
		display: none;
	}
	.cs-icon-sm {
		display: inline-flex;
	}
	.cs-g-date :deep(.cs-control) {
		width: 104px;
	}
}
</style>
