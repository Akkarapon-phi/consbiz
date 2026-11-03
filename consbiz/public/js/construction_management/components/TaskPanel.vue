<script setup>
// แผงด้านขวาของหน้า Gantt: คน/เครื่องจักร และวัสดุของงานที่เลือก (คลิก WBS/ชื่องานในตาราง)
// ข้อมูลเป็นแถวของ Construction Resource Plan / Construction Material Plan ที่ App ถือไว้
// การแก้ทุกครั้งส่งกลับให้ App (record → Undo ได้ และบันทึกพร้อมแผนงาน) แผงนี้ไม่เก็บสถานะเอง ยกเว้นช่องเพิ่มรายการ
// วันที่ต้องสั่ง/ต้องจองคิดจากวันเริ่มงานปัจจุบัน (schedule.js) ลากงานแล้วเปลี่ยนตามทันที
// สถานะวัสดุ = ยอดที่ขอ/สั่งซื้อ/รับแล้วของโครงการที่ตัดให้แถวนี้ (coverage จาก allocate_materials) ไม่ได้ผูก MR ทีละแถว
import { computed, reactive, ref, watch } from "vue";
import FrappeControl from "./FrappeControl.vue";
import { PREP_DUE_DAYS } from "../columns";
import { book_by, from_day, material_dates, material_key, to_day } from "../schedule";

const props = defineProps({
	task: Object,
	resources: Array,
	materials: Array,
	// ชื่อคน/เครื่องจักรที่เคยลงใน Daily Report { labour, equipment }
	options: Object,
	bufferDays: Number,
	// null = ไม่มีสิทธิ์อ่านแผนนั้น
	resourcePlan: Object,
	materialPlan: Object,
	canEditResources: Boolean,
	canEditMaterials: Boolean,
	day: Number,
	coverage: Map, // key ของแถววัสดุ → { requested, ordered, received, state, shortfall }
});
const emit = defineEmits([
	"close",
	"add-resource",
	"update-resource",
	"remove-resource",
	"add-material",
	"update-material",
	"remove-material",
	"open-plan",
]);

const TYPES = [
	{ value: "Labour", label: __("แรงงาน"), unit: __("คน/วัน"), icon: "users" },
	{ value: "Equipment", label: __("เครื่องจักร"), unit: __("คัน/วัน"), icon: "truck" },
];
const type_of = (value) => TYPES.find((t) => t.value === value) || TYPES[0];

const start = computed(() => to_day(props.task.start_date));
const fmt_day = (day) => (day === null ? "-" : frappe.datetime.str_to_user(from_day(day)));
const fmt_qty = (value) => format_number(value || 0, null, value % 1 ? 2 : 0);
const icon = (name, size = "sm") => frappe.utils.icon(name, size);

// ป้ายจำนวนวันที่เหลือ (สีตาม indicator ของ Frappe)
function due_pill(target, done) {
	if (done) return { color: "green", label: __("สั่งแล้ว") };
	if (target === null) return { color: "gray", label: __("ยังไม่มีวันเริ่มงาน") };
	const days = target - props.day;
	if (days < 0) return { color: "red", label: __("เลยกำหนด {0} วัน", [-days]) };
	if (days === 0) return { color: "red", label: __("วันนี้") };
	return { color: days <= PREP_DUE_DAYS ? "orange" : "gray", label: __("อีก {0} วัน", [days]) };
}

const resource_rows = computed(() =>
	props.resources.map((row) => {
		const target = book_by(start.value, row.lead_time_days);
		// งานเริ่มแล้วไม่ต้องจอง
		const started = start.value !== null && start.value <= props.day;
		return {
			row,
			type: type_of(row.resource_type),
			target,
			pill: started ? { color: "blue", label: __("เริ่มงานแล้ว") } : due_pill(target, false),
		};
	})
);

