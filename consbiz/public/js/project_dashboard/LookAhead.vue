<script setup>
// Tab "Look-ahead": แผนงานระยะสั้นรายวัน (สัปดาห์ที่แล้ว / สัปดาห์นี้ / สัปดาห์หน้า / ...) จัดกลุ่มตาม WBS ระดับบน
// แต่ละวันเป็นกล่องสีตามสถานะของวัน (เทียบ "ณ วันที่" ที่เลือก) วันหยุดแรเงา, ขวามือ: สถานะ/% และทรัพยากร/ขอตรวจที่ค้าง
//   ทำแล้ว (เขียว) / ไม่ได้ทำตามแผน (แดง) / วันที่ดู (ฟ้าเข้ม) / แผนข้างหน้า (ฟ้าอ่อน)
//   ทำนอกแผน (ขอบประเขียว) / แผนหลังงานเสร็จ 100% (เทา) มีเส้นแบ่งทุกวัน เส้นเข้มขึ้นที่ต้นสัปดาห์
// ข้อมูลจาก construction_management/lookahead.py พิมพ์ได้ (A4 แนวนอน) ด้วยสไตล์ชุดเดียวกับหน้าจอ
import { computed, onMounted, ref } from "vue";
import FrappeControl from "../construction_management/components/FrappeControl.vue";
import { date, percent } from "./format";

const API = "consbiz.consbiz.doctype.construction_management.lookahead.get_lookahead";
const WEEK_OPTIONS = [2, 3, 4, 6];
// สีหัวสัปดาห์ตามลำดับ (สัปดาห์ที่แล้ว = เทา, สัปดาห์นี้ = ฟ้า, ถัดไป = ส้ม, เขียว, ม่วง ...)
const WEEK_TONES = ["gray", "blue", "orange", "green", "purple", "cyan", "pink", "yellow", "gray"];

const props = defineProps({ name: String });

const data = ref(null);
const loading = ref(false);
const status_date = ref(frappe.datetime.get_today());
const weeks = ref(3);
const include_last_week = ref(true);
const search = ref("");
const table = ref(null);

async function load() {
	loading.value = true;
	try {
		const { message } = await frappe.call(API, {
			name: props.name,
			date: status_date.value,
			weeks: weeks.value,
			include_last_week: include_last_week.value ? 1 : 0,
		});
		data.value = message;
	} finally {
		loading.value = false;
	}
}
defineExpose({ load });
onMounted(load);

function set_date(value) {
	if (!value || value === status_date.value) return;
	status_date.value = value;
	load();
}
function set_weeks(value) {
	weeks.value = value;
	load();
}
function toggle_last_week() {
	include_last_week.value = !include_last_week.value;
	load();
}

const locale = frappe.boot.lang === "th" ? "th-TH" : undefined;
const weekday_fmt = new Intl.DateTimeFormat(locale, { weekday: "narrow" });
const obj = (day) => frappe.datetime.str_to_obj(day);

// คอลัมน์รายวันและหัวสัปดาห์
const days = computed(() => {
	if (!data.value) return [];
	const holidays = new Set(data.value.holidays);
	const result = [];
	for (let day = data.value.start; day <= data.value.end; day = frappe.datetime.add_days(day, 1)) {
		result.push({
			day,
			number: obj(day).getDate(),
			weekday: weekday_fmt.format(obj(day)),
			holiday: holidays.has(day),
			today: day === data.value.today,
			week_start: obj(day).getDay() === 1,
		});
	}
	return result;
});

const week_groups = computed(() => {
	if (!data.value) return [];
	const groups = [];
	for (let i = 0; i < days.value.length; i += 7) {
		const first = days.value[i].day;
		const offset = Math.round((obj(first) - obj(data.value.this_week)) / (7 * 86400000));
		const label =
			offset === -1
				? __("สัปดาห์ที่แล้ว")
				: offset === 0
				? __("สัปดาห์นี้")
				: offset === 1
				? __("สัปดาห์หน้า")
				: __("อีก {0} สัปดาห์", [offset]);
		groups.push({
			key: first,
			label,
			range: `${date(first)} – ${date(days.value[Math.min(i + 6, days.value.length - 1)].day)}`,
			tone: WEEK_TONES[offset + 1] || "gray",
		});
	}
	return groups;
});

