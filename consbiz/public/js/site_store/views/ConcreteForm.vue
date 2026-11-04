<template>
	<div class="ss-has-bar">
		<TopBar
			:title="doc.name ? doc.task_name || doc.wbs || doc.name : 'เทคอนกรีต'"
			:subtitle="doc.name || 'บันทึกใหม่'"
			back_to="concrete"
		>
			<template #actions>
				<span v-if="readonly" class="ss-tag tone-green">ส่งแล้ว</span>
				<span v-else-if="doc.name" class="ss-tag tone-amber">ร่าง</span>
			</template>
		</TopBar>

		<div class="ss-content">
			<Skeleton v-if="!setup" :rows="3" />
			<template v-else>
				<div class="ss-split">
					<div class="ss-split-main">
						<div class="ss-form">
							<Picker
								v-if="!readonly"
								v-model="doc.wbs"
								label="งาน (WBS)"
								:options="setup.wbs"
								required
								@select="(o) => (doc.task_name = o.label)"
							/>
							<div v-else class="ss-facts">
								<div class="ss-fact">
									<span>งาน</span><b>{{ doc.wbs }} {{ doc.task_name }}</b>
								</div>
							</div>
							<div class="ss-form-row">
								<label class="ss-field">
									<span class="ss-field-label">ตำแหน่ง</span>
									<input
										v-model="doc.location"
										class="ss-input"
										placeholder="เช่น ฐานราก F3"
										:disabled="readonly"
									/>
								</label>
								<label class="ss-field">
									<span class="ss-field-label">วันที่เท<em>*</em></span>
									<input
										v-model="doc.date"
										class="ss-input"
										type="date"
										:disabled="readonly"
									/>
								</label>
							</div>
							<Picker
								v-model="doc.concrete_item"
								label="ชนิดคอนกรีต"
								:options="setup.items"
								remote="Item"
								:display_value="doc.concrete_item_name"
								required
								:class="{ 'is-readonly': readonly }"
								@select="(o) => (doc.concrete_item_name = o.label)"
							/>
							<div class="ss-form-row">
								<label class="ss-field">
									<span class="ss-field-label">กำลังอัด</span>
									<input
										v-model="doc.strength"
										class="ss-input"
										placeholder="240 ksc"
										:disabled="readonly"
									/>
								</label>
								<label class="ss-field">
									<span class="ss-field-label">ตามแผน (คิว)</span>
									<input
										v-model.number="doc.planned_qty"
										class="ss-input"
										type="number"
										inputmode="decimal"
										:disabled="readonly"
									/>
								</label>
							</div>
							<Picker
								v-model="doc.supplier"
								label="ผู้ขาย / แพลนท์"
								:options="setup.suppliers"
								remote="Supplier"
								:display_value="doc.supplier_name"
								clearable
								:class="{ 'is-readonly': readonly }"
								@select="(o) => (doc.supplier_name = o.label)"
							/>
							<label
								class="ss-toggle"
								:class="{ 'is-on': doc.employer_supplied, 'is-readonly': readonly }"
							>
								<input
									v-model="doc.employer_supplied"
									type="checkbox"
									:true-value="1"
									:false-value="0"
									:disabled="readonly"
								/>
								<span class="ss-toggle-track"><span></span></span>
								<span>
									<b>ผู้ว่าจ้างจัดหา</b>
									<small
										>ค่าตั้งต้นของตั๋วที่เพิ่มใหม่ (หักงวดผู้ว่าจ้างตามปริมาณจริง)</small
									>
								</span>
							</label>
						</div>
					</div>
					<aside class="ss-split-side">
						<h2 class="ss-section-title">
							ตั๋วรถ ({{ doc.tickets.length }})
							<span class="ss-section-total">{{ num(total) }} คิว</span>
						</h2>
						<div
							v-if="doc.planned_qty"
							class="ss-progress ss-progress--lg"
							:class="{ 'is-over': total > doc.planned_qty }"
						>
							<span
								:style="{ width: `${Math.min((total / doc.planned_qty) * 100, 100)}%` }"
							></span>
							<em>{{ Math.round((total / doc.planned_qty) * 100) }}% ของแผน</em>
						</div>
						<TransitionGroup tag="div" class="ss-list" name="ss-list">
							<button
								v-for="(t, i) in doc.tickets"
								:key="t._key"
								type="button"
								class="ss-card ss-card--row ss-ticket"
								:style="{ '--i': i }"
								@click="edit_ticket(t)"
							>
								<span class="ss-ticket-no">#{{ i + 1 }}</span>
								<span class="ss-card-main">
									<span class="ss-card-title">ตั๋ว {{ t.ticket_no }}</span>
									<span class="ss-card-meta">
										<template v-if="t.vehicle_no">{{ t.vehicle_no }} · </template>
										{{ short_time(t.arrive_time)
										}}<template v-if="t.slump"> · slump {{ t.slump }}</template>
										<span v-if="t.employer_supplied" class="ss-tag tone-violet"
											>ผู้ว่าจ้าง</span
										>
									</span>
								</span>
								<span class="ss-qty"
									><b>{{ num(t.qty) }}</b
									><small>คิว</small></span
								>
							</button>
						</TransitionGroup>
						<button v-if="!readonly" type="button" class="ss-add-row" @click="new_ticket">
							<Icon name="plus" :size="20" :stroke="2.6" /> เพิ่มตั๋วรถ
						</button>

						<label v-if="!readonly || doc.remarks" class="ss-field" style="margin-top: 16px">
							<span class="ss-field-label">หมายเหตุ</span>
							<textarea
								v-model="doc.remarks"
								class="ss-input"
								rows="2"
								:disabled="readonly"
							></textarea>
						</label>
					</aside>
				</div>
			</template>
		</div>

		<Teleport to="#ss-layer">
			<Transition name="ss-bar">
				<div v-if="setup && !readonly" class="ss-bottom-bar">
					<button
						type="button"
						class="ss-btn ss-btn--ghost ss-btn--lg"
						:disabled="saving"
						@click="save(0)"
					>
						บันทึกร่าง
					</button>
					<button
						type="button"
						class="ss-btn ss-btn--primary ss-btn--lg ss-grow"
						:disabled="saving || !doc.tickets.length"
						@click="save(1)"
					>
						<span v-if="saving" class="ss-spinner"></span>
						<template v-else>ยืนยัน {{ num(total) }} คิว</template>
					</button>
				</div>
			</Transition>
		</Teleport>

		<Sheet :open="!!ticket" :title="ticket?._new ? 'เพิ่มตั๋วรถ' : 'ตั๋วรถ'" @close="ticket = null">
			<div v-if="ticket" class="ss-form">
				<div class="ss-form-row">
					<label class="ss-field">
						<span class="ss-field-label">เลขตั๋ว<em>*</em></span>
						<input
							ref="ticket_input"
							v-model="ticket.ticket_no"
							class="ss-input"
							inputmode="numeric"
							:disabled="readonly"
						/>
					</label>
					<label class="ss-field">
						<span class="ss-field-label">ทะเบียนรถ</span>
						<input v-model="ticket.vehicle_no" class="ss-input" :disabled="readonly" />
					</label>
				</div>
				<div class="ss-field">
					<span class="ss-field-label">ปริมาณ (คิว)<em>*</em></span>
					<Stepper v-model="ticket.qty" :step="0.5" class="ss-stepper--xl" />
					<div class="ss-quick">
						<button
							v-for="q in [3, 4, 5, 5.5, 6]"
							:key="q"
							type="button"
							class="ss-reason"
							:class="{ 'is-active': ticket.qty === q }"
							@click="ticket.qty = q"
						>
							{{ q }}
						</button>
					</div>
				</div>
				<div class="ss-form-row">
					<label class="ss-field">
						<span class="ss-field-label">มาถึง</span>
						<input
							v-model="ticket.arrive_time"
							class="ss-input"
							type="time"
							:disabled="readonly"
						/>
					</label>
					<label class="ss-field">
						<span class="ss-field-label">เทเสร็จ</span>
						<input
							v-model="ticket.finish_time"
							class="ss-input"
							type="time"
							:disabled="readonly"
						/>
					</label>
				</div>
				<div class="ss-form-row">
					<label class="ss-field">
						<span class="ss-field-label">Slump (ซม.)</span>
						<input
							v-model.number="ticket.slump"
							class="ss-input"
							type="number"
							inputmode="decimal"
							:disabled="readonly"
						/>
					</label>
					<label class="ss-field">
						<span class="ss-field-label">เก็บตัวอย่าง (ก้อน)</span>
						<input
							v-model.number="ticket.samples"
							class="ss-input"
							type="number"
							inputmode="numeric"
							:disabled="readonly"
						/>
					</label>
				</div>
				<label class="ss-toggle" :class="{ 'is-on': ticket.employer_supplied }">
					<input
						v-model="ticket.employer_supplied"
						type="checkbox"
						:true-value="1"
						:false-value="0"
						:disabled="readonly"
					/>
					<span class="ss-toggle-track"><span></span></span>
					<span><b>ผู้ว่าจ้างจัดหา</b></span>
				</label>
				<label class="ss-field">
					<span class="ss-field-label">หมายเหตุ</span>
					<input
						v-model="ticket.remarks"
						class="ss-input"
						placeholder="เช่น เศษนำไปเทที่ ..."
						:disabled="readonly"
					/>
				</label>
			</div>
			<template v-if="!readonly" #footer>
				<div class="ss-sheet-actions">
					<button
						v-if="!ticket?._new"
						type="button"
						class="ss-btn ss-btn--ghost-danger"
						@click="remove_ticket"
					>
						<Icon name="trash" :size="18" />
					</button>
					<button
						type="button"
						class="ss-btn ss-btn--primary ss-btn--block ss-btn--lg"
						:disabled="!ticket?.ticket_no || !ticket?.qty"
						@click="save_ticket"
					>
						{{ ticket?._new ? "เพิ่มตั๋ว" : "บันทึก" }}
					</button>
				</div>
			</template>
		</Sheet>
	</div>
