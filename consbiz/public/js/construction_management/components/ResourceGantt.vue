<script setup>
// มุมมอง "ทรัพยากร" ของหน้า Gantt (ดูอย่างเดียว): แถวเป็นทรัพยากร จัดกลุ่ม แรงงาน / เครื่องจักร / วัสดุ
// แถวทรัพยากร: แรงงาน/เครื่องจักร = จำนวนสูงสุดต่อวันในแต่ละช่องเวลา (สีเข้มตามจำนวน), วัสดุ = ช่วงที่ใช้และจุดวันต้องสั่ง
// แถวย่อย (งานที่ใช้): แถบช่วงงาน + เส้นประจากวันต้องสั่ง/ต้องจองถึงวันเริ่มงาน สีตามกำหนด (prep_tone)
// ข้อมูลเป็นแถวแผนทรัพยากร/วัสดุและวันที่งานที่ App ถืออยู่ (รวมที่แก้แต่ยังไม่บันทึก) แก้รายการที่แผงงาน (TaskPanel)
// คลิกแถวย่อย = กลับไปมุมมองงานและเปิดแผงของงานนั้น (emit open-task)
// ตารางชื่อด้านซ้ายกับ timeline อยู่ใน scroll เดียวกัน (ซ้าย/หัว sticky) จึงไม่ต้อง sync การเลื่อน
import { computed, onBeforeUnmount, onMounted, reactive, ref } from "vue";
import {
	book_by,
	from_day,
	is_requested,
	material_dates,
	material_key,
	periods,
	resource_daily,
	to_day,
	today,
} from "../schedule";
import { period_label, prep_tone } from "../columns";

const props = defineProps({
	tasks: Array,
	resources: Array,
	materials: Array,
	bufferDays: Number,
	coverage: Map, // วัสดุ: key ของแถว → ยอดที่ตัดได้ (allocate_materials)
	supply: Object, // วัสดุ: item_code → ยอดของโครงการ แยกซื้อเอง/ลูกค้าจัดหา (หน่วยสต็อก)
	range: Object,
	ppd: Number,
	units: Object,
	holidays: Set,
	countingHolidays: Set,
	statusDay: Number,
	contractFinish: String,
	rowHeight: Number,
	headerHeight: Number,
});
const emit = defineEmits(["open-task"]);

const TYPES = [
	{ key: "Labour", label: __("แรงงาน"), unit: __("คน/วัน"), icon: "users" },
	{ key: "Equipment", label: __("เครื่องจักร"), unit: __("คัน/วัน"), icon: "truck" },
	{ key: "Material", label: __("วัสดุ"), icon: "package" },
];

const body = ref(null);
const viewport_width_px = ref(0);
const left_width = computed(() => Math.min(340, Math.max(viewport_width_px.value * 0.4, 180)));
const collapsed = reactive(new Set());
const hovered = ref(null);

const task_by_name = computed(() => new Map(props.tasks.map((t) => [t.name, t])));
const day = computed(() => today());

const x = (d) => (d - props.range.start) * props.ppd;
const width = computed(() => (props.range.end - props.range.start) * props.ppd);
const fmt_day = (d) => (d === null || d === undefined ? "-" : frappe.datetime.str_to_user(from_day(d)));
const fmt_qty = (value) => format_number(value || 0, null, value % 1 ? 2 : 0);
const icon = (name, size = "sm") => frappe.utils.icon(name, size);

// ---------- หัว timeline ----------

function header_row(unit, top_level) {
	return periods(props.range.start, props.range.end, unit).map((period) => ({
		...period,
		x: x(period.start),
		width: (period.end - period.start) * props.ppd,
		label: period_label(period, unit, top_level),
	}));
}
const top_header = computed(() => header_row(props.units.top, true));
const bottom_header = computed(() => header_row(props.units.bottom, false));
const show_bottom_labels = computed(() => (bottom_header.value[0]?.width || 0) >= 18);
const holiday_rects = computed(() =>
	props.ppd < 3
		? []
		: [...props.holidays].filter((d) => d >= props.range.start && d < props.range.end).map(x)
);
const day_x = (d) => (d >= props.range.start && d < props.range.end ? x(d) : null);
const today_x = computed(() => day_x(day.value + 1));
const status_x = computed(() => day_x(props.statusDay + 1));
const finish_x = computed(() => (props.contractFinish ? day_x(to_day(props.contractFinish) + 1) : null));