// แถวงานกรองด้วยคำค้น (WBS หรือชื่องาน)
const groups = computed(() => {
	if (!data.value) return [];
	const text = search.value.trim().toLowerCase();
	return data.value.groups
		.map((group) => ({
			...group,
			tasks: group.tasks
				.filter((t) => !text || `${t.wbs} ${t.item_name}`.toLowerCase().includes(text))
				.map((task) => ({ ...task, cells: cells_of(task) })),
		}))
		.filter((group) => group.tasks.length);
});

// ช่องรายวันของงาน: สถานะของวัน + ข้อความเมื่อชี้ (วันที่หลัง "ณ วันที่" ถือเป็นอนาคต ไม่นับงานที่ลงไว้)
const DAY_STATES = {
	done: __("ทำแล้ว"),
	missed: __("ไม่ได้ทำตามแผน"),
	current: __("แผนวันที่ดู"),
	planned: __("แผนข้างหน้า"),
	extra: __("ทำนอกแผน"),
	complete: __("งานเสร็จแล้ว"),
};

function day_state(task, day, planned, worked) {
	const ref = data.value.date;
	const finished = task.finished_on && task.finished_on <= ref && day > task.finished_on;
	if (worked) return planned ? "done" : "extra";
	if (!planned) return null;
	if (finished) return "complete";
	if (day < ref) return "missed";
	return day === ref ? "current" : "planned";
}

const fmt_qty = (value) => format_number(value || 0, null, value % 1 ? 2 : 0);

function cells_of(task) {
	const planned = new Set(task.days);
	return days.value.map((d) => {
		const work = d.day <= data.value.date ? task.work?.[d.day] : null;
		const state = day_state(task, d.day, planned.has(d.day), Boolean(work));
		return {
			...d,
			state,
			title: state
				? [
						`${date(d.day)} · ${DAY_STATES[state]}`,
						work
							? task.uom && work.qty
								? __("ทำได้ {0} {1} ({2})", [fmt_qty(work.qty), task.uom, percent(work.percent)])
								: __("ทำได้ {0}", [percent(work.percent)])
							: "",
						work?.refs?.length ? work.refs.join(", ") : "",
				  ]
						.filter(Boolean)
						.join("\n")
				: "",
		};
	});
}

const summary = computed(() => {
	const tasks = (data.value?.groups || []).flatMap((g) => g.tasks);
	return {
		total: tasks.length,
		overdue: tasks.filter((t) => t.overdue || t.status === "overdue").length,
		late: tasks.filter((t) => ["behind", "not_started"].includes(t.status)).length,
		critical: tasks.filter((t) => t.critical && t.status !== "done").length,
	};
});

function open_task_report() {
	frappe.set_route("query-report", "Construction Delay Analysis", {
		construction_management: props.name,
		date: status_date.value,
	});
}

function open_inspection(name) {
	frappe.set_route("Form", "Inspection Request", name);
}

// พิมพ์: คัดลอกสไตล์ทั้งหมดของหน้า (ตัวแปรสีของ Frappe + สไตล์ .la) ไปหน้าต่างใหม่ แล้วพิมพ์แนวนอน
function print() {
	const win = window.open("", "_blank");
	if (!win) return;
	const styles = [...document.querySelectorAll("link[rel='stylesheet'], style")]
		.map((el) => el.outerHTML)
		.join("");
	const title = frappe.utils.escape_html(
		`${__("Look-ahead {0} สัปดาห์", [weeks.value])} · ${cur_frm?.doc?.name || props.name}`
	);
	win.document.write(`<!doctype html><html><head><meta charset="utf-8"><title>${title}</title>${styles}
		<style>
			@page { size: A4 landscape; margin: 8mm; }
			body { display: block !important; background: #fff; padding: 0; margin: 0; }
			.la-print-title { font-size: 16px; font-weight: 700; margin-bottom: 4px; }
			.la-print-sub { color: #666; font-size: 11px; margin-bottom: 8px; }
			.la-scroll { overflow: visible !important; }
			.la-table { font-size: 10px; }
			.la-table, .la-card { box-shadow: none !important; }
		</style></head><body class="la-printing">
		<div class="la-print-title">${title}</div>
		<div class="la-print-sub">${__("ณ วันที่")} ${date(status_date.value)} · ${date(data.value.start)} – ${date(
		data.value.end
	)}</div>
		<div class="la">${table.value.outerHTML}</div>
		<div class="la-print-sub" style="margin-top:8px">${legend_text()}</div>
		</body></html>`);
	win.document.close();
	win.onload = () => {
		win.focus();
		win.print();
	};
}

