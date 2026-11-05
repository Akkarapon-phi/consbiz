<template>
	<div>
		<TopBar title="Look-ahead" :subtitle="state.project?.project_name">
			<template #actions>
				<button
					type="button"
					class="ss-icon-btn"
					:class="{ 'is-spinning': loading }"
					aria-label="โหลดใหม่"
					@click="load"
				>
					<Icon name="refresh" :size="20" />
				</button>
			</template>
		</TopBar>

		<div class="ss-content">
			<Skeleton v-if="data === null" :rows="4" />
			<Empty
				v-else-if="data === false"
				icon="layers"
				title="โครงการนี้ยังไม่มีแผนงาน"
				text="สร้างแผนงานก่อสร้างของโครงการในระบบเต็มก่อน"
			/>
			<template v-else>
				<!-- เลือกสัปดาห์ (สัปดาห์ที่แล้ว + 3 สัปดาห์ข้างหน้า ตามแผนปัจจุบัน) -->
				<div v-if="!xl" class="ss-filters">
					<button
						v-for="w in weeks"
						:key="w.start"
						type="button"
						class="ss-filter"
						:class="{ 'is-active': week === w.start }"
						@click="choose_week(w.start)"
					>
						{{ w.label }} <span class="ss-filter-count">{{ w.range }}</span>
					</button>
				</div>

				<div class="ss-cal-summary">
					<span class="ss-tag tone-blue">{{ summary.total }} งาน</span>
					<span v-if="summary.late" class="ss-tag tone-amber">ช้ากว่าแผน {{ summary.late }}</span>
					<span v-if="summary.overdue" class="ss-tag tone-rose"
						>เลยกำหนด {{ summary.overdue }}</span
					>
					<span v-if="summary.critical" class="ss-tag tone-rose"
						><Icon name="flag" :size="12" /> วิกฤต {{ summary.critical }}</span
					>
				</div>

				<!-- แท็บเล็ต/จอใหญ่: ตารางงาน × วัน (แท็บเล็ต 2 สัปดาห์, จอใหญ่ทั้งช่วง 4 สัปดาห์) -->
				<div v-if="wide && groups.length" class="ss-la-table" :style="{ '--n': days.length }">
					<div class="ss-la-tr ss-la-weeks">
						<div class="ss-la-corner"></div>
						<div
							v-for="w in shown_weeks"
							:key="w.start"
							class="ss-la-week"
							:class="{ 'is-current': w.start === String(data.this_week) }"
							:style="{ gridColumn: `span ${w.days}` }"
						>
							<b>{{ w.label }}</b> {{ w.range }}
						</div>
					</div>
					<div class="ss-la-tr ss-la-thead">
						<div class="ss-la-corner">งาน</div>
						<div
							v-for="d in days"
							:key="d.date"
							class="ss-la-th"
							:class="{
								'is-today': d.date === String(data.today),
								'is-holiday': d.holiday,
								'is-week-start': d.monday,
							}"
						>
							<small>{{ d.dow }}</small
							><b>{{ d.num }}</b>
						</div>
					</div>
					<template v-for="group in groups" :key="`t-${group.wbs}-${group.label}`">
						<div class="ss-la-tr ss-la-group">
							<i class="ss-wbs">{{ group.wbs }}</i> {{ group.label }}
							<span>{{ group.tasks.length }} งาน</span>
						</div>
						<div
							v-for="t in group.tasks"
							:key="t.name"
							class="ss-la-tr"
							:class="{ 'is-late': t.overdue || t.status === 'overdue' }"
						>
							<div class="ss-la-name">
								<span class="ss-la-title">
									<i class="ss-wbs">{{ t.wbs }}</i> {{ t.item_name }}
									<Icon v-if="t.critical" name="flag" :size="13" class="ss-la-critical" />
								</span>
								<span class="ss-la-sub">
									<span class="ss-tag" :class="`tone-${STATUS_TONE[t.status] || 'gray'}`">{{
										t.status_label
									}}</span>
									<span
										>{{ pct(t.actual_pct) }}% · {{ thai_date(t.start_date) }} –
										{{ thai_date(t.end_date) }}</span
									>
								</span>
								<span v-if="t.resources?.length" class="ss-la-res">{{
									t.resources.join(" · ")
								}}</span>
							</div>
							<div
								v-for="cell in cells(t)"
								:key="cell.date"
								class="ss-la-cell"
								:class="{
									'is-today': cell.date === String(data.today),
									'is-holiday': cell.holiday,
									'is-week-start': cell.monday,
								}"
							>
								<span
									v-if="cell.state"
									class="ss-la-box"
									:class="`is-${cell.state}`"
									:title="cell.title"
								></span>
							</div>
						</div>
					</template>
				</div>

				<div v-if="!wide" class="ss-la-days" aria-hidden="true">
					<span></span>
					<span
						v-for="day in week_days"
						:key="day.date"
						:class="{ 'is-today': day.date === data.today, 'is-holiday': day.holiday }"
						><small>{{ day.dow }}</small
						><b>{{ day.num }}</b></span
					>
				</div>

				<Empty v-if="!groups.length" icon="sparkles" title="ไม่มีงานตามแผนในสัปดาห์นี้" />
				<template v-for="group in wide ? [] : groups" :key="group.wbs + group.label">
					<h2 class="ss-section-title">
						<span
							><i class="ss-wbs">{{ group.wbs }}</i> {{ group.label }}</span
						>
						<span class="ss-section-total">{{ group.tasks.length }}</span>
					</h2>
					<div class="ss-list ss-list--form">
						<div
							v-for="(t, i) in group.tasks"
							:key="t.name"
							class="ss-card ss-la-task"
							:class="{ 'is-late': t.overdue || t.status === 'overdue' }"
							:style="{ '--i': i }"
						>
							<div class="ss-card-head">
								<span class="ss-card-main">
									<span class="ss-card-title">{{ t.item_name }}</span>
									<span class="ss-card-meta">
										<i class="ss-wbs">{{ t.wbs }}</i>
										{{ thai_date(t.start_date) }} – {{ thai_date(t.end_date) }}
										<span v-if="t.critical" class="ss-tag tone-rose"
											><Icon name="flag" :size="12" /> วิกฤต</span
										>
									</span>
								</span>
								<span class="ss-tag" :class="`tone-${STATUS_TONE[t.status] || 'gray'}`">{{
									t.status_label
								}}</span>
							</div>
							<div class="ss-la-row">
								<span class="ss-la-pct">{{ pct(t.actual_pct) }}%</span>
								<span
									v-for="cell in cells(t)"
									:key="cell.date"
									class="ss-la-box"
									:class="cell.state && `is-${cell.state}`"
									:title="cell.title"
								></span>
							</div>
							<div v-if="t.resources?.length || t.inspections?.length" class="ss-chips">
								<span v-for="r in t.resources.slice(0, 4)" :key="r" class="ss-chip">{{
									r
								}}</span>
								<span v-for="ir in t.inspections" :key="ir.name" class="ss-tag tone-teal"
									><Icon name="search-check" :size="12" /> {{ ir.name }}
									{{ ir.result === "Failed" ? "ไม่ผ่าน" : "รอตรวจ" }}</span
								>
							</div>
						</div>
					</div>
				</template>

				<div class="ss-cal-legend">
					<span v-for="(label, key) in DAY_STATES" :key="key"
						><i class="ss-la-box" :class="`is-${key}`"></i>{{ label }}</span
					>
				</div>
			</template>
		</div>
	</div>
