<!-- เมนูการเงินของหมวดแผนงาน (เฉพาะผู้ที่เห็นงบต้นทุน): tab Cash Flow / ต้นทุน / Earned Value (จำใน URL)
     ข้อมูลจาก finance.get_finance ชุดเดียวกับ Tab การเงินของ Construction Management -->
<template>
	<div>
		<TopBar title="การเงิน" :subtitle="state.project?.project_name">
			<template #actions>
				<button v-if="allowed && !wide" type="button" class="ss-icon-btn" :class="{ 'is-spinning': finance.loading }" aria-label="โหลดใหม่" @click="load_finance(project, { force: true })">
					<Icon name="refresh" :size="20" />
				</button>
			</template>
		</TopBar>
		<div v-if="!allowed" class="ss-content">
			<Empty icon="alert" title="ไม่มีสิทธิ์ดูข้อมูลการเงิน" text="ต้องมีสิทธิ์เห็นงบต้นทุนของแผนงาน" />
		</div>
		<div v-else class="ss-content ss-fin">
			<div :class="wide ? 'ss-list-head' : 'ss-fin-head'">
				<StatusTabs v-if="wide" v-model="tab" :options="TABS" />
				<Segmented v-else v-model="tab" :options="TABS" />
				<div :class="wide ? 'ss-list-tools' : 'ss-fin-date'">
					<span class="ss-fin-date-label">ณ วันที่</span>
					<DateInput :model-value="finance.date" :variant="wide ? 'tool' : 'field'" label="ณ วันที่" @update:model-value="set_date" />
					<button type="button" class="ss-btn" :class="{ 'ss-btn--soft ss-list-create': wide }" :disabled="finance.date === today()" @click="set_date(today())"><span>วันนี้</span></button>
					<button v-if="wide" type="button" class="ss-icon-btn" :class="{ 'is-spinning': finance.loading }" aria-label="โหลดใหม่" @click="load_finance(project, { force: true })">
						<Icon name="refresh" :size="17" />
					</button>
				</div>
			</div>

			<Skeleton v-if="d === undefined" :rows="6" />
			<Empty v-else-if="d === null" icon="layers" title="โครงการนี้ยังไม่มีแผนงาน" text="ข้อมูลการเงินคำนวณจากแผนงานก่อสร้าง" />

			<template v-else-if="tab === 'cash'">
				<div class="ss-stats">
					<div v-for="(tile, i) in cash_tiles" :key="tile.label" class="ss-stat" :class="`tone-${tile.tone}`" :style="{ '--i': i }">
						<span class="ss-stat-icon"><Icon :name="tile.icon" :size="20" /></span>
						<span class="ss-stat-value ss-stat-value--money">{{ tile.value }}</span>
						<span class="ss-stat-label">{{ tile.label }}</span>
						<span class="ss-stat-label">{{ tile.note }}</span>
					</div>
				</div>
				<section class="ss-fin-card">
					<h3 class="ss-fin-title">มูลค่างานสะสม</h3>
					<p class="ss-fin-note">Cash Plan = % แผนปัจจุบัน x มูลค่าสัญญาปรับปรุง · Cash Actual = มูลค่างานที่ทำได้จริง</p>
					<MoneyChart v-if="cash_curve.length > 1" :points="cash_curve" :series="CASH_SERIES" :mark_date="dateOf(d.date)" :aria="`Cash Plan สะสม ${money(d.summary.plan)} Cash Actual สะสม ${money(d.summary.actual)}`" />
					<Empty v-else icon="calendar" title="ยังไม่ได้กำหนดวันที่ของแผนงาน" />
				</section>
				<section v-if="d.months.length" class="ss-fin-card">
					<h3 class="ss-fin-title">Cash Flow รายเดือน</h3>
					<p class="ss-fin-note">เดือนหลังวันที่ดูแสดงเฉพาะแผน</p>
					<div class="rb-month ss-fin-table">
						<table>
							<thead>
								<tr>
									<th class="is-name">เดือน</th>
									<th>แผนรายเดือน</th>
									<th>แผนสะสม</th>
									<th>จริงรายเดือน</th>
									<th>จริงสะสม</th>
									<th>ส่วนต่างสะสม</th>
								</tr>
							</thead>
							<tbody>
								<tr v-for="row in d.months" :key="row.month" :class="{ 'is-future': row.actual === null, 'is-current': row.month === current_month }">
									<th class="is-name">{{ month_label(row.month) }}</th>
									<td>{{ cell(row.plan) }}</td>
									<td>{{ cell(row.plan_cum) }}</td>
									<td>{{ cell(row.actual) }}</td>
									<td>{{ cell(row.actual_cum) }}</td>
									<td :class="{ 'is-short': row.variance < -0.5 }">{{ signed(row.variance) }}</td>
								</tr>
							</tbody>
						</table>
					</div>
				</section>
			</template>

			<template v-else-if="tab === 'cost'">
				<Empty v-if="!d.cost?.rows?.length" icon="layers" title="ยังไม่มีข้อมูลต้นทุน" text="ตั้งงบที่ตารางงบต้นทุนตามหมวดของแผนงาน" />
				<section v-else class="ss-fin-card">
					<h3 class="ss-fin-title">ต้นทุนตามหมวด</h3>
					<p class="ss-fin-note">ใช้จริง = บัญชีค่าใช้จ่ายที่ผูก Project · ผูกพัน = PO ที่ยังไม่ตั้งหนี้ · งานเสร็จ {{ pct(d.cost.progress) }}</p>
					<div class="rb-month ss-fin-table">
						<table>
							<thead>
								<tr>
									<th class="is-name">หมวด</th>
									<th>งบ</th>
									<th>ใช้จริง</th>
									<th>ผูกพัน</th>
									<th>คงเหลือ</th>
									<th class="is-text">ใช้ไปเทียบงาน</th>
								</tr>
							</thead>
							<tbody>
								<tr v-for="row in d.cost.rows" :key="row.category ?? '_none'">
									<th class="is-name" :title="row.label">{{ row.label }}</th>
									<td>{{ row.budget ? money(row.budget) : "-" }}</td>
									<td>{{ money(row.actual) }}</td>
									<td>{{ row.committed ? money(row.committed) : "-" }}</td>
									<td :class="{ 'is-short': row.remaining < 0 }">{{ cell(row.remaining) }}</td>
									<td class="is-text">
										<div class="ss-fin-bar-cell">
											<div class="ss-fin-bar" :title="`ใช้จริง ${pct(row.actual_pct)} · รวมผูกพัน ${pct(row.used)} · งานเสร็จ ${pct(d.cost.progress)}`">
												<i class="is-actual" :style="{ width: bar(row.actual, row.budget) }"></i>
												<i class="is-committed" :style="{ left: bar(row.actual, row.budget), width: bar(row.committed, row.budget) }"></i>
												<b :style="{ left: `${Math.min(d.cost.progress, 100)}%` }"></b>
											</div>
											<span class="ss-tag" :class="`tone-${COST_TONES[row.tone]}`">{{ row.budget ? pct(row.used) : "ยังไม่ตั้งงบ" }}</span>
										</div>
									</td>
								</tr>
							</tbody>
							<tfoot>
								<tr>
									<th class="is-name">{{ d.cost.total.label }}</th>
									<td>{{ d.cost.total.budget ? money(d.cost.total.budget) : "-" }}</td>
									<td>{{ money(d.cost.total.actual) }}</td>
									<td>{{ money(d.cost.total.committed) }}</td>
									<td :class="{ 'is-short': d.cost.total.remaining < 0 }">{{ cell(d.cost.total.remaining) }}</td>
									<td class="is-text"><span class="ss-tag" :class="`tone-${COST_TONES[d.cost.total.tone]}`">{{ COST_NOTES[d.cost.total.tone] }}</span></td>
								</tr>
							</tfoot>
						</table>
					</div>
					<div class="ss-fin-legend">
						<span><i class="is-actual"></i>ใช้จริง</span>
						<span><i class="is-committed"></i>ผูกพัน</span>
						<span><i class="is-mark"></i>% งานที่เสร็จ</span>
					</div>
				</section>
			</template>

			<template v-else>
				<Empty v-if="!d.evm" icon="trending" title="ยังไม่มีข้อมูล Earned Value" text="ต้องตั้งงบต้นทุนและมีแผนงานที่เริ่มแล้ว" />
				<template v-else>
					<div class="ss-stats">
						<div v-for="(tile, i) in evm_tiles" :key="tile.label" class="ss-stat" :class="`tone-${tile.tone}`" :style="{ '--i': i }">
							<span class="ss-stat-icon"><Icon :name="tile.icon" :size="20" /></span>
							<span class="ss-stat-value ss-stat-value--money">{{ tile.value }}</span>
							<span class="ss-stat-label">{{ tile.label }}</span>
						</div>
					</div>
					<section class="ss-fin-card">
						<h3 class="ss-fin-title">Earned Value</h3>
						<p class="ss-fin-note">BAC {{ money(d.evm.bac) }} · PV {{ money(d.evm.pv) }} · EV {{ money(d.evm.ev) }} · AC {{ money(d.evm.ac) }}</p>
						<MoneyChart v-if="d.evm.series.length > 1" :points="d.evm.series" :series="EVM_SERIES" :aria="`PV ${money(d.evm.pv)} EV ${money(d.evm.ev)} AC ${money(d.evm.ac)}`" />
						<div class="rb-month ss-fin-table">
							<table>
								<thead>
									<tr>
										<th class="is-name">วันที่</th>
										<th>PV</th>
										<th>EV</th>
										<th>AC</th>
									</tr>
								</thead>
								<tbody>
									<tr v-for="row in d.evm.series" :key="row.date">
										<th class="is-name">{{ thai_date(row.date, { year: true }) }}</th>
										<td>{{ money(row.pv) }}</td>
										<td>{{ money(row.ev) }}</td>
										<td>{{ money(row.ac) }}</td>
									</tr>
								</tbody>
							</table>
						</div>
					</section>
				</template>
			</template>
		</div>
	</div>
