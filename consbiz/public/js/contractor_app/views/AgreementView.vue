<!-- สัญญา 1 ฉบับของผู้รับเหมา (ดูอย่างเดียว): ยอดสรุป รายการงาน (งานหลัก + งานเพิ่มแนบท้าย) งวดงาน ใบเบิก
     ปุ่ม "สร้างใบเบิกงวด" เมื่อสัญญาดำเนินการอยู่และไม่มีใบเบิกที่ยังไม่อนุมัติ (contractor_app.get_agreement) -->
<template>
	<div>
		<!-- เปิดจากลิงก์: หน้านี้คือหน้าแรก (ไม่มีปุ่มย้อนกลับ) -->
		<TopBar
			:title="doc?.title || 'สัญญา'"
			:subtitle="doc?.project_name"
			:back_to="boot.agreement ? undefined : 'contractor'"
			no_project
		/>

		<div class="ss-content">
			<Skeleton v-if="!doc" :rows="5" />
			<template v-else>
				<ListHead
					v-model="tab"
					:tabs="TABS"
					:create="view.can_claim ? 'สร้างใบเบิกงวด' : ''"
					@create="go('contractor-claim', { name: 'new', agreement: doc.name })"
				>
					<template #tools>
						<button
							v-if="view.open_claim"
							type="button"
							class="ss-btn ss-btn--soft ss-list-create"
							@click="go('contractor-claim', { name: view.open_claim })"
						>
							ใบเบิกที่ค้างอยู่
						</button>
					</template>
				</ListHead>

				<section v-if="tab === 'summary'" class="ss-card">
					<div class="ss-doc-head-top">
						<span class="ss-tag" :class="`tone-${doc.status_tone}`">{{ doc.status_label }}</span>
						<span class="ss-doc-date">{{ doc.name }}</span>
					</div>
					<span class="ss-progress ss-progress--lg">
						<span :style="{ width: `${Math.min(doc.progress_percent || 0, 100)}%` }"></span>
						<em>เบิกแล้ว {{ num(doc.progress_percent) }}%</em>
					</span>
					<div class="ss-facts ss-facts--grid">
						<div v-for="f in facts" :key="f.label" class="ss-fact">
							<span>{{ f.label }}</span><b>{{ f.value }}</b>
						</div>
					</div>
					<p v-if="doc.status === 'Closed' && doc.close_reason" class="ss-muted">
						ปิดสัญญา {{ thai_date(doc.closed_on, { year: true }) }}: {{ doc.close_reason }}
					</p>
				</section>

				<section v-else-if="tab === 'items'" class="ss-card">
					<template v-for="g in groups" :key="g.key">
						<h2 v-if="g.label" class="ss-section-title">{{ g.label }}</h2>
						<div class="ss-facts">
							<div v-for="r in g.rows" :key="r.name" class="ss-fact">
								<span
									>{{ r.item_name }}<br /><small
										>{{ num(r.qty) }} {{ r.uom || "" }} x {{ money(r.rate) }} · เบิกแล้ว
										{{ num(r.claimed_qty) }}</small
									></span
								>
								<b>{{ money(r.amount) }}</b>
							</div>
						</div>
					</template>
					<template v-if="doc.billing_method === 'Milestone' && doc.milestones.length">
						<h2 class="ss-section-title">งวดงาน</h2>
						<div class="ss-facts">
							<div v-for="m in doc.milestones" :key="m.name" class="ss-fact">
								<span
									>{{ m.description }} ({{ num(m.percent) }}%)
									<small v-if="m.target_date"
										><br />กำหนด {{ thai_date(m.target_date, { year: true }) }}</small
									></span
								>
								<b>{{ money(m.amount) }}</b>
							</div>
						</div>
					</template>
				</section>

				<section v-else class="ss-card">
					<Empty v-if="!view.claims.length" icon="receive" title="ยังไม่มีใบเบิก" />
					<div v-else class="ss-list">
						<button
							v-for="c in view.claims"
							:key="c.name"
							type="button"
							class="ss-card ss-card--row"
							@click="go('contractor-claim', { name: c.name })"
						>
							<span class="ss-card-main">
								<span class="ss-card-title">งวดที่ {{ c.claim_no }}</span>
								<span class="ss-card-meta"
									>{{ thai_date(c.posting_date, { year: true }) }} ·
									<span class="ss-tag" :class="`tone-${c.status_tone}`">{{
										c.status_label
									}}</span></span
								>
							</span>
							<span class="ss-qty"><b>{{ money(c.gross_amount) }}</b><small>บาท</small></span>
						</button>
					</div>
					<template v-if="view.variations.length">
						<h2 class="ss-section-title">งานเพิ่ม (รายการแนบท้าย)</h2>
						<div class="ss-facts">
							<div v-for="v in view.variations" :key="v.name" class="ss-fact">
								<span
									>ครั้งที่ {{ v.revision_no }} · {{ thai_date(v.posting_date, { year: true }) }}
									<small v-if="v.reason"><br />{{ v.reason }}</small></span
								>
								<b>+{{ money(v.addition_amount) }}</b>
							</div>
						</div>
					</template>
				</section>
			</template>
		</div>
	</div>
