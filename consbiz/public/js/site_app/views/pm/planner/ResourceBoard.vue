<!-- Gantt ทรัพยากร (ดูอย่างเดียว): วัสดุ = ต้องทำเรื่องสั่ง / ของต้องถึง / ช่วงใช้งาน, คน-เครื่องจักร = ต้องจอง / ช่วงใช้งาน + จำนวนสูงสุดต่อช่วง
     ใช้ในหน้าแผนงาน/แก้แผน (ค่าตามที่กำลังแก้) และหน้าทรัพยากร แกนเวลา = time_axis.js ชุดเดียวกับ PlanSheet -->
<template>
	<div class="pl-board">
		<div class="rb-legend">
			<span><i class="rb-mark is-order tone-gray"></i>ต้องทำเรื่องสั่ง / ต้องจอง</span>
			<span><i class="rb-mark is-arrive"></i>ของต้องถึง</span>
			<span><i class="rb-swatch"></i>ช่วงใช้งาน</span>
			<span class="rb-legend-tones">
				<i class="rb-dot tone-rose"></i>เลยกำหนด
				<i class="rb-dot tone-amber"></i>ใกล้ถึง
				<i class="rb-dot tone-green"></i>ขอแล้ว
			</span>
		</div>
		<Empty v-if="!groups.length" icon="users" title="ยังไม่มีแผนทรัพยากร" text="เพิ่มคน เครื่องจักร หรือวัสดุที่แท็บทรัพยากรของงาน" />
		<div
			v-else
			ref="scroller"
			class="pl-scroll"
			:style="{ '--grid-w': `${grid_w}px`, '--row-h': `${ROW_H}px` }"
		>
			<div class="pl-sheet" :style="{ width: `${grid_w + timeline_w}px` }">
				<div class="pl-head">
					<div class="pl-head-cells">
						<div class="pl-hcell rb-corner" :style="{ width: `${grid_w}px` }">
							<span>ทรัพยากร</span>
							<button type="button" class="rb-link" @click="set_all(true)">ขยาย</button>
							<button type="button" class="rb-link" @click="set_all(false)">ย่อ</button>
						</div>
					</div>
					<div class="pl-head-time" :style="{ width: `${timeline_w}px` }">
						<div class="pl-head-row">
							<span
								v-for="period in top_periods"
								:key="period.start"
								:style="{ left: `${x(period.start)}px`, width: `${x(period.end) - x(period.start)}px` }"
								><b>{{ period.label }}</b></span
							>
						</div>
						<div class="pl-head-row is-bottom">
							<span
								v-for="period in bottom_periods"
								:key="period.start"
								:style="{ left: `${x(period.start)}px`, width: `${x(period.end) - x(period.start)}px` }"
								>{{ period.label }}</span
							>
						</div>
					</div>
				</div>

				<div class="pl-body" :style="{ height: `${body_h}px` }">
					<svg class="pl-bg" :width="timeline_w" :height="body_h" aria-hidden="true">
						<line v-for="period in bottom_periods" :key="period.start" class="pl-vline" :x1="x(period.start)" :x2="x(period.start)" y1="0" :y2="body_h" />
						<rect v-for="day in off_days" :key="`o${day}`" class="pl-off" :x="x(day)" y="0" :width="x(day + 1) - x(day)" :height="body_h" />
						<rect v-if="today_in_range" class="pl-today" :x="x(today_day)" y="0" :width="Math.max(x(today_day + 1) - x(today_day), 2)" :height="body_h" />
						<line class="pl-cutoff" :x1="day_mid(p.cutoff_day)" :x2="day_mid(p.cutoff_day)" y1="0" :y2="body_h" />
						<line v-if="finish_day !== null" class="rb-finish" :x1="x(finish_day + 1)" :x2="x(finish_day + 1)" y1="0" :y2="body_h" />
					</svg>
					<div
						v-for="(row, i) in rows"
						:key="row.key"
						class="pl-row"
						:class="{ 'is-group': row.kind !== 'usage', 'is-level-0': row.kind === 'group' }"
						:style="{ top: `${i * ROW_H}px` }"
					>
						<div class="pl-cells" @click="on_click(row)">
							<div class="pl-cell col-item_name" :style="{ width: `${grid_w}px` }">
								<span class="pl-indent" :style="{ width: `${INDENT[row.kind]}px` }"></span>
								<span v-if="row.kind !== 'usage'" class="pl-caret" :class="{ 'is-closed': collapsed.has(row.key) }">
									<Icon name="chevron-down" :size="14" :stroke="2.4" />
								</span>
								<Icon v-if="row.kind === 'group'" :name="row.type.icon" :size="14" />
								<span class="pl-name" :title="row.kind === 'usage' ? row.title : row.summary_title || row.label">{{ row.label }}</span>
								<small v-if="row.kind === 'group'" class="rb-count">{{ row.items.length }}</small>
								<small v-else class="rb-summary" :class="row.tone && `tone-${row.tone}`">{{ row.kind === 'usage' ? row.qty_text : row.summary }}</small>
							</div>
						</div>
						<div class="pl-track" :style="{ width: `${timeline_w}px` }">
							<template v-if="row.kind === 'item'">
								<template v-if="row.type.key === 'Material'">
									<template v-for="usage in row.usages" :key="usage.key">
										<div v-if="usage.start !== null" class="rb-span" :style="span(usage.start, usage.end)" :title="usage.title"></div>
										<i
											v-if="usage.target !== null"
											class="rb-mark is-order"
											:class="`tone-${usage.tone}`"
											:style="{ left: `${day_mid(usage.target)}px` }"
											:title="usage.title"
										></i>
									</template>
								</template>
								<template v-else>
									<span
										v-for="cell in load_cells(row)"
										:key="cell.left"
										class="rb-load"
										:style="{ left: `${cell.left}px`, width: `${cell.width}px`, background: cell.background }"
										:title="cell.title"
										>{{ cell.text }}</span
									>
								</template>
							</template>
							<template v-else-if="row.kind === 'usage' && row.start !== null">
								<span
									v-if="row.target !== null && row.target < row.start"
									class="rb-lead"
									:style="{ left: `${day_mid(row.target)}px`, width: `${x(row.start) - day_mid(row.target)}px` }"
								></span>
								<div class="rb-use" :class="`is-${row.type.key.toLowerCase()}`" :style="span(row.start, row.end)" :title="row.title"></div>
								<i
									v-if="row.target !== null"
									class="rb-mark is-order"
									:class="`tone-${row.tone}`"
									:style="{ left: `${day_mid(row.target)}px` }"
									:title="row.title"
								></i>
								<i
									v-if="row.required_by !== null"
									class="rb-mark is-arrive"
									:style="{ left: `${day_mid(row.required_by)}px` }"
									:title="row.title"
								></i>
								<span class="pl-label" :style="{ left: `${x(row.end + 1) + 6}px` }">{{ row.qty_text }}</span>
							</template>
						</div>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref } from "vue";