// ---------- แถว ----------

function usage_row(type, row) {
	const task = task_by_name.value.get(row.task);
	const start = to_day(task?.start_date);
	const end = to_day(task?.end_date);
	let target;
	let required_by = null;
	let pending;
	let qty_text;
	let cov = null;
	if (type.key === "Material") {
		({ order_by: target, required_by } = material_dates(start, props.bufferDays, row.lead_time_days));
		cov = props.coverage?.get(material_key(row)) || null;
		pending = !is_requested(cov);
		qty_text = `${fmt_qty(row.qty)} ${row.uom || ""}`.trim();
	} else {
		target = book_by(start, row.lead_time_days);
		pending = start === null || start > day.value;
		qty_text = `${fmt_qty(row.qty_per_day)} ${type.unit}`;
	}
	const tone = prep_tone(target, pending, day.value);
	const verb = type.key === "Material" ? __("ต้องสั่ง") : __("ต้องจอง");
	const status =
		type.key === "Material"
			? cov && cov.requested > 0
				? `${__("ขอแล้ว")} ${fmt_qty(cov.requested)} · ${__("สั่งซื้อ")} ${fmt_qty(cov.ordered)} · ${__("รับ")} ${fmt_qty(
						cov.received
				  )}${cov.state === "partial" ? ` · ${__("ขาด")} ${fmt_qty(cov.shortfall)}` : ""}`
				: __("ยังไม่ได้ขอ")
			: pending
			? ""
			: __("เริ่มงานแล้ว");
	return {
		key: `u:${row.name || row.key}`,
		kind: "usage",
		task,
		row,
		start,
		end,
		target,
		required_by,
		tone,
		label: task ? `${task.wbs || ""} ${task.item_name || ""}`.trim() : __("(ไม่พบงาน)"),
		qty_text,
		title: [
			task ? `${task.wbs || ""} ${task.item_name || ""}`.trim() : "",
			qty_text,
			start !== null ? `${__("ใช้")}: ${fmt_day(start)} - ${fmt_day(end)}` : __("งานยังไม่มีวันที่"),
			type.key === "Material" && required_by !== null ? `${__("ต้องมีภายใน")}: ${fmt_day(required_by)}` : "",
			target !== null ? `${verb}: ${fmt_day(target)} (${__("เตรียมล่วงหน้า {0} วัน", [row.lead_time_days || 0])})` : "",
			status,
			__("คลิกเพื่อเปิดงานนี้"),
		]
			.filter(Boolean)
			.join("\n"),
	};
}

// ยอดของโครงการแยกซื้อเอง / ลูกค้าจัดหา (หน่วยสต็อก)
function supply_text(supply, uom) {
	const line = (label, s, ordered) =>
		`${label}: ${__("ขอ")} ${fmt_qty(s.requested)}${s.draft ? ` (${__("ร่าง")} ${fmt_qty(s.draft)})` : ""}${
			ordered ? ` · ${__("สั่งซื้อ")} ${fmt_qty(s.ordered)}` : ""
		} · ${__("รับ")} ${fmt_qty(s.received)} ${uom}`;
	return [
		supply.purchase?.requested ? line(__("ซื้อเอง"), supply.purchase, true) : "",
		supply.customer?.requested ? line(__("ลูกค้าจัดหา"), supply.customer, false) : "",
	]
		.filter(Boolean)
		.join("\n");
}

// แรงงาน/เครื่องจักร: จำนวนสูงสุดต่อวันในแต่ละช่องเวลาของหัวล่าง
function load_cells(rows) {
	const daily = resource_daily(rows, task_by_name.value, props.countingHolidays);
	if (!daily.size) return { cells: [], peak: 0, total: 0 };
	const values = [...daily.values()];
	const peak = Math.max(...values);
	const total = values.reduce((sum, v) => sum + v, 0);
	const cells = [];
	for (const period of bottom_header.value) {
		let max = 0;
		let sum = 0;
		for (let d = period.start; d < period.end; d++) {
			const value = daily.get(d) || 0;
			max = Math.max(max, value);
			sum += value;
		}
		if (max > 0) cells.push({ x: period.x, width: period.width, max, sum, period });
	}
	return { cells, peak, total };
}

