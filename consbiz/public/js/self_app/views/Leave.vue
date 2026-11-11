<!-- ขอลา: วันลาคงเหลือตามประเภท (Leave Allocation ของ HRMS) + ใบลาของตัวเอง
     ส่งใบลา = Leave Application สถานะ Open ผู้อนุมัติการลา (ตาม HRMS) อนุมัติ/Submit ในระบบ
     ใบที่ยังไม่พิจารณาถอนได้ (ลบ) จำนวนวันคำนวณที่ server (หักวันหยุดตามประเภทการลา) -->
<template>
	<div>
		<TopBar title="ลา" no_project>
			<template #actions>
				<button
					v-if="!wide"
					type="button"
					class="ss-icon-btn"
					:class="{ 'is-spinning': loading }"
					aria-label="โหลดใหม่"
					@click="load"
				>
					<Icon name="refresh" :size="20" />
				</button>
			</template>
		</TopBar>

		<div class="ss-content">
			<Skeleton v-if="data === null" :rows="3" />
			<template v-else>
				<div v-if="data.balances.length" class="ss-stats">
					<div
						v-for="(b, i) in data.balances"
						:key="b.leave_type"
						class="ss-stat tone-green"
						:style="{ '--i': i }"
					>
						<span class="ss-stat-icon"><Icon name="calendar" :size="20" /></span>
						<span class="ss-stat-value">{{ days_text(b.remaining_leaves) }}</span>
						<span class="ss-stat-label">{{ b.leave_type }} คงเหลือ</span>
						<span v-if="b.leaves_pending_approval" class="ss-stat-alert"
							>รออนุมัติ {{ days_text(b.leaves_pending_approval) }} วัน</span
						>
					</div>
				</div>

				<div v-if="wide" class="ss-list-head">
					<StatusTabs v-model="tab" :options="tabs" />
					<div class="ss-list-tools">
						<button
							type="button"
							class="ss-icon-btn"
							:class="{ 'is-spinning': loading }"
							aria-label="โหลดใหม่"
							@click="load"
						>
							<Icon name="refresh" :size="17" />
						</button>
						<button type="button" class="ss-btn ss-btn--primary ss-list-create" @click="open_form">
							<Icon name="plus" :size="18" :stroke="2.6" />
							<span>ขอลา</span>
						</button>
					</div>
				</div>
				<div v-else class="ss-tabs">
					<button
						v-for="t in tabs"
						:key="t.value"
						type="button"
						class="ss-tab"
						:class="{ 'is-active': tab === t.value }"
						@click="tab = t.value"
					>
						{{ t.label }} <span class="ss-tab-count">{{ t.count }}</span>
					</button>
				</div>

				<Empty
					v-if="!shown.length"
					icon="calendar"
					:title="data.applications.length ? 'ไม่มีใบลาในสถานะนี้' : 'ยังไม่มีใบลา'"
					text="กดปุ่ม ขอลา เพื่อส่งใบลาให้ผู้อนุมัติ"
				/>
				<div v-else class="ss-list">
					<button
						v-for="(row, i) in shown"
						:key="row.name"
						type="button"
						class="ss-card ss-card--row"
						:style="{ '--i': i }"
						@click="viewing = row"
					>
						<span class="ss-avatar" :class="`tone-${STATUS[row.status]?.tone || 'gray'}`">
							<Icon name="calendar" :size="18" />
						</span>
						<span class="ss-card-main">
							<span class="ss-card-title">{{ row.leave_type }}</span>
							<span class="ss-card-meta">{{ range_text(row) }}</span>
						</span>
						<span class="ss-leave-side">
							<span class="ss-tag" :class="`tone-${STATUS[row.status]?.tone || 'gray'}`">{{
								STATUS[row.status]?.label || row.status
							}}</span>
							<small>{{ days_text(row.total_leave_days) }} วัน</small>
						</span>
					</button>
				</div>
			</template>
		</div>

		<Teleport to="#ss-layer">
			<Transition name="ss-pop">
				<button v-if="data && !wide" type="button" class="ss-fab" @click="open_form">
					<Icon name="plus" :size="26" :stroke="2.6" />
					<span>ขอลา</span>
				</button>
			</Transition>
		</Teleport>

		<Sheet
			:open="form_open"
			title="ขอลา"
			:subtitle="approver_text"
			@close="form_open = false"
		>
			<div class="ss-field">
				<span class="ss-field-label">ประเภทการลา<em>*</em></span>
				<SelectBox v-model="form.leave_type" :options="type_options" placeholder="เลือกประเภทการลา" />
			</div>
			<div class="ss-leave-dates">
				<div class="ss-field">
					<span class="ss-field-label">ตั้งแต่วันที่<em>*</em></span>
					<DateInput v-model="form.from_date" @change="on_from" />
				</div>
				<div class="ss-field">
					<span class="ss-field-label">ถึงวันที่<em>*</em></span>
					<DateInput v-model="form.to_date" :min="form.from_date" />
				</div>
			</div>
			<label class="ss-toggle" :class="{ 'is-on': form.half_day }">
				<input v-model="form.half_day" type="checkbox" />
				<span class="ss-toggle-track"><span></span></span>
				<span>ลาครึ่งวัน</span>
			</label>
			<div v-if="form.half_day && form.from_date !== form.to_date" class="ss-field">
				<span class="ss-field-label">วันที่ลาครึ่งวัน</span>
				<DateInput v-model="form.half_day_date" :min="form.from_date" />
			</div>
			<label class="ss-field">
				<span class="ss-field-label">เหตุผล</span>
				<textarea v-model="form.description" class="ss-input" rows="3" placeholder="เช่น ไปพบแพทย์"></textarea>
			</label>
			<div class="ss-field">
				<span class="ss-field-label">เอกสารประกอบ (เช่น ใบรับรองแพทย์)</span>
				<PhotoInput v-model="form.files" :max="3" label="แนบรูป" />
			</div>
			<div class="ss-facts">
				<div class="ss-fact">
					<span>จำนวนวันลา</span>
					<b>
						<span v-if="counting" class="ss-spinner"></span>
						<template v-else-if="leave_count != null">{{ days_text(leave_count) }} วัน</template>
						<template v-else>—</template>
					</b>
				</div>
				<div v-if="selected_balance" class="ss-fact">
					<span>คงเหลือ</span><b>{{ days_text(selected_balance.remaining_leaves) }} วัน</b>
				</div>
			</div>
			<template #footer>
				<button
					type="button"
					class="ss-btn ss-btn--primary ss-btn--block ss-btn--lg"
					:disabled="busy || !can_submit"
					@click="submit"
				>
					<span v-if="busy" class="ss-spinner"></span>
					<span>ส่งใบลา</span>
				</button>
			</template>
		</Sheet>

		<Sheet
			:open="!!viewing"
			:title="viewing?.leave_type"
			:subtitle="viewing?.name"
			@close="viewing = null"
		>
			<div v-if="viewing" class="ss-facts">
				<div class="ss-fact">
					<span>สถานะ</span>
					<b><span class="ss-tag" :class="`tone-${STATUS[viewing.status]?.tone || 'gray'}`">{{
						STATUS[viewing.status]?.label || viewing.status
					}}</span></b>
				</div>
				<div class="ss-fact"><span>วันที่</span><b>{{ range_text(viewing) }}</b></div>
				<div class="ss-fact"><span>จำนวน</span><b>{{ days_text(viewing.total_leave_days) }} วัน</b></div>
				<div v-if="viewing.leave_approver && viewing.docstatus === 1" class="ss-fact">
					<span>ผู้อนุมัติ</span><b>{{ viewing.leave_approver_name || viewing.leave_approver }}</b>
				</div>
				<div v-if="viewing.description" class="ss-fact"><span>เหตุผล</span><b>{{ viewing.description }}</b></div>
				<div class="ss-fact"><span>ส่งเมื่อ</span><b>{{ thai_date(viewing.posting_date, { year: true }) }}</b></div>
			</div>
			<template v-if="viewing?.can_delete" #footer>
				<button
					type="button"
					class="ss-btn ss-btn--ghost-danger ss-btn--block ss-btn--lg"
					:disabled="busy"
					@click="withdraw(viewing)"
				>
					<Icon name="trash" :size="18" />
					<span>ถอนใบลา</span>
				</button>
			</template>
		</Sheet>
	</div>