</template>

<script setup>
import { computed, ref } from "vue";
import Empty from "../../shared/components/Empty.vue";
import Skeleton from "../../shared/components/Skeleton.vue";
import TopBar from "../../shared/components/TopBar.vue";
import ListHead from "../../shared/components/ListHead.vue";
import { back, boot, go, money, num, show_error, state, thai_date } from "../../shared/api.js";
import { capi } from "../api.js";

const TABS = [
	{ value: "summary", label: "สรุป" },
	{ value: "items", label: "รายการงาน" },
	{ value: "claims", label: "ใบเบิก" },
];
const tab = ref("summary");
const view = ref({});
const doc = computed(() => view.value.doc);

const groups = computed(() => {
	const out = [{ key: "main", label: null, rows: [] }];
	for (const r of doc.value?.items || []) {
		if (!r.variation) out[0].rows.push(r);
		else {
			let g = out.find((x) => x.key === r.variation);
			if (!g) out.push((g = { key: r.variation, label: `งานเพิ่ม ${r.variation}`, rows: [] }));
			g.rows.push(r);
		}
	}
	if (out.length > 1 && out[0].rows.length) out[0].label = "งานหลักตามสัญญา";
	return out.filter((g) => g.rows.length);
});

const facts = computed(() => {
	const d = doc.value;
	const rows = [
		["มูลค่าสัญญา", money(d.total_amount)],
		...(Number(d.variation_amount)
			? [
					["งานหลัก", money(d.original_amount)],
					[`งานเพิ่ม (${d.revision || 0} ครั้ง)`, money(d.variation_amount)],
			  ]
			: []),
		["เบิกแล้ว", money(d.claimed_amount)],
		["คงเหลือ", money((d.total_amount || 0) - (d.claimed_amount || 0))],
		["วิธีเบิก", d.billing_method === "Milestone" ? "ตามงวดงาน" : "ตามปริมาณงานจริง"],
		["ระยะสัญญา", `${thai_date(d.start_date, { year: true })} – ${thai_date(d.end_date, { year: true })}`],
		[
			`เงินประกันผลงาน ${num(d.retention_percent)}%${
				d.retention_cap_percent ? ` (เพดาน ${num(d.retention_cap_percent)}%)` : ""
			}`,
			`หักแล้ว ${money(d.retention_held)}`,
		],
		[`หัก ณ ที่จ่าย`, `${num(d.wht_percent)}%`],
	];
	if (Number(d.advance_amount))
		rows.push([
			`เงินล่วงหน้า ${num(d.advance_percent)}% (หักคืนงวดละ ${num(d.advance_recovery_percent)}%)`,
			`${money(d.advance_amount)} · หักคืนแล้ว ${money(d.advance_recovered)}`,
		]);
	if (Number(d.penalty_per_day))
		rows.push(["ค่าปรับต่อวัน", `${money(d.penalty_per_day)} · ปรับแล้ว ${money(d.penalty_total)}`]);
	if (d.warranty_days) rows.push(["ระยะรับประกัน", `${d.warranty_days} วัน`]);
	if (d.contract_no) rows.unshift(["เลขที่สัญญา", d.contract_no]);
	return rows.map(([label, value]) => ({ label, value }));
});

async function load() {
	try {
		view.value = await capi("get_agreement", {
			name: state.route.params.name || boot.agreement,
		});
	} catch (error) {
		show_error(error);
		back("contractor");
	}
}
load();
</script>