const groups = computed(() => {
	const result = [];
	for (const type of TYPES) {
		const rows = type.key === "Material" ? props.materials : props.resources.filter((r) => r.resource_type === type.key);
		const by_name = new Map();
		for (const row of rows) {
			const name = type.key === "Material" ? row.item_code : row.resource;
			if (!name) continue;
			if (!by_name.has(name)) by_name.set(name, []);
			by_name.get(name).push(row);
		}
		if (!by_name.size) continue;
		const items = [...by_name.entries()]
			.map(([name, list]) => {
				const usages = list.map((row) => usage_row(type, row)).sort((a, b) => (a.start ?? Infinity) - (b.start ?? Infinity));
				const dated = usages.filter((u) => u.start !== null);
				const item = {
					key: `r:${type.key}:${name}`,
					kind: "resource",
					type,
					name,
					label: type.key === "Material" ? list[0].item_label || name : name,
					usages,
					first: dated.length ? Math.min(...dated.map((u) => u.start)) : null,
					last: dated.length ? Math.max(...dated.map((u) => u.end)) : null,
				};
				if (type.key === "Material") {
					// รวมตามหน่วย (รายการเดียวกันปกติหน่วยเดียว)
					const by_uom = new Map();
					for (const row of list) by_uom.set(row.uom || "", (by_uom.get(row.uom || "") || 0) + (row.qty || 0));
					item.summary = [...by_uom].map(([uom, qty]) => `${fmt_qty(qty)} ${uom}`.trim()).join(" + ");
					const pending = usages.filter((u) => u.tone !== "green" && u.target !== null);
					const next = pending.length ? Math.min(...pending.map((u) => u.target)) : null;
					item.tone = prep_tone(next, usages.some((u) => u.tone !== "green"), day.value);
					const supply = props.supply?.[name];
					const uom = list[0].stock_uom || "";
					item.summary_title = [
						next !== null ? `${__("ต้องสั่งครั้งถัดไป")}: ${fmt_day(next)}` : __("ขอครบแล้ว"),
						supply ? supply_text(supply, uom) : "",
					]
						.filter(Boolean)
						.join("\n");
				} else {
					const load = load_cells(list);
					item.cells = load.cells;
					item.peak = load.peak;
					item.summary = __("สูงสุด {0} {1}", [fmt_qty(load.peak), type.unit]);
					item.summary_title = `${__("รวม")} ${fmt_qty(load.total)} ${type.key === "Labour" ? __("คน-วัน") : __("คัน-วัน")}`;
				}
				return item;
			})
			.sort((a, b) => (a.first ?? Infinity) - (b.first ?? Infinity) || a.label.localeCompare(b.label));
		result.push({ key: `g:${type.key}`, kind: "group", type, label: type.label, count: items.length, items });
	}
	return result;
});

const rows = computed(() => {
	const result = [];
	for (const group of groups.value) {
		result.push(group);
		if (collapsed.has(group.key)) continue;
		for (const item of group.items) {
			result.push(item);
			if (!collapsed.has(item.key)) result.push(...item.usages.map((u) => ({ ...u, type: item.type })));
		}
	}
	return result.map((row, i) => ({ ...row, y: i * props.rowHeight }));
});

const chart_height = computed(() => Math.max(rows.value.length * props.rowHeight, 1));

function toggle(row) {
	if (collapsed.has(row.key)) collapsed.delete(row.key);
	else collapsed.add(row.key);
}

function set_all(expanded) {
	collapsed.clear();
	if (!expanded) for (const group of groups.value) for (const item of group.items) collapsed.add(item.key);
}

function on_row_click(row) {
	if (row.kind === "usage") {
		if (row.task) emit("open-task", row.task.name);
	} else toggle(row);
}

