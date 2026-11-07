<!-- รายละเอียดเอกสารจัดซื้อ/ขาย: หัวเอกสาร, ความคืบหน้า, รายการ, ยอดรวม, เอกสารต้นทาง/ปลายทาง, PDF, ส่งเอกสาร -->
<template>
	<div :class="{ 'ss-has-bar': has_bar }">
		<TopBar :title="config.label" :subtitle="params.name" :back_to="params.kind">
			<template #actions>
				<button
					v-if="doc"
					type="button"
					class="ss-icon-btn"
					aria-label="PDF / พิมพ์ / แชร์"
					title="PDF / พิมพ์ / แชร์"
					@click="pdf = true"
				>
					<Icon name="printer" :size="19" />
				</button>
				<a
					class="ss-icon-btn"
					:href="desk_url(config.doctype, params.name)"
					aria-label="เปิดในระบบเต็ม"
					title="เปิดในระบบเต็ม"
				>
					<Icon name="external" :size="19" />
				</a>
				<!-- เปิด/ปิด sidebar ขวา (มอบหมาย ไฟล์แนบ ความคิดเห็น ความเคลื่อนไหว) -->
				<button
					v-if="doc"
					type="button"
					class="ss-icon-btn"
					:class="{ 'is-on': side_open }"
					:aria-pressed="side_open"
					aria-label="แผงข้อมูลเอกสาร"
					title="แผงข้อมูลเอกสาร (มอบหมาย ไฟล์แนบ ความคิดเห็น)"
					@click="toggle_side"
				>
					<Icon name="panel-right" :size="19" />
				</button>
			</template>
		</TopBar>

		<div class="ss-content ss-docview">
			<Skeleton v-if="!doc" :rows="3" />
			<template v-else>
				<section class="ss-dv-head">
					<!-- ขั้นตอนของเอกสาร: ผ่านแล้ว / ขั้นปัจจุบัน (มี %) / ยังไม่ถึง -->
					<ol class="ss-dv-steps" :aria-label="`ขั้นตอน: ${doc.status_label}`">
						<li v-for="(st, i) in doc.steps" :key="i" :class="`is-${st.state}`">
							<span class="ss-dv-step-dot">
								<Icon v-if="st.state === 'done'" name="check" :size="13" :stroke="3" />
								<Icon v-else-if="st.state === 'error'" name="x" :size="13" :stroke="3" />
								<template v-else>{{ i + 1 }}</template>
							</span>
							<span class="ss-dv-step-text">
								<b>{{ st.label }}</b>
								<small v-if="st.note && st.state !== 'todo'">{{ st.note }}</small>
							</span>
						</li>
					</ol>

					<dl class="ss-dv-fields">
						<div class="is-wide">
							<dt>{{ config.party || "เรื่อง" }}</dt>
							<dd>
								<InlineEdit
									v-if="!config.party && edit.title"
									:model-value="doc.title"
									:label="edit.title.label"
									:display="doc.title || doc.name"
									editable
									:save="(v) => save_field('title', v)"
								/>
								<template v-else>{{ doc.party || doc.title || doc.name }}</template>
							</dd>
						</div>
						<div>
							<dt>สถานะ</dt>
							<dd>
								<span class="ss-tag" :class="`tone-${doc.status_tone}`">{{
									doc.status_label
								}}</span>
							</dd>
						</div>
						<div v-if="doc.purpose">
							<dt>วัตถุประสงค์</dt>
							<dd>{{ doc.purpose }}</dd>
						</div>
						<div>
							<dt>วันที่</dt>
							<dd>{{ thai_date(doc.date, { year: true }) }}</dd>
						</div>
						<div v-if="doc.due || edit[due_field]">
							<dt>{{ config.due || "วันที่ต้องการ" }}</dt>
							<dd :class="{ 'is-due': overdue }">
								<InlineEdit
									v-if="edit[due_field]"
									fieldtype="Date"
									:model-value="doc.due"
									:label="edit[due_field].label"
									:display="thai_date(doc.due, { year: true })"
									:min="doc.date"
									:apply_label="
										item_date_field === due_field ? 'ใช้วันนี้กับทุกรายการ' : null
									"
									required
									editable
									:save="(v, apply) => save_field(due_field, v, apply)"
								/>
								<template v-else>{{ thai_date(doc.due, { year: true }) }}</template>
							</dd>
						</div>
						<div v-if="doc.po_no && !edit.po_no">
							<dt>เลขที่ใบสั่งซื้อลูกค้า</dt>
							<dd>{{ doc.po_no }}</dd>
						</div>
						<div v-if="doc.bill_no">
							<dt>เลขที่บิลผู้ขาย</dt>
							<dd>{{ doc.bill_no }}</dd>
						</div>
						<div>
							<dt>ผู้จัดทำ</dt>
							<dd>{{ doc.request_by || doc.owner_name }}</dd>
						</div>
						<div v-if="params.kind === 'mr'">
							<dt>ผู้อนุมัติ</dt>
							<dd :class="{ 'is-empty': !doc.approve_by }">{{ doc.approve_by || "–" }}</dd>
						</div>
						<!-- ช่องที่แก้ได้หลังส่ง (เลขที่ใบกำกับภาษี, เลขที่ PO ลูกค้า ฯลฯ) ที่ไม่ได้แสดงที่อื่น -->
						<div v-for="f in extra_fields" :key="f.fieldname">
							<dt>{{ f.label }}</dt>
							<dd>
								<InlineEdit
									:model-value="f.value"
									:label="f.label"
									add_label=""
									:fieldtype="f.fieldtype"
									:display="
										f.fieldtype === 'Date' ? thai_date(f.value, { year: true }) : f.value
									"
									editable
									:save="(v) => save_field(f.fieldname, v)"
								/>
							</dd>
						</div>
						<div v-if="doc.project" class="is-full">
							<dt>โครงการ</dt>
							<dd class="is-line" :title="doc.project_name">
								{{ doc.project_name || doc.project }} <small>{{ doc.project }}</small>
							</dd>
						</div>
					</dl>
				</section>

				<div class="ss-dv-body">
					<div class="ss-dv-main">
						<h2 class="ss-section-title ss-section-title--first">
							<span
								>รายการ <span class="ss-count">{{ doc.items.length }}</span></span
							>
						</h2>

						<!-- จอกว้าง: ตารางรายการ -->
						<div v-if="wide" class="ss-table-wrap">
							<table class="ss-table ss-table--doc">
								<thead>
									<tr>
										<th class="is-idx">#</th>
										<th>รายการ</th>
										<th class="is-num">จำนวน</th>
										<th>หน่วย</th>
										<th class="is-num">หน่วยละ</th>
										<th class="is-num">เป็นเงิน</th>
										<th v-if="has_item_date">วันที่ต้องการ</th>
										<th v-if="is_mr" class="is-center">ไม่คิดภาษี</th>
									</tr>
								</thead>
								<tbody>
									<tr v-for="(it, i) in doc.items" :key="i" class="is-static">
										<td class="is-idx">{{ i + 1 }}</td>
										<td class="is-item">
											<b>{{ it.item_name || it.item_code }}</b>
											<small
												>{{ it.item_code
												}}<template v-if="item_progress(it)">
													· {{ item_progress(it) }}</template
												></small
											>
											<RichText
												v-if="has_desc(it)"
												:html="it.description"
												class="ss-item-desc"
											/>
										</td>
										<td class="is-num">{{ num(it.qty) }}</td>
										<td>{{ it.uom }}</td>
										<td class="is-num">{{ money(it.rate) }}</td>
										<td class="is-num is-strong">{{ money(it.amount) }}</td>
										<td v-if="has_item_date" class="is-date">
											<InlineEdit
												v-if="item_date_field"
												fieldtype="Date"
												:model-value="it[item_date_field]"
												:label="item_date_label"
												:subtitle="it.item_name || it.item_code"
												:display="thai_date(it[item_date_field], { year: true })"
												:min="doc.date"
												required
												editable
												:save="(v) => save_item(it, v)"
											/>
											<template v-else>{{
												thai_date(it.schedule_date || it.delivery_date, {
													year: true,
												})
											}}</template>
										</td>
										<td v-if="is_mr" class="is-center">
											<span
												class="ss-checkmark"
												:class="{ 'is-on': it.custom_vat_nocal }"
											>
												<Icon
													v-if="it.custom_vat_nocal"
													name="check"
													:size="12"
													:stroke="3.2"
												/>
											</span>
										</td>
									</tr>
								</tbody>
							</table>
						</div>

						<!-- มือถือ: การ์ดรายการ -->
						<div v-else class="ss-list ss-list--form">
							<div
								v-for="(it, i) in doc.items"
								:key="i"
								class="ss-card"
								:style="{ '--i': Math.min(i, 12) }"
							>
								<div class="ss-doc-row">
									<span class="ss-doc-title">{{ it.item_name || it.item_code }}</span>
									<b class="ss-doc-money">{{ money(it.amount) }}</b>
								</div>
								<span class="ss-card-meta ss-item-code">{{ it.item_code }}</span>
								<span class="ss-card-meta"
									>{{ num(it.qty) }} {{ it.uom }} × {{ money(it.rate)
									}}<template
										v-if="!item_date_field && (it.schedule_date || it.delivery_date)"
									>
										· ต้องการ
										{{ thai_date(it.schedule_date || it.delivery_date) }}</template
									></span
								>
								<span v-if="item_date_field" class="ss-card-meta"
									>{{ item_date_label }}
									<InlineEdit
										fieldtype="Date"
										:model-value="it[item_date_field]"
										:label="item_date_label"
										:subtitle="it.item_name || it.item_code"
										:display="thai_date(it[item_date_field])"
										:min="doc.date"
										required
										editable
										:save="(v) => save_item(it, v)"
								/></span>
								<RichText
									v-if="has_desc(it)"
									:html="it.description"
									:lines="4"
									class="ss-item-desc"
								/>
								<div v-if="item_progress(it) || it.custom_vat_nocal" class="ss-chips">
									<span v-if="item_progress(it)" class="ss-chip">{{
										item_progress(it)
									}}</span>
									<span v-if="it.custom_vat_nocal" class="ss-chip">ไม่คิดภาษี</span>
								</div>
							</div>
						</div>

						<!-- ท้ายเอกสาร: หมายเหตุ/ตัวอักษร (ซ้าย) + สรุปยอด (ขวา) แบบระบบเต็ม -->
						<div class="ss-dv-foot">
							<div class="ss-dv-notes">
								<div v-if="doc.remarks || edit[remarks_field]">
									<span class="ss-field-label">หมายเหตุ</span>
									<InlineEdit
										v-if="edit[remarks_field]"
										:model-value="doc.remarks"
										label="หมายเหตุ"
										add_label=""
										multiline
										editable
										:save="(v) => save_field(remarks_field, v)"
										><div class="ss-text-block">{{ doc.remarks }}</div></InlineEdit
									>
									<div v-else class="ss-text-block">{{ doc.remarks }}</div>
								</div>
								<div v-if="is_mr" class="ss-dv-flags">
									<span class="ss-flag" :class="{ 'is-on': doc.included_vat }">
										<span class="ss-checkmark" :class="{ 'is-on': doc.included_vat }"
											><Icon
												v-if="doc.included_vat"
												name="check"
												:size="12"
												:stroke="3.2"
										/></span>
										มูลค่ารวมภาษี
									</span>
									<span class="ss-flag" :class="{ 'is-on': doc.vat_override }">
										<span class="ss-checkmark" :class="{ 'is-on': doc.vat_override }"
											><Icon
												v-if="doc.vat_override"
												name="check"
												:size="12"
												:stroke="3.2"
										/></span>
										แก้ไขภาษี
									</span>
								</div>
							</div>
							<div class="ss-totals">
								<div v-for="r in doc.summary.rows" :key="r.label">
									<span>{{ r.label }}</span
									><b>{{ money(r.value) }}</b>
								</div>
								<div class="is-grand">
									<span>{{ doc.summary.grand_label }}</span
									><b>{{ money(doc.summary.grand) }}</b>
								</div>
								<div v-if="doc.summary.in_words" class="ss-totals-words">
									({{ doc.summary.in_words }})
								</div>
								<template v-if="doc.summary.net !== undefined">
									<div v-for="d in doc.summary.deductions" :key="d.label" class="is-deduct">
										<span>{{ d.label }}</span
										><b>{{ money(d.value) }}</b>
									</div>
									<div class="is-net">
										<span>{{ doc.summary.net_label }}</span
										><b>{{ money(doc.summary.net) }}</b>
									</div>
								</template>
								<div v-if="doc.totals.outstanding_amount" class="is-due">
									<span>ค้าง{{ due_word }}</span
									><b>{{ money(doc.totals.outstanding_amount) }}</b>
								</div>
							</div>
						</div>
					</div>
				</div>
			</template>
		</div>

		<!-- sidebar ขวาแยกจากเนื้อหา: จอ ≥1480 กางค้างและดันเนื้อหา (html[data-rside]) จอเล็กกว่าเลื่อนทับพร้อมพื้นหลังมืด -->
		<Teleport to="#ss-layer">
			<Transition name="ss-rside-fade">
				<div v-if="side_open && !xl" class="ss-rside-backdrop" @click="side_open = false"></div>
			</Transition>
			<Transition name="ss-rside">
				<aside
					v-if="side_open && doc"
					class="ss-rside"
					:class="{ 'is-overlay': !xl }"
					aria-label="ข้อมูลเอกสาร"
				>
					<header class="ss-rside-head">
						<b>ข้อมูลเอกสาร</b>
						<button
							type="button"
							class="ss-icon-btn ss-icon-btn--sm"
							aria-label="ปิดแผง"
							@click="toggle_side"
						>
							<Icon name="x" :size="18" />
						</button>
					</header>
					<div class="ss-rside-body">
						<DocActivity
							ref="activity"
							:kind="params.kind"
							:name="params.name"
							:doctype="config.doctype"
						>
							<section v-if="related.length" class="ss-act-block">
								<h3>เอกสารที่เกี่ยวข้อง</h3>
								<div class="ss-flow">
									<button
										v-for="l in related"
										:key="l.doctype + l.name"
										type="button"
										class="ss-flow-item"
										@click="open_link(l)"
									>
										<Icon
											:name="l.dir === 'before' ? 'chevron-left' : 'chevron-right'"
											:size="16"
										/>
										<span class="ss-flow-main">
											<small>{{ link_label(l.doctype) }}</small>
											<b>{{ l.name }}</b>
										</span>
										<span class="ss-tag" :class="`tone-${l.status_tone}`">{{
											l.status_label
										}}</span>
									</button>
								</div>
							</section>
						</DocActivity>
					</div>
				</aside>
			</Transition>
		</Teleport>

		<Teleport to="#ss-layer">
			<Transition name="ss-bar">
				<div v-if="has_bar" class="ss-bottom-bar">
					<button
						v-if="doc.can_edit"
						type="button"
						class="ss-btn ss-btn--ghost ss-btn--lg"
						:class="{ 'ss-grow': !doc.can_submit }"
						@click="go(`${config.section}-form`, { kind: params.kind, name: params.name })"
					>
						<Icon name="pen" :size="17" /> แก้ไข
					</button>
					<button
						v-if="doc.can_submit"
						type="button"
						class="ss-btn ss-btn--primary ss-btn--lg ss-grow"
						:disabled="busy"
						@click="confirm = true"
					>
						ส่ง{{ config.label }}
					</button>
					<!-- เอกสารที่ส่งแล้ว: สร้างเอกสารถัดไป (ขอซื้อ → สั่งซื้อ → แจ้งหนี้, เสนอราคา → สั่งขาย → แจ้งหนี้) -->
					<button
						v-if="next_kind"
						type="button"
						class="ss-btn ss-btn--primary ss-btn--lg ss-grow"
						@click="
							go(`${config.section}-form`, {
								kind: next_kind,
								name: 'new',
								source: params.name,
							})
						"
					>
						<Icon name="plus" :size="18" :stroke="2.4" /> สร้าง{{ DOC_KINDS[next_kind].label }}
					</button>
				</div>
			</Transition>
		</Teleport>

		<Sheet :open="confirm" :title="`ส่ง${config.label}`" :subtitle="params.name" @close="confirm = false">
			<p class="ss-muted">
				ส่งแล้วแก้ได้เฉพาะบางช่อง (มีรูปดินสอ) เช่น กำหนดส่ง เลขที่อ้างอิง
				ที่เหลือต้องยกเลิกแล้วแก้ในระบบเต็ม
			</p>
			<div v-if="doc" class="ss-facts ss-facts--grid">
				<div class="ss-fact">
					<span>{{ config.party || "เรื่อง" }}</span
					><b>{{ doc.party || doc.title }}</b>
				</div>
				<div class="ss-fact">
					<span>ยอดรวม</span><b>{{ money(doc.summary.grand) }}</b>
				</div>
			</div>
			<template #footer>
				<button
					type="button"
					class="ss-btn ss-btn--primary ss-btn--block ss-btn--lg"
					:disabled="busy"
					@click="submit"
				>
					<span v-if="busy" class="ss-spinner"></span>
					<template v-else>ยืนยันส่ง</template>
				</button>
			</template>
		</Sheet>

		<PdfViewer
			:open="pdf"
			:url="doc?.pdf_url"
			:name="params.name"
			:title="config.label"
			@close="pdf = false"
		/>
	</div>
