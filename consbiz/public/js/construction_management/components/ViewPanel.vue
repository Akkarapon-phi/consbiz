<script setup>
// เนื้อหาแผง "มุมมอง" (อยู่ใน Popover ของปุ่มมุมมองใน Toolbar: ปิดเมื่อคลิกข้างนอกหรือ Esc) แบ่ง 2 Tab:
// ทั่วไป (การแสดงผล + บนแถบงาน) / Baseline (เปิดดู บันทึก ใช้เทียบ ลบ)
// S-Curve และคอลัมน์เป็นเมนูแยกบนแถบเครื่องมือ (CurvesMenu.vue, ColumnsMenu.vue) คำสั่งอื่นอยู่ในเมนูของหน้า (App.commands)
// settings เป็น reactive ของ App แก้ตรงได้ (App บันทึกลง User Settings เอง)
import { computed } from "vue";

const props = defineProps({
	settings: Object,
	canWrite: Boolean,
	tab: String,
	baselines: Array,
	viewedBaseline: String,
	activeBaseline: String,
	canDeleteBaseline: Boolean,
});
const emit = defineEmits([
	"update:tab",
	"view-baseline",
	"save-baseline",
	"activate-baseline",
	"delete-baseline",
]);

const TABS = [
	{ key: "general", label: __("ทั่วไป") },
	{ key: "baseline", label: __("Baseline") },
];
const viewed = computed(() => props.baselines.find((b) => b.name === props.viewedBaseline) || null);
const date = (value) => frappe.datetime.str_to_user(value);

const general = computed(() => [
	...(props.canWrite
		? [
				{
					key: "auto_save",
					label: __("บันทึกอัตโนมัติ"),
					title: __("บันทึกให้เองหลังหยุดแก้ไขครู่หนึ่ง"),
				},
		  ]
		: []),
	{
		key: "show_status",
		label: __("สีตามสถานะ"),
		title: __("เขียว = เสร็จแล้ว, ส้ม = ช้ากว่าแผนไม่เกิน 10%, แดง = ช้ากว่าแผนเกิน 10% (ณ วันที่เลือกดู)"),
	},
	{
		key: "show_critical",
		label: __("งานวิกฤต"),
		title: __("ขอบแดงที่งานบนสายงานวิกฤต (Float = 0) ถ้าเลื่อนจะทำให้โครงการเสร็จช้าลง"),
	},
	{
		key: "dim_curves",
		label: __("S-Curve จางเมื่อชี้งาน"),
		title: __("ชี้เมาส์ที่แถวงานแล้วเส้น S-Curve จางลง ไม่บังแถบงาน"),
	},
]);

const bars = [
	{ key: "show_baseline_bars", label: __("แถบ Baseline"), title: __("แถบบางใต้แถบงาน") },
	{ key: "show_split", label: __("% แผนที่แบ่ง"), title: __("แสดง % แผนที่กำหนดเองบนแถบงาน") },
	{
		key: "show_links",
		label: __("เส้นงานก่อนหน้า"),
		title: __("ลูกศรจากงานก่อนหน้าไปงานที่ตามมา (FS / SS / FF / SF)"),
	},
	{
		key: "show_prep",
		label: __("ช่วงเตรียมล่วงหน้า"),
		title: __("เส้นประหน้าแถบงาน จากวันต้องสั่งวัสดุ/จองคน-เครื่องจักรรายการแรกถึงวันเริ่มงาน (แดง = เลยกำหนด, ส้ม = ภายใน 14 วัน, เขียว = เตรียมครบ)"),
	},
	{ key: "show_labels", label: __("ชื่องาน"), title: __("WBS และชื่องานท้ายแถบ") },
	{ key: "show_progress", label: __("% แผน / จริง"), title: __("% แผนและ % จริง ณ วันที่เลือกดู ท้ายแถบ") },
];

const icon = (name, size = "sm") => frappe.utils.icon(name, size);
</script>

