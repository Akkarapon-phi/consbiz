<script setup>
// ปฏิทินหน้างานรายเดือน: แต่ละวันบอกว่าลง Daily Report แล้วหรือยัง (+% ของวันนั้น) และมี Daily Request ไหม
// กดวันที่เพื่อดูเอกสารของวันนั้นด้านขวา แล้วเปิด/สร้าง Daily Report หรือ Daily Request ของวันนั้นได้เลย
// ข้อมูลจาก dashboard.get_site_calendar วันที่ "ขาดรายงาน" = วันทำงานตั้งแต่เริ่มสัญญาถึงวันนี้ที่ยังไม่มี DR ที่ Submit
// 1 วันสร้าง DR / DRQ ได้หลายฉบับ (แบ่งกันลงหลายคน) แต่ 1 คำขอที่อนุมัติแล้วสร้าง DR ได้ 1 ฉบับ
// สีพื้นของวัน (ลำดับก่อนหลัง): DR Submit แล้ว > DR ร่าง > DRQ รออนุมัติ > DRQ อนุมัติแล้ว (รอลง DR) > ขาดรายงาน
// ความสูงคงที่: ปฏิทิน 6 สัปดาห์ทุกเดือน และแผงด้านขวาเลื่อนในตัว (ไม่ยืดตามจำนวนเอกสาร)
import { computed, onMounted, ref } from "vue";
import { date, document_indicator, percent } from "../format";

const API = "consbiz.consbiz.doctype.construction_management.dashboard.get_site_calendar";
const MAKE_REPORT = "consbiz.consbiz.doctype.daily_request.daily_request.make_daily_report";

const props = defineProps({ name: String, statusDate: String });

// month_start/month_end ของ frappe.datetime ไม่รับวันที่ ใช้ moment (รูปแบบตั้งต้นของ Frappe คือ YYYY-MM-DD)
const month_start = (day) => moment(day).startOf("month").format();
const month_end = (day) => moment(day).endOf("month").format();

const month = ref(month_start(props.statusDate));
const data = ref(null);
const loading = ref(false);
const selected = ref(props.statusDate);

async function load() {
	loading.value = true;
	try {
		const { message } = await frappe.call(API, { name: props.name, month: month.value });
		data.value = message;
	} finally {
		loading.value = false;
	}
}
defineExpose({ load });
onMounted(load);

function shift_month(step) {
	month.value = frappe.datetime.add_months(month.value, step);
	load();
}

function this_month() {
	month.value = month_start(frappe.datetime.get_today());
	selected.value = frappe.datetime.get_today();
	load();
}

const locale = frappe.boot.lang === "th" ? "th-TH" : undefined;
const month_title = computed(() =>
	new Intl.DateTimeFormat(locale, { month: "long", year: "numeric" }).format(
		frappe.datetime.str_to_obj(month.value)
	)
);
// หัวคอลัมน์จันทร์-อาทิตย์
const weekdays = computed(() => {
	const fmt = new Intl.DateTimeFormat(locale, { weekday: "short" });
	return [...Array(7)].map((_, i) => fmt.format(new Date(2024, 0, 1 + i)));
});

const by_date = (rows) => {
	const map = {};
	for (const row of rows || []) (map[row.date] ||= []).push(row);
	return map;
};
const reports = computed(() => by_date(data.value?.reports));
const requests = computed(() => by_date(data.value?.requests));
const holidays = computed(() => new Set(data.value?.holidays || []));