</template>

<script setup>
import { computed, inject, onBeforeUnmount, ref, watch } from "vue";
import Icon from "../components/Icon.vue";
import TopBar from "../components/TopBar.vue";
import Skeleton from "../components/Skeleton.vue";
import Sheet from "../components/Sheet.vue";
import PdfViewer from "../components/PdfViewer.vue";
import RichText from "../components/RichText.vue";
import DocActivity from "./DocActivity.vue";
import InlineEdit from "../components/InlineEdit.vue";
import { use_shortcuts } from "../shortcuts.js";
import { DOC_KINDS, in_app, open_doc } from "./kinds.js";
import {
	call,
	celebrate,
	desk_url,
	go,
	html_text,
	money,
	num,
	post,
	show_error,
	state,
	thai_date,
	toast,
} from "../api.js";

const reload_summary = inject("reload_summary");
const params = state.route.params;
const config = DOC_KINDS[params.kind] || DOC_KINDS.po;

const doc = ref(null);
const busy = ref(false);
const confirm = ref(false);
const pdf = ref(false);

// แท็บเล็ต/จอใหญ่: ตารางรายการ + ช่องข้อมูลหลายคอลัมน์, มือถือ: การ์ด
const mq_wide = window.matchMedia("(min-width: 768px)");
const wide = ref(mq_wide.matches);
const on_media = () => (wide.value = mq_wide.matches);
mq_wide.addEventListener("change", on_media);
onBeforeUnmount(() => mq_wide.removeEventListener("change", on_media));

