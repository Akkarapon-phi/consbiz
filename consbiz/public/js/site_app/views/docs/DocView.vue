<template>
	<!-- รายละเอียดเอกสารจัดซื้อ/ขาย: หัวเอกสาร, ความคืบหน้า, รายการ, ยอดรวม, เอกสารต้นทาง/ปลายทาง, PDF, ส่งเอกสาร -->
	<div :class="{ 'ss-has-bar': has_bar }">
		<TopBar :title="config.label" :subtitle="params.name" :back_to="params.kind">
			<template #actions>
				<button
					v-if="doc"
					type="button"
					class="ss-icon-btn"
					aria-label="PDF / แชร์"
					title="PDF / แชร์"
					@click="pdf = true"
				>
					<Icon name="file" :size="19" />
				</button>
				<a
					class="ss-icon-btn"
					:href="desk_url(config.doctype, params.name)"
					aria-label="เปิดในระบบเต็ม"
					title="เปิดในระบบเต็ม"
				>
					<Icon name="external" :size="19" />
				</a>
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
							<dd>{{ doc.party || doc.title || doc.name }}</dd>
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
						<div v-if="doc.due">
							<dt>{{ config.due || "วันที่ต้องการ" }}</dt>
							<dd :class="{ 'is-due': overdue }">{{ thai_date(doc.due, { year: true }) }}</dd>
						</div>
						<div v-if="doc.po_no">
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
											<small
												v-if="
													it.description && strip(it.description) !== it.item_name
												"
												class="is-desc"
												>{{ strip(it.description) }}</small
											>
										</td>
										<td class="is-num">{{ num(it.qty) }}</td>
										<td>{{ it.uom }}</td>
										<td class="is-num">{{ money(it.rate) }}</td>
										<td class="is-num is-strong">{{ money(it.amount) }}</td>
										<td v-if="has_item_date" class="is-date">
											{{
												thai_date(it.schedule_date || it.delivery_date, {
													year: true,
												})
											}}
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
								<span class="ss-card-meta"
									>{{ num(it.qty) }} {{ it.uom }} × {{ money(it.rate)
									}}<template v-if="it.schedule_date || it.delivery_date">
										· ต้องการ
										{{ thai_date(it.schedule_date || it.delivery_date) }}</template
									></span
								>
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
								<div v-if="doc.remarks">
									<span class="ss-field-label">หมายเหตุ</span>
									<div class="ss-text-block">{{ doc.remarks }}</div>
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

					<aside v-if="related.length" class="ss-dv-side">
						<h2 class="ss-section-title ss-section-title--first">เอกสารที่เกี่ยวข้อง</h2>
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
					</aside>
				</div>
			</template>
		</div>

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
						v-if="doc.next_kind"
						type="button"
						class="ss-btn ss-btn--primary ss-btn--lg ss-grow"
						@click="
							go(`${config.section}-form`, {
								kind: doc.next_kind,
								name: 'new',
								source: params.name,
							})
						"
					>
						<Icon name="plus" :size="18" :stroke="2.4" /> สร้าง{{
							DOC_KINDS[doc.next_kind].label
						}}
					</button>
				</div>
			</Transition>
		</Teleport>

		<Sheet :open="confirm" :title="`ส่ง${config.label}`" :subtitle="params.name" @close="confirm = false">
			<p class="ss-muted">ส่งแล้วแก้ไขไม่ได้ ต้องยกเลิกแล้วแก้ไขในระบบเต็ม</p>
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
import { computed, inject, onBeforeUnmount, ref } from "vue";
import Icon from "../../components/Icon.vue";
import TopBar from "../../components/TopBar.vue";
import Skeleton from "../../components/Skeleton.vue";
import Sheet from "../../components/Sheet.vue";
import PdfViewer from "../../components/PdfViewer.vue";
import { DOC_KINDS } from "../../sections.js";
import { call, celebrate, desk_url, go, money, num, post, show_error, state, thai_date } from "../../api.js";

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
const strip = (html) =>
	String(html || "")
		.replace(/<[^>]*>/g, " ")
		.replace(/\s+/g, " ")
		.trim();
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
const has_item_date = computed(() => doc.value?.items.some((it) => it.schedule_date || it.delivery_date));
const has_bar = computed(
	() => !!(doc.value && (doc.value.can_edit || doc.value.can_submit || doc.value.next_kind))
);

const progress = computed(() =>
	doc.value?.docstatus === 1
		? (config.progress || []).map(([field, label]) => ({ label, value: doc.value.progress[field] || 0 }))
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

// เอกสารจัดซื้อ/ขายเปิดในแอป ที่เหลือ (ใบรับของ, ใบส่งของ, รับ/จ่ายเงิน) เปิดในระบบเต็ม
function open_link(l) {
	if (l.kind) go(`${DOC_KINDS[l.kind].section}-doc`, { kind: l.kind, name: l.name });
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
</script>