// ช่องของปฏิทิน: เริ่มวันจันทร์ ครบทุกสัปดาห์ของเดือน
const cells = computed(() => {
	if (!data.value) return [];
	const { today, contract_start, contract_finish } = data.value;
	const first = frappe.datetime.str_to_obj(month.value);
	const offset = (first.getDay() + 6) % 7;
	const start = frappe.datetime.add_days(month.value, -offset);
	const end_of_month = month_end(month.value);
	// 6 สัปดาห์เสมอ ความสูงไม่เปลี่ยนตามเดือน
	const total = 42;
	return [...Array(total)].map((_, i) => {
		const day = frappe.datetime.add_days(start, i);
		const day_reports = reports.value[day] || [];
		const submitted = day_reports.find((r) => r.docstatus === 1);
		const in_contract = (!contract_start || day >= contract_start) && (!contract_finish || day <= contract_finish);
		const holiday = holidays.value.has(day);
		const day_requests = requests.value[day] || [];
		let state = "none";
		if (submitted) state = "done";
		else if (day_reports.length) state = "draft";
		else if (day_requests.some((r) => r.docstatus === 0 && r.status !== "Rejected")) state = "req-pending";
		else if (day_requests.some((r) => r.docstatus === 1 && r.status === "Approved")) state = "req-approved";
		else if (in_contract && !holiday && day <= today && day >= month.value && day <= end_of_month)
			state = "missing";
		return {
			day,
			number: frappe.datetime.str_to_obj(day).getDate(),
			outside: day < month.value || day > end_of_month,
			today: day === today,
			future: day > today,
			holiday,
			state,
			progress: day_reports
				.filter((r) => r.docstatus === 1)
				.reduce((sum, r) => sum + (r.today_progress || 0), 0),
			requests: requests.value[day] || [],
			reports: day_reports.length,
		};
	});
});

const selected_day = computed(() => ({
	date: selected.value,
	label: new Intl.DateTimeFormat(locale, {
		weekday: "long",
		day: "numeric",
		month: "long",
		year: "numeric",
	}).format(frappe.datetime.str_to_obj(selected.value)),
	holiday: holidays.value.has(selected.value),
	future: data.value && selected.value > data.value.today,
	reports: reports.value[selected.value] || [],
	requests: requests.value[selected.value] || [],
}));

// คำขอที่อนุมัติแล้วและยังไม่มี DR อ้างถึง: สร้าง DR จากคำขอได้ (ดึงงาน คน เครื่องจักรมาให้) ฉบับละ 1 DR
const open_requests = computed(() =>
	selected_day.value.requests.filter(
		(r) =>
			r.docstatus === 1 &&
			r.status === "Approved" &&
			!selected_day.value.reports.some((report) => report.daily_request === r.name)
	)
);
const has_report = computed(() => selected_day.value.reports.length > 0);
const owner_name = (row) => frappe.user.full_name(row.owner);

function select(cell) {
	selected.value = cell.day;
	if (cell.outside) {
		month.value = month_start(cell.day);
		load();
	}
}

function open(doctype, name) {
	frappe.set_route("Form", doctype, name);
}

function new_report(request) {
	if (request) {
		frappe.call(MAKE_REPORT, { source_name: request.name }).then(({ message }) => {
			const doc = frappe.model.sync(message)[0];
			frappe.set_route("Form", doc.doctype, doc.name);
		});
		return;
	}
	frappe.new_doc("Daily Report", { construction_management: props.name, date: selected.value });
}

function new_request() {
	frappe.new_doc("Daily Request", { construction_management: props.name, date: selected.value });
}

const request_tone = (row) => document_indicator(row)?.color || "gray";
</script>

