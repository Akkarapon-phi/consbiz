<script setup>
// แถบเครื่องมือ 2 แถว
// 1. แถบคำสั่ง: Undo/Redo + สวิตช์บันทึกอัตโนมัติ | มาตราส่วนเวลา | ซูม | วันที่เลือกดู + วันนี้
//    ขวา: เมนู Baseline / WBS / แสดงผล / ตารางสรุป / คอลัมน์
//    Baseline: เลือกชุดที่เปิดดูได้ทีละชุด คำสั่งบันทึก/ใช้เทียบ/ลบ แยกไว้ใต้รายการ (ทำงานกับชุดที่เปิดดูอยู่)
// 2. ตัวเลข ณ วันที่เลือกดู: % Baseline / แผน / จริง, เร็ว-ช้ากว่า Baseline (ไม่มี Baseline ใช้แผน)
//    ขวา: วันเริ่ม-สิ้นสุดสัญญา, ระยะเวลาสัญญา, วันที่แผนเสร็จ, มูลค่าสัญญา
// settings เป็น reactive ของ App แก้ตรงได้ (App บันทึกลง User Settings เอง)
// สวิตช์ใช้ class switch-control ของ Frappe, เมนูเป็น dropdown ของ Bootstrap (คลิกในเมนูไม่ปิดเมนู)
import { computed } from "vue";
import FrappeControl from "./FrappeControl.vue";

const props = defineProps({
	scales: Object,
	settings: Object,
	curves: Array,
	summaryOptions: Array,
	wbsDepth: Number,
	statusDate: String,
	readout: Object,
	finishDate: String,
	contractStart: String,
	contractFinish: String,
	contractDuration: Number,
	totalAmount: Number,
	contractAmount: Number,
	canWrite: Boolean,
	canUndo: Boolean,
	canRedo: Boolean,
	baselines: Array,
	viewedBaseline: String,
	activeBaseline: String,
	canDeleteBaseline: Boolean,
});
defineEmits([
	"choose-columns",
	"wbs-level",
	"today",
	"zoom",
	"undo",
	"redo",
	"update:statusDate",
	"view-baseline",
	"save-baseline",
	"activate-baseline",
	"delete-baseline",
]);

// สิ่งที่แสดงบนแถบงาน (key ใน settings)
const bar_toggles = [
	{ key: "show_baseline_bars", label: __("แถบ Baseline") },
	{ key: "show_split", label: __("% แผนที่แบ่ง"), title: __("แสดง % แผนที่กำหนดเองบนแถบงาน") },
	{
		key: "show_links",
		label: __("เส้นงานก่อนหน้า"),
		title: __("แสดงลูกศรจากงานก่อนหน้าไปงานที่ตามมา (FS / SS / FF / SF)"),
	},
	{ key: "show_labels", label: __("ชื่องาน"), title: __("แสดง WBS และชื่องานท้ายแถบ") },
	{
		key: "show_progress",
		label: __("% แผน / จริง"),
		title: __("แสดง % แผนและ % จริง ณ วันที่เลือกดู ท้ายแถบ"),
	},
	{
		key: "show_status",
		label: __("สีตามสถานะ"),
		title: __(
			"สีแถบงานตามสถานะ ณ วันที่เลือกดู: เขียว = เสร็จแล้ว, ส้ม = ช้ากว่าแผนไม่เกิน 10%, แดง = ช้ากว่าแผนเกิน 10%"
		),
	},
];

// แถวของตารางสรุปจัดกลุ่มตามเส้น (Baseline / แผน / จริง)
const summary_groups = computed(() =>
	props.curves
		.map((curve) => ({
			...curve,
			rows: props.summaryOptions.filter((row) => row.curve === curve.key),
		}))
		.filter((group) => group.rows.length)
);

function toggle_summary_row(key) {
	const keys = props.settings.summary_keys;
	props.settings.summary_keys = keys.includes(key)
		? keys.filter((k) => k !== key)
		: props.summaryOptions.map((r) => r.key).filter((k) => k === key || keys.includes(k));
}

// ระดับ WBS: ระดับ 1 = หัวข้อหลัก (1), ระดับ 2 = 1.1, ...
const levels = computed(() =>
	Array.from({ length: Math.max(props.wbsDepth, 0) }, (_, i) => ({
		level: i + 1,
		example: Array.from({ length: i + 1 }, () => "1").join("."),
	}))
);