const is_mr = params.kind === "mr";
// รายละเอียดที่ต่างจากชื่อรายการ (ERPNext ตั้ง description = ชื่อรายการเป็นค่าเริ่มต้น)
const has_desc = (it) => {
	const text = html_text(it.description);
	return !!text && text !== it.item_name;
};
const due_word = config.section === "buy" ? "จ่าย" : "รับ";
const overdue = computed(
	() =>
		doc.value?.docstatus === 1 &&
		doc.value.due &&
		new Date(doc.value.due) < new Date(new Date().toDateString()) &&
		(doc.value.totals.outstanding_amount > 0 || doc.value.status_tone === "amber")
);
const related = computed(() =>
	doc.value
		? [
				...doc.value.before.map((x) => ({ ...x, dir: "before" })),
				...doc.value.after.map((x) => ({ ...x, dir: "after" })),
		  ]
		: []
);
const has_item_date = computed(
	() => !!item_date_field.value || doc.value?.items.some((it) => it.schedule_date || it.delivery_date)
);

// ---------------------------------------------------------------- แก้ไขหลังส่ง (ช่อง Allow on Submit, site_docs.AFTER_SUBMIT)
const activity = ref(null);
const after = computed(() => doc.value?.after_submit || null);
const edit = computed(() => Object.fromEntries((after.value?.fields || []).map((f) => [f.fieldname, f])));
const due_field = computed(() => after.value?.due_field);
const remarks_field = computed(() => after.value?.remarks_field);
// ช่องที่ไม่มีที่แสดงในหน้าดู: ต่อท้ายช่องข้อมูล
const extra_fields = computed(() =>
	(after.value?.fields || []).filter(
		(f) =>
			![due_field.value, remarks_field.value].includes(f.fieldname) &&
			!(f.fieldname === "title" && !config.party)
	)
);
const item_date_field = computed(
	() => (after.value?.items || []).find((f) => ["schedule_date", "delivery_date"].includes(f)) || null
);
const item_date_label = computed(() => (item_date_field.value === "delivery_date" ? "กำหนดส่ง" : "ต้องการ"));

