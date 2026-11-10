<!-- สร้าง/แก้ BOQ ในแอปออฟฟิศ แทนฟอร์มระบบเต็ม (สูตรยอดตรงกับ boq.py, เลข WBS ตรงกับ assign_wbs)
     หลัง Submit แก้ไม่ได้ งานเพิ่ม-ลดต่อจากนี้เป็นหน้าที่ของ Variation Order -->
<template>
	<div class="ss-boq-form" :class="{ 'no-tools': doc && !draft }">
		<TopBar :title="title" :subtitle="doc?.customer" back_to="boq" no_project />

		<div class="ss-content ss-boq-content">
			<div v-if="doc" class="ss-list-head ss-boq-tabbar">
				<StatusTabs v-model="tab" :options="TABS" />
				<div class="ss-list-tools">
					<a
						v-if="doc?.name && doc.can?.export"
						class="ss-icon-btn"
						:href="export_url"
						title="ส่งออก Excel"
						aria-label="ส่งออก Excel"
					>
						<Icon name="receive" :size="19" />
					</a>
					<template v-if="draft">
						<template v-if="doc.plan">
							<a v-if="doc.can?.open_plan" class="ss-btn ss-btn--soft ss-list-create" :href="plan_url">เปิดแผนงาน</a>
							<button v-if="doc.can?.sync_plan" type="button" class="ss-btn ss-btn--soft ss-list-create" :disabled="busy" @click="open_sync">
								อัปเดตแผนงาน
							</button>
						</template>
						<button
							v-else-if="doc.name && doc.can_create_plan"
							type="button"
							class="ss-btn ss-btn--soft ss-list-create"
							:disabled="busy"
							@click="create_plan"
						>
							สร้างแผนงาน
						</button>
						<button
							type="button"
							class="ss-btn ss-btn--primary ss-list-create"
							aria-label="บันทึก"
							:disabled="busy || !dirty"
							@click="save()"
						>
							<Icon name="save" :size="18" />
							<span>บันทึก</span>
						</button>
						<button
							v-if="doc.name && doc.can?.submit"
							type="button"
							class="ss-btn ss-btn--soft ss-list-create"
							:disabled="busy"
							@click="ask('submit')"
						>
							Submit
						</button>
					</template>
					<template v-else-if="doc">
						<button
							v-if="doc.docstatus === 1 && !doc.plan && doc.can?.cancel"
							type="button"
							class="ss-btn ss-btn--ghost-danger ss-list-create"
							:disabled="busy"
							@click="ask('cancel')"
						>
							ยกเลิก
						</button>
						<button
							v-if="doc.docstatus === 2 && doc.can?.amend"
							type="button"
							class="ss-btn ss-btn--soft ss-list-create"
							:disabled="busy"
							@click="run('amend_boq')"
						>
							แก้ไขฉบับใหม่
						</button>
						<a v-if="doc.plan && doc.can?.open_plan" class="ss-btn ss-btn--soft ss-list-create" :href="plan_url">เปิดแผนงาน</a>
						<button
							v-else-if="doc.docstatus === 1 && !doc.plan && doc.can_create_plan"
							type="button"
							class="ss-btn ss-btn--primary ss-list-create"
							:disabled="busy"
							@click="create_plan"
						>
							สร้างแผนงาน
						</button>
					</template>
				</div>
			</div>

			<Skeleton v-if="!doc" :rows="6" />
			<template v-else>
				<div class="ss-boq-head">
					<Picker
						v-model="doc.customer"
						label="ลูกค้า"
						:display_value="doc.customer"
						:remote_fn="(q) => search('Customer', q)"
						:class="{ 'is-locked': !draft }"
						clearable
					/>
					<label class="ss-field">
						<span class="ss-field-label">โครงการ</span>
						<input v-model="doc.project" class="ss-input" :disabled="!draft" />
					</label>
					<label class="ss-field">
						<span class="ss-field-label">สถานที่</span>
						<input v-model="doc.location" class="ss-input" :disabled="!draft" />
					</label>
					<div class="ss-field">
						<span class="ss-field-label">วันที่</span>
						<DateInput v-model="doc.date" label="วันที่" :disabled="!draft" />
					</div>
					<div class="ss-field">
						<span class="ss-field-label">บริษัท</span>
						<SelectBox
							v-model="doc.company"
							label="บริษัท"
							:options="companies"
							:disabled="!draft"
						/>
					</div>
					<div class="ss-boq-checks">
						<label class="ss-checkline">
							<input
								:checked="!!doc.combined_rate"
								type="checkbox"
								:disabled="!draft"
								@change="toggle_combined"
							/>
							<span>ราคารวม (ไม่แยกค่าวัสดุ/ค่าแรง)</span>
						</label>
						<label class="ss-checkline">
							<input
								v-model="doc.round_down_total"
								type="checkbox"
								:true-value="1"
								:false-value="0"
								:disabled="!draft"
							/>
							<span>ตัดสตางค์ยอดรวม</span>
						</label>
					</div>
				</div>

				<div v-if="doc.docstatus === 1" class="ss-banner tone-blue">
					<Icon name="alert" :size="20" />
					<div class="ss-banner-text">
						Submit แล้ว แก้ไม่ได้ งานเพิ่ม-ลดต่อจากนี้ให้ทำผ่าน Variation Order
					</div>
				</div>

				<div v-if="draft" class="ss-boq-tools">
					<button type="button" class="pl-tool" @click="add_row">
						<Icon name="plus" :size="16" /><span>เพิ่มรายการ</span>
					</button>
					<span class="ss-boq-sep"></span>
					<button
						type="button"
						class="pl-tool"
						:disabled="!selected.size"
						@click="shift_level(1)"
					>
						<Icon name="indent" :size="16" /><span>Indent</span>
					</button>
					<button
						type="button"
						class="pl-tool"
						:disabled="!selected.size"
						@click="shift_level(-1)"
					>
						<Icon name="outdent" :size="16" /><span>Outdent</span>
					</button>
					<button
						type="button"
						class="pl-tool"
						:disabled="!selected.size"
						@click="remove_rows"
					>
						<Icon name="trash" :size="16" /><span>ลบแถว</span>
					</button>
					<span class="ss-boq-sep"></span>
					<button type="button" class="pl-tool" @click="file_input.click()">
						<Icon name="file" :size="16" /><span>นำเข้า Excel</span>
					</button>
					<a class="pl-tool" :href="template_url"
						><Icon name="receive" :size="16" /><span>แม่แบบ Excel</span></a
					>
					<input
						ref="file_input"
						type="file"
						accept=".xlsx,.csv"
						hidden
						@change="read_file"
					/>
				</div>

				<div class="ss-boq-table-wrap">
					<table ref="table" class="ss-boq-table" :class="{ 'is-combined': doc.combined_rate }">
						<thead>
							<tr>
								<th v-if="draft" :rowspan="header_rows" class="c-grip"></th>
								<th v-if="draft" :rowspan="header_rows" class="c-check"></th>
								<th :rowspan="header_rows" class="c-wbs">ลำดับที่</th>
								<th :rowspan="header_rows" class="c-name">รายการ</th>
								<th :rowspan="header_rows" class="c-qty">จำนวน</th>
								<th :rowspan="header_rows" class="c-uom">หน่วย</th>
								<template v-if="doc.combined_rate">
									<th class="c-num">ราคาต่อหน่วย</th>
									<th class="c-sum">จำนวนเงิน</th>
								</template>
								<template v-else>
									<th colspan="2">ค่าวัสดุ</th>
									<th colspan="2">ค่าแรงงาน</th>
									<th rowspan="2" class="c-sum">รวมค่าวัสดุ<br />และค่าแรงงาน</th>
								</template>
								<th v-if="draft" :rowspan="header_rows" class="c-more"></th>
							</tr>
							<tr v-if="!doc.combined_rate">
								<th class="c-num">ราคาต่อหน่วย</th>
								<th class="c-num">จำนวนเงิน</th>
								<th class="c-num">ราคาต่อหน่วย</th>
								<th class="c-num">จำนวนเงิน</th>
							</tr>
						</thead>
						<tbody>
							<tr
								v-for="(row, i) in rows"
								:key="row._key"
								:data-row="row._key"
								:class="{
									'is-dragging': dragging.has(row._key),
									'is-heading': has_children(i),
									'is-sticky': is_sticky(row),
									'is-selected': selected.has(row._key),
								}"
								:style="
									is_sticky(row)
										? { '--ss-boq-offset': `${heading_tops[row._key]}px` }
										: null
								"
								@mousedown.capture="draft && press_row($event, i)"
								@click.capture="draft && guard_click($event)"
								@contextmenu="draft && open_menu($event, i)"
								@touchstart.passive="draft && hold_start($event, i)"
								@touchmove.passive="hold_end"
								@touchend.passive="hold_end"
								@touchcancel.passive="hold_end"
							>
								<td v-if="draft" class="c-grip">
									<span
										class="ss-grip"
										title="ลากเพื่อย้ายลำดับ"
										aria-hidden="true"
										@pointerdown="start_drag($event, i)"
									>
										<Icon name="grip" :size="15" :stroke="2.6" />
									</span>
								</td>
								<td v-if="draft" class="c-check">
									<input
										type="checkbox"
										:checked="selected.has(row._key)"
										:aria-label="`เลือกแถว ${row.wbs}`"
										@click="pick_row($event, i)"
									/>
								</td>
								<td class="c-wbs">{{ row.wbs }}</td>
								<td class="c-name">
									<div
										class="ss-boq-name"
										:style="{ paddingLeft: `${(row.level - 1) * 14}px` }"
									>
										<BoqItemInput
											:model-value="row.item_name"
											:search="search_items"
											:disabled="!draft"
											@update:model-value="type_name(row, $event)"
											@pick="apply_item(row, $event)"
										/>
										<RichText :html="row.description" class="ss-boq-desc" />
									</div>
								</td>
								<td class="c-qty">
									<input
										v-model.number="row.quantity"
										type="number"
										step="any"
										class="ss-boq-input is-num"
										:disabled="!draft"
									/>
								</td>
								<td class="c-uom">
									<SelectBox
										v-model="row.uom"
										variant="cell"
										label="หน่วย"
										:options="uom_options"
										:disabled="!draft"
										placeholder=""
									/>
								</td>
								<td class="c-num">
									<input
										v-model.number="row.material_rate"
										type="number"
										step="any"
										class="ss-boq-input is-num"
										:disabled="!draft"
									/>
								</td>
								<template v-if="!doc.combined_rate">
									<td class="c-num c-amount">{{ amount(row_amounts(row).material) }}</td>
									<td class="c-num">
										<input
											v-model.number="row.labour_rate"
											type="number"
											step="any"
											class="ss-boq-input is-num"
											:disabled="!draft || !!row.combined_rate"
										/>
									</td>
									<td class="c-num c-amount">{{ amount(row_amounts(row).labour) }}</td>
								</template>
								<td class="c-sum c-amount">{{ amount(row_amounts(row).total) }}</td>
								<td v-if="draft" class="c-more">
									<button
										type="button"
										class="ss-boq-find"
										title="รายละเอียดแถว"
										aria-label="รายละเอียดแถว"
										@click="detail = row"
									>
										<Icon name="pen" :size="14" />
									</button>
								</td>
							</tr>
							<tr v-if="!rows.length" @contextmenu="draft && open_menu($event, -1)">
								<td :colspan="column_count" class="ss-boq-empty">
									ยังไม่มีรายการ กด "เพิ่มรายการ" หรือนำเข้าจาก Excel
								</td>
							</tr>
						</tbody>
					</table>
				</div>

				<div class="ss-boq-totals">
					<div v-if="!doc.combined_rate">
						<span>ค่าวัสดุรวม</span><b>{{ num2(totals.material) }}</b>
					</div>
					<div v-if="!doc.combined_rate">
						<span>ค่าแรงรวม</span><b>{{ num2(totals.labour) }}</b>
					</div>
					<div class="is-grand">
						<span>มูลค่ารวม</span><b>{{ num2(totals.grand) }}</b>
					</div>
				</div>

				<button
					v-if="doc.name && doc.docstatus !== 1 && doc.can?.delete"
					type="button"
					class="ss-btn ss-btn--ghost-danger ss-boq-delete"
					:disabled="busy"
					@click="ask('delete')"
				>
					<Icon name="trash" :size="16" /> {{ doc.docstatus === 0 ? "ลบร่างนี้" : "ลบฉบับนี้" }}
				</button>
			</template>
		</div>

		<!-- ยืนยัน -->
		<Sheet :open="!!confirm" :title="CONFIRM[confirm]?.title" @close="confirm = null">
			<p class="ss-muted">{{ CONFIRM[confirm]?.text }}</p>
			<template #footer>
				<button
					type="button"
					class="ss-btn ss-btn--block ss-btn--lg"
					:class="confirm === 'submit' ? 'ss-btn--primary' : 'ss-btn--ghost-danger'"
					:disabled="busy"
					@click="confirmed"
				>
					{{ CONFIRM[confirm]?.action }}
				</button>
			</template>
		</Sheet>

		<!-- อัปเดตแผนงานจาก BOQ -->
		<Sheet :open="!!sync" title="อัปเดตแผนงานจาก BOQ" @close="sync = null">
			<template v-if="sync">
				<p v-if="sync.reason || sync.in_sync" class="ss-muted">
					{{ sync.reason || "แผนงานตรงกับ BOQ แล้ว" }}
				</p>
				<template v-else>
					<div v-if="sync.blockers.length" class="ss-banner tone-rose">
						<Icon name="alert" :size="20" />
						<div class="ss-banner-text">
							<div v-for="text in sync.blockers" :key="text">{{ text }}</div>
						</div>
					</div>
					<p class="ss-muted">
						เพิ่ม {{ sync.added.length }} · แก้ {{ sync.changed.length }} · ลบ {{ sync.removed.length }} · เลข
						WBS เปลี่ยน {{ sync.moved }} แถว แถวเดิมคงวันที่และงานก่อนหน้าไว้ แถวใหม่เริ่มที่วันเริ่มแผน
						ต้องกำหนดวันเอง
					</p>
					<section v-for="group in sync_groups" :key="group.title" class="ss-boq-sync">
						<h4>{{ group.title }}</h4>
						<div v-for="row in group.rows" :key="row.wbs" class="ss-boq-sync-row">
							<span>{{ row.wbs }} {{ row.item_name }}</span>
							<small v-if="row.fields">{{ row.fields.join(", ") }}</small>
						</div>
					</section>
				</template>
			</template>
			<template #footer>
				<button
					type="button"
					class="ss-btn ss-btn--primary ss-btn--block ss-btn--lg"
					:disabled="busy || !sync?.can_apply"
					@click="apply_sync"
				>
					อัปเดตแผนงาน
				</button>
			</template>
		</Sheet>

		<PlanMenu :menu="menu" @close="menu = null" />

		<!-- รายละเอียดแถว -->
		<Sheet
			:open="!!detail"
			:title="detail?.item_name || 'รายละเอียดแถว'"
			@close="detail = null"
		>
			<div v-if="detail" class="ss-form">
				<label class="ss-checkline">
					<input
						:checked="!!detail.combined_rate"
						type="checkbox"
						@change="toggle_row_combined(detail)"
					/>
					<span>ราคารวมแถวนี้ (รวมค่าแรงเข้าค่าวัสดุ)</span>
				</label>
				<label class="ss-field">
					<span class="ss-field-label">กลุ่มรายการ</span>
					<input v-model="detail.item_group" class="ss-input" />
				</label>
				<div class="ss-field">
					<span class="ss-field-label">คำอธิบาย</span>
					<RichEditor v-model="detail.description" />
				</div>
			</div>
		</Sheet>

		<!-- นำเข้า Excel -->
		<Sheet :open="!!imported" title="นำเข้าจาก Excel" full @close="imported = null">
			<template v-if="imported">
				<Segmented v-model="import_mode" :options="IMPORT_MODES" />
				<p class="ss-muted">
					พบ {{ imported.items.length }} แถว ตรงกับ BOQ Item
					{{ imported.items.filter((x) => x.match === "exact").length }} แถว
					<template v-if="review.length"> ต้องตรวจ {{ review.length }} แถว</template>
				</p>
				<div v-for="item in review" :key="item.row_no" class="ss-boq-review">
					<div class="ss-boq-review-name">
						<b>{{ item.row_no }}. {{ item.row.item_name }}</b>
						<small
							>{{ item.row.quantity }} {{ item.row.uom
							}}<template v-if="item.note"> · {{ item.note }}</template></small
						>
					</div>
					<SelectBox
						v-model="item.item_code"
						variant="tool"
						label="BOQ Item"
						:options="
							item.suggestions.map((s) => ({
								value: s.item_code,
								label: `${s.item_name} (${Math.round(s.score * 100)}%)`,
							}))
						"
						placeholder="ไม่ผูก BOQ Item"
						:disabled="!!item.create"
					/>
					<label class="ss-checkline">
						<input
							v-model="item.create"
							type="checkbox"
							:true-value="1"
							:false-value="0"
							@change="item.create && (item.item_code = null)"
						/>
						<span>สร้างใหม่</span>
					</label>
				</div>
			</template>
			<template #footer>
				<button
					type="button"
					class="ss-btn ss-btn--primary ss-btn--block ss-btn--lg"
					:disabled="busy"
					@click="finish_import"
				>
					นำเข้า {{ imported?.items.length }} รายการ
				</button>
			</template>
		</Sheet>
	</div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, reactive, ref, shallowRef, watch } from "vue";
