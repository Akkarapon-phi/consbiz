<template>
	<div class="ss-work-pilot">
		<Hero />

		<div v-if="!state.project" class="ss-content">
			<Empty icon="building" title="ยังไม่ได้เลือกโครงการ" text="เลือกโครงการที่ดูแลเพื่อเริ่มใช้งาน">
				<button type="button" class="ss-btn ss-btn--primary" @click="$emit('pick-project')">
					เลือกโครงการ
				</button>
			</Empty>
		</div>

		<div v-else class="ss-content ss-work-content">
			<header class="ss-work-greeting">
				<div>
					<h1>{{ greeting }}, {{ display_name }}</h1>
					<p>ติดตามงาน ความก้าวหน้า และสถานะของโครงการได้จากที่นี่</p>
				</div>
				<button
					v-if="actions[0]"
					type="button"
					class="ss-btn ss-btn--primary ss-work-create"
					:disabled="actions[0].disabled"
					@click="actions[0].run()"
				>
					<Icon name="plus" :size="17" />
					{{ actions[0].label }}
				</button>
			</header>

			<div v-if="loading" class="ss-work-loading">
				<div v-for="i in 6" :key="i" class="ss-plan ss-plan--loading">
					<span class="ss-sk ss-sk-number"></span><span class="ss-sk ss-sk-line"></span>
				</div>
			</div>

			<Empty
				v-else-if="!summary.construction_management"
				icon="layers"
				title="โครงการนี้ยังไม่มีแผนงาน"
				text="สร้างแผนงานก่อสร้าง (Construction Management) ของโครงการในระบบเต็มก่อน"
			/>

			<div v-else class="ss-work-grid">
				<section class="ss-work-card ss-work-progress">
					<div class="ss-work-head">
						<div>
							<span>ความก้าวหน้าโครงการ</span>
							<strong>{{ pct(progress?.actual) }}<small>%</small></strong>
						</div>
						<span class="ss-work-variance" :class="`is-${variance_tone}`">
							<Icon :name="variance >= 0 ? 'trending' : 'alert'" :size="13" />
							{{ variance_text }}
						</span>
					</div>
					<div
						class="ss-work-track"
						:aria-label="`จริง ${pct(progress?.actual)}% แผน ${pct(progress?.plan)}%`"
					>
						<span class="is-plan" :style="{ width: `${clamp(progress?.plan)}%` }"></span>
						<span class="is-actual" :style="{ width: `${clamp(progress?.actual)}%` }"></span>
					</div>
					<dl class="ss-work-facts">
						<div><dt>ผลงานจริง</dt><dd>{{ pct(progress?.actual) }}%</dd></div>
						<div><dt>ตามแผน</dt><dd>{{ pct(progress?.plan) }}%</dd></div>
						<div>
							<dt>สิ้นสุดสัญญา</dt>
							<dd>{{ progress?.finish_date ? thai_date(progress.finish_date, { year: true }) : "–" }}</dd>
						</div>
						<div><dt>เวลาที่เหลือ</dt><dd>{{ days_left || "–" }}</dd></div>
					</dl>
					<div class="ss-work-progress-actions">
						<button type="button" class="ss-btn ss-btn--primary" @click="go('plan')">
							<Icon name="gantt" :size="16" /> ดูแผนงาน
						</button>
						<button
							v-if="inspection_action"
							type="button"
							class="ss-btn ss-btn--soft"
							:disabled="inspection_action.disabled"
							@click="inspection_action.run()"
						>
							<Icon name="search-check" :size="16" /> ขอตรวจงาน
						</button>
					</div>
				</section>

				<section class="ss-work-stats" aria-label="ตัวเลขสรุป">
					<button
						v-for="(stat, index) in stats"
						:key="stat.key"
						type="button"
						:class="{ 'is-featured': index === 0 }"
						@click="go(stat.view, stat.params || {})"
					>
						<span>{{ stat.label }} <i><Icon :name="stat.icon" :size="15" /></i></span>
						<strong>{{ stat.value }}</strong>
						<small>{{ stat.alert || "ดูรายละเอียด" }}</small>
					</button>
				</section>

				<section v-if="summary?.curve?.length > 1" class="ss-work-card ss-work-curve">
					<div class="ss-work-head">
						<div><h2>ความก้าวหน้ารายเดือน</h2><p>ผลงานจริงเทียบแผนสะสม</p></div>
					</div>
					<SCurve :points="summary.curve" :basis="progress?.basis" fill />
				</section>

				<section v-if="quick_actions.length" class="ss-work-card ss-work-quick">
					<div class="ss-work-head"><h2>ทำรายการด่วน</h2></div>
					<div class="ss-work-quick-list">
						<button
							v-for="action in quick_actions"
							:key="action.label"
							type="button"
							:disabled="action.disabled"
							@click="action.run()"
						>
							<i><Icon :name="action.icon" :size="17" /></i>
							<span><b>{{ action.label }}</b><small>{{ action.note }}</small></span>
							<Icon name="chevron-right" :size="15" />
						</button>
					</div>
				</section>

				<section v-if="categories.length" class="ss-work-card ss-work-categories">
					<div class="ss-work-head">
						<h2>หมวดงาน</h2>
						<span>ทั้งหมด {{ summary.categories.length }} หมวด</span>
					</div>
					<div class="ss-work-cat-list">
						<div v-for="category in categories" :key="category.wbs" class="ss-work-cat-row">
							<span :title="category.item_name"><small>{{ category.wbs }}</small>{{ category.item_name }}</span>
							<b>{{ pct(category.percent) }}%</b>
							<div class="ss-work-track">
								<span class="is-actual" :style="{ width: `${clamp(category.percent)}%` }"></span>
							</div>
						</div>
					</div>
				</section>

				<section class="ss-work-card ss-work-followups">
					<div class="ss-work-head">
						<h2>งานที่ต้องติดตาม</h2>
						<button type="button" class="ss-link" @click="go('reports')">ดูรายงานทั้งหมด</button>
					</div>
					<div v-if="followups.length" class="ss-work-table-wrap">
						<table>
							<thead><tr><th>เลขที่</th><th>รายการ</th><th>รายละเอียด</th><th>สถานะ</th><th>อัปเดต</th><th></th><th class="col-modified"></th></tr></thead>
							<tbody>
								<tr
									v-for="row in followups"
									:key="row.key"
									:class="{ 'is-clickable': row.run }"
									@click="open_followup(row)"
								>
									<td>{{ row.ref }}</td>
									<td>
										<span class="ss-work-row-title">
											<span class="ss-work-row-icon" :class="`is-${row.tone}`"><Icon :name="row.icon" :size="13" /></span>{{ row.title }}
										</span>
									</td>
									<td>{{ row.detail }}</td>
									<td><span class="ss-work-row-status" :class="`is-${row.tone}`"><i></i>{{ row.status }}</span></td>
									<td>{{ row.when }}</td>
									<td><Icon v-if="row.run" name="chevron-right" :size="14" /></td>
									<ModifiedCell :value="row.document?.modified" :row="row.document" />
								</tr>
							</tbody>
						</table>
					</div>
					<div v-else class="ss-work-empty"><Icon name="check" :size="18" /> ไม่มีงานที่ต้องติดตาม</div>
				</section>
			</div>
		</div>
	</div>
