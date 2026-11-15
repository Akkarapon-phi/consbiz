<!-- ใบเบิกงวดทั้งหมดของผู้รับเหมา (ที่ร่างเอง + ที่อนุมัติแล้ว) แท็บตามสถานะ กดแล้วเปิด/แก้ใบเบิก -->
<template>
	<div>
		<TopBar title="ใบเบิกงวด" no_project>
			<template #actions>
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
			<Skeleton v-if="rows === null" :rows="3" />
			<template v-else>
				<StatusTabs v-model="tab" :options="tabs" />
				<Empty
					v-if="!shown.length"
					icon="receive"
					title="ไม่มีใบเบิก"
					text="สร้างใบเบิกได้จากหน้าสัญญา (เมนูสัญญา)"
				/>
				<div v-else class="ss-list">
					<button
						v-for="(c, i) in shown"
						:key="c.name"
						type="button"
						class="ss-card ss-card--row"
						:style="{ '--i': i }"
						@click="go('contractor-claim', { name: c.name })"
					>
						<span class="ss-avatar" :class="`tone-${c.status_tone}`"
							><Icon name="receive" :size="18"
						/></span>
						<span class="ss-card-main">
							<span class="ss-card-title">งวดที่ {{ c.claim_no }} · {{ c.title }}</span>
							<span class="ss-card-meta"
								>{{ thai_date(c.posting_date, { year: true }) }} ·
								<span class="ss-tag" :class="`tone-${c.status_tone}`">{{
									c.status_label
								}}</span></span
							>
						</span>
						<span class="ss-qty"
							><b>{{ money(c.gross_amount) }}</b><small>บาท</small></span
						>
					</button>
				</div>
			</template>
		</div>
	</div>
</template>

<script setup>
import { computed, ref } from "vue";
import Empty from "../../shared/components/Empty.vue";
import Icon from "../../shared/components/Icon.vue";
import Skeleton from "../../shared/components/Skeleton.vue";
import StatusTabs from "../../shared/components/StatusTabs.vue";
import TopBar from "../../shared/components/TopBar.vue";
import { go, money, show_error, thai_date } from "../../shared/api.js";
import { capi } from "../api.js";

const FILTERS = [
	{ value: "open", label: "กำลังดำเนินการ", test: (c) => c.docstatus === 0 },
	{ value: "approved", label: "อนุมัติแล้ว", test: (c) => c.docstatus === 1 },
	{ value: "all", label: "ทั้งหมด", test: () => true },
];
const rows = ref(null);
const loading = ref(false);
const tab = ref("open");
const tabs = computed(() =>
	FILTERS.map((f) => ({
		value: f.value,
		label: f.label,
		count: (rows.value || []).filter(f.test).length,
	}))
);
const shown = computed(() =>
	(rows.value || []).filter(FILTERS.find((f) => f.value === tab.value).test)
);

async function load() {
	loading.value = true;
	try {
		rows.value = (await capi("get_home")).claims;
		if (tab.value === "open" && !rows.value.some(FILTERS[0].test)) tab.value = "all";
	} catch (error) {
		show_error(error);
		rows.value ??= [];
	} finally {
		loading.value = false;
	}
}
load();
</script>
