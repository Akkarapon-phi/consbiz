<template>
	<div>
		<TopBar title="แผนงาน" :subtitle="state.project?.project_name">
			<template #actions>
				<a
					v-if="data?.can_edit_plan"
					class="ss-icon-btn"
					:href="`/app/construction-gantt/${encodeURIComponent(data.construction_management)}`"
					aria-label="แก้แผนในระบบเต็ม"
					title="แก้แผนในระบบเต็ม"
				>
					<Icon name="pen" :size="19" />
				</a>
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
				<div class="ss-gantt-tools">
					<Segmented v-model="zoom" :options="ZOOMS" />
					<div class="ss-filters">
						<button
							v-for="f in FILTERS"
							:key="f.value"
							type="button"
							class="ss-filter"
							:class="{ 'is-active': filter === f.value }"
							@click="filter = f.value"
						>
							{{ f.label }} <span class="ss-filter-count">{{ count(f.value) }}</span>
						</button>
						<button
							type="button"
							class="ss-filter"
							:class="{ 'is-active': show_baseline }"
							@click="show_baseline = !show_baseline"
						>
							Baseline
						</button>
						<button type="button" class="ss-filter" @click="scroll_today(true)">
							<Icon name="calendar" :size="14" /> วันนี้
						</button>
					</div>
				</div>

				<div ref="scroller" class="ss-gantt" :style="{ '--px': `${px}px`, '--days': total_days }">
					<!-- หัวตาราง: เดือน (และวันที่เมื่อซูมเป็นสัปดาห์) -->
					<div class="ss-gantt-row ss-gantt-head">
						<div class="ss-gantt-name">งาน</div>
						<div class="ss-gantt-track">
							<span
								v-for="m in months"
								:key="m.key"
								class="ss-gantt-month"
								:style="{ left: `${m.offset * px}px`, width: `${m.days * px}px` }"
								>{{ m.label }}</span
							>
						</div>
					</div>
					<div class="ss-gantt-body">
						<div
							class="ss-gantt-today"
							:style="{ left: `calc(var(--name-w) + ${today_offset * px}px)` }"
						></div>
						<div
							v-for="row in visible"
							:key="row.name"
							class="ss-gantt-row"
							:class="{
								'is-group': row.is_group,
								[`is-${row.status}`]: row.status,
								'is-critical': row.critical,
							}"
						>
							<button
								type="button"
								class="ss-gantt-name"
								:style="{ paddingLeft: `${10 + row.indent * 12}px` }"
								@click="row.is_group ? toggle(row) : (detail = row)"
							>
								<Icon
									v-if="row.is_group"
									:name="collapsed.has(row.name) ? 'chevron-right' : 'chevron-down'"
									:size="14"
									:stroke="2.6"
								/>
								<i class="ss-wbs">{{ row.wbs }}</i>
								<span>{{ row.item_name }}</span>
							</button>
							<div class="ss-gantt-track" @click="!row.is_group && (detail = row)">
								<span
									v-if="show_baseline && row.baseline_start && !row.is_group"
									class="ss-gantt-baseline"
									:style="bar(row.baseline_start, row.baseline_end)"
								></span>
								<span v-if="row.start" class="ss-gantt-bar" :style="bar(row.start, row.end)">
									<span
										class="ss-gantt-fill"
										:style="{ width: `${clamp(row.actual)}%` }"
									></span>
								</span>
							</div>
						</div>
						<div v-if="!visible.length" class="ss-options-note">ไม่มีงานในตัวกรองนี้</div>
					</div>
				</div>

				<div class="ss-cal-legend">
					<span><i class="ss-lg ss-lg-bar"></i>แผน</span>
					<span><i class="ss-lg ss-lg-fill"></i>ทำแล้ว</span>
					<span><i class="ss-lg ss-lg-late"></i>ล่าช้า</span>
					<span><i class="ss-lg ss-lg-critical"></i>วิกฤต</span>
					<span v-if="show_baseline"><i class="ss-lg ss-lg-base"></i>Baseline</span>
				</div>
			</template>
		</div>

		<Sheet :open="!!detail" :title="detail?.item_name" :subtitle="detail?.wbs" @close="detail = null">
			<template v-if="detail">
				<div class="ss-doc-head-top" style="margin-bottom: 12px">
					<span class="ss-tag" :class="`tone-${STATUS_TONE[detail.status] || 'gray'}`">{{
						detail.status_label
					}}</span>
					<span v-if="detail.critical" class="ss-tag tone-rose"
						><Icon name="flag" :size="12" /> งานวิกฤต</span
					>
				</div>
				<div class="ss-plan-bar">
					<span class="ss-plan-bar-plan" :style="{ width: `${clamp(detail.plan)}%` }"></span>
					<span class="ss-plan-bar-actual" :style="{ width: `${clamp(detail.actual)}%` }"></span>
				</div>
				<div class="ss-late-foot" style="margin: 6px 0 14px">
					<span>ทำแล้ว {{ pct(detail.actual) }}%</span
					><span>แผน ณ วันนี้ {{ pct(detail.plan) }}%</span>
				</div>
				<div class="ss-facts ss-facts--grid">
					<div class="ss-fact">
						<span>แผนปัจจุบัน</span
						><b>{{ thai_date(detail.start) }} – {{ thai_date(detail.end, { year: true }) }}</b>
					</div>
					<div class="ss-fact">
						<span>ระยะเวลา</span><b>{{ days_between(detail.start, detail.end) + 1 }} วัน</b>
					</div>
					<div v-if="detail.baseline_start" class="ss-fact">
						<span>Baseline</span
						><b
							>{{ thai_date(detail.baseline_start) }} –
							{{ thai_date(detail.baseline_end, { year: true }) }}</b
						>
					</div>
					<div v-if="detail.quantity" class="ss-fact">
						<span>ปริมาณ</span><b>{{ num(detail.quantity) }} {{ detail.uom }}</b>
					</div>
					<div class="ss-fact">
						<span>น้ำหนักงาน</span><b>{{ pct(detail.weight) }}%</b>
					</div>
				</div>
			</template>
		</Sheet>
	</div>