import Icon from "../../../shared/components/Icon.vue";
import TopBar from "../../../shared/components/TopBar.vue";
import Sheet from "../../../shared/components/Sheet.vue";
import Skeleton from "../../../shared/components/Skeleton.vue";
import Picker from "../../../shared/components/Picker.vue";
import SelectBox from "../../../shared/components/SelectBox.vue";
import DateInput from "../../../shared/components/DateInput.vue";
import RichEditor from "../../../shared/components/RichEditor.vue";
import Segmented from "../../../shared/components/Segmented.vue";
import StatusTabs from "../../../shared/components/StatusTabs.vue";
import RichText from "../../../shared/components/RichText.vue";
import PlanMenu from "../../../site_app/views/pm/planner/PlanMenu.vue";
import BoqItemInput from "./BoqItemInput.vue";
import {
	boot,
	call,
	go,
	post,
	set_leave_guard,
	show_error,
	state,
	today,
	toast,
} from "../../../shared/api.js";

const API = "consbiz.boq_app";
const EXCEL = "consbiz.consbiz.doctype.boq.boq_excel";
const CONFIRM = {
	submit: {
		title: "Submit BOQ",
		text: "หลัง Submit จะแก้รายการและราคาไม่ได้ งานเพิ่ม-ลดต่อจากนี้ต้องทำผ่าน Variation Order",
		action: "Submit",
	},
	cancel: {
		title: "ยกเลิก BOQ",
		text: "ยกเลิกแล้วต้องแก้ไขเป็นฉบับใหม่ก่อนจึงจะใช้ต่อได้",
		action: "ยกเลิก BOQ",
	},
	delete: { title: "ลบ BOQ", text: "ลบแล้วย้อนกลับไม่ได้", action: "ลบ" },
};
const TABS = [{ value: "items", label: "รายการ" }];
const IMPORT_MODES = [
	{ value: "append", label: "ต่อท้ายรายการเดิม" },
	{ value: "replace", label: "แทนที่ทั้งหมด" },
];