// ป้ายสถานะวัสดุ: ขอครบแล้วแสดงขั้นล่าสุด (ลูกค้าจัดหาใช้คำของลูกค้า) ไม่งั้นนับวันถึงวันต้องสั่ง
function material_pill(row, cov, order_by) {
	const customer = Boolean(row.customer_provided);
	switch (cov?.state) {
		case "received":
			return { color: "green", label: customer ? __("ลูกค้าส่งแล้ว") : __("รับแล้ว") };
		case "ordered":
			return { color: "green", label: customer ? __("ขอลูกค้าแล้ว") : __("สั่งซื้อแล้ว") };
		case "requested":
			return { color: "blue", label: customer ? __("ขอลูกค้าแล้ว") : __("ขอซื้อแล้ว") };
		default:
			return due_pill(order_by, false);
	}
}

const material_rows = computed(() =>
	props.materials.map((row) => {
		const dates = material_dates(start.value, props.bufferDays, row.lead_time_days);
		const cov = props.coverage?.get(material_key(row)) || null;
		const unit = row.uom || "";
		// ยอดที่ตัดให้แถวนี้ เช่น "ขอแล้ว 20 · สั่งซื้อ 0 · รับ 0 จาก 70 ถุง"
		const progress =
			cov && cov.requested > 0
				? [
						`${customer_word(row, "requested")} ${fmt_qty(cov.requested)}`,
						row.customer_provided ? "" : `${__("สั่งซื้อ")} ${fmt_qty(cov.ordered)}`,
						`${customer_word(row, "received")} ${fmt_qty(cov.received)}`,
				  ]
						.filter(Boolean)
						.join(" · ") + ` ${__("จาก")} ${fmt_qty(row.qty)} ${unit}`
				: "";
		return {
			row,
			...dates,
			cov,
			progress,
			shortfall: cov && cov.state === "partial" ? `${__("ขาด")} ${fmt_qty(cov.shortfall)} ${unit}` : "",
			pill: material_pill(row, cov, dates.order_by),
		};
	})
);

function customer_word(row, stage) {
	if (stage === "requested") return row.customer_provided ? __("ขอลูกค้า") : __("ขอซื้อ");
	return row.customer_provided ? __("ลูกค้าส่ง") : __("รับ");
}

// แก้ค่าในแถว: ค่าไม่ถูกต้องไม่ส่งต่อ และสร้างช่องใหม่ (resets) ให้กลับไปแสดงค่าเดิม
const resets = ref(0);
function edit(event, row, field, value) {
	const invalid = field === "lead_time_days" ? cint(value) < 0 : !(flt(value) > 0);
	if (invalid) {
		frappe.show_alert({
			message: field === "lead_time_days" ? __("จำนวนวันต้องไม่ติดลบ") : __("จำนวนต้องมากกว่า 0"),
			indicator: "red",
		});
		resets.value++;
		return;
	}
	emit(event, row, field, value);
}

// ---------- เพิ่มรายการ ----------

const new_resource = reactive({ resource_type: "Labour", resource: "", qty_per_day: null, lead_time_days: 0 });
const EMPTY_MATERIAL = { item_code: "", item_label: "", uom: "", stock_uom: "", factor: 1, customer_provided: 0, qty: null, lead_time_days: 0 };
const new_material = reactive({ ...EMPTY_MATERIAL });
const adding = ref(null); // "resource" | "material"

watch(
	() => props.task.name,
	() => (adding.value = null)
);

const resource_choices = computed(() =>
	(new_resource.resource_type === "Equipment" ? props.options?.equipment : props.options?.labour) || []
);

function add_resource() {
	const values = { ...new_resource, resource: (new_resource.resource || "").trim() };
	if (!values.resource || !(values.qty_per_day > 0) || cint(values.lead_time_days) < 0) {
		frappe.show_alert({ message: __("กรอกชื่อ จำนวนต่อวัน (มากกว่า 0) และจำนวนวันจองล่วงหน้า (ไม่ติดลบ)"), indicator: "red" });
		return;
	}
	emit("add-resource", values);
	Object.assign(new_resource, { resource: "", qty_per_day: null, lead_time_days: 0 });
}