</template>

<script setup>
import { computed, nextTick, ref, watch } from "vue";
import Icon from "../../components/Icon.vue";
import TopBar from "../../components/TopBar.vue";
import Skeleton from "../../components/Skeleton.vue";
import Empty from "../../components/Empty.vue";
import Segmented from "../../components/Segmented.vue";
import Sheet from "../../components/Sheet.vue";
import { call, num, show_error, state, thai_date } from "../../api.js";

const ZOOMS = [
	{ value: "week", label: "สัปดาห์" },
	{ value: "month", label: "เดือน" },
	{ value: "quarter", label: "ไตรมาส" },
];
const PX = { week: 22, month: 6, quarter: 2.2 };
const FILTERS = [
	{ value: "all", label: "ทั้งหมด" },
	{ value: "late", label: "ล่าช้า" },
	{ value: "critical", label: "วิกฤต" },
	{ value: "active", label: "กำลังทำ" },
];
const LATE = ["behind", "not_started", "overdue"];
const STATUS_TONE = {
	done: "green",
	not_due: "gray",
	on_track: "blue",
	behind: "amber",
	not_started: "rose",
	overdue: "rose",
};
const MONTHS = [
	"ม.ค.",
	"ก.พ.",
	"มี.ค.",
	"เม.ย.",
	"พ.ค.",
	"มิ.ย.",
	"ก.ค.",
	"ส.ค.",
	"ก.ย.",
	"ต.ค.",
	"พ.ย.",
	"ธ.ค.",
];

const data = ref(null); // null = กำลังโหลด, false = ไม่มีแผนงาน
const loading = ref(false);
const zoom = ref("month");
const filter = ref("all");
const show_baseline = ref(false);
const collapsed = ref(new Set());
const detail = ref(null);
const scroller = ref(null);

const px = computed(() => PX[zoom.value]);
const pct = (v) => (Number(v) || 0).toLocaleString("th-TH", { maximumFractionDigits: 1 });
const clamp = (v) => Math.max(0, Math.min(100, Number(v) || 0));
const days_between = (a, b) => Math.round((new Date(b) - new Date(a)) / 86400000);