const diamond = (cx, cy, r) => `M${cx},${cy - r} L${cx + r},${cy} L${cx},${cy + r} L${cx - r},${cy} z`;
const bar_x = (start) => x(start);
const bar_w = (start, end) => Math.max((end - start + 1) * props.ppd, 2);
const load_title = (item, cell) =>
	`${item.label} · ${cell.period.label || fmt_day(cell.period.start)}\n${__("สูงสุด {0} {1}", [
		fmt_qty(cell.max),
		item.type.unit,
	])}\n${__("รวม")} ${fmt_qty(cell.sum)} ${item.type.key === "Labour" ? __("คน-วัน") : __("คัน-วัน")}`;

// ---------- เลื่อนและขนาด (ชุดเดียวกับ Timeline: App เรียก scroll_to_day / viewport_width) ----------

function scroll_to_day(d) {
	if (!body.value) return;
	body.value.scrollLeft = Math.max(x(d) - 40, 0);
}

function viewport_width() {
	return Math.max((body.value?.clientWidth || 0) - left_width.value, 0);
}

let observer;
onMounted(() => {
	observer = new ResizeObserver(() => (viewport_width_px.value = body.value.clientWidth));
	observer.observe(body.value);
});
onBeforeUnmount(() => observer?.disconnect());

defineExpose({ body, scroll_to_day, viewport_width, set_all });
</script>

