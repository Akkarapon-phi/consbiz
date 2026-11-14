<!-- ตั้งค่าบัญชีค่าแรงคนงานรายวันต่อบริษัท (หัวข้อ "บัญชี" ของหน้าตั้งค่า, Labour Settings, API consbiz/labour.py)
     ใช้ตอนอนุมัติใบลงเวลา (Journal Entry / ร่าง PI ของ ผรม.) และจ่ายเงินเบิกล่วงหน้า
     ไม่เจอบัญชีที่ตรง = ปุ่ม "สร้างบัญชีใหม่" (ระบบเสนอชื่อ กลุ่มแม่ และเลขบัญชีถัดไป suggest_account / create_account)
     ข้อที่ต้องตั้งนอกหน้านี้ (อัตราประกันสังคม, Thai Tax Settings, บัญชีหัก ณ ที่จ่าย) แสดงเป็นรายการตรวจด้านบน -->
<template>
	<div class="ss-settings-form">
		<div class="ss-settings-form-inner">
			<Skeleton v-if="!data" :rows="6" />
			<template v-else>
				<header class="ls-head">
					<div>
						<h2 class="ls-title">ค่าแรงคนงาน</h2>
						<p class="ss-muted ls-hint">บัญชีที่ระบบใช้ลงค่าแรงคนงานรายวันและเงินเบิกล่วงหน้า แยกตามบริษัท</p>
					</div>
					<div class="ls-company">
						<SelectBox
							:model-value="data.company"
							:options="data.companies.map((c) => ({ value: c, label: c }))"
							label="บริษัท"
							@update:model-value="load"
						/>
					</div>
				</header>

				<div class="ls-checks">
					<a
						v-for="c in data.checks"
						:key="c.label"
						class="ls-check"
						:class="c.ok ? 'is-ok' : 'is-warn'"
						:href="c.link"
						target="_blank"
						rel="noopener"
					>
						<Icon :name="c.ok ? 'check' : 'alert'" :size="16" />
						<span><b>{{ c.label }}</b> {{ c.text }}</span>
						<Icon name="external" :size="14" />
					</a>
				</div>

				<section v-for="group in GROUPS" :key="group.title" class="ls-group">
					<h3 class="ss-section-title">{{ group.title }}</h3>
					<p class="ss-muted ls-hint">{{ group.hint }}</p>
					<div class="ls-fields">
						<div v-for="f in group.fields" :key="f.field" class="ls-field">
							<template v-if="f.field !== 'subcontract_wht_percent'">
								<Picker
									:model-value="values[f.field]"
									:label="f.label"
									:display_value="labels[f.field]"
									:remote_fn="(txt) => search(f.field, txt)"
									:required="f.required"
									clearable
									@update:model-value="(v) => set(f.field, v)"
								/>
								<small class="ss-muted">{{ f.hint }}</small>
								<button
									v-if="data.can_edit && can_create(f.field) && creating?.field !== f.field"
									type="button"
									class="ls-create-link"
									@click="start_create(f.field)"
								>
									<Icon name="plus" :size="13" />
									{{ f.field === "subcontract_item" ? "สร้าง Item ใหม่" : "สร้างบัญชีใหม่" }}
								</button>

								<!-- สร้างใหม่ในที่ -->
								<div v-if="creating?.field === f.field" class="ls-create">
									<Skeleton v-if="creating.loading" :rows="2" />
									<template v-else-if="f.field === 'subcontract_item'">
										<label class="ss-field">
											<span class="ss-field-label">ชื่อ Item</span>
											<input v-model="creating.account_name" class="ss-input" />
										</label>
										<small class="ss-muted">Item ที่ไม่ใช่สต็อก ใช้เป็นบรรทัดของ Purchase Invoice ค่าแรง ผรม.</small>
									</template>
									<template v-else>
										<label class="ss-field">
											<span class="ss-field-label">ชื่อบัญชี</span>
											<input v-model="creating.account_name" class="ss-input" />
										</label>
										<div class="ls-create-row">
											<SelectBox
												v-model="creating.parent_account"
												:options="creating.parents"
												label="อยู่ใต้กลุ่ม"
												@update:model-value="refresh_number"
											/>
											<label class="ss-field ls-number">
												<span class="ss-field-label">เลขบัญชี</span>
												<input v-model="creating.account_number" class="ss-input" inputmode="numeric" placeholder="ไม่มี" />
											</label>
										</div>
									</template>
									<div class="ls-create-actions">
										<button type="button" class="ss-btn ss-btn--ghost" @click="creating = null">ยกเลิก</button>
										<button
											type="button"
											class="ss-btn ss-btn--primary"
											:disabled="busy || creating.loading || !creating.account_name?.trim() || (f.field !== 'subcontract_item' && !creating.parent_account)"
											@click="create"
										>
											<span v-if="busy" class="ss-spinner"></span>
											<template v-else>สร้างแล้วเลือก</template>
										</button>
									</div>
								</div>
							</template>
							<template v-else>
								<label class="ss-field">
									<span class="ss-field-label">{{ f.label }}</span>
									<input
										v-model.number="values.subcontract_wht_percent"
										class="ss-input"
										inputmode="decimal"
										:disabled="!data.can_edit"
									/>
								</label>
								<small class="ss-muted">{{ f.hint }}</small>
							</template>
						</div>
					</div>
				</section>

				<div v-if="data.can_edit" class="ls-actions">
					<span v-if="dirty" class="ss-muted">ยังไม่ได้บันทึก</span>
					<button type="button" class="ss-btn ss-btn--primary" :disabled="saving || !dirty" @click="save">
						<span v-if="saving" class="ss-spinner"></span>
						<template v-else>บันทึก</template>
					</button>
				</div>
				<p v-else class="ss-muted">ดูได้อย่างเดียว (แก้ได้เฉพาะ Accounts Manager / System Manager)</p>
			</template>
		</div>
	</div>