<template>
	<section class="pd-card pdc">
		<header class="pd-card-head">
			<div>
				<h4 class="pd-card-title">{{ __("ปฏิทินหน้างาน") }}</h4>
				<div class="pd-card-sub">{{ __("Daily Report และ Daily Request รายวัน กดวันที่เพื่อดูหรือสร้างเอกสาร") }}</div>
			</div>
			<div class="pdc-nav">
				<button type="button" class="pdc-nav-btn" :title="__('เดือนก่อน')" @click="shift_month(-1)" v-html="frappe.utils.icon('chevron-left', 'sm')" />
				<span class="pdc-month">{{ month_title }}</span>
				<button type="button" class="pdc-nav-btn" :title="__('เดือนถัดไป')" @click="shift_month(1)" v-html="frappe.utils.icon('chevron-right', 'sm')" />
				<button type="button" class="pdc-today-btn" @click="this_month">{{ __("เดือนนี้") }}</button>
			</div>
		</header>

		<div v-if="data" class="pdc-summary">
			<span class="pd-pill pd-tone-green">{{ __("ลงรายงานแล้ว {0} วัน", [data.summary.report_days]) }}</span>
			<span class="pd-pill" :class="data.summary.missing_days ? 'pd-tone-red' : 'pd-tone-gray'">
				{{ __("ขาดรายงาน {0} วัน", [data.summary.missing_days]) }}
			</span>
			<span class="pd-pill pd-tone-blue">{{ __("ความคืบหน้าเดือนนี้ +{0}", [percent(data.summary.progress)]) }}</span>
			<span class="pd-pill pd-tone-orange">{{ __("คำขอ {0} ฉบับ", [data.summary.requests]) }}</span>
		</div>

		<div class="pdc-body" :class="{ 'pd-loading': loading }">
			<div class="pdc-calendar">
				<div v-for="weekday in weekdays" :key="weekday" class="pdc-weekday">{{ weekday }}</div>
				<button
					v-for="cell in cells"
					:key="cell.day"
					type="button"
					class="pdc-day"
					:class="[
						`pdc-${cell.state}`,
						{
							'pdc-outside': cell.outside,
							'pdc-today': cell.today,
							'pdc-holiday': cell.holiday,
							'pdc-selected': cell.day === selected,
						},
					]"
					@click="select(cell)"
				>
					<span class="pdc-number">{{ cell.number }}</span>
					<span v-if="cell.reports > 1" class="pdc-count" :title="__('Daily Report {0} ฉบับ', [cell.reports])">{{ cell.reports }}</span>
					<span v-if="cell.state === 'done'" class="pdc-progress">+{{ percent(cell.progress) }}</span>
					<span v-else-if="cell.state === 'draft'" class="pdc-tag">{{ __("ร่าง") }}</span>
					<span v-else-if="cell.state === 'req-pending'" class="pdc-tag">{{ __("รออนุมัติ") }}</span>
					<span v-else-if="cell.state === 'req-approved'" class="pdc-tag">{{ __("รอลง DR") }}</span>
					<span v-else-if="cell.state === 'missing'" class="pdc-tag">{{ __("ยังไม่ลง") }}</span>
					<span v-if="cell.requests.length" class="pdc-requests">
						<i v-for="row in cell.requests" :key="row.name" :class="`pd-tone-${request_tone(row)}`" />
					</span>
				</button>
			</div>

			<aside class="pdc-detail">
				<div class="pdc-detail-date">
					{{ selected_day.label }}
					<span v-if="selected_day.holiday" class="pd-pill pd-pill-sm pd-tone-gray">{{ __("วันหยุด") }}</span>
				</div>

				<div class="pdc-section">
					<div class="pdc-section-title">
						<span class="pdc-section-icon pd-tone-green" v-html="frappe.utils.icon('file-text', 'sm')" />
						{{ __("Daily Report") }}
					</div>
					<button
						v-for="row in selected_day.reports"
						:key="row.name"
						type="button"
						class="pdc-doc"
						@click="open('Daily Report', row.name)"
					>
						<span class="pdc-doc-main">
							<strong>{{ row.name }}</strong>
							<span class="pdc-doc-sub">
								{{ __("วันนี้ +{0} · สะสม {1}", [percent(row.today_progress), percent(row.cumulative_progress)]) }}
								· {{ owner_name(row) }}
							</span>
							<span v-if="row.problems" class="pdc-doc-note">{{ row.problems }}</span>
						</span>
						<span class="pd-pill pd-pill-sm" :class="`pd-tone-${document_indicator(row).color}`">
							{{ document_indicator(row).label }}
						</span>
					</button>
					<div v-if="!has_report" class="pdc-empty">
						{{ selected_day.future ? __("ยังไม่ถึงวัน") : __("ยังไม่ได้ลงรายงาน") }}
					</div>
					<div v-if="has_report" class="pdc-note">
						{{ __("วันนี้สร้าง Daily Report แล้ว {0} ฉบับ สร้างเพิ่มได้ถ้าแบ่งกันลงหลายคน (ระวังลงงานซ้ำกัน)", [selected_day.reports.length]) }}
					</div>
					<template v-if="!selected_day.future && data?.can_create_report">
						<button
							v-for="request in open_requests"
							:key="request.name"
							type="button"
							class="pdc-create"
							@click="new_report(request)"
						>
							<span v-html="frappe.utils.icon('plus', 'xs')" />
							{{ __("สร้าง Daily Report จากคำขอ {0}", [request.name]) }}
						</button>
						<button
							type="button"
							class="pdc-create"
							:class="{ 'pdc-create-soft': open_requests.length || has_report }"
							@click="new_report()"
						>
							<span v-html="frappe.utils.icon('plus', 'xs')" />
							{{ has_report ? __("สร้าง Daily Report เพิ่ม") : __("สร้าง Daily Report") }}
						</button>
					</template>
				</div>

				<div class="pdc-section">
					<div class="pdc-section-title">
						<span class="pdc-section-icon pd-tone-orange" v-html="frappe.utils.icon('clipboard', 'sm')" />
						{{ __("Daily Request") }}
					</div>
					<button
						v-for="row in selected_day.requests"
						:key="row.name"
						type="button"
						class="pdc-doc"
						@click="open('Daily Request', row.name)"
					>
						<span class="pdc-doc-main">
							<strong>{{ row.name }}</strong>
							<span class="pdc-doc-sub">
								{{ __("คาดว่าจะได้ +{0}", [percent(row.expected_progress)]) }} · {{ row.requested_by || owner_name(row) }}
							</span>
						</span>
						<span class="pd-pill pd-pill-sm" :class="`pd-tone-${request_tone(row)}`">
							{{ document_indicator(row).label }}
						</span>
					</button>
					<div v-if="!selected_day.requests.length" class="pdc-empty">{{ __("ไม่มีคำขอ") }}</div>
					<div v-else class="pdc-note">
						{{ __("วันนี้สร้าง Daily Request แล้ว {0} ฉบับ", [selected_day.requests.length]) }}
					</div>
					<button v-if="data?.can_create_request" type="button" class="pdc-create pdc-create-soft" @click="new_request">
						<span v-html="frappe.utils.icon('plus', 'xs')" />
						{{ selected_day.requests.length ? __("สร้าง Daily Request เพิ่ม") : __("สร้าง Daily Request") }}
					</button>
				</div>
			</aside>
		</div>

		<footer class="pdc-legend">
			<span><i class="pdc-swatch pdc-done" />{{ __("ลงรายงานแล้ว") }}</span>
			<span><i class="pdc-swatch pdc-draft" />{{ __("ฉบับร่าง") }}</span>
			<span><i class="pdc-swatch pdc-req-pending" />{{ __("DRQ รออนุมัติ") }}</span>
			<span><i class="pdc-swatch pdc-req-approved" />{{ __("DRQ อนุมัติแล้ว รอลง DR") }}</span>
			<span><i class="pdc-swatch pdc-missing" />{{ __("ยังไม่ลงรายงาน") }}</span>
			<span><i class="pdc-swatch pdc-holiday" />{{ __("วันหยุด") }}</span>
			<span><i class="pdc-dot pd-tone-orange" />{{ __("มีคำขอ (สีตามสถานะ)") }}</span>
		</footer>
	</section>