function legend_text() {
	return [
		__("เขียว = ทำแล้ว"),
		__("แดง = ไม่ได้ทำตามแผน"),
		__("ฟ้าเข้ม = แผนวันที่ดู"),
		__("ฟ้าอ่อน = แผนข้างหน้า"),
		__("ขอบประ = ทำนอกแผน"),
		__("เทา = งานเสร็จแล้ว"),
		__("ช่องแรเงา = วันหยุด"),
	].join(" · ");
}
</script>

<template>
	<div class="la">
		<div class="la-toolbar">
			<div class="la-group">
				<span class="text-muted">{{ __("ณ วันที่") }}</span>
				<FrappeControl
					class="la-date"
					:df="{ fieldtype: 'Date' }"
					:model-value="status_date"
					@update:model-value="set_date"
				/>
				<button type="button" class="la-chip" @click="set_date(frappe.datetime.get_today())">
					{{ __("วันนี้") }}
				</button>
			</div>
			<div class="la-segment" role="group" :aria-label="__('จำนวนสัปดาห์')">
				<button
					v-for="option in WEEK_OPTIONS"
					:key="option"
					type="button"
					:class="{ active: weeks === option }"
					@click="set_weeks(option)"
				>
					{{ __("{0} สัปดาห์", [option]) }}
				</button>
			</div>
			<button type="button" class="la-chip" :class="{ 'la-chip-on': include_last_week }" @click="toggle_last_week">
				<span v-html="frappe.utils.icon(include_last_week ? 'check' : 'plus', 'xs')" />
				{{ __("รวมสัปดาห์ที่แล้ว") }}
			</button>
			<div class="la-search">
				<span v-html="frappe.utils.icon('search', 'sm')" />
				<input v-model="search" type="search" class="form-control" :placeholder="__('ค้นหา WBS / ชื่องาน')" />
			</div>
			<button type="button" class="la-chip la-print-btn" :disabled="!data" @click="print">
				<span v-html="frappe.utils.icon('printer', 'sm')" />{{ __("พิมพ์") }}
			</button>
		</div>

		<div v-if="data" class="la-summary">
			<span class="pd-pill pd-tone-blue">{{ __("งานในช่วง {0}", [summary.total]) }}</span>
			<span class="pd-pill" :class="summary.overdue ? 'pd-tone-red' : 'pd-tone-gray'">
				{{ __("ควรเสร็จแล้ว {0}", [summary.overdue]) }}
			</span>
			<span class="pd-pill" :class="summary.late ? 'pd-tone-orange' : 'pd-tone-gray'">
				{{ __("ช้ากว่าแผน {0}", [summary.late]) }}
			</span>
			<span class="pd-pill" :class="summary.critical ? 'pd-tone-red' : 'pd-tone-gray'">
				{{ __("งานวิกฤต {0}", [summary.critical]) }}
			</span>
			<a class="la-link" href="#" @click.prevent="open_task_report">{{ __("วิเคราะห์ความล่าช้า") }} →</a>
		</div>

		<div v-if="!data" class="la-skeleton" />
		<div v-else class="la-card" :class="{ 'pd-loading': loading }">
			<div class="la-scroll">
				<table ref="table" class="la-table">
					<thead>
						<tr class="la-week-row">
							<th rowspan="2" class="la-name-col la-sticky">{{ __("งาน / กิจกรรม") }}</th>
							<th
								v-for="week in week_groups"
								:key="week.key"
								colspan="7"
								class="la-week"
							>
								<span class="la-week-chip" :class="`la-tone-${week.tone}`">
									<strong>{{ week.label }}</strong>
									<small>{{ week.range }}</small>
								</span>
							</th>
							<th rowspan="2" class="la-status-col la-sticky-end">{{ __("สถานะ / หมายเหตุ") }}</th>
						</tr>
						<tr class="la-day-row">
							<th
								v-for="d in days"
								:key="d.day"
								class="la-day"
								:class="{ 'la-holiday': d.holiday, 'la-today': d.today, 'la-week-start': d.week_start }"
								:title="date(d.day)"
							>
								<span class="la-weekday">{{ d.weekday }}</span>
								<span class="la-daynum">{{ d.number }}</span>
							</th>
						</tr>
					</thead>
					<tbody v-for="group in groups" :key="group.wbs">
						<tr class="la-group-row">
							<td class="la-name-col la-sticky">
								<span class="la-group-wbs">{{ group.wbs }}</span>{{ group.label }}
								<span class="la-group-count">{{ group.tasks.length }}</span>
							</td>
							<td :colspan="days.length" />
							<td class="la-status-col la-sticky-end" />
						</tr>
						<tr v-for="task in group.tasks" :key="task.name" class="la-task-row">
							<td class="la-name-col la-sticky">
								<div class="la-task">
									<span class="la-wbs">{{ task.wbs }}</span>
									<div class="la-task-main">
										<div class="la-task-name" :title="task.item_name">{{ task.item_name }}</div>
										<div class="la-task-sub">
											<template v-if="task.overdue">
												<span class="la-text-red">← {{ __("ค้างจาก {0}", [date(task.end_date)]) }}</span>
											</template>
											<template v-else>{{ date(task.start_date) }} – {{ date(task.end_date) }}</template>
										</div>
									</div>
								</div>
							</td>
							<td
								v-for="cell in task.cells"
								:key="cell.day"
								class="la-cell"
								:class="{
									'la-holiday': cell.holiday,
									'la-today': cell.today,
									'la-week-start': cell.week_start,
								}"
							>
								<span v-if="cell.state" class="la-box" :class="`la-box-${cell.state}`" :title="cell.title" />
							</td>
							<td class="la-status-col la-sticky-end">
								<div class="la-status">
									<span class="pd-pill pd-pill-sm" :class="`pd-tone-${task.status_color}`">
										{{ task.status_label }}
									</span>
									<div class="la-progress" :title="`${__('แผน')} ${percent(task.plan_pct)}`">
										<div class="la-progress-track">
											<div class="la-progress-plan" :style="{ width: Math.min(task.plan_pct, 100) + '%' }" />
											<div class="la-progress-actual" :style="{ width: Math.min(task.actual_pct, 100) + '%' }" />
										</div>
										<span>{{ percent(task.actual_pct) }}</span>
									</div>
								<div
									v-if="task.resources.length || task.inspections.length || (task.critical && task.status !== 'done')"
									class="la-notes"
								>
									<span v-if="task.critical && task.status !== 'done'" class="pd-pill pd-pill-sm pd-tone-red">
										{{ __("วิกฤต") }}
									</span>
									<a
										v-for="inspection in task.inspections"
										:key="inspection.name"
										href="#"
										class="pd-pill pd-pill-sm"
										:class="inspection.result === 'Failed' ? 'pd-tone-red' : 'pd-tone-orange'"
										@click.prevent="open_inspection(inspection.name)"
									>
										{{ inspection.result === "Failed" ? __("ตรวจไม่ผ่าน") : __("รอตรวจ") }}
									</a>
									<span v-for="resource in task.resources" :key="resource" class="la-resource">
										{{ resource }}
									</span>
								</div>
								</div>
							</td>
						</tr>
					</tbody>
					<tbody v-if="!groups.length">
						<tr>
							<td :colspan="days.length + 2" class="la-empty">
								{{ search ? __("ไม่พบงานที่ค้นหา") : __("ไม่มีงานในช่วงนี้") }}
							</td>
						</tr>
					</tbody>
				</table>
			</div>
		</div>

		<div v-if="data" class="la-legend">
			<span v-for="(label, key) in DAY_STATES" :key="key">
				<i class="la-box la-legend-box" :class="`la-box-${key}`" />{{ label }}
			</span>
			<span><i class="la-legend-holiday" />{{ __("วันหยุด") }}</span>
			<span><i class="la-legend-today" />{{ __("วันนี้") }}</span>
		</div>
	</div>