</template>

<script setup>
import { computed, ref, watch } from "vue";
import Icon from "../../../shared/components/Icon.vue";
import TopBar from "../../../shared/components/TopBar.vue";
import Skeleton from "../../../shared/components/Skeleton.vue";
import Empty from "../../../shared/components/Empty.vue";
import DateInput from "../../../shared/components/DateInput.vue";
import Segmented from "../../../shared/components/Segmented.vue";
import StatusTabs from "../../../shared/components/StatusTabs.vue";
import { boot, money, remember_tab, state, thai_date } from "../../../shared/api.js";
import { use_wide } from "../../../shared/table.js";
import { MONTHS } from "../pm/planner/time_axis.js";
import MoneyChart from "./MoneyChart.vue";
import { finance, load_finance, today } from "./finance_data.js";

const TABS = [
	{ value: "cash", label: "Cash Flow" },
	{ value: "cost", label: "ต้นทุน" },
	{ value: "evm", label: "Earned Value" },
];
const CASH_SERIES = [
	{ key: "plan", label: "Cash Plan", slot: 1, dashed: true },
	{ key: "actual", label: "Cash Actual", slot: 2 },
];
const EVM_SERIES = [
	{ key: "pv", label: "PV", slot: 1, dashed: true },
	{ key: "ev", label: "EV", slot: 2 },
	{ key: "ac", label: "AC", slot: 3 },
];
const COST_TONES = { red: "rose", orange: "amber", green: "green", gray: "gray" };
const COST_NOTES = { red: "เกินงบ", orange: "ใช้เร็วกว่างาน", green: "ปกติ", gray: "ยังไม่ตั้งงบ" };

