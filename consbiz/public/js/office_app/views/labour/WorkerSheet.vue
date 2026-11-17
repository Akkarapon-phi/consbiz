<!-- เพิ่ม/แก้คนงานรายวัน (consbiz.labour.get_worker / save_worker) ใช้ในหน้าลงเวลาและทะเบียนคนงาน
     name ว่าง = เพิ่มใหม่ (ข้อมูลหลัก + ข้อมูลเพิ่มเติมพับไว้) มี name = แก้ (เปิดทุกส่วน)
     ค่าแรงเปลี่ยน = เพิ่มแถวประวัติตั้งแต่วันที่ระบุ (ไม่แก้แถวเดิม ใบลงเวลาที่ผ่านแล้วคิดตามอัตราเดิม)
     emit saved = แถวคนงานแบบเดียวกับ get_sheet().workers -->
<template>
	<Sheet :open="open" :title="name ? 'แก้ข้อมูลคนงาน' : 'คนงานใหม่'" :subtitle="name || ''" @close="$emit('close')">
		<Skeleton v-if="loading" :rows="5" />
		<div v-else class="wk-form">
			<label class="ss-field">
				<span class="ss-field-label">ชื่อ-นามสกุล<em>*</em></span>
				<input v-model="form.worker_name" class="ss-input" :disabled="readonly" />
			</label>
			<div class="wk-row">
				<label class="ss-field">
					<span class="ss-field-label">ตำแหน่ง</span>
					<input v-model="form.position" class="ss-input" placeholder="เช่น ช่างไม้ กรรมกร" :disabled="readonly" />
				</label>
				<Picker
					v-model="form.team"
					label="ทีม/ชุด"
					:options="teams.filter((t) => t !== 'ไม่ระบุทีม').map((t) => ({ value: t, label: t }))"
					placeholder="เลือกหรือพิมพ์ทีมใหม่"
					allow_text
					clearable
				/>
			</div>
			<div class="ss-field">
				<span class="ss-field-label">จ่ายผ่าน</span>
				<Segmented v-model="form.payee_type" :options="PAYEE" />
			</div>
			<Picker
				v-if="form.payee_type === 'Subcontractor'"
				v-model="form.supplier"
				label="ผู้รับเหมา/หัวหน้าชุด"
				:display_value="form.supplier_name"
				remote="Supplier"
				required
			/>
			<div class="wk-row">
				<label class="ss-field">
					<span class="ss-field-label">ค่าแรง/วัน<em>*</em></span>
					<MoneyInput v-model="form.daily_rate" />
				</label>
				<div v-if="name && rate_changed" class="ss-field">
					<span class="ss-field-label">ค่าแรงใหม่ตั้งแต่</span>
					<DateInput v-model="form.rate_from" />
				</div>
			</div>
			<p v-if="name && rates.length > 1" class="ss-muted wk-small">
				ประวัติค่าแรง: {{ rates.map((r) => `${thai_date(r.from_date, { year: true })} ${money(r.daily_rate)}`).join(" → ") }}
			</p>

			<button v-if="!name" type="button" class="wk-more" @click="more = !more">
				<Icon :name="more ? 'chevron-down' : 'chevron-right'" :size="14" />
				ข้อมูลเพิ่มเติม (บัตร ธนาคาร ประกันสังคม OT)
			</button>

			<template v-if="more || name">
				<h3 class="ss-section-title">ข้อมูลส่วนตัว</h3>
				<div class="wk-row">
					<label class="ss-field">
						<span class="ss-field-label">เลขบัตรประชาชน/พาสปอร์ต</span>
						<input v-model="form.id_number" class="ss-input" />
					</label>
					<label class="ss-field">
						<span class="ss-field-label">สัญชาติ</span>
						<input v-model="form.nationality" class="ss-input" />
					</label>
				</div>
				<label class="ss-field">
					<span class="ss-field-label">โทรศัพท์</span>
					<input v-model="form.phone" class="ss-input" type="tel" inputmode="tel" />
				</label>

				<h3 class="ss-section-title">บัญชีรับเงิน</h3>
				<div class="wk-row">
					<Picker
						v-model="form.bank_name"
						label="ธนาคาร"
						:options="BANKS.map((b) => ({ value: b, label: b }))"
						allow_text
						clearable
					/>
					<label class="ss-field">
						<span class="ss-field-label">เลขที่บัญชี</span>
						<input v-model="form.bank_account" class="ss-input" inputmode="numeric" placeholder="ตัวเลข 10-15 หลัก" />
					</label>
				</div>
				<label class="ss-toggle" :class="{ 'is-on': form.account_holder_other }">
					<input v-model="form.account_holder_other" type="checkbox" />
					<span class="ss-toggle-track"><span></span></span>
					<span>รับเงินผ่านบัญชีผู้อื่น</span>
				</label>
				<div v-if="form.account_holder_other" class="wk-row">
					<label class="ss-field">
						<span class="ss-field-label">ชื่อเจ้าของบัญชี<em>*</em></span>
						<input v-model="form.account_holder" class="ss-input" />
					</label>
					<label class="ss-field">
						<span class="ss-field-label">ความเกี่ยวข้อง</span>
						<input v-model="form.account_holder_relation" class="ss-input" placeholder="เช่น ภรรยา หัวหน้าชุด" />
					</label>
				</div>

				<h3 class="ss-section-title">OT และประกันสังคม</h3>
				<label class="ss-toggle" :class="{ 'is-on': form.ot_flat }">
					<input v-model="form.ot_flat" type="checkbox" />
					<span class="ss-toggle-track"><span></span></span>
					<span>OT เหมาเป็นชั่วโมง (ไม่ติ๊ก = ตามกฎหมาย ค่าแรง ÷ 8 x 1.5)</span>
				</label>
				<label v-if="form.ot_flat" class="ss-field">
					<span class="ss-field-label">ค่า OT/ชั่วโมง<em>*</em></span>
					<MoneyInput v-model="form.ot_hourly_rate" />
				</label>
				<template v-if="form.payee_type === 'Company'">
					<label class="ss-toggle" :class="{ 'is-on': form.sso_registered }">
						<input v-model="form.sso_registered" type="checkbox" />
						<span class="ss-toggle-track"><span></span></span>
						<span>ขึ้นทะเบียนประกันสังคม (หักเงินสมทบ)</span>
					</label>
					<label v-if="form.sso_registered" class="ss-field">
						<span class="ss-field-label">เลขประกันสังคม</span>
						<input v-model="form.sso_number" class="ss-input" />
					</label>
				</template>

				<template v-if="name">
					<h3 class="ss-section-title">สถานะ</h3>
					<Segmented v-model="form.status" :options="STATUS" />
				</template>
			</template>
		</div>
		<template v-if="!loading && !readonly" #footer>
			<div class="ss-sheet-actions">
				<button type="button" class="ss-btn ss-btn--primary ss-btn--block ss-btn--lg" :disabled="!can_save || busy" @click="save">
					<span v-if="busy" class="ss-spinner"></span>
					<template v-else>{{ name ? "บันทึก" : "เพิ่มคนงาน" }}</template>
				</button>
			</div>
		</template>
	</Sheet>
