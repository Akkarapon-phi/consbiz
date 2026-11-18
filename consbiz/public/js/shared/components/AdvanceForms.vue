<!-- ฟอร์มขอเบิก + ใบเคลียร์/เบิกสำรองจ่าย (API consbiz/self_advance.py) ใช้ 2 ที่ (ตกลง 2026-11-18):
     Self Service หน้าเบิกเงิน (พนักงานขอเอง, employee = null) / หมวดบุคคล หน้าเบิกเงิน (HR บันทึกแทนพนักงานที่ไม่มีมือถือ, employee = รหัส)
     data = ผลของ get_advance_data ของพนักงานคนนั้น (วงเงิน, ประเภทค่าใช้จ่าย) เปิดด้วย ref: open_request(type) / open_clear(advance | null)
     ส่งสำเร็จ emit done({ kind: "advance" | "claim", over_limit }) หน้าแม่โหลดใหม่/แสดงผลเอง -->
<template>
	<!-- ขอเบิก -->
	<Sheet
		:open="request_open"
		:title="form.type ? TYPE_INFO[form.type].label : 'ขอเบิก'"
		:subtitle="subtitle(form.type ? 'ส่งให้ผู้อนุมัติการเบิก' : 'เลือกประเภทการเบิก')"
		form
		@close="request_open = false"
	>
		<!-- ขั้น 1: เลือกประเภท (สำรองจ่าย = เปิดฟอร์มรายการค่าใช้จ่ายทันที) -->
		<div v-if="!form.type" class="ss-options ss-advance-types">
			<button v-for="t in REQUEST_TYPES" :key="t.value" type="button" class="ss-option" @click="choose_type(t.value)">
				<span class="ss-avatar" :class="`tone-${t.tone}`"><Icon :name="t.icon" :size="18" /></span>
				<span class="ss-option-main">
					<span class="ss-option-label">{{ t.label }}</span>
					<span class="ss-option-desc">{{ t.desc }}</span>
				</span>
				<Icon name="chevron-right" :size="16" />
			</button>
		</div>

		<!-- ขั้น 2: กรอก -->
		<template v-else>
			<button v-if="!locked_type" type="button" class="ss-link ss-advance-change" @click="form.type = null">
				<Icon name="chevron-left" :size="14" /> เปลี่ยนประเภท
			</button>
			<div class="ss-field">
				<span class="ss-field-label">จำนวนเงิน (บาท)<em>*</em></span>
				<MoneyInput v-model="form.amount" class="ss-input" placeholder="0.00" />
			</div>
			<template v-if="form.type === 'Salary Advance'">
				<div class="ss-facts">
					<div class="ss-fact"><span>เงินเดือน</span><b>{{ money(data.salary.base) }}</b></div>
					<div class="ss-fact">
						<span>วงเงิน {{ num(data.salary.percent) }}%</span><b>{{ money(data.salary.limit) }}</b>
					</div>
					<div class="ss-fact"><span>ยังหักคืนไม่ครบ</span><b>{{ money(data.salary.used) }}</b></div>
					<div class="ss-fact"><span>เบิกได้อีก</span><b>{{ money(data.salary.available) }}</b></div>
				</div>
				<p v-if="over_limit" class="ss-note ss-note--warn">
					เกินวงเงิน {{ money(Number(form.amount) - data.salary.available) }} บาท ต้องให้ผู้บริหารอนุมัติเพิ่ม
				</p>
			</template>
			<div v-else class="ss-field">
				<span class="ss-field-label">วันที่ต้องการรับเงิน</span>
				<DateInput v-model="form.required_date" :min="today()" clearable />
			</div>
			<label class="ss-field">
				<span class="ss-field-label">วัตถุประสงค์<em>*</em></span>
				<textarea
					v-model="form.purpose"
					class="ss-input"
					rows="2"
					:placeholder="form.type === 'Salary Advance' ? 'เช่น ค่าเทอมลูก' : 'เช่น ซื้อวัสดุเร่งด่วนหน้างาน'"
				></textarea>
			</label>
			<p class="ss-note">
				<template v-if="form.type === 'Salary Advance'">
					หักคืนจากเงินเดือน ผู้อนุมัติเป็นผู้กำหนดจำนวนงวด (1–{{ data.max_installments }} เดือน)
				</template>
				<template v-else>รับเงินแล้วเคลียร์ด้วยบิลภายใน {{ data.clear_days || 15 }} วันหลังรับเงิน</template>
			</p>
		</template>
		<template v-if="form.type" #footer>
			<button
				type="button"
				class="ss-btn ss-btn--primary ss-btn--block ss-btn--lg"
				:disabled="busy || !can_request"
				@click="send_request"
			>
				<span v-if="busy" class="ss-spinner"></span>
				<span>{{ employee ? "บันทึกแทนและส่งอนุมัติ" : "ส่งขอเบิก" }}</span>
			</button>
		</template>
	</Sheet>

	<!-- ใบเคลียร์ / เบิกสำรองจ่าย -->
	<Sheet
		:open="!!claim"
		full
		form
		:title="claim?.advance ? 'เคลียร์เงินทดรองจ่าย' : 'เบิกสำรองจ่าย'"
		:subtitle="
			subtitle(
				claim?.advance
					? `${claim.advance.name} · คงค้าง ${money(claim.advance.unclaimed)} บาท`
					: 'ทุกรายการต้องแนบรูปบิล/ใบเสร็จ'
			)
		"
		@close="close_claim"
	>
		<template v-if="claim">
			<section v-for="(row, i) in claim.rows" :key="row.key" class="ss-card ss-expense-row">
				<div class="ss-dayoff-head">
					<b>รายการที่ {{ i + 1 }}</b>
					<button
						v-if="claim.rows.length > 1"
						type="button"
						class="ss-icon-btn"
						aria-label="ลบรายการ"
						@click="claim.rows.splice(i, 1)"
					>
						<Icon name="trash" :size="16" />
					</button>
				</div>
				<div class="ss-leave-dates">
					<div class="ss-field">
						<span class="ss-field-label">ประเภท<em>*</em></span>
						<SelectBox v-model="row.expense_type" :options="type_options" placeholder="เลือก" />
					</div>
					<div class="ss-field">
						<span class="ss-field-label">วันที่</span>
						<DateInput v-model="row.expense_date" />
					</div>
				</div>
				<label class="ss-field">
					<span class="ss-field-label">รายละเอียด</span>
					<input v-model="row.description" class="ss-input" placeholder="เช่น ค่าน้ำมันรถไปไซต์" />
				</label>
				<div class="ss-field">
					<span class="ss-field-label">จำนวนเงิน (บาท)<em>*</em></span>
					<MoneyInput v-model="row.amount" class="ss-input" placeholder="0.00" />
				</div>
				<div class="ss-field">
					<span class="ss-field-label">รูปบิล/ใบเสร็จ<em>*</em></span>
					<PhotoInput v-model="row.photos" :max="1" :label="employee ? 'ถ่ายรูป/แนบไฟล์บิล' : 'ถ่ายรูปบิล'" />
				</div>
			</section>
			<button type="button" class="ss-btn ss-btn--soft ss-btn--block" @click="add_row">
				<Icon name="plus" :size="18" /><span>เพิ่มรายการ</span>
			</button>
			<label class="ss-field">
				<span class="ss-field-label">หมายเหตุ</span>
				<textarea v-model="claim.remark" class="ss-input" rows="2"></textarea>
			</label>
			<div class="ss-facts">
				<div class="ss-fact"><span>รวมค่าใช้จ่าย</span><b>{{ money(claim_total) }} บาท</b></div>
				<template v-if="claim.advance">
					<div class="ss-fact">
						<span>ตัดจากเงินทดรองจ่าย</span><b>{{ money(Math.min(claim_total, claim.advance.unclaimed)) }}</b>
					</div>
					<div v-if="claim_total < claim.advance.unclaimed" class="ss-fact">
						<span>ต้องคืนเงินให้บริษัท</span
						><b class="ss-text-danger">{{ money(claim.advance.unclaimed - claim_total) }}</b>
					</div>
					<div v-else-if="claim_total > claim.advance.unclaimed" class="ss-fact">
						<span>บริษัทจ่ายเพิ่ม</span><b>{{ money(claim_total - claim.advance.unclaimed) }}</b>
					</div>
				</template>
			</div>
		</template>
		<template #footer>
			<button
				type="button"
				class="ss-btn ss-btn--primary ss-btn--block ss-btn--lg"
				:disabled="busy || !can_send_claim"
				@click="send_claim"
			>
				<span v-if="busy" class="ss-spinner"></span>
				<span>{{ employee ? "บันทึกแทนและส่งอนุมัติ" : "ส่งให้ผู้อนุมัติ" }}</span>
			</button>
		</template>
	</Sheet>
