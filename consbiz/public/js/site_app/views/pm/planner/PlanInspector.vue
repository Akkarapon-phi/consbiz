<!-- แผงรายละเอียดงานที่เลือก (หน้าแก้แผนในแอป) จอใหญ่ = แผงขวาของ PlanEdit, มือถือ = อยู่ใน Sheet
     แท็บทั่วไป: แก้วันเริ่ม/จบ/จำนวนวัน, % จริง ณ วัน Cut-off, งานก่อนหน้า (ชนิด + lag), แท็บ % แผน: PlanDistribution.vue, แท็บทรัพยากร: PlanResources.vue ทุกการแก้ Undo ได้ (planner.record) -->
<template>
	<div class="pl-insp">
		<header class="pl-insp-head">
			<span class="ss-chip ss-chip--id">{{ task.wbs }}</span>
			<div class="pl-insp-title">
				<b>{{ task.item_name }}</b>
				<small>{{ task.is_group ? "หัวข้อกลุ่ม" : m.status.label }}</small>
			</div>
			<button v-if="closable" type="button" class="ss-icon-btn ss-icon-btn--sm" aria-label="ปิด" @click="$emit('close')">
				<Icon name="x" :size="18" />
			</button>
		</header>

		<div v-if="!task.is_group" class="pl-tabs pl-insp-tabs" role="tablist">
			<button
				v-for="item in TABS"
				:key="item.value"
				type="button"
				role="tab"
				:aria-selected="active_tab === item.value"
				:class="{ 'is-active': active_tab === item.value }"
				@click="$emit('update:tab', item.value)"
			>
				{{ item.label }}
				<span v-if="item.value === 'resources' && resource_count" class="pl-tab-count">{{ resource_count }}</span>
			</button>
		</div>

		<PlanDistribution v-if="active_tab === 'plan'" :p="p" :task="task" />
		<PlanResources v-else-if="active_tab === 'resources'" :p="p" :task="task" />
		<template v-else>
			<section class="pl-insp-sec">
				<h4>กำหนดการ</h4>
				<div class="pl-insp-grid">
					<label>
						<span>เริ่ม</span>
						<DateInput
							v-if="editable"
							:model-value="task.start_date"
							label="วันเริ่ม"
							@update:model-value="(v) => p.update_task(task, 'start_date', v)"
						/>
						<b v-else>{{ thai(task.start_date) }}</b>
					</label>
					<label>
						<span>จบ</span>
						<DateInput
							v-if="editable"
							:model-value="task.end_date"
							label="วันจบ"
							@update:model-value="(v) => p.update_task(task, 'end_date', v)"
						/>
						<b v-else>{{ thai(task.end_date) }}</b>
					</label>
					<label class="is-wide">
						<span>จำนวนวัน{{ p.data?.use_working_days ? " (วันทำงาน)" : "" }}</span>
						<div v-if="editable" class="pl-stepper">
							<button type="button" aria-label="ลด" @click="p.update_task(task, 'duration', (task.duration || 1) - 1)">
								<Icon name="minus" :size="16" />
							</button>
							<input
								class="ss-input"
								inputmode="numeric"
								:value="task.duration"
								@change="(e) => p.update_task(task, 'duration', e.target.value)"
							/>
							<button type="button" aria-label="เพิ่ม" @click="p.update_task(task, 'duration', (task.duration || 0) + 1)">
								<Icon name="plus" :size="16" />
							</button>
						</div>
						<b v-else>{{ task.duration || "-" }} วัน</b>
					</label>
				</div>
				<p v-if="task.baseline_start_date" class="pl-insp-note">
					แผนสัญญา {{ thai(task.baseline_start_date) }} – {{ thai(task.baseline_end_date) }}
					<span v-if="shift" :class="shift > 0 ? 'is-late' : 'is-early'"
						>({{ shift > 0 ? "ช้ากว่า" : "เร็วกว่า" }} {{ Math.abs(shift) }} วัน)</span
					>
				</p>
			</section>

			<section class="pl-insp-sec">
				<h4>ความคืบหน้า ณ {{ thai(p.cutoff) }}</h4>
				<div class="pl-insp-progress">
					<div class="pl-meter">
						<i class="is-plan" :style="{ width: `${m.plan_pct}%` }"></i>
						<i class="is-actual" :style="{ width: `${m.actual_pct}%` }"></i>
					</div>
					<div class="pl-insp-pcts">
						<div>
							<small>แผน</small><b>{{ pct(m.plan_pct) }}%</b>
						</div>
						<div>
							<small>จริง</small>
							<span v-if="editable" class="pl-pct-input">
								<input
									class="ss-input"
									inputmode="decimal"
									:value="pct(m.actual_pct)"
									@change="(e) => p.update_task(task, 'actual_pct', e.target.value)"
								/>%
							</span>
							<b v-else>{{ pct(m.actual_pct) }}%</b>
						</div>
						<div>
							<small>ต่าง</small>
							<b :class="diff < -0.05 ? 'is-late' : diff > 0.05 ? 'is-early' : ''"
								>{{ diff > 0 ? "+" : "" }}{{ pct(diff) }}</b
							>
						</div>
					</div>
					<label v-if="editable && task.quantity > 0" class="pl-qty">
						<span>ปริมาณทำแล้วสะสม ({{ task.uom || "หน่วย" }})</span>
						<input
							class="ss-input"
							inputmode="decimal"
							:value="fixed(m.actual_qty, 2)"
							@change="(e) => p.update_task(task, 'actual_qty', e.target.value)"
						/>
						<small>จาก {{ num(task.quantity) }} {{ task.uom }}</small>
					</label>
				</div>
			</section>

			<section v-if="!task.is_group" class="pl-insp-sec">
				<h4>
					งานก่อนหน้า
					<small v-if="m.total_float !== null" :class="{ 'is-late': m.critical }"
						>{{ m.critical ? "งานวิกฤต" : `Float ${m.total_float} วัน` }}</small
					>
				</h4>
				<ul v-if="links.length" class="pl-links-list">
					<li v-for="(link, i) in links" :key="link.task">
						<div class="pl-link-name">
							<b>{{ p.by_name.get(link.task)?.wbs }}</b>
							<span>{{ p.by_name.get(link.task)?.item_name }}</span>
						</div>
						<template v-if="editable">
							<SelectBox
								:model-value="link.type"
								:options="LINK_TYPES"
								variant="cell"
								label="ชนิด"
								@update:model-value="(v) => change_link(i, { type: v })"
							/>
							<input
								class="ss-input pl-lag"
								inputmode="numeric"
								title="lag (วัน) ติดลบ = ซ้อนกัน"
								:value="link.lag > 0 ? `+${link.lag}` : link.lag || 0"
								@change="(e) => change_link(i, { lag: Math.round(Number(e.target.value)) || 0 })"
							/>
							<button type="button" class="ss-icon-btn ss-icon-btn--sm" aria-label="ลบ" @click="remove_link(i)">
								<Icon name="trash" :size="16" />
							</button>
						</template>
						<span v-else class="pl-link-type">{{ link.type }}{{ link.lag ? (link.lag > 0 ? `+${link.lag}` : link.lag) : "" }}</span>
					</li>
				</ul>
				<p v-else class="pl-insp-note">ไม่มีงานก่อนหน้า เริ่มตามวันที่กำหนด</p>
				<SelectBox
					v-if="editable"
					:model-value="null"
					:options="candidates"
					placeholder="+ เพิ่มงานก่อนหน้า (FS)"
					label="เพิ่มงานก่อนหน้า"
					@update:model-value="add_link"
				/>
			</section>

			<section class="pl-insp-sec">
				<h4>ข้อมูลงาน</h4>
				<dl class="pl-insp-dl">
					<template v-if="task.quantity">
						<dt>ปริมาณ</dt>
						<dd>{{ num(task.quantity) }} {{ task.uom }}</dd>
					</template>
					<template v-if="p.data?.can_view_value">
						<dt>มูลค่า</dt>
						<dd>{{ money(task.amount) }}</dd>
					</template>
					<dt>น้ำหนัก</dt>
					<dd>{{ fixed(task.weight, 3) }}%</dd>
					<template v-if="task.is_variation">
						<dt>งานเพิ่ม (VO)</dt>
						<dd>{{ task.counted_from ? `นับตั้งแต่ ${thai(task.counted_from)}` : "ยังไม่อนุมัติ" }}</dd>
					</template>
				</dl>
			</section>
		</template>
	</div>
