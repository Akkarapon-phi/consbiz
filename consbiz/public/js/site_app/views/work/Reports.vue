<template>
	<div>
		<TopBar title="รายงานประจำวัน" :subtitle="state.project?.project_name">
			<template #search>
				<HeaderSearch
					v-if="active_tab !== 'calendar'"
					:key="active_tab"
					v-model="txt"
					placeholder="ค้นหาเลขที่ ผู้จัดทำ หรือปัญหา"
				/>
			</template>
			<template #actions>
				<button
					v-if="!wide"
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

		<div v-if="active_tab !== 'calendar'" class="ss-content">
			<ReportList
				:key="active_tab"
				:kind="active_tab === 'report' ? 'dr' : 'drq'"
				:tab="active_tab"
				:tabs="tabs"
				:search="txt"
				@update:tab="set_tab"
			/>
		</div>

		<div v-else class="ss-content">
			<div v-if="wide" class="ss-list-head">
				<StatusTabs :model-value="active_tab" :options="tabs" @update:model-value="set_tab" />
				<div class="ss-list-tools">
					<button
						type="button"
						class="ss-icon-btn"
						:class="{ 'is-spinning': loading }"
						aria-label="โหลดใหม่"
						@click="load"
					>
						<Icon name="refresh" :size="17" />
					</button>
				</div>
			</div>
			<Empty
				v-if="data === false"
				icon="layers"
				title="โครงการนี้ยังไม่มีแผนงาน"
				text="รายงานประจำวันต้องอ้างแผนงานก่อสร้างของโครงการ"
			/>
			<div v-else class="ss-split ss-split--calendar">
				<!-- ปฏิทินของเดือน -->
				<div class="ss-split-main">
					<div class="ss-cal">
						<div class="ss-cal-head">
							<button
								type="button"
								class="ss-icon-btn"
								aria-label="เดือนก่อน"
								@click="shift(-1)"
							>
								<Icon name="chevron-left" :size="22" :stroke="2.4" />
							</button>
							<div class="ss-cal-title">
								<b>{{ month_title }}</b>
								<button v-if="!is_this_month" type="button" class="ss-link" @click="go_today">
									กลับวันนี้
								</button>
							</div>
							<button
								type="button"
								class="ss-icon-btn"
								aria-label="เดือนถัดไป"
								@click="shift(1)"
							>
								<Icon name="chevron-right" :size="22" :stroke="2.4" />
							</button>
						</div>

						<div class="ss-cal-summary">
							<span class="ss-tag tone-green"
								><Icon name="check" :size="12" :stroke="3" /> มีรายงาน
								{{ data?.summary.report_days ?? "–" }} วัน</span
							>
							<span v-if="data?.summary.missing_days" class="ss-tag tone-rose"
								><Icon name="alert" :size="12" /> ขาด
								{{ data.summary.missing_days }} วัน</span
							>
							<span v-if="data?.summary.progress" class="ss-tag tone-orange"
								><Icon name="trending" :size="12" /> +{{ pct(data.summary.progress) }}%
								เดือนนี้</span
							>
						</div>

						<div class="ss-cal-grid" :class="{ 'is-loading': loading }">
							<span v-for="d in WEEKDAYS" :key="d" class="ss-cal-dow">{{ d }}</span>
							<span v-for="n in lead" :key="`lead-${n}`" class="ss-cal-blank"></span>
							<button
								v-for="cell in cells"
								:key="cell.date"
								type="button"
								class="ss-cal-day"
								:class="{
									'is-today': cell.date === today_date,
									'is-selected': cell.date === selected,
									'is-holiday': cell.holiday,
									'is-missing': cell.missing,
									'is-future': cell.date > today_date,
								}"
								:aria-label="cell.label"
								@click="select(cell.date)"
							>
								<span class="ss-cal-num">{{ cell.day }}</span>
								<span class="ss-cal-marks">
									<i v-if="cell.missing" class="is-missing"></i>
									<i
										v-for="r in cell.reports.slice(0, 3)"
										:key="r.name"
										class="is-report"
										:class="`tone-${r.status_tone}`"
									></i>
									<i
										v-for="r in cell.requests.slice(0, 2)"
										:key="r.name"
										class="is-request"
										:class="`tone-${r.status_tone}`"
									></i>
								</span>
							</button>
						</div>

						<div class="ss-cal-legend">
							<span><i class="is-report tone-green"></i>รายงาน</span>
							<span><i class="is-report tone-gray"></i>ร่าง</span>
							<span><i class="is-request tone-amber"></i>ขออนุมัติ</span>
							<span><i class="is-missing"></i>ขาดรายงาน</span>
						</div>
					</div>
				</div>

				<!-- เอกสารของวันที่เลือก -->
				<aside class="ss-split-side">
					<h2 class="ss-section-title ss-section-title--first">
						{{ selected ? day_title(selected) : "เลือกวันที่" }}
						<span v-if="selected_cell?.holiday" class="ss-tag tone-gray">วันหยุด</span>
					</h2>

					<div v-if="selected" class="ss-day-actions">
						<button
							v-if="boot.can.daily_report && selected <= today_date"
							type="button"
							class="ss-btn ss-btn--primary"
							@click="go('report-form', { kind: 'dr', name: 'new', date: selected })"
						>
							<Icon name="plus" :size="18" :stroke="2.6" /> เขียนรายงาน
						</button>
						<button
							v-if="boot.can.daily_request"
							type="button"
							class="ss-btn ss-btn--soft"
							@click="go('report-form', { kind: 'drq', name: 'new', date: selected })"
						>
							<Icon name="send" :size="17" />
							{{ selected < today_date ? "ขออนุมัติย้อนหลัง" : "ขออนุมัติล่วงหน้า" }}
						</button>
					</div>

					<Skeleton v-if="data === null" :rows="2" />
					<Empty
						v-else-if="selected && !day_docs.length"
						icon="clipboard"
						title="ยังไม่มีเอกสารของวันนี้"
						:text="
							selected <= today_date
								? 'เขียนรายงานของวันนี้ได้จากปุ่มด้านบน'
								: 'ขออนุมัติปฏิบัติงานล่วงหน้าได้จากปุ่มด้านบน'
						"
					/>
					<TransitionGroup v-else tag="div" class="ss-list" name="ss-list">
						<button
							v-for="(r, i) in day_docs"
							:key="r.name"
							type="button"
							class="ss-card"
							:style="{ '--i': i }"
							@click="go('report-view', { kind: r.kind, name: r.name })"
						>
							<div class="ss-card-head">
								<span class="ss-avatar" :class="`tone-${r.status_tone}`">
									<Icon :name="r.kind === 'dr' ? 'clipboard' : 'send'" :size="18" />
								</span>
								<span class="ss-card-main">
									<span class="ss-card-title">{{
										r.kind === "dr" ? "รายงานประจำวัน" : "ขออนุมัติปฏิบัติงาน"
									}}</span>
									<span class="ss-card-meta"
										>{{ r.name }} · {{ r.requested_by || r.owner_name }}</span
									>
								</span>
								<span class="ss-tag" :class="`tone-${r.status_tone}`">{{
									r.status_label
								}}</span>
							</div>
							<div class="ss-chips">
								<template v-if="r.kind === 'dr'">
									<span class="ss-chip"
										>วันนี้ <b>+{{ pct(r.today_progress) }}%</b></span
									>
									<span class="ss-chip"
										>สะสม <b>{{ pct(r.cumulative_progress) }}%</b></span
									>
									<span v-if="r.weather" class="ss-chip"
										><Icon name="cloud-sun" :size="12" /> {{ r.weather }}</span
									>
								</template>
								<span v-else class="ss-chip"
									>คาดสะสม <b>{{ pct(r.expected_progress) }}%</b></span
								>
							</div>
							<div v-if="r.problems" class="ss-note-line">
								<Icon name="alert" :size="13" /> {{ r.problems }}
							</div>
						</button>
					</TransitionGroup>
				</aside>
			</div>
		</div>
	</div>