</template>

<script setup>
import { computed, reactive, ref } from "vue";
import Icon from "./Icon.vue";
import Sheet from "./Sheet.vue";
import SelectBox from "./SelectBox.vue";
import DateInput from "./DateInput.vue";
import MoneyInput from "./MoneyInput.vue";
import PhotoInput from "./PhotoInput.vue";
import { money, num, post, show_error, today } from "../api.js";

const props = defineProps({
	data: { type: Object, default: null },
	// HR บันทึกแทน: รหัส + ชื่อพนักงาน (ไม่ส่ง = ผู้ใช้ขอเอง)
	employee: { type: String, default: null },
	employee_name: { type: String, default: "" },
	// ประเภทที่เลือกได้ในขั้นแรก (ไม่ส่ง = ทั้ง 3)
	types: { type: Array, default: null },
});
const emit = defineEmits(["done"]);

const API = "consbiz.self_advance.";
const ALL_TYPES = [
	{ value: "Salary Advance", label: "เบิกเงินเดือนล่วงหน้า", desc: "รับก่อน หักคืนจากเงินเดือน", icon: "wallet", tone: "green" },
	{ value: "Expense Advance", label: "เบิกทดรองจ่าย", desc: "รับเงินไปจ่ายงาน แล้วเคลียร์ด้วยบิล", icon: "calculator", tone: "blue" },
	{ value: "reimburse", label: "เบิกสำรองจ่าย", desc: "จ่ายเองไปแล้ว ส่งบิลเบิกคืน", icon: "receive", tone: "amber" },
];
const REQUEST_TYPES = computed(() => ALL_TYPES.filter((t) => !props.types || props.types.includes(t.value)));
const TYPE_INFO = Object.fromEntries(ALL_TYPES.map((t) => [t.value, t]));
const busy = ref(false);
const subtitle = (text) => (props.employee_name ? `แทน ${props.employee_name} · ${text}` : text);
const extra = () => (props.employee ? { employee: props.employee } : {});

