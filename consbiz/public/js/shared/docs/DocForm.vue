<!-- สร้าง/แก้ไขร่างเอกสารจัดซื้อ/ขาย (ชุดเดียวทั้ง 6 ชนิด) ข้อมูล/บันทึกผ่าน site_docs.get_form / preview_doc / save_doc
     ยอดเงินและภาษีคำนวณที่ server (ERPNext) ทุกครั้งที่แก้ (หน่วงเล็กน้อย) ฟอร์มใหม่เก็บร่างใน localStorage -->
<template>
	<div class="ss-has-bar">
		<TopBar :title="title" :subtitle="subtitle" :back_to="back_view" :back_params="back_params" />

		<div class="ss-content ss-docform">
			<Skeleton v-if="!form" :rows="3" />
			<div v-else class="ss-docform-body" :class="{ 'has-insight': xl }">
				<div class="ss-docform-main">
					<div v-if="from_plan" class="ss-banner tone-blue">
						<Icon name="info" :size="22" />
						<div>
							<div class="ss-banner-title">รายการจากแผนวัสดุ</div>
							<div class="ss-banner-text">
								ดึงเฉพาะส่วนที่ยังขาดมาให้แล้ว ยังไม่บันทึก ตรวจ แก้ไข แล้วกดบันทึกเอง
							</div>
						</div>
					</div>
					<div v-if="form.source" class="ss-banner tone-blue">
						<Icon name="info" :size="22" />
						<div>
							<div class="ss-banner-title">สร้างจาก {{ source_label }} {{ form.source }}</div>
							<div class="ss-banner-text">
								ดึงรายการที่ยังค้างมาให้แล้ว ลบหรือแก้จำนวนได้ เอกสารจะอ้างถึงต้นทางให้เอง
							</div>
						</div>
					</div>

					<!-- หัวเอกสาร: แท็บเล็ต/จอใหญ่ = ตาราง 3-4 คอลัมน์ -->
					<section class="ss-form ss-docform-head">
						<Picker
							v-if="party_field"
							v-model="form[party_field]"
							class="ss-docform-party"
							:label="config.party"
							:display_value="form.party_label"
							:remote_fn="search_parties"
							required
							@select="(o) => (form.party_label = o.label)"
						/>
						<template v-if="is_mr">
							<label class="ss-field ss-docform-party">
								<span class="ss-field-label">เรื่อง</span>
								<input
									v-model="form.title"
									class="ss-input"
									placeholder="เช่น ขอซื้อวัสดุงานโครงสร้าง ชั้น 2"
								/>
							</label>
							<div class="ss-field">
								<span class="ss-field-label">วัตถุประสงค์<em>*</em></span>
								<SelectBox
									v-model="form.material_request_type"
									label="วัตถุประสงค์"
									:options="PURPOSES"
								/>
							</div>
						</template>
						<div v-for="f in fields" :key="f.field" class="ss-field">
							<span class="ss-field-label">{{ f.label }}<em v-if="f.required">*</em></span>
							<DateInput
								v-if="f.type === 'date'"
								v-model="form[f.field]"
								:label="f.label"
								:clearable="!f.required"
								@change="(v) => f.rows && fill_rows(f.rows, v)"
							/>
							<input
								v-else
								v-model="form[f.field]"
								class="ss-input"
								:placeholder="f.placeholder"
							/>
						</div>
						<template v-if="is_mr">
							<Picker
								v-model="form.custom_request_by"
								label="ผู้จัดทำ"
								:display_value="form.request_by_label"
								:remote_fn="search_signatures"
								clearable
								@select="(o) => (form.request_by_label = o.label)"
							/>
							<Picker
								v-model="form.custom_approve_by"
								label="ผู้อนุมัติ"
								:display_value="form.approve_by_label"
								:remote_fn="search_signatures"
								clearable
								@select="(o) => (form.approve_by_label = o.label)"
							/>
						</template>
						<div v-if="form.tax_templates.length" class="ss-field">
							<span class="ss-field-label">ภาษี</span>
							<SelectBox v-model="tax_value" label="ภาษี" :options="tax_options" />
						</div>
						<label v-if="has_discount" class="ss-field">
							<span class="ss-field-label">ส่วนลดท้ายบิล (%)</span>
							<input
								v-model.number="form.additional_discount_percentage"
								class="ss-input ss-input--num"
								type="number"
								inputmode="decimal"
								min="0"
								max="100"
								step="any"
								placeholder="0"
							/>
						</label>
						<!-- ออฟฟิศ: บริษัทของเอกสารใหม่ (มีหลายบริษัท) และโครงการเลือกในฟอร์ม -->
						<div v-if="company_choice" class="ss-field">
							<span class="ss-field-label">บริษัท<em>*</em></span>
							<SelectBox
								:model-value="form.company"
								label="บริษัท"
								:options="company_options"
								@update:model-value="change_company"
							/>
						</div>
						<Picker
							v-if="editable_project"
							v-model="form.project"
							class="ss-docform-project"
							label="โครงการ"
							placeholder="ไม่ระบุโครงการ"
							:display_value="form.project_name"
							:remote_fn="search_projects"
							clearable
							@select="(o) => (form.project_name = o?.label || '')"
						/>
						<div v-else-if="form.project" class="ss-field ss-docform-project">
							<span class="ss-field-label">โครงการ</span>
							<span class="ss-docform-project-name" :title="form.project_name"
								>{{ form.project_name || form.project }}
								<small>{{ form.project }}</small></span
							>
						</div>
					</section>

					<section class="ss-docform-items">
						<h2 class="ss-section-title ss-section-title--first">
							<span
								>รายการ <span class="ss-count">{{ form.items.length }}</span></span
							>
							<span v-if="form.items.length" class="ss-section-total">{{
								money(lines_total)
							}}</span>
						</h2>
						<Empty
							v-if="!form.items.length && !wide"
							:icon="config.icon"
							title="ยังไม่มีรายการ"
							text="เลือกสินค้า/บริการ แล้วใส่จำนวนและราคา"
						/>
						<LineEditor
							:items="form.items"
							:wide="wide"
							:is_mr="is_mr"
							:date_field="row_date.field"
							:date_label="row_date.label"
							:show_errors="show_errors"
							:search_fn="find_items"
							@add="add_item"
							@remove="remove_rows"
							@reorder="(items) => (form.items = items)"
							@detail="(row) => (detail_row = row)"
							@focus-row="(row) => (insight_row = row)"
							:active_row="xl ? insight_row : null"
							@browse="item_sheet = true"
						/>
					</section>

					<!-- ท้ายเอกสาร: หมายเหตุ/ตัวเลือกภาษี (ซ้าย) + สรุปยอด (ขวา) แบบระบบเต็ม -->
					<section class="ss-docform-foot">
						<div class="ss-docform-notes">
							<label v-if="remarks_field" class="ss-field">
								<span class="ss-field-label">หมายเหตุ</span>
								<textarea v-model="form[remarks_field]" class="ss-input" rows="3"></textarea>
							</label>
							<div
								v-if="is_mr && form.material_request_type !== 'Customer Provided'"
								class="ss-dv-flags"
							>
								<label class="ss-checkline">
									<input
										v-model="form.custom_included_vat"
										type="checkbox"
										:true-value="1"
										:false-value="0"
									/>
									<span>มูลค่ารวมภาษี</span>
								</label>
								<label class="ss-checkline">
									<input
										v-model="form.custom_vat_override"
										type="checkbox"
										:true-value="1"
										:false-value="0"
									/>
									<span>แก้ไขภาษี</span>
								</label>
							</div>
							<!-- หัก ณ ที่จ่าย / เงินประกันผลงาน (% ของยอดก่อนภาษี) ใบแจ้งหนี้ขายติ๊ก "แก้ไขยอดเอง" ได้ -->
							<div v-if="has_deduct" class="ss-deducts">
								<div v-for="d in DEDUCTS" :key="d.subject" class="ss-deduct">
									<label class="ss-checkline">
										<input
											v-model="form[d.subject]"
											type="checkbox"
											:true-value="1"
											:false-value="0"
										/>
										<span>{{ d.label }}</span>
									</label>
									<template v-if="form[d.subject]">
										<label class="ss-deduct-pct">
											<input
												v-model.number="form[d.percent]"
												class="ss-cell ss-cell--num"
												type="number"
												inputmode="decimal"
												min="0"
												step="any"
												:aria-label="`${d.label} (%)`"
											/>
											<span>%</span>
										</label>
										<template v-if="form.fields.includes(d.edit)">
											<label class="ss-checkline ss-deduct-edit">
												<input
													v-model="form[d.edit]"
													type="checkbox"
													:true-value="1"
													:false-value="0"
												/>
												<span>กรอกยอดเอง</span>
											</label>
											<MoneyInput
												v-if="form[d.edit]"
												v-model="form[d.amount]"
												class="ss-cell ss-cell--num ss-deduct-amount"
												:aria-label="`ยอด${d.label}`"
											/>
										</template>
									</template>
								</div>
							</div>
							<p v-if="!is_mr" class="ss-muted ss-docform-note">
								<Icon name="info" :size="14" /> เงื่อนไขชำระเงินและบัญชีอื่นๆ
								แก้ต่อได้ในระบบเต็มหลังบันทึก
							</p>
						</div>
						<div class="ss-totals" :class="{ 'is-stale': previewing }">
							<div v-for="r in form.summary.rows" :key="r.label">
								<span>{{ r.label }}</span>
								<MoneyInput
									v-if="r.tax && is_mr && form.custom_vat_override"
									v-model="form.custom_vat"
									class="ss-cell ss-cell--num ss-totals-input"
									aria-label="ภาษีมูลค่าเพิ่ม"
								/>
								<b v-else>{{ money(r.value) }}</b>
							</div>
							<div class="is-grand">
								<span
									>{{ form.summary.grand_label }}
									<span v-if="previewing" class="ss-spinner ss-spinner--sm"></span
								></span>
								<b>{{ money(grand_total) }}</b>
							</div>
							<div v-if="form.summary.in_words" class="ss-totals-words">
								({{ form.summary.in_words }})
							</div>
							<template v-if="form.summary.net !== undefined">
								<div v-for="d in form.summary.deductions" :key="d.label" class="is-deduct">
									<span>{{ d.label }}</span
									><b>{{ money(d.value) }}</b>
								</div>
								<div class="is-net">
									<span>{{ form.summary.net_label }}</span
									><b>{{ money(form.summary.net) }}</b>
								</div>
							</template>
						</div>
					</section>

					<!-- รายละเอียดของแถว (ปุ่มปากกา) แบบฟอร์มแถวของระบบเต็ม -->
					<Sheet
						:open="!!detail_row"
						title="รายละเอียดรายการ"
						:subtitle="detail_row?.item_code"
						@close="detail_row = null"
					>
						<div v-if="detail_row" class="ss-form ss-row-detail">
							<div class="ss-field">
								<span class="ss-field-label">รายการ</span>
								<b>{{ detail_row.item_name }}</b>
							</div>
							<div class="ss-field">
								<span class="ss-field-label">รายละเอียด</span>
								<RichEditor
									v-model="detail_row.description"
									label="รายละเอียด"
									placeholder="รายละเอียด/สเปกของรายการ"
								/>
							</div>
							<div class="ss-form-row">
								<label class="ss-field">
									<span class="ss-field-label">จำนวน</span>
									<input
										v-model.number="detail_row.qty"
										class="ss-input ss-input--num"
										type="number"
										inputmode="decimal"
										step="any"
									/>
								</label>
								<div class="ss-field">
									<span class="ss-field-label">หน่วย</span>
									<SelectBox
										v-model="detail_row.uom"
										label="หน่วย"
										:options="
											(detail_row.uoms || []).map((u) => ({ value: u, label: u }))
										"
									/>
								</div>
							</div>
							<div class="ss-form-row">
								<label class="ss-field">
									<span class="ss-field-label">หน่วยละ</span>
									<MoneyInput
										v-model="detail_row.rate"
										class="ss-input ss-input--num"
										aria-label="หน่วยละ"
									/>
								</label>
								<div class="ss-field">
									<span class="ss-field-label">เป็นเงิน</span>
									<b class="ss-row-detail-amount">{{
										money((Number(detail_row.qty) || 0) * (Number(detail_row.rate) || 0))
									}}</b>
								</div>
							</div>
							<div v-if="row_date.field" class="ss-field">
								<span class="ss-field-label">{{ row_date.label }}</span>
								<DateInput v-model="detail_row[row_date.field]" :label="row_date.label" />
							</div>
							<label v-if="is_mr" class="ss-field">
								<span class="ss-field-label">WBS (งานในแผน)</span>
								<input
									v-model="detail_row.custom_wbs"
									class="ss-input"
									placeholder="เช่น 4.1.2"
								/>
							</label>
							<label v-if="is_mr" class="ss-checkline">
								<input
									v-model="detail_row.custom_vat_nocal"
									type="checkbox"
									:true-value="1"
									:false-value="0"
								/>
								<span>ไม่คิดภาษี</span>
							</label>
						</div>
						<template #footer>
							<button
								type="button"
								class="ss-btn ss-btn--primary ss-btn--block"
								@click="detail_row = null"
							>
								เสร็จ
							</button>
						</template>
					</Sheet>
				</div>
				<ItemInsight v-if="xl" :kind="kind" :project="form.project || null" :row="insight_row" />
			</div>
		</div>

		<Teleport to="#ss-layer">
			<Transition name="ss-bar">
				<div v-if="form" class="ss-bottom-bar">
					<span class="ss-bar-summary">
						<small>ยอดรวม</small> <b>{{ money(grand_total) }}</b>
					</span>
					<button
						type="button"
						class="ss-btn ss-btn--ghost ss-btn--lg"
						:class="{ 'ss-grow': !form.can_submit }"
						:disabled="saving"
						@click="save(0)"
					>
						บันทึกร่าง
					</button>
					<button
						v-if="form.can_submit"
						type="button"
						class="ss-btn ss-btn--primary ss-btn--lg ss-grow"
						:disabled="saving"
						@click="ask_submit"
					>
						<span v-if="saving" class="ss-spinner"></span>
						<template v-else>บันทึกและส่ง</template>
					</button>
				</div>
			</Transition>
		</Teleport>

		<!-- เลือกสินค้า/บริการ (แตะได้หลายรายการ) -->
		<Sheet
			:open="item_sheet"
			title="เพิ่มรายการ"
			:subtitle="`เพิ่มแล้ว ${added} รายการ`"
			full
			@close="item_sheet = false"
		>
			<div class="ss-search">
				<Icon name="search" :size="18" />
				<input
					ref="item_input"
					v-model="item_txt"
					type="search"
					placeholder="ค้นหารหัส ชื่อ หรือกลุ่มสินค้า"
					@input="search_items"
				/>
			</div>
			<div class="ss-options">
				<button
					v-for="it in item_results"
					:key="it.item_code"
					type="button"
					class="ss-option"
					:class="{ 'is-active': in_form.has(it.item_code) }"
					@click="add_item(it)"
				>
					<span class="ss-check-box"
						><Icon v-if="in_form.has(it.item_code)" name="check" :size="14" :stroke="3"
					/></span>
					<span class="ss-option-main">
						<span class="ss-option-label">{{ it.item_name }}</span>
						<span class="ss-option-desc"
							>{{ it.item_code }} · {{ it.item_group }} · {{ it.stock_uom
							}}<template v-if="it.rate && !is_mr"> · {{ money(it.rate) }}</template></span
						>
					</span>
				</button>
				<div v-if="item_loading" class="ss-options-note">กำลังค้นหา…</div>
				<div v-else-if="!item_results.length" class="ss-options-note">ไม่พบรายการ</div>
			</div>
			<template #footer>
				<button
					type="button"
					class="ss-btn ss-btn--primary ss-btn--block"
					@click="item_sheet = false"
				>
					เสร็จ
				</button>
			</template>
		</Sheet>

		<Sheet :open="confirm" :title="`ส่ง${config.label}`" @close="confirm = false">
			<p class="ss-muted">ส่งแล้วแก้ไขไม่ได้ ต้องยกเลิกแล้วแก้ไขในระบบเต็ม</p>
			<div v-if="form" class="ss-facts ss-facts--grid">
				<div v-if="party_field" class="ss-fact">
					<span>{{ config.party }}</span
					><b>{{ form.party_label || form[party_field] }}</b>
				</div>
				<div class="ss-fact">
					<span>รายการ</span><b>{{ form.items.length }}</b>
				</div>
				<div v-if="!is_mr" class="ss-fact">
					<span>ยอดรวม</span><b>{{ money(grand_total) }}</b>
				</div>
			</div>
			<template #footer>
				<button
					type="button"
					class="ss-btn ss-btn--primary ss-btn--block ss-btn--lg"
					:disabled="saving"
					@click="save(1)"
				>
					<span v-if="saving" class="ss-spinner"></span>
					<template v-else>ยืนยันส่ง</template>
				</button>
			</template>
		</Sheet>
	</div>