</template>

<script setup>
import { computed, reactive, ref, watch } from "vue";
import Icon from "../../shared/components/Icon.vue";
import TopBar from "../../shared/components/TopBar.vue";
import Skeleton from "../../shared/components/Skeleton.vue";
import Empty from "../../shared/components/Empty.vue";
import Sheet from "../../shared/components/Sheet.vue";
import SelectBox from "../../shared/components/SelectBox.vue";
import DateInput from "../../shared/components/DateInput.vue";
import PhotoInput from "../../shared/components/PhotoInput.vue";
import StatusTabs from "../../shared/components/StatusTabs.vue";
import { use_wide } from "../../shared/table.js";
import { call, celebrate, post, show_error, thai_date, toast, today } from "../../shared/api.js";

const API = "consbiz.self_service.";
const STATUS = {
	Open: { label: "รออนุมัติ", tone: "amber" },
	Approved: { label: "อนุมัติ", tone: "green" },
	Rejected: { label: "ไม่อนุมัติ", tone: "rose" },
	Cancelled: { label: "ยกเลิก", tone: "gray" },
};

const data = ref(null);
// ผู้อนุมัติ = Role Leave Approver ในโครงการเดียวกัน: คนเดียวแสดงชื่อ หลายคนแสดงจำนวน
const approver_text = computed(() => {
	if (data.value?.leave_approver_name) return `ผู้อนุมัติ: ${data.value.leave_approver_name}`;
	if (data.value?.approver_count) return `ผู้อนุมัติ ${data.value.approver_count} คน (คนใดคนหนึ่งอนุมัติ)`;
	return "ยังไม่มีผู้อนุมัติการลา ติดต่อฝ่ายบุคคล";
});
const loading = ref(false);
const busy = ref(false);
const wide = use_wide();
const tab = ref("all");
const viewing = ref(null);

