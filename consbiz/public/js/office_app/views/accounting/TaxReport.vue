<!-- รายงานภาษีรายเดือน: ภาษีขาย / ภาษีซื้อ / ภ.ง.ด.3 / ภ.ง.ด.53 = Script Report ของ erpnext_thailand (Sales Tax Report, Purchase Tax Report, PND3, PND53)
     กรองบริษัทที่เลือกในแอป + ที่อยู่บริษัท (สาขาที่ยื่น) ส่งออก Excel (`export_report`) แบบฟอร์มยื่นพิมพ์จากรายงานในระบบเต็ม
     URL: acc-tax-report/<รายงาน>/<YYYY-MM> API consbiz/accounting_app.py -->
<template>
	<div>
		<TopBar title="รายงานภาษี" />

		<div class="ss-content">
			<div v-if="wide" class="ss-list-head">
				<StatusTabs v-model="report" :options="tabs" />
				<div class="ss-list-tools">
					<span class="acc-month">
						<button
							type="button"
							class="ss-icon-btn"
							aria-label="เดือนก่อน"
							title="เดือนก่อน"
							@click="shift(-1)"
						>
							<Icon name="chevron-left" :size="17" />
						</button>
						<DateInput
							v-model="month"
							picker="month"
							variant="tool"
							label="เลือกเดือน"
						/>
						<button
							type="button"
							class="ss-icon-btn"
							aria-label="เดือนถัดไป"
							title="เดือนถัดไป"
							@click="shift(1)"
						>
							<Icon name="chevron-right" :size="17" />
						</button>
					</span>
					<SelectBox
						v-if="addresses.length > 1"
						v-model="address"
						:options="address_options"
						label="ที่อยู่บริษัท (สาขา)"
						variant="tool"
					/>
					<button
						type="button"
						class="ss-icon-btn"
						:class="{ 'is-spinning': loading }"
						aria-label="โหลดใหม่"
						title="โหลดใหม่"
						@click="load"
					>
						<Icon name="refresh" :size="17" />
					</button>
					<a
						class="ss-icon-btn"
						:href="desk_report_url"
						title="พิมพ์แบบยื่นในระบบเต็ม"
						aria-label="พิมพ์แบบยื่นในระบบเต็ม"
					>
						<Icon name="printer" :size="17" />
					</a>
					<a class="ss-btn ss-btn--primary ss-list-create" :href="excel_url">
						<Icon name="file" :size="18" /> <span>Excel</span>
					</a>
				</div>
			</div>
			<template v-else>
				<Segmented v-model="report" :options="tabs" />
				<div class="acc-month acc-month--mobile">
					<button
						type="button"
						class="ss-icon-btn"
						aria-label="เดือนก่อน"
						@click="shift(-1)"
					>
						<Icon name="chevron-left" :size="17" />
					</button>
					<DateInput v-model="month" picker="month" label="เลือกเดือน" />
					<button
						type="button"
						class="ss-icon-btn"
						aria-label="เดือนถัดไป"
						@click="shift(1)"
					>
						<Icon name="chevron-right" :size="17" />
					</button>
					<a class="ss-icon-btn" :href="excel_url" aria-label="Excel"
						><Icon name="file" :size="18"
					/></a>
				</div>
			</template>

			<Skeleton v-if="!data" :rows="6" />
			<template v-else>
				<div class="ss-stats ss-stats--3">
					<div class="ss-stat">
						<span class="ss-stat-value">{{ data.totals.count }}</span>
						<span class="ss-stat-label">รายการ</span>
					</div>
					<div class="ss-stat">
						<span class="ss-stat-value ss-stat-value--money">{{
							money(data.totals.tax_base)
						}}</span>
						<span class="ss-stat-label">{{
							is_vat ? "มูลค่าสินค้า/บริการ" : "จำนวนเงินที่จ่าย"
						}}</span>
					</div>
					<div class="ss-stat">
						<span class="ss-stat-value ss-stat-value--money">{{
							money(data.totals.tax_amount)
						}}</span>
						<span class="ss-stat-label">{{
							is_vat ? "ภาษีมูลค่าเพิ่ม" : "ภาษีที่หัก"
						}}</span>
					</div>
				</div>

				<Empty
					v-if="!data.rows.length"
					icon="list"
					:title="`ไม่มีรายการ${current_label}เดือนนี้`"
				/>
				<div v-else class="ss-card">
					<div class="ss-table-wrap">
						<table class="ss-table ss-table--list">
							<thead>
								<tr>
									<th
										v-for="c in data.columns"
										:key="c.fieldname"
										:class="{ 'is-num': is_num(c) }"
									>
										{{ c.label }}
									</th>
								</tr>
							</thead>
							<tbody>
								<tr
									v-for="(r, i) in data.rows"
									:key="i"
									:class="{ 'is-static': !can_open(r) }"
									@click="open(r)"
								>
									<td
										v-for="c in data.columns"
										:key="c.fieldname"
										:class="{ 'is-num': is_num(c) }"
									>
										<template v-if="c.fieldtype === 'Date'">{{
											r[c.fieldname]
												? thai_date(r[c.fieldname], { year: true })
												: "—"
										}}</template>
										<template v-else-if="c.fieldtype === 'Currency'">{{
											money(r[c.fieldname])
										}}</template>
										<template v-else-if="c.fieldtype === 'Float'">{{
											num(r[c.fieldname])
										}}</template>
										<template v-else>{{ r[c.fieldname] ?? "—" }}</template>
									</td>
								</tr>
								<tr class="is-static">
									<td
										v-for="(c, i) in data.columns"
										:key="c.fieldname"
										:class="{ 'is-num': is_num(c) }"
									>
										<b v-if="i === 0">รวม</b>
										<b
											v-else-if="
												c.fieldname === 'tax_base' ||
												c.fieldname === 'tax_amount'
											"
											>{{ money(data.totals[c.fieldname]) }}</b
										>
									</td>
								</tr>
							</tbody>
						</table>
					</div>
				</div>
				<p class="ss-muted">
					{{
						is_vat
							? "เรียงตามเลขที่ เดือนตามวันที่ยื่น (รวมใบที่ยื่นล่าช้าเข้าเดือนนี้)"
							: "เฉพาะหนังสือรับรองที่ยืนยันแล้ว ตามวันที่จ่าย"
					}}
					· แบบฟอร์มสำหรับยื่น พิมพ์จากรายงานในระบบเต็ม (ปุ่มเครื่องพิมพ์)
				</p>
			</template>
		</div>
	</div>