</template>

<script setup>
import { computed, inject, nextTick, onBeforeUnmount, ref, watch } from "vue";
import Icon from "../components/Icon.vue";
import TopBar from "../components/TopBar.vue";
import Skeleton from "../components/Skeleton.vue";
import Empty from "../components/Empty.vue";
import Picker from "../components/Picker.vue";
import Sheet from "../components/Sheet.vue";
import LineEditor from "./LineEditor.vue";
import ItemInsight from "./ItemInsight.vue";
import MoneyInput from "../components/MoneyInput.vue";
import RichEditor from "../components/RichEditor.vue";
import SelectBox from "../components/SelectBox.vue";
import DateInput from "../components/DateInput.vue";
import { DOC_KINDS, PLAN_SOURCE, clear_plan_request, plan_request } from "./kinds.js";
import { app } from "../app.js";
import { boot, call, celebrate, go, money, post, show_error, state, toast } from "../api.js";

const reload_summary = inject("reload_summary");

// จอกว้าง ≥1000 (แท็บเล็ตแนวนอน/คอมพิวเตอร์): ตารางรายการแก้ไขในช่อง
// แคบกว่านั้น (มือถือ, แท็บเล็ตแนวตั้ง ที่เนื้อหากว้างไม่ถึง ~650px): การ์ด กดง่ายบนจอสัมผัส
const mq_wide = window.matchMedia("(min-width: 1000px)");
const wide = ref(mq_wide.matches);
const on_media = () => (wide.value = mq_wide.matches);
mq_wide.addEventListener("change", on_media);
onBeforeUnmount(() => mq_wide.removeEventListener("change", on_media));
const params = state.route.params;
const kind = DOC_KINDS[params.kind] ? params.kind : "po";
const config = DOC_KINDS[kind];
const is_mr = kind === "mr";
const is_new = !params.name || params.name === "new";
// ขอซื้อจากแผนวัสดุ: รายการมาจากแถวที่ติ๊กในหมวดทรัพยากร (ไม่ใช่เอกสารต้นทาง)
const from_plan = kind === "mr" && params.source === PLAN_SOURCE;
const plan = from_plan ? plan_request() : null;
const source_doc = from_plan ? null : params.source || null;