// เทียบ % จริงกับ Baseline ณ วันที่เลือก ยังไม่ตั้ง Baseline เทียบกับแผนปัจจุบัน (ตรงกับ target_progress ฝั่ง Python)
// ต่างกันไม่ถึง 0.005% ถือว่าตามแผน ใช้ indicator มาตรฐานของ Frappe
const variance = computed(() => {
	const { baseline, plan, actual } = props.readout;
	const target = baseline ?? plan;
	if (target === null || actual === null) return null;
	const diff = actual - target;
	const label = baseline !== null ? "Baseline" : __("แผน");
	if (Math.abs(diff) < 0.005) return { text: __("ตาม{0}", [label]), color: "gray" };
	return diff > 0
		? { text: __("เร็วกว่า{0} {1}", [label, percent(diff)]), color: "green" }
		: { text: __("ช้ากว่า{0} {1}", [label, percent(-diff)]), color: "red" };
});

// แผนงานเสร็จหลังวันสิ้นสุดสัญญา
const late = computed(
	() => props.finishDate && props.contractFinish && props.finishDate > props.contractFinish
);

const viewed = computed(() => props.baselines.find((b) => b.name === props.viewedBaseline) || null);

const revised = computed(() => props.contractAmount !== props.totalAmount);

const icon = (name) => frappe.utils.icon(name, "sm");
const amount = (value) => format_number(value || 0, null, 2);
const percent = (value) =>
	value === null || value === undefined ? "-" : format_number(value, null, 2) + "%";
const date = (value) => frappe.datetime.str_to_user(value);
</script>

