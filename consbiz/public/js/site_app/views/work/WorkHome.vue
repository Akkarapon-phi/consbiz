<template>
	<div>
		<Hero @pick-project="$emit('pick-project')" />

		<div v-if="!state.project" class="ss-content ss-content--lift">
			<Empty icon="building" title="ยังไม่ได้เลือกโครงการ" text="เลือกโครงการที่ดูแลเพื่อเริ่มใช้งาน">
				<button type="button" class="ss-btn ss-btn--primary" @click="$emit('pick-project')">
					เลือกโครงการ
				</button>
			</Empty>
		</div>

		<div v-else class="ss-content ss-content--lift">
			<!-- ความคืบหน้า ณ วันนี้ -->
			<div v-if="loading" class="ss-plan ss-plan--loading">
				<span class="ss-sk ss-sk-number"></span>
				<span class="ss-sk ss-sk-line"></span>
			</div>
			<Empty
				v-else-if="!summary.construction_management"
				icon="layers"
				title="โครงการนี้ยังไม่มีแผนงาน"
				text="สร้างแผนงานก่อสร้าง (Construction Management) ของโครงการในระบบเต็มก่อน"
			/>
			<div v-else-if="progress" class="ss-plan">
				<div class="ss-plan-head">
					<div class="ss-plan-figure">
						<span>ทำได้จริง</span>
						<b>{{ pct(progress.actual) }}<small>%</small></b>
					</div>
					<div class="ss-plan-figure is-plan">
						<span>ตามแผน</span>
						<b>{{ pct(progress.plan) }}<small>%</small></b>
					</div>
					<span class="ss-tag" :class="`tone-${variance_tone}`">
						<Icon :name="variance >= 0 ? 'check' : 'alert'" :size="13" />
						{{ variance_text }}
					</span>
				</div>
				<div
					class="ss-plan-bar"
					:aria-label="`จริง ${pct(progress.actual)}% แผน ${pct(progress.plan)}%`"
				>
					<span class="ss-plan-bar-plan" :style="{ width: `${clamp(progress.plan)}%` }"></span>
					<span class="ss-plan-bar-actual" :style="{ width: `${clamp(progress.actual)}%` }"></span>
				</div>
				<div class="ss-plan-foot">
					<span>{{ progress.basis === "Baseline" ? "เทียบ Baseline" : "เทียบแผนปัจจุบัน" }}</span>
					<span v-if="progress.finish_date"
						>สิ้นสุดสัญญา {{ thai_date(progress.finish_date, { year: true }) }} ·
						{{ days_left }}</span
					>
				</div>
			</div>

			<div v-if="summary?.curve?.length > 1" class="ss-plan ss-plan--curve">
				<h2 class="ss-section-title ss-section-title--first">S-Curve</h2>
				<SCurve :points="summary.curve" :basis="progress?.basis" />
			</div>

			<div class="ss-stats">
				<button
					v-for="(s, i) in stats"
					:key="s.key"
					type="button"
					class="ss-stat"
					:class="`tone-${s.tone}`"
					:style="{ '--i': i }"
					@click="go(s.view, s.params || {})"
				>
					<span class="ss-stat-icon"><Icon :name="s.icon" :size="20" /></span>
					<span class="ss-stat-value">
						<span v-if="loading" class="ss-sk ss-sk-number"></span>
						<template v-else>{{ s.value }}</template>
					</span>
					<span class="ss-stat-label">{{ s.label }}</span>
					<span v-if="s.alert" class="ss-stat-alert">{{ s.alert }}</span>
				</button>
			</div>

			<h2 class="ss-section-title">ทำรายการ</h2>
			<div class="ss-actions">
				<button
					v-for="(a, i) in actions"
					:key="a.label"
					type="button"
					class="ss-action"
					:class="`tone-${a.tone}`"
					:style="{ '--i': i }"
					:disabled="a.disabled"
					@click="a.run ? a.run() : open(a.url)"
				>
					<span class="ss-action-icon"><Icon :name="a.icon" :size="26" :stroke="2" /></span>
					<span class="ss-action-label">{{ a.label }}</span>
					<span class="ss-action-note">{{ a.note }}</span>
				</button>
			</div>

			<template v-if="summary?.requests_ready?.length">
				<h2 class="ss-section-title">
					อนุมัติแล้ว รอทำรายงาน
					<button type="button" class="ss-link" @click="go('reports', { tab: 'request' })">
						ดูทั้งหมด
					</button>
				</h2>
				<div class="ss-list">
					<button
						v-for="(r, i) in summary.requests_ready"
						:key="r.name"
						type="button"
						class="ss-card ss-card--row"
						:style="{ '--i': i }"
						@click="go('report-view', { kind: 'drq', name: r.name })"
					>
						<span class="ss-avatar tone-blue"><Icon name="clipboard-check" :size="18" /></span>
						<span class="ss-card-main">
							<span class="ss-card-title">{{ r.requested_by || r.name }}</span>
							<span class="ss-card-sub"
								>{{ r.name }} · คาดว่าได้ {{ pct(r.expected_progress) }}%</span
							>
						</span>
						<span class="ss-due" :class="{ 'is-late': r.date < today() }">{{
							relative_date(r.date)
						}}</span>
					</button>
				</div>
			</template>

			<template v-if="summary?.late_tasks?.length">
				<h2 class="ss-section-title">
					งานที่ช้ากว่าแผน
					<span class="ss-count">{{ summary.late_count }}</span>
				</h2>
				<div class="ss-list">
					<div
						v-for="(t, i) in summary.late_tasks"
						:key="t.wbs"
						class="ss-card ss-late"
						:style="{ '--i': i }"
					>
						<div class="ss-card-head">
							<span class="ss-card-main">
								<span class="ss-card-title">{{ t.item_name }}</span>
								<span class="ss-card-meta">
									<i class="ss-wbs">{{ t.wbs }}</i>
									{{ t.status_label }}
									<span v-if="t.critical" class="ss-tag tone-rose">
										<Icon name="flag" :size="12" /> วิกฤต
									</span>
								</span>
							</span>
							<span v-if="t.delay_days > 0" class="ss-due is-late"
								>ช้า {{ t.delay_days }} วัน</span
							>
						</div>
						<div class="ss-plan-bar ss-plan-bar--sm">
							<span class="ss-plan-bar-plan" :style="{ width: `${clamp(t.plan_pct)}%` }"></span>
							<span
								class="ss-plan-bar-actual"
								:style="{ width: `${clamp(t.actual_pct)}%` }"
							></span>
						</div>
						<div class="ss-late-foot">
							<span>จริง {{ pct(t.actual_pct) }}%</span>
							<span>แผน {{ pct(t.plan_pct) }}%</span>
						</div>
					</div>
				</div>
			</template>
		</div>
	</div>