</template>

<script setup>
import { computed, reactive, ref, watch } from "vue";
import Icon from "../../../shared/components/Icon.vue";
import Skeleton from "../../../shared/components/Skeleton.vue";
import Segmented from "../../../shared/components/Segmented.vue";
import MoneyInput from "../../../shared/components/MoneyInput.vue";
import DateInput from "../../../shared/components/DateInput.vue";
import Picker from "../../../shared/components/Picker.vue";
import Sheet from "../../../shared/components/Sheet.vue";
import { call, money, post, show_error, thai_date, toast, today } from "../../../shared/api.js";

const props = defineProps({
	open: Boolean,
	project: String,
	name: String,
	teams: { type: Array, default: () => [] },
});
const emit = defineEmits(["close", "saved"]);

const PAYEE = [
	{ value: "Company", label: "บริษัท" },
	{ value: "Subcontractor", label: "ผรม./หัวหน้าชุด" },
];
const STATUS = [
	{ value: "Active", label: "ทำงานอยู่" },
	{ value: "Inactive", label: "เลิกจ้าง" },
];
const BANKS = [
	"กสิกรไทย",
	"กรุงเทพ",
	"กรุงไทย",
	"ไทยพาณิชย์",
	"กรุงศรีอยุธยา",
	"ทหารไทยธนชาต (ttb)",
	"ออมสิน",
	"ธ.ก.ส.",
	"อาคารสงเคราะห์",
	"ยูโอบี",
	"ซีไอเอ็มบี ไทย",
	"เกียรตินาคินภัทร",
	"แลนด์ แอนด์ เฮ้าส์",
];

