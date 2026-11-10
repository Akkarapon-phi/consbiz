<!-- แท็บ "ทรัพยากร" ของแผงงาน: คน/เครื่องจักร และวัสดุของงานที่เลือก (ตรงกับ construction_management/components/TaskPanel.vue ของระบบเต็ม)
     ข้อมูลอยู่ใน planner.js ทุกการแก้ Undo ได้และบันทึกพร้อมแผนงาน แผงนี้เก็บเองแค่ช่องเพิ่มรายการ
     วันต้องจอง/ต้องสั่งคิดจากวันเริ่มงานปัจจุบัน สถานะวัสดุ = ยอดขอ/สั่ง/รับของโครงการที่ตัดให้แถวนี้ (planner.material_coverage) -->
<template>
	<div class="pl-res">
		<section v-if="resource_plan" class="pl-insp-sec">
			<h4>คน / เครื่องจักร</h4>
			<p v-if="!resource_rows.length" class="pl-insp-note">ยังไม่ได้กำหนด</p>
			<article v-for="item in resource_rows" :key="item.row.name || item.row.key" class="pl-res-item">
				<header>
					<Icon :name="item.type.icon" :size="15" />
					<b :title="item.row.resource">{{ item.row.resource }}</b>
					<span class="ss-tag" :class="`tone-${item.pill.tone}`">{{ item.pill.label }}</span>
					<button
						v-if="p.can_edit_resources"
						type="button"
						class="ss-icon-btn ss-icon-btn--sm"
						aria-label="ลบ"
						title="ลบ"
						@click="p.remove_resource(item.row)"
					>
						<Icon name="trash" :size="15" />
					</button>
				</header>
				<div class="pl-res-fields">
					<label>
						<span>{{ item.type.unit }}</span>
						<input
							v-if="p.can_edit_resources"
							class="ss-input"
							inputmode="decimal"
							:value="item.row.qty_per_day"
							@change="(e) => edit(e, item.row, 'qty_per_day')"
						/>
						<b v-else>{{ qty(item.row.qty_per_day) }}</b>
					</label>
					<label>
						<span>จองล่วงหน้า (วัน)</span>
						<input
							v-if="p.can_edit_resources"
							class="ss-input"
							inputmode="numeric"
							:value="item.row.lead_time_days || 0"
							@change="(e) => edit(e, item.row, 'lead_time_days')"
						/>
						<b v-else>{{ item.row.lead_time_days || 0 }}</b>
					</label>
					<label>
						<span>ต้องจองภายใน</span>
						<b>{{ date(item.target) }}</b>
					</label>
				</div>
			</article>

			<template v-if="p.can_edit_resources">
				<div v-if="adding === 'resource'" class="pl-res-add">
					<div class="pl-res-fields is-two">
						<label>
							<span>ชนิด</span>
							<SelectBox v-model="new_resource.resource_type" :options="TYPES" label="ชนิด" />
						</label>
						<Picker
							v-model="new_resource.resource"
							label="ชื่อ (ตรงกับใน Daily Report)"
							:options="resource_choices"
							allow_text
						/>
						<label>
							<span>{{ type_of(new_resource.resource_type).unit }}</span>
							<input v-model="new_resource.qty_per_day" class="ss-input" inputmode="decimal" />
						</label>
						<label>
							<span>จองล่วงหน้า (วัน)</span>
							<input v-model="new_resource.lead_time_days" class="ss-input" inputmode="numeric" />
						</label>
					</div>
					<div class="pl-res-actions">
						<button type="button" class="pl-tool is-small" @click="adding = null">ยกเลิก</button>
						<button type="button" class="ss-btn ss-btn--primary pl-save" @click="add_resource">เพิ่ม</button>
					</div>
				</div>
				<button v-else type="button" class="pl-res-more" @click="adding = 'resource'">
					<Icon name="plus" :size="14" /> เพิ่มคน / เครื่องจักร
				</button>
			</template>
		</section>

		<section v-if="material_plan" class="pl-insp-sec">
			<h4>วัสดุ <small>ของถึงก่อนเริ่มงาน {{ buffer_days }} วัน</small></h4>
			<p v-if="!material_rows.length" class="pl-insp-note">ยังไม่ได้กำหนด</p>
			<article v-for="item in material_rows" :key="item.row.name || item.row.key" class="pl-res-item">
				<header>
					<Icon name="cart" :size="15" />
					<b :title="item.row.item_code">{{ item.row.item_label || item.row.item_code }}</b>
					<span class="ss-tag" :class="`tone-${item.pill.tone}`">{{ item.pill.label }}</span>
					<button
						v-if="p.can_edit_materials"
						type="button"
						class="ss-icon-btn ss-icon-btn--sm"
						aria-label="ลบ"
						title="ลบ"
						@click="p.remove_material(item.row)"
					>
						<Icon name="trash" :size="15" />
					</button>
				</header>
				<small v-if="item.row.customer_provided" class="pl-res-owner">ผู้ว่าจ้างจัดหา</small>
				<div class="pl-res-fields is-two">
					<label>
						<span>จำนวน{{ item.row.uom ? ` (${item.row.uom})` : "" }}</span>
						<input
							v-if="p.can_edit_materials"
							class="ss-input"
							inputmode="decimal"
							:value="item.row.qty"
							@change="(e) => edit(e, item.row, 'qty')"
						/>
						<b v-else>{{ qty(item.row.qty) }}</b>
					</label>
					<label>
						<span>Lead Time (วัน)</span>
						<input
							v-if="p.can_edit_materials"
							class="ss-input"
							inputmode="numeric"
							:value="item.row.lead_time_days || 0"
							@change="(e) => edit(e, item.row, 'lead_time_days')"
						/>
						<b v-else>{{ item.row.lead_time_days || 0 }}</b>
					</label>
					<label>
						<span>ต้องสั่งภายใน</span>
						<b>{{ date(item.order_by) }}</b>
					</label>
					<label>
						<span>ต้องการภายใน</span>
						<b>{{ date(item.required_by) }}</b>
					</label>
				</div>
				<p v-if="item.progress || item.shortfall" class="pl-insp-note">
					{{ item.progress }}<template v-if="item.progress && item.shortfall"> · </template>
					<b v-if="item.shortfall" class="is-late">{{ item.shortfall }}</b>
				</p>
				<a
					v-if="item.row.material_request"
					class="pl-res-link"
					:href="`/app/material-request/${encodeURIComponent(item.row.material_request)}`"
					target="_blank"
					rel="noopener"
				>
					MR ที่สร้างจากแผน: {{ item.row.material_request }}
					<template v-if="item.row.request_status">· {{ item.row.request_status }}</template>
				</a>
			</article>

			<template v-if="p.can_edit_materials">
				<div v-if="adding === 'material'" class="pl-res-add">
					<Picker
						:model-value="new_material.item_code"
						label="วัสดุ (Item)"
						:remote_fn="search_items"
						:display_value="new_material.item_label"
						@select="set_item"
					/>
					<label v-if="new_material.item_code && !new_material.customer_provided" class="pl-switch" :class="{ 'is-on': new_material.employer_supplied }">
						<input v-model="new_material.employer_supplied" type="checkbox" />
						<span class="pl-switch-track"><i></i></span>
						<span>ผู้ว่าจ้างจัดหา</span>
					</label>
					<div class="pl-res-fields is-two">
						<label>
							<span>จำนวน{{ new_material.uom ? ` (${new_material.uom})` : "" }}</span>
							<input v-model="new_material.qty" class="ss-input" inputmode="decimal" />
						</label>
						<label>
							<span>Lead Time (วัน)</span>
							<input v-model="new_material.lead_time_days" class="ss-input" inputmode="numeric" />
						</label>
					</div>
					<div class="pl-res-actions">
						<button type="button" class="pl-tool is-small" @click="adding = null">ยกเลิก</button>
						<button type="button" class="ss-btn ss-btn--primary pl-save" :disabled="adding_material" @click="add_material">
							เพิ่ม
						</button>
					</div>
				</div>
				<button v-else type="button" class="pl-res-more" @click="adding = 'material'">
					<Icon name="plus" :size="14" /> เพิ่มวัสดุ
				</button>
			</template>
		</section>

		<p v-if="!resource_plan && !material_plan" class="pl-insp-note">ไม่มีสิทธิ์ดูแผนทรัพยากรและแผนวัสดุ</p>
	</div>