// ---------------------------------------------------------------- โครงการ / บริษัท (แอปออฟฟิศ)
const editable_project = computed(() => app.project_filter && !!config.project);
const company_choice = computed(
	() => app.project_filter && is_new && !params.source && (boot.companies || []).length > 1
);
const company_options = (boot.companies || []).map((c) => ({ value: c.name, label: c.name }));
const company_override = ref(null);
let project_list = null;
async function search_projects(txt) {
	project_list = project_list || (await call("get_projects"));
	const q = (txt || "").trim().toLowerCase();
	return project_list
		.filter((p) => !form.value?.company || p.company === form.value.company)
		.filter((p) => !q || `${p.name} ${p.project_name}`.toLowerCase().includes(q))
		.slice(0, 80)
		.map((p) => ({ value: p.name, label: p.project_name || p.name, description: p.name }));
}
// เปลี่ยนบริษัทของเอกสารใหม่ = เริ่มฟอร์มใหม่ (ภาษี/ราคา/คู่ค้าขึ้นกับบริษัท)
async function change_company(company) {
	if (!company || company === form.value?.company) return;
	if (form.value?.items.length && !window.confirm("เปลี่ยนบริษัทจะล้างรายการที่กรอกไว้ ทำต่อไหม?")) return;
	company_override.value = company;
	try {
		localStorage.removeItem(draft_key);
	} catch {
		/* เข้าถึงไม่ได้ */
	}
	form.value = null;
	await load();
}

