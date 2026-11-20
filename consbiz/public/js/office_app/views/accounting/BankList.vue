<template>
	<div>
		<TopBar title="บัญชีธนาคาร">
			<template #actions>
				<button v-if="!wide && can_create" type="button" class="ss-btn ss-btn--primary ss-list-create"
					aria-label="สร้างบัญชีธนาคาร" @click="form = true"><Icon name="plus" :size="18" /></button>
			</template>
		</TopBar>
		<div class="ss-content">
			<ListHead
				v-if="wide"
				v-model="filter"
				:tabs="tabs"
				v-model:search="search"
				search_placeholder="ค้นหาบัญชีธนาคาร"
				:create="can_create ? 'สร้างบัญชีธนาคาร' : ''"
				:loading="loading"
				@create="form = true"
				@refresh="load"
			><template #filters><ProjectFilter /></template></ListHead>
			<template v-else>
				<label class="ss-search">
					<Icon name="search" :size="17" />
					<input v-model="search" type="search" placeholder="ค้นหาบัญชีธนาคาร" />
				</label>
				<Segmented v-model="filter" :options="tabs" /><ProjectFilter />
			</template>
			<ListCard :on="wide">
				<Skeleton v-if="loading && !data" />
				<Empty v-else-if="failed" icon="alert" title="โหลดบัญชีธนาคารไม่สำเร็จ" />
				<Empty
					v-else-if="!rows.length"
					icon="building"
					:title="search || filter !== 'all' ? 'ไม่พบบัญชีที่ตรงกับตัวกรอง' : 'ไม่มีบัญชีธนาคารของบริษัท'"
				/>
				<DataTable v-else-if="wide" :columns="columns" :rows="rows" @open="open">
					<template #account_name="{ row }">
						<b>{{ row.account_name }}</b
						><small>{{ row.bank }}</small>
					</template>
					<template #bank_account_no="{ row }">{{ row.bank_account_no || "—" }}</template>
					<template #balance="{ row }"
						><b>{{ amount(row) }}</b></template
					>
				</DataTable>
				<div v-else class="ss-list">
					<button
						v-for="row in rows"
						:key="row.name"
						type="button"
						class="ss-card"
						@click="open(row)"
					>
						<div class="ss-card-head">
							<span class="ss-card-main"
								><b class="ss-card-title">{{ row.account_name }}</b>
								<span class="ss-card-meta"
									>{{ row.bank }} · {{ row.bank_account_no || "—" }}</span
								>
							</span>
							<Icon name="chevron-right" :size="16" />
						</div>
						<div class="ss-chips">
							<span class="ss-chip">{{ row.account || "—" }}</span>
							<b v-if="data.can_gl" class="ss-chip">{{ amount(row) }}</b>
						</div>
					</button>
				</div>
			</ListCard>
		</div>
		<BankForm v-if="form" @close="form = false" @saved="(name) => open({ name })" />
	</div>
</template>

<script setup>
import { computed, ref, watch } from "vue";
import { boot, call, go, money, show_error } from "../../../shared/api.js";
import { matches, use_wide } from "../../../shared/table.js";
import DataTable from "../../../shared/components/DataTable.vue";
import Empty from "../../../shared/components/Empty.vue";
import Icon from "../../../shared/components/Icon.vue";
import ListCard from "../../../shared/components/ListCard.vue";
import ListHead from "../../../shared/components/ListHead.vue";
import Segmented from "../../../shared/components/Segmented.vue";
import Skeleton from "../../../shared/components/Skeleton.vue";
import TopBar from "../../../shared/components/TopBar.vue";
import ProjectFilter from "../../../shared/docs/ProjectFilter.vue";
import { report_scope } from "./report_data.js";
import BankForm from "./BankForm.vue";

const wide = use_wide();
const can_create = !!boot.accounting?.["acc-bank-accounts"]?.create;
const form = ref(false);
const search = ref("");
const data = ref(null);
const loading = ref(false);
const failed = ref(false);
const columns = computed(() => [
	{ key: "account_name", label: "ชื่อบัญชี / ธนาคาร", sort: true },
	{ key: "bank_account_no", label: "เลขที่บัญชี", sort: true },
	{ key: "account", label: "ผังบัญชี", sort: true },
	...(data.value?.can_gl ? [{ key: "balance", label: "ยอดคงเหลือ", sort: true, class: "is-num" }] : []),
]);
const filter = ref("all");
const filters = [
	{ value: "all", label: "ทั้งหมด", test: () => true },
	{ value: "active", label: "ใช้งาน", test: (row) => !row.disabled },
	{ value: "disabled", label: "ปิดใช้งาน", test: (row) => !!row.disabled },
];
const tabs = computed(() => filters.map(({ value, label, test }) => ({
	value, label, count: (data.value?.rows || []).filter(test).length,
})));
const active_filter = computed(() => filters.find((f) => f.value === filter.value));
const rows = computed(() =>
	(data.value?.rows || []).filter((r) =>
		active_filter.value.test(r) &&
		matches(search.value, r.account_name, r.bank, r.bank_account_no, r.account, r.company)
	)
);
const amount = (row) =>
	row.balance == null ? "—" : [money(row.balance), row.currency].filter(Boolean).join(" ");
function open(row) {
	form.value = false;
	go("acc-bank-detail", { name: row.name });
}
let job = 0;
async function load() {
	const id = ++job;
	loading.value = true;
	failed.value = false;
	try {
		const result = await call("consbiz.bank_app.list_accounts", report_scope());
		if (id === job) data.value = result;
	} catch (e) {
		if (id === job) {
			failed.value = true;
			show_error(e);
		}
	} finally {
		if (id === job) loading.value = false;
	}
}
watch(
	() => JSON.stringify(report_scope()),
	() => {
		form.value = false;
		data.value = null;
		load();
	},
	{ immediate: true }
);
</script>