</template>

<script setup>
import { computed, reactive, ref } from "vue";
import Icon from "../Icon.vue";
import Skeleton from "../Skeleton.vue";
import SelectBox from "../SelectBox.vue";
import Picker from "../Picker.vue";
import { call, post, show_error, toast } from "../../api.js";

const API = "consbiz.labour.";
const GROUPS = [
	{
		title: "คนงานที่บริษัทจ่ายเอง",
		hint: "อนุมัติใบลงเวลาแล้วระบบลง Journal Entry ผูกโครงการ: Dr. ค่าแรง + ประกันสังคมนายจ้าง / Cr. ประกันสังคมค้างจ่าย เงินเบิก หักอื่นๆ ค่าแรงค้างจ่าย",
		fields: [
			{ field: "wage_expense_account", label: "ค่าแรงทางตรง", hint: "บัญชีค่าใช้จ่าย (Expense) เช่น ค่าแรงงานก่อสร้าง", required: true },
			{ field: "wage_payable_account", label: "ค่าแรงค้างจ่าย", hint: "หนี้สิน (Liability) ที่ไม่ใช่เจ้าหนี้การค้า บัญชีจ่ายเงินตัดบัญชีนี้", required: true },
			{ field: "employer_sso_expense_account", label: "ประกันสังคมส่วนนายจ้าง", hint: "ค่าใช้จ่าย (Expense) เงินสมทบส่วนบริษัท" },
			{ field: "sso_payable_account", label: "ประกันสังคมค้างจ่าย", hint: "หนี้สิน (Liability) รอนำส่ง สปส. (ส่วนลูกจ้าง + นายจ้าง)" },
			{ field: "advance_account", label: "เงินเบิกล่วงหน้าคนงาน", hint: "สินทรัพย์ (Asset) ที่ไม่ใช่ลูกหนี้การค้า ใช้กับเมนูเบิกล่วงหน้า" },
			{ field: "other_deduction_account", label: "หักอื่นๆ", hint: "เช่น รายได้อื่น ว่าง = ลดค่าแรงทางตรง" },
		],
	},
	{
		title: "คนงานผ่าน ผรม./หัวหน้าชุด",
		hint: "อนุมัติแล้วระบบสร้างร่าง Purchase Invoice 1 ใบต่อ ผรม. (ค่าแรง - หักอื่นๆ) ลงบัญชีค่าแรงทางตรง ฝ่ายบัญชีตรวจแล้ว Submit เอง",
		fields: [
			{ field: "subcontract_item", label: "รายการค่าแรง ผรม.", hint: "Item ที่ไม่ใช่สต็อก เช่น ค่าแรงผู้รับเหมาช่วง" },
			{ field: "subcontract_wht_percent", label: "หัก ณ ที่จ่าย (%)", hint: "ปกติ 3% ใส่ 0 = ไม่หัก" },
		],
	},
];

const data = ref(null);
const values = reactive({});
const labels = reactive({});
const saved = ref("");
const saving = ref(false);
const busy = ref(false);
const creating = ref(null);
const dirty = computed(() => JSON.stringify(values) !== saved.value);

function apply(result) {
	data.value = result;
	creating.value = null;
	for (const key of Object.keys(values)) delete values[key];
	Object.assign(values, result.values);
	for (const key of Object.keys(labels)) delete labels[key];
	Object.assign(labels, result.labels);
	saved.value = JSON.stringify(values);
}

async function load(company) {
	try {
		apply(await call(API + "get_settings", { company }));
	} catch (error) {
		show_error(error);
	}
}

