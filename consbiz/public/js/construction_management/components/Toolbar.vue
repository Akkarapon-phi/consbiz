<script setup>
// แถบเครื่องมือ 2 แถว
// 1. มาตราส่วนเวลา, ซูม, วันนี้, ระดับ WBS, คอลัมน์, วันที่เลือกดู
// 2. เปิด/ปิดเส้น S-Curve ทีละเส้น (เป็น legend ไปในตัว), สิ่งที่แสดงบนแถบงาน, ตารางสรุป และค่า % ณ วันที่เลือก
// settings เป็น reactive ของ App แก้ตรงได้ (App บันทึกลง User Settings เอง)
import { computed } from "vue";
import FrappeControl from "./FrappeControl.vue";

const props = defineProps({
	scales: Object,
	settings: Object,
	curves: Array,
	wbsDepth: Number,
	statusDate: String,
	readout: Object,
	finishDate: String,
	contractFinish: String,
	totalAmount: Number,
});
defineEmits(["choose-columns", "wbs-level", "today", "zoom", "update:statusDate"]);

// ปุ่มเปิด/ปิดสิ่งที่แสดงบนแถบงานและใต้ตาราง (key ใน settings)
const toggles = [
	{ key: "show_baseline_bars", label: __("แถบ Baseline") },
	{ key: "show_split", label: __("% ที่แบ่ง"), title: __("แสดง % แผนที่กำหนดเองบนแถบงาน") },
	{ key: "show_labels", label: __("ชื่องาน"), title: __("แสดง WBS และชื่องานท้ายแถบ") },
	{
		key: "show_progress",
		label: __("% แผน/จริง"),
		title: __("แสดง % แผนและ % จริง ณ วันที่เลือกดู ท้ายแถบ"),
	},
	{
		key: "show_status",
		label: __("สี Status"),
		title: __(
			"สีแถบงานตามสถานะ ณ วันที่เลือกดู: เขียว = เสร็จแล้ว, ส้ม = ช้ากว่าแผนไม่เกิน 10%, แดง = ช้ากว่าแผนเกิน 10%"
		),
	},
	{ key: "show_summary", label: __("ตารางสรุป") },
];

// ระดับ WBS: ระดับ 1 = หัวข้อหลัก (1), ระดับ 2 = 1.1, ...
const levels = computed(() =>
	Array.from({ length: Math.max(props.wbsDepth, 0) }, (_, i) => ({
		level: i + 1,
		example: Array.from({ length: i + 1 }, () => "1").join("."),
	}))
);

// เทียบ % จริงกับแผน ณ วันที่เลือก (ต่างกันไม่ถึง 0.005% ถือว่าตามแผน)
const variance = computed(() => {
	const { plan, actual } = props.readout;
	if (plan === null || actual === null) return null;
	const diff = actual - plan;
	if (Math.abs(diff) < 0.005) return { text: __("ตามแผน"), class: "text-muted" };
	return diff > 0
		? { text: __("เร็วกว่าแผน {0}", [percent(diff)]), class: "text-success" }
		: { text: __("ช้ากว่าแผน {0}", [percent(-diff)]), class: "text-danger" };
});

// แผนงานเสร็จหลังวันสิ้นสุดสัญญา
const late = computed(
	() => props.finishDate && props.contractFinish && props.finishDate > props.contractFinish
);

const amount = (value) => format_number(value || 0, null, 2);
const percent = (value) =>
	value === null || value === undefined ? "-" : format_number(value, null, 2) + "%";
</script>

