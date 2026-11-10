<template>
	<div>
		<Hero />

		<div v-if="!state.project" class="ss-content">
			<Empty
				icon="building"
				title="ยังไม่ได้เลือกโครงการ"
				text="เลือกโครงการที่ดูแลเพื่อเริ่มใช้งาน"
			>
				<button
					type="button"
					class="ss-btn ss-btn--primary"
					@click="$emit('pick-project')"
				>
					เลือกโครงการ
				</button>
			</Empty>
		</div>

		<div v-else class="ss-content ss-pm-content">
			<div v-if="!loaded" class="ss-plan ss-plan--loading">
				<span class="ss-sk ss-sk-number"></span>
				<span class="ss-sk ss-sk-line"></span>
			</div>
			<Empty
				v-else-if="!d"
				icon="layers"
				title="โครงการนี้ยังไม่มีแผนงาน"
				text="สร้างแผนงานก่อสร้าง (Construction Management) ของโครงการในระบบเต็มก่อน"
			/>
			<!-- มือถือเรียงตามลำดับนี้ แท็บเล็ต/จอใหญ่จัดตำแหน่งด้วยกริดใน style.css -->
			<div v-else class="ss-pm-board" :class="{ 'has-curve': d.curve?.length > 1 }">
				<!-- เวลาเทียบงาน -->
				<div class="ss-plan ss-pm-progress">
					<div class="ss-plan-head">
						<div class="ss-plan-figure">
							<span>งานเสร็จ</span>
							<b>{{ pct(d.progress.actual) }}<small>%</small></b>
						</div>
						<div class="ss-plan-figure is-plan">
							<span>ตามแผน</span>
							<b>{{ pct(d.progress.plan) }}<small>%</small></b>
						</div>
						<div class="ss-plan-figure is-plan">
							<span>เวลาผ่านไป</span>
							<b>{{ pct(time_used) }}<small>%</small></b>
						</div>
					</div>
					<div class="ss-plan-bar">
						<span
							class="ss-plan-bar-plan"
							:style="{ width: `${clamp(d.progress.plan)}%` }"
						></span>
						<span
							class="ss-plan-bar-actual"
							:style="{ width: `${clamp(d.progress.actual)}%` }"
						></span>
					</div>
					<div class="ss-pm-dates">
						<div>
							<span>เริ่มสัญญา</span
							><b>{{ thai_date(d.schedule.start_date, { year: true }) }}</b>
						</div>
						<div>
							<span>สิ้นสุดสัญญา</span
							><b>{{ thai_date(d.schedule.contract_finish, { year: true }) }}</b>
							<small v-if="d.schedule.extension_days"
								>ขยาย {{ d.schedule.extension_days }} วัน</small
							>
						</div>
						<div :class="{ 'is-late': d.schedule.overrun_days > 0 }">
							<span>คาดว่าเสร็จ</span
							><b>{{ thai_date(d.schedule.forecast_finish, { year: true }) }}</b>
							<small v-if="d.schedule.overrun_days > 0"
								>เกินสัญญา {{ d.schedule.overrun_days }} วัน</small
							>
							<small v-else>{{ days_left }}</small>
						</div>
					</div>
					<div
						v-if="d.show_values && (d.schedule.penalty > 0 || d.schedule.warning)"
						class="ss-banner tone-rose"
					>
						<Icon name="alert" :size="22" />
						<div>
							<div class="ss-banner-title">
								ค่าปรับคาดการณ์ {{ money(d.schedule.penalty) }}
							</div>
							<div class="ss-banner-text">
								{{
									d.schedule.warning ||
									`${pct(d.schedule.penalty_percent)}% ของมูลค่าสัญญา`
								}}
							</div>
						</div>
					</div>
				</div>

				<div v-if="d.curve?.length > 1" class="ss-plan ss-plan--curve ss-pm-curve">
					<h2 class="ss-section-title ss-section-title--first">S-Curve</h2>
					<SCurve :points="d.curve" :basis="d.progress.basis" fill />
				</div>

				<!-- สถานะงาน -->
				<div class="ss-plan ss-pm-status">
					<h2 class="ss-section-title ss-section-title--first">
						สถานะงาน <span class="ss-section-total">{{ d.tasks.total }} งาน</span>
					</h2>
					<div
						class="ss-stack"
						role="img"
						:aria-label="status_parts.map((p) => `${p.label} ${p.count}`).join(', ')"
					>
						<span
							v-for="p in status_parts"
							:key="p.key"
							:class="`tone-${p.tone}`"
							:style="{ flexGrow: p.count }"
							:title="`${p.label} ${p.count}`"
						></span>
					</div>
					<div class="ss-stack-legend">
						<button
							v-for="p in status_parts"
							:key="p.key"
							type="button"
							:class="`tone-${p.tone}`"
							@click="go('plan')"
						>
							<i></i>{{ p.label }} <b>{{ p.count }}</b>
						</button>
					</div>
				</div>

				<div class="ss-stats">
					<div v-if="d.show_values" class="ss-stat tone-blue" style="--i: 0">
						<span class="ss-stat-icon"><Icon name="file" :size="20" /></span>
						<span class="ss-stat-value ss-stat-value--money">{{
							money_short(d.contract.revised_amount)
						}}</span>
						<span class="ss-stat-label"
							>มูลค่าสัญญา{{ d.contract.variation_amount ? "ปรับปรุง" : "" }}</span
						>
						<span v-if="d.contract.pending_count" class="ss-stat-alert"
							>VO รอ {{ d.contract.pending_count }}</span
						>
					</div>
					<div v-if="d.show_values" class="ss-stat tone-violet" style="--i: 1">
						<span class="ss-stat-icon"><Icon name="layers" :size="20" /></span>
						<span class="ss-stat-value ss-stat-value--money"
							>{{ d.contract.variation_amount > 0 ? "+" : ""
							}}{{ money_short(d.contract.variation_amount) }}</span
						>
						<span class="ss-stat-label">งานลด-งานเพิ่ม (อนุมัติแล้ว)</span>
					</div>
					<div
						v-if="d.evm"
						class="ss-stat"
						:class="d.evm.spi < 0.95 ? 'tone-rose' : 'tone-green'"
						style="--i: 2"
					>
						<span class="ss-stat-icon"><Icon name="trending" :size="20" /></span>
						<span class="ss-stat-value">{{ ratio(d.evm.spi) }}</span>
						<span class="ss-stat-label">SPI · CPI {{ ratio(d.evm.cpi) }}</span>
					</div>
					<div class="ss-stat tone-amber" style="--i: 3">
						<span class="ss-stat-icon"><Icon name="clock" :size="20" /></span>
						<span class="ss-stat-value">{{ d.extensions.pending_count }}</span>
						<span class="ss-stat-label">ขอขยายเวลา รออนุมัติ</span>
					</div>
					<div class="ss-stat tone-teal" style="--i: 4">
						<span class="ss-stat-icon"><Icon name="search-check" :size="20" /></span>
						<span class="ss-stat-value">{{ d.quality.pending }}</span>
						<span class="ss-stat-label">รอตรวจงาน</span>
						<span v-if="d.quality.failed" class="ss-stat-alert"
							>ไม่ผ่าน {{ d.quality.failed }}</span
						>
					</div>
					<div v-if="d.materials" class="ss-stat tone-orange" style="--i: 5">
						<span class="ss-stat-icon"><Icon name="cart" :size="20" /></span>
						<span class="ss-stat-value">{{ d.materials.late + d.materials.due }}</span>
						<span class="ss-stat-label"
							>วัสดุต้องสั่งใน {{ d.materials.days }} วัน</span
						>
						<span v-if="d.materials.late" class="ss-stat-alert"
							>เลยกำหนด {{ d.materials.late }}</span
						>
					</div>
				</div>

				<PlanPanels
					v-if="d.categories?.length"
					:tasks="d.late_tasks"
					:categories="d.categories"
				/>

				<div class="ss-pm-links">
					<button
						type="button"
						class="ss-btn ss-btn--ghost ss-btn--lg ss-btn--block"
						@click="go('pm-docs')"
					>
						<Icon name="file" :size="17" /> เอกสารโครงการ
					</button>
					<a
						v-if="d.can_edit_plan"
						class="ss-btn ss-btn--soft ss-btn--lg ss-btn--block"
						:href="`/app/construction-gantt/${encodeURIComponent(
							d.construction_management
						)}`"
					>
						<Icon name="pen" :size="17" /> แก้แผนงาน (ระบบเต็ม)
					</a>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup>
import { computed, inject, onMounted } from "vue";
import Icon from "../../../shared/components/Icon.vue";
import Empty from "../../../shared/components/Empty.vue";
import Hero from "../../../shared/components/Hero.vue";
import PlanPanels from "../../../shared/components/PlanPanels.vue";
import SCurve from "../../../shared/components/SCurve.vue";
import { go, state, thai_date, today } from "../../../shared/api.js";

defineEmits(["pick-project"]);
const reload_summary = inject("reload_summary");

// undefined = ยังไม่โหลด, null = ไม่มีแผนงาน
const loaded = computed(() => state.summaries.pm !== undefined);
const d = computed(() => state.summaries.pm);

const pct = (v) => (Number(v) || 0).toLocaleString("th-TH", { maximumFractionDigits: 1 });
const clamp = (v) => Math.max(0, Math.min(100, Number(v) || 0));
const ratio = (v) => (v === null || v === undefined ? "–" : Number(v).toFixed(2));
const money = (v) =>
	`${(Number(v) || 0).toLocaleString("th-TH", { maximumFractionDigits: 2 })} บาท`;
function money_short(v) {
	const n = Number(v) || 0;
	if (Math.abs(n) >= 1e6)
		return `${(n / 1e6).toLocaleString("th-TH", { maximumFractionDigits: 2 })} ล้าน`;
	if (Math.abs(n) >= 1e3)
		return `${(n / 1e3).toLocaleString("th-TH", { maximumFractionDigits: 1 })} พัน`;
	return n.toLocaleString("th-TH");
}

const days_between = (a, b) => Math.round((new Date(b) - new Date(a)) / 86400000);
const time_used = computed(() => {
	const s = d.value?.schedule;
	if (!s?.start_date || !s.contract_finish) return 0;
	return (
		(days_between(s.start_date, today()) /
			Math.max(1, days_between(s.start_date, s.contract_finish))) *
		100
	);
});
const days_left = computed(() => {
	const days = days_between(today(), d.value.schedule.contract_finish);
	return days >= 0 ? `อีก ${days} วัน` : `เลยมา ${-days} วัน`;
});

// สถานะงาน (delay.STATUS) เรียงจากเสร็จ → ล่าช้า
const STATUS_PARTS = [
	["done", "เสร็จแล้ว", "green"],
	["on_track", "ตามแผน", "blue"],
	["behind", "ช้ากว่าแผน", "amber"],
	["not_started", "ควรเริ่มแล้ว", "orange"],
	["overdue", "ควรเสร็จแล้ว", "rose"],
	["not_due", "ยังไม่ถึงกำหนด", "gray"],
];
const status_parts = computed(() =>
	STATUS_PARTS.map(([key, label, tone]) => ({
		key,
		label,
		tone,
		count: d.value.tasks.counts[key] || 0,
	})).filter((p) => p.count)
);

onMounted(() => {
	if (state.project) reload_summary();
});
</script>