// ช่วงของแกนเวลา: ต้นเดือนของวันแรกสุด ถึงสิ้นเดือนของวันท้ายสุด
const range = computed(() => {
	const rows = data.value?.rows || [];
	const dates = rows.flatMap((r) => [r.start, r.end, r.baseline_start, r.baseline_end]).filter(Boolean);
	dates.push(data.value?.today);
	const min = dates.reduce((a, b) => (a < b ? a : b));
	const max = dates.reduce((a, b) => (a > b ? a : b));
	const start = new Date(`${min.slice(0, 7)}-01T00:00:00`);
	const end_month = new Date(`${max.slice(0, 7)}-01T00:00:00`);
	const end = new Date(end_month.getFullYear(), end_month.getMonth() + 1, 0);
	return { start, end };
});
const offset = (date) => Math.round((new Date(`${date}T00:00:00`) - range.value.start) / 86400000);
const total_days = computed(() => Math.round((range.value.end - range.value.start) / 86400000) + 1);
const today_offset = computed(() => offset(data.value.today) + 0.5);

const months = computed(() => {
	const out = [];
	const d = new Date(range.value.start);
	while (d <= range.value.end) {
		const days = new Date(d.getFullYear(), d.getMonth() + 1, 0).getDate();
		const yy = String((d.getFullYear() + 543) % 100);
		out.push({
			key: `${d.getFullYear()}-${d.getMonth()}`,
			offset: Math.round((d - range.value.start) / 86400000),
			days,
			label: zoom.value === "quarter" ? MONTHS[d.getMonth()] : `${MONTHS[d.getMonth()]} ${yy}`,
		});
		d.setMonth(d.getMonth() + 1);
	}
	return out;
});

function bar(start, end) {
	return {
		left: `${offset(start) * px.value}px`,
		width: `${Math.max(1, offset(end) - offset(start) + 1) * px.value}px`,
	};
}

function matches_with(row, f) {
	if (f === "late") return LATE.includes(row.status);
	if (f === "critical") return row.critical;
	if (f === "active") return row.status && !["done", "not_due"].includes(row.status);
	return true;
}
const count = (f) => (data.value?.rows || []).filter((r) => !r.is_group && matches_with(r, f)).length;

// แถวที่แสดง: กรองแล้วคงหัวข้อของงานที่ผ่านตัวกรอง, หัวข้อที่พับซ่อนแถวลูก
const visible = computed(() => {
	const rows = data.value?.rows || [];
	const keep = new Set();
	const parents = [];
	for (const row of rows) {
		while (parents.length && parents[parents.length - 1].indent >= row.indent) parents.pop();
		if (row.is_group) {
			parents.push(row);
			continue;
		}
		if (filter.value === "all" || matches_with(row, filter.value)) {
			keep.add(row.name);
			parents.forEach((p) => keep.add(p.name));
		}
	}
	const out = [];
	let hide_below = null;
	for (const row of rows) {
		if (hide_below !== null && row.indent > hide_below) continue;
		hide_below = null;
		if (!keep.has(row.name) && !(filter.value === "all" && row.is_group)) continue;
		out.push(row);
		if (row.is_group && collapsed.value.has(row.name)) hide_below = row.indent;
	}
	return out;
});

function toggle(row) {
	const set = new Set(collapsed.value);
	set.has(row.name) ? set.delete(row.name) : set.add(row.name);
	collapsed.value = set;
}

function scroll_today(smooth = false) {
	const el = scroller.value;
	if (!el) return;
	const name_w = el.querySelector(".ss-gantt-name")?.offsetWidth || 0;
	const target = today_offset.value * px.value - (el.clientWidth - name_w) / 3;
	el.scrollTo({ left: Math.max(0, target), behavior: smooth ? "smooth" : "auto" });
}

async function load() {
	loading.value = true;
	try {
		const result = await call("consbiz.site_app.get_plan", { project: state.project.name });
		data.value = result || false;
		// หัวข้อที่เสร็จหมดแล้วพับไว้ (เห็นงานที่กำลังทำก่อน)
		if (result)
			collapsed.value = new Set(
				result.rows.filter((r) => r.is_group && r.actual >= 100).map((r) => r.name)
			);
		await nextTick();
		scroll_today();
	} catch (error) {
		show_error(error);
		data.value ??= false;
	} finally {
		loading.value = false;
	}
}

// เปลี่ยนซูม: เลื่อนให้วันนี้อยู่ในจอ
watch(zoom, async () => {
	await nextTick();
	scroll_today();
});

load();
</script>