</template>

<script setup>
import { computed } from "vue";
import Icon from "../../../../shared/components/Icon.vue";
import DateInput from "../../../../shared/components/DateInput.vue";
import SelectBox from "../../../../shared/components/SelectBox.vue";
import { money, num, thai_date } from "../../../../shared/api.js";
import { parse_predecessors, to_day } from "../../../../construction_management/schedule.js";
import { LINK_TYPES } from "./planner.js";
import PlanDistribution from "./PlanDistribution.vue";
import PlanResources from "./PlanResources.vue";

const props = defineProps({
	p: { type: Object, required: true },
	task: { type: Object, required: true },
	closable: { type: Boolean, default: true },
	// แท็บอยู่ที่ PlanEdit: คงเดิมเมื่อเลือกงานอื่น และเมนูคลิกขวาเปิดแท็บที่ต้องการได้
	tab: { type: String, default: "main" },
});
defineEmits(["close", "update:tab"]);

const TABS = [
	{ value: "main", label: "ทั่วไป" },
	{ value: "plan", label: "% แผน" },
	{ value: "resources", label: "ทรัพยากร" },
];
const resource_count = computed(() => {
	const marks = props.p.plan_marks.get(props.task.name);
	return marks ? marks.resources.length + marks.materials.length : 0;
});
// หัวข้อกลุ่มมีแค่แท็บทั่วไป
const active_tab = computed(() => (props.task.is_group ? "main" : props.tab));

const m = computed(
	() => props.p.metrics.get(props.task.name) || { plan_pct: 0, actual_pct: 0, actual_qty: 0, status: {}, total_float: null }
);
const editable = computed(() => props.p.can_write && !props.task.is_group);
const diff = computed(() => m.value.actual_pct - m.value.plan_pct);
const shift = computed(() => {
	const now = to_day(props.task.end_date);
	const base = to_day(props.task.baseline_end_date);
	return now === null || base === null ? 0 : now - base;
});
const links = computed(() => parse_predecessors(props.task.predecessors));
const candidates = computed(() => {
	const used = new Set(links.value.map((l) => l.task));
	return props.p.tasks
		.filter((t) => !t.is_group && t.name !== props.task.name && !used.has(t.name))
		.map((t) => ({ value: t.name, label: `${t.wbs} ${t.item_name}` }));
});

const thai = (value) => (value ? thai_date(value, { year: true }) : "-");
const pct = (value) => (Number(value) || 0).toFixed(3);
const fixed = (value, digits = 1) => (Number(value) || 0).toFixed(digits).replace(/\.0+$/, "");

function change_link(index, patch) {
	props.p.update_links(
		props.task,
		links.value.map((link, i) => (i === index ? { ...link, ...patch } : link))
	);
}
function remove_link(index) {
	props.p.update_links(
		props.task,
		links.value.filter((_, i) => i !== index)
	);
}
function add_link(name) {
	if (!name) return;
	props.p.update_links(props.task, [...links.value, { task: name, type: "FS", lag: 0 }]);
}
</script>