// ช่องหัวเอกสาร (ตรงกับ FORM ใน site_docs.py) rows = ช่องของแถวที่ตามค่านี้เมื่อแก้
const PARTY = { po: "supplier", pi: "supplier", qtn: "party_name", so: "customer", si: "customer" };
const FIELDS = {
	mr: [
		{ field: "transaction_date", label: "วันที่", type: "date", required: true },
		{
			field: "schedule_date",
			label: "ต้องการภายใน",
			type: "date",
			required: true,
			rows: "schedule_date",
		},
	],
	po: [
		{ field: "transaction_date", label: "วันที่", type: "date", required: true },
		{ field: "schedule_date", label: "กำหนดส่ง", type: "date", required: true, rows: "schedule_date" },
	],
	pi: [
		{ field: "posting_date", label: "วันที่", type: "date", required: true },
		{ field: "due_date", label: "ครบกำหนดจ่าย", type: "date" },
		{ field: "bill_no", label: "เลขที่บิลผู้ขาย", placeholder: "เลขที่ใบแจ้งหนี้ของผู้ขาย" },
		{ field: "tax_invoice_number", label: "เลขที่ใบกำกับภาษี", placeholder: "เมื่อมีภาษีซื้อ" },
	],
	qtn: [
		{ field: "transaction_date", label: "วันที่", type: "date", required: true },
		{ field: "valid_till", label: "ยืนราคาถึง", type: "date" },
	],
	so: [
		{ field: "po_no", label: "เลขที่ใบสั่งซื้อลูกค้า", placeholder: "PO ของลูกค้า (ถ้ามี)" },
		{ field: "transaction_date", label: "วันที่", type: "date", required: true },
		{ field: "delivery_date", label: "กำหนดส่งมอบ", type: "date", required: true, rows: "delivery_date" },
	],
	si: [
		{ field: "po_no", label: "เลขที่ใบสั่งซื้อลูกค้า", placeholder: "PO ของลูกค้า (ถ้ามี)" },
		{ field: "posting_date", label: "วันที่", type: "date", required: true },
		{ field: "due_date", label: "ครบกำหนดรับ", type: "date" },
	],
};
const REMARKS = { mr: "custom_remark", pi: "remarks", si: "remarks" };
// หัก ณ ที่จ่าย / เงินประกันผลงาน (edit/amount = ใบแจ้งหนี้ขายกรอกยอดเอง)
const DEDUCTS = [
	{
		label: "หัก ณ ที่จ่าย",
		subject: "custom_subject_to_wht",
		percent: "custom_wht_percent",
		edit: "custom_edit_wht",
		amount: "custom_wht_amount",
	},
	{
		label: "เงินประกันผลงาน",
		subject: "custom_subject_to_retention",
		percent: "custom_retention_percent",
		edit: "custom_edit_retention",
		amount: "custom_retention_amount",
	},
];
const PURPOSES = [
	{ value: "Purchase", label: "ซื้อ" },
	{ value: "Customer Provided", label: "ผู้ว่าจ้างจัดหา" },
];
const SOURCE_KIND = { po: "mr", pi: "po", so: "qtn", si: "so" };