const doc = ref(null);
const rows = ref([]);
const uoms = ref([]);
const busy = ref(false);
const dirty = ref(false);
const selected = reactive(new Set());
const confirm = ref(null);
const detail = ref(null);
const menu = ref(null);
const table = ref(null);
const tab = ref("items");
const heading_tops = shallowRef({});
const released = shallowRef(new Set());
const dragging = shallowRef(new Set());
const file_input = ref(null);
const imported = ref(null);
const import_mode = ref("append");
let next_key = 0;
let last_pick = null;
let clipboard = null;
let heading_spans = [];
let scroll_frame = 0;
let table_observer = null;
let drag = null;
const SLIDE_MS = 180;
const SCROLL_EDGE = 48;
const SCROLL_STEP = 14;
let hold_timer = null;
const HOLD_MS = 500;

const props_name = computed(() => state.route.params.name);
// ร่างที่ผู้ใช้ไม่มีสิทธิ์แก้ = ดูอย่างเดียว (BOQ ใหม่ยังไม่มี can)
const draft = computed(() => doc.value?.docstatus === 0 && (!doc.value.name || !!doc.value.can?.write));
const title = computed(() => doc.value?.name || "BOQ ใหม่");
const export_url = computed(
	() => `/api/method/${EXCEL}.export_boq_items?boq=${encodeURIComponent(doc.value.name)}`
);
const template_url = `/api/method/${EXCEL}.export_boq_items`;
const plan_url = computed(() => `/conserp/pm/plan-edit/${encodeURIComponent(doc.value.plan)}`);
const companies = computed(() =>
	(boot.companies || []).map((c) => ({ value: c.name, label: c.name }))
);
const uom_options = computed(() => uoms.value.map((u) => ({ value: u, label: u })));
const header_rows = computed(() => (doc.value?.combined_rate ? 1 : 2));
const column_count = computed(() => (doc.value?.combined_rate ? 6 : 9) + (draft.value ? 3 : 0));
const review = computed(() =>
	(imported.value?.items || []).filter((x) => ["suggest", "none"].includes(x.match))
);

