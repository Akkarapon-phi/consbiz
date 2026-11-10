<script setup>
// Tab "ภาพรวม" ของแผนงาน: S-Curve + สรุปความคืบหน้า (บนสุด), ตัวเลขที่ต้องติดตาม, ปฏิทินหน้างาน,
// กำหนดเวลา/ค่าปรับ และงานที่ล่าช้า (EVM และ Cash Flow อยู่ใน Tab การเงิน: Finance.vue)
// ข้อมูลจาก dashboard.get_dashboard ณ วันที่เลือก ตัวเลขละเอียดกดไปรายงาน/รายการเอกสาร
import { computed, onMounted, ref } from "vue";
import FrappeControl from "../construction_management/components/FrappeControl.vue";
import ProgressCurve from "./components/ProgressCurve.vue";
import SiteCalendar from "./components/SiteCalendar.vue";
import Stat from "./components/Stat.vue";
import { date, money, percent, ratio } from "./format";

const API = "consbiz.consbiz.doctype.construction_management.dashboard.get_dashboard";

const props = defineProps({ name: String });

const data = ref(null);
const loading = ref(false);
const status_date = ref(frappe.datetime.get_today());
const calendar = ref(null);

async function load() {
	loading.value = true;
	try {
		const { message } = await frappe.call(API, { name: props.name, date: status_date.value });
		data.value = message;
		calendar.value?.load();
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

const currency = computed(() => data.value?.currency);
const fmt_money = (value, narrow) => money(value, currency.value, narrow);
const icon = (name, size = "sm") => frappe.utils.icon(name, size);

// ---------- ความคืบหน้า ----------

const plan_label = computed(() =>
	data.value.progress.basis === "Baseline" ? __("แผนสัญญา") : __("แผน")
);

const variance = computed(() => {
	const { plan, actual } = data.value.progress;
	const diff = actual - plan;
	if (Math.abs(diff) < 0.005) return { text: __("ตาม{0}", [plan_label.value]), color: "gray" };
	return diff > 0
		? { text: __("เร็วกว่า{0} {1}", [plan_label.value, percent(diff)]), color: "green" }
		: { text: __("ช้ากว่า{0} {1}", [plan_label.value, percent(-diff)]), color: "red" };
});

// ---------- กำหนดเวลา: แถบเวลาจากวันเริ่มสัญญาถึงวันหลังสุด ----------

const timeline = computed(() => {
	const s = data.value.schedule;
	if (!s.start_date || !s.contract_finish) return null;
	const day = (value) => (value ? frappe.datetime.str_to_obj(value).getTime() : null);
	const start = day(s.start_date);
	const finish = s.handover_date || s.forecast_finish;
	const end = Math.max(day(s.contract_finish), day(finish) || 0, day(data.value.date));
	const pos = (value) => (value === null ? null : ((day(value) - start) / (end - start || 1)) * 100);
	const markers = [
		s.extension_days && {
			key: "original",
			x: pos(s.finish_date),
			label: __("สิ้นสุดเดิม"),
			value: s.finish_date,
		},
		{
			key: "contract",
			x: pos(s.contract_finish),
			label: s.extension_days ? __("สิ้นสุดปรับปรุง") : __("สิ้นสุดสัญญา"),
			value: s.contract_finish,
		},
		finish && {
			key: s.overrun_days ? "late" : "ok",
			x: pos(finish),
			label: s.handover_date ? __("ส่งมอบจริง") : __("คาดว่าเสร็จ"),
			value: finish,
		},
	].filter(Boolean);
	const remaining = Math.round((day(s.contract_finish) - day(data.value.date)) / 86400000);
	const total = Math.round((day(s.contract_finish) - start) / 86400000) + 1;
	return {
		// เวลาที่ใช้ไปเทียบระยะสัญญา (ปรับปรุง) ใช้ในกล่องความคืบหน้า
		time_pct: Math.min(Math.max(((day(data.value.date) - start) / 86400000 + 1) / (total || 1), 0), 1) * 100,
		total,
		elapsed: Math.min(Math.max(pos(data.value.date), 0), 100),
		contract: pos(s.contract_finish),
		markers,
		remaining,
	};
});

// ---------- ตัวเลขที่ต้องติดตาม ----------

function open_list(doctype, filters = {}) {
	frappe.route_options = { construction_management: props.name, ...filters };
	frappe.set_route("List", doctype);
}

function open_report(report, filters = {}) {
	frappe.set_route("query-report", report, {
		construction_management: props.name,
		...filters,
	});
}

const stats = computed(() => {
	const d = data.value;
	const items = [
		{
			label: __("งานที่ช้ากว่าแผน / ค้าง"),
			icon: "triangle-alert",
			value: d.tasks.late,
			note: __("จากงานทั้งหมด {0} งาน", [d.tasks.total]),
			color: d.tasks.late ? "orange" : "green",
			route: () => open_report("Construction Delay Analysis", { date: d.date }),
		},
		{
			label: __("งานวิกฤตที่ล่าช้า"),
			icon: "zap",
			value: d.tasks.critical_late,
			note: __("เลื่อนแล้วโครงการเสร็จช้าลง"),
			color: d.tasks.critical_late ? "red" : "green",
			route: () => open_report("Construction Delay Analysis", { date: d.date }),
		},
		{
			label: __("งานลด-งานเพิ่ม รออนุมัติ"),
			icon: "git-pull-request",
			value: d.contract.pending_count,
			note: d.contract.pending_count && d.show_values ? fmt_money(d.contract.pending_total) : __("ไม่มีค้าง"),
			color: d.contract.pending_count ? "orange" : "gray",
			route: () => open_list("Variation Order", { docstatus: 1, employer_status: "Pending" }),
		},
		{
			label: __("ขอขยายเวลา รออนุมัติ"),
			icon: "hourglass",
			value: d.extensions.pending_count,
			note: d.extensions.pending_count
				? __("ขอ {0} วัน", [d.extensions.pending_total])
				: __("ไม่มีค้าง"),
			color: d.extensions.pending_count ? "orange" : "gray",
			route: () => open_list("Extension of Time", { docstatus: 1, employer_status: "Pending" }),
		},
		{
			label: __("ขอตรวจงาน รอผล / ไม่ผ่าน"),
			icon: "clipboard-check",
			value: `${d.quality.pending} / ${d.quality.failed}`,
			note: __("ผ่านแล้ว {0}", [d.quality.passed]),
			color: d.quality.failed ? "red" : d.quality.pending ? "orange" : "green",
			route: () => open_list("Inspection Request", { docstatus: 1 }),
		},
		{
			label: __("Punch List ค้าง"),
			icon: "list-checks",
			value: d.quality.punch_open,
			note: __("รายการที่ยังไม่ปิด"),
			color: d.quality.punch_open ? "orange" : "green",
			route: () => open_list("Punch List", { docstatus: 1, status: "Open" }),
		},
	];
	if (d.materials) {
		items.push({
			label: __("วัสดุเลยวันต้องสั่ง"),
			icon: "package",
			value: d.materials.late,
			note: __("ต้องสั่งใน {0} วันอีก {1}", [d.materials.days, d.materials.due]),
			color: d.materials.late ? "red" : d.materials.due ? "orange" : "green",
			route: () => frappe.set_route("Form", "Construction Material Plan", props.name),
		});
	}
	if (d.retention) {
		items.push({
			label: __("เงินประกันผลงานค้างรับ"),
			icon: "wallet",
			value: fmt_money(d.retention.outstanding, true),
			note: d.retention.overdue
				? __("เลยกำหนด {0}", [fmt_money(d.retention.overdue, true)])
				: __("ไม่มีเลยกำหนด"),
			color: d.retention.overdue ? "red" : "blue",
		});
	}
	return items;
});

// ---------- กราฟ ----------

// ป้ายแกน x รายเดือนแบบสั้น เช่น "ต.ค. 69" (จุดสุดท้ายคือวันที่เลือกดู แสดงวันที่เต็ม)
const month_label = new Intl.DateTimeFormat(frappe.boot.lang === "th" ? "th-TH" : undefined, {
	month: "short",
	year: "2-digit",
});
function axis_labels(rows) {
	return rows.map((row, i) =>
		i === rows.length - 1 && rows.length > 1 && row.date === data.value.date
			? date(row.date)
			: month_label.format(frappe.datetime.str_to_obj(row.date))
	);
}


const index_color = (value) =>
	value === null || value === undefined ? "gray" : value >= 1 ? "green" : "red";

</script>

<template>
	<div class="pd">
		<div class="pd-toolbar">
			<div class="pd-toolbar-group">
				<span class="pd-toolbar-icon" v-html="icon('calendar')" />
				<span class="text-muted">{{ __("ณ วันที่") }}</span>
				<FrappeControl
					class="pd-date-input"
					:df="{ fieldtype: 'Date' }"
					:model-value="status_date"
					@update:model-value="set_date"
				/>
				<button type="button" class="pd-chip-btn" @click="set_date(frappe.datetime.get_today())">
					{{ __("วันนี้") }}
				</button>
				<button
					type="button"
					class="pd-icon-btn"
					:class="{ 'pd-spin': loading }"
					:disabled="loading"
					:title="__('โหลดใหม่')"
					@click="load"
					v-html="icon('refresh')"
				/>
			</div>
			<div class="pd-toolbar-links">
				<button
					type="button"
					class="pd-chip-btn"
					@click="open_report('Construction Delay Analysis', { date: status_date })"
				>
					<span v-html="icon('triangle-alert')" />{{ __("วิเคราะห์ความล่าช้า") }}
				</button>
				<button
					v-if="data?.evm"
					type="button"
					class="pd-chip-btn"
					@click="open_report('Construction Earned Value', { to_date: status_date })"
				>
					<span v-html="icon('trending-up')" />{{ __("Earned Value") }}
				</button>
			</div>
		</div>

		<div v-if="!data" class="pd-skeleton">
			<div class="pd-skeleton-block pd-skeleton-hero" />
			<div class="pd-skeleton-row">
				<div v-for="i in 4" :key="i" class="pd-skeleton-block" />
			</div>
		</div>

		<div v-else class="pd-body" :class="{ 'pd-loading': loading }">
			<!-- S-Curve + สรุปความคืบหน้า -->
			<section class="pd-card pd-hero">
				<div class="pd-hero-chart">
					<header class="pd-card-head">
						<div>
							<h4 class="pd-card-title">{{ __("S-Curve") }}</h4>
							<div class="pd-card-sub">{{ __("ความคืบหน้าสะสม {0} เทียบกับงานจริง", [plan_label]) }}</div>
						</div>
					</header>
					<ProgressCurve
						:rows="data.curve"
						:status-date="data.date"
						:plan-label="plan_label"
						:height="290"
					/>
				</div>
				<aside class="pd-hero-side">
					<div class="pd-big">
						<span class="pd-big-label">{{ __("ความคืบหน้าจริง") }}</span>
						<span class="pd-big-value">{{ percent(data.progress.actual) }}</span>
						<span class="pd-pill" :class="`pd-tone-${variance.color}`">{{ variance.text }}</span>
					</div>
					<div class="pd-meters">
						<div class="pd-meter">
							<div class="pd-meter-head">
								<span><i class="pd-dot pd-dot-plan" />{{ plan_label }}</span>
								<strong>{{ percent(data.progress.plan) }}</strong>
							</div>
							<div class="pd-meter-track">
								<div class="pd-meter-fill pd-fill-plan" :style="{ width: Math.min(data.progress.plan, 100) + '%' }" />
							</div>
						</div>
						<div class="pd-meter">
							<div class="pd-meter-head">
								<span><i class="pd-dot pd-dot-actual" />{{ __("จริง") }}</span>
								<strong>{{ percent(data.progress.actual) }}</strong>
							</div>
							<div class="pd-meter-track">
								<div class="pd-meter-fill pd-fill-actual" :style="{ width: Math.min(data.progress.actual, 100) + '%' }" />
							</div>
						</div>
						<!-- ระยะเวลา: เวลาที่ใช้ไปเทียบความคืบหน้า และวันคงเหลือถึงวันสิ้นสุดสัญญา (ปรับปรุง) -->
						<div v-if="timeline" class="pd-meter">
							<div class="pd-meter-head">
								<span><i class="pd-dot pd-dot-time" />{{ __("เวลาที่ใช้ไป") }}</span>
								<strong>{{ percent(timeline.time_pct) }}</strong>
							</div>
							<div class="pd-meter-track">
								<div class="pd-meter-fill pd-fill-time" :style="{ width: timeline.time_pct + '%' }" />
							</div>
							<div class="pd-meter-note" :class="{ 'pd-text-red': timeline.remaining < 0 }">
								{{
									timeline.remaining >= 0
										? __("เหลืออีก {0} วันถึงวันสิ้นสุดสัญญา (จาก {1} วัน)", [timeline.remaining, timeline.total])
										: __("เลยวันสิ้นสุดสัญญามา {0} วัน", [-timeline.remaining])
								}}
							</div>
						</div>
					</div>
					<div class="pd-facts">
						<div v-if="data.show_values">
							<span>{{ __("มูลค่าสัญญาปรับปรุง") }}</span>
							<strong>{{ fmt_money(data.contract.revised_amount) }}</strong>
						</div>
						<div v-if="data.show_values && data.contract.variation_amount">
							<span>{{ __("งานเพิ่ม-ลดที่อนุมัติ") }}</span>
							<strong>{{ fmt_money(data.contract.variation_amount) }}</strong>
						</div>
						<div v-if="data.evm">
							<span>SPI</span>
							<strong :class="`pd-text-${index_color(data.evm.spi)}`">{{ ratio(data.evm.spi) }}</strong>
						</div>
					</div>
				</aside>
			</section>

			<div class="pd-stats">
				<Stat v-for="stat in stats" :key="stat.label" v-bind="stat" />
			</div>

			<SiteCalendar ref="calendar" :name="name" :status-date="status_date" />

			<div class="pd-row-even">
				<section class="pd-card pd-schedule">
					<header class="pd-card-head">
						<div>
							<h4 class="pd-card-title">{{ __("กำหนดเวลา") }}</h4>
							<div v-if="timeline" class="pd-card-sub">
								{{ date(data.schedule.start_date) }} - {{ date(data.schedule.contract_finish) }}
							</div>
						</div>
						<span class="pd-pill" :class="data.schedule.overrun_days ? 'pd-tone-red' : 'pd-tone-green'">
							{{
								data.schedule.overrun_days
									? __("เกินกำหนด {0} วัน", [data.schedule.overrun_days])
									: __("ทันกำหนด")
							}}
						</span>
					</header>
					<template v-if="timeline">
						<div class="pd-track">
							<div class="pd-track-elapsed" :style="{ width: timeline.elapsed + '%' }" />
							<div class="pd-track-over" :style="{ left: timeline.contract + '%' }" />
							<div class="pd-track-today" :style="{ left: timeline.elapsed + '%' }" />
							<div
								v-for="marker in timeline.markers"
								:key="marker.key"
								class="pd-marker"
								:class="`pd-marker-${marker.key}`"
								:style="{ left: marker.x + '%' }"
								:title="`${marker.label} ${date(marker.value)}`"
							/>
						</div>
						<div class="pd-track-labels">
							<span>{{ date(data.schedule.start_date) }}</span>
							<span>{{ __("วันนี้") }}</span>
						</div>
						<div class="pd-milestones">
							<div v-for="marker in timeline.markers" :key="marker.key" class="pd-milestone">
								<i class="pd-marker-dot" :class="`pd-marker-${marker.key}`" />
								<span class="pd-milestone-label">{{ marker.label }}</span>
								<strong>{{ date(marker.value) }}</strong>
							</div>
						</div>
					</template>
					<div v-else class="pd-empty-note">{{ __("ยังไม่ได้กำหนดวันเริ่ม-สิ้นสุดสัญญา") }}</div>
					<div class="pd-facts pd-facts-inline">
						<div v-if="data.show_values">
							<span>{{ __("ค่าปรับคาดการณ์") }}</span>
							<strong :class="{ 'pd-text-red': data.schedule.penalty }">
								{{ fmt_money(data.schedule.penalty) }}
							</strong>
						</div>
						<div v-if="data.schedule.extension_days">
							<span>{{ __("ขยายเวลาแล้ว") }}</span>
							<strong>{{ __("{0} วัน", [data.schedule.extension_days]) }}</strong>
						</div>
					</div>
					<div v-if="data.schedule.warning" class="pd-alert">
						<span v-html="icon('triangle-alert')" />{{ data.schedule.warning }}
					</div>
				</section>

				<section class="pd-card">
					<header class="pd-card-head">
						<h4 class="pd-card-title">{{ __("งานที่ต้องติดตาม") }}</h4>
						<a class="pd-link" href="#" @click.prevent="open_report('Construction Delay Analysis', { date: data.date })">
							{{ __("ดูทั้งหมด") }} →
						</a>
					</header>
					<ul v-if="data.tasks.worst.length" class="pd-list">
						<li v-for="task in data.tasks.worst" :key="task.wbs" class="pd-list-row">
							<span class="pd-wbs">{{ task.wbs }}</span>
							<div class="pd-list-main">
								<div class="pd-list-title">
									{{ task.item_name }}
									<span v-if="task.critical" class="pd-pill pd-pill-sm pd-tone-red">{{ __("วิกฤต") }}</span>
								</div>
								<div
									class="pd-mini"
									:title="`${plan_label} ${percent(task.plan_pct)} · ${__('จริง')} ${percent(task.actual_pct)}`"
								>
									<div class="pd-meter-fill pd-fill-plan pd-mini-plan" :style="{ width: Math.min(task.plan_pct, 100) + '%' }" />
									<div class="pd-meter-fill pd-fill-actual" :style="{ width: Math.min(task.actual_pct, 100) + '%' }" />
								</div>
							</div>
							<div class="pd-list-end">
								<span class="pd-pill pd-pill-sm" :class="`pd-tone-${task.status_color}`">{{ task.status_label }}</span>
								<span v-if="task.delay_days" class="pd-text-red pd-num">{{ __("{0} วัน", [task.delay_days]) }}</span>
							</div>
						</li>
					</ul>
					<div v-else class="pd-empty-note">
						<span v-html="icon('circle-check', 'md')" />{{ __("ไม่มีงานที่ล่าช้า") }}
					</div>
				</section>
			</div>
		</div>
	</div>
</template>

<style>
/* โทเค็นที่ใช้ร่วมกับ Tab เอกสารโครงการ (Documents.vue) และการ์ดตัวเลข (Stat.vue) */
.pd,
.pdoc {
	--pd-radius: 16px;
	--pd-radius-sm: 10px;
	--pd-border: color-mix(in srgb, var(--border-color) 70%, transparent);
	--pd-shadow: 0 1px 2px rgb(0 0 0 / 0.04), 0 4px 16px rgb(0 0 0 / 0.04);
	--pd-shadow-hover: 0 2px 4px rgb(0 0 0 / 0.06), 0 10px 28px rgb(0 0 0 / 0.08);
}
.pd-tone-green {
	--pd-tone-bg: color-mix(in srgb, var(--green-500) 14%, transparent);
	--pd-tone-fg: var(--green-600);
}
.pd-tone-orange {
	--pd-tone-bg: color-mix(in srgb, var(--orange-500) 14%, transparent);
	--pd-tone-fg: var(--orange-600);
}
.pd-tone-red {
	--pd-tone-bg: color-mix(in srgb, var(--red-500) 14%, transparent);
	--pd-tone-fg: var(--red-600);
}
.pd-tone-blue {
	--pd-tone-bg: color-mix(in srgb, var(--blue-500) 14%, transparent);
	--pd-tone-fg: var(--blue-600);
}
.pd-tone-gray {
	--pd-tone-bg: color-mix(in srgb, var(--gray-500) 12%, transparent);
	--pd-tone-fg: var(--gray-600);
}
.pd-pill {
	display: inline-flex;
	align-items: center;
	gap: 4px;
	padding: 4px 12px;
	border-radius: 999px;
	background: var(--pd-tone-bg);
	color: var(--pd-tone-fg);
	font-size: var(--text-sm);
	font-weight: 600;
	white-space: nowrap;
}
.pd-pill-sm {
	padding: 2px 8px;
	font-size: var(--text-xs);
}
/* การ์ดพื้นฐาน ใช้ทั้งใน Dashboard.vue และคอมโพเนนต์ลูก (SiteCalendar.vue) */
.pd-loading {
	opacity: 0.55;
}
.pd-card {
	display: flex;
	flex-direction: column;
	gap: 16px;
	min-width: 0;
	padding: 20px 24px;
	border: 1px solid var(--pd-border);
	border-radius: var(--pd-radius);
	background: var(--card-bg);
	box-shadow: var(--pd-shadow);
}
.pd-card-head {
	display: flex;
	align-items: flex-start;
	justify-content: space-between;
	gap: var(--padding-sm);
}
.pd-card-title {
	margin: 0;
	color: var(--heading-color);
	font-size: var(--text-lg);
	font-weight: 700;
}
.pd-card-sub {
	margin-top: 2px;
	color: var(--text-muted);
	font-size: var(--text-sm);
}
</style>

<style scoped>
.pd {
	container-type: inline-size;
	padding: var(--padding-sm) 0 var(--padding-xl);
}
.pd-body {
	display: flex;
	flex-direction: column;
	gap: 20px;
	transition: opacity 0.2s;
}

/* แถบเครื่องมือ */
.pd-toolbar {
	display: flex;
	flex-wrap: wrap;
	align-items: center;
	justify-content: space-between;
	gap: var(--padding-sm);
	margin-bottom: 20px;
}
.pd-toolbar-group {
	display: flex;
	align-items: center;
	gap: 8px;
	padding: 4px 4px 4px 14px;
	border: 1px solid var(--pd-border);
	border-radius: var(--radius);
	background: var(--card-bg);
	box-shadow: var(--pd-shadow);
}
.pd-toolbar-icon {
	display: flex;
	color: var(--text-muted);
}
.pd-toolbar-links {
	display: flex;
	flex-wrap: wrap;
	gap: 8px;
}
.pd-date-input :deep(.form-control) {
	width: 120px;
	height: 30px;
	border-radius: var(--radius);
}
.pd-chip-btn,
.pd-icon-btn {
	display: inline-flex;
	align-items: center;
	gap: 6px;
	height: 32px;
	padding: 0 14px;
	border: 1px solid var(--pd-border);
	border-radius: var(--radius);
	background: var(--card-bg);
	color: var(--text-color);
	font-size: var(--text-sm);
	font-weight: 500;
	transition: background 0.15s ease;
}
.pd-toolbar-group .pd-chip-btn,
.pd-toolbar-group .pd-icon-btn {
	border-color: transparent;
	background: var(--control-bg);
}
.pd-icon-btn {
	justify-content: center;
	width: 32px;
	padding: 0;
}
.pd-chip-btn:hover,
.pd-icon-btn:hover {
	background: var(--fg-hover-color);
}
.pd-spin :deep(svg) {
	animation: pd-spin 0.8s linear infinite;
}
@keyframes pd-spin {
	to {
		transform: rotate(360deg);
	}
}

/* การ์ด */
.pd-link {
	color: var(--text-muted);
	font-size: var(--text-sm);
	font-weight: 500;
	white-space: nowrap;
}
.pd-link:hover {
	color: var(--text-color);
	text-decoration: none;
}
.pd-row-even {
	display: grid;
	grid-template-columns: repeat(2, minmax(0, 1fr));
	gap: 20px;
	align-items: start;
}
/* ใช้ .pd นำหน้าให้ชนะสีตัวเลขของการ์ด (.pd-index-value, .pd-facts strong) */
.pd .pd-text-green {
	color: var(--green-600);
}
.pd .pd-text-red {
	color: var(--red-600);
}
.pd .pd-text-gray {
	color: var(--text-muted);
}
.pd-num {
	font-variant-numeric: tabular-nums;
	white-space: nowrap;
}
.pd-empty-note {
	display: flex;
	align-items: center;
	gap: 8px;
	padding: 24px;
	border-radius: var(--pd-radius-sm);
	background: var(--subtle-fg);
	color: var(--text-muted);
	justify-content: center;
}

/* S-Curve + สรุป */
.pd-hero {
	display: grid;
	grid-template-columns: minmax(0, 1fr) 300px;
	gap: 24px;
	padding: 24px;
	background:
		radial-gradient(circle at 100% 0%, color-mix(in srgb, var(--consbiz-gantt-plan) 8%, transparent), transparent 45%),
		var(--card-bg);
}
.pd-hero-chart {
	min-width: 0;
}
.pd-hero-side {
	display: flex;
	flex-direction: column;
	gap: 20px;
	padding-left: 24px;
	border-left: 1px solid var(--pd-border);
}
.pd-big {
	display: flex;
	flex-direction: column;
	align-items: flex-start;
	gap: 6px;
}
.pd-big-label {
	color: var(--text-muted);
	font-size: var(--text-sm);
}
.pd-big-value {
	color: var(--heading-color);
	font-size: 44px;
	font-weight: 800;
	line-height: 1;
	letter-spacing: -0.02em;
	font-variant-numeric: tabular-nums;
}
.pd-meters {
	display: flex;
	flex-direction: column;
	gap: 14px;
}
.pd-meter-head {
	display: flex;
	justify-content: space-between;
	margin-bottom: 6px;
	font-size: var(--text-sm);
}
.pd-meter-head span {
	display: flex;
	align-items: center;
	gap: 6px;
	color: var(--text-muted);
}
.pd-meter-track,
.pd-mini {
	position: relative;
	overflow: hidden;
	border-radius: 999px;
	background: var(--control-bg);
}
.pd-meter-track {
	height: 10px;
}
.pd-mini {
	height: 6px;
	max-width: 260px;
	margin-top: 6px;
}
.pd-meter-fill {
	position: absolute;
	inset: 0 auto 0 0;
	border-radius: inherit;
	transition: width 0.4s ease;
}
.pd-fill-plan {
	background: var(--consbiz-gantt-plan);
}
.pd-fill-actual {
	background: var(--consbiz-gantt-actual);
}
.pd-mini-plan {
	opacity: 0.3;
}
.pd-dot {
	display: inline-block;
	width: 8px;
	height: 8px;
	border-radius: 50%;
}
.pd-dot-plan {
	background: var(--consbiz-gantt-plan);
}
.pd-dot-actual {
	background: var(--consbiz-gantt-actual);
}
.pd-dot-time {
	background: var(--consbiz-gantt-status-date);
}
.pd-fill-time {
	background: var(--consbiz-gantt-status-date);
	opacity: 0.7;
}
.pd-meter-note {
	margin-top: 4px;
	color: var(--text-muted);
	font-size: var(--text-xs);
}
.pd-facts {
	display: grid;
	gap: 12px;
	margin-top: auto;
}
.pd-facts > div {
	display: flex;
	flex-direction: column;
	gap: 2px;
}
.pd-facts span {
	color: var(--text-muted);
	font-size: var(--text-xs);
}
.pd-facts strong {
	color: var(--heading-color);
	font-size: var(--text-md);
	font-variant-numeric: tabular-nums;
}
.pd-facts-inline {
	grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
	padding: 14px 16px;
	border-radius: var(--pd-radius-sm);
	background: var(--subtle-fg);
}

/* กำหนดเวลา */
.pd-track {
	position: relative;
	height: 12px;
	margin-top: 4px;
	border-radius: 999px;
	background: var(--control-bg);
}
.pd-track-elapsed {
	position: absolute;
	inset: 0 auto 0 0;
	border-radius: inherit;
	background: linear-gradient(
		90deg,
		color-mix(in srgb, var(--consbiz-gantt-plan) 35%, transparent),
		var(--consbiz-gantt-plan)
	);
}
.pd-track-over {
	position: absolute;
	inset: 0 0 0 auto;
	border-radius: 0 999px 999px 0;
	background: repeating-linear-gradient(
		45deg,
		color-mix(in srgb, var(--consbiz-gantt-critical) 25%, transparent) 0 4px,
		transparent 4px 8px
	);
}
.pd-track-today {
	position: absolute;
	top: -6px;
	bottom: -6px;
	width: 2px;
	margin-left: -1px;
	border-radius: 2px;
	background: var(--consbiz-gantt-today);
}
.pd-marker,
.pd-marker-dot {
	border-radius: 50%;
	box-shadow: 0 0 0 3px var(--card-bg);
}
.pd-marker {
	position: absolute;
	top: 50%;
	width: 16px;
	height: 16px;
	margin: -8px 0 0 -8px;
}
.pd-marker-dot {
	display: inline-block;
	flex: none;
	width: 10px;
	height: 10px;
}
.pd-marker-original {
	background: var(--gray-400);
}
.pd-marker-contract {
	background: var(--consbiz-gantt-finish);
}
.pd-marker-ok {
	background: var(--consbiz-gantt-done);
}
.pd-marker-late {
	background: var(--consbiz-gantt-critical);
}
.pd-track-labels {
	display: flex;
	justify-content: space-between;
	color: var(--text-muted);
	font-size: var(--text-xs);
}
.pd-milestones {
	display: flex;
	flex-direction: column;
	gap: 10px;
}
.pd-milestone {
	display: flex;
	align-items: center;
	gap: 10px;
	font-size: var(--text-sm);
}
.pd-milestone-label {
	flex: 1;
	color: var(--text-muted);
}
.pd-alert {
	display: flex;
	align-items: center;
	gap: 8px;
	padding: 10px 14px;
	border-radius: var(--pd-radius-sm);
	background: color-mix(in srgb, var(--red-500) 10%, transparent);
	color: var(--red-600);
	font-size: var(--text-sm);
}

/* ตัวเลขที่ต้องติดตาม */
.pd-stats {
	display: grid;
	grid-template-columns: repeat(auto-fill, minmax(min(240px, 100%), 1fr));
	gap: 14px;
}

/* รายการ */
.pd-list {
	display: flex;
	flex-direction: column;
	gap: 4px;
	margin: 0;
	padding: 0;
	list-style: none;
}
.pd-list-row {
	display: flex;
	align-items: center;
	gap: 12px;
	padding: 10px 12px;
	margin: 0 -12px;
	border-radius: var(--pd-radius-sm);
	color: var(--text-color);
	transition: background 0.15s ease;
}
.pd-list-row:hover {
	background: var(--fg-hover-color);
	text-decoration: none;
}
.pd-list-main {
	flex: 1;
	min-width: 0;
}
.pd-list-title {
	display: flex;
	align-items: center;
	gap: 6px;
	overflow: hidden;
	color: var(--heading-color);
	font-weight: 500;
	text-overflow: ellipsis;
	white-space: nowrap;
}
.pd-list-sub {
	overflow: hidden;
	color: var(--text-muted);
	font-size: var(--text-sm);
	text-overflow: ellipsis;
	white-space: nowrap;
}
.pd-list-end {
	display: flex;
	flex-direction: column;
	align-items: flex-end;
	gap: 4px;
	font-size: var(--text-sm);
}
.pd-wbs {
	flex: none;
	min-width: 44px;
	padding: 4px 8px;
	border-radius: 8px;
	background: var(--subtle-fg);
	color: var(--text-muted);
	font-size: var(--text-xs);
	font-weight: 600;
	text-align: center;
	font-variant-numeric: tabular-nums;
}

/* โครงตอนโหลด */
.pd-skeleton {
	display: flex;
	flex-direction: column;
	gap: 20px;
}
.pd-skeleton-row {
	display: grid;
	grid-template-columns: repeat(4, 1fr);
	gap: 14px;
}
.pd-skeleton-block {
	height: 96px;
	border-radius: var(--pd-radius);
	background: linear-gradient(90deg, var(--control-bg), var(--subtle-fg), var(--control-bg));
	background-size: 200% 100%;
	animation: pd-shimmer 1.2s ease-in-out infinite;
}
.pd-skeleton-hero {
	height: 340px;
}
@keyframes pd-shimmer {
	to {
		background-position: -200% 0;
	}
}

/* พื้นที่แคบ (วัดจากความกว้างของ Tab ไม่ใช่จอ): เรียงเป็นคอลัมน์เดียว */
@container (max-width: 760px) {
	.pd-hero,
	.pd-row-even {
		grid-template-columns: minmax(0, 1fr);
	}
	.pd-hero-side {
		padding: 20px 0 0;
		border-left: none;
		border-top: 1px solid var(--pd-border);
	}
}
@container (max-width: 480px) {
	.pd-card,
	.pd-hero {
		padding: 16px;
	}
	.pd-big-value {
		font-size: 36px;
	}
	.pd-skeleton-row {
		grid-template-columns: repeat(2, 1fr);
	}
}
</style>