async function save_after(values, items, apply) {
	try {
		doc.value = await post("consbiz.site_docs.save_after_submit", {
			kind: params.kind,
			name: params.name,
			values,
			items,
			apply_items: apply ? 1 : 0,
			modified: after.value?.modified,
		});
		toast("บันทึกแล้ว", "success");
		activity.value?.reload();
	} catch (error) {
		show_error(error);
		throw error;
	}
}
const save_field = (field, value, apply) => save_after({ [field]: value }, null, apply);
const save_item = (it, value) => save_after({}, [{ name: it.name, [item_date_field.value]: value }]);
// ---------------------------------------------------------------- sidebar ขวา
const SIDE_KEY = "consbiz.site.doc_side";
const mq_xl = window.matchMedia("(min-width: 1480px)");
const xl = ref(mq_xl.matches);
const saved_side = (() => {
	try {
		return localStorage.getItem(SIDE_KEY);
	} catch {
		return null;
	}
})();
// จอใหญ่: ค่าเริ่มต้นเปิด (จำในเครื่อง) จอเล็ก: ปิดจนกดปุ่ม
const side_open = ref(xl.value && saved_side !== "closed");
function toggle_side() {
	side_open.value = !side_open.value;
	if (xl.value) {
		try {
			localStorage.setItem(SIDE_KEY, side_open.value ? "open" : "closed");
		} catch {
			/* เก็บไม่ได้: ใช้ค่าเริ่มต้น */
		}
	}
}
const on_xl = () => {
	xl.value = mq_xl.matches;
	side_open.value = xl.value && saved_side !== "closed";
};
mq_xl.addEventListener("change", on_xl);
const on_key = (e) => e.key === "Escape" && !xl.value && (side_open.value = false);
window.addEventListener("keydown", on_key);
watch(
	() => side_open.value && xl.value,
	(push) => {
		if (push) document.documentElement.dataset.rside = "open";
		else delete document.documentElement.dataset.rside;
	},
	{ immediate: true }
);
onBeforeUnmount(() => {
	mq_xl.removeEventListener("change", on_xl);
	window.removeEventListener("keydown", on_key);
	delete document.documentElement.dataset.rside;
});