</template>

<style>
/* ไม่ scoped: หน้าพิมพ์คัดลอกสไตล์นี้ไปใช้กับตารางที่คัดลอกไป */
.la {
	--la-day: 28px;
	--la-row: 44px;
	--la-line: color-mix(in srgb, var(--border-color) 55%, transparent);
	--la-plan: var(--consbiz-gantt-plan);
	--la-done: var(--consbiz-gantt-done);
	--la-critical: var(--consbiz-gantt-critical);
	padding: var(--padding-sm) 0 var(--padding-xl);
}
.la-tone-gray {
	--la-tone: var(--gray-500);
}
.la-tone-blue {
	--la-tone: var(--blue-500);
}
.la-tone-orange {
	--la-tone: var(--orange-500);
}
.la-tone-green {
	--la-tone: var(--green-500);
}
.la-tone-purple {
	--la-tone: var(--purple-500);
}
.la-tone-cyan {
	--la-tone: var(--cyan-500, var(--blue-400));
}
.la-tone-pink {
	--la-tone: var(--pink-500, var(--red-400));
}
.la-tone-yellow {
	--la-tone: var(--yellow-500);
}

/* แถบเครื่องมือ */
.la-toolbar {
	display: flex;
	flex-wrap: wrap;
	align-items: center;
	gap: 8px;
	margin-bottom: 14px;
}
.la-group {
	display: flex;
	align-items: center;
	gap: 8px;
	padding: 4px 4px 4px 14px;
	border: 1px solid var(--la-line);
	border-radius: var(--radius);
	background: var(--card-bg);
}
.la-date .form-control {
	width: 120px;
	height: 30px;
	border-radius: var(--radius);
}
.la-chip,
.la-segment button {
	display: inline-flex;
	align-items: center;
	gap: 6px;
	height: 32px;
	padding: 0 14px;
	border: 1px solid var(--la-line);
	border-radius: var(--radius);
	background: var(--card-bg);
	color: var(--text-color);
	font-size: var(--text-sm);
	font-weight: 500;
	white-space: nowrap;
}
.la-group .la-chip {
	border-color: transparent;
	background: var(--control-bg);
}
.la-chip:hover,
.la-segment button:hover {
	background: var(--fg-hover-color);
}
.la-chip-on {
	border-color: color-mix(in srgb, var(--la-plan) 40%, transparent);
	background: color-mix(in srgb, var(--la-plan) 10%, transparent);
	color: var(--la-plan);
}
.la-chip svg {
	stroke: currentColor;
}
.la-segment {
	display: inline-flex;
	gap: 2px;
	padding: 2px;
	border-radius: var(--radius);
	background: var(--control-bg);
}
.la-segment button {
	height: 26px;
	padding: 0 12px;
	border: none;
	border-radius: var(--radius-sm);
	background: transparent;
	color: var(--text-muted);
}
.la-segment button.active {
	background: var(--card-bg);
	color: var(--text-color);
	font-weight: 600;
	box-shadow: var(--shadow-sm);
}
.la-search {
	display: flex;
	flex: 1 1 200px;
	align-items: center;
	gap: 6px;
	max-width: 280px;
	padding-left: 12px;
	border: 1px solid var(--la-line);
	border-radius: var(--radius);
	background: var(--card-bg);
	color: var(--text-muted);
}
.la-search .form-control {
	height: 32px;
	border: none;
	background: transparent;
	box-shadow: none;
}
.la-print-btn {
	margin-left: auto;
}
.la-summary {
	display: flex;
	flex-wrap: wrap;
	align-items: center;
	gap: 8px;
	margin-bottom: 14px;
}
.la-link {
	margin-left: auto;
	color: var(--text-muted);
	font-size: var(--text-sm);
}