const party_field = PARTY[kind];
const remarks_field = REMARKS[kind];
const form = ref(null);
const show_errors = ref(false);
const saving = ref(false);
const confirm = ref(false);
const previewing = ref(false);
let uid = 0;

// ช่องที่ server ไม่มี (เช่น ไม่ได้ติดตั้ง erpnext_thailand) ไม่แสดง
const fields = computed(() =>
	FIELDS[kind].filter((f) => !form.value?.fields || form.value.fields.includes(f.field))
);
const title = computed(() => (is_new ? `${config.label}ใหม่` : `แก้ไข${config.label}`));
const subtitle = computed(() =>
	is_new ? form.value?.project_name || state.project?.project_name || "" : params.name
);
const source_label = computed(() => DOC_KINDS[SOURCE_KIND[kind]]?.label || "");
const back_view = computed(() =>
	from_plan ? "resources" : is_new && !params.source ? kind : `${config.section}-doc`
);
const back_params = computed(() =>
	from_plan || (is_new && !params.source)
		? {}
		: { kind: is_new ? SOURCE_KIND[kind] : kind, name: is_new ? params.source : params.name }
);
const grand_total = computed(() => form.value?.summary?.grand || 0);
const tax_options = computed(() => [
	...form.value.tax_templates.map((t) => ({ value: t.name, label: t.title || t.name })),
	{ value: "", label: "ไม่มีภาษี" },
]);
// ภาษี: select ใช้ "" แทน "ไม่มีภาษี"
const tax_value = computed({
	get: () => form.value?.taxes_and_charges || "",
	set: (value) => (form.value.taxes_and_charges = value || null),
});
const has_deduct = computed(() => !!form.value?.fields?.includes("custom_subject_to_wht"));
const has_discount = computed(() => !!form.value?.fields?.includes("additional_discount_percentage"));
// วันที่รายแถว (แก้ต่างจากหัวเอกสารได้)
const row_date = computed(
	() =>
		({
			mr: { field: "schedule_date", label: "ต้องการภายใน" },
			po: { field: "schedule_date", label: "กำหนดส่ง" },
			so: { field: "delivery_date", label: "กำหนดส่งมอบ" },
		}[kind] || {})
);
const lines_total = computed(() =>
	(form.value?.items || []).reduce((s, r) => s + (Number(r.qty) || 0) * (Number(r.rate) || 0), 0)
);
const find_items = (txt) =>
	call("consbiz.site_docs.search_items", { kind, txt, project: form.value?.project || null });