<template>
	<div ref="body" class="rg-body">
		<div v-if="!groups.length" class="rg-empty text-muted">
			<span v-html="icon('chart-gantt', 'lg')" />
			<div>{{ __("ยังไม่มีแผนทรัพยากรหรือวัสดุ") }}</div>
			<div class="small">
				{{ __("กลับไปมุมมองงาน แล้วคลิก WBS/ชื่องานเพื่อเพิ่มคน เครื่องจักร และวัสดุของงาน") }}
			</div>
		</div>
		<div v-else class="rg-inner" :style="{ width: left_width + width + 'px' }">
			<!-- หัว -->
			<div class="rg-head" :style="{ height: headerHeight + 'px' }">
				<div class="rg-corner" :style="{ width: left_width + 'px' }">
					<span>{{ __("ทรัพยากร") }}</span>
					<span class="rg-corner-actions">
						<button type="button" class="rg-link" @click="set_all(true)">{{ __("ขยาย") }}</button>
						<button type="button" class="rg-link" @click="set_all(false)">{{ __("ย่อ") }}</button>
					</span>
				</div>
				<svg :width="width" :height="headerHeight" class="rg-header">
					<g v-for="period in top_header" :key="'t' + period.start">
						<rect :x="period.x" y="0" :width="period.width" :height="headerHeight / 2" class="rg-header-cell" />
						<text :x="period.x + 6" :y="headerHeight / 2 - 8" class="rg-header-text">{{ period.label }}</text>
					</g>
					<g v-for="period in bottom_header" :key="'b' + period.start">
						<rect
							:x="period.x"
							:y="headerHeight / 2"
							:width="period.width"
							:height="headerHeight / 2"
							class="rg-header-cell"
						/>
						<text
							v-if="show_bottom_labels"
							:x="period.x + period.width / 2"
							:y="headerHeight - 8"
							class="rg-header-text"
							text-anchor="middle"
						>
							{{ period.label }}
						</text>
					</g>
				</svg>
			</div>

			<div class="rg-rows">
				<!-- ชื่อด้านซ้าย -->
				<div class="rg-names" :style="{ width: left_width + 'px' }">
					<div
						v-for="row in rows"
						:key="row.key"
						class="rg-name"
						:class="['rg-' + row.kind, { 'rg-hover': hovered === row.key }]"
						:style="{ height: rowHeight + 'px' }"
						:title="row.kind === 'usage' ? row.title : row.summary_title || ''"
						@click="on_row_click(row)"
						@mouseenter="hovered = row.key"
						@mouseleave="hovered = null"
					>
						<template v-if="row.kind === 'group'">
							<span
								class="rg-caret"
								v-html="icon(collapsed.has(row.key) ? 'chevron-right' : 'chevron-down', 'xs')"
							/>
							<span class="rg-icon" v-html="icon(row.type.icon)" />
							<span class="rg-label">{{ row.label }}</span>
							<span class="rg-count">{{ row.count }}</span>
						</template>
						<template v-else-if="row.kind === 'resource'">
							<span
								class="rg-caret"
								v-html="icon(collapsed.has(row.key) ? 'chevron-right' : 'chevron-down', 'xs')"
							/>
							<span class="rg-label">{{ row.label }}</span>
							<span class="rg-summary" :class="row.tone ? 'rg-tone-' + row.tone : ''">{{ row.summary }}</span>
						</template>
						<template v-else>
							<span class="rg-label">{{ row.label }}</span>
							<span class="rg-summary">{{ row.qty_text }}</span>
						</template>
					</div>
				</div>

				<!-- timeline -->
				<svg :width="width" :height="chart_height" class="rg-chart">
					<rect
						v-for="hx in holiday_rects"
						:key="'h' + hx"
						:x="hx"
						y="0"
						:width="ppd"
						:height="chart_height"
						class="rg-holiday"
					/>
					<line
						v-for="period in bottom_header"
						:key="'g' + period.start"
						:x1="period.x"
						:x2="period.x"
						y1="0"
						:y2="chart_height"
						class="rg-grid-line"
					/>
					<g
						v-for="row in rows"
						:key="row.key"
						:class="'rg-' + row.kind"
						@mouseenter="hovered = row.key"
						@mouseleave="hovered = null"
						@click="row.kind === 'usage' && on_row_click(row)"
					>
						<rect
							x="0"
							:y="row.y"
							:width="width"
							:height="rowHeight"
							class="rg-row-bg"
							:class="{ 'rg-hover': hovered === row.key }"
						/>
						<line x1="0" :x2="width" :y1="row.y + rowHeight" :y2="row.y + rowHeight" class="rg-row-line" />

						<!-- แรงงาน/เครื่องจักร: จำนวนสูงสุดต่อวันในแต่ละช่อง -->
						<template v-if="row.kind === 'resource' && row.cells">
							<g v-for="cell in row.cells" :key="cell.x" :class="'rg-load-' + row.type.key">
								<title>{{ load_title(row, cell) }}</title>
								<rect
									:x="cell.x + 1"
									:y="row.y + 6"
									:width="Math.max(cell.width - 2, 1)"
									:height="rowHeight - 12"
									rx="3"
									class="rg-load"
									:style="{ opacity: 0.25 + (0.75 * cell.max) / (row.peak || 1) }"
								/>
								<text
									v-if="cell.width >= 22"
									:x="cell.x + cell.width / 2"
									:y="row.y + rowHeight / 2 + 4"
									text-anchor="middle"
									class="rg-load-text"
								>
									{{ fmt_qty(cell.max) }}
								</text>
							</g>
						</template>

						<!-- วัสดุ: ช่วงที่ใช้ของทุกงาน และจุดวันต้องสั่ง -->
						<template v-else-if="row.kind === 'resource'">
							<template v-for="usage in row.usages" :key="usage.key">
								<rect
									v-if="usage.start !== null"
									:x="bar_x(usage.start)"
									:y="row.y + rowHeight / 2 - 3"
									:width="bar_w(usage.start, usage.end)"
									height="6"
									rx="3"
									class="rg-material-span"
								>
									<title>{{ usage.title }}</title>
								</rect>
								<path
									v-if="usage.target !== null"
									:d="diamond(x(usage.target) + ppd / 2, row.y + rowHeight / 2, 5)"
									class="rg-mark"
									:class="'rg-tone-' + usage.tone"
								>
									<title>{{ usage.title }}</title>
								</path>
							</template>
						</template>

						<!-- งานที่ใช้: เส้นเตรียมล่วงหน้า + แถบช่วงงาน -->
						<template v-else-if="row.kind === 'usage' && row.start !== null">
							<title>{{ row.title }}</title>
							<line
								v-if="row.target !== null && row.target < row.start"
								:x1="x(row.target) + ppd / 2"
								:x2="bar_x(row.start)"
								:y1="row.y + rowHeight / 2"
								:y2="row.y + rowHeight / 2"
								class="rg-lead"
								:class="'rg-tone-' + row.tone"
							/>
							<line
								v-if="row.required_by !== null && row.required_by < row.start"
								:x1="x(row.required_by) + ppd / 2"
								:x2="x(row.required_by) + ppd / 2"
								:y1="row.y + rowHeight / 2 - 5"
								:y2="row.y + rowHeight / 2 + 5"
								class="rg-required"
								:class="'rg-tone-' + row.tone"
							/>
							<rect
								:x="bar_x(row.start)"
								:y="row.y + 8"
								:width="bar_w(row.start, row.end)"
								:height="rowHeight - 16"
								:rx="(rowHeight - 16) / 2"
								class="rg-bar"
								:class="'rg-bar-' + row.type.key"
							/>
							<path
								v-if="row.target !== null"
								:d="diamond(x(row.target) + ppd / 2, row.y + rowHeight / 2, 4.5)"
								class="rg-mark"
								:class="'rg-tone-' + row.tone"
							/>
							<text
								:x="bar_x(row.start) + bar_w(row.start, row.end) + 6"
								:y="row.y + rowHeight / 2 + 4"
								class="rg-bar-text"
							>
								{{ row.qty_text }}
							</text>
						</template>
					</g>

					<line
						v-if="finish_x !== null"
						:x1="finish_x"
						:x2="finish_x"
						y1="0"
						:y2="chart_height"
						class="rg-finish"
					>
						<title>{{ __("สิ้นสุดสัญญา") }}</title>
					</line>
					<line v-if="today_x !== null" :x1="today_x" :x2="today_x" y1="0" :y2="chart_height" class="rg-today">
						<title>{{ __("วันนี้") }}</title>
					</line>
					<line
						v-if="status_x !== null"
						:x1="status_x"
						:x2="status_x"
						y1="0"
						:y2="chart_height"
						class="rg-status"
					>
						<title>{{ __("วันที่เลือกดู") }}</title>
					</line>
				</svg>
			</div>
		</div>
	</div>