function search(field, txt) {
	if (field === "subcontract_item") return call(API + "search_service_items", { txt });
	return call(API + "search_accounts", { company: data.value.company, field, txt });
}

function set(field, value, label = null) {
	if (!data.value.can_edit) return;
	values[field] = value || null;
	labels[field] = label;
}

const can_create = (field) => (field === "subcontract_item" ? data.value.can_create_item : data.value.can_create_account);

async function start_create(field) {
	if (field === "subcontract_item") {
		creating.value = { field, account_name: "ค่าแรงผู้รับเหมาช่วง" };
		return;
	}
	creating.value = { field, loading: true };
	try {
		const s = await call(API + "suggest_account", { company: data.value.company, field });
		if (creating.value?.field === field) creating.value = { field, ...s, loading: false };
	} catch (error) {
		show_error(error);
		creating.value = null;
	}
}

async function refresh_number(parent) {
	if (!parent || !creating.value) return;
	try {
		creating.value.account_number = (await call(API + "number_for", { parent })) || "";
	} catch {
		// เลขบัญชีกรอกเองได้
	}
}

async function create() {
	const c = creating.value;
	busy.value = true;
	try {
		const result =
			c.field === "subcontract_item"
				? await post(API + "create_service_item", { item_name: c.account_name })
				: await post(API + "create_account", {
						company: data.value.company,
						field: c.field,
						account_name: c.account_name,
						parent_account: c.parent_account,
						account_number: c.account_number || null,
				  });
		set(c.field, result.value, result.label);
		creating.value = null;
		toast(`สร้าง ${result.label} แล้ว กดบันทึกเพื่อใช้`, "success");
	} catch (error) {
		show_error(error);
	} finally {
		busy.value = false;
	}
}

async function save() {
	saving.value = true;
	try {
		apply(await post(API + "save_settings", { company: data.value.company, values: { ...values } }));
		toast("บันทึกตั้งค่าค่าแรงแล้ว", "success");
	} catch (error) {
		show_error(error);
	} finally {
		saving.value = false;
	}
}

load();
</script>

<style scoped>
.ls-head {
	display: flex;
	flex-wrap: wrap;
	align-items: flex-end;
	justify-content: space-between;
	gap: 12px 24px;
}
.ls-title {
	margin: 0;
	font-size: var(--ss-fs-lg);
	font-weight: 700;
	color: var(--ss-text);
}
.ls-company {
	width: 280px;
	max-width: 100%;
}
.ls-checks {
	display: flex;
	flex-direction: column;
	gap: 6px;
}
.ls-check {
	display: flex;
	align-items: center;
	gap: 8px;
	padding: 8px 10px;
	border-radius: 10px;
	border: 1px solid var(--ss-border);
	color: var(--ss-text);
	text-decoration: none;
	font-size: var(--ss-fs);
}
.ls-check span {
	flex: 1;
}
.ls-check.is-ok {
	--tone: var(--tone-green);
}
.ls-check.is-warn {
	--tone: var(--tone-amber);
	background: var(--tone-amber-bg);
}
.ls-check > :first-child {
	color: var(--tone);
}
.ls-group {
	padding: 4px 16px 16px;
	border: 1px solid var(--ss-border);
	border-radius: 12px;
	background: var(--ss-surface);
}
.ls-hint {
	margin: 4px 2px 12px;
	font-size: var(--ss-fs-sm);
}
.ls-fields {
	display: grid;
	grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
	gap: 16px 20px;
}
.ls-field {
	display: flex;
	flex-direction: column;
	gap: 4px;
	min-width: 0;
}
.ls-field small {
	font-size: var(--ss-fs-sm);
}
.ls-create-link {
	align-self: flex-start;
	display: inline-flex;
	align-items: center;
	gap: 4px;
	padding: 0;
	border: 0;
	background: none;
	color: var(--ss-brand);
	font-size: var(--ss-fs-sm);
	font-weight: 600;
	cursor: pointer;
}
.ls-create {
	display: flex;
	flex-direction: column;
	gap: 8px;
	margin-top: 4px;
	padding: 10px;
	border: 1px dashed var(--ss-brand);
	border-radius: 10px;
	background: var(--ss-brand-soft);
}
.ls-create-row {
	display: grid;
	grid-template-columns: minmax(0, 1fr) 110px;
	gap: 8px;
}
.ls-create-actions {
	display: flex;
	justify-content: flex-end;
	gap: 8px;
}
.ls-actions {
	position: sticky;
	bottom: 0;
	display: flex;
	align-items: center;
	justify-content: flex-end;
	gap: 12px;
	padding: 10px 0;
	background: var(--ss-surface);
}
</style>