<template>
	<div class="cs-toolbar">
		<div class="cs-bar">
			<template v-if="canWrite">
				<div class="cs-segment">
					<button
						type="button"
						class="cs-seg-btn"
						:title="__('ย้อนกลับ (Ctrl+Z)')"
						:disabled="!canUndo"
						@click="$emit('undo')"
						v-html="icon('undo-2')"
					/>
					<button
						type="button"
						class="cs-seg-btn"
						:title="__('ทำซ้ำ (Ctrl+Y)')"
						:disabled="!canRedo"
						@click="$emit('redo')"
						v-html="icon('redo-2')"
					/>
				</div>
				<label class="switch-control cs-switch" :title="__('บันทึกให้เองหลังหยุดแก้ไขครู่หนึ่ง')">
					<span class="switch-text">
						<span class="label-area">{{ __("บันทึกอัตโนมัติ") }}</span>
					</span>
					<span class="input-area"><input v-model="settings.auto_save" type="checkbox" /></span>
					<span class="switch-visual"><span class="switch-thumb" /></span>
				</label>
				<span class="cs-divider" />
			</template>

			<div class="cs-segment" role="group" :aria-label="__('มาตราส่วนเวลา')">
				<button
					v-for="(scale, key) in scales"
					:key="key"
					type="button"
					class="cs-seg-btn"
					:class="{ active: settings.scale === key }"
					@click="settings.scale = key"
				>
					{{ scale.label }}
				</button>
			</div>
			<div class="cs-segment">
				<button
					type="button"
					class="cs-seg-btn"
					:title="__('ย่อ timeline')"
					@click="$emit('zoom', 'out')"
					v-html="icon('zoom-out')"
				/>
				<button
					type="button"
					class="cs-seg-btn"
					:title="__('ขยาย timeline')"
					@click="$emit('zoom', 'in')"
					v-html="icon('zoom-in')"
				/>
				<button
					type="button"
					class="cs-seg-btn"
					:title="__('ย่อให้เห็นทั้งโครงการในหน้าจอ')"
					@click="$emit('zoom', 'fit')"
					v-html="icon('scan')"
				/>
			</div>
			<span class="cs-divider" />
			<!-- วันที่เลือกดูกับปุ่มวันนี้อยู่กลุ่มเดียวกัน: วันนี้ = ดูค่า ณ วันนี้และเลื่อนไปที่วันนี้ -->
			<div class="cs-status-date" :title="__('ค่า % และสถานะงานคิด ณ วันที่นี้')">
				<span>{{ __("ณ วันที่") }}</span>
				<FrappeControl
					:df="{ fieldtype: 'Date' }"
					:model-value="statusDate"
					@update:model-value="(v) => v && $emit('update:statusDate', v)"
				/>
				<button type="button" class="btn btn-default btn-sm" @click="$emit('today')">
					{{ __("วันนี้") }}
				</button>
			</div>

			<div class="cs-bar-end">
				<div class="dropdown">
					<button
						type="button"
						class="btn btn-default btn-sm cs-btn dropdown-toggle"
						data-toggle="dropdown"
						aria-haspopup="true"
						aria-expanded="false"
						:title="__('เลือก Baseline ที่จะดู และจัดการ Baseline')"
					>
						<span v-html="icon('flag')" />
						<span class="cs-baseline-label">
							{{ viewed ? __("Baseline: {0}", [viewed.title]) : __("Baseline") }}
						</span>
					</button>
					<div class="dropdown-menu dropdown-menu-right cs-menu">
						<div class="cs-menu-title">{{ __("เปิดดู") }}</div>
						<a
							v-for="baseline in baselines"
							:key="baseline.name"
							class="dropdown-item cs-baseline-item"
							href="#"
							:title="baseline.reason || ''"
							@click.prevent="$emit('view-baseline', baseline.name)"
						>
							<span
								class="cs-check"
								:style="{ visibility: baseline.name === viewedBaseline ? 'visible' : 'hidden' }"
								v-html="icon('check')"
							/>
							<span class="cs-baseline-name">
								{{ baseline.title }}
								<span class="text-muted">{{ date(baseline.baseline_date) }}</span>
							</span>
							<span v-if="baseline.name === activeBaseline" class="indicator-pill blue">
								{{ __("ใช้เทียบ") }}
							</span>
						</a>
						<div v-if="!baselines.length" class="dropdown-item disabled">
							{{ __("ยังไม่มี Baseline") }}
						</div>
						<template v-if="canWrite">
							<div class="dropdown-divider" />
							<a class="dropdown-item" href="#" @click.prevent="$emit('save-baseline')">
								{{ __("บันทึก Baseline ใหม่...") }}
							</a>
							<a
								class="dropdown-item"
								:class="{ disabled: !viewed || viewed.name === activeBaseline }"
								href="#"
								@click.prevent="$emit('activate-baseline')"
							>
								{{ __("ใช้ชุดที่เปิดดูเทียบกับความคืบหน้าจริง") }}
							</a>
							<a
								v-if="canDeleteBaseline"
								class="dropdown-item text-danger"
								:class="{ disabled: !viewed || viewed.name === activeBaseline }"
								:title="__('ชุดที่ใช้เทียบอยู่ลบไม่ได้ ให้เลือกชุดอื่นเป็นตัวเทียบก่อน')"
								href="#"
								@click.prevent="$emit('delete-baseline')"
							>
								{{ __("ลบชุดที่เปิดดู") }}
							</a>
						</template>
					</div>
				</div>

				<div class="dropdown">
					<button
						type="button"
						class="btn btn-default btn-sm cs-btn dropdown-toggle"
						data-toggle="dropdown"
						aria-haspopup="true"
						aria-expanded="false"
					>
						<span v-html="icon('list-tree')" />{{ __("WBS") }}
					</button>
					<div class="dropdown-menu dropdown-menu-right">
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

				<div class="dropdown">
					<button
						type="button"
						class="btn btn-default btn-sm cs-btn dropdown-toggle"
						data-toggle="dropdown"
						aria-haspopup="true"
						aria-expanded="false"
					>
						<span v-html="icon('sliders-horizontal')" />{{ __("แสดงผล") }}
					</button>
					<div class="dropdown-menu dropdown-menu-right cs-menu" @click.stop>
						<div class="cs-menu-title">{{ __("เส้น S-Curve") }}</div>
						<label v-for="curve in curves" :key="curve.key" class="switch-control cs-menu-item">
							<span class="switch-text">
								<span class="label-area">
									<span class="cs-dot" :style="{ background: curve.color }" />
									{{ curve.label }}
								</span>
							</span>
							<span class="input-area">
								<input v-model="settings.curves[curve.key]" type="checkbox" />
							</span>
							<span class="switch-visual"><span class="switch-thumb" /></span>
						</label>
						<div class="dropdown-divider" />
						<div class="cs-menu-title">{{ __("บนแถบงาน") }}</div>
						<label
							v-for="toggle in bar_toggles"
							:key="toggle.key"
							class="switch-control cs-menu-item"
							:title="toggle.title"
						>
							<span class="switch-text">
								<span class="label-area">{{ toggle.label }}</span>
							</span>
							<span class="input-area">
								<input v-model="settings[toggle.key]" type="checkbox" />
							</span>
							<span class="switch-visual"><span class="switch-thumb" /></span>
						</label>
					</div>
				</div>

				<div class="dropdown">
					<button
						type="button"
						class="btn btn-default btn-sm cs-btn dropdown-toggle"
						data-toggle="dropdown"
						aria-haspopup="true"
						aria-expanded="false"
					>
						<span v-html="icon('table-2')" />{{ __("ตารางสรุป") }}
					</button>
					<div class="dropdown-menu dropdown-menu-right cs-menu" @click.stop>
						<label class="switch-control cs-menu-item">
							<span class="switch-text">
								<span class="label-area"
									><b>{{ __("แสดงตารางสรุป") }}</b></span
								>
							</span>
							<span class="input-area">
								<input v-model="settings.show_summary" type="checkbox" />
							</span>
							<span class="switch-visual"><span class="switch-thumb" /></span>
						</label>
						<template v-for="group in summary_groups" :key="group.key">
							<div class="dropdown-divider" />
							<div class="cs-menu-title">
								<span class="cs-dot" :style="{ background: group.color }" />
								{{ group.label }}
							</div>
							<label
								v-for="row in group.rows"
								:key="row.key"
								class="switch-control cs-menu-item"
							>
								<span class="switch-text">
									<span class="label-area">{{ row.label }}</span>
								</span>
								<span class="input-area">
									<input
										type="checkbox"
										:checked="settings.summary_keys.includes(row.key)"
										:disabled="!settings.show_summary"
										@change="toggle_summary_row(row.key)"
									/>
								</span>
								<span class="switch-visual"><span class="switch-thumb" /></span>
							</label>
						</template>
					</div>
				</div>

				<button
					type="button"
					class="btn btn-default btn-sm cs-btn"
					@click="$emit('choose-columns')"
				>
					<span v-html="icon('columns-3')" />{{ __("คอลัมน์") }}
				</button>
			</div>
		</div>

		<div class="cs-stats">
			<div
				v-for="curve in curves"
				v-show="readout[curve.key] !== null"
				:key="curve.key"
				class="cs-stat"
			>
				<span class="cs-stat-label">
					<span class="cs-dot" :style="{ background: curve.color }" />{{ curve.label }}
				</span>
				<span class="cs-stat-value">{{ percent(readout[curve.key]) }}</span>
			</div>
			<span v-if="variance" class="indicator-pill" :class="variance.color">
				{{ variance.text }}
			</span>

			<div class="cs-stats-end">
				<div v-if="contractStart" class="cs-stat">
					<span class="cs-stat-label">{{ __("เริ่มสัญญา") }}</span>
					<span class="cs-stat-value">{{ date(contractStart) }}</span>
				</div>
				<div v-if="contractFinish" class="cs-stat">
					<span class="cs-stat-label">{{ __("สิ้นสุดสัญญา") }}</span>
					<span class="cs-stat-value">{{ date(contractFinish) }}</span>
				</div>
				<div v-if="contractDuration" class="cs-stat">
					<span class="cs-stat-label">{{ __("ระยะเวลาสัญญา") }}</span>
					<span class="cs-stat-value">{{ __("{0} วัน", [contractDuration]) }}</span>
				</div>
				<div v-if="finishDate" class="cs-stat">
					<span class="cs-stat-label">{{ __("แผนเสร็จ") }}</span>
					<span
						class="cs-stat-value"
						:class="{ 'text-danger': late }"
						:title="late ? __('แผนงานเสร็จหลังวันสิ้นสุดสัญญา') : ''"
					>
						{{ date(finishDate) }}
					</span>
				</div>
				<div
					class="cs-stat"
					:title="
						revised
							? __('สัญญาเดิม {0} + งานเพิ่ม-ลดที่อนุมัติแล้ว {1}', [
									amount(contractAmount),
									amount(totalAmount - contractAmount),
							  ])
							: ''
					"
				>
					<span class="cs-stat-label">
						{{ revised ? __("มูลค่าสัญญาปรับปรุง") : __("มูลค่าสัญญา") }}
					</span>
					<span class="cs-stat-value">{{ amount(totalAmount) }}</span>
				</div>
			</div>
		</div>
	</div>