</template>

<style scoped>
.rg-body {
	flex: 1 1 auto;
	min-width: 0;
	overflow: auto;
}
.rg-empty {
	display: flex;
	flex-direction: column;
	align-items: center;
	justify-content: center;
	gap: 6px;
	height: 100%;
	padding: 24px;
	text-align: center;
}
.rg-empty :deep(svg) {
	stroke: currentColor;
}
.rg-head {
	position: sticky;
	top: 0;
	z-index: 3;
	display: flex;
	background: var(--card-bg);
}
.rg-corner {
	position: sticky;
	left: 0;
	z-index: 4;
	flex: none;
	display: flex;
	align-items: flex-end;
	justify-content: space-between;
	padding: 0 10px 8px;
	background: var(--card-bg);
	border-right: 1px solid var(--border-color);
	border-bottom: 1px solid color-mix(in srgb, var(--border-color) 60%, transparent);
	font-size: var(--text-sm);
	font-weight: 600;
	color: var(--text-muted);
}
.rg-corner-actions {
	display: flex;
	gap: 8px;
}
.rg-link {
	padding: 0;
	border: none;
	background: none;
	color: var(--text-muted);
	font-size: var(--text-xs);
	font-weight: 400;
}
.rg-link:hover {
	color: var(--text-color);
	text-decoration: underline;
}
.rg-header {
	display: block;
	flex: none;
}
.rg-header-cell {
	fill: var(--card-bg);
	stroke: color-mix(in srgb, var(--border-color) 60%, transparent);
}
.rg-header-text {
	fill: var(--text-muted);
	font-size: 11px;
	font-weight: 500;
}
.rg-rows {
	display: flex;
}
.rg-names {
	position: sticky;
	left: 0;
	z-index: 2;
	flex: none;
	background: var(--card-bg);
	border-right: 1px solid var(--border-color);
}
.rg-name {
	display: flex;
	align-items: center;
	gap: 6px;
	padding: 0 10px;
	border-bottom: 1px solid color-mix(in srgb, var(--border-color) 45%, transparent);
	font-size: var(--text-sm);
	cursor: pointer;
	white-space: nowrap;
	overflow: hidden;
}
.rg-name.rg-hover {
	background: var(--consbiz-gantt-row-hover);
}
.rg-name.rg-group {
	background: var(--subtle-fg);
	font-weight: 600;
	color: var(--text-color);
}
.rg-name.rg-resource {
	padding-left: 22px;
	font-weight: 500;
}
.rg-name.rg-usage {
	padding-left: 44px;
	color: var(--text-muted);
}
.rg-caret,
.rg-icon {
	display: inline-flex;
	flex: none;
}
.rg-caret :deep(svg),
.rg-icon :deep(svg) {
	stroke: currentColor;
}
.rg-label {
	flex: 1 1 auto;
	min-width: 0;
	overflow: hidden;
	text-overflow: ellipsis;
}
.rg-count {
	flex: none;
	padding: 0 6px;
	border-radius: var(--radius-full, 999px);
	background: var(--control-bg);
	font-size: var(--text-xs);
	font-weight: 500;
	color: var(--text-muted);
}
.rg-summary {
	flex: none;
	font-size: var(--text-xs);
	color: var(--text-muted);
}
.rg-summary.rg-tone-red {
	color: var(--red-600);
}
.rg-summary.rg-tone-orange {
	color: var(--orange-600);
}
.rg-chart {
	display: block;
	flex: none;
}
.rg-holiday {
	fill: var(--consbiz-gantt-holiday);
}
.rg-grid-line {
	stroke: color-mix(in srgb, var(--border-color) 55%, transparent);
}
.rg-row-bg {
	fill: transparent;
}
.rg-group .rg-row-bg {
	fill: var(--subtle-fg);
	opacity: 0.6;
}
.rg-row-bg.rg-hover {
	fill: var(--consbiz-gantt-row-hover);
	opacity: 0.6;
}
.rg-usage {
	cursor: pointer;
}
.rg-row-line {
	stroke: color-mix(in srgb, var(--border-color) 45%, transparent);
}
.rg-load-Labour {
	--rg-color: var(--consbiz-gantt-bar);
}
.rg-load-Equipment {
	--rg-color: var(--purple-500);
}
.rg-load {
	fill: var(--rg-color);
}
.rg-load-text {
	font-size: 10px;
	font-weight: 600;
	fill: var(--text-color);
	paint-order: stroke;
	stroke: var(--card-bg);
	stroke-width: 3px;
	pointer-events: none;
}
.rg-material-span {
	fill: var(--gray-400);
	opacity: 0.7;
}
.rg-bar {
	opacity: 0.6;
}
.rg-bar-Labour {
	fill: var(--consbiz-gantt-bar);
}
.rg-bar-Equipment {
	fill: var(--purple-500);
}
.rg-bar-Material {
	fill: var(--gray-500);
}
.rg-bar-text {
	font-size: 11px;
	fill: var(--text-muted);
	pointer-events: none;
}
.rg-lead {
	stroke-width: 1.5;
	stroke-dasharray: 3 3;
	pointer-events: none;
}
.rg-required {
	stroke-width: 1.5;
	pointer-events: none;
}
.rg-mark {
	stroke: var(--card-bg);
	stroke-width: 1;
}
.rg-tone-gray {
	--rg-tone: var(--gray-500);
}
.rg-tone-green {
	--rg-tone: var(--consbiz-gantt-done);
}
.rg-tone-orange {
	--rg-tone: var(--consbiz-gantt-late);
}
.rg-tone-red {
	--rg-tone: var(--consbiz-gantt-critical);
}
.rg-mark.rg-tone-gray,
.rg-mark.rg-tone-green,
.rg-mark.rg-tone-orange,
.rg-mark.rg-tone-red {
	fill: var(--rg-tone);
}
.rg-lead,
.rg-required {
	stroke: var(--rg-tone);
}
.rg-today {
	stroke: var(--consbiz-gantt-today);
	stroke-width: 1.5;
}
.rg-finish {
	stroke: var(--consbiz-gantt-finish);
	stroke-width: 1.5;
}
.rg-status {
	stroke: var(--consbiz-gantt-status-date);
	stroke-width: 1.5;
	stroke-dasharray: 6 3;
}
</style>