const in_form = computed(() => new Set(form.value?.items.map((r) => r.item_code)));

// ---------------------------------------------------------------- โหลด / ร่างในเครื่อง

const draft_key = `consbiz.site.docform.${kind}.${params.source || "new"}.${state.project?.name || ""}`;

function with_uid(items) {
	return items.map((row) => ({ ...row, uid: ++uid }));
}

async function load() {
	if (from_plan && !plan) {
		toast("เลือกวัสดุจากหน้าทรัพยากรอีกครั้ง", "warning");
		go("resources", {}, { replace: true });
		return;
	}
	try {
		const data = await call("consbiz.site_docs.get_form", {
			kind,
			name: is_new ? null : params.name,
			source: source_doc,
			// เอกสารใหม่: โครงการ (หน้างาน = ที่ทำงานอยู่, ออฟฟิศ = ตัวกรอง) / บริษัท (ออฟฟิศ)
			project: plan?.project || state.project?.name || null,
			company: company_override.value || state.company || null,
			plan_rows: plan ? JSON.stringify(plan.rows) : null,
		});
		data.items = with_uid(data.items);
		// รายการมาจากแผนที่เลือกครั้งนี้ ไม่กู้ร่างเก่าในเครื่องมาทับ
		const restored = is_new && !from_plan && restore_draft(data);
		form.value = data;
		if (data.plan_others) {
			toast(`รายการผู้ว่าจ้างจัดหาอีก ${data.plan_others} รายการต้องแยกใบ บันทึกใบนี้แล้วเลือกต่อที่หน้าทรัพยากร`, "info");
		}
		// ร่างที่กู้คืนยังไม่มียอดของรายการที่กรอกค้างไว้: คำนวณใหม่ทันที
		if (restored) preview();
	} catch (error) {
		show_error(error);
	}
}