</template>

<style scoped>
.pdc-nav {
	display: flex;
	align-items: center;
	gap: 6px;
}
.pdc-month {
	min-width: 130px;
	color: var(--heading-color);
	font-weight: 600;
	text-align: center;
}
.pdc-nav-btn,
.pdc-today-btn {
	display: inline-grid;
	place-items: center;
	height: 32px;
	border: 1px solid var(--pd-border);
	border-radius: var(--radius);
	background: var(--card-bg);
	color: var(--text-color);
	font-size: var(--text-sm);
}
.pdc-nav-btn {
	width: 32px;
}
.pdc-today-btn {
	padding: 0 14px;
}
.pdc-nav-btn:hover,
.pdc-today-btn:hover {
	background: var(--fg-hover-color);
}
.pdc-summary {
	display: flex;
	flex-wrap: wrap;
	gap: 8px;
}
.pdc-body {
	display: grid;
	grid-template-columns: minmax(0, 1fr) 300px;
	gap: 24px;
	transition: opacity 0.2s;
}

/* ปฏิทิน */
.pdc-calendar {
	display: grid;
	grid-template-columns: repeat(7, minmax(0, 1fr));
	gap: 6px;
}
.pdc-weekday {
	padding-bottom: 4px;
	color: var(--text-muted);
	font-size: var(--text-xs);
	font-weight: 600;
	text-align: center;
}
.pdc-day {
	position: relative;
	display: flex;
	flex-direction: column;
	align-items: flex-start;
	justify-content: space-between;
	min-height: 68px;
	padding: 8px;
	border: 1px solid transparent;
	border-radius: 12px;
	background: var(--subtle-fg);
	color: var(--text-color);
	text-align: left;
	transition:
		transform 0.12s ease,
		box-shadow 0.12s ease;
}
.pdc-day:hover {
	transform: translateY(-1px);
	box-shadow: var(--pd-shadow-hover);
}
.pdc-number {
	font-size: var(--text-sm);
	font-weight: 600;
}
.pdc-progress,
.pdc-tag {
	font-size: 11px;
	font-weight: 700;
	font-variant-numeric: tabular-nums;
	white-space: nowrap;
}
.pdc-done {
	background: color-mix(in srgb, var(--green-500) 16%, transparent);
	color: var(--green-700, var(--green-600));
}
.pdc-draft {
	background: color-mix(in srgb, var(--orange-500) 14%, transparent);
	color: var(--orange-600);
}
.pdc-req-pending,
.pdc-day.pdc-req-pending {
	background: color-mix(in srgb, var(--yellow-500) 22%, transparent);
	color: var(--yellow-700, var(--yellow-600));
}
.pdc-req-approved,
.pdc-day.pdc-req-approved {
	background: color-mix(in srgb, var(--blue-500) 14%, transparent);
	color: var(--blue-600);
}
.pdc-missing {
	border: 1px dashed color-mix(in srgb, var(--red-500) 45%, transparent);
	background: transparent;
}
.pdc-missing .pdc-tag {
	color: var(--red-600);
	font-weight: 500;
}
.pdc-holiday {
	background: repeating-linear-gradient(
		135deg,
		var(--subtle-fg) 0 6px,
		color-mix(in srgb, var(--gray-500) 10%, transparent) 6px 12px
	);
	color: var(--text-muted);
}
.pdc-outside {
	opacity: 0.35;
}
.pdc-today .pdc-number {
	display: inline-grid;
	place-items: center;
	min-width: 22px;
	height: 22px;
	margin: -3px 0 0 -3px;
	padding: 0 4px;
	border-radius: 999px;
	background: var(--consbiz-gantt-today);
	color: var(--neutral-white, #fff);
}
.pdc-selected {
	box-shadow:
		0 0 0 2px var(--card-bg),
		0 0 0 4px var(--consbiz-gantt-plan);
}
.pdc-requests {
	position: absolute;
	top: 9px;
	right: 8px;
	display: flex;
	gap: 3px;
}
.pdc-requests i,
.pdc-dot {
	display: inline-block;
	width: 8px;
	height: 8px;
	border-radius: 50%;
	background: var(--pd-tone-fg);
}

/* รายละเอียดวันที่เลือก */
/* contain: size = ไม่ให้เนื้อหาของแผงกำหนดความสูงแถว แผงสูงเท่าปฏิทินแล้วเลื่อนในตัว */
.pdc-detail {
	display: flex;
	flex-direction: column;
	gap: 18px;
	padding-left: 24px;
	border-left: 1px solid var(--pd-border);
	contain: size;
	overflow-y: auto;
	overscroll-behavior: contain;
}
.pdc-detail-date {
	display: flex;
	flex-wrap: wrap;
	align-items: center;
	gap: 8px;
	color: var(--heading-color);
	font-size: var(--text-md);
	font-weight: 700;
}
.pdc-section {
	display: flex;
	flex-direction: column;
	gap: 8px;
}
.pdc-section-title {
	display: flex;
	align-items: center;
	gap: 8px;
	color: var(--text-muted);
	font-size: var(--text-sm);
	font-weight: 600;
}
.pdc-section-icon {
	display: grid;
	place-items: center;
	width: 26px;
	height: 26px;
	border-radius: 8px;
	background: var(--pd-tone-bg);
	color: var(--pd-tone-fg);
}
.pdc-section-icon :deep(svg),
.pdc-create :deep(svg) {
	stroke: currentColor;
}
.pdc-doc {
	display: flex;
	align-items: flex-start;
	justify-content: space-between;
	gap: 8px;
	padding: 10px 12px;
	border: 1px solid var(--pd-border);
	border-radius: var(--pd-radius-sm);
	background: var(--card-bg);
	color: var(--text-color);
	text-align: left;
	transition: background 0.15s ease;
}
.pdc-doc:hover {
	background: var(--fg-hover-color);
}
.pdc-doc-main {
	display: flex;
	flex-direction: column;
	gap: 2px;
	min-width: 0;
}
.pdc-doc-sub {
	color: var(--text-muted);
	font-size: var(--text-xs);
}
.pdc-doc-note {
	overflow: hidden;
	color: var(--text-muted);
	font-size: var(--text-xs);
	text-overflow: ellipsis;
	white-space: nowrap;
}
.pdc-note {
	color: var(--text-muted);
	font-size: var(--text-xs);
}
/* จำนวน Daily Report ของวัน (มากกว่า 1 ฉบับ) มุมขวาล่าง ไม่ทับจุดคำขอมุมขวาบน */
.pdc-count {
	position: absolute;
	bottom: 8px;
	right: 8px;
	min-width: 16px;
	padding: 0 4px;
	border-radius: 8px;
	background: var(--gray-600);
	color: var(--white, #fff);
	font-size: 10px;
	font-weight: 700;
	line-height: 16px;
	text-align: center;
}
.pdc-empty {
	padding: 10px;
	border-radius: var(--pd-radius-sm);
	background: var(--subtle-fg);
	color: var(--text-muted);
	font-size: var(--text-sm);
	text-align: center;
}
.pdc-create {
	display: inline-flex;
	align-items: center;
	justify-content: center;
	gap: 6px;
	height: 34px;
	border: none;
	border-radius: var(--radius);
	background: var(--btn-primary, var(--primary));
	color: var(--neutral-white, #fff);
	font-size: var(--text-sm);
	font-weight: 600;
}
.pdc-create:hover {
	opacity: 0.9;
}
.pdc-create-soft {
	border: 1px solid var(--pd-border);
	background: var(--card-bg);
	color: var(--text-color);
}
.pdc-create-soft:hover {
	background: var(--fg-hover-color);
	opacity: 1;
}

.pdc-legend {
	display: flex;
	flex-wrap: wrap;
	gap: 6px 18px;
	color: var(--text-muted);
	font-size: var(--text-xs);
}
.pdc-legend span {
	display: inline-flex;
	align-items: center;
	gap: 6px;
}
.pdc-swatch {
	display: inline-block;
	width: 14px;
	height: 14px;
	border-radius: 4px;
}

@container (max-width: 760px) {
	.pdc-body {
		grid-template-columns: minmax(0, 1fr);
	}
	/* วางใต้ปฏิทิน: สูงคงที่ เลื่อนในตัว */
	.pdc-detail {
		height: 320px;
		padding: 18px 0 0;
		border-left: none;
		border-top: 1px solid var(--pd-border);
	}
	.pdc-day {
		min-height: 52px;
		padding: 6px;
	}
	.pdc-tag {
		display: none;
	}
}
@container (max-width: 480px) {
	.pdc-calendar {
		gap: 3px;
	}
	.pdc-day {
		min-height: 44px;
		padding: 4px;
		border-radius: 8px;
	}
	.pdc-progress {
		font-size: 9px;
	}
	/* จุดคำขอต่อท้ายในช่อง ไม่ลอยทับตัวเลข */
	.pdc-requests {
		position: static;
		margin-top: 2px;
	}
	.pdc-requests i {
		width: 6px;
		height: 6px;
	}
	.pd-card-head {
		flex-direction: column;
	}
}
</style>