const num2 = (v) =>
	(Number(v) || 0).toLocaleString("en-US", {
		minimumFractionDigits: 2,
		maximumFractionDigits: 2,
	});
const search = (doctype, txt) => call(`${API}.search`, { doctype, txt });

// ---------- แถว ----------
const make_row = (values) => ({
	wbs: "",
	item_code: null,
	item_name: "",
	quantity: null,
	uom: null,
	item_group: null,
	combined_rate: doc.value?.combined_rate ? 1 : 0,
	material_rate: null,
	labour_rate: null,
	description: null,
	...values,
	_key: ++next_key,
	level:
		(values?.wbs || "").split(".").filter((part) => part.trim()).length || values?.level || 1,
});

// ต้องตรงกับ assign_wbs ใน boq.py
function renumber() {
	let counters = [];
	for (const row of rows.value) {
		const level = Math.max(1, Math.min(row.level, counters.length + 1));
		counters = counters.slice(0, level);
		counters[level - 1] = (counters[level - 1] || 0) + 1;
		row.level = level;
		row.wbs = counters.join(".");
	}
}

// ต้องตรงกับ calculate_row ใน boq.py
function row_amounts(row) {
	const quantity = Number(row.quantity) || 0;
	const material = quantity * (Number(row.material_rate) || 0);
	const labour = quantity * (Number(row.labour_rate) || 0);
	let total = material + labour;
	if (doc.value?.round_down_total) total = Math.trunc(Number(total.toFixed(6)));
	return { material, labour, total };
}
const amount = (value) => (value ? num2(value) : "");
const has_children = (i) => rows.value[i + 1]?.level > rows.value[i].level;
const totals = computed(() =>
	rows.value.reduce(
		(sum, row) => {
			const amounts = row_amounts(row);
			sum.material += amounts.material;
			sum.labour += amounts.labour;
			sum.grand += amounts.total;
			return sum;
		},
		{ material: 0, labour: 0, grand: 0 }
	)
);