// เลือก Item แล้วดึงชื่อ หน่วย และ Lead Time ของ Item มาเป็นค่าตั้งต้น
async function set_item(code) {
	new_material.item_code = code || "";
	if (!code) return;
	const { message } = await frappe.db.get_value("Item", code, [
		"item_name",
		"stock_uom",
		"lead_time_days",
		"is_customer_provided_item",
	]);
	if (new_material.item_code !== code || !message) return;
	Object.assign(new_material, {
		item_label: message.item_name || code,
		uom: message.stock_uom || "",
		stock_uom: message.stock_uom || "",
		factor: 1,
		customer_provided: message.is_customer_provided_item ? 1 : 0,
		lead_time_days: message.lead_time_days || 0,
	});
}

function add_material() {
	if (!new_material.item_code || !(new_material.qty > 0) || cint(new_material.lead_time_days) < 0) {
		frappe.show_alert({ message: __("เลือก Item กรอกจำนวน (มากกว่า 0) และ Lead Time (ไม่ติดลบ)"), indicator: "red" });
		return;
	}
	emit("add-material", { ...new_material });
	Object.assign(new_material, EMPTY_MATERIAL);
}

function open_request(name) {
	frappe.set_route("Form", "Material Request", name);
}
</script>

<template>
	<aside class="cs-task-panel">
		<header class="cs-tp-head">
			<div class="cs-tp-title">
				<span class="cs-tp-wbs">{{ task.wbs }}</span>
				<span class="cs-tp-name">{{ task.item_name }}</span>
				<span class="cs-tp-dates">
					{{ fmt_day(start) }} - {{ fmt_day(to_day(task.end_date)) }}
					<template v-if="task.duration">({{ task.duration }} {{ __("วัน") }})</template>
				</span>
			</div>
			<button type="button" class="btn btn-xs btn-default cs-tp-close" :title="__('ปิด')" @click="emit('close')">
				<span v-html="icon('x')" />
			</button>
		</header>

		<!-- คน / เครื่องจักร -->
		<section v-if="resourcePlan" class="cs-tp-section">
			<div class="cs-tp-section-head">
				<h6>{{ __("คน / เครื่องจักร") }}</h6>
				<a v-if="resourcePlan.exists" href="#" class="cs-tp-link" @click.prevent="emit('open-plan', 'Construction Resource Plan')">
					{{ __("เปิดแผน") }}
				</a>
			</div>
			<div v-if="!resource_rows.length" class="cs-tp-empty">{{ __("ยังไม่ได้กำหนด") }}</div>
			<div v-for="item in resource_rows" :key="item.row.name || item.row.key" class="cs-tp-item">
				<div class="cs-tp-item-head">
					<span class="cs-tp-item-icon" v-html="icon(item.type.icon)" />
					<span class="cs-tp-item-name">{{ item.row.resource }}</span>
					<span class="indicator-pill no-indicator-dot cs-tp-pill" :class="item.pill.color">{{ item.pill.label }}</span>
					<button
						v-if="canEditResources"
						type="button"
						class="btn btn-xs btn-link cs-tp-remove"
						:title="__('ลบ')"
						@click="emit('remove-resource', item.row)"
					>
						<span v-html="icon('trash-2', 'xs')" />
					</button>
				</div>
				<div class="cs-tp-fields">
					<label>
						<span>{{ item.type.unit }}</span>
						<FrappeControl
							v-if="canEditResources"
							:key="resets"
							:df="{ fieldtype: 'Float' }"
							:model-value="item.row.qty_per_day"
							@update:model-value="(v) => edit('update-resource', item.row, 'qty_per_day', v)"
						/>
						<b v-else>{{ fmt_qty(item.row.qty_per_day) }}</b>
					</label>
					<label>
						<span>{{ __("จองล่วงหน้า (วัน)") }}</span>
						<FrappeControl
							v-if="canEditResources"
							:key="resets"
							:df="{ fieldtype: 'Int' }"
							:model-value="item.row.lead_time_days || 0"
							@update:model-value="(v) => edit('update-resource', item.row, 'lead_time_days', v)"
						/>
						<b v-else>{{ item.row.lead_time_days || 0 }}</b>
					</label>
					<label>
						<span>{{ __("ต้องจองภายใน") }}</span>
						<b>{{ fmt_day(item.target) }}</b>
					</label>
				</div>
			</div>

			<template v-if="canEditResources">
				<div v-if="adding === 'resource'" class="cs-tp-add">
					<div class="cs-tp-fields">
						<label>
							<span>{{ __("ชนิด") }}</span>
							<FrappeControl
								:df="{ fieldtype: 'Select', options: TYPES.map(({ value, label }) => ({ value, label })) }"
								v-model="new_resource.resource_type"
							/>
						</label>
						<label class="cs-tp-wide">
							<span>{{ __("ชื่อ (ตรงกับที่ลงใน Daily Report)") }}</span>
							<!-- key: เปลี่ยนชนิดแล้วสร้าง control ใหม่ให้ตัวเลือกเปลี่ยนตาม -->
							<FrappeControl
								:key="new_resource.resource_type"
								:df="{ fieldtype: 'Autocomplete', options: resource_choices }"
								v-model="new_resource.resource"
							/>
						</label>
						<label>
							<span>{{ type_of(new_resource.resource_type).unit }}</span>
							<FrappeControl :df="{ fieldtype: 'Float' }" v-model="new_resource.qty_per_day" />
						</label>
						<label>
							<span>{{ __("จองล่วงหน้า (วัน)") }}</span>
							<FrappeControl :df="{ fieldtype: 'Int' }" v-model="new_resource.lead_time_days" />
						</label>
					</div>
					<div class="cs-tp-actions">
						<button type="button" class="btn btn-xs btn-default" @click="adding = null">{{ __("ยกเลิก") }}</button>
						<button type="button" class="btn btn-xs btn-primary" @click="add_resource">{{ __("เพิ่ม") }}</button>
					</div>
				</div>
				<button v-else type="button" class="btn btn-xs btn-default cs-tp-add-btn" @click="adding = 'resource'">
					<span v-html="icon('plus', 'xs')" />{{ __("เพิ่มคน / เครื่องจักร") }}
				</button>
			</template>
		</section>

		<!-- วัสดุ -->
		<section v-if="materialPlan" class="cs-tp-section">
			<div class="cs-tp-section-head">
				<h6>{{ __("วัสดุ") }}</h6>
				<a v-if="materialPlan.exists" href="#" class="cs-tp-link" @click.prevent="emit('open-plan', 'Construction Material Plan')">
					{{ __("เปิดแผน") }}
				</a>
			</div>
			<div class="cs-tp-note">{{ __("ให้ของถึงก่อนเริ่มงาน {0} วัน (Buffer Days ของแผนวัสดุ)", [bufferDays || 0]) }}</div>
			<div v-if="!material_rows.length" class="cs-tp-empty">{{ __("ยังไม่ได้กำหนด") }}</div>
			<div v-for="item in material_rows" :key="item.row.name || item.row.key" class="cs-tp-item">
				<div class="cs-tp-item-head">
					<span class="cs-tp-item-icon" v-html="icon('package')" />
					<span class="cs-tp-item-name" :title="item.row.item_code">{{ item.row.item_label || item.row.item_code }}</span>
					<span v-if="item.row.customer_provided" class="cs-tp-tag" :title="__('Customer Provided Item')">{{ __("ลูกค้าจัดหา") }}</span>
					<span class="indicator-pill no-indicator-dot cs-tp-pill" :class="item.pill.color">{{ item.pill.label }}</span>
					<button
						v-if="canEditMaterials"
						type="button"
						class="btn btn-xs btn-link cs-tp-remove"
						:title="__('ลบ')"
						@click="emit('remove-material', item.row)"
					>
						<span v-html="icon('trash-2', 'xs')" />
					</button>
				</div>
				<div class="cs-tp-fields">
					<label>
						<span>{{ __("จำนวน") }} {{ item.row.uom ? `(${item.row.uom})` : "" }}</span>
						<FrappeControl
							v-if="canEditMaterials"
							:key="resets"
							:df="{ fieldtype: 'Float' }"
							:model-value="item.row.qty"
							@update:model-value="(v) => edit('update-material', item.row, 'qty', v)"
						/>
						<b v-else>{{ fmt_qty(item.row.qty) }}</b>
					</label>
					<label>
						<span>{{ __("Lead Time (วัน)") }}</span>
						<FrappeControl
							v-if="canEditMaterials"
							:key="resets"
							:df="{ fieldtype: 'Int' }"
							:model-value="item.row.lead_time_days || 0"
							@update:model-value="(v) => edit('update-material', item.row, 'lead_time_days', v)"
						/>
						<b v-else>{{ item.row.lead_time_days || 0 }}</b>
					</label>
					<label>
						<span>{{ __("ต้องสั่งภายใน") }}</span>
						<b>{{ fmt_day(item.order_by) }}</b>
					</label>
					<label>
						<span>{{ __("ต้องการภายใน") }}</span>
						<b>{{ fmt_day(item.required_by) }}</b>
					</label>
				</div>
				<div v-if="item.progress || item.shortfall" class="cs-tp-note">
					{{ item.progress }}<template v-if="item.progress && item.shortfall"> · </template>
					<b v-if="item.shortfall" class="cs-tp-short">{{ item.shortfall }}</b>
				</div>
				<a v-if="item.row.material_request" href="#" class="cs-tp-link" @click.prevent="open_request(item.row.material_request)">
					{{ __("MR ที่สร้างจากแผน") }}: {{ item.row.material_request }}
					<template v-if="item.row.request_status">· {{ __(item.row.request_status) }}</template>
				</a>
			</div>

			<template v-if="canEditMaterials">
				<div v-if="adding === 'material'" class="cs-tp-add">
					<div class="cs-tp-fields">
						<label class="cs-tp-wide">
							<span>{{ __("Item") }}</span>
							<FrappeControl
								:df="{ fieldtype: 'Link', options: 'Item' }"
								:model-value="new_material.item_code"
								@update:model-value="set_item"
							/>
						</label>
						<label>
							<span>{{ __("จำนวน") }} {{ new_material.uom ? `(${new_material.uom})` : "" }}</span>
							<FrappeControl :df="{ fieldtype: 'Float' }" v-model="new_material.qty" />
						</label>
						<label>
							<span>{{ __("Lead Time (วัน)") }}</span>
							<FrappeControl :df="{ fieldtype: 'Int' }" v-model="new_material.lead_time_days" />
						</label>
					</div>
					<div class="cs-tp-actions">
						<button type="button" class="btn btn-xs btn-default" @click="adding = null">{{ __("ยกเลิก") }}</button>
						<button type="button" class="btn btn-xs btn-primary" @click="add_material">{{ __("เพิ่ม") }}</button>
					</div>
				</div>
				<button v-else type="button" class="btn btn-xs btn-default cs-tp-add-btn" @click="adding = 'material'">
					<span v-html="icon('plus', 'xs')" />{{ __("เพิ่มวัสดุ") }}
				</button>
			</template>
		</section>

		<div v-if="!resourcePlan && !materialPlan" class="cs-tp-empty">
			{{ __("ไม่มีสิทธิ์ดูแผนทรัพยากรและแผนวัสดุ") }}
		</div>
	</aside>
