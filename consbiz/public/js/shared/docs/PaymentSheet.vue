<!-- รับชำระ (ใบแจ้งหนี้ขาย) / จ่ายชำระ (ใบแจ้งหนี้ซื้อ) ต่อจากหน้าดูใบแจ้งหนี้ (DocView.vue, doc.can_pay)
     = Payment Entry ของ ERPNext (consbiz/accounting_app.py `payment_defaults` / `make_payment`)
     รายการหักเติมจากใบแจ้งหนี้ (หัก ณ ที่จ่าย / เงินประกันผลงาน) ยอดรับ/จ่ายจริง = ยอดตัดหนี้ - รายการหัก
     มีสิทธิ์ Submit = ยืนยันลงบัญชีทันที ไม่มี = ร่างไว้ให้ฝ่ายบัญชี -->
<template>
	<Sheet :open="open" :title="word" :subtitle="name" @close="emit('close')">
		<Skeleton v-if="!form" :rows="4" />
		<div v-else class="ss-form">
			<div class="ss-facts ss-facts--grid">
				<div class="ss-fact">
					<span>{{ receive ? "ลูกค้า" : "ผู้ขาย" }}</span
					><b>{{ info.party_name || info.party }}</b>
				</div>
				<div class="ss-fact">
					<span>ยอดค้าง</span><b>{{ money(info.outstanding) }}</b>
				</div>
			</div>
			<div class="ss-form-row">
				<label class="ss-field">
					<span class="ss-field-label"
						>วันที่{{ receive ? "รับ" : "จ่าย" }}เงิน<em>*</em></span
					>
					<DateInput v-model="form.posting_date" label="วันที่" />
				</label>
				<label class="ss-field">
					<span class="ss-field-label">ยอดตัดหนี้<em>*</em></span>
					<MoneyInput v-model="form.allocated" class="ss-input" />
				</label>
			</div>
			<label class="ss-field">
				<span class="ss-field-label">บัญชีเงินสด/ธนาคาร<em>*</em></span>
				<SelectBox
					v-model="form.account"
					:options="accounts"
					label="บัญชีเงินสด/ธนาคาร"
					placeholder="เลือกบัญชี"
				/>
			</label>
			<div class="ss-form-row">
				<label class="ss-field">
					<span class="ss-field-label">วิธีชำระเงิน</span>
					<SelectBox
						v-model="form.mode_of_payment"
						:options="modes"
						label="วิธีชำระเงิน"
						placeholder="ไม่ระบุ"
					/>
				</label>
				<label class="ss-field">
					<span class="ss-field-label">เลขที่อ้างอิง (เช็ค/โอน)</span>
					<input v-model="form.reference_no" class="ss-input" placeholder="-" />
				</label>
			</div>

			<div v-if="form.deductions.length" class="ss-table-wrap">
				<table class="ss-table ss-table--list">
					<thead>
						<tr>
							<th>รายการหัก</th>
							<th class="is-num">ยอด</th>
							<th></th>
						</tr>
					</thead>
					<tbody>
						<tr v-for="(d, i) in form.deductions" :key="i" class="is-static">
							<td>
								<span class="ss-cell-main">{{ d.description || d.account }}</span>
								<small v-if="d.wht"
									>ฐาน {{ money(d.wht_base) }} x {{ num(d.wht_rate) }}%</small
								>
								<small v-else>{{ d.account }}</small>
							</td>
							<td class="is-num">
								<MoneyInput
									v-model="d.amount"
									class="ss-input"
									@update:model-value="(v) => rebase(d, v)"
								/>
							</td>
							<td class="col-nowrap">
								<button
									type="button"
									class="ss-icon-btn"
									title="ไม่หักรายการนี้"
									aria-label="ไม่หักรายการนี้"
									@click="form.deductions.splice(i, 1)"
								>
									<Icon name="trash" :size="16" />
								</button>
							</td>
						</tr>
					</tbody>
				</table>
			</div>
			<p v-else-if="info.paid_before" class="ss-muted">
				ใบนี้มีการ{{ word }}ไปแล้วบางส่วน ระบบไม่เติมรายการหักให้ซ้ำ
				(หักเพิ่มได้ในระบบเต็ม)
			</p>

			<template v-if="info.needs_tax_invoice">
				<label class="ss-checkline">
					<input v-model="form.has_tax_invoice" type="checkbox" class="ss-check" />
					<span
						>ได้รับใบกำกับภาษีจากผู้ขายแล้ว (ภาษีซื้อรอเรียกเก็บ
						{{ money(info.undue_tax) }})</span
					>
				</label>
				<div v-if="form.has_tax_invoice" class="ss-form-row">
					<label class="ss-field">
						<span class="ss-field-label">เลขที่ใบกำกับภาษี<em>*</em></span>
						<input v-model="form.tax_invoice_number" class="ss-input" />
					</label>
					<label class="ss-field">
						<span class="ss-field-label">วันที่ใบกำกับภาษี<em>*</em></span>
						<DateInput v-model="form.tax_invoice_date" label="วันที่ใบกำกับภาษี" />
					</label>
				</div>
				<p v-else class="ss-muted">
					ยังไม่ได้รับ = ภาษีซื้อค้างเป็นรอเรียกเก็บ ล้างภายหลังในระบบเต็ม
				</p>
			</template>
			<p v-else-if="receive && info.undue_tax" class="ss-muted">
				ภาษีขายรอเรียกเก็บ {{ money(info.undue_tax) }} ถึงกำหนดเมื่อรับเงิน
				ระบบออกใบกำกับภาษีให้อัตโนมัติ
			</p>

			<div class="ss-facts ss-facts--grid">
				<div class="ss-fact">
					<span>รายการหัก</span><b>{{ money(deducted) }}</b>
				</div>
				<div class="ss-fact">
					<span>ยอด{{ receive ? "รับ" : "จ่าย" }}จริง</span><b>{{ money(net) }}</b>
				</div>
			</div>
			<p v-if="error" class="ss-note-line">{{ error }}</p>
			<p v-if="!info.can_submit" class="ss-muted">
				คุณสร้างร่างรายการได้ ผู้มีสิทธิ์ Submit Payment Entry เป็นผู้ยืนยันลงบัญชี
			</p>
		</div>
		<template #footer>
			<button
				type="button"
				class="ss-btn ss-btn--primary ss-btn--block ss-btn--lg"
				:disabled="busy || !form || !!error"
				@click="save"
			>
				<span v-if="busy" class="ss-spinner"></span>
				<template v-else>{{
					info?.can_submit ? `ยืนยัน${word}` : "สร้างร่างรายการ"
				}}</template>
			</button>
		</template>
	</Sheet>