function merge_combined(row) {
	if (row.combined_rate && Number(row.labour_rate)) {
		row.material_rate = (Number(row.material_rate) || 0) + Number(row.labour_rate);
		row.labour_rate = 0;
	}
}
function toggle_combined(event) {
	doc.value.combined_rate = event.target.checked ? 1 : 0;
	for (const row of rows.value) {
		row.combined_rate = doc.value.combined_rate;
		merge_combined(row);
	}
}
function toggle_row_combined(row) {
	row.combined_rate = row.combined_rate ? 0 : 1;
	merge_combined(row);
}

const subtree_end = (i) => {
	let end = i + 1;
	while (end < rows.value.length && rows.value[end].level > rows.value[i].level) end++;
	return end;
};
const selected_indexes = () => rows.value.flatMap((row, i) => (selected.has(row._key) ? [i] : []));
// แถวที่เลือกรวมแถวย่อย (เลือกทั้งแม่และลูกก็นับครั้งเดียว)
function block_indexes() {
	const picked = new Set();
	for (const i of selected_indexes()) {
		const end = subtree_end(i);
		for (let j = i; j < end; j++) picked.add(j);
	}
	return [...picked].sort((a, b) => a - b);
}

// แถวใหม่: เลือกแถวนั้นไว้ กดเพิ่มต่อจะได้แถวถัดไปในระดับเดียวกัน
function place_new(at, values) {
	const row = make_row(values);
	rows.value.splice(at, 0, row);
	renumber();
	selected.clear();
	selected.add(row._key);
	last_pick = row._key;
	nextTick(() => table.value?.querySelector(`[data-row="${row._key}"] .ss-boq-input`)?.focus());
}
// ปุ่มบนแถบเครื่องมือ: ต่อจากแถวที่เลือก (ไม่เลือก = ท้ายตาราง) ระดับเดียวกับแถวนั้น แถวย่อยใช้เมนูคลิกขวาหรือ Indent
function add_row() {
	const picked = selected_indexes().at(-1) ?? -1;
	const index = picked >= 0 ? picked : rows.value.length - 1;
	const anchor = rows.value[index];
	place_new(anchor ? subtree_end(index) : 0, { level: anchor?.level || 1 });
}
// คลิก = เลือกแถวเดียว, Ctrl/⌘ = เพิ่มหรือเอาออกทีละแถว, Shift = ช่วงติดกันจากแถวล่าสุด
function select_row(index, { adding = false, range = false } = {}) {
	const key = rows.value[index]._key;
	const from = range ? rows.value.findIndex((row) => row._key === last_pick) : -1;
	if (from >= 0) {
		if (!adding) selected.clear();
		const [start, end] = [from, index].sort((a, b) => a - b);
		for (let i = start; i <= end; i++) selected.add(rows.value[i]._key);
		return;
	}
	if (!adding) selected.clear();
	if (adding && selected.has(key)) selected.delete(key);
	else selected.add(key);
	last_pick = key;
}
const has_modifier = (event) => event.ctrlKey || event.metaKey || event.shiftKey;
// กด Ctrl/Shift ไม่ให้โฟกัสช่อง ลากเลือกข้อความ หรือเปิดช่องเลือกในแถว
function press_row(event, index) {
	if (event.button !== 0 || event.target.closest(".c-check, .c-grip")) return;
	if (has_modifier(event)) event.preventDefault();
	select_row(index, { adding: event.ctrlKey || event.metaKey, range: event.shiftKey });
}
function guard_click(event) {
	if (has_modifier(event) && !event.target.closest(".c-check")) {
		event.preventDefault();
		event.stopPropagation();
	}
}
function pick_row(event, index) {
	select_row(index, { adding: true, range: event.shiftKey });
	if (event.shiftKey) event.target.checked = true;
}
function shift_level(step) {
	for (const i of block_indexes()) rows.value[i].level = Math.max(1, rows.value[i].level + step);
	renumber();
}
function remove_rows() {
	const removed = new Set(block_indexes());
	rows.value = rows.value.filter((row, i) => !removed.has(i));
	selected.clear();
	last_pick = null;
	renumber();
}

