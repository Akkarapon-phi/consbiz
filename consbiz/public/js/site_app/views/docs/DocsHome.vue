<template>
	<!-- หน้าหลักของหมวดจัดซื้อ / ขาย (ชุดเดียวกัน ข้อมูลจาก site_docs.get_summary) -->
	<div>
		<Hero @pick-project="$emit('pick-project')" />

		<div class="ss-content ss-content--lift">
			<ScopeSwitch />

			<div class="ss-stats">
				<button
					v-for="(s, i) in stats"
					:key="s.key"
					type="button"
					class="ss-stat"
					:class="`tone-${s.tone}`"
					:style="{ '--i': i }"
					@click="go(s.view, { filter: s.filter || 'todo' })"
				>
					<span class="ss-stat-icon"><Icon :name="s.icon" :size="20" /></span>
					<span class="ss-stat-value" :class="{ 'ss-stat-value--money': s.money }">
						<span v-if="loading" class="ss-sk ss-sk-number"></span>
						<template v-else>{{ s.value }}</template>
					</span>
					<span class="ss-stat-label">{{ s.label }}</span>
					<span v-if="s.alert" class="ss-stat-alert">{{ s.alert }}</span>
				</button>
			</div>

			<h2 class="ss-section-title">สร้างเอกสาร</h2>
			<div class="ss-create-row">
				<button
					v-for="k in kinds"
					:key="k.key"
					type="button"
					class="ss-btn ss-btn--soft"
					@click="go(`${section}-form`, { kind: k.key, name: 'new' })"
				>
					<Icon name="plus" :size="16" :stroke="2.6" /> {{ k.label }}
				</button>
			</div>

			<h2 class="ss-section-title">เอกสาร</h2>
			<div class="ss-actions">
				<button
					v-for="(k, i) in kinds"
					:key="k.key"
					type="button"
					class="ss-action"
					:class="`tone-${k.tone}`"
					:style="{ '--i': i }"
					@click="go(k.key)"
				>
					<span class="ss-action-icon"><Icon :name="k.icon" :size="26" :stroke="2" /></span>
					<span class="ss-action-label">{{ k.label }}</span>
					<span class="ss-action-note">{{ k.todo }}</span>
				</button>
				<button
					v-if="summary?.drafts"
					type="button"
					class="ss-action tone-gray"
					:style="{ '--i': kinds.length }"
					@click="go(kinds[0].key, { filter: 'draft' })"
				>
					<span class="ss-action-icon"><Icon name="pen" :size="24" :stroke="2" /></span>
					<span class="ss-action-label">ร่าง {{ summary.drafts }} ฉบับ</span>
					<span class="ss-action-note">ยังไม่ได้ส่ง</span>
				</button>
			</div>

			<template v-for="block in lists" :key="block.title">
				<template v-if="block.rows?.length">
					<h2 class="ss-section-title">
						{{ block.title }}
						<button type="button" class="ss-link" @click="go(block.view, { filter: 'todo' })">
							ดูทั้งหมด
						</button>
					</h2>
					<div class="ss-list">
						<DocCard
							v-for="(row, i) in block.rows"
							:key="row.name"
							:row="row"
							:kind="row.kind"
							:i="i"
						/>
					</div>
				</template>
			</template>
		</div>
	</div>
</template>

<script setup>
import { computed, inject, onMounted, watch } from "vue";
import Icon from "../../components/Icon.vue";
import Hero from "../../components/Hero.vue";
import DocCard from "./DocCard.vue";
import ScopeSwitch from "./ScopeSwitch.vue";
import { DOC_KINDS } from "../../sections.js";
import { go, money, state } from "../../api.js";

defineEmits(["pick-project"]);
const reload_summary = inject("reload_summary");

const section = state.section;
const summary = computed(() => state.summaries[section]);
const loading = computed(() => !summary.value);
const kinds = Object.entries(DOC_KINDS)
	.filter(([, k]) => k.section === section)
	.map(([key, k]) => ({ key, ...k }));

const stats = computed(() => {
	const s = summary.value || {};
	if (section === "buy") {
		return [
			{
				key: "mr",
				label: "ขอซื้อ รอสั่งซื้อ",
				value: s.mr_todo?.count ?? 0,
				icon: "clipboard",
				tone: "teal",
				view: "mr",
			},
			{
				key: "po",
				label: `สั่งซื้อ รอรับของ (${s.po_receive?.count ?? 0} ใบ)`,
				value: money(s.po_receive?.amount, { short: true }),
				money: true,
				icon: "cart",
				tone: "blue",
				view: "po",
			},
			{
				key: "pi",
				label: `ค้างจ่าย (${s.pi_unpaid?.count ?? 0} ใบ)`,
				value: money(s.pi_unpaid?.amount, { short: true }),
				money: true,
				icon: "file",
				tone: "violet",
				view: "pi",
			},
			{
				key: "overdue",
				label: "เกินกำหนดจ่าย",
				value: money(s.pi_overdue?.amount, { short: true }),
				money: true,
				icon: "alert",
				tone: s.pi_overdue?.count ? "rose" : "green",
				view: "pi",
				alert: s.pi_overdue?.count ? `${s.pi_overdue.count} ใบ` : "",
			},
		];
	}
	return [
		{
			key: "qtn",
			label: `เสนอราคา รอตอบรับ (${s.qtn_open?.count ?? 0} ใบ)`,
			value: money(s.qtn_open?.amount, { short: true }),
			money: true,
			icon: "file",
			tone: "violet",
			view: "qtn",
		},
		{
			key: "so",
			label: `สั่งขาย รอส่งมอบ/วางบิล (${s.so_todo?.count ?? 0} ใบ)`,
			value: money(s.so_todo?.amount, { short: true }),
			money: true,
			icon: "clipboard-check",
			tone: "blue",
			view: "so",
		},
		{
			key: "si",
			label: `ค้างรับ (${s.si_unpaid?.count ?? 0} ใบ)`,
			value: money(s.si_unpaid?.amount, { short: true }),
			money: true,
			icon: "receive",
			tone: "green",
			view: "si",
		},
		{
			key: "overdue",
			label: "เกินกำหนดรับ",
			value: money(s.si_overdue?.amount, { short: true }),
			money: true,
			icon: "alert",
			tone: s.si_overdue?.count ? "rose" : "green",
			view: "si",
			alert: s.si_overdue?.count ? `${s.si_overdue.count} ใบ` : "",
		},
	];
});

const lists = computed(() => {
	const s = summary.value || {};
	return section === "buy"
		? [
				{ title: "ถึงกำหนดรับของ (7 วัน)", rows: s.due_soon, view: "po" },
				{ title: "ถึงกำหนดจ่าย (7 วัน)", rows: s.to_pay, view: "pi" },
		  ]
		: [
				{ title: "ใบเสนอราคาใกล้หมดอายุ", rows: s.expiring, view: "qtn" },
				{ title: "ถึงกำหนดรับเงิน (7 วัน)", rows: s.to_collect, view: "si" },
		  ];
});

// เปลี่ยนขอบเขต โครงการนี้/ทุกโครงการ: โหลดตัวเลขใหม่
watch(
	() => state.doc_scope,
	() => {
		state.summaries[section] = null;
		reload_summary();
	}
);
onMounted(() => {
	if (state.project) reload_summary();
});
</script>
