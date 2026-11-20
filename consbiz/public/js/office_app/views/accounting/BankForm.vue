<template>
	<Sheet
		open
		form
		:title="doc ? 'แก้ไขบัญชีธนาคาร' : 'สร้างบัญชีธนาคาร'"
		@close="!saving && $emit('close')"
	>
		<div v-if="!doc && !state.company" class="ss-field">
			<span class="ss-field-label">บริษัท <em>*</em></span>
			<SelectBox
				v-model="company"
				label="บริษัท"
				placeholder="เลือกบริษัท"
				:options="companies"
				variant="field"
			/>
		</div>
		<div v-else class="ss-fact">
			<span>บริษัท</span><b>{{ company }}</b>
		</div>
		<label class="ss-field">
			<span class="ss-field-label">ชื่อบัญชี <em>*</em></span>
			<input v-model.trim="account_name" class="ss-input" autocomplete="off" />
		</label>
		<ComboBox v-if="!new_bank" v-model="bank" label="ธนาคาร" :options="banks" required />
		<label v-else class="ss-field">
			<span class="ss-field-label">ชื่อธนาคารใหม่ <em>*</em></span>
			<input v-model.trim="bank" class="ss-input" autocomplete="off" />
		</label>
		<button v-if="options?.can_create_bank" type="button" class="ss-link" @click="toggle_bank">
			{{ new_bank ? "เลือกธนาคารที่มีอยู่" : "+ สร้างธนาคารใหม่" }}
		</button>
		<label class="ss-field">
			<span class="ss-field-label">เลขที่บัญชี</span>
			<input v-model.trim="bank_account_no" class="ss-input" autocomplete="off" />
		</label>
		<ComboBox v-model="account" label="ผังบัญชี (GL)" :options="accounts" required />
		<label class="ss-toggle" :class="{ 'is-on': is_default }">
			<input v-model="is_default" type="checkbox" />
			<span class="ss-toggle-track"><span></span></span><span>บัญชีเริ่มต้นของบริษัท</span>
		</label>
		<template #footer>
			<button type="button" class="ss-btn ss-btn--soft" :disabled="saving" @click="$emit('close')">
				ยกเลิก
			</button>
			<button type="button" class="ss-btn ss-btn--primary" :disabled="!ready || saving" @click="save">
				<Icon name="check" :size="16" /> บันทึก
			</button>
		</template>
	</Sheet>
</template>

<script setup>
import { computed, ref, watch } from "vue";
import { boot, call, show_error, state } from "../../../shared/api.js";
import ComboBox from "../../../shared/components/ComboBox.vue";
import Icon from "../../../shared/components/Icon.vue";
import SelectBox from "../../../shared/components/SelectBox.vue";
import Sheet from "../../../shared/components/Sheet.vue";

const props = defineProps({ doc: Object });
const emit = defineEmits(["saved", "close"]);
const companies = (boot.companies || []).map((c) => ({ value: c.name, label: c.name }));
const company = ref(
	props.doc?.company || state.company || (companies.length === 1 ? companies[0].value : "")
);
const account_name = ref(props.doc?.account_name || "");
const bank = ref(props.doc?.bank || "");
const bank_account_no = ref(props.doc?.bank_account_no || "");
const account = ref(props.doc?.account || "");
const is_default = ref(!!props.doc?.is_default);
const options = ref(null);
const new_bank = ref(false);
const saving = ref(false);
const choices = (names) => (names || []).map((value) => ({ value, label: value }));
const banks = computed(() => choices(options.value?.banks));
const accounts = computed(() => choices(options.value?.accounts));
const ready = computed(
	() => options.value && company.value && account_name.value && bank.value && account.value
);
function toggle_bank() {
	new_bank.value = !new_bank.value;
	bank.value = "";
}

watch(
	company,
	async (value, previous, onCleanup) => {
		let active = true;
		onCleanup(() => (active = false));
		options.value = null;
		if (previous !== undefined) account.value = "";
		if (!value) return;
		try {
			const result = await call("consbiz.bank_app.form_options", {
				company: value,
				name: props.doc?.name,
			});
			if (active) {
				options.value = result;
				if (!result.banks.length && result.can_create_bank) new_bank.value = true;
			}
		} catch (e) {
			if (active) show_error(e);
		}
	},
	{ immediate: true }
);

async function save() {
	if (saving.value || !ready.value) return;
	saving.value = true;
	try {
		const name = await call(
			"consbiz.bank_app.save_account",
			{
				company: company.value,
				account_name: account_name.value,
				bank: bank.value,
				account: account.value,
				bank_account_no: bank_account_no.value,
				is_default: Number(is_default.value),
				new_bank: Number(new_bank.value),
				name: props.doc?.name,
				modified: props.doc?.modified,
			},
			{ post: true }
		);
		emit("saved", name);
	} catch (e) {
		show_error(e);
	} finally {
		saving.value = false;
	}
}
</script>