// ---------- เมนูคลิกขวา ----------
function insert_row(index, where) {
	const anchor = rows.value[index];
	if (where === "above") place_new(index, { level: anchor.level });
	else place_new(subtree_end(index), { level: anchor.level + (where === "sub" ? 1 : 0) });
}
function copy_rows(cut) {
	clipboard = { cut, rows: block_indexes().map((i) => ({ ...rows.value[i] })) };
	if (cut) remove_rows();
}
// วางใต้แถวที่คลิก (ต่อจากแถวย่อยของแถวนั้น) ระดับบนสุดของที่คัดลอกเท่ากับแถวที่คลิก
// ตัดแล้ววางครั้งแรกคงรหัสแถวเดิม แผนงานอ้าง BOQ ด้วยรหัสนี้ ส่วนคัดลอกเป็นแถวใหม่เสมอ
function paste_rows(index) {
	const target = rows.value[index];
	const at = target ? subtree_end(index) : rows.value.length;
	const shift = (target?.level || 1) - Math.min(...clipboard.rows.map((row) => row.level));
	const pasted = clipboard.rows.map(({ _key, name, ...row }) =>
		make_row({ ...row, ...(clipboard.cut ? { name } : {}), wbs: "", level: row.level + shift })
	);
	clipboard.cut = false;
	rows.value.splice(at, 0, ...pasted);
	renumber();
	selected.clear();
	pasted.forEach((row) => selected.add(row._key));
	last_pick = pasted[0]._key;
}
function open_menu(event, index) {
	event.preventDefault();
	const paste = {
		label: "วาง",
		icon: "clipboard",
		hint: clipboard ? `${clipboard.rows.length} แถว` : "",
		disabled: !clipboard,
		action: () => paste_rows(index),
	};
	let items = [paste, { label: "เพิ่มรายการ", icon: "plus", action: add_row }];
	if (index >= 0) {
		if (!selected.has(rows.value[index]._key)) select_row(index);
		const count = block_indexes().length;
		const named = (label) => (count > 1 ? `${label} ${count} แถว` : label);
		items = [
			{ label: named("คัดลอก"), icon: "copy", action: () => copy_rows(false) },
			{ label: named("ตัด"), icon: "scissors", action: () => copy_rows(true) },
			paste,
			{ sep: true },
			{ label: "แทรกแถวด้านบน", icon: "chevron-up", action: () => insert_row(index, "above") },
			{ label: "แทรกแถวด้านล่าง", icon: "chevron-down", action: () => insert_row(index, "below") },
			{ label: "เพิ่มรายการย่อย", icon: "indent", action: () => insert_row(index, "sub") },
			{ sep: true },
			{ label: named("ลบ"), icon: "trash", danger: true, action: remove_rows },
		];
	}
	menu.value = { x: event.clientX, y: event.clientY, items };
}
// จอสัมผัสไม่มีคลิกขวา (iPad ไม่ส่ง contextmenu): กดค้าง = เปิดเมนู
function hold_start(event, index) {
	if (event.target.closest(".c-grip")) return;
	const { clientX, clientY } = event.touches[0];
	hold_end();
	hold_timer = setTimeout(
		() => open_menu({ preventDefault() {}, clientX, clientY }, index),
		HOLD_MS
	);
}
function hold_end() {
	clearTimeout(hold_timer);
}

// ---------- ลากย้ายแถว ----------
// แถวย้ายจริงระหว่างลาก (เลข WBS เปลี่ยนตาม) แถวอื่นเลื่อนหลบด้วย animation จึงเห็นตำแหน่งที่จะวางทันที Esc = ยกเลิก
// offsetTop ไม่นับ sticky/transform จึงได้ตำแหน่งจริงของแถวแม้กำลัง animate
function slide_rows(change) {
	const body = table.value?.tBodies[0];
	if (!body || window.matchMedia("(prefers-reduced-motion: reduce)").matches) return change();
	const before = new Map(rows.value.map((row, i) => [row._key, body.rows[i].offsetTop]));
	change();
	nextTick(() =>
		rows.value.forEach((row, i) => {
			const tr = body.rows[i];
			const delta = before.get(row._key) - tr.offsetTop;
			const pinned =
				Math.abs(tr.cells[0].getBoundingClientRect().top - tr.getBoundingClientRect().top) > 1;
			if (!delta || pinned) return;
			tr.animate([{ transform: `translateY(${delta}px)` }, { transform: "none" }], {
				duration: SLIDE_MS,
				easing: "cubic-bezier(0.22, 1, 0.36, 1)",
			});
		})
	);
}
// ระดับที่วางได้: ไม่ทำให้แถวถัดไปกลายเป็นลูกของแถวที่ลาก และลึกกว่าแถวก่อนหน้าได้ไม่เกิน 1 ระดับ คงระดับเดิมถ้าทำได้
function drop_level(base, previous, next) {
	const lowest = next ? next.level : 1;
	const highest = previous ? previous.level + 1 : 1;
	return Math.min(highest, Math.max(lowest, base));
}
function drag_to(client_y) {
	const body = table.value.tBodies[0];
	const y = client_y - table.value.getBoundingClientRect().top;
	const marks = rows.value.map((row, i) => ({
		row,
		mid: body.rows[i].offsetTop + body.rows[i].offsetHeight / 2,
		top: body.rows[i].offsetTop,
		bottom: body.rows[i].offsetTop + body.rows[i].offsetHeight,
		moving: dragging.value.has(row._key),
	}));
	const moving = marks.filter((mark) => mark.moving);
	const rest = marks.filter((mark) => !mark.moving);
	// อยู่ในช่วงแถวที่ลากอยู่แล้ว ไม่ขยับ กันแถวสลับไปมาเมื่อแถวที่ลากสูงกว่าแถวข้างเคียง
	if (y >= moving[0].top && y <= moving.at(-1).bottom) return;
	const at =
		y < moving[0].top
			? rest.findIndex((mark) => mark.mid > y)
			: rest.findLastIndex((mark) => mark.mid < y) + 1;
	const first = marks.indexOf(moving[0]);
	const together = marks.indexOf(moving.at(-1)) - first + 1 === moving.length;
	if (at < 0 || (together && at === first)) return;
	const others = rest.map((mark) => mark.row);
	const block = moving.map((mark) => mark.row);
	const base = drag.levels.get(block[0]._key);
	const shift = drop_level(base, others[at - 1], others[at]) - base;
	slide_rows(() => {
		for (const row of block) row.level = Math.max(1, drag.levels.get(row._key) + shift);
		rows.value = [...others.slice(0, at), ...block, ...others.slice(at)];
		renumber();
	});
}
// เลื่อนจอเองเมื่อลากถึงขอบ BOQ ยาวเกินจอเป็นปกติ
function drag_scroll() {
	if (!drag) return;
	const el = table.value;
	const box = el.parentElement;
	const inner = getComputedStyle(box).overflowY === "auto";
	const top = el.tHead.rows[0].cells[0].getBoundingClientRect().bottom;
	const bottom = inner ? box.getBoundingClientRect().bottom : window.innerHeight;
	const step =
		drag.y < top + SCROLL_EDGE ? -SCROLL_STEP : drag.y > bottom - SCROLL_EDGE ? SCROLL_STEP : 0;
	if (step) {
		(inner ? box : window).scrollBy({ top: step, behavior: "instant" });
		drag_to(drag.y);
	}
	drag.frame = requestAnimationFrame(drag_scroll);
}
function on_drag_move(event) {
	drag.y = event.clientY;
	drag_to(event.clientY);
}
const on_drag_up = () => end_drag(false);
const on_drag_cancel = () => end_drag(true);
function on_drag_key(event) {
	if (event.key === "Escape") end_drag(true);
}
function drag_listen(on) {
	const method = on ? "addEventListener" : "removeEventListener";
	window[method]("pointermove", on_drag_move);
	window[method]("pointerup", on_drag_up);
	window[method]("pointercancel", on_drag_cancel);
	window[method]("keydown", on_drag_key);
	document.documentElement.classList.toggle("ss-boq-grabbing", on);
}
// ลากแถวที่เลือกทั้งหมดรวมแถวย่อย ถ้าจับแถวที่ไม่ได้เลือก = ลากแถวนั้นกับแถวย่อย
function start_drag(event, index) {
	if (event.button !== 0 || drag) return;
	event.preventDefault();
	if (!selected.has(rows.value[index]._key)) select_row(index);
	const block = block_indexes().map((i) => rows.value[i]);
	drag = {
		y: event.clientY,
		frame: 0,
		levels: new Map(block.map((row) => [row._key, row.level])),
		before: rows.value.map((row) => ({ row, level: row.level })),
	};
	dragging.value = new Set(block.map((row) => row._key));
	drag_listen(true);
	drag.frame = requestAnimationFrame(drag_scroll);
}
function end_drag(cancelled) {
	if (!drag) return;
	const { before, frame } = drag;
	drag = null;
	cancelAnimationFrame(frame);
	drag_listen(false);
	dragging.value = new Set();
	if (cancelled)
		slide_rows(() => {
			rows.value = before.map(({ row, level }) => {
				row.level = level;
				return row;
			});
			renumber();
		});
}