// จับค่าตอนสร้างหน้า: ระหว่าง animation ออก route เปลี่ยนแล้ว หน้าเก่าต้องแสดงของเดิม
const tab = ref(TABS.some((t) => t.value === state.route.params.tab) ? state.route.params.tab : "cash");
const project = state.project.name;
const wide = use_wide();
// เปิด URL ตรงโดยไม่มีสิทธิ์ (เมนูซ่อนอยู่แล้ว) ไม่ต้องเรียก API
const allowed = !!boot.can?.finance;
if (allowed) load_finance(project);

watch(tab, (value) => remember_tab("finance", value, "cash"));

const d = computed(() => (finance.project === project ? finance.data : undefined));

function set_date(value) {
	if (value) load_finance(project, { date: value });
}

const dateOf = (value) => String(value).slice(0, 10);
const cell = (value) => (value === null || value === undefined ? "-" : money(value));
const signed = (value) => (value === null || value === undefined ? "-" : `${value > 0 ? "+" : ""}${money(value)}`);
const pct = (value) => (value === null || value === undefined ? "-" : `${Math.round(value).toLocaleString("th-TH")}%`);
const bar = (value, budget) => `${Math.min(Math.max(budget ? (value / budget) * 100 : 0, 0), 100)}%`;
const ratio = (value) => (value === null || value === undefined ? "-" : Number(value).toFixed(2));
const month_label = (value) => {
	const [year, month] = String(value).split("-").map(Number);
	return `${MONTHS[month - 1]} ${(year + 543) % 100}`;
};
const index_tone = (value) => (value === null || value === undefined ? "gray" : value >= 1 ? "green" : "rose");