function restore_draft(data) {
	try {
		const saved = JSON.parse(localStorage.getItem(draft_key) || "null");
		if (!saved) return;
		Object.assign(data, saved, { items: with_uid(saved.items || []) });
		toast("กู้ข้อมูลที่กรอกค้างไว้แล้ว", "info");
		return true;
	} catch {
		/* ร่างเสียหรือเข้าถึงไม่ได้: เริ่มใหม่ */
	}
}

// ค่าที่ส่งให้ server (ช่องที่กรอกได้เท่านั้น)
function payload() {
	const f = form.value;
	// โครงการ/บริษัทของเอกสาร (ออฟฟิศแก้โครงการได้ในฟอร์ม บริษัทเลือกได้เฉพาะเอกสารใหม่)
	const out = { name: f.name, source: f.source, project: f.project || null, company: f.company || null };
	if (plan) out.plan_rows = plan.rows;
	// ช่องหัวเอกสารที่ server รับ (FORM ใน site_docs.py ที่ DocType มีจริง)
	for (const field of [...(f.fields || []), party_field, remarks_field]) {
		if (field) out[field] = f[field] ?? null;
	}
	out.items = f.items.map((row) => ({
		key: row.key,
		item_code: row.item_code,
		qty: Number(row.qty) || 0,
		uom: row.uom,
		rate: Number(row.rate) || 0,
		description: row.description || null,
		...(row.schedule_date ? { schedule_date: row.schedule_date } : {}),
		...(row.delivery_date ? { delivery_date: row.delivery_date } : {}),
		...(is_mr
			? { custom_wbs: row.custom_wbs || null, custom_vat_nocal: row.custom_vat_nocal ? 1 : 0 }
			: {}),
	}));
	return out;
}

let draft_timer = null;
let preview_timer = null;
let preview_id = 0;
watch(
	() => form.value && JSON.stringify(payload()),
	(value, old) => {
		if (!value || !old) return;
		if (is_new && !from_plan) {
			clearTimeout(draft_timer);
			draft_timer = setTimeout(() => {
				try {
					const { items, ...rest } = payload();
					localStorage.setItem(
						draft_key,
						JSON.stringify({
							...rest,
							party_label: form.value.party_label,
							items: form.value.items,
						})
					);
				} catch {
					/* พื้นที่เต็ม/โหมดส่วนตัว: ไม่เก็บร่าง */
				}
			}, 600);
		}
		clearTimeout(preview_timer);
		preview_timer = setTimeout(preview, 450);
	}
);

// ยอดรวม/ภาษีจาก ERPNext (ข้อมูลยังไม่ครบ เช่น ยังไม่เลือกผู้ขาย = คงยอดเดิมไว้)
async function preview() {
	const id = ++preview_id;
	previewing.value = true;
	try {
		const result = await post("consbiz.site_docs.preview_doc", { kind, data: payload() });
		if (id !== preview_id) return;
		form.value.totals = result.totals;
		form.value.taxes = result.taxes;
		form.value.summary = result.summary;
	} catch {
		/* แสดงข้อผิดพลาดตอนบันทึก */
	} finally {
		if (id === preview_id) previewing.value = false;
	}
}

