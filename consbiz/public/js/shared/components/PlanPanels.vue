<!-- หน้าภาพรวม (ควบคุมงาน, แผนงาน): งานที่ช้ากว่าแผน + ความคืบหน้าแต่ละหมวด ซ้าย-ขวาเท่ากันใน .ss-dash / .ss-pm-board
     แถวสูงคงที่ แบ่งหน้าแทนการยาวลงไปเรื่อยๆ (Design.md "หน้าภาพรวม") ข้อมูลจาก dashboard.late_tasks / category_progress -->
<template>
	<div class="ss-dash-halves">
		<section class="ss-dash-half">
			<h2 class="ss-section-title">
				งานที่ช้ากว่าแผน
				<span v-if="tasks.length" class="ss-count">{{ tasks.length }}</span>
			</h2>
			<PagedList
				v-if="tasks.length"
				v-slot="{ row: t }"
				:rows="tasks"
				row_key="wbs"
				:page_size="LATE_PAGE_SIZE"
				:row_height="LATE_ROW_HEIGHT"
			>
				<div class="ss-late-row">
					<div class="ss-late-row-head">
						<i class="ss-wbs">{{ t.wbs }}</i>
						<b :title="t.item_name">{{ t.item_name }}</b>
						<span v-if="t.critical" class="ss-tag tone-rose">
							<Icon name="flag" :size="12" /> วิกฤต
						</span>
						<span v-if="t.delay_days > 0" class="ss-due is-late"
							>ช้า {{ t.delay_days }} วัน</span
						>
					</div>
					<div class="ss-late-row-foot">
						<span class="ss-late-row-status" :title="t.status_label">{{
							t.status_label
						}}</span>
						<div class="ss-plan-bar ss-plan-bar--sm">
							<span
								class="ss-plan-bar-plan"
								:style="{ width: `${clamp(t.plan_pct)}%` }"
							></span>
							<span
								class="ss-plan-bar-actual"
								:style="{ width: `${clamp(t.actual_pct)}%` }"
							></span>
						</div>
						<span>จริง {{ pct(t.actual_pct) }}% · แผน {{ pct(t.plan_pct) }}%</span>
					</div>
				</div>
			</PagedList>
			<div v-else class="ss-plan ss-dash-none">
				<Icon name="check" :size="16" /> ไม่มีงานที่ช้ากว่าแผน
			</div>
		</section>

		<section class="ss-dash-half">
			<h2 class="ss-section-title">ความคืบหน้าแต่ละหมวด</h2>
			<div class="ss-plan ss-category-card">
				<PagedList
					v-slot="{ row: c }"
					:rows="categories"
					row_key="wbs"
					:page_size="CATEGORY_PAGE_SIZE"
					:row_height="CATEGORY_ROW_HEIGHT"
				>
					<div class="ss-category">
						<div class="ss-category-head">
							<i class="ss-wbs">{{ c.wbs }}</i>
							<span :title="c.item_name">{{ c.item_name }}</span>
							<b>{{ pct(c.percent) }}%</b>
						</div>
						<div
							class="ss-plan-bar ss-plan-bar--sm"
							:aria-label="`${c.item_name} ${pct(c.percent)}%`"
						>
							<span
								class="ss-plan-bar-actual"
								:style="{ width: `${clamp(c.percent)}%` }"
							></span>
						</div>
					</div>
				</PagedList>
			</div>
		</section>
	</div>
</template>

<script setup>
import Icon from "./Icon.vue";
import PagedList from "./PagedList.vue";

defineProps({
	tasks: { type: Array, default: () => [] },
	categories: { type: Array, default: () => [] },
});

const LATE_PAGE_SIZE = 5;
const LATE_ROW_HEIGHT = 62;
const CATEGORY_PAGE_SIZE = 6;
const CATEGORY_ROW_HEIGHT = 42;

const pct = (value) =>
	(Number(value) || 0).toLocaleString("th-TH", {
		minimumFractionDigits: 0,
		maximumFractionDigits: 1,
	});
const clamp = (value) => Math.max(0, Math.min(100, Number(value) || 0));
</script>