const cash_tiles = computed(() => {
	const { contract, summary } = d.value;
	const amount = contract.revised_amount || contract.total_amount || 0;
	const share = (value) => (amount ? `${((value / amount) * 100).toFixed(2)}% ของมูลค่าสัญญา` : "");
	const variance = summary.actual - summary.plan;
	return [
		{
			label: "มูลค่าสัญญาปรับปรุง",
			value: money(amount, { short: true }),
			note: contract.variation_amount ? `งานเพิ่ม-ลด ${money(contract.variation_amount, { short: true })}` : "ตามสัญญาเดิม",
			icon: "file",
			tone: "blue",
		},
		{ label: "Cash Plan สะสม", value: money(summary.plan, { short: true }), note: share(summary.plan), icon: "calendar", tone: "violet" },
		{ label: "Cash Actual สะสม", value: money(summary.actual, { short: true }), note: share(summary.actual), icon: "trending", tone: "green" },
		{
			label: "ส่วนต่าง (จริง - แผน)",
			value: `${variance > 0 ? "+" : ""}${money(variance, { short: true })}`,
			note: variance >= 0 ? "เร็วกว่าแผน" : "ช้ากว่าแผน",
			icon: "alert",
			tone: Math.abs(variance) < 0.5 ? "gray" : variance > 0 ? "green" : "rose",
		},
	];
});

// จุด: ต้นเดือนแรก (0), สิ้นแต่ละเดือน และวันที่ดู (เดือนปัจจุบันเทียบแผน ณ วันที่ดู) ตรงกับกราฟใน Tab การเงินของระบบเต็ม
const cash_curve = computed(() => {
	const months = d.value.months;
	if (!months.length) return [];
	const day = dateOf(d.value.date);
	const rows = [{ date: months[0].month, plan: 0, actual: months[0].month <= day ? 0 : null }];
	for (const m of months) {
		if (m.month <= day && day < m.month_end) {
			rows.push({ date: day, plan: m.plan_at_date, actual: m.actual_cum });
			rows.push({ date: m.month_end, plan: m.plan_cum, actual: null });
		} else {
			rows.push({ date: m.month_end, plan: m.plan_cum, actual: m.month_end <= day ? m.actual_cum : null });
		}
	}
	return rows;
});

const current_month = computed(() => {
	const day = dateOf(d.value.date);
	return d.value.months.find((m) => m.month <= day && day <= m.month_end)?.month;
});

const evm_tiles = computed(() => {
	const e = d.value.evm;
	return [
		{ label: "SPI ประสิทธิภาพเวลา", value: ratio(e.spi), icon: "clock", tone: index_tone(e.spi) },
		{ label: "CPI ประสิทธิภาพต้นทุน", value: ratio(e.cpi), icon: "trending", tone: index_tone(e.cpi) },
		{ label: "EAC ต้นทุนรวมที่คาด", value: e.eac === null ? "-" : money(e.eac, { short: true }), icon: "layers", tone: "blue" },
		{ label: "VAC ส่วนต่างงบ", value: e.vac === null ? "-" : money(e.vac, { short: true }), icon: "alert", tone: e.vac < 0 ? "rose" : "green" },
	];
});
</script>
