<!-- แผนตัดเหล็ก 1 แผน (หมวดควบคุมงาน) แท็บ รายการตัด / ผลการตัด / ตั้งค่า
     เพิ่มเหล็ก = sheet เลือกรูปทรงจากภาพ กรอกด้านที่รูปนั้นใช้ เห็นความยาวตัดทันที (bar_cut_app.preview)
     "คำนวณและบันทึก" = บันทึก Bar Cut Plan (validate คำนวณความยาวตัด + จัดตัด) ผลการตัดมาจาก server เสมอ
     ลอกหน้าตาฟอร์มจากคอนกรีต (ConcreteForm.vue) API consbiz/bar_cut_app.py -->
<template>
	<div class="ss-has-bar">
		<TopBar
			:title="doc?.name ? doc.title || doc.name : 'แผนตัดเหล็กใหม่'"
			:subtitle="doc?.name || state.project?.project_name"
			back_to="rebar"
		/>

		<div class="ss-content">
			<Skeleton v-if="!doc || !setup" :rows="4" />
			<template v-else>
				<div v-if="wide" class="ss-list-head">
					<StatusTabs v-model="tab" :options="tabs" />
					<div class="ss-list-tools">
						<span v-if="dirty && doc.patterns.length" class="ss-tag tone-amber"
							>แก้แล้ว ยังไม่คำนวณใหม่</span
						>
					</div>
				</div>
				<Segmented v-else v-model="tab" :options="tabs" />

				<!-- ---------------- รายการตัด ---------------- -->
				<template v-if="tab === 'items'">
					<div class="ss-form">
						<div class="ss-form-row">
							<label class="ss-field">
								<span class="ss-field-label">ชื่อแผน<em>*</em></span>
								<input
									v-model="doc.title"
									class="ss-input"
									placeholder="เช่น คาน B1 ชั้น 2"
									:disabled="readonly"
								/>
							</label>
							<label class="ss-field">
								<span class="ss-field-label">วันที่</span>
								<DateInput
									v-model="doc.date"
									label="วันที่"
									:disabled="readonly"
								/>
							</label>
						</div>
					</div>

					<h2 class="ss-section-title">
						เหล็กที่ต้องตัด ({{ doc.items.length }})
						<span class="ss-section-total">{{ num(total_pieces) }} ชิ้น</span>
					</h2>
					<Empty
						v-if="!doc.items.length"
						icon="list-ordered"
						title="ยังไม่มีเหล็กที่ต้องตัด"
						text="กด “เพิ่มเหล็ก” เลือกรูปทรงแล้วกรอกขนาด"
					/>
					<div v-else class="ss-list">
						<button
							v-for="(r, i) in doc.items"
							:key="r._key"
							type="button"
							class="ss-card ss-card--row"
							:style="{ '--i': i }"
							@click="edit_item(r)"
						>
							<!-- eslint-disable-next-line vue/no-v-html -->
							<span class="ss-shape ss-rebar-thumb" v-html="thumb(r)"></span>
							<span class="ss-card-main">
								<span class="ss-card-title"
									>{{ r.mark || `#${i + 1}` }} · {{ r.rebar_type }}</span
								>
								<span class="ss-card-meta">
									{{ shape_name(r.shape) }} · ยาวตัด
									{{ r.cut_length ? num(r.cut_length) : "—" }} มม.
									<template v-if="r.weight">
										· {{ meters(r.weight, 1) }} กก.</template
									>
								</span>
							</span>
							<span class="ss-qty"
								><b>{{ num(r.qty) }}</b
								><small>ชิ้น</small></span
							>
						</button>
					</div>
					<button v-if="!readonly" type="button" class="ss-add-row" @click="new_item">
						<Icon name="plus" :size="20" :stroke="2.6" /> เพิ่มเหล็ก
					</button>
				</template>

				<!-- ---------------- ผลการตัด ---------------- -->
				<template v-else-if="tab === 'result'">
					<Empty
						v-if="!doc.patterns.length"
						icon="list-ordered"
						title="ยังไม่ได้คำนวณ"
						text="เพิ่มเหล็กที่ต้องตัดแล้วกด “คำนวณและบันทึก”"
					/>
					<template v-else>
						<div v-if="dirty" class="ss-banner tone-amber">
							<Icon name="alert" :size="22" />
							<div class="ss-banner-text">
								ผลนี้มาจากข้อมูลที่บันทึกล่าสุด กด “คำนวณและบันทึก” เพื่อคิดใหม่
							</div>
						</div>
						<div class="ss-facts ss-facts--grid">
							<div class="ss-fact">
								<span>เหล็กที่ใช้</span
								><b
									>{{ meters(doc.total_stock_length) }} ม. ({{
										meters(doc.total_weight)
									}}
									กก.)</b
								>
							</div>
							<div class="ss-fact">
								<span>ความยาวตัด</span
								><b>{{ meters(doc.total_required_length) }} ม.</b>
							</div>
							<div class="ss-fact">
								<span
									><i class="ss-cut-swatch is-reusable"></i>เศษเก็บ (ยาวตั้งแต่
									{{ doc.min_reusable }} ม.)</span
								><b>{{ meters(doc.reusable_offcut) }} ม.</b>
							</div>
							<div class="ss-fact">
								<span><i class="ss-cut-swatch is-scrap"></i>เศษทิ้ง</span
								><b
									>{{ meters(doc.scrap) }} ม. ({{
										meters(doc.loss_percent, 1)
									}}%)</b
								>
							</div>
						</div>
						<section v-for="g in groups" :key="g.rebar_type" class="ss-card">
							<h2 class="ss-section-title">
								{{ g.rebar_type }}
								<span class="ss-section-total">{{ g.used }}</span>
							</h2>
							<div v-for="(p, i) in g.patterns" :key="i" class="ss-cut-row">
								<span class="ss-cut-label"
									>{{ meters(p.stock_length, 0) }} ม. × <b>{{ p.bars }}</b></span
								>
								<div class="ss-cut-bar">
									<template v-for="(piece, j) in p.pieces" :key="j">
										<div
											v-for="k in piece.count"
											:key="k"
											class="ss-cut-piece"
											:style="{ width: `${width(piece.length / 1000, p)}%` }"
											:title="`${meters(
												piece.length / 1000,
												3
											)} ม. (${piece.marks.join(', ')})`"
										>
											{{
												width(piece.length / 1000, p) > 9
													? meters(piece.length / 1000)
													: ""
											}}
										</div>
									</template>
									<div
										v-if="p.offcut > 0"
										class="ss-cut-offcut"
										:class="
											p.offcut_type === 'Reusable'
												? 'is-reusable'
												: 'is-scrap'
										"
										:style="{ width: `${width(p.offcut, p)}%` }"
										:title="`เศษ ${meters(p.offcut, 3)} ม.`"
									>
										{{ width(p.offcut, p) > 9 ? meters(p.offcut) : "" }}
									</div>
								</div>
							</div>
							<p class="ss-muted">
								<template v-for="(p, i) in g.patterns" :key="i">
									{{ meters(p.stock_length, 0) }} ม. × {{ p.bars }} เส้น:
									{{
										p.pieces
											.map(
												(x) =>
													`${meters(x.length / 1000)} ม. x ${
														x.count
													} (${x.marks.join(", ")})`
											)
											.join(" + ")
									}}<br />
								</template>
							</p>
						</section>
					</template>
				</template>

				<!-- ---------------- ตั้งค่า ---------------- -->
				<template v-else>
					<h2 class="ss-section-title">เหล็กที่มี</h2>
					<p class="ss-muted">
						ไม่ระบุ = ใช้ความยาวมาตรฐานของประเภทเหล็กไม่จำกัดจำนวน
						ระบุแล้วใช้เฉพาะที่ระบุ (เช่น เศษเก็บจากงานก่อน)
					</p>
					<div class="ss-list">
						<div v-for="s in doc.stock" :key="s._key" class="ss-card ss-form">
							<div class="ss-form-row">
								<Picker
									v-model="s.rebar_type"
									label="ประเภทเหล็ก"
									:options="rebar_options"
									:class="{ 'is-readonly': readonly }"
									required
								/>
								<label class="ss-field">
									<span class="ss-field-label">ยาว (ม.)<em>*</em></span>
									<input
										v-model.number="s.length"
										class="ss-input"
										type="number"
										inputmode="decimal"
										:disabled="readonly"
									/>
								</label>
								<label class="ss-field">
									<span class="ss-field-label">จำนวน (ว่าง = ไม่จำกัด)</span>
									<input
										v-model.number="s.qty"
										class="ss-input"
										type="number"
										inputmode="numeric"
										:disabled="readonly"
									/>
								</label>
							</div>
							<button
								v-if="!readonly"
								type="button"
								class="ss-btn ss-btn--ghost-danger"
								@click="doc.stock = doc.stock.filter((x) => x !== s)"
							>
								<Icon name="trash" :size="16" /> ลบ
							</button>
						</div>
					</div>
					<button v-if="!readonly" type="button" class="ss-add-row" @click="add_stock">
						<Icon name="plus" :size="20" :stroke="2.6" /> เพิ่มเหล็กที่มี
					</button>

					<h2 class="ss-section-title">การตัด</h2>
					<div class="ss-form">
						<div class="ss-form-row">
							<label class="ss-field">
								<span class="ss-field-label">ความหนาใบตัด (มม.)</span>
								<input
									v-model.number="doc.kerf"
									class="ss-input"
									type="number"
									inputmode="decimal"
									:disabled="readonly"
								/>
							</label>
							<label class="ss-field">
								<span class="ss-field-label"
									>เศษยาวตั้งแต่ (ม.) นับเป็นเศษเก็บ</span
								>
								<input
									v-model.number="doc.min_reusable"
									class="ss-input"
									type="number"
									inputmode="decimal"
									:disabled="readonly"
								/>
							</label>
							<label class="ss-field">
								<span class="ss-field-label">ปัดความยาวตัดขึ้น (มม.)</span>
								<input
									v-model.number="doc.round_up"
									class="ss-input"
									type="number"
									inputmode="numeric"
									:disabled="readonly"
								/>
							</label>
						</div>
					</div>

					<h2 class="ss-section-title">ความยาวตัด (เท่าของขนาดเหล็ก d)</h2>
					<div class="ss-form">
						<label
							class="ss-toggle"
							:class="{ 'is-on': doc.use_bend_deduction, 'is-readonly': readonly }"
						>
							<input
								v-model="doc.use_bend_deduction"
								type="checkbox"
								:true-value="1"
								:false-value="0"
								:disabled="readonly"
							/>
							<span class="ss-toggle-track"><span></span></span>
							<span>
								<b>หักระยะที่จุดดัด</b>
								<small>ความยาวตัด = ผลรวมด้าน - ระยะหักที่จุดดัด + ระยะขอ</small>
							</span>
						</label>
						<div v-if="doc.use_bend_deduction" class="ss-form-row">
							<label v-for="f in BENDS" :key="f.field" class="ss-field">
								<span class="ss-field-label">{{ f.label }}</span>
								<input
									v-model.number="doc[f.field]"
									class="ss-input"
									type="number"
									inputmode="decimal"
									:disabled="readonly"
								/>
							</label>
						</div>
						<div class="ss-form-row">
							<label v-for="f in HOOKS" :key="f.field" class="ss-field">
								<span class="ss-field-label">{{ f.label }}</span>
								<input
									v-model.number="doc[f.field]"
									class="ss-input"
									type="number"
									inputmode="decimal"
									:disabled="readonly"
								/>
							</label>
						</div>
						<p class="ss-muted">
							แก้ค่าแล้วกด “คำนวณและบันทึก” ความยาวตัดทุกแถวคิดใหม่
						</p>
					</div>
				</template>
			</template>
		</div>

		<Teleport to="#ss-layer">
			<Transition name="ss-bar">
				<div v-if="doc && setup" class="ss-bottom-bar">
					<button
						v-if="view.can_delete"
						type="button"
						class="ss-btn ss-btn--ghost-danger ss-btn--lg"
						@click="deleting = true"
					>
						<Icon name="trash" :size="17" /> ลบ
					</button>
					<button
						v-if="view.pdf_url"
						type="button"
						class="ss-btn ss-btn--ghost ss-btn--lg"
						:disabled="dirty"
						:title="dirty ? 'คำนวณและบันทึกก่อน' : ''"
						@click="pdf = true"
					>
						<Icon name="printer" :size="17" /> PDF
					</button>
					<button
						v-if="!readonly"
						type="button"
						class="ss-btn ss-btn--primary ss-btn--lg ss-grow"
						:disabled="
							saving || !doc.title || !doc.items.length || (!dirty && !!doc.name)
						"
						@click="save"
					>
						<span v-if="saving" class="ss-spinner"></span>
						<template v-else>คำนวณและบันทึก</template>
					</button>
				</div>
			</Transition>
		</Teleport>

		<!-- เพิ่ม / แก้เหล็ก 1 แถว -->
		<Sheet
			:open="!!item"
			:title="item?._new ? 'เพิ่มเหล็ก' : 'แก้เหล็ก'"
			full
			@close="item = null"
		>
			<div v-if="item" class="ss-form">
				<!-- ขั้นที่ 1: เลือกรูปทรง (รูปทรงมีหลายสิบแบบ จึงซ่อนเมื่อเลือกแล้ว) -->
				<div v-if="!readonly && choosing" class="ss-shape-grid">
					<button
						v-for="s in setup.shapes"
						:key="s.name"
						type="button"
						class="ss-shape-card"
						:class="{ 'is-active': item.shape === s.name }"
						@click="pick_shape(s)"
					>
						<!-- eslint-disable-next-line vue/no-v-html -->
						<span class="ss-shape" v-html="shape_svg(s.svg)"></span>
						<span>{{ s.name }} · {{ s.shape_name }}</span>
					</button>
				</div>
				<template v-if="shape && !choosing">
					<button
						v-if="!readonly"
						type="button"
						class="ss-btn ss-btn--soft"
						@click="choosing = true"
					>
						<Icon name="swap" :size="16" /> เปลี่ยนรูปทรง ({{ shape.name }})
					</button>
					<!-- eslint-disable-next-line vue/no-v-html -->
					<div
						class="ss-shape ss-shape-preview"
						v-html="shape_svg(shape.svg, item)"
					></div>
					<div class="ss-facts">
						<div class="ss-fact">
							<span>{{ shape.shape_name }}</span>
							<b v-if="cut">
								ยาวตัด {{ num(cut.cut_length) }} มม. · รวม
								{{ meters((cut.cut_length * (item.qty || 0)) / 1000) }} ม. ·
								{{
									meters(
										((cut.cut_length * (item.qty || 0)) / 1000) *
											cut.unit_weight
									)
								}}
								กก.
							</b>
							<b v-else
								>กรอกประเภทเหล็กและด้าน
								{{ shape.dims.join(", ").toUpperCase() }}</b
							>
						</div>
					</div>
					<div class="ss-form-row">
						<Picker
							v-model="item.rebar_type"
							label="ประเภทเหล็ก"
							:options="rebar_options"
							:class="{ 'is-readonly': readonly }"
							required
							@select="update_cut"
						/>
						<label class="ss-field">
							<span class="ss-field-label">เลขเหล็ก / ตำแหน่ง</span>
							<input
								v-model="item.mark"
								class="ss-input"
								placeholder="เช่น B1-1"
								:disabled="readonly"
							/>
						</label>
					</div>
					<div class="ss-form-row">
						<label v-for="d in shape.dims" :key="d" class="ss-field">
							<span class="ss-field-label"
								>{{ d.toUpperCase() }} ({{ DIM_UNITS[d] || "มม." }})<em
									>*</em
								></span
							>
							<input
								v-model.number="item[d]"
								class="ss-input"
								type="number"
								inputmode="decimal"
								:disabled="readonly"
								@input="update_cut"
							/>
						</label>
					</div>
					<div class="ss-field">
						<span class="ss-field-label">จำนวน (ชิ้น)<em>*</em></span>
						<Stepper v-model="item.qty" :min="1" class="ss-stepper--xl" />
					</div>
				</template>
			</div>
			<template v-if="!readonly" #footer>
				<div class="ss-sheet-actions">
					<button
						v-if="!item?._new"
						type="button"
						class="ss-btn ss-btn--ghost-danger"
						@click="remove_item"
					>
						<Icon name="trash" :size="18" />
					</button>
					<button
						v-if="item?._new"
						type="button"
						class="ss-btn ss-btn--ghost ss-btn--lg"
						:disabled="!item_ready"
						@click="save_item(true)"
					>
						เพิ่มแล้วทำต่อ
					</button>
					<button
						type="button"
						class="ss-btn ss-btn--primary ss-btn--block ss-btn--lg"
						:disabled="!item_ready"
						@click="save_item(false)"
					>
						{{ item?._new ? "เพิ่ม" : "ตกลง" }}
					</button>
				</div>
			</template>
		</Sheet>

		<DeleteSheet
			:open="deleting"
			label="แผนตัดเหล็ก"
			:name="doc?.name"
			:method="`${API}.delete_plan`"
			:args="{ name: doc?.name }"
			@close="deleting = false"
			@deleted="back('rebar')"
		/>
		<PdfViewer
			:open="pdf"
			:url="view.pdf_url"
			:name="doc?.name"
			title="แผนตัดเหล็ก"
			@close="pdf = false"
		/>
	</div>
</template>

<script setup>
import { computed, ref, watch } from "vue";
import DateInput from "../../../shared/components/DateInput.vue";
import DeleteSheet from "../../../shared/components/DeleteSheet.vue";
import Empty from "../../../shared/components/Empty.vue";
import Icon from "../../../shared/components/Icon.vue";
import PdfViewer from "../../../shared/components/PdfViewer.vue";
import Picker from "../../../shared/components/Picker.vue";
import Segmented from "../../../shared/components/Segmented.vue";
import Sheet from "../../../shared/components/Sheet.vue";
import Skeleton from "../../../shared/components/Skeleton.vue";
import StatusTabs from "../../../shared/components/StatusTabs.vue";
import Stepper from "../../../shared/components/Stepper.vue";
import TopBar from "../../../shared/components/TopBar.vue";
import { use_wide } from "../../../shared/table.js";
import {
	back,
	call,
	celebrate,
	go,
	num,
	post,
	replace_params,
	show_error,
	state,
	today,
} from "../../../shared/api.js";
import { API, DIM_UNITS, DIMS, SETTINGS, meters, shape_svg } from "./rebar.js";

const BENDS = [45, 90, 135, 180].map((a) => ({ field: `bend_${a}`, label: `หักที่ดัด ${a}°` }));
const HOOKS = [90, 135, 180].map((a) => ({ field: `hook_${a}`, label: `ขอ ${a}°` }));
const INPUT = [
	"name",
	"modified",
	"project",
	"title",
	"date",
	"kerf",
	"min_reusable",
	...SETTINGS,
];
const ITEM = ["mark", "shape", "rebar_type", ...DIMS, "qty", "remarks"];
const STOCK = ["rebar_type", "length", "qty", "remarks"];

const params = state.route.params;
const wide = use_wide();
let key = 0;
const setup = ref(null);
const view = ref({});
const doc = ref(null);
const saved = ref("");
const saving = ref(false);
const item = ref(null);
const cut = ref(null);
const choosing = ref(false);
const deleting = ref(false);
const pdf = ref(false);
const tab = ref(["items", "result", "settings"].includes(params.tab) ? params.tab : "items");
watch(tab, (value) => replace_params("rebar-plan", { name: params.name, tab: value }));

const readonly = computed(() => !view.value.can_write);
const tabs = computed(() => [
	{ value: "items", label: "รายการตัด", count: doc.value?.items.length },
	{ value: "result", label: "ผลการตัด" },
	{ value: "settings", label: "ตั้งค่า" },
]);
const rebar_options = computed(() =>
	(setup.value?.rebar_types || []).map((r) => ({
		value: r.name,
		label: r.name,
		description: r.standard_lengths ? `ยาวมาตรฐาน ${r.standard_lengths} ม.` : "",
	}))
);
const shapes = computed(() =>
	Object.fromEntries((setup.value?.shapes || []).map((s) => [s.name, s]))
);
const shape = computed(() => (item.value ? shapes.value[item.value.shape] : null));
const shape_name = (name) => shapes.value[name]?.shape_name || name;
const thumb = (r) => shape_svg(shapes.value[r.shape]?.svg, r);
const total_pieces = computed(() =>
	(doc.value?.items || []).reduce((s, r) => s + (Number(r.qty) || 0), 0)
);
const item_ready = computed(
	() =>
		!!item.value?.rebar_type &&
		!!shape.value &&
		Number(item.value.qty) > 0 &&
		shape.value.dims.every((d) => Number(item.value[d]) > 0)
);

// ผลการตัดแยกตามประเภทเหล็ก + สรุปจำนวนเส้นที่ใช้ต่อความยาว
const groups = computed(() => {
	const out = [];
	for (const p of doc.value?.patterns || []) {
		let g = out.find((x) => x.rebar_type === p.rebar_type);
		if (!g) out.push((g = { rebar_type: p.rebar_type, patterns: [] }));
		g.patterns.push(p);
	}
	for (const g of out) {
		g.used =
			"ใช้ " +
			(doc.value.summary || [])
				.filter((s) => s.rebar_type === g.rebar_type)
				.map((s) => `${meters(s.stock_length, 0)} ม. × ${s.bars} เส้น`)
				.join(" + ");
	}
	return out;
});
const width = (length_m, p) => (length_m / p.stock_length) * 100;

const payload = () =>
	JSON.stringify({
		...Object.fromEntries(INPUT.map((f) => [f, doc.value[f] ?? null])),
		items: doc.value.items.map((r) => Object.fromEntries(ITEM.map((f) => [f, r[f] ?? null]))),
		stock: doc.value.stock.map((r) => Object.fromEntries(STOCK.map((f) => [f, r[f] ?? null]))),
	});
const dirty = computed(() => !!doc.value && (!doc.value.name || payload() !== saved.value));

function apply(result) {
	view.value = result;
	const d = result.doc;
	doc.value = {
		...d,
		items: d.items.map((r) => ({ ...r, _key: ++key })),
		stock: d.stock.map((r) => ({ ...r, _key: ++key })),
	};
	if (!d.name) {
		Object.assign(doc.value, setup.value.defaults, { date: today() });
		for (const f of ["use_bend_deduction", ...SETTINGS, "kerf", "min_reusable"])
			if (doc.value[f] != null) doc.value[f] = Number(doc.value[f]);
	}
	saved.value = payload();
}

// ---- เหล็ก 1 แถว
function new_item() {
	const last = doc.value.items.at(-1);
	item.value = {
		_new: true,
		_key: ++key,
		mark: "",
		shape: last?.shape || setup.value.shapes[0]?.name,
		rebar_type: last?.rebar_type || null,
		qty: 1,
		...Object.fromEntries(DIMS.map((d) => [d, null])),
	};
	// แถวแรกเริ่มจากเลือกรูปทรง แถวต่อไปใช้รูปทรงเดิม (กดเปลี่ยนได้)
	choosing.value = !last;
	cut.value = null;
	update_cut();
}
function edit_item(r) {
	item.value = { ...r, _new: false };
	choosing.value = false;
	cut.value = r.cut_length
		? { cut_length: r.cut_length, unit_weight: r.total_length ? r.weight / r.total_length : 0 }
		: null;
	update_cut();
}
function pick_shape(s) {
	item.value.shape = s.name;
	// ด้านที่รูปใหม่ไม่ใช้ ล้างทิ้ง
	for (const d of DIMS) if (!s.dims.includes(d)) item.value[d] = null;
	choosing.value = false;
	update_cut();
}
let timer = null;
let seq = 0;
function update_cut() {
	clearTimeout(timer);
	timer = setTimeout(async () => {
		if (!item_ready.value) {
			cut.value = null;
			return;
		}
		const mine = ++seq;
		const it = item.value;
		try {
			const result = await call(`${API}.preview`, {
				shape: it.shape,
				rebar_type: it.rebar_type,
				dimensions: Object.fromEntries(shape.value.dims.map((d) => [d, it[d]])),
				settings: Object.fromEntries(SETTINGS.map((f) => [f, doc.value[f]])),
			});
			if (mine === seq) cut.value = result;
		} catch (e) {
			show_error(e);
		}
	}, 300);
}
function save_item(again) {
	const it = item.value;
	const { _new, ...clean } = it;
	// ความยาวตัด/น้ำหนักของแถวเป็นค่าชั่วคราวจนกว่าจะคำนวณและบันทึก
	if (cut.value) {
		clean.cut_length = cut.value.cut_length;
		clean.total_length = (cut.value.cut_length * clean.qty) / 1000;
		clean.weight = clean.total_length * cut.value.unit_weight;
	}
	const index = doc.value.items.findIndex((x) => x._key === it._key);
	if (index >= 0) doc.value.items.splice(index, 1, clean);
	else doc.value.items.push(clean);
	if (again) {
		// เพิ่มต่อได้ทันที: คงรูปทรงและประเภทเหล็ก ล้างค่าอื่น
		item.value = {
			...clean,
			_new: true,
			_key: ++key,
			mark: "",
			qty: 1,
			...Object.fromEntries(DIMS.map((d) => [d, null])),
		};
		cut.value = null;
	} else {
		item.value = null;
	}
}
function remove_item() {
	doc.value.items = doc.value.items.filter((x) => x._key !== item.value._key);
	item.value = null;
}
function add_stock() {
	doc.value.stock.push({ _key: ++key, rebar_type: null, length: 12, qty: null, remarks: "" });
}

async function save() {
	saving.value = true;
	try {
		const is_new = !doc.value.name;
		const result = await post(`${API}.save_plan`, { data: payload() });
		apply(result);
		await celebrate("คำนวณแล้ว", `ใช้เหล็ก ${meters(result.doc.total_weight)} กก.`);
		tab.value = "result";
		if (is_new) go("rebar-plan", { name: result.doc.name, tab: "result" }, { replace: true });
	} catch (e) {
		show_error(e);
	} finally {
		saving.value = false;
	}
}

async function load() {
	try {
		setup.value = await call(`${API}.get_setup`);
		const name = params.name && params.name !== "new" ? params.name : undefined;
		apply(await call(`${API}.get_plan`, { name, project: state.project?.name }));
	} catch (e) {
		show_error(e);
		back("rebar");
	}
}
load();
</script>