// ---------- BOQ Item ----------
const search_items = (txt) => search("BOQ Item", txt);
// เหมือนฟอร์มระบบเต็ม: เติมชื่อ หน่วย กลุ่ม ราคากรอกเอง คำอธิบายตาม Item (Item ไม่มี = ไม่ค้างของ Item เดิม)
function apply_item(row, option) {
	Object.assign(row, {
		item_code: option.value,
		item_name: option.label,
		uom: option.uom,
		item_group: option.item_group,
		description: option.description || null,
	});
}
// พิมพ์เองแล้วไม่ใช่ Item เดิม ประวัติราคาจะได้ไม่อ้าง Item ที่ชื่อไม่ตรง
function type_name(row, text) {
	row.item_name = text;
	row.item_code = null;
}

// ---------- หัวข้อตามลงมา ----------
// แถวที่มีแถวย่อยติดใต้หัวตาราง ซ้อนเป็นชั้นตามระดับ (ตัวเลขใน heading_tops = ความสูงรวมของหัวข้อแม่)
const is_sticky = (row) =>
	row._key in heading_tops.value &&
	!released.value.has(row._key) &&
	!dragging.value.has(row._key);
function update_released() {
	const el = table.value;
	if (!el) return;
	const table_top = el.getBoundingClientRect().top;
	const head_bottom = el.tHead.rows[0].cells[0].getBoundingClientRect().bottom;
	const next = new Set(
		heading_spans
			.filter((span) => table_top + span.end <= head_bottom + span.stop)
			.map((span) => span.key)
	);
	const same = next.size === released.value.size && [...next].every((key) => released.value.has(key));
	if (!same) released.value = next;
}
// sticky ของเซลล์ติดได้ตลอดทั้งตาราง จึงต้องปล่อยเองเมื่อแถวย่อยของหัวข้อนั้นเลื่อนพ้นไปแล้ว
function on_table_scroll() {
	if (scroll_frame) return;
	scroll_frame = requestAnimationFrame(() => {
		scroll_frame = 0;
		update_released();
	});
}
function measure_headings() {
	const body = table.value?.tBodies[0];
	if (!body) return;
	const tops = {};
	const spans = [];
	const heights = [];
	rows.value.forEach((row, i) => {
		const tr = body.rows[i];
		if (!tr || !has_children(i)) return;
		heights.length = row.level - 1;
		const top = heights.reduce((sum, height) => sum + (height || 0), 0);
		heights[row.level - 1] = tr.offsetHeight;
		const last = body.rows[subtree_end(i) - 1];
		tops[row._key] = top;
		spans.push({ key: row._key, stop: top + tr.offsetHeight, end: last.offsetTop + last.offsetHeight });
	});
	heading_tops.value = tops;
	heading_spans = spans;
	update_released();
}