// ---------------------------------------------------------------- รายการ

const item_sheet = ref(false);
const item_txt = ref("");
const item_results = ref([]);
const item_loading = ref(false);
const item_input = ref(null);
const added = ref(0);
let search_timer = null;

function search_items() {
	clearTimeout(search_timer);
	search_timer = setTimeout(async () => {
		item_loading.value = true;
		try {
			item_results.value = await call("consbiz.site_docs.search_items", {
				kind,
				txt: item_txt.value,
				project: form.value?.project || null,
			});
		} catch (error) {
			show_error(error);
		} finally {
			item_loading.value = false;
		}
	}, 220);
}

watch(item_sheet, async (open) => {
	if (!open) return;
	added.value = 0;
	item_txt.value = "";
	search_items();
	await nextTick();
	setTimeout(() => item_input.value?.focus(), 320);
});

function add_item(it) {
	const date_field = { mr: "schedule_date", po: "schedule_date", so: "delivery_date" }[kind];
	form.value.items.push({
		uid: ++uid,
		key: null,
		item_code: it.item_code,
		item_name: it.item_name,
		qty: 1,
		uom: it.stock_uom,
		uoms: it.uoms,
		rate: it.rate || 0,
		...(date_field ? { [date_field]: form.value[date_field] } : {}),
	});
	added.value++;
}

// ลบแถว (1 แถวจากปุ่มถังขยะ หรือหลายแถวที่เลือกในตาราง)
function remove_rows(rows) {
	const gone = new Set(Array.isArray(rows) ? rows : [rows]);
	form.value.items = form.value.items.filter((r) => !gone.has(r));
}

// จอใหญ่มาก (≥1480): แผงข้อมูลประกอบของแถวที่เลือก (ItemInsight)
const mq_xl = window.matchMedia("(min-width: 1480px)");
const xl = ref(mq_xl.matches);
const on_xl = () => (xl.value = mq_xl.matches);
mq_xl.addEventListener("change", on_xl);
onBeforeUnmount(() => mq_xl.removeEventListener("change", on_xl));
const insight_row = ref(null);
watch(
	() => form.value?.items.length,
	() => {
		if (insight_row.value && !form.value.items.includes(insight_row.value)) insight_row.value = null;
	}
);

// แถวที่เปิดรายละเอียด (ปุ่มปากกา)
const detail_row = ref(null);

const search_signatures = (txt) => call("consbiz.site_docs.search_signatures", { txt });

function fill_rows(field, value) {
	if (value) form.value.items.forEach((row) => (row[field] = value));
}

function row_error(row) {
	if (!(Number(row.qty) > 0)) return "ใส่จำนวนมากกว่า 0";
	return "";
}

async function search_parties(txt) {
	return call("consbiz.site_docs.search_parties", { kind, txt, company: form.value.company });
}

// ---------------------------------------------------------------- บันทึก

function form_error() {
	if (party_field && !form.value[party_field]) return `เลือก${config.party}`;
	const missing = fields.value.find((f) => f.required && !form.value[f.field]);
	if (missing) return `ใส่${missing.label}`;
	if (!form.value.items.length) return "เพิ่มรายการอย่างน้อย 1 รายการ";
	const bad = form.value.items.find(row_error);
	if (bad) return `${bad.item_name || bad.item_code}: ${row_error(bad)}`;
	return "";
}

function ask_submit() {
	const error = form_error();
	if (error) {
		show_errors.value = true;
		return toast(error, "error");
	}
	confirm.value = true;
}

async function save(submit) {
	const error = form_error();
	if (error) {
		show_errors.value = true;
		return toast(error, "error");
	}
	saving.value = true;
	try {
		const result = await post("consbiz.site_docs.save_doc", { kind, data: payload(), submit });
		if (from_plan) clear_plan_request();
		try {
			localStorage.removeItem(draft_key);
		} catch {
			/* ไม่มีร่าง */
		}
		confirm.value = false;
		reload_summary();
		await celebrate(submit ? `ส่ง${config.label}แล้ว` : "บันทึกร่างแล้ว", result.name);
		go(`${config.section}-doc`, { kind, name: result.name }, { replace: true });
	} catch (err) {
		show_error(err);
	} finally {
		saving.value = false;
	}
}

load();
</script>