</template>

<style scoped>
/* เว้นจากหัวเพจด้านบน */
.cs-toolbar {
	padding-top: var(--padding-md);
	margin-bottom: var(--padding-sm);
}
.cs-bar,
.cs-stats {
	display: flex;
	flex-wrap: wrap;
	align-items: center;
	gap: var(--padding-sm);
}
.cs-bar-end,
.cs-stats-end {
	display: flex;
	flex-wrap: wrap;
	align-items: center;
	gap: var(--padding-sm);
	margin-left: auto;
}

/* กลุ่มปุ่มแบบ segmented control */
.cs-segment {
	display: inline-flex;
	align-items: center;
	gap: 2px;
	padding: 2px;
	border-radius: var(--radius);
	background: var(--control-bg);
}
.cs-seg-btn {
	display: inline-flex;
	align-items: center;
	justify-content: center;
	min-width: 28px;
	height: 24px;
	padding: 0 var(--padding-sm);
	border: 0;
	border-radius: var(--radius-3);
	background: transparent;
	color: var(--text-muted);
	font-size: var(--text-sm);
	line-height: 1;
}
.cs-seg-btn:hover:not(:disabled) {
	color: var(--text-color);
}
.cs-seg-btn.active {
	background: var(--card-bg);
	color: var(--text-color);
	font-weight: 600;
	box-shadow: var(--shadow-sm);
}
.cs-seg-btn:disabled {
	opacity: 0.4;
	cursor: default;
}
.cs-btn {
	display: inline-flex;
	align-items: center;
	gap: 6px;
}
.cs-switch {
	width: auto;
	gap: var(--padding-sm);
	font-size: var(--text-sm);
}
.cs-switch .label-area {
	font-size: var(--text-sm);
}
.cs-divider {
	width: 1px;
	height: 20px;
	background: var(--border-color);
}
.cs-status-date {
	display: flex;
	align-items: center;
	gap: var(--padding-xs);
	font-size: var(--text-sm);
	color: var(--text-muted);
}
.cs-status-date :deep(.cs-control) {
	width: 130px;
}

