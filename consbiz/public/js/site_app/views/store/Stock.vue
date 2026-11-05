<template>
	<div>
		<TopBar title="คลังวัสดุ" :subtitle="data?.warehouse || state.project?.project_name">
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
			<div class="ss-search ss-search--sticky">
				<Icon name="search" :size="18" />
				<input v-model="txt" type="search" placeholder="ค้นหาวัสดุ" />
				<button v-if="txt" type="button" class="ss-search-clear" @click="txt = ''">
					<Icon name="x" :size="16" />
				</button>
			</div>
			<div class="ss-filters">
				<button
					v-for="f in FILTERS"
					:key="f.value"
					type="button"
					class="ss-filter"
					:class="{ 'is-active': filter === f.value }"
					@click="filter = f.value"
				>
					{{ f.label }}
					<span v-if="data" class="ss-filter-count">{{ count(f.value) }}</span>
				</button>
			</div>

			<Skeleton v-if="data === null" :rows="6" />
			<Empty v-else-if="!rows.length" icon="warehouse" :title="txt ? 'ไม่พบวัสดุ' : 'ไม่มีรายการ'" />
			<div v-else class="ss-list">
				<button
					v-for="(item, i) in rows.slice(0, limit)"
					:key="item.item_code"
					type="button"
					class="ss-card ss-stock"
					:style="{ '--i': Math.min(i, 12) }"
					@click="detail = item"
				>
					<span class="ss-thumb">
						<img v-if="item.image" :src="item.image" alt="" loading="lazy" />
						<Icon v-else name="package" :size="22" />
					</span>
					<span class="ss-card-main">
						<span class="ss-card-title">{{ item.item_name }}</span>
						<span
							class="ss-stock-bar"
							:title="`ใช้ไป ${num(item.used)} จาก ${num(item.received)}`"
						>
							<span
								:style="{ width: `${bar(item)}%` }"
								:class="{ 'is-low': item.balance <= 0 }"
							></span>
						</span>
						<span class="ss-card-meta">
							<span v-if="item.employer" class="ss-tag tone-violet"
								>ผู้ว่าจ้าง {{ num(item.employer) }}</span
							>
							<span v-if="item.pending" class="ss-tag tone-blue"
								>ค้างส่ง {{ num(item.pending) }}</span
							>
							<template v-if="!item.employer && !item.pending"
								>รับ {{ num(item.received) }} · ใช้ {{ num(item.used) }}</template
							>
						</span>
					</span>
					<span class="ss-qty" :class="{ 'is-zero': item.balance <= 0 }"
						><b>{{ num(item.balance) }}</b
						><small>{{ item.uom }}</small></span
					>
				</button>
				<button
					v-if="rows.length > limit"
					type="button"
					class="ss-btn ss-btn--ghost ss-btn--block"
					@click="limit += 60"
				>
					แสดงเพิ่ม
				</button>
			</div>
		</div>

		<Sheet
			:open="!!detail"
			:title="detail?.item_name"
			:subtitle="detail?.item_code"
			@close="detail = null"
		>
			<div v-if="detail" class="ss-stock-detail">
				<div class="ss-donut" :style="{ '--p': bar(detail) }">
					<div>
						<b>{{ num(detail.balance) }}</b>
						<small>{{ detail.uom }} คงเหลือ</small>
					</div>
				</div>
				<div class="ss-facts ss-facts--grid">
					<div class="ss-fact">
						<span>รับเข้า</span><b>{{ num(detail.received) }}</b>
					</div>
					<div class="ss-fact">
						<span>ใช้ไป</span><b>{{ num(detail.used) }}</b>
					</div>
					<div class="ss-fact">
						<span>ของบริษัท</span><b>{{ num(detail.company) }}</b>
					</div>
					<div class="ss-fact">
						<span>ผู้ว่าจ้างจัดหา</span><b>{{ num(detail.employer) }}</b>
					</div>
					<div class="ss-fact">
						<span>สั่งแล้วค้างส่ง</span><b>{{ num(detail.pending) }}</b>
					</div>
					<div class="ss-fact">
						<span>ต้องใช้ตามแผน</span><b>{{ num(detail.need) }}</b>
					</div>
				</div>
			</div>
			<template #footer>
				<button
					v-if="detail?.balance > 0"
					type="button"
					class="ss-btn ss-btn--primary ss-btn--block ss-btn--lg"
					@click="issue"
				>
					<Icon name="issue" :size="18" /> เบิกวัสดุนี้
				</button>
			</template>
		</Sheet>
	</div>
</template>

<script setup>
import { computed, ref } from "vue";
import Icon from "../../../shared/components/Icon.vue";
import TopBar from "../../../shared/components/TopBar.vue";
import Skeleton from "../../../shared/components/Skeleton.vue";
import Empty from "../../../shared/components/Empty.vue";
import Sheet from "../../../shared/components/Sheet.vue";
import { call, go, num, show_error, state } from "../../../shared/api.js";

const FILTERS = [
	{ value: "stock", label: "มีของ" },
	{ value: "all", label: "ทั้งหมด" },
	{ value: "employer", label: "ผู้ว่าจ้าง" },
	{ value: "pending", label: "ค้างส่ง" },
	{ value: "empty", label: "หมด" },
];

const data = ref(null);
const loading = ref(false);
const txt = ref("");
const filter = ref("stock");
const detail = ref(null);
const limit = ref(80);

const match = {
	stock: (i) => i.balance > 0,
	all: () => true,
	employer: (i) => i.employer > 0,
	pending: (i) => i.pending > 0,
	empty: (i) => i.balance <= 0 && i.received > 0,
};
const count = (f) => (data.value?.items || []).filter(match[f]).length;

const rows = computed(() => {
	const q = txt.value.trim().toLowerCase();
	return (data.value?.items || []).filter(
		(i) => match[filter.value](i) && (!q || `${i.item_name} ${i.item_code}`.toLowerCase().includes(q))
	);
});

const bar = (item) =>
	item.received > 0
		? Math.max(0, Math.min(100, (item.balance / item.received) * 100))
		: item.balance > 0
		? 100
		: 0;

function issue() {
	detail.value = null;
	go("issue");
}

async function load() {
	loading.value = true;
	try {
		data.value = await call("get_stock", { project: state.project.name });
		// ยังไม่มีของในคลัง: เปิดที่ "ทั้งหมด" (เห็นรายการค้างส่ง) แทนหน้าว่าง
		if (filter.value === "stock" && !count("stock")) filter.value = "all";
	} catch (error) {
		show_error(error);
		data.value ??= { items: [] };
	} finally {
		loading.value = false;
	}
}
load();
</script>