import Icon from "../../../../shared/components/Icon.vue";
import Empty from "../../../../shared/components/Empty.vue";
import { item_daily, plan_extra_days, plan_groups } from "./resource_rows.js";
import { use_time_axis } from "./time_axis.js";
import { to_day, today } from "../../../../construction_management/schedule.js";

const props = defineProps({
	p: { type: Object, required: true },
	settings: { type: Object, required: true },
});
const emit = defineEmits(["open"]);

const ROW_H = 36;
const INDENT = { group: 0, item: 14, usage: 44 };
const GRID_W = 280;
const GRID_W_NARROW = 140;
// ช่องแคบกว่านี้ไม่แสดงจำนวน (ดูจาก tooltip)
const MIN_LOAD_WIDTH = 22;

const p = computed(() => props.p);
const scroller = ref(null);
const collapsed = reactive(new Set());
const { x, day_mid, span, range, timeline_w, top_periods, bottom_periods, off_days } = use_time_axis(p, props.settings, () => plan_extra_days(props.p));

const narrow = window.matchMedia("(max-width: 767px)");
const is_narrow = ref(narrow.matches);
const on_narrow = () => (is_narrow.value = narrow.matches);
const grid_w = computed(() => (is_narrow.value ? GRID_W_NARROW : GRID_W));