<template>
	<div class="cs-view-panel">
		<nav class="cs-view-tabs" role="tablist">
			<button
				v-for="item in TABS"
				:key="item.key"
				type="button"
				role="tab"
				:class="{ active: tab === item.key }"
				@click="emit('update:tab', item.key)"
			>
				{{ item.label }}
			</button>
		</nav>

		<div class="cs-view-body">
			<template v-if="tab === 'general'">
				<div class="cs-view-title">{{ __("การแสดงผล") }}</div>
				<label v-for="item in general" :key="item.key" class="switch-control cs-view-switch">
					<span class="switch-text">
						<span class="label-area">{{ item.label }}</span>
						<span class="cs-view-hint">{{ item.title }}</span>
					</span>
					<span class="input-area"><input v-model="settings[item.key]" type="checkbox" /></span>
					<span class="switch-visual"><span class="switch-thumb" /></span>
				</label>
				<div class="cs-view-title">{{ __("บนแถบงาน") }}</div>
				<label v-for="item in bars" :key="item.key" class="switch-control cs-view-switch">
					<span class="switch-text">
						<span class="label-area">{{ item.label }}</span>
						<span class="cs-view-hint">{{ item.title }}</span>
					</span>
					<span class="input-area"><input v-model="settings[item.key]" type="checkbox" /></span>
					<span class="switch-visual"><span class="switch-thumb" /></span>
				</label>
			</template>

			<template v-else-if="tab === 'baseline'">
				<div class="cs-view-title">{{ __("เปิดดู") }}</div>
				<button
					v-for="baseline in baselines"
					:key="baseline.name"
					type="button"
					class="cs-view-row"
					:class="{ active: baseline.name === viewedBaseline }"
					:title="baseline.reason || ''"
					@click="emit('view-baseline', baseline.name)"
				>
					<span class="cs-view-radio" />
					<span class="cs-view-row-main">
						{{ baseline.title }}
						<span class="cs-view-hint">{{ date(baseline.baseline_date) }}</span>
					</span>
					<span v-if="baseline.name === activeBaseline" class="indicator-pill blue">{{ __("ใช้เทียบ") }}</span>
				</button>
				<div v-if="!baselines.length" class="cs-view-hint">{{ __("ยังไม่มี Baseline") }}</div>
				<template v-if="canWrite">
					<div class="cs-view-title">{{ __("จัดการ") }}</div>
					<button type="button" class="cs-view-row" @click="emit('save-baseline')">
						<span v-html="icon('plus')" />{{ __("บันทึก Baseline ใหม่...") }}
					</button>
					<button
						type="button"
						class="cs-view-row"
						:disabled="!viewed || viewed.name === activeBaseline"
						@click="emit('activate-baseline')"
					>
						<span v-html="icon('check')" />{{ __("ใช้ชุดที่เปิดดูเทียบกับความคืบหน้าจริง") }}
					</button>
					<button
						v-if="canDeleteBaseline"
						type="button"
						class="cs-view-row text-danger"
						:disabled="!viewed || viewed.name === activeBaseline"
						:title="__('ชุดที่ใช้เทียบอยู่ลบไม่ได้ ให้เลือกชุดอื่นเป็นตัวเทียบก่อน')"
						@click="emit('delete-baseline')"
					>
						<span v-html="icon('trash-2')" />{{ __("ลบชุดที่เปิดดู") }}
					</button>
				</template>
			</template>
		</div>
	</div>
</template>

<style scoped>
.cs-view-panel {
	width: 340px;
	max-width: 100%;
	padding-top: 12px;
}
.cs-view-tabs {
	display: flex;
	gap: 2px;
	margin: 0 12px;
	padding: 3px;
	border-radius: var(--radius);
	background: var(--control-bg);
}
.cs-view-tabs button {
	flex: 1;
	height: 28px;
	padding: 0 4px;
	white-space: nowrap;
	border: none;
	border-radius: var(--radius-sm);
	background: transparent;
	color: var(--text-muted);
	font-size: var(--text-sm);
}
.cs-view-tabs button.active {
	background: var(--card-bg);
	color: var(--text-color);
	font-weight: 600;
	box-shadow: var(--shadow-sm);
}
/* สูงไม่เกินจอ แผงจึงเปิดใต้ปุ่มได้เสมอ (ไม่ทับปุ่ม) เนื้อหาเลื่อนในแผง */
.cs-view-body {
	max-height: min(60vh, 520px);
	overflow-y: auto;
	padding: 12px 16px 16px;
}
.cs-view-switch {
	width: 100%;
	align-items: flex-start;
	padding: 8px 0;
	border-bottom: 1px solid color-mix(in srgb, var(--border-color) 60%, transparent);
	gap: var(--padding-md);
}
.cs-view-switch .switch-text {
	display: flex;
	flex-direction: column;
	gap: 2px;
}
.cs-view-switch .label-area {
	display: flex;
	align-items: center;
	gap: 6px;
	font-size: var(--text-sm);
	font-weight: 500;
}
.cs-view-hint {
	color: var(--text-muted);
	font-size: var(--text-xs);
	line-height: 1.4;
}
.cs-view-title {
	margin: 16px 0 4px;
	color: var(--text-muted);
	font-size: var(--text-xs);
	font-weight: 700;
	letter-spacing: 0.04em;
	text-transform: uppercase;
}
.cs-view-title:first-child {
	margin-top: 0;
}
.cs-view-row {
	display: flex;
	align-items: center;
	gap: 10px;
	width: calc(100% + 20px);
	padding: 8px 10px;
	margin: 0 -10px;
	border: none;
	border-radius: var(--radius);
	background: transparent;
	color: var(--text-color);
	font-size: var(--text-sm);
	text-align: left;
}
.cs-view-row:hover:not(:disabled) {
	background: var(--fg-hover-color);
}
.cs-view-row:disabled {
	opacity: 0.45;
	cursor: default;
}
.cs-view-row :deep(svg) {
	flex: none;
	stroke: currentColor;
}
.cs-view-row-main {
	display: flex;
	flex: 1;
	flex-direction: column;
	min-width: 0;
}
.cs-view-radio {
	flex: none;
	width: 14px;
	height: 14px;
	border: 1.5px solid var(--gray-400);
	border-radius: 50%;
}
.cs-view-row.active .cs-view-radio {
	border: 4px solid var(--primary);
}

/* จอสัมผัส: แถวสูงขึ้นให้กดง่าย */
@media (pointer: coarse) {
	.cs-view-tabs button {
		height: 34px;
	}
	.cs-view-row {
		min-height: 40px;
	}
}
</style>