// เอกสารถัดไปสร้างได้เฉพาะชนิดที่แอปนี้ดูแล (หน้างานขอซื้อได้ สั่งซื้อทำที่แอปออฟฟิศ)
const next_kind = computed(() =>
	doc.value?.next_kind && in_app(doc.value.next_kind) ? doc.value.next_kind : null
);

const has_bar = computed(
	() => !!(doc.value && (doc.value.can_edit || doc.value.can_submit || next_kind.value))
);

const progress = computed(() =>
	doc.value?.docstatus === 1
		? (config.progress || [])
				// null = ไม่มีขั้นนี้ (สั่งซื้อของใบขอซื้อผู้ว่าจ้างจัดหา)
				.filter(([field]) => doc.value.progress[field] != null)
				.map(([field, label]) => ({ label, value: doc.value.progress[field] || 0 }))
		: []
);

const LINK_LABELS = {
	"Material Request": "ใบขอซื้อ",
	"Purchase Order": "ใบสั่งซื้อ",
	"Purchase Receipt": "ใบรับของ",
	"Purchase Invoice": "ใบแจ้งหนี้ซื้อ",
	Quotation: "ใบเสนอราคา",
	"Sales Order": "ใบสั่งขาย",
	"Delivery Note": "ใบส่งของ",
	"Sales Invoice": "ใบแจ้งหนี้ขาย",
	"Payment Entry": "รับ/จ่ายเงิน",
};
const link_label = (doctype) => LINK_LABELS[doctype] || doctype;