</template>

<script setup>
import { computed, reactive, ref, watch } from "vue";
import Icon from "../../../../shared/components/Icon.vue";
import Picker from "../../../../shared/components/Picker.vue";
import SelectBox from "../../../../shared/components/SelectBox.vue";
import { call, num, post, show_error, thai_date, toast } from "../../../../shared/api.js";
import { due_pill, material_pill } from "./resource_rows.js";
import { book_by, from_day, material_dates, material_key, to_day } from "../../../../construction_management/schedule.js";

const props = defineProps({
	p: { type: Object, required: true },
	task: { type: Object, required: true },
});

const TYPES = [
	{ value: "Labour", label: "แรงงาน", unit: "คน/วัน", icon: "users" },
	{ value: "Equipment", label: "เครื่องจักร", unit: "คัน/วัน", icon: "truck" },
];
const EMPTY_RESOURCE = { resource_type: "Labour", resource: "", qty_per_day: "", lead_time_days: 0 };
const EMPTY_MATERIAL = {
	item_code: "",
	item_label: "",
	uom: "",
	stock_uom: "",
	factor: 1,
	customer_provided: 0,
	employer_supplied: false,
	qty: "",
	lead_time_days: 0,
};

const type_of = (value) => TYPES.find((t) => t.value === value) || TYPES[0];
const qty = (value) => num(value || 0);
const date = (day) => (day === null || day === undefined ? "-" : thai_date(from_day(day), { year: true }));