/* การ์ดและตาราง */
.la-card {
	overflow: hidden;
	border: 1px solid var(--la-line);
	border-radius: 16px;
	background: var(--card-bg);
	box-shadow:
		0 1px 2px rgb(0 0 0 / 0.04),
		0 4px 16px rgb(0 0 0 / 0.04);
	transition: opacity 0.2s;
}
.la-scroll {
	overflow-x: auto;
}
.la-table {
	width: max-content;
	min-width: 100%;
	border-collapse: separate;
	border-spacing: 0;
	font-size: var(--text-sm);
}
.la-table th,
.la-table td {
	border-bottom: 1px solid var(--la-line);
	background: var(--card-bg);
}
.la-sticky {
	position: sticky;
	left: 0;
	z-index: 2;
	box-shadow: 1px 0 0 var(--la-line);
}
.la-name-col {
	width: 270px;
	min-width: 270px;
	max-width: 270px;
	padding: 0 16px;
	text-align: left;
}
.la-status-col {
	width: 230px;
	min-width: 230px;
	max-width: 230px;
	padding: 6px 14px;
	text-align: left;
}
/* ตรึงคอลัมน์สถานะไว้ขวา เลื่อนเฉพาะช่องวันที่ */
.la-sticky-end {
	position: sticky;
	right: 0;
	z-index: 2;
	box-shadow: -1px 0 0 var(--la-line);
}
thead th {
	color: var(--text-muted);
	font-size: var(--text-xs);
	font-weight: 600;
	vertical-align: bottom;
}
.la-week-row th {
	padding-top: 12px;
	padding-bottom: 6px;
	border-bottom: none;
}
.la-week {
	padding: 12px 3px 6px;
}
.la-week-chip {
	display: flex;
	flex-direction: column;
	align-items: center;
	gap: 1px;
	padding: 5px 8px;
	border-radius: 10px;
	background: color-mix(in srgb, var(--la-tone) 14%, transparent);
	color: color-mix(in srgb, var(--la-tone) 85%, var(--text-color));
}
.la-week-chip strong {
	font-size: var(--text-sm);
}
.la-week-chip small {
	font-size: 10px;
	opacity: 0.8;
}
.la-day {
	width: var(--la-day);
	min-width: var(--la-day);
	padding: 4px 0 8px;
	text-align: center;
}
.la-weekday,
.la-daynum {
	display: block;
	line-height: 1.3;
}
.la-daynum {
	color: var(--heading-color);
	font-size: var(--text-sm);
	font-weight: 700;
}
.la-day.la-today .la-daynum {
	display: inline-block;
	min-width: 22px;
	border-radius: 999px;
	background: var(--consbiz-gantt-today);
	color: var(--neutral-white, #fff);
}
/* เส้นแบ่งวัน (ทุกช่อง) และเส้นเข้มที่ต้นสัปดาห์ */
.la-day,
.la-cell {
	box-shadow: inset 1px 0 0 var(--la-line);
}
.la-day.la-week-start,
.la-cell.la-week-start {
	box-shadow: inset 1.5px 0 0 color-mix(in srgb, var(--border-color) 100%, var(--gray-500) 35%);
}

/* แถวกลุ่ม */
.la-group-row td {
	height: 34px;
	background: var(--subtle-fg);
	color: var(--heading-color);
	font-weight: 700;
}
.la-group-wbs {
	margin-right: 8px;
	color: var(--text-muted);
}
.la-group-count {
	margin-left: 8px;
	padding: 0 8px;
	border-radius: 999px;
	background: var(--control-bg);
	color: var(--text-muted);
	font-size: var(--text-xs);
}

/* แถวงาน */
.la-task-row td {
	height: var(--la-row);
}
.la-task-row:hover td {
	background: color-mix(in srgb, var(--consbiz-gantt-row-hover) 60%, var(--card-bg));
}
.la-task {
	display: flex;
	align-items: center;
	gap: 10px;
	min-width: 0;
}
.la-wbs {
	flex: none;
	min-width: 44px;
	padding: 3px 6px;
	border-radius: 8px;
	background: var(--subtle-fg);
	color: var(--text-muted);
	font-size: var(--text-xs);
	font-weight: 600;
	text-align: center;
	font-variant-numeric: tabular-nums;
}
.la-task-main {
	min-width: 0;
}
.la-task-name {
	overflow: hidden;
	color: var(--heading-color);
	font-weight: 500;
	text-overflow: ellipsis;
	white-space: nowrap;
}
.la-task-sub {
	color: var(--text-muted);
	font-size: var(--text-xs);
	font-variant-numeric: tabular-nums;
}
.la-text-red {
	color: var(--red-600);
}

/* ช่องรายวัน */
.la-cell {
	position: relative;
	padding: 0;
}
.la-holiday {
	background-image: repeating-linear-gradient(
		135deg,
		transparent 0 5px,
		color-mix(in srgb, var(--gray-500) 12%, transparent) 5px 10px
	) !important;
}
td.la-today {
	background-color: color-mix(in srgb, var(--consbiz-gantt-today) 6%, var(--card-bg));
}
/* กล่องรายวัน: เว้นขอบ 2px ให้เห็นเป็นช่องแยกกัน */
.la-box {
	position: absolute;
	inset: 50% 2px auto;
	display: grid;
	place-items: center;
	height: 18px;
	margin-top: -9px;
	border-radius: 4px;
	color: var(--neutral-white, #fff);
	font-size: 11px;
	font-weight: 700;
	line-height: 1;
}
.la-box-done {
	background: var(--green-500);
}
.la-box-missed {
	background: var(--red-500);
}
.la-box-current {
	background: var(--blue-500);
	box-shadow: 0 0 0 2px color-mix(in srgb, var(--blue-500) 35%, transparent);
}
.la-box-planned {
	background: color-mix(in srgb, var(--blue-500) 28%, transparent);
}
.la-box-extra {
	border: 1.5px dashed var(--green-600);
	background: color-mix(in srgb, var(--green-500) 14%, transparent);
	color: var(--green-700, var(--green-600));
}
.la-box-complete {
	background: color-mix(in srgb, var(--gray-500) 30%, transparent);
}

/* สถานะและหมายเหตุ */
.la-status {
	display: grid;
	grid-template-columns: minmax(0, 1fr) auto;
	align-items: center;
	gap: 4px 8px;
}
.la-status .pd-pill {
	justify-self: start;
	overflow: hidden;
	max-width: 100%;
	text-overflow: ellipsis;
}
.la-status .la-notes {
	grid-column: 1 / -1;
}
/* % อยู่บรรทัดเดียวกับป้ายสถานะ แถบความคืบหน้าบางๆ อยู่ใต้ทั้งสองอย่าง */
.la-progress {
	display: contents;
	font-size: var(--text-xs);
	font-weight: 600;
	font-variant-numeric: tabular-nums;
}
.la-progress-track {
	position: relative;
	grid-row: 2;
	grid-column: 1 / -1;
	height: 4px;
	overflow: hidden;
	border-radius: 999px;
	background: var(--control-bg);
}
.la-progress-plan,
.la-progress-actual {
	position: absolute;
	inset: 0 auto 0 0;
	border-radius: inherit;
}
.la-progress-plan {
	background: color-mix(in srgb, var(--la-plan) 30%, transparent);
}
.la-progress-actual {
	background: var(--la-done);
}
.la-notes {
	display: flex;
	flex-wrap: wrap;
	gap: 4px;
	padding: 4px 0;
}
.la-resource {
	padding: 2px 8px;
	border-radius: 999px;
	background: var(--subtle-fg);
	color: var(--text-color);
	font-size: var(--text-xs);
	white-space: nowrap;
}
.la-empty {
	padding: 32px !important;
	color: var(--text-muted);
	text-align: center;
}

/* คำอธิบายสัญลักษณ์ */
.la-legend {
	display: flex;
	flex-wrap: wrap;
	gap: 6px 18px;
	margin-top: 12px;
	color: var(--text-muted);
	font-size: var(--text-xs);
}
.la-legend span {
	display: inline-flex;
	align-items: center;
	gap: 6px;
}
.la-legend i {
	display: inline-block;
	width: 22px;
	height: 10px;
	border-radius: 999px;
}
.la-legend .la-legend-box {
	position: static;
	display: inline-grid;
	width: 18px;
	height: 16px;
	margin: 0;
	border-radius: 4px;
	font-size: 10px;
	font-style: normal;
}
.la-legend-holiday {
	border-radius: 3px !important;
	background: repeating-linear-gradient(
		135deg,
		transparent 0 3px,
		color-mix(in srgb, var(--gray-500) 25%, transparent) 3px 6px
	);
	box-shadow: inset 0 0 0 1px var(--la-line);
}
.la-legend-today {
	width: 10px !important;
	background: var(--consbiz-gantt-today);
}
.la-skeleton {
	height: 420px;
	border-radius: 16px;
	background: linear-gradient(90deg, var(--control-bg), var(--subtle-fg), var(--control-bg));
	background-size: 200% 100%;
	animation: la-shimmer 1.2s ease-in-out infinite;
}
@keyframes la-shimmer {
	to {
		background-position: -200% 0;
	}
}

/* หน้าพิมพ์ */
.la-printing .la-sticky,
.la-printing .la-sticky-end {
	position: static;
}
.la-printing .la-name-col {
	width: 240px;
	min-width: 240px;
	max-width: 240px;
	padding: 0 8px;
}
.la-printing .la-task-name,
.la-printing .la-task-sub {
	font-size: 9px;
	white-space: nowrap;
}
.la-printing .la-wbs {
	min-width: 34px;
	font-size: 9px;
}
.la-printing .la-status-col {
	width: 190px;
	min-width: 190px;
	max-width: 190px;
}
.la-printing .la {
	--la-day: 20px;
	--la-row: 30px;
}
@media print {
	.la-table th,
	.la-table td,
	.la-box,
	.la-week-chip,
	.la-holiday,
	.pd-pill {
		-webkit-print-color-adjust: exact;
		print-color-adjust: exact;
	}
}
</style>