const tabs = computed(() => {
	const rows = data.value?.applications || [];
	const count = (status) => rows.filter((r) => r.status === status).length;
	return [
		{ value: "all", label: "ทั้งหมด", count: rows.length },
		{ value: "Open", label: "รออนุมัติ", count: count("Open") },
		{ value: "Approved", label: "อนุมัติ", count: count("Approved") },
		{ value: "Rejected", label: "ไม่อนุมัติ", count: count("Rejected") },
	];
});
const shown = computed(() =>
	(data.value?.applications || []).filter((r) => tab.value === "all" || r.status === tab.value)
);

const days_text = (value) => {
	const n = Number(value) || 0;
	return Number.isInteger(n) ? String(n) : n.toFixed(1);
};
function range_text(row) {
	const from = thai_date(row.from_date, { year: true });
	const text = row.from_date === row.to_date ? from : `${from} – ${thai_date(row.to_date, { year: true })}`;
	return row.half_day ? `${text} (ครึ่งวัน)` : text;
}

async function load() {
	loading.value = true;
	try {
		data.value = await call(`${API}get_leave_data`);
	} catch (error) {
		show_error(error);
		data.value ??= { balances: [], leave_types: [], applications: [] };
	} finally {
		loading.value = false;
	}
}
load();

// ---------------------------------------------------------------- ฟอร์มขอลา

const form_open = ref(false);
const form = reactive({});
const leave_count = ref(null);
const counting = ref(false);

const type_options = computed(() =>
	(data.value?.leave_types || []).map((name) => {
		const balance = data.value.balances.find((b) => b.leave_type === name);
		return {
			value: name,
			label: name,
			description: balance
				? `คงเหลือ ${days_text(balance.remaining_leaves)} วัน`
				: data.value.lwps.includes(name)
				? "ไม่รับค่าจ้าง"
				: "",
		};
	})
);
const selected_balance = computed(() =>
	data.value?.balances.find((b) => b.leave_type === form.leave_type)
);
const can_submit = computed(
	() => form.leave_type && form.from_date && form.to_date && form.to_date >= form.from_date && leave_count.value > 0
);

function open_form() {
	Object.assign(form, {
		leave_type: data.value?.leave_types.length === 1 ? data.value.leave_types[0] : null,
		from_date: today(),
		to_date: today(),
		half_day: false,
		half_day_date: today(),
		description: "",
		files: [],
	});
	form_open.value = true;
}

function on_from(value) {
	if (!form.to_date || form.to_date < value) form.to_date = value;
	form.half_day_date = value;
}

function payload() {
	return {
		leave_type: form.leave_type,
		from_date: form.from_date,
		to_date: form.to_date,
		half_day: form.half_day ? 1 : 0,
		half_day_date: form.from_date === form.to_date ? form.from_date : form.half_day_date,
		description: form.description,
	};
}

let count_stamp = 0;
watch(
	() => [form_open.value, form.leave_type, form.from_date, form.to_date, form.half_day, form.half_day_date],
	async () => {
		leave_count.value = null;
		if (!form_open.value || !form.leave_type || !form.from_date || !form.to_date) return;
		if (form.to_date < form.from_date) return;
		const stamp = ++count_stamp;
		counting.value = true;
		try {
			const days = await call(`${API}leave_days`, { data: payload() });
			if (stamp === count_stamp) leave_count.value = days;
		} catch (error) {
			if (stamp === count_stamp) show_error(error);
		} finally {
			if (stamp === count_stamp) counting.value = false;
		}
	}
);

async function submit() {
	if (form.files.some((f) => f.uploading)) {
		toast("รอให้อัปโหลดรูปเสร็จก่อน", "warning");
		return;
	}
	busy.value = true;
	try {
		await post(`${API}apply_leave`, {
			data: payload(),
			files: form.files.map((f) => f.name).filter(Boolean),
		});
		form_open.value = false;
		celebrate("ส่งใบลาแล้ว", data.value.leave_approver_name ? `รอ ${data.value.leave_approver_name} อนุมัติ` : "");
		tab.value = "all";
		await load();
	} catch (error) {
		show_error(error);
	} finally {
		busy.value = false;
	}
}

async function withdraw(row) {
	busy.value = true;
	try {
		await post(`${API}delete_leave`, { name: row.name });
		viewing.value = null;
		toast("ถอนใบลาแล้ว", "success");
		await load();
	} catch (error) {
		show_error(error);
	} finally {
		busy.value = false;
	}
}
</script>