</template>

<script setup>
import { computed, inject, onMounted } from "vue";
import Icon from "../../../shared/components/Icon.vue";
import ModifiedCell from "../../../shared/components/ModifiedCell.vue";
import Empty from "../../../shared/components/Empty.vue";
import Hero from "../../../shared/components/Hero.vue";
import SCurve from "../../../shared/components/SCurve.vue";
import { boot, go, relative_date, state, thai_date, today } from "../../../shared/api.js";

defineEmits(["pick-project"]);
const reload_summary = inject("reload_summary");

const summary = computed(() => state.summaries.work);
const loading = computed(() => !summary.value);
const progress = computed(() => summary.value?.progress);
const cm = computed(() => summary.value?.construction_management);
const display_name = computed(() => (boot.full_name || boot.user || "ผู้ใช้งาน").split(" ")[0]);
const greeting = computed(() => {
	const hour = new Date().getHours();
	if (hour < 12) return "อรุณสวัสดิ์";
	if (hour < 17) return "สวัสดีตอนบ่าย";
	return "สวัสดีตอนเย็น";
});

const pct = (value) =>
	(Number(value) || 0).toLocaleString("th-TH", { minimumFractionDigits: 0, maximumFractionDigits: 1 });
const clamp = (value) => Math.max(0, Math.min(100, Number(value) || 0));

const variance = computed(() => (progress.value?.actual || 0) - (progress.value?.plan || 0));
const variance_tone = computed(() =>
	variance.value >= 0 ? "green" : variance.value > -5 ? "amber" : "rose"
);
const variance_text = computed(() => {
	const v = Math.abs(variance.value);
	if (v < 0.05) return "ตามแผน";
	return `${variance.value > 0 ? "เร็วกว่า" : "ช้ากว่า"}แผน ${pct(v)}%`;
});
const days_left = computed(() => {
	if (!progress.value?.finish_date) return "";
	const days = Math.round((new Date(progress.value.finish_date) - new Date(today())) / 86400000);
	if (days === 0) return "วันนี้";
	return days > 0 ? `อีก ${days} วัน` : `เลยมา ${-days} วัน`;
});