</template>

<script setup>
import { computed, onBeforeUnmount, ref } from "vue";
import Icon from "../../components/Icon.vue";
import TopBar from "../../components/TopBar.vue";
import Skeleton from "../../components/Skeleton.vue";
import Empty from "../../components/Empty.vue";
import { call, iso_date, replace_params, show_error, state, thai_date } from "../../api.js";

// สถานะของวัน: ชุดเดียวกับ Tab Look-ahead ของ CM (project_dashboard/LookAhead.vue day_state)
const DAY_STATES = {
	done: "ทำแล้ว",
	missed: "ไม่ได้ทำตามแผน",
	current: "วันนี้",
	planned: "แผนข้างหน้า",
	extra: "ทำนอกแผน",
	complete: "เสร็จแล้ว",
};
const STATUS_TONE = {
	done: "green",
	not_due: "gray",
	on_track: "blue",
	behind: "amber",
	not_started: "rose",
	overdue: "rose",
};
const DOW = ["อา", "จ", "อ", "พ", "พฤ", "ศ", "ส"];

const data = ref(null);
const loading = ref(false);
const week = ref(state.route.params.week || null);

const pct = (v) => (Number(v) || 0).toLocaleString("th-TH", { maximumFractionDigits: 0 });
const add_days = (date, n) => {
	const d = new Date(`${date}T00:00:00`);
	d.setDate(d.getDate() + n);
	return iso_date(d);
};

const weeks = computed(() => {
	if (!data.value) return [];
	const out = [];
	for (let start = String(data.value.start); start <= String(data.value.end); start = add_days(start, 7)) {
		const diff = Math.round((new Date(start) - new Date(String(data.value.this_week))) / (7 * 86400000));
		const label =
			diff === 0
				? "สัปดาห์นี้"
				: diff === -1
				? "สัปดาห์ที่แล้ว"
				: diff === 1
				? "สัปดาห์หน้า"
				: `อีก ${diff} สัปดาห์`;
		out.push({ start, label, range: `${thai_date(start)}–${thai_date(add_days(start, 6))}` });
	}
	return out;
});