</template>

<script setup>
import { computed, inject, onMounted } from "vue";
import Icon from "../../components/Icon.vue";
import Empty from "../../components/Empty.vue";
import Hero from "../../components/Hero.vue";
import SCurve from "../../components/SCurve.vue";
import { boot, desk_new_url, go, relative_date, state, thai_date, today } from "../../api.js";

defineEmits(["pick-project"]);
const reload_summary = inject("reload_summary");

const summary = computed(() => state.summaries.work);
const loading = computed(() => !summary.value);
const progress = computed(() => summary.value?.progress);
const cm = computed(() => summary.value?.construction_management);

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
	const days = Math.round((new Date(progress.value.finish_date) - new Date(today())) / 86400000);
	if (days === 0) return "วันนี้";
	return days > 0 ? `อีก ${days} วัน` : `เลยมา ${-days} วัน`;
});

const stats = computed(() => {
	const s = summary.value || {};
	return [
		{
			key: "today",
			label: "รายงานวันนี้",
			value: s.reports_today ?? 0,
			icon: "clipboard",
			tone: "orange",
			view: "reports",
			alert: s.report_drafts ? `ร่าง ${s.report_drafts}` : "",
		},
		{
			key: "request",
			label: "รออนุมัติ",
			value: s.requests_pending ?? 0,
			icon: "send",
			tone: "blue",
			view: "reports",
			params: { tab: "request" },
		},
		{
			key: "inspection",
			label: "รอตรวจงาน",
			value: s.inspections_pending ?? 0,
			icon: "search-check",
			tone: "teal",
			view: "inspections",
			alert: s.inspections_failed ? `ไม่ผ่าน ${s.inspections_failed}` : "",
		},
		{
			key: "punch",
			label: "Punch List ค้างแก้",
			value: s.punch_open ?? 0,
			icon: "list-checks",
			tone: s.punch_open ? "rose" : "green",
			view: "inspections",
			params: { tab: "punch" },
		},
	];
});

const actions = computed(() => {
	const values = { construction_management: cm.value };
	return [
		{
			label: "เขียนรายงาน",
			note: "Daily Report ของวันนี้",
			icon: "clipboard",
			tone: "orange",
			disabled: !cm.value || !boot.can.daily_report,
			run: () => go("report-form", { kind: "dr", name: "new", date: today() }),
		},
		{
			label: "ขออนุมัติล่วงหน้า",
			note: "Daily Request ล่วงหน้า",
			icon: "send",
			tone: "blue",
			disabled: !cm.value || !boot.can.daily_request,
			run: () => go("report-form", { kind: "drq", name: "new", date: today() }),
		},
		{
			label: "ขอตรวจงาน",
			note: "เปิดในระบบเต็ม",
			icon: "search-check",
			tone: "teal",
			disabled: !cm.value || !boot.can.inspection,
			url: desk_new_url("Inspection Request", values),
		},
		{
			label: "เทคอนกรีต",
			note: "บันทึกตั๋วรถทีละคัน",
			icon: "truck",
			tone: "violet",
			disabled: !cm.value || !boot.can.concrete,
			run: () => go("concrete"),
		},
	];
});

function open(url) {
	if (url) window.location.href = url;
}

onMounted(() => {
	if (state.project) reload_summary();
});
</script>