const form = reactive({});
const rates = ref([]);
const original_rate = ref(0);
const loading = ref(false);
const busy = ref(false);
const more = ref(false);
const readonly = ref(false);

const rate_changed = computed(() => Number(form.daily_rate || 0) !== Number(original_rate.value || 0));
const can_save = computed(
	() =>
		form.worker_name?.trim() &&
		Number(form.daily_rate) > 0 &&
		(form.payee_type !== "Subcontractor" || form.supplier) &&
		(!form.account_holder_other || form.account_holder?.trim()) &&
		(!form.ot_flat || Number(form.ot_hourly_rate) > 0)
);

function reset() {
	for (const key of Object.keys(form)) delete form[key];
	Object.assign(form, {
		worker_name: "",
		position: "",
		team: null,
		payee_type: "Company",
		supplier: null,
		daily_rate: null,
		rate_from: today(),
		nationality: "ไทย",
		account_holder_other: false,
		ot_flat: false,
		sso_registered: false,
		status: "Active",
	});
	rates.value = [];
	original_rate.value = 0;
	readonly.value = false;
	more.value = false;
}

async function load() {
	reset();
	if (!props.name) return;
	loading.value = true;
	try {
		const data = await call("consbiz.labour.get_worker", { name: props.name });
		Object.assign(form, data, {
			account_holder_other: !!data.account_holder_other,
			ot_flat: !!data.ot_flat,
			sso_registered: !!data.sso_registered,
			rate_from: today(),
		});
		rates.value = data.rates;
		original_rate.value = data.daily_rate;
		readonly.value = !data.can_write;
	} catch (error) {
		show_error(error);
		emit("close");
	} finally {
		loading.value = false;
	}
}

watch(
	() => props.open,
	(open) => open && load(),
	{ immediate: true }
);

async function save() {
	busy.value = true;
	try {
		const values = { ...form };
		values.account_holder_other = values.account_holder_other ? 1 : 0;
		values.ot_flat = values.ot_flat ? 1 : 0;
		values.sso_registered = values.sso_registered ? 1 : 0;
		if (props.name && !rate_changed.value) delete values.daily_rate;
		delete values.rates;
		const result = await post("consbiz.labour.save_worker", {
			values,
			name: props.name || undefined,
			project: props.project,
		});
		toast(props.name ? "บันทึกข้อมูลคนงานแล้ว" : `เพิ่ม ${result.worker_name} แล้ว`, "success");
		emit("saved", { worker: result.name, ...result });
	} catch (error) {
		show_error(error);
	} finally {
		busy.value = false;
	}
}
</script>

<style scoped>
.wk-form {
	display: flex;
	flex-direction: column;
	gap: 12px;
}
.wk-row {
	display: grid;
	grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
	gap: 12px;
}
.wk-small {
	margin: -4px 0 0;
	font-size: var(--ss-fs-sm);
}
.wk-more {
	display: inline-flex;
	align-items: center;
	gap: 4px;
	align-self: flex-start;
	padding: 0;
	border: 0;
	background: none;
	color: var(--ss-brand);
	font: inherit;
	font-weight: 600;
	cursor: pointer;
}
</style>