// ---------- โหลด / บันทึก ----------
function use_doc(data) {
	doc.value = data;
	// ค่า 0 แสดงเป็นช่องว่าง แถวหมวดจะได้ไม่มีเลข 0 เต็มตาราง (บันทึกแล้วเป็น 0 เหมือนเดิม)
	const blank = (value) => (Number(value) ? value : null);
	rows.value = (data.rows || []).map((row) =>
		make_row({
			...row,
			quantity: blank(row.quantity),
			material_rate: blank(row.material_rate),
			labour_rate: blank(row.labour_rate),
		})
	);
	selected.clear();
	last_pick = null;
	nextTick(() => (dirty.value = false));
}
async function load() {
	const name = props_name.value;
	try {
		const [setup, data] = await Promise.all([
			call(`${API}.get_setup`),
			name && name !== "new" ? call(`${API}.get_boq`, { name }) : null,
		]);
		uoms.value = setup.uoms;
		use_doc(
			data || {
				docstatus: 0,
				date: today(),
				company: state.company || boot.default_company || null,
				combined_rate: 0,
				round_down_total: 0,
				rows: [],
			}
		);
	} catch (error) {
		show_error(error);
	}
}
const payload = () => {
	const { rows: _rows, plan, can_create_plan, can, ...header } = doc.value;
	return {
		...header,
		rows: rows.value.map(({ _key, level, ...row }) => row),
	};
};
async function save() {
	busy.value = true;
	try {
		const data = await post(`${API}.save_boq`, { data: payload() });
		use_doc(data);
		toast("บันทึกแล้ว", "success");
		if (props_name.value === "new") go("boq-form", { name: data.name }, { replace: true });
		return true;
	} catch (error) {
		show_error(error);
		return false;
	} finally {
		busy.value = false;
	}
}
const ask = (action) => (confirm.value = action);
async function run(method) {
	busy.value = true;
	try {
		const data = await post(`${API}.${method}`, { name: doc.value.name });
		confirm.value = null;
		use_doc(data);
		if (data.name !== props_name.value) go("boq-form", { name: data.name }, { replace: true });
	} catch (error) {
		show_error(error);
	} finally {
		busy.value = false;
	}
}
async function confirmed() {
	const action = confirm.value;
	if (action === "submit") {
		if (dirty.value && !(await save())) return;
		await run("submit_boq");
	} else if (action === "cancel") await run("cancel_boq");
	else {
		busy.value = true;
		try {
			await post(`${API}.delete_boq`, { name: doc.value.name });
			dirty.value = false;
			confirm.value = null;
			go("boq");
		} catch (error) {
			show_error(error);
		} finally {
			busy.value = false;
		}
	}
}
const SYNC = "consbiz.consbiz.doctype.construction_management.boq_sync";
const sync = ref(null);
const sync_groups = computed(() =>
	[
		{ title: "รายการที่จะลบ", rows: sync.value?.removed || [] },
		{ title: "รายการใหม่", rows: sync.value?.added || [] },
		{ title: "รายการที่แก้", rows: sync.value?.changed || [] },
	].filter((group) => group.rows.length)
);
async function open_sync() {
	if (dirty.value && !(await save())) return;
	busy.value = true;
	try {
		sync.value = await call(`${SYNC}.preview_boq_sync`, { boq: doc.value.name });
	} catch (error) {
		show_error(error);
	} finally {
		busy.value = false;
	}
}
async function apply_sync() {
	busy.value = true;
	try {
		await post(`${SYNC}.apply_boq_sync`, { boq: doc.value.name, modified: sync.value.modified });
		sync.value = null;
		toast("อัปเดตแผนงานแล้ว", "success");
	} catch (error) {
		show_error(error);
	} finally {
		busy.value = false;
	}
}
async function create_plan() {
	busy.value = true;
	try {
		await post(`${API}.create_plan`, { name: doc.value.name });
		use_doc(await call(`${API}.get_boq`, { name: doc.value.name }));
		toast("สร้างแผนงานแล้ว", "success");
	} catch (error) {
		show_error(error);
	} finally {
		busy.value = false;
	}
}

// ---------- Excel ----------
function read_file(event) {
	const file = event.target.files[0];
	event.target.value = "";
	if (!file) return;
	const reader = new FileReader();
	reader.onload = async () => {
		busy.value = true;
		try {
			const result = await post(`${EXCEL}.import_boq_items`, {
				filename: file.name,
				content: reader.result.split(",")[1],
			});
			result.items.forEach((item) => (item.create = 0));
			import_mode.value = rows.value.length ? "append" : "replace";
			imported.value = result;
		} catch (error) {
			show_error(error);
		} finally {
			busy.value = false;
		}
	};
	reader.readAsDataURL(file);
}
async function finish_import() {
	busy.value = true;
	try {
		const { items, info, warnings } = imported.value;
		const created = await post(`${EXCEL}.apply_boq_matches`, {
			items: items.map(({ row, missing, item_code, create }) => ({
				row,
				missing,
				item_code,
				create,
			})),
		});
		const replace = import_mode.value === "replace";
		for (const [field, value] of Object.entries(info || {})) {
			if (field === "round_down_total" && !replace && rows.value.length) continue;
			if (replace || !doc.value[field]) doc.value[field] = value;
		}
		const new_rows = created.map((row) => {
			const made = make_row({
				...row,
				combined_rate: doc.value.combined_rate ? 1 : row.combined_rate,
			});
			merge_combined(made);
			return made;
		});
		rows.value = replace ? new_rows : [...rows.value, ...new_rows];
		renumber();
		imported.value = null;
		toast(`นำเข้า ${created.length} รายการ`, "success");
		if (warnings?.length) toast(warnings.join(" / "), "error");
	} catch (error) {
		show_error(error);
	} finally {
		busy.value = false;
	}
}

watch([doc, rows], () => (dirty.value = true), { deep: true });
set_leave_guard(
	async () => !dirty.value || window.confirm("ยังไม่ได้บันทึก ออกจากหน้านี้หรือไม่")
);
// จัดลำดับ/ระดับเปลี่ยนโดยความสูงตารางไม่เปลี่ยน ResizeObserver จึงไม่พอ
watch(
	() => rows.value.map((row) => `${row._key}:${row.level}`).join(),
	() => nextTick(measure_headings)
);
watch(table, (el) => {
	table_observer?.disconnect();
	if (!el) return;
	table_observer = new ResizeObserver(measure_headings);
	table_observer.observe(el);
});
window.addEventListener("scroll", on_table_scroll, { capture: true, passive: true });
onBeforeUnmount(() => {
	set_leave_guard(null);
	table_observer?.disconnect();
	window.removeEventListener("scroll", on_table_scroll, { capture: true });
	cancelAnimationFrame(scroll_frame);
	hold_end();
	end_drag(true);
});
load();
</script>