<template>
	<div class="cs-toolbar">
		<div class="cs-toolbar-row">
			<div class="btn-group" role="group">
				<button
					v-for="(scale, key) in scales"
					:key="key"
					type="button"
					class="btn btn-default btn-sm"
					:class="{ active: settings.scale === key }"
					@click="settings.scale = key"
				>
					{{ scale.label }}
				</button>
			</div>
			<div class="btn-group" role="group">
				<button
					type="button"
					class="btn btn-default btn-sm"
					:title="__('ย่อ timeline')"
					@click="$emit('zoom', 'out')"
				>
					−
				</button>
				<button
					type="button"
					class="btn btn-default btn-sm"
					:title="__('ขยาย timeline')"
					@click="$emit('zoom', 'in')"
				>
					+
				</button>
				<button
					type="button"
					class="btn btn-default btn-sm"
					:title="__('ย่อให้เห็นทั้งโครงการในหน้าจอ')"
					@click="$emit('zoom', 'fit')"
				>
					{{ __("พอดีจอ") }}
				</button>
			</div>
			<button type="button" class="btn btn-default btn-sm" @click="$emit('today')">
				{{ __("วันนี้") }}
			</button>
			<div class="dropdown">
				<button
					type="button"
					class="btn btn-default btn-sm dropdown-toggle"
					data-toggle="dropdown"
					aria-haspopup="true"
					aria-expanded="false"
				>
					{{ __("แสดง WBS") }}
				</button>
				<div class="dropdown-menu">
					<a
						v-for="item in levels"
						:key="item.level"
						class="dropdown-item"
						href="#"
						@click.prevent="$emit('wbs-level', item.level)"
					>
						{{ __("ถึงระดับ {0} (เช่น {1})", [item.level, item.example]) }}
					</a>
					<div class="dropdown-divider" />
					<a class="dropdown-item" href="#" @click.prevent="$emit('wbs-level', null)">
						{{ __("ขยายทั้งหมด") }}
					</a>
				</div>
			</div>
			<button type="button" class="btn btn-default btn-sm" @click="$emit('choose-columns')">
				{{ __("คอลัมน์") }}
			</button>

			<div class="cs-status-date">
				<span class="text-muted">{{ __("ดู ณ วันที่") }}</span>
				<FrappeControl
					:df="{ fieldtype: 'Date' }"
					:model-value="statusDate"
					@update:model-value="(v) => v && $emit('update:statusDate', v)"
				/>
			</div>
		</div>

		<div class="cs-toolbar-row">
			<span class="text-muted cs-label">{{ __("S-Curve") }}</span>
			<button
				v-for="curve in curves"
				:key="curve.key"
				type="button"
				class="btn btn-default btn-xs cs-chip"
				:class="{ active: settings.curves[curve.key] }"
				@click="settings.curves[curve.key] = !settings.curves[curve.key]"
			>
				<span class="cs-dot" :style="{ background: curve.color }" />
				{{ curve.label }}
			</button>
			<span class="cs-separator" />
			<span class="text-muted cs-label">{{ __("แสดง") }}</span>
			<button
				v-for="toggle in toggles"
				:key="toggle.key"
				type="button"
				class="btn btn-default btn-xs cs-chip"
				:class="{ active: settings[toggle.key] }"
				:title="toggle.title"
				@click="settings[toggle.key] = !settings[toggle.key]"
			>
				{{ toggle.label }}
			</button>

			<div class="cs-readout">
				<span v-for="curve in curves" :key="curve.key">
					<span class="cs-dot" :style="{ background: curve.color }" />
					{{ curve.label }} <b>{{ percent(readout[curve.key]) }}</b>
				</span>
				<span v-if="variance !== null" :class="variance.class">{{ variance.text }}</span>
				<span
					v-if="finishDate"
					:class="late ? 'text-danger' : 'text-muted'"
					:title="late ? __('แผนงานเสร็จหลังวันสิ้นสุดสัญญา') : ''"
				>
					{{ __("แผนเสร็จ") }} <b>{{ frappe.datetime.str_to_user(finishDate) }}</b>
				</span>
				<span class="text-muted" v-if="contractFinish">
					{{ __("สิ้นสุดสัญญา") }}
					<b>{{ frappe.datetime.str_to_user(contractFinish) }}</b>
				</span>
				<span class="text-muted">
					{{ __("มูลค่ารวม") }} <b>{{ amount(totalAmount) }}</b>
				</span>
			</div>
		</div>
	</div>
</template>

<style scoped>
.cs-toolbar {
	margin-bottom: var(--padding-sm);
}
.cs-toolbar-row {
	display: flex;
	flex-wrap: wrap;
	align-items: center;
	gap: var(--padding-xs) var(--padding-sm);
	margin-bottom: var(--padding-xs);
}
.cs-status-date {
	display: flex;
	align-items: center;
	gap: var(--padding-xs);
	margin-left: auto;
	font-size: var(--text-sm);
}
.cs-status-date :deep(.cs-control) {
	width: 130px;
}
.cs-label {
	font-size: var(--text-sm);
}
.cs-chip {
	display: inline-flex;
	align-items: center;
	gap: 6px;
}
.cs-chip:not(.active) {
	opacity: 0.55;
}
.cs-separator {
	width: 1px;
	height: 18px;
	background: var(--border-color);
}
.cs-dot {
	display: inline-block;
	width: 8px;
	height: 8px;
	border-radius: 50%;
}
.cs-readout {
	display: flex;
	flex-wrap: wrap;
	align-items: center;
	gap: var(--padding-xs) var(--padding-md);
	margin-left: auto;
	font-size: var(--text-sm);
}
</style>
