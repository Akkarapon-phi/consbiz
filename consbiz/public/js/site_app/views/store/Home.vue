<template>
	<div>
		<Hero @pick-project="$emit('pick-project')" />

		<div v-if="state.project" class="ss-content ss-content--lift">
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
					@click="a.run"
				>
					<span class="ss-action-icon"><Icon :name="a.icon" :size="26" :stroke="2" /></span>
					<span class="ss-action-label">{{ a.label }}</span>
					<span class="ss-action-note">{{ a.note }}</span>
				</button>
			</div>

			<template v-if="summary?.due_soon?.length">
				<h2 class="ss-section-title">
					ของที่รอรับ
					<button type="button" class="ss-link" @click="go('receive')">ดูทั้งหมด</button>
				</h2>
				<div class="ss-list">
					<button
						v-for="(d, i) in summary.due_soon"
						:key="d.name"
						type="button"
						class="ss-card ss-card--row"
						:style="{ '--i': i }"
						@click="go('receive-form', { doctype: d.doctype, name: d.name })"
					>
						<span class="ss-avatar" :class="`tone-${d.employer ? 'violet' : tone(d.party)}`">{{
							initials(d.party)
						}}</span>
						<span class="ss-card-main">
							<span class="ss-card-title">{{ d.party }}</span>
							<span class="ss-card-sub"
								>{{ d.items.names.join(", ")
								}}<template v-if="d.items.count > 3">
									+{{ d.items.count - 3 }}</template
								></span
							>
						</span>
						<span class="ss-due" :class="{ 'is-late': d.overdue }">{{
							relative_date(d.schedule_date)
						}}</span>
					</button>
				</div>
			</template>
		</div>

		<div v-else class="ss-content ss-content--lift">
			<Empty icon="building" title="ยังไม่ได้เลือกโครงการ" text="เลือกโครงการที่ดูแลเพื่อเริ่มใช้งาน">
				<button type="button" class="ss-btn ss-btn--primary" @click="$emit('pick-project')">
					เลือกโครงการ
				</button>
			</Empty>
		</div>
	</div>
</template>

<script setup>
import { computed, inject, onMounted } from "vue";
import Icon from "../../components/Icon.vue";
import Empty from "../../components/Empty.vue";
import Hero from "../../components/Hero.vue";
import { go, initials, num, relative_date, state, toast, tone } from "../../api.js";

defineEmits(["pick-project"]);
const reload_summary = inject("reload_summary");

const summary = computed(() => state.summary);
const loading = computed(() => !state.summary);

const stats = computed(() => {
	const s = summary.value || {};
	return [
		{
			key: "pending",
			label: "รอรับของ",
			value: s.pending_count ?? 0,
			icon: "receive",
			tone: "blue",
			view: "receive",
		},
		{
			key: "borrow",
			label: "อุปกรณ์ค้างคืน",
			value: s.borrow_count ?? 0,
			icon: "wrench",
			tone: s.overdue_count ? "rose" : "amber",
			view: "borrow",
			alert: s.overdue_count ? `เกินกำหนด ${s.overdue_count}` : "",
		},
		{
			key: "issue",
			label: "ใบเบิกวันนี้",
			value: s.issues_today ?? 0,
			icon: "issue",
			tone: "teal",
			view: "issue",
			params: { tab: "history" },
		},
		{
			key: "received",
			label: "รับของวันนี้ (ใบ)",
			value: s.receipts_today ?? 0,
			icon: "package",
			tone: "violet",
			view: "receive",
			params: { tab: "done" },
		},
	];
});

const actions = computed(() => [
	{
		label: "รับของ",
		note: "ตรวจรับตามใบสั่งซื้อ",
		icon: "receive",
		tone: "blue",
		run: () => go("receive"),
	},
	{ label: "เบิกวัสดุ", note: "ตัดของผู้ว่าจ้างก่อน", icon: "issue", tone: "teal", run: () => go("issue") },
	{
		label: "ยืมอุปกรณ์",
		note: "ผู้ยืมเซ็นรับ",
		icon: "wrench",
		tone: "amber",
		run: () => go("borrow-new"),
	},
]);

onMounted(() => {
	if (state.project) reload_summary();
	if (summary.value && !summary.value.warehouse)
		toast("โครงการนี้ยังไม่มีคลัง ตั้งคลังที่หน้า Project ก่อน", "warning");
});
</script>