// ปริมาณที่ดำเนินการแล้วของแต่ละรายการ
// ช่องปริมาณที่เกี่ยวกับเอกสารแต่ละชนิด (แถวของ SO มี ordered_qty ของการผลิต ไม่ใช่การสั่งซื้อ)
const ITEM_PROGRESS = {
	mr: [
		["ordered_qty", "สั่งแล้ว"],
		["received_qty", "รับแล้ว"],
	],
	po: [["received_qty", "รับแล้ว"]],
	so: [["delivered_qty", "ส่งมอบแล้ว"]],
};
function item_progress(it) {
	const pairs = ITEM_PROGRESS[params.kind] || [];
	if (doc.value.docstatus !== 1) return "";
	return pairs
		.filter(([field]) => it[field] !== undefined && it[field] !== null)
		.map(([field, label]) => `${label} ${num(it[field])}/${num(it.qty)}`)
		.join(" · ");
}

// เอกสารจัดซื้อ/ขาย: ชนิดที่แอปนี้ดูแลเปิดในแอป ชนิดอื่นไปแอปที่ดูแล (open_doc) ที่เหลือ (ใบรับของ, ใบส่งของ, รับ/จ่ายเงิน) เปิดในระบบเต็ม
function open_link(l) {
	if (l.kind) open_doc(l.kind, l.name);
	else window.location.href = desk_url(l.doctype, l.name);
}

async function load() {
	try {
		doc.value = await call("consbiz.site_docs.get_doc", { kind: params.kind, name: params.name });
	} catch (error) {
		show_error(error);
	}
}

async function submit() {
	busy.value = true;
	try {
		await post("consbiz.site_docs.submit_doc", { kind: params.kind, name: params.name });
		confirm.value = false;
		await celebrate(`ส่ง${config.label}แล้ว`, params.name);
		reload_summary();
		await load();
	} catch (error) {
		show_error(error);
	} finally {
		busy.value = false;
	}
}

load();

// คีย์ลัด (แอปออฟฟิศ): e แก้ไขร่าง, p PDF, i แผงข้อมูลเอกสาร
use_shortcuts({
	e: () => doc.value?.can_edit && go(`${config.section}-form`, { kind: params.kind, name: params.name }),
	p: () => doc.value && (pdf.value = true),
	i: () => doc.value && toggle_side(),
});
</script>