/* เมนูสวิตช์ */
.cs-menu {
	min-width: 230px;
	border-radius: var(--radius-md);
	padding: var(--padding-xs) 0;
}
/* เมนู Baseline: เครื่องหมายถูก = ชุดที่เปิดดู ป้าย "ใช้เทียบ" = ชุดที่ใช้กับรายงาน */
.cs-baseline-label {
	display: inline-block;
	max-width: 180px;
	overflow: hidden;
	text-overflow: ellipsis;
	white-space: nowrap;
	vertical-align: bottom;
}
.cs-baseline-item {
	display: flex;
	align-items: center;
	gap: 6px;
}
.cs-baseline-name {
	flex: 1;
}
.cs-menu-title {
	display: flex;
	align-items: center;
	gap: 6px;
	padding: var(--padding-xs) var(--padding-md) 2px;
	font-size: var(--text-xs);
	font-weight: 600;
	color: var(--text-muted);
}
.cs-menu-item {
	padding: 4px var(--padding-md);
	margin: 0 var(--padding-xs);
	width: auto;
	border-radius: var(--radius-sm);
	gap: var(--padding-lg);
}
.cs-menu-item:hover {
	background: var(--subtle-fg);
}
.cs-menu-item .label-area {
	display: flex;
	align-items: center;
	gap: 6px;
	font-size: var(--text-sm);
}

/* ตัวเลข ณ วันที่เลือกดู */
.cs-stats {
	margin-top: var(--padding-sm);
	padding: var(--padding-sm) var(--padding-md);
	gap: var(--padding-sm) var(--padding-xl);
	border: 1px solid var(--border-color);
	border-radius: var(--radius-lg);
	background: var(--card-bg);
}
.cs-stats-end {
	gap: var(--padding-sm) var(--padding-xl);
}
.cs-stat {
	display: flex;
	flex-direction: column;
	gap: 2px;
}
.cs-stat-label {
	display: flex;
	align-items: center;
	gap: 6px;
	font-size: var(--text-xs);
	color: var(--text-muted);
}
.cs-stat-value {
	font-size: var(--text-base);
	font-weight: 600;
	color: var(--text-color);
}
.cs-dot {
	display: inline-block;
	width: 8px;
	height: 8px;
	border-radius: 50%;
}
</style>
