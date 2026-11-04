<template>
	<div class="ss-has-bar">
		<TopBar title="ยืมอุปกรณ์" :subtitle="state.project?.project_name" back_to="borrow" />

		<div class="ss-content">
			<Skeleton v-if="!setup" :rows="3" />
			<template v-else>
				<div class="ss-split">
					<div class="ss-split-main">
						<h2 class="ss-section-title ss-section-title--first">ผู้ยืม</h2>
						<Segmented
							v-model="form.borrower_type"
							:options="[
								{ value: 'Employee', label: 'พนักงาน' },
								{ value: 'Subcontractor', label: 'ผู้รับเหมา' },
								{ value: 'Worker', label: 'คนงาน' },
							]"
						/>
						<div class="ss-form">
							<Transition name="ss-fade" mode="out-in">
								<Picker
									v-if="form.borrower_type === 'Employee'"
									key="emp"
									v-model="form.employee"
									label="พนักงาน"
									remote="Employee"
									required
								/>
								<label
									v-else-if="form.borrower_type === 'Worker'"
									key="worker"
									class="ss-field"
								>
									<span class="ss-field-label">ชื่อคนงาน<em>*</em></span>
									<input
										v-model="form.worker_name"
										class="ss-input"
										placeholder="ชื่อ-นามสกุล"
									/>
								</label>
								<span v-else key="none"></span>
							</Transition>
							<Picker
								v-if="form.borrower_type !== 'Employee'"
								v-model="form.supplier"
								:label="
									form.borrower_type === 'Worker'
										? 'สังกัดผู้รับเหมา (ถ้ามี)'
										: 'ผู้รับเหมา'
								"
								remote="Supplier"
								:required="form.borrower_type === 'Subcontractor'"
								clearable
							/>
							<label class="ss-field">
								<span class="ss-field-label">เบอร์ติดต่อ</span>
								<input v-model="form.contact" class="ss-input" type="tel" inputmode="tel" />
							</label>
							<div class="ss-field">
								<span class="ss-field-label">กำหนดคืน</span>
								<div class="ss-quick ss-quick--left">
									<button
										v-for="d in DUE"
										:key="d.days"
										type="button"
										class="ss-reason"
										:class="{ 'is-active': form.due_date === add_days(d.days) }"
										@click="form.due_date = add_days(d.days)"
									>
										{{ d.label }}
									</button>
								</div>
								<input v-model="form.due_date" class="ss-input" type="date" :min="today()" />
							</div>
						</div>

						<h2 class="ss-section-title">
							อุปกรณ์ ({{ lines.length }})
							<button type="button" class="ss-link" @click="picking = true">+ เพิ่ม</button>
						</h2>
						<TransitionGroup tag="div" class="ss-list" name="ss-list">
							<div v-for="line in lines" :key="line.item_code" class="ss-card ss-card--row">
								<span class="ss-card-main">
									<span class="ss-card-title">{{ line.item_name }}</span>
									<span class="ss-card-meta"
										>ในคลัง {{ num(line.available) }} {{ line.uom }}</span
									>
								</span>
								<Stepper
									v-model="line.qty"
									:max="line.available"
									:min="0"
									@update:model-value="(v) => !v && remove(line)"
								/>
							</div>
						</TransitionGroup>
						<button type="button" class="ss-add-row" @click="picking = true">
							<Icon name="plus" :size="20" :stroke="2.6" /> เลือกอุปกรณ์
						</button>
					</div>
					<aside class="ss-split-side">
						<h2 class="ss-section-title">ส่งมอบ</h2>
						<div class="ss-form">
							<div class="ss-field">
								<span class="ss-field-label">ลายเซ็นผู้ยืม</span>
								<SignaturePad
									v-model="form.borrower_signature"
									hint="ให้ผู้ยืมเซ็นรับอุปกรณ์"
								/>
							</div>
							<div class="ss-field">
								<span class="ss-field-label">รูปอุปกรณ์ตอนส่งมอบ</span>
								<PhotoInput v-model="photos" :max="1" />
							</div>
							<label class="ss-field">
								<span class="ss-field-label">หมายเหตุ</span>
								<input v-model="form.remarks" class="ss-input" />
							</label>
							<details class="ss-details">
								<summary>คลัง</summary>
								<Picker
									v-model="form.source_warehouse"
									label="คลังต้นทาง"
									:options="setup.warehouses"
									required
								/>
								<Picker
									v-model="form.loan_warehouse"
									label="คลังอุปกรณ์ระหว่างยืม"
									:options="setup.warehouses"
									required
								/>
							</details>
						</div>
					</aside>
				</div>
			</template>
		</div>

		<Teleport to="#ss-layer">
			<Transition name="ss-bar">
				<div v-if="setup" class="ss-bottom-bar">
					<div class="ss-bar-summary">
						<b>{{ lines.length }}</b> รายการ
					</div>
					<button
						type="button"
						class="ss-btn ss-btn--primary ss-btn--lg"
						:disabled="!ready || saving"
						@click="submit"
					>
						<span v-if="saving" class="ss-spinner"></span>
						<template v-else>ส่งมอบอุปกรณ์</template>
					</button>
				</div>
			</Transition>
		</Teleport>

		<Sheet
			:open="picking"
			title="เลือกอุปกรณ์"
			:subtitle="form.source_warehouse"
			full
			@close="picking = false"
		>
			<div class="ss-search">
				<Icon name="search" :size="18" />
				<input v-model="txt" type="search" placeholder="ค้นหาอุปกรณ์ในคลัง" />
			</div>
			<div class="ss-options">
				<button
					v-for="it in choices"
					:key="it.item_code"
					type="button"
					class="ss-option"
					:class="{ 'is-active': lines.some((l) => l.item_code === it.item_code) }"
					@click="toggle(it)"
				>
					<span class="ss-option-main">
						<span class="ss-option-label">{{ it.item_name }}</span>
						<span class="ss-option-desc"
							>{{ it.item_code }} · มี {{ num(it.qty) }} {{ it.uom }}</span
						>
					</span>
					<Icon v-if="lines.some((l) => l.item_code === it.item_code)" name="check" :size="18" />
				</button>
				<div v-if="!choices.length" class="ss-options-note">ไม่พบอุปกรณ์ในคลังนี้</div>
			</div>
			<template #footer>
				<button
					type="button"
					class="ss-btn ss-btn--primary ss-btn--block ss-btn--lg"
					@click="picking = false"
				>
					เสร็จ ({{ lines.length }})
				</button>
			</template>
		</Sheet>
	</div>