</template>

<script setup>
import { computed, inject, nextTick, reactive, ref } from "vue";
import Icon from "../components/Icon.vue";
import TopBar from "../components/TopBar.vue";
import Skeleton from "../components/Skeleton.vue";
import Sheet from "../components/Sheet.vue";
import Stepper from "../components/Stepper.vue";
import Picker from "../components/Picker.vue";
import {
	back,
	call,
	celebrate,
	go,
	now_time,
	num,
	post,
	short_time,
	show_error,
	state,
	toast,
	today,
	vibrate,
} from "../api.js";

const reload_summary = inject("reload_summary");
const params = state.route.params;
let key = 0;

const setup = ref(null);
const saving = ref(false);
const ticket = ref(null);
const ticket_input = ref(null);
const doc = reactive({
	name: null,
	docstatus: 0,
	wbs: null,
	task_name: "",
	location: "",
	date: today(),
	concrete_item: null,
	concrete_item_name: "",
	strength: "",
	supplier: null,
	supplier_name: "",
	employer_supplied: 0,
	planned_qty: null,
	remarks: "",
	tickets: [],
});

const readonly = computed(() => doc.docstatus === 1);
const total = computed(() => doc.tickets.reduce((s, t) => s + (Number(t.qty) || 0), 0));

function new_ticket() {
	const last = doc.tickets[doc.tickets.length - 1];
	const next_no =
		last && /^\d+$/.test(last.ticket_no)
			? String(Number(last.ticket_no) + 1).padStart(last.ticket_no.length, "0")
			: "";
	ticket.value = {
		_new: true,
		_key: ++key,
		ticket_no: next_no,
		vehicle_no: "",
		arrive_time: now_time(),
		finish_time: "",
		qty: last?.qty || 5,
		slump: last?.slump || null,
		samples: null,
		employer_supplied: doc.employer_supplied,
		remarks: "",
	};
	nextTick(() => setTimeout(() => ticket_input.value?.focus(), 320));
}