// ขนาดจอ: มือถือ 1 สัปดาห์ (การ์ด), แท็บเล็ต 2 สัปดาห์ (ตาราง), จอใหญ่ทั้งช่วง (ตาราง ไม่ต้องเลือกสัปดาห์)
const mq_wide = window.matchMedia("(min-width: 768px)");
const mq_xl = window.matchMedia("(min-width: 1180px)");
const wide = ref(mq_wide.matches);
const xl = ref(mq_xl.matches);
const on_resize = () => {
	wide.value = mq_wide.matches;
	xl.value = mq_xl.matches;
};
mq_wide.addEventListener("change", on_resize);
mq_xl.addEventListener("change", on_resize);
onBeforeUnmount(() => {
	mq_wide.removeEventListener("change", on_resize);
	mq_xl.removeEventListener("change", on_resize);
});

const holidays = computed(() => new Set((data.value?.holidays || []).map(String)));
const first_day = computed(() => (xl.value && data.value ? String(data.value.start) : week.value));
const span = computed(() => {
	if (!xl.value) return wide.value ? 14 : 7;
	return Math.round((new Date(String(data.value.end)) - new Date(String(data.value.start))) / 86400000) + 1;
});
const days = computed(() =>
	!first_day.value
		? []
		: Array.from({ length: span.value }, (_, i) => {
				const date = add_days(first_day.value, i);
				const dow = new Date(`${date}T00:00:00`).getDay();
				return {
					date,
					dow: DOW[dow],
					num: Number(date.slice(8)),
					holiday: holidays.value.has(date),
					monday: dow === 1,
				};
		  })
);
const week_days = computed(() => days.value.slice(0, 7));
// แถบชื่อสัปดาห์เหนือหัววันของตาราง
const shown_weeks = computed(() =>
	weeks.value
		.filter((w) => days.value.some((d) => d.date >= w.start && d.date <= add_days(w.start, 6)))
		.map((w) => ({
			...w,
			days: days.value.filter((d) => d.date >= w.start && d.date <= add_days(w.start, 6)).length,
		}))
);

function day_state(task, day, planned, worked) {
	const ref_day = String(data.value.date);
	const finished = task.finished_on && task.finished_on <= ref_day && day > task.finished_on;
	if (worked) return planned ? "done" : "extra";
	if (!planned) return null;
	if (finished) return "complete";
	if (day < ref_day) return "missed";
	return day === ref_day ? "current" : "planned";
}

function cells(task) {
	const planned = new Set((task.days || []).map(String));
	return (wide.value ? days.value : week_days.value).map((d) => {
		const work = d.date <= String(data.value.date) ? task.work?.[d.date] : null;
		const state_ = day_state(task, d.date, planned.has(d.date), Boolean(work));
		return {
			date: d.date,
			holiday: d.holiday,
			monday: d.monday,
			state: state_,
			title: state_ ? `${thai_date(d.date)} · ${DAY_STATES[state_]}` : "",
		};
	});
}

// งานที่มีวันตามแผนหรือมีงานทำในสัปดาห์ที่เลือก (งานเลยกำหนดแสดงทุกสัปดาห์)
const groups = computed(() => {
	if (!data.value || !first_day.value) return [];
	const start = first_day.value;
	const end = add_days(start, (wide.value ? span.value : 7) - 1);
	return data.value.groups
		.map((g) => ({
			...g,
			tasks: g.tasks.filter(
				(t) =>
					t.overdue ||
					(t.days || []).some((d) => d >= start && d <= end) ||
					Object.keys(t.work || {}).some((d) => d >= start && d <= end)
			),
		}))
		.filter((g) => g.tasks.length);
});

const summary = computed(() => {
	const tasks = groups.value.flatMap((g) => g.tasks);
	return {
		total: tasks.length,
		overdue: tasks.filter((t) => t.overdue || t.status === "overdue").length,
		late: tasks.filter((t) => ["behind", "not_started"].includes(t.status)).length,
		critical: tasks.filter((t) => t.critical && t.status !== "done").length,
	};
});

function choose_week(start) {
	week.value = start;
	replace_params("lookahead", { week: start });
}

async function load() {
	loading.value = true;
	try {
		const result = await call("consbiz.site_app.get_lookahead", {
			project: state.project.name,
			weeks: 3,
		});
		data.value = result || false;
		if (result && !weeks.value.some((w) => w.start === week.value)) week.value = String(result.this_week);
	} catch (error) {
		show_error(error);
		data.value ??= false;
	} finally {
		loading.value = false;
	}
}

load();
</script>