const groups = computed(() => plan_groups(props.p));
const rows = computed(() => {
	const result = [];
	for (const group of groups.value) {
		result.push(group);
		if (collapsed.has(group.key)) continue;
		for (const item of group.items) {
			result.push(item);
			if (!collapsed.has(item.key)) result.push(...item.usages);
		}
	}
	return result;
});
const body_h = computed(() => rows.value.length * ROW_H);

const today_day = today();
const today_in_range = computed(() => today_day >= range.value.start && today_day < range.value.end);
// วันสิ้นสุดสัญญา (รวมขยายเวลา)
const finish_day = computed(() => {
	const day = to_day(props.p.data?.revised_finish_date || props.p.data?.finish_date);
	return day !== null && day >= range.value.start && day < range.value.end ? day : null;
});

const short = (value) => (Number.isInteger(value) ? String(value) : value.toFixed(1));

// จำนวนสูงสุดต่อวันในแต่ละช่องเวลา
function load_cells(item) {
	const daily = item_daily(props.p, item);
	const cells = [];
	for (const period of bottom_periods.value) {
		let peak = 0;
		let sum = 0;
		for (let day = period.start; day < period.end; day++) {
			const value = daily.get(day) || 0;
			peak = Math.max(peak, value);
			sum += value;
		}
		if (!peak) continue;
		const left = x(period.start);
		const width = x(period.end) - left;
		cells.push({
			left,
			width,
			// เข้มตามสัดส่วนของจำนวนสูงสุดของรายการนี้
			background: `color-mix(in srgb, var(--pl-actual) ${Math.round(16 + (52 * peak) / (item.peak || peak))}%, var(--ss-surface))`,
			text: width >= MIN_LOAD_WIDTH ? short(peak) : "",
			title: `${item.label}\nสูงสุด ${short(peak)} ${item.type.unit}\nรวม ${short(sum)} ${item.type.total_unit}`,
		});
	}
	return cells;
}

function on_click(row) {
	if (row.kind === "usage") {
		if (row.task) emit("open", row.task);
		return;
	}
	if (collapsed.has(row.key)) collapsed.delete(row.key);
	else collapsed.add(row.key);
}

// เปิดมาให้เห็นรายการ: รายการแรกที่ยังต้องเตรียม (ถึงกำหนดหลังวัน Cut-off) ไม่มี = รายการแรกของแผน
function first_focus_day() {
	const days = groups.value.flatMap((group) => group.items.flatMap((item) => item.usages)).flatMap((usage) => usage.target ?? usage.start ?? []);
	const upcoming = days.filter((day) => day >= props.p.cutoff_day);
	return Math.min(...(upcoming.length ? upcoming : days.length ? days : [props.p.cutoff_day]));
}

// ขยาย = เห็นทุกงาน, ย่อ = เหลือแถวของแต่ละรายการ
function set_all(expanded) {
	collapsed.clear();
	if (!expanded) for (const group of groups.value) for (const item of group.items) collapsed.add(item.key);
}

function scroll_to_day(day, align = 0.3) {
	const el = scroller.value;
	if (!el) return;
	el.scrollTo({ left: Math.max(x(day) - (el.clientWidth - grid_w.value) * align, 0), behavior: "smooth" });
}

onMounted(() => {
	narrow.addEventListener("change", on_narrow);
	nextTick(() => {
		const el = scroller.value;
		if (el) el.scrollLeft = Math.max(x(first_focus_day()) - (el.clientWidth - grid_w.value) * 0.15, 0);
	});
});
onBeforeUnmount(() => narrow.removeEventListener("change", on_narrow));

defineExpose({ scroll_to_day });
</script>