function edit_ticket(t) {
	ticket.value = { ...t, _new: false };
}

function save_ticket() {
	const t = ticket.value;
	if (doc.tickets.some((x) => x._key !== t._key && x.ticket_no === t.ticket_no)) {
		show_error(new Error(`เลขตั๋ว ${t.ticket_no} ซ้ำกับตั๋วอื่นในใบนี้`));
		return;
	}
	vibrate(10);
	const index = doc.tickets.findIndex((x) => x._key === t._key);
	const clean = { ...t, _new: false };
	if (index >= 0) doc.tickets.splice(index, 1, clean);
	else doc.tickets.push(clean);
	ticket.value = null;
}

function remove_ticket() {
	doc.tickets = doc.tickets.filter((x) => x._key !== ticket.value._key);
	ticket.value = null;
}

async function save(submit) {
	if (!doc.wbs || !doc.concrete_item || !doc.date) {
		show_error(new Error("กรอกงาน (WBS) วันที่ และชนิดคอนกรีตก่อน"));
		return;
	}
	saving.value = true;
	try {
		const result = await post("save_concrete", {
			project: state.project.name,
			submit,
			data: {
				...doc,
				tickets: doc.tickets.map(({ _key, _new, ...t }) => t),
			},
		});
		reload_summary();
		if (submit) {
			await celebrate("บันทึกคอนกรีตแล้ว", `${num(total.value)} คิว · ${result.name}`);
			back("concrete");
		} else {
			doc.name = result.name;
			show_saved();
			if (!params.name) go("concrete-form", { name: result.name }, { replace: true });
		}
	} catch (error) {
		show_error(error);
	} finally {
		saving.value = false;
	}
}

function show_saved() {
	toast("บันทึกร่างแล้ว", "success");
}

async function load() {
	try {
		const [s, existing] = await Promise.all([
			call("get_concrete_setup", { project: state.project.name }),
			params.name ? call("get_concrete_doc", { name: params.name }) : null,
		]);
		if (existing) {
			Object.assign(doc, existing, {
				tickets: (existing.tickets || []).map((t) => ({ ...t, _key: ++key })),
			});
		} else if (s.suppliers.length) {
			doc.supplier = s.suppliers[0].value;
			doc.supplier_name = s.suppliers[0].label;
			if (s.items.length) {
				doc.concrete_item = s.items[0].value;
				doc.concrete_item_name = s.items[0].label;
			}
		}
		setup.value = s;
	} catch (error) {
		show_error(error);
		back("concrete");
	}
}
load();
</script>