const resource_plan = computed(() => props.p.data?.resource_plan);
const material_plan = computed(() => props.p.data?.material_plan);
const buffer_days = computed(() => material_plan.value?.buffer_days || 0);
const start = computed(() => to_day(props.task.start_date));

const resource_rows = computed(() =>
	props.p.resources
		.filter((row) => row.task === props.task.name)
		.map((row) => {
			const target = book_by(start.value, row.lead_time_days);
			const started = start.value !== null && start.value <= props.p.cutoff_day;
			return {
				row,
				type: type_of(row.resource_type),
				target,
				pill: started ? { tone: "blue", label: "เริ่มงานแล้ว" } : due_pill(target, props.p.cutoff_day),
			};
		})
);

const material_rows = computed(() =>
	props.p.materials
		.filter((row) => row.task === props.task.name)
		.map((row) => {
			const dates = material_dates(start.value, buffer_days.value, row.lead_time_days);
			const coverage = props.p.material_coverage.get(material_key(row)) || null;
			const owner = Boolean(row.customer_provided);
			const unit = row.uom || "";
			const progress =
				coverage && coverage.requested > 0
					? [
							`${owner ? "ขอผู้ว่าจ้าง" : "ขอซื้อ"} ${qty(coverage.requested)}`,
							owner ? "" : `สั่งซื้อ ${qty(coverage.ordered)}`,
							`${owner ? "ผู้ว่าจ้างส่ง" : "รับ"} ${qty(coverage.received)}`,
					  ]
							.filter(Boolean)
							.join(" · ") + ` จาก ${qty(row.qty)} ${unit}`
					: "";
			return {
				row,
				...dates,
				progress,
				shortfall: coverage?.state === "partial" ? `ขาด ${qty(coverage.shortfall)} ${unit}` : "",
				pill: material_pill(row, coverage, dates.order_by, props.p.cutoff_day),
			};
		})
);

// แก้ค่าในแถว: ค่าไม่ถูกต้องไม่ลงแผน และคืนค่าเดิมในช่อง
function edit(event, row, field) {
	const value = Number(String(event.target.value).replace(/,/g, ""));
	const is_days = field === "lead_time_days";
	if (!Number.isFinite(value) || (is_days ? value < 0 : value <= 0)) {
		toast(is_days ? "จำนวนวันต้องไม่ติดลบ" : "จำนวนต้องมากกว่า 0", "error");
		event.target.value = row[field] ?? 0;
		return;
	}
	props.p.update_plan_row(row, field, value);
}