</template>

<script setup>
import { computed, inject, reactive, ref, watch } from "vue";
import Icon from "../components/Icon.vue";
import TopBar from "../components/TopBar.vue";
import Skeleton from "../components/Skeleton.vue";
import Segmented from "../components/Segmented.vue";
import Stepper from "../components/Stepper.vue";
import Picker from "../components/Picker.vue";
import Sheet from "../components/Sheet.vue";
import SignaturePad from "../components/SignaturePad.vue";
import PhotoInput from "../components/PhotoInput.vue";
import { back, call, celebrate, go, num, post, show_error, state, today, vibrate } from "../api.js";

const DUE = [
	{ days: 0, label: "วันนี้" },
	{ days: 1, label: "พรุ่งนี้" },
	{ days: 3, label: "3 วัน" },
	{ days: 7, label: "1 สัปดาห์" },
	{ days: 30, label: "1 เดือน" },
];

const reload_summary = inject("reload_summary");
const setup = ref(null);
const items = ref([]);
const lines = ref([]);
const photos = ref([]);
const picking = ref(false);
const txt = ref("");
const saving = ref(false);
const form = reactive({
	borrower_type: "Employee",
	employee: null,
	worker_name: "",
	supplier: null,
	contact: "",
	due_date: add_days(0),
	source_warehouse: null,
	loan_warehouse: null,
	borrower_signature: null,
	remarks: "",
});

function add_days(days) {
	const d = new Date(today());
	d.setDate(d.getDate() + days);
	return d.toISOString().slice(0, 10);
}

const choices = computed(() => {
	const q = txt.value.trim().toLowerCase();
	return items.value
		.filter((i) => !q || `${i.item_name} ${i.item_code}`.toLowerCase().includes(q))
		.slice(0, 200);
});

const ready = computed(() => {
	const who =
		(form.borrower_type === "Employee" && form.employee) ||
		(form.borrower_type === "Subcontractor" && form.supplier) ||
		(form.borrower_type === "Worker" && form.worker_name.trim());
	return (
		who &&
		lines.value.some((l) => l.qty > 0) &&
		form.source_warehouse &&
		form.loan_warehouse &&
		!photos.value.some((p) => p.uploading)
	);
});

function toggle(item) {
	vibrate(8);
	if (lines.value.some((l) => l.item_code === item.item_code)) remove(item);
	else
		lines.value.push({
			item_code: item.item_code,
			item_name: item.item_name,
			uom: item.uom,
			available: item.qty,
			qty: 1,
		});
}

function remove(item) {
	lines.value = lines.value.filter((l) => l.item_code !== item.item_code);
}

watch(
	() => form.source_warehouse,
	async (warehouse, old) => {
		if (!warehouse || !old) return;
		lines.value = [];
		items.value = await call("warehouse_items", { warehouse });
	}
);

async function submit() {
	saving.value = true;
	try {
		const result = await post("submit_borrowing", {
			project: state.project.name,
			data: {
				...form,
				photo: photos.value[0]?.file_url,
				items: lines.value
					.filter((l) => l.qty > 0)
					.map((l) => ({ item_code: l.item_code, qty: l.qty })),
			},
		});
		reload_summary();
		await celebrate("ส่งมอบอุปกรณ์แล้ว", result.name);
		go("borrow-detail", { name: result.name }, { replace: true });
	} catch (error) {
		show_error(error);
	} finally {
		saving.value = false;
	}
}

call("get_borrow_setup", { project: state.project.name })
	.then((data) => {
		setup.value = data;
		items.value = data.items;
		form.source_warehouse = data.source_warehouse;
		form.loan_warehouse = data.loan_warehouse;
	})
	.catch((error) => {
		show_error(error);
		back("borrow");
	});
</script>