</template>

<script setup>
import { computed, ref, watch } from "vue";
import DateInput from "../components/DateInput.vue";
import Icon from "../components/Icon.vue";
import MoneyInput from "../components/MoneyInput.vue";
import SelectBox from "../components/SelectBox.vue";
import Sheet from "../components/Sheet.vue";
import Skeleton from "../components/Skeleton.vue";
import { call, celebrate, money, num, post, show_error } from "../api.js";

const props = defineProps({ open: Boolean, kind: String, name: String });
const emit = defineEmits(["close", "done"]);
const API = "consbiz.accounting_app";

const info = ref(null);
const form = ref(null);
const busy = ref(false);
const receive = computed(() => props.kind === "si");
const word = computed(() => (receive.value ? "รับชำระ" : "จ่ายชำระ"));
const accounts = computed(() =>
	(info.value?.accounts || []).map((a) => ({
		value: a.value,
		label: a.label,
		description: a.account_type === "Bank" ? "ธนาคาร" : "เงินสด",
	}))
);
const modes = computed(() => [
	{ value: null, label: "ไม่ระบุ" },
	...(info.value?.modes || []).map((m) => ({ value: m, label: m })),
]);
const round2 = (v) => Math.round((Number(v) || 0) * 100) / 100;
const deducted = computed(() =>
	round2((form.value?.deductions || []).reduce((s, d) => s + (Number(d.amount) || 0), 0))
);
const net = computed(() => round2((Number(form.value?.allocated) || 0) - deducted.value));
const error = computed(() => {
	if (!form.value) return "";
	const allocated = Number(form.value.allocated) || 0;
	if (allocated <= 0) return "ยอดตัดหนี้ต้องมากกว่า 0";
	if (allocated - info.value.outstanding > 0.005)
		return `ยอดตัดหนี้เกินยอดค้าง ${money(info.value.outstanding)}`;
	if (net.value < 0) return "รายการหักมากกว่ายอดตัดหนี้";
	if (!form.value.account) return "";
	if (
		form.value.has_tax_invoice &&
		!(form.value.tax_invoice_number && form.value.tax_invoice_date)
	)
		return "กรอกเลขที่และวันที่ใบกำกับภาษี";
	return "";
});

// แก้ยอดหัก ณ ที่จ่าย = ฐานภาษีตามอัตรา (หนังสือรับรองใช้ฐานนี้)
function rebase(d, value) {
	if (d.wht && d.wht_rate) d.wht_base = round2(((Number(value) || 0) * 100) / d.wht_rate);
}

async function load() {
	info.value = null;
	form.value = null;
	try {
		const d = await call(`${API}.payment_defaults`, { kind: props.kind, name: props.name });
		info.value = d;
		const banks = d.accounts.filter((a) => a.account_type === "Bank");
		form.value = {
			posting_date: d.posting_date,
			allocated: d.outstanding,
			account:
				d.accounts.length === 1
					? d.accounts[0].value
					: banks.length === 1
					? banks[0].value
					: null,
			mode_of_payment: null,
			reference_no: "",
			deductions: d.deductions.map((x) => ({ ...x })),
			has_tax_invoice: false,
			tax_invoice_number: "",
			tax_invoice_date: d.posting_date,
		};
	} catch (e) {
		show_error(e);
		emit("close");
	}
}

async function save() {
	if (!form.value.account) return show_error(new Error("กรุณาเลือกบัญชีเงินสด/ธนาคาร"));
	busy.value = true;
	try {
		const f = form.value;
		const result = await post(`${API}.make_payment`, {
			kind: props.kind,
			name: props.name,
			submit: info.value.can_submit ? 1 : 0,
			data: JSON.stringify({
				...f,
				reference_date: f.posting_date,
				has_tax_invoice: f.has_tax_invoice ? 1 : 0,
				deductions: f.deductions.map((d) => ({
					account: d.account,
					cost_center: d.cost_center,
					description: d.description,
					amount: Number(d.amount) || 0,
					wht_type: d.wht_type || null,
					wht_base: d.wht ? d.wht_base : 0,
				})),
			}),
		});
		await celebrate(
			result.docstatus === 1 ? `${word.value}แล้ว` : "สร้างร่างรายการแล้ว",
			result.name
		);
		emit("done", result);
	} catch (e) {
		show_error(e);
	} finally {
		busy.value = false;
	}
}

watch(
	() => props.open,
	(value) => value && load(),
	{ immediate: true }
);
</script>