</template>

<script setup>
import { computed, ref } from "vue";
import ReportList from "./ReportList.vue";
import Icon from "../../../shared/components/Icon.vue";
import HeaderSearch from "../../../shared/components/HeaderSearch.vue";
import StatusTabs from "../../../shared/components/StatusTabs.vue";
import TopBar from "../../../shared/components/TopBar.vue";
import Skeleton from "../../../shared/components/Skeleton.vue";
import Empty from "../../../shared/components/Empty.vue";
import {
	boot,
	call,
	go,
	iso_date,
	relative_date,
	remember_tab,
	replace_params,
	show_error,
	state,
	today,
} from "../../../shared/api.js";
import { use_wide } from "../../../shared/table.js";

const WEEKDAYS = ["อา", "จ", "อ", "พ", "พฤ", "ศ", "ส"];
const MONTHS = [
	"มกราคม",
	"กุมภาพันธ์",
	"มีนาคม",
	"เมษายน",
	"พฤษภาคม",
	"มิถุนายน",
	"กรกฎาคม",
	"สิงหาคม",
	"กันยายน",
	"ตุลาคม",
	"พฤศจิกายน",
	"ธันวาคม",
];

const today_date = today();
// URL = /reports/<tab> หรือ /reports/<วันที่> (params ที่ว่างถูกตัดออกจาก URL วันที่จึงมาในตำแหน่ง tab ได้)
const is_day = (value) => /^\d{4}-\d{2}-\d{2}$/.test(value || "");
const route_params = state.route.params;
const selected = ref(
	is_day(route_params.day) ? route_params.day : is_day(route_params.tab) ? route_params.tab : today_date
);

