<!-- แท็บ "% แผน" ของแผงงาน: กำหนด % แผนของงานเป็นรายวัน/สัปดาห์/เดือน (ตรงกับ construction_management/plan_dialog.js ของระบบเต็ม)
     แก้เป็นร่างในแผงก่อน รวมได้ 100% แล้วกด "ใช้ค่านี้" จึงลงแผน (Undo ได้ บันทึกพร้อม plan_distribution ของงาน) -->
<template>
	<section class="pl-insp-sec">
		<h4>
			แบ่ง % แผนของงาน
			<small :class="{ 'is-early': custom }">{{ custom ? "กำหนดเอง" : "ตามจำนวนวัน" }}</small>
		</h4>
		<p v-if="!rows.length" class="pl-insp-note">กำหนดวันเริ่มและวันจบของงานก่อน</p>
		<template v-else>
			<Segmented v-if="p.can_write" :model-value="unit" :options="units" class="pl-seg" @update:model-value="change_unit" />
			<p class="pl-insp-note">% ของแต่ละช่วงกระจายเท่าๆ กันในวันทำงานของช่วงนั้น</p>
			<div class="pl-dist">
				<div class="pl-dist-row is-head">
					<span>ช่วง</span>
					<span>วัน</span>
					<span>%</span>
					<span>สะสม</span>
				</div>
				<div v-for="(row, i) in rows" :key="row.start" class="pl-dist-row">
					<span>{{ label(row) }}</span>
					<span class="pl-dist-num">{{ row.days }}</span>
					<input
						v-model="row.text"
						class="ss-input"
						inputmode="decimal"
						:disabled="!row.days || !p.can_write"
						:aria-label="`% ของช่วง ${label(row)}`"
						@input="touched = true"
					/>
					<span class="pl-dist-num">{{ cumulative[i].toFixed(3) }}</span>
				</div>
			</div>
			<div class="pl-dist-foot">
				<span>รวม <b :class="valid ? 'is-early' : 'is-late'">{{ total.toFixed(3) }}%</b></span>
				<button v-if="p.can_write" type="button" class="pl-tool is-small" @click="spread_evenly">เฉลี่ยเท่ากัน</button>
				<button v-if="custom && p.can_write" type="button" class="pl-tool is-small" @click="clear">คิดตามจำนวนวัน</button>
				<button v-if="p.can_write" type="button" class="ss-btn ss-btn--primary pl-save" :disabled="!touched || !valid" @click="apply">
					ใช้ค่านี้
				</button>
			</div>
		</template>
	</section>
</template>

<script setup>
import { computed, ref, watch } from "vue";
import Segmented from "../../../../shared/components/Segmented.vue";
import { thai_date } from "../../../../shared/api.js";
import { from_day, parse_distribution, segments, to_day } from "../../../../construction_management/schedule.js";

const props = defineProps({
	p: { type: Object, required: true },
	task: { type: Object, required: true },
});

const unit = ref("week");
const rows = ref([]);
const touched = ref(false);

const units = computed(() => [
	{ value: "day", label: "รายวัน" },
	{ value: props.p.data?.week_by_month ? "mweek" : "week", label: "รายสัปดาห์" },
	{ value: "month", label: "รายเดือน" },
]);
const current = computed(() => parse_distribution(props.task.plan_distribution));
const custom = computed(() => Boolean(current.value));
const percents = computed(() => rows.value.map((row) => Math.max(Number(row.text) || 0, 0)));
const cumulative = computed(() => {
	let sum = 0;
	return percents.value.map((percent) => (sum += percent));
});
const total = computed(() => cumulative.value.at(-1) || 0);
const valid = computed(() => Math.abs(total.value - 100) <= 0.01);

const round = (value, digits) => Number(value.toFixed(digits));
const text_of = (value) => String(round(value, 4));

function working_days(from, to) {
	let count = 0;
	for (let day = from; day <= to; day++) if (!props.p.counting.has(day)) count++;
	return count;
}

// ค่าเริ่มต้น: ใช้ % เดิมถ้ากำหนดไว้ด้วยหน่วยนี้และจำนวนช่วงตรงกัน ไม่งั้นแบ่งตามสัดส่วนวันทำงาน
function build_rows(distribution) {
	const start = to_day(props.task.start_date);
	const end = to_day(props.task.end_date);
	if (start === null || end === null) return [];
	const parts = segments(start, end, unit.value).map((part) => ({
		...part,
		days: working_days(part.start, part.end),
	}));
	if (distribution?.unit === unit.value && distribution.weights.length === parts.length) {
		return parts.map((part, i) => ({ ...part, text: text_of(distribution.weights[i] || 0) }));
	}
	const total_days = parts.reduce((sum, part) => sum + part.days, 0) || 1;
	return with_shares(parts, (part) => (part.days / total_days) * 100);
}

// ปัดทศนิยม 3 ตำแหน่ง แล้วให้ช่วงสุดท้ายที่มีวันทำงานรับเศษ ยอดรวมจึงได้ 100 พอดี
function with_shares(parts, share_of) {
	const last = parts.findLastIndex((part) => part.days);
	let used = 0;
	return parts.map((part, i) => {
		let percent = part.days ? round(share_of(part), 3) : 0;
		if (i === last) percent = round(100 - used, 3);
		used += percent;
		return { ...part, text: text_of(percent) };
	});
}

function reset() {
	const saved = current.value?.unit;
	const allowed = units.value.map((option) => option.value);
	unit.value = allowed.includes(saved) ? saved : allowed[1];
	rows.value = build_rows(current.value);
	touched.value = false;
}
watch(
	() =>
		[props.task.name, props.task.start_date, props.task.end_date, props.task.plan_distribution, props.p.data?.week_by_month].join(
			"|"
		),
	reset,
	{ immediate: true }
);

function change_unit(value) {
	if (value === unit.value) return;
	unit.value = value;
	rows.value = build_rows(null);
	touched.value = true;
}
function spread_evenly() {
	const count = rows.value.filter((row) => row.days).length || 1;
	rows.value = with_shares(rows.value, () => 100 / count);
	touched.value = true;
}
function apply() {
	if (!valid.value) return;
	props.p.update_distribution(
		props.task,
		JSON.stringify({ unit: unit.value, weights: percents.value.map((percent) => round(percent, 6)) })
	);
	touched.value = false;
}
function clear() {
	props.p.update_distribution(props.task, null);
}

function label(part) {
	const first = thai_date(from_day(part.start));
	return part.start === part.end ? first : `${first} – ${thai_date(from_day(part.end))}`;
}
</script>