// ---------- เพิ่มรายการ ----------
const adding = ref(null); // "resource" | "material"
const adding_material = ref(false);
const new_resource = reactive({ ...EMPTY_RESOURCE });
const new_material = reactive({ ...EMPTY_MATERIAL });

watch(
	() => props.task.name,
	() => (adding.value = null)
);

const resource_choices = computed(() =>
	(new_resource.resource_type === "Equipment" ? resource_plan.value?.options?.equipment : resource_plan.value?.options?.labour || [])?.map(
		(name) => ({ value: name, label: name })
	) || []
);

const is_days_valid = (value) => Number.isInteger(Number(value || 0)) && Number(value || 0) >= 0;

function add_resource() {
	const resource = String(new_resource.resource || "").trim();
	const qty_per_day = Number(new_resource.qty_per_day);
	if (!resource || !(qty_per_day > 0) || !is_days_valid(new_resource.lead_time_days)) {
		toast("กรอกชื่อ จำนวนต่อวัน (มากกว่า 0) และจำนวนวันจองล่วงหน้า (ไม่ติดลบ)", "error");
		return;
	}
	const added = props.p.add_resource(props.task, {
		resource_type: new_resource.resource_type,
		resource,
		qty_per_day,
		lead_time_days: Number(new_resource.lead_time_days || 0),
	});
	if (added) Object.assign(new_resource, { resource: "", qty_per_day: "", lead_time_days: 0 });
}

// เลือกได้เฉพาะ Item หลัก (Item คู่ของผู้ว่าจ้างจัดหาระบบเลือกให้เมื่อติ๊ก)
async function search_items(txt) {
	const rows = await call("consbiz.site_docs.search_items", { kind: "mr", txt });
	return rows.map((row) => ({
		value: row.item_code,
		label: row.item_name || row.item_code,
		description: row.item_code,
		stock_uom: row.stock_uom,
	}));
}

// เลือก Item แล้วดึง Lead Time และ Customer Provided มาเป็นค่าตั้งต้น
async function set_item(option) {
	const code = option.value;
	Object.assign(new_material, {
		item_code: code || "",
		item_label: option.label || "",
		uom: option.stock_uom || "",
		stock_uom: option.stock_uom || "",
		customer_provided: 0,
		employer_supplied: false,
		lead_time_days: 0,
	});
	if (!code) return;
	try {
		const item = await call("frappe.client.get_value", {
			doctype: "Item",
			filters: code,
			fieldname: ["lead_time_days", "is_customer_provided_item"],
		});
		if (new_material.item_code !== code || !item) return;
		Object.assign(new_material, {
			lead_time_days: item.lead_time_days || 0,
			customer_provided: item.is_customer_provided_item ? 1 : 0,
		});
	} catch (error) {
		show_error(error);
	}
}

async function add_material() {
	const qty_value = Number(new_material.qty);
	if (!new_material.item_code || !(qty_value > 0) || !is_days_valid(new_material.lead_time_days)) {
		toast("เลือก Item กรอกจำนวน (มากกว่า 0) และ Lead Time (ไม่ติดลบ)", "error");
		return;
	}
	const { employer_supplied, ...material } = { ...new_material, qty: qty_value, lead_time_days: Number(new_material.lead_time_days || 0) };
	adding_material.value = true;
	try {
		// ผู้ว่าจ้างจัดหา: ใช้ Item คู่ (สร้างให้ถ้ายังไม่มี) ยอดจึงแยกจากของที่ซื้อเอง
		if (employer_supplied && !material.customer_provided) {
			const code = await post("consbiz.employer_supplied.get_employer_item", { item_code: material.item_code });
			Object.assign(material, {
				item_code: code,
				item_label: `${material.item_label} (ผู้ว่าจ้างจัดหา)`,
				customer_provided: 1,
			});
		}
		props.p.add_material(props.task, material);
		Object.assign(new_material, EMPTY_MATERIAL);
	} catch (error) {
		show_error(error);
	} finally {
		adding_material.value = false;
	}
}
</script>