</template>

<style scoped>
.cs-task-panel {
	flex: 0 0 340px;
	display: flex;
	flex-direction: column;
	gap: 16px;
	min-width: 0;
	padding: 12px 14px 20px;
	overflow-y: auto;
	border-left: 1px solid color-mix(in srgb, var(--border-color) 70%, transparent);
	background: var(--card-bg);
	font-size: var(--text-sm);
}
.cs-tp-head {
	display: flex;
	align-items: flex-start;
	gap: 8px;
}
.cs-tp-title {
	display: flex;
	flex: 1;
	flex-direction: column;
	gap: 2px;
	min-width: 0;
}
.cs-tp-wbs {
	color: var(--text-muted);
	font-size: var(--text-xs);
	font-weight: 600;
}
.cs-tp-name {
	color: var(--heading-color);
	font-size: var(--text-md);
	font-weight: 700;
	line-height: 1.3;
}
.cs-tp-dates,
.cs-tp-note {
	color: var(--text-muted);
	font-size: var(--text-xs);
}
.cs-tp-short {
	color: var(--red-600);
}
.cs-tp-tag {
	flex: none;
	padding: 0 6px;
	border-radius: var(--radius-sm);
	background: var(--control-bg);
	color: var(--text-muted);
	font-size: var(--text-2xs, 10px);
}
.cs-tp-close :deep(svg),
.cs-tp-item-icon :deep(svg),
.cs-tp-remove :deep(svg),
.cs-tp-add-btn :deep(svg) {
	stroke: currentColor;
}
.cs-tp-section {
	display: flex;
	flex-direction: column;
	gap: 8px;
}
.cs-tp-section-head {
	display: flex;
	align-items: center;
	justify-content: space-between;
	padding-bottom: 4px;
	border-bottom: 1px solid color-mix(in srgb, var(--border-color) 70%, transparent);
}
.cs-tp-section-head h6 {
	margin: 0;
	color: var(--heading-color);
	font-size: var(--text-sm);
	font-weight: 700;
}
.cs-tp-link {
	color: var(--text-muted);
	font-size: var(--text-xs);
}
.cs-tp-link:hover {
	color: var(--text-color);
}
.cs-tp-empty {
	padding: 10px;
	border-radius: var(--radius);
	background: var(--subtle-fg);
	color: var(--text-muted);
	font-size: var(--text-xs);
	text-align: center;
}
.cs-tp-item,
.cs-tp-add {
	display: flex;
	flex-direction: column;
	gap: 8px;
	padding: 10px;
	border: 1px solid color-mix(in srgb, var(--border-color) 70%, transparent);
	border-radius: var(--radius);
}
.cs-tp-add {
	background: var(--subtle-fg);
}
.cs-tp-item-head {
	display: flex;
	align-items: center;
	gap: 6px;
	min-width: 0;
}
.cs-tp-item-icon {
	display: flex;
	color: var(--text-muted);
}
.cs-tp-item-name {
	flex: 1;
	min-width: 0;
	overflow: hidden;
	font-weight: 600;
	text-overflow: ellipsis;
	white-space: nowrap;
}
.cs-tp-pill {
	flex: none;
	height: 20px;
	padding: 0 8px;
	font-size: var(--text-xs);
}
.cs-tp-remove {
	padding: 0 2px;
	color: var(--text-muted);
}
.cs-tp-fields {
	display: grid;
	grid-template-columns: repeat(2, minmax(0, 1fr));
	gap: 6px 10px;
}
.cs-tp-fields label {
	display: flex;
	flex-direction: column;
	gap: 2px;
	min-width: 0;
	margin: 0;
}
.cs-tp-fields label > span {
	color: var(--text-muted);
	font-size: var(--text-xs);
}
.cs-tp-fields label > b {
	font-weight: 600;
	font-variant-numeric: tabular-nums;
}
.cs-tp-wide {
	grid-column: 1 / -1;
}
.cs-tp-actions {
	display: flex;
	justify-content: flex-end;
	gap: 6px;
}
.cs-tp-add-btn {
	display: inline-flex;
	align-items: center;
	align-self: flex-start;
	gap: 4px;
}
/* จอแคบ: แผงลอยทับ timeline ด้านขวา */
@media (max-width: 768px) {
	.cs-task-panel {
		position: absolute;
		top: 0;
		right: 0;
		bottom: 0;
		z-index: 5;
		width: min(340px, 90%);
		box-shadow: -8px 0 24px rgb(0 0 0 / 0.12);
	}
}
</style>