const tabs = [
	{ value: "calendar", label: "ปฏิทิน" },
	...(boot.can.view_daily_report ? [{ value: "report", label: "รายงานประจำวัน" }] : []),
	...(boot.can.view_daily_request ? [{ value: "request", label: "ขออนุมัติปฏิบัติงาน" }] : []),
];
const wide = use_wide();
const tab = ref(tabs.some((t) => t.value === route_params.tab) ? route_params.tab : "calendar");
const txt = ref("");
// มือถือมีแต่ปฏิทิน (ตารางและพิมพ์หลายรายการใช้บนจอ ≥768)
const active_tab = computed(() => (wide.value ? tab.value : "calendar"));

function set_tab(value) {
	tab.value = value;
	txt.value = "";
	remember_tab("reports", value, "calendar");
}

const month = ref(`${selected.value.slice(0, 7)}-01`); // วันที่ 1 ของเดือนที่แสดง
const data = ref(null); // null = กำลังโหลด, false = ไม่มีแผนงาน
const loading = ref(false);

const pct = (value) => (Number(value) || 0).toLocaleString("th-TH", { maximumFractionDigits: 2 });
const is_this_month = computed(() => month.value.slice(0, 7) === today_date.slice(0, 7));
const month_title = computed(() => {
	const [y, m] = month.value.split("-").map(Number);
	return `${MONTHS[m - 1]} ${y + 543}`;
});
const DAY_NAMES = ["อาทิตย์", "จันทร์", "อังคาร", "พุธ", "พฤหัสบดี", "ศุกร์", "เสาร์"];
const day_title = (date) => {
	const [y, m, d] = date.split("-").map(Number);
	const rel = relative_date(date);
	const full = `วัน${DAY_NAMES[new Date(y, m - 1, d).getDay()]}ที่ ${d} ${MONTHS[m - 1]}`;
	return /\d/.test(rel) ? full : `${rel} · ${full}`;
};

// ช่องว่างก่อนวันที่ 1 (สัปดาห์เริ่มวันอาทิตย์)
const lead = computed(() => {
	const [y, m] = month.value.split("-").map(Number);
	return new Date(y, m - 1, 1).getDay();
});

const cells = computed(() => {
	const [y, m] = month.value.split("-").map(Number);
	const count = new Date(y, m, 0).getDate();
	const d = data.value || {};
	const holidays = new Set((d.holidays || []).map(String));
	const by_day = (rows, kind) => {
		const map = {};
		for (const r of rows || []) (map[String(r.date)] ||= []).push({ ...r, kind });
		return map;
	};
	const reports = by_day(d.reports, "dr");
	const requests = by_day(d.requests, "drq");
	const start = d.contract_start ? String(d.contract_start) : null;
	return Array.from({ length: count }, (_, i) => {
		const date = iso_date(new Date(y, m - 1, i + 1));
		const day_reports = reports[date] || [];
		const day_requests = requests[date] || [];
		const holiday = holidays.has(date);
		// วันทำงานที่ผ่านมาแล้ว (ตั้งแต่เริ่มสัญญา) ที่ยังไม่มีรายงานที่ส่งแล้ว (ตรงกับ get_site_calendar)
		const missing =
			!!data.value &&
			!holiday &&
			date <= today_date &&
			(!start || date >= start) &&
			!day_reports.some((r) => r.docstatus === 1);
		return {
			date,
			day: i + 1,
			holiday,
			missing,
			reports: day_reports,
			requests: day_requests,
			label: `${i + 1} ${MONTHS[m - 1]} รายงาน ${day_reports.length} ขออนุมัติ ${day_requests.length}`,
		};
	});
});

const selected_cell = computed(() => cells.value.find((c) => c.date === selected.value));
const day_docs = computed(() => {
	const cell = selected_cell.value;
	return cell ? [...cell.requests, ...cell.reports] : [];
});

let request_id = 0;
async function load() {
	const id = ++request_id;
	loading.value = true;
	try {
		const result = await call("consbiz.site_app.get_calendar", {
			project: state.project.name,
			month: month.value,
		});
		if (id === request_id) data.value = result || false;
	} catch (error) {
		show_error(error);
		if (id === request_id) data.value ??= { reports: [], requests: [], holidays: [], summary: {} };
	} finally {
		if (id === request_id) loading.value = false;
	}
}

function select(date) {
	selected.value = date;
	replace_params("reports", { day: date });
}

function shift(delta) {
	const [y, m] = month.value.split("-").map(Number);
	month.value = iso_date(new Date(y, m - 1 + delta, 1));
	// เดือนอื่น: เลือกวันที่ 1 (เดือนนี้: วันนี้)
	select(month.value.slice(0, 7) === today_date.slice(0, 7) ? today_date : month.value);
	load();
}

function go_today() {
	month.value = `${today_date.slice(0, 7)}-01`;
	select(today_date);
	load();
}

load();
</script>
