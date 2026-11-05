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
				<!-- หัวเอกสาร: คู่ค้า + สถานะ / ช่องข้อมูลเรียงเป็นตาราง (จอกว้างหลายคอลัมน์) -->
				<section class="ss-dv-head">
					<div class="ss-dv-title">
						<div class="ss-dv-party">
							<small>{{ config.party || "เรื่อง" }}</small>
							<b>{{ doc.party || doc.title || doc.name }}</b>
						</div>
						<span class="ss-tag ss-tag--lg" :class="`tone-${doc.status_tone}`">{{
							doc.status_label
						}}</span>
					</div>
					<!-- มือถือ: ยอดเด่น (จอกว้างอยู่ในตารางช่องข้อมูลและท้ายตารางรายการ) -->
					<div v-if="!wide && has_money" class="ss-doc-total">
						<div>
							<small>ยอดรวม</small>
							<b>{{ money(grand_total) }}</b>
						</div>
						<div v-if="doc.totals.outstanding_amount" class="is-due">
							<small>ค้าง{{ due_word }}</small>
							<b>{{ money(doc.totals.outstanding_amount) }}</b>
						</div>
					</div>
					<dl class="ss-dv-fields">
						<div>
							<dt>เลขที่</dt>
							<dd>{{ doc.name }}</dd>
						</div>
						<div>
							<dt>วันที่</dt>
							<dd>{{ thai_date(doc.date, { year: true }) }}</dd>
						</div>
						<div v-if="doc.due">
							<dt>{{ config.due || "ต้องการภายใน" }}</dt>
							<dd :class="{ 'is-due': overdue }">{{ thai_date(doc.due, { year: true }) }}</dd>
						</div>
						<div v-if="doc.bill_no">
							<dt>เลขที่บิลผู้ขาย</dt>
							<dd>{{ doc.bill_no }}</dd>
						</div>
						<div v-if="doc.project">
							<dt>โครงการ</dt>
							<dd>{{ doc.project }}</dd>
						</div>
						<div>
							<dt>ผู้ทำเอกสาร</dt>
							<dd>{{ doc.owner_name }}</dd>
						</div>
						<template v-if="wide && has_money">
							<div>
								<dt>ยอดรวมทั้งสิ้น</dt>
								<dd class="is-money">{{ money(grand_total) }}</dd>
							</div>
							<div v-if="doc.totals.outstanding_amount">
								<dt>ค้าง{{ due_word }}</dt>
								<dd class="is-money is-due">{{ money(doc.totals.outstanding_amount) }}</dd>
							</div>
						</template>
						<div v-for="p in progress" :key="p.label" class="ss-dv-progress">
							<dt>{{ p.label }}</dt>
							<dd>
								<span class="ss-table-pct">
									<i><b :style="{ width: `${Math.min(100, p.value)}%` }"></b></i>
									{{ Math.round(p.value) }}%
								</span>
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

						<!-- จอกว้าง: ตารางรายการ + สรุปยอดท้ายตาราง แบบใบเอกสาร -->
						<div v-if="wide" class="ss-table-wrap">
							<table class="ss-table ss-table--doc">
								<thead>
									<tr>
										<th class="is-idx">#</th>
										<th>รายการ</th>
										<th class="is-num">จำนวน</th>
										<th>หน่วย</th>
										<th v-if="has_money" class="is-num">ราคา/หน่วย</th>
										<th v-if="has_money" class="is-num">จำนวนเงิน</th>
										<th v-if="has_item_date">กำหนด</th>
										<th v-if="item_cols.length">ดำเนินการแล้ว</th>
									</tr>
								</thead>
								<tbody>
									<tr v-for="(it, i) in doc.items" :key="i" class="is-static">
										<td class="is-idx">{{ i + 1 }}</td>
										<td class="is-item">
											<b>{{ it.item_name || it.item_code }}</b>
											<small v-if="it.item_name && it.item_name !== it.item_code">{{
												it.item_code
											}}</small>
										</td>
										<td class="is-num">{{ num(it.qty) }}</td>
										<td>{{ it.uom }}</td>
										<td v-if="has_money" class="is-num">{{ money(it.rate) }}</td>
										<td v-if="has_money" class="is-num is-strong">
											{{ money(it.amount) }}
										</td>
										<td v-if="has_item_date" class="is-date">
											{{ thai_date(it.schedule_date || it.delivery_date) }}
										</td>
										<td v-if="item_cols.length">
											<span
												v-for="c in item_cols"
												:key="c.field"
												class="ss-dv-done"
												:class="{ 'is-full': Number(it[c.field]) >= Number(it.qty) }"
												>{{ c.label }} {{ num(it[c.field] || 0) }}/{{
													num(it.qty)
												}}</span
											>
										</td>
									</tr>
								</tbody>
								<tfoot v-if="has_money">
									<tr>
										<td :colspan="foot_span"></td>
										<th>รวมเป็นเงิน</th>
										<td class="is-num">{{ money(doc.totals.total) }}</td>
										<td
											v-if="has_item_date || item_cols.length"
											:colspan="tail_span"
										></td>
									</tr>
									<tr v-if="doc.totals.discount_amount">
										<td :colspan="foot_span"></td>
										<th>ส่วนลด</th>
										<td class="is-num">−{{ money(doc.totals.discount_amount) }}</td>
										<td
											v-if="has_item_date || item_cols.length"
											:colspan="tail_span"
										></td>
									</tr>
									<tr v-for="t in doc.taxes" :key="t.description">
										<td :colspan="foot_span"></td>
										<th>
											{{ t.description
											}}<template v-if="t.rate"> {{ t.rate }}%</template>
										</th>
										<td class="is-num">{{ money(t.amount) }}</td>
										<td
											v-if="has_item_date || item_cols.length"
											:colspan="tail_span"
										></td>
									</tr>
									<tr class="is-grand">
										<td :colspan="foot_span"></td>
										<th>ยอดรวมทั้งสิ้น</th>
										<td class="is-num">{{ money(grand_total) }}</td>
										<td
											v-if="has_item_date || item_cols.length"
											:colspan="tail_span"
										></td>
									</tr>
								</tfoot>
							</table>
						</div>

						<!-- มือถือ: การ์ดรายการ + สรุปยอด -->
						<template v-else>
							<div class="ss-list ss-list--form">
								<div
									v-for="(it, i) in doc.items"
									:key="i"
									class="ss-card"
									:style="{ '--i': Math.min(i, 12) }"
								>
									<div class="ss-doc-row">
										<span class="ss-doc-title">{{ it.item_name || it.item_code }}</span>
										<b v-if="has_money" class="ss-doc-money">{{ money(it.amount) }}</b>
									</div>
									<span class="ss-card-meta"
										>{{ num(it.qty) }} {{ it.uom
										}}<template v-if="has_money"> × {{ money(it.rate) }}</template
										><template v-if="it.schedule_date || it.delivery_date">
											· ส่ง
											{{ thai_date(it.schedule_date || it.delivery_date) }}</template
										></span
									>
									<div v-if="item_progress(it)" class="ss-chips">
										<span class="ss-chip">{{ item_progress(it) }}</span>
									</div>
								</div>
							</div>
							<div v-if="has_money" class="ss-totals">
								<div v-if="doc.totals.total !== undefined">
									<span>รวมเป็นเงิน</span><b>{{ money(doc.totals.total) }}</b>
								</div>
								<div v-if="doc.totals.discount_amount">
									<span>ส่วนลด</span><b>−{{ money(doc.totals.discount_amount) }}</b>
								</div>
								<div v-for="t in doc.taxes" :key="t.description">
									<span
										>{{ t.description
										}}<template v-if="t.rate"> {{ t.rate }}%</template></span
									><b>{{ money(t.amount) }}</b>
								</div>
								<div class="is-grand">
									<span>ยอดรวมทั้งสิ้น</span><b>{{ money(grand_total) }}</b>
								</div>
							</div>
						</template>
					</div>

					<aside v-if="related.length || doc.remarks" class="ss-dv-side">
						<template v-if="related.length">
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
						</template>
						<template v-if="doc.remarks">
							<h2
								class="ss-section-title"
								:class="{ 'ss-section-title--first': !related.length }"
							>
								หมายเหตุ
							</h2>
							<div class="ss-text-block">{{ doc.remarks }}</div>
						</template>
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
					<span>ยอดรวม</span><b>{{ money(doc.totals.grand_total) }}</b>
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

// ใบขอซื้อไม่มีราคา/ยอดเงิน
const has_money = params.kind !== "mr";
const due_word = config.section === "buy" ? "จ่าย" : "รับ";
const grand_total = computed(() => doc.value?.totals.rounded_total || doc.value?.totals.grand_total || 0);
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
// คอลัมน์ "ดำเนินการแล้ว" ของตาราง (เฉพาะเอกสารที่ส่งแล้ว)
const item_cols = computed(() =>
	doc.value?.docstatus === 1
		? (ITEM_PROGRESS[params.kind] || [])
				.filter(([field]) =>
					doc.value.items.some((it) => it[field] !== undefined && it[field] !== null)
				)
				.map(([field, label]) => ({ field, label }))
		: []
);
// ท้ายตาราง: ป้ายอยู่ใต้คอลัมน์ราคา ยอดอยู่ใต้คอลัมน์จำนวนเงิน
const foot_span = 4;
const tail_span = computed(() => (has_item_date.value ? 1 : 0) + (item_cols.value.length ? 1 : 0));

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
