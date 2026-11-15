<!-- ใบกำกับภาษีขาย / ซื้อ (Sales / Purchase Tax Invoice ของ erpnext_thailand, ระบบสร้างจาก GL ภาษี) ดู + แก้ช่องที่ยอมให้แก้หลังยืนยัน:
     ภาษีซื้อ = เลขที่/วันที่ใบกำกับของผู้ขาย + ยื่นล่าช้า (เดือน), ภาษีขาย = ยื่นล่าช้า (เดือนที่ยื่น = วันที่ + จำนวนเดือน)
     URL: acc-tax-doc/<หน้ารายการ>/<เลขที่> API consbiz/accounting_app.py -->
<template>
	<div>
		<TopBar :title="title" :subtitle="doc?.party_name" :back_to="params.kind" />

		<div class="ss-content">
			<div v-if="doc" class="ss-list-head">
				<StatusTabs v-model="tab" :options="TABS" />
				<div class="ss-list-tools">
					<a
						class="ss-icon-btn"
						:href="desk_url(doc.doctype, doc.name)"
						title="เปิดในระบบเต็ม"
						aria-label="เปิดในระบบเต็ม"
						><Icon name="external" :size="17"
					/></a>
					<button
						v-if="edit.length"
						type="button"
						class="ss-btn ss-btn--primary ss-list-create"
						:disabled="busy || !dirty"
						@click="save"
					>
						<Icon name="save" :size="18" /> <span>บันทึก</span>
					</button>
				</div>
			</div>

			<Skeleton v-if="!doc" :rows="5" />
			<template v-else>
				<section class="ss-card ss-form">
					<div class="ss-doc-head-top">
						<span class="ss-tag" :class="`tone-${doc.status_tone}`">{{
							doc.status_label
						}}</span>
						<span class="ss-doc-date">{{ doc.name }}</span>
					</div>
					<div class="ss-facts ss-facts--grid">
						<div v-for="f in facts" :key="f.label" class="ss-fact">
							<span>{{ f.label }}</span
							><b>{{ f.value }}</b>
						</div>
						<div v-if="doc.voucher_no" class="ss-fact">
							<span>เอกสารต้นทาง</span>
							<b
								><a href="#" @click.prevent="open_voucher">{{
									doc.voucher_no
								}}</a></b
							>
						</div>
					</div>
					<div v-if="edit.length" class="ss-form-row">
						<label v-if="edit.includes('number')" class="ss-field">
							<span class="ss-field-label"
								>เลขที่ใบกำกับภาษีของผู้ขาย<em>*</em></span
							>
							<input v-model="form.number" class="ss-input" />
						</label>
						<label v-if="edit.includes('date')" class="ss-field">
							<span class="ss-field-label">วันที่ใบกำกับภาษี<em>*</em></span>
							<DateInput v-model="form.date" label="วันที่ใบกำกับภาษี" />
						</label>
						<label class="ss-field">
							<span class="ss-field-label">ยื่นล่าช้า</span>
							<SelectBox
								v-model="form.months_delayed"
								:options="DELAYS"
								label="ยื่นล่าช้า"
							/>
						</label>
					</div>
					<p v-if="edit.length" class="ss-muted">
						ใบกำกับภาษีซื้อที่ได้รับช้า ยื่นในเดือนถัดไปได้ไม่เกิน 6 เดือน เดือนที่ยื่น
						= วันที่ใบกำกับ + จำนวนเดือน
					</p>
				</section>
			</template>
		</div>
	</div>
</template>

<script setup>
import { computed, ref } from "vue";
import DateInput from "../../../shared/components/DateInput.vue";
import Icon from "../../../shared/components/Icon.vue";
import SelectBox from "../../../shared/components/SelectBox.vue";
import Skeleton from "../../../shared/components/Skeleton.vue";
import StatusTabs from "../../../shared/components/StatusTabs.vue";
import TopBar from "../../../shared/components/TopBar.vue";
import { open_doc } from "../../../shared/docs/kinds.js";
import {
	back,
	call,
	desk_url,
	go,
	money,
	num,
	post,
	show_error,
	state,
	thai_date,
	toast,
} from "../../../shared/api.js";
import { API } from "./kinds.js";

const params = state.route.params;
const type = params.kind === "acc-purchase-tax" ? "purchase" : "sales";
const label = type === "sales" ? "ใบกำกับภาษีขาย" : "ใบกำกับภาษีซื้อ";
const TABS = [{ value: "detail", label }];
const DELAYS = [0, 1, 2, 3, 4, 5, 6].map((n) => ({
	value: n,
	label: n ? `${n} เดือน` : "ไม่ล่าช้า",
}));

const tab = ref("detail");
const doc = ref(null);
const edit = ref([]);
const form = ref({});
const busy = ref(false);

const title = computed(() => `${label} ${params.name}`);
const facts = computed(() => {
	const d = doc.value;
	return [
		[type === "sales" ? "ลูกค้า" : "ผู้ขาย", d.party_name || d.party],
		[
			"เลขประจำตัวผู้เสียภาษี",
			`${d.tax_id || "—"}${d.branch_code ? ` · สาขา ${d.branch_code}` : ""}`,
		],
		...(type === "purchase" && !edit.value.length ? [["เลขที่ใบกำกับ", d.number || "—"]] : []),
		["วันที่ใบกำกับ", d.date ? thai_date(d.date, { year: true }) : "—"],
		["เดือนที่ยื่น", d.report_date ? thai_date(d.report_date, { year: true }) : "—"],
		["มูลค่าก่อนภาษี", money(d.tax_base)],
		[`ภาษี${d.tax_percent ? ` ${num(d.tax_percent)}%` : ""}`, money(d.tax_amount)],
		["บริษัท", d.company],
		...(d.company_tax_address ? [["ที่อยู่บริษัท", d.company_tax_address]] : []),
	].map(([label, value]) => ({ label, value }));
});
const dirty = computed(
	() =>
		!!doc.value &&
		edit.value.some((f) => String(form.value[f] ?? "") !== String(doc.value[f] ?? ""))
);

function apply(result) {
	doc.value = result.doc;
	edit.value = result.edit || [];
	form.value = Object.fromEntries(edit.value.map((f) => [f, result.doc[f]]));
}

function open_voucher() {
	const d = doc.value;
	if (d.voucher_kind) open_doc(d.voucher_kind, d.voucher_no);
	else if (d.voucher_type === "Payment Entry")
		go("acc-payment", {
			kind: type === "sales" ? "acc-receipts" : "acc-payments",
			name: d.voucher_no,
		});
	else window.location.href = desk_url(d.voucher_type, d.voucher_no);
}

async function save() {
	busy.value = true;
	try {
		const values = Object.fromEntries(
			edit.value
				.filter((f) => String(form.value[f] ?? "") !== String(doc.value[f] ?? ""))
				.map((f) => [f, form.value[f]])
		);
		apply(
			await post(`${API}.save_tax_invoice`, {
				type,
				name: params.name,
				values: JSON.stringify(values),
			})
		);
		toast("บันทึกแล้ว", "success");
	} catch (e) {
		show_error(e);
	} finally {
		busy.value = false;
	}
}

async function load() {
	try {
		apply(await call(`${API}.get_tax_invoice`, { type, name: params.name }));
	} catch (e) {
		show_error(e);
		back(params.kind);
	}
}
load();
</script>