// ---------------------------------------------------------------- ขอเบิก

const request_open = ref(false);
const form = reactive({});
const over_limit = computed(
	() => form.type === "Salary Advance" && Number(form.amount) > (props.data?.salary?.available || 0)
);
const can_request = computed(() => form.type && Number(form.amount) > 0 && form.purpose?.trim());

// ไม่ระบุชนิด = เริ่มที่หน้าเลือกประเภท / ระบุ = เข้าฟอร์มชนิดนั้นเลย ไม่มีปุ่มเปลี่ยนประเภท
const locked_type = ref(false);
function open_request(type = null) {
	if (type === "reimburse") return open_clear(null);
	const known = TYPE_INFO[type] ? type : null;
	Object.assign(form, { type: known, amount: null, purpose: "", required_date: null });
	locked_type.value = !!known;
	request_open.value = true;
}
function choose_type(type) {
	if (type === "reimburse") {
		request_open.value = false;
		open_clear(null);
		return;
	}
	form.type = type;
}

async function send_request() {
	busy.value = true;
	try {
		await post(`${API}request_advance`, {
			advance_type: form.type,
			amount: form.amount,
			purpose: form.purpose,
			required_date: form.required_date || undefined,
			...extra(),
		});
		request_open.value = false;
		emit("done", { kind: "advance", over_limit: over_limit.value });
	} catch (error) {
		show_error(error);
	} finally {
		busy.value = false;
	}
}

// ---------------------------------------------------------------- เคลียร์ / เบิกสำรองจ่าย

const claim = ref(null);
let row_key = 0;
const new_row = () => ({ key: ++row_key, expense_type: null, expense_date: today(), description: "", amount: null, photos: [] });
const type_options = computed(() => (props.data?.expense_types || []).map((t) => ({ value: t, label: t })));
const claim_total = computed(() => (claim.value?.rows || []).reduce((s, r) => s + (Number(r.amount) || 0), 0));
const can_send_claim = computed(
	() =>
		claim.value?.rows.length &&
		claim.value.rows.every((r) => r.expense_type && Number(r.amount) > 0 && r.photos[0]?.name && !r.photos[0]?.uploading)
);

function open_clear(advance) {
	claim.value = { advance, rows: [new_row()], remark: "" };
}
function add_row() {
	claim.value.rows.push(new_row());
}
function close_claim() {
	if (!busy.value) claim.value = null;
}

async function send_claim() {
	busy.value = true;
	try {
		await post(`${API}submit_claim`, {
			rows: claim.value.rows.map((r) => ({
				expense_type: r.expense_type,
				expense_date: r.expense_date,
				description: r.description,
				amount: r.amount,
				receipt: r.photos[0].name,
			})),
			remark: claim.value.remark,
			advance: claim.value.advance?.name,
			...extra(),
		});
		claim.value = null;
		emit("done", { kind: "claim" });
	} catch (error) {
		show_error(error);
	} finally {
		busy.value = false;
	}
}

defineExpose({ open_request, open_clear });
</script>