const stats = computed(() => {
	const s = summary.value || {};
	return [
		{
			key: "today",
			when: boot.can.view_daily_report,
			label: "รายงานวันนี้",
			value: s.reports_today ?? 0,
			icon: "clipboard",
			tone: "orange",
			view: "reports",
			alert: s.report_drafts ? `ร่าง ${s.report_drafts}` : "",
		},
		{
			key: "request",
			when: boot.can.view_daily_request,
			label: "รออนุมัติ",
			value: s.requests_pending ?? 0,
			icon: "send",
			tone: "blue",
			view: "reports",
			params: { tab: "request" },
		},
		{
			key: "inspection",
			when: boot.can.inspection,
			label: "รอตรวจงาน",
			value: s.inspections_pending ?? 0,
			icon: "search-check",
			tone: "teal",
			view: "inspections",
			alert: s.inspections_failed ? `ไม่ผ่าน ${s.inspections_failed}` : "",
		},
		{
			key: "punch",
			when: boot.can.punch_list,
			label: "Punch List ค้างแก้",
			value: s.punch_open ?? 0,
			icon: "list-checks",
			tone: s.punch_open ? "rose" : "green",
			view: "inspections",
			params: { tab: "punch" },
		},
	].filter((stat) => stat.when);
});

const actions = computed(() => {
	return [
		{
			when: boot.can.daily_report,
			label: "เขียนรายงาน",
			short_label: "วันนี้",
			note: "Daily Report ของวันนี้",
			icon: "clipboard",
			tone: "orange",
			disabled: !cm.value,
			run: () => go("report-form", { kind: "dr", name: "new", date: today() }),
		},
		{
			when: boot.can.daily_request,
			label: "ขออนุมัติล่วงหน้า",
			short_label: "REQ",
			note: "Daily Request ล่วงหน้า",
			icon: "send",
			tone: "blue",
			disabled: !cm.value,
			run: () => go("report-form", { kind: "drq", name: "new", date: today() }),
		},
		{
			when: boot.can.create_inspection,
			label: "ขอตรวจงาน",
			short_label: "IR",
			note: "ส่งใบขอตรวจถึงผู้ตรวจ",
			icon: "search-check",
			tone: "teal",
			disabled: !cm.value,
			run: () => go("site-form", { kind: "inspection", name: "new" }),
		},
		{
			when: boot.can.concrete,
			label: "เทคอนกรีต",
			short_label: "คอนกรีต",
			note: "บันทึกตั๋วรถทีละคัน",
			icon: "truck",
			tone: "violet",
			disabled: !cm.value,
			run: () => go("concrete"),
		},
	].filter((action) => action.when);
});

const categories = computed(() => (summary.value?.categories || []).slice(0, 6));
const inspection_action = computed(() => actions.value.find((action) => action.icon === "search-check"));
// ปุ่มเขียนรายงานอยู่ที่หัวหน้า ขอตรวจงานอยู่ในการ์ดความก้าวหน้า ไม่ต้องซ้ำ
const quick_actions = computed(() =>
	actions.value.filter((action, index) => index > 0 && action !== inspection_action.value)
);
const followups = computed(() => {
	const s = summary.value || {};
	const requests = (s.requests_ready || []).map((row) => ({
		key: `request-${row.name}`,
		document: row,
		ref: row.name,
		title: row.requested_by || "ขออนุมัติปฏิบัติงาน",
		detail: `คาดว่าได้ ${pct(row.expected_progress)}%`,
		status: "รอทำรายงาน",
		tone: "ready",
		icon: "clipboard-check",
		when: row.date ? relative_date(row.date) : "–",
		run: () => go("report-view", { kind: "drq", name: row.name }),
	}));
	const late_tasks = (s.late_tasks || []).map((row) => ({
		key: `task-${row.wbs}`,
		ref: row.wbs,
		title: row.item_name,
		detail: row.status_label || `จริง ${pct(row.actual_pct)}% · แผน ${pct(row.plan_pct)}%`,
		status: row.delay_days > 0 ? `ช้า ${row.delay_days} วัน` : "ต้องติดตาม",
		tone: row.critical ? "critical" : "late",
		icon: row.critical ? "flag" : "alert",
		when: `จริง ${pct(row.actual_pct)}%`,
		run: null,
	}));
	return [...requests, ...late_tasks].slice(0, 5);
});

function open_followup(row) {
	row.run?.();
}

onMounted(() => {
	if (state.project) reload_summary();
});
</script>