</template>

<script setup>
import { computed, ref, watch } from "vue";
import DateInput from "../../../shared/components/DateInput.vue";
import Empty from "../../../shared/components/Empty.vue";
import Icon from "../../../shared/components/Icon.vue";
import Segmented from "../../../shared/components/Segmented.vue";
import SelectBox from "../../../shared/components/SelectBox.vue";
import Skeleton from "../../../shared/components/Skeleton.vue";
import StatusTabs from "../../../shared/components/StatusTabs.vue";
import TopBar from "../../../shared/components/TopBar.vue";
import { use_wide } from "../../../shared/table.js";
import {
	boot,
	call,
	go,
	money,
	num,
	replace_params,
	scope_args,
	scope_key,
	show_error,
	state,
	thai_date,
} from "../../../shared/api.js";
import { API } from "./kinds.js";

const REPORTS = [
	{ value: "sales", label: "ภาษีขาย", desk: "Sales Tax Report" },
	{ value: "purchase", label: "ภาษีซื้อ", desk: "Purchase Tax Report" },
	{ value: "pnd3", label: "ภ.ง.ด.3", desk: "PND3" },
	{ value: "pnd53", label: "ภ.ง.ด.53", desk: "PND53" },
];
const allowed = boot.accounting?.reports || [];
const tabs = REPORTS.filter((r) => allowed.includes(r.value));

const wide = use_wide();
const params = state.route.params;
const now = new Date();
const this_month = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
const report = ref(tabs.some((t) => t.value === params.report) ? params.report : tabs[0]?.value);
const month = ref(/^\d{4}-\d{2}$/.test(params.month || "") ? params.month : this_month);
const addresses = ref([]);
const address = ref(null);
const data = ref(null);
const loading = ref(false);

const is_vat = computed(() => report.value === "sales" || report.value === "purchase");
const current_label = computed(() => REPORTS.find((r) => r.value === report.value)?.label || "");
const address_options = computed(() => [
	{ value: null, label: "ทุกสาขา" },
	...addresses.value.map((a) => ({
		value: a.value,
		label: a.label,
		description: a.description,
	})),
]);
const ym = computed(() => month.value.split("-").map(Number));
const query = computed(() => {
	const [year, m] = ym.value;
	const q = { key: report.value, year, month: m };
	const { company } = scope_args();
	if (company) q.company = company;
	if (address.value) q.company_address = address.value;
	return new URLSearchParams(q).toString();
});
const excel_url = computed(() => `/api/method/${API}.export_report?${query.value}`);
const desk_report_url = computed(() => {
	const [year, m] = ym.value;
	const desk = REPORTS.find((r) => r.value === report.value)?.desk || "";
	const q = { year, month: m };
	if (address.value) q[is_vat.value ? "company_tax_address" : "company_address"] = address.value;
	if (is_vat.value) q.filter_based_on = "Fiscal Year";
	return `/app/query-report/${encodeURIComponent(desk)}?${new URLSearchParams(q)}`;
});

const is_num = (c) => ["Currency", "Float", "Int"].includes(c.fieldtype);
function can_open(r) {
	return !!r.name;
}
function open(r) {
	if (!r.name) return;
	// รายงานภาษีขาย/ซื้อต่อท้ายใบที่ยกเลิกด้วย " (CANCEL)"
	if (is_vat.value)
		go("acc-tax-doc", {
			kind: report.value === "sales" ? "acc-sales-tax" : "acc-purchase-tax",
			name: String(r.name).split(" (")[0],
		});
	else go("acc-wht-doc", { name: r.name });
}

function shift(step) {
	const [y, m] = ym.value;
	const d = new Date(y, m - 1 + step, 1);
	month.value = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
}

async function load_options() {
	try {
		const { company } = scope_args();
		const result = await call(`${API}.report_options`, { company });
		addresses.value = result.addresses;
		if (!addresses.value.some((a) => a.value === address.value)) address.value = null;
	} catch (e) {
		show_error(e);
	}
}
async function load() {
	if (!report.value) return;
	loading.value = true;
	try {
		const [year, m] = ym.value;
		const { company } = scope_args();
		data.value = await call(`${API}.get_report`, {
			key: report.value,
			year,
			month: m,
			company,
			company_address: address.value || undefined,
		});
	} catch (e) {
		show_error(e);
		data.value ??= { rows: [], columns: [], totals: { count: 0, tax_base: 0, tax_amount: 0 } };
	} finally {
		loading.value = false;
	}
}

watch([report, month], () => {
	replace_params("acc-tax-report", { report: report.value, month: month.value });
	load();
});
watch(address, load);
watch(scope_key, async () => {
	await load_options();
	load();
});
load_options();
load();
</script>

<style scoped>
.acc-month {
	display: inline-flex;
	align-items: center;
	gap: 4px;
}
.acc-month--mobile {
	display: flex;
	margin: 8px 0;
}
.acc-month--mobile :deep(.ss-select),
.acc-month--mobile :deep(.ss-date) {
	flex: 1;
}
</style>
