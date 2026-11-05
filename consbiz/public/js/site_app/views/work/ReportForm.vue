<template>
	<div class="ss-has-bar">
		<TopBar :title="title" :subtitle="subtitle" back_to="reports" :back_params="back_params">
			<template #actions>
				<span v-if="doc?.name" class="ss-tag tone-gray">ร่าง</span>
			</template>
		</TopBar>

		<div class="ss-content">
			<Skeleton v-if="!setup" :rows="3" />
			<div v-else class="ss-wizard">
				<!-- ขั้นตอน: แตะย้อนไปขั้นที่ผ่านมาได้ จอกว้าง (≥1180) เป็นแถบซ้ายพร้อมสรุปของแต่ละขั้น -->
				<nav
					class="ss-steps"
					:style="{ '--count': steps.length, '--step': step }"
					aria-label="ขั้นตอน"
				>
					<button
						v-for="(s, i) in steps"
						:key="s.key"
						type="button"
						class="ss-step"
						:class="{ 'is-active': i === step, 'is-done': i < step }"
						:disabled="i > step && !can_jump(i)"
						@click="jump(i)"
					>
						<span class="ss-step-dot">
							<Icon v-if="i < step" name="check" :size="13" :stroke="3" />
							<template v-else>{{ i + 1 }}</template>
						</span>
						<span class="ss-step-text">
							<span class="ss-step-label">{{ s.label }}</span>
							<small class="ss-step-hint">{{ step_hint(s.key) }}</small>
						</span>
					</button>
					<p v-if="is_new" class="ss-steps-note">
						<Icon name="check" :size="13" :stroke="2.6" /> ร่างเก็บไว้ในเครื่องนี้ระหว่างกรอก
					</p>
				</nav>

				<Transition :name="`ss-step-${direction}`" mode="out-in">
					<!-- 1. ทั่วไป -->
					<div v-if="current === 'general'" key="general" class="ss-step-body">
						<div v-if="doc.status === 'Rejected'" class="ss-banner tone-rose">
							<Icon name="ban" :size="22" />
							<div>
								<div class="ss-banner-title">ไม่อนุมัติ: แก้ไขแล้วส่งใหม่</div>
								<div class="ss-banner-text">{{ doc.rejection_reason }}</div>
							</div>
						</div>
						<div v-if="same_day.length" class="ss-banner tone-blue">
							<Icon name="info" :size="22" />
							<div>
								<div class="ss-banner-title">
									วันนี้มีเอกสารแล้ว {{ same_day.length }} ฉบับ
								</div>
								<div class="ss-banner-text">
									{{ same_day.map((d) => `${d.name} (${d.owner_name})`).join(", ") }}
									· แบ่งกันลงได้หลายฉบับ
								</div>
							</div>
						</div>
						<div class="ss-form">
							<div class="ss-form-row">
								<label class="ss-field">
									<span class="ss-field-label">วันที่<em>*</em></span>
									<input
										v-model="doc.date"
										class="ss-input"
										type="date"
										@change="date_changed"
									/>
								</label>
								<label v-if="is_report" class="ss-field">
									<span class="ss-field-label">ผู้ควบคุมงาน</span>
									<input
										v-model="doc.supervisor_name"
										class="ss-input"
										placeholder="ชื่อผู้ลงนาม"
									/>
								</label>
								<label v-else class="ss-field">
									<span class="ss-field-label">ผู้ขออนุมัติ</span>
									<input
										v-model="doc.requested_by"
										class="ss-input"
										placeholder="ชื่อผู้ลงนาม"
									/>
								</label>
							</div>

							<template v-if="is_report">
								<div class="ss-field">
									<span class="ss-field-label">สภาพอากาศ</span>
									<div class="ss-choices">
										<button
											v-for="w in setup.weather_options"
											:key="w"
											type="button"
											class="ss-choice"
											:class="{ 'is-active': doc.weather === w }"
											@click="doc.weather = doc.weather === w ? null : w"
										>
											<Icon :name="weather_icon(w)" :size="16" /> {{ w }}
										</button>
									</div>
								</div>
								<label class="ss-field">
									<span class="ss-field-label">ผลกระทบต่องาน</span>
									<input
										v-model="doc.weather_impact"
										class="ss-input"
										placeholder="เช่น หยุดงานกลางแจ้ง 1 ชั่วโมง"
									/>
								</label>
								<div v-if="doc.daily_request" class="ss-facts">
									<div class="ss-fact">
										<span>ตามคำขออนุมัติ</span><b>{{ doc.daily_request }}</b>
									</div>
								</div>
							</template>
							<template v-else>
								<div class="ss-form-row">
									<label class="ss-field">
										<span class="ss-field-label">เริ่มงาน</span>
										<input v-model="doc.start_time" class="ss-input" type="time" />
									</label>
									<label class="ss-field">
										<span class="ss-field-label">เลิกงาน</span>
										<input v-model="doc.end_time" class="ss-input" type="time" />
									</label>
								</div>
								<Picker
									v-model="doc.approver"
									label="ผู้อนุมัติ"
									:options="approver_options"
									required
								/>
							</template>
						</div>
					</div>

					<!-- 2. งานที่ทำ / จะทำ -->
					<div v-else-if="current === 'items'" key="items" class="ss-step-body">
						<div class="ss-items-bar">
							<span class="ss-items-total">
								<small>{{ is_report ? "ความคืบหน้าโครงการวันนี้" : "จะเพิ่มขึ้น" }}</small>
								<b>+{{ pct(project_percent) }}%</b>
							</span>
							<button
								v-if="planned_to_add.length"
								type="button"
								class="ss-btn ss-btn--soft ss-btn--sm"
								@click="add_planned"
							>
								<Icon name="calendar" :size="15" /> งานตามแผน ({{ planned_to_add.length }})
							</button>
						</div>

						<Empty
							v-if="!doc.items.length"
							icon="list-checks"
							:title="is_report ? 'วันนี้ทำงานอะไรบ้าง' : 'จะทำงานอะไรบ้าง'"
							text="เพิ่มงานตามแผนของวันนี้ หรือเลือกงานจากแผนงาน"
						/>
						<TransitionGroup
							tag="div"
							class="ss-list ss-list--form ss-list--tasks"
							name="ss-list"
						>
							<div
								v-for="(row, i) in doc.items"
								:key="row.wbs"
								class="ss-card ss-task-row"
								:class="{ 'is-late': show_errors && row_error(row) }"
								:style="{ '--i': i }"
							>
								<div class="ss-task-info">
									<span class="ss-card-title">{{
										task_of(row).item_name || row.item_name
									}}</span>
									<span class="ss-card-meta"
										><i class="ss-wbs">{{ row.wbs }}</i>
										{{ task_of(row).group_path || row.group_path }}</span
									>
									<div class="ss-task-progress">
										<div class="ss-plan-bar ss-plan-bar--sm">
											<span
												class="ss-plan-bar-plan"
												:style="{
													width: `${clamp(prev_pct(row) + row_percent(row))}%`,
												}"
											></span>
											<span
												class="ss-plan-bar-actual"
												:style="{ width: `${clamp(prev_pct(row))}%` }"
											></span>
										</div>
										<div class="ss-late-foot">
											<span>ทำแล้ว {{ pct(prev_pct(row)) }}%</span>
											<span v-if="is_qty(row)"
												>คงเหลือ {{ num(remaining(row)) }}
												{{ task_of(row).uom }}</span
											>
											<span v-else>คงเหลือ {{ pct(100 - prev_pct(row)) }}%</span>
										</div>
									</div>
								</div>
								<button
									type="button"
									class="ss-icon-btn ss-icon-btn--sm ss-task-del"
									aria-label="ลบงาน"
									title="ลบงาน"
									@click="remove_row(row)"
								>
									<Icon name="trash" :size="17" />
								</button>

								<div class="ss-task-input">
									<Stepper
										v-if="is_qty(row)"
										v-model="row.qty"
										:step="qty_step(row)"
										:max="null"
									/>
									<Stepper v-else v-model="row.percent" :step="5" :max="100" />
									<span class="ss-task-unit">
										<b>{{ is_qty(row) ? task_of(row).uom || "หน่วย" : "%" }}</b>
										<small v-if="is_qty(row)">= {{ pct(row_percent(row)) }}%</small>
										<small v-else>งานเหมา</small>
									</span>
									<button
										type="button"
										class="ss-btn ss-btn--soft ss-btn--sm"
										@click="fill_rest(row)"
									>
										ครบ
									</button>
								</div>
								<div v-if="show_errors && row_error(row)" class="ss-field-error">
									{{ row_error(row) }}
								</div>
								<div class="ss-task-notes">
									<input
										v-model="row.location"
										class="ss-input ss-input--sm"
										aria-label="ตำแหน่ง"
										placeholder="ตำแหน่ง เช่น ชั้น 2 โซน B"
									/>
									<input
										v-model="row.remarks"
										class="ss-input ss-input--sm"
										aria-label="หมายเหตุ"
										:placeholder="
											is_report ? 'หมายเหตุของงานนี้ (ถ้ามี)' : 'หมายเหตุ (ถ้ามี)'
										"
									/>
								</div>
							</div>
						</TransitionGroup>
						<button type="button" class="ss-add-row" @click="task_sheet = true">
							<Icon name="plus" :size="20" :stroke="2.6" /> เลือกงานจากแผนงาน
						</button>
					</div>

					<!-- 3. บุคลากร / เครื่องจักร -->
					<div v-else-if="current === 'resources'" key="resources" class="ss-step-body">
						<div class="ss-cols">
							<div class="ss-form">
								<h2 class="ss-section-title ss-section-title--first">
									<span><Icon name="users" :size="16" /> บุคลากร</span>
									<span class="ss-section-total">{{ labour_total }} คน</span>
								</h2>
								<div
									v-for="r in doc.labour"
									:key="r.role"
									class="ss-res-row"
									:class="{ 'is-zero': !r.qty }"
								>
									<span class="ss-res-name">{{ r.role }}</span>
									<Stepper v-model="r.qty" />
									<button
										type="button"
										class="ss-icon-btn ss-icon-btn--sm"
										:aria-label="`ลบ ${r.role}`"
										@click="doc.labour = doc.labour.filter((x) => x !== r)"
									>
										<Icon name="x" :size="17" />
									</button>
								</div>
								<div class="ss-res-add">
									<input
										v-model="new_role"
										class="ss-input ss-input--sm"
										placeholder="ตำแหน่งอื่น เช่น ช่างไม้"
										@keydown.enter.prevent="add_role"
									/>
									<button
										type="button"
										class="ss-btn ss-btn--soft ss-btn--sm"
										:disabled="!new_role.trim()"
										@click="add_role"
									>
										เพิ่ม
									</button>
								</div>
							</div>
							<div class="ss-form">
								<h2 class="ss-section-title ss-section-title--first">
									<span><Icon name="truck" :size="16" /> เครื่องจักร</span>
									<span class="ss-section-total">{{ equipment_total }} คัน/เครื่อง</span>
								</h2>
								<div
									v-for="r in doc.equipment"
									:key="r.equipment"
									class="ss-res-row"
									:class="{ 'is-zero': !r.qty }"
								>
									<span class="ss-res-name">{{ r.equipment }}</span>
									<Stepper v-model="r.qty" />
									<button
										type="button"
										class="ss-icon-btn ss-icon-btn--sm"
										:aria-label="`ลบ ${r.equipment}`"
										@click="doc.equipment = doc.equipment.filter((x) => x !== r)"
									>
										<Icon name="x" :size="17" />
									</button>
									<label v-if="r.qty" class="ss-res-hours">
										<input
											v-model.number="r.hours"
											class="ss-input ss-input--sm"
											type="number"
											inputmode="decimal"
											min="0"
										/>
										<small>ชม.</small>
									</label>
								</div>
								<div class="ss-res-add">
									<input
										v-model="new_equipment"
										class="ss-input ss-input--sm"
										placeholder="เครื่องจักรอื่น"
										@keydown.enter.prevent="add_equipment"
									/>
									<button
										type="button"
										class="ss-btn ss-btn--soft ss-btn--sm"
										:disabled="!new_equipment.trim()"
										@click="add_equipment"
									>
										เพิ่ม
									</button>
								</div>
							</div>
						</div>
					</div>

					<!-- 4. ปัญหา / หมายเหตุ + สรุป -->
					<div v-else key="notes" class="ss-step-body">
						<div class="ss-cols ss-cols--review">
							<div class="ss-form">
								<template v-if="is_report">
									<label class="ss-field">
										<span class="ss-field-label">ปัญหา / อุปสรรค</span>
										<textarea
											v-model="doc.problems"
											class="ss-input"
											rows="3"
											placeholder="เช่น วัสดุมาส่งล่าช้า เครื่องจักรเสีย"
										></textarea>
									</label>
								</template>
								<template v-else>
									<label class="ss-field">
										<span class="ss-field-label">วัสดุที่ต้องใช้ / ต้องเตรียม</span>
										<textarea
											v-model="doc.materials"
											class="ss-input"
											rows="2"
											placeholder="เช่น คอนกรีต 240 ksc 12 ม³ เข้าหน้างาน 9.00 น."
										></textarea>
									</label>
									<label class="ss-field">
										<span class="ss-field-label">มาตรการความปลอดภัย</span>
										<textarea
											v-model="doc.safety_measures"
											class="ss-input"
											rows="2"
											placeholder="เช่น งานบนที่สูง ใช้ Full body harness"
										></textarea>
									</label>
								</template>
								<label class="ss-field">
									<span class="ss-field-label">หมายเหตุ</span>
									<textarea v-model="doc.remarks" class="ss-input" rows="2"></textarea>
								</label>
							</div>

							<div>
								<h2 class="ss-section-title">
									สรุปก่อน{{ is_report ? "ส่ง" : "ขออนุมัติ" }}
								</h2>
								<div class="ss-facts ss-facts--grid ss-review">
									<div class="ss-fact">
										<span>วันที่</span><b>{{ thai_date(doc.date, { year: true }) }}</b>
									</div>
									<div v-if="is_report" class="ss-fact">
										<span>สภาพอากาศ</span><b>{{ doc.weather || "–" }}</b>
									</div>
									<div v-else class="ss-fact">
										<span>ผู้อนุมัติ</span><b>{{ approver_label || "–" }}</b>
									</div>
									<div class="ss-fact">
										<span>งาน</span><b>{{ doc.items.length }} รายการ</b>
									</div>
									<div class="ss-fact">
										<span>ความคืบหน้า</span><b>+{{ pct(project_percent) }}%</b>
									</div>
									<div class="ss-fact">
										<span>บุคลากร</span><b>{{ labour_total }} คน</b>
									</div>
									<div class="ss-fact">
										<span>เครื่องจักร</span><b>{{ equipment_total }}</b>
									</div>
								</div>
							</div>
						</div>
					</div>
				</Transition>
			</div>
		</div>

		<Teleport to="#ss-layer">
			<Transition name="ss-bar">
				<div v-if="setup" class="ss-bottom-bar">
					<button
						v-if="step > 0"
						type="button"
						class="ss-btn ss-btn--ghost ss-btn--lg"
						:disabled="saving"
						@click="move(-1)"
					>
						<Icon name="chevron-left" :size="18" :stroke="2.4" /> ย้อนกลับ
					</button>
					<template v-if="step < steps.length - 1">
						<button
							type="button"
							class="ss-btn ss-btn--primary ss-btn--lg ss-grow"
							@click="move(1)"
						>
							ถัดไป: {{ steps[step + 1].label }}
							<Icon name="chevron-right" :size="18" :stroke="2.4" />
							<kbd class="ss-kbd">Ctrl ↵</kbd>
						</button>
					</template>
					<template v-else-if="is_report">
						<button
							type="button"
							class="ss-btn ss-btn--ghost ss-btn--lg"
							:class="{ 'ss-grow': !setup.can_submit }"
							:disabled="saving"
							@click="save(0)"
						>
							บันทึกร่าง
						</button>
						<button
							v-if="setup.can_submit"
							type="button"
							class="ss-btn ss-btn--primary ss-btn--lg ss-grow"
							:disabled="saving"
							@click="save(1)"
						>
							<span v-if="saving" class="ss-spinner"></span>
							<template v-else>ส่งรายงาน</template>
						</button>
					</template>
					<button
						v-else
						type="button"
						class="ss-btn ss-btn--primary ss-btn--lg ss-grow"
						:disabled="saving"
						@click="save(0)"
					>
						<span v-if="saving" class="ss-spinner"></span>
						<template v-else>ส่งขออนุมัติ</template>
					</button>
				</div>
			</Transition>
		</Teleport>

		<!-- เลือกงานจากแผน (เลือกได้หลายงาน) -->
		<Sheet
			:open="task_sheet"
			title="เลือกงาน"
			:subtitle="`${doc?.items.length || 0} งานที่เลือก`"
			full
			@close="task_sheet = false"
		>
			<div class="ss-search">
				<Icon name="search" :size="18" />
				<input v-model="task_txt" type="search" placeholder="ค้นหา WBS หรือชื่องาน" />
			</div>
			<div class="ss-filters">
				<button
					v-for="f in TASK_FILTERS"
					:key="f.value"
					type="button"
					class="ss-filter"
					:class="{ 'is-active': task_filter === f.value }"
					@click="task_filter = f.value"
				>
					{{ f.label }} <span class="ss-filter-count">{{ task_count(f.value) }}</span>
				</button>
			</div>
			<div class="ss-options">
				<template v-for="group in task_groups" :key="group.path">
					<div class="ss-option-group">{{ group.path || "งาน" }}</div>
					<button
						v-for="t in group.tasks"
						:key="t.wbs"
						type="button"
						class="ss-option"
						:class="{ 'is-active': chosen.has(t.wbs), 'is-done': t.previous_percent >= 100 }"
						:disabled="t.previous_percent >= 100 && !chosen.has(t.wbs)"
						@click="toggle_task(t)"
					>
						<span class="ss-check-box"
							><Icon v-if="chosen.has(t.wbs)" name="check" :size="14" :stroke="3"
						/></span>
						<span class="ss-option-main">
							<span class="ss-option-label"
								><i class="ss-wbs">{{ t.wbs }}</i> {{ t.item_name }}</span
							>
							<span class="ss-option-desc">
								<template v-if="t.in_plan"
									><b class="ss-in-plan">ตามแผนวันนี้</b> ·
								</template>
								ทำแล้ว {{ pct(t.previous_percent) }}%<template v-if="t.quantity">
									· คงเหลือ {{ num(t.quantity - t.previous_qty) }} {{ t.uom }}</template
								>
							</span>
						</span>
					</button>
				</template>
				<div v-if="!task_groups.length" class="ss-options-note">ไม่พบงาน</div>
			</div>
			<template #footer>
				<button
					type="button"
					class="ss-btn ss-btn--primary ss-btn--block ss-btn--lg"
					@click="task_sheet = false"
				>
					เสร็จ ({{ doc?.items.length || 0 }} งาน)
				</button>
			</template>
		</Sheet>
	</div>
</template>

<script setup>
import { computed, inject, onBeforeUnmount, ref, watch } from "vue";
import Icon from "../../components/Icon.vue";
import TopBar from "../../components/TopBar.vue";
import Skeleton from "../../components/Skeleton.vue";
import Empty from "../../components/Empty.vue";
import Picker from "../../components/Picker.vue";
import Sheet from "../../components/Sheet.vue";
import Stepper from "../../components/Stepper.vue";
import { REPORT_KINDS } from "../../sections.js";
import { call, celebrate, go, num, post, show_error, state, thai_date, toast, vibrate } from "../../api.js";

const reload_summary = inject("reload_summary");
const params = state.route.params;
const kind = REPORT_KINDS[params.kind] || REPORT_KINDS.dr;
const is_report = kind.doctype === "Daily Report";
const is_new = !params.name || params.name === "new";

const STEPS = is_report
	? [
			{ key: "general", label: "สภาพอากาศ" },
			{ key: "items", label: "งานที่ทำ" },
			{ key: "resources", label: "คน/เครื่องจักร" },
			{ key: "notes", label: "ปัญหา/หมายเหตุ" },
	  ]
	: [
			{ key: "general", label: "วันเวลา" },
			{ key: "items", label: "งานที่จะทำ" },
			{ key: "resources", label: "คน/เครื่องจักร" },
			{ key: "notes", label: "วัสดุ/ความปลอดภัย" },
	  ];
const TASK_FILTERS = [
	{ value: "plan", label: "ตามแผนวันนี้" },
	{ value: "open", label: "ยังไม่ครบ" },
	{ value: "all", label: "ทั้งหมด" },
];
const TOLERANCE = 1e-6;

const setup = ref(null);
const doc = ref(null);
const step = ref(0);
const direction = ref("next");
const saving = ref(false);
const task_sheet = ref(false);
const task_txt = ref("");
const task_filter = ref("plan");
const new_role = ref("");
// แสดงข้อผิดพลาดของแถวหลังกดถัดไป/บันทึกครั้งแรก (ไม่แดงตั้งแต่ยังไม่ได้กรอก)
const show_errors = ref(false);
const new_equipment = ref("");
// ขั้นที่ผ่านแล้ว (ย้อนไปแก้แล้วกระโดดกลับได้)
const reached = ref(is_new ? 0 : STEPS.length - 1);

const steps = STEPS;
const current = computed(() => steps[step.value].key);
const title = computed(() =>
	is_new ? (is_report ? "เขียนรายงาน" : "ขออนุมัติล่วงหน้า") : `แก้ไข${kind.short}`
);
const subtitle = computed(() =>
	doc.value ? `${thai_date(doc.value.date, { year: true })} · ${doc.value.name || kind.label}` : ""
);
const back_params = computed(() => (doc.value ? { day: doc.value.date } : {}));

const pct = (value) => (Number(value) || 0).toLocaleString("th-TH", { maximumFractionDigits: 2 });
const clamp = (value) => Math.max(0, Math.min(100, Number(value) || 0));

// ---------------------------------------------------------------- โหลด / ร่างที่ค้างในเครื่อง

const draft_key = computed(
	() =>
		`consbiz.site.draft:${state.project?.name}:${params.kind}:${params.name || "new"}:${
			params.from || ""
		}`
);

async function load(date) {
	try {
		const result = await call("consbiz.site_app.get_report_form", {
			project: state.project.name,
			doctype: kind.doctype,
			name: is_new ? null : params.name,
			date: date || params.date,
			from_request: params.from,
		});
		if (date && doc.value) {
			// เปลี่ยนวันที่: ใช้รายการงาน (ตามแผนของวันนั้น) และเอกสารวันเดียวกันชุดใหม่ ข้อมูลที่กรอกคงเดิม
			setup.value = { ...setup.value, tasks: result.tasks, same_day: result.same_day };
			return;
		}
		setup.value = result;
		doc.value = restore_draft() || result.doc;
		if (!result.editable) {
			toast("เอกสารนี้แก้ไขไม่ได้แล้ว", "warning");
			go("report-view", { kind: params.kind, name: params.name }, { replace: true });
		}
	} catch (error) {
		show_error(error);
	}
}

function restore_draft() {
	try {
		const saved = JSON.parse(localStorage.getItem(draft_key.value) || "null");
		if (saved && is_new) {
			toast("กู้ข้อมูลที่กรอกค้างไว้", "info");
			return saved;
		}
	} catch {
		// ไม่มี / อ่านไม่ได้
	}
	return null;
}

let draft_timer = null;
watch(
	doc,
	(value) => {
		if (!value || !is_new) return;
		clearTimeout(draft_timer);
		draft_timer = setTimeout(() => {
			try {
				localStorage.setItem(draft_key.value, JSON.stringify(value));
			} catch {
				// เต็ม / private mode
			}
		}, 500);
	},
	{ deep: true }
);

function clear_draft() {
	clearTimeout(draft_timer);
	try {
		localStorage.removeItem(draft_key.value);
	} catch {
		// ไม่เป็นไร
	}
}

function date_changed() {
	if (doc.value.date) load(doc.value.date);
}

// ---------------------------------------------------------------- ขั้นตอน

function step_error(index) {
	const key = steps[index].key;
	const d = doc.value;
	if (key === "general") {
		if (!d.date) return "กรุณาเลือกวันที่";
		if (!is_report && !d.approver) return "กรุณาเลือกผู้อนุมัติ";
	}
	if (key === "items") {
		if (!d.items.length)
			return is_report ? "เพิ่มงานที่ทำอย่างน้อย 1 งาน" : "เพิ่มงานที่จะทำอย่างน้อย 1 งาน";
		const bad = d.items.find((row) => row_error(row));
		if (bad) return `${bad.wbs}: ${row_error(bad)}`;
	}
	return null;
}

function move(delta) {
	if (delta > 0) {
		const error = step_error(step.value);
		if (error) {
			show_errors.value = true;
			toast(error, "error");
			vibrate([30, 40, 30]);
			return;
		}
	}
	direction.value = delta > 0 ? "next" : "prev";
	step.value += delta;
	reached.value = Math.max(reached.value, step.value);
	window.scrollTo({ top: 0, behavior: "smooth" });
}

const can_jump = (i) => i <= reached.value;
function jump(i) {
	if (i === step.value || !can_jump(i)) return;
	// ข้ามไปข้างหน้าได้เมื่อขั้นระหว่างทางไม่มีข้อผิดพลาด
	for (let k = step.value; k < i; k++) {
		const error = step_error(k);
		if (error) {
			toast(error, "error");
			return;
		}
	}
	direction.value = i > step.value ? "next" : "prev";
	step.value = i;
}

// ---------------------------------------------------------------- งาน

const tasks_by_wbs = computed(() => Object.fromEntries((setup.value?.tasks || []).map((t) => [t.wbs, t])));
const task_of = (row) => tasks_by_wbs.value[row.wbs] || {};
const chosen = computed(() => new Set(doc.value?.items.map((r) => r.wbs)));
const is_qty = (row) => Number(task_of(row).quantity ?? row.boq_qty) > 0;
const prev_pct = (row) => Number(task_of(row).previous_percent ?? row.previous_percent) || 0;
const prev_qty = (row) => Number(task_of(row).previous_qty ?? row.previous_qty) || 0;
const boq_qty = (row) => Number(task_of(row).quantity ?? row.boq_qty) || 0;
const row_percent = (row) =>
	is_qty(row) ? ((Number(row.qty) || 0) / boq_qty(row)) * 100 : Number(row.percent) || 0;
const remaining = (row) => Math.max(0, boq_qty(row) - prev_qty(row));
// ขั้นของปุ่ม +/-: ราว 1/20 ของปริมาณงาน ปัดเป็น 1 / 5 / 10 ...
function qty_step(row) {
	const rough = boq_qty(row) / 20;
	if (rough <= 1) return rough < 0.5 ? 0.5 : 1;
	const base = 10 ** Math.floor(Math.log10(rough));
	return [1, 2, 5, 10].map((m) => m * base).find((s) => s >= rough) || base * 10;
}

function row_error(row) {
	if (row_percent(row) <= 0) return is_report ? "กรอกปริมาณที่ทำได้" : "กรอกปริมาณที่จะทำ";
	if (prev_pct(row) + row_percent(row) > 100 + TOLERANCE + 0.005) {
		return is_qty(row)
			? `เกินปริมาณคงเหลือ ${num(remaining(row))} ${task_of(row).uom || ""} (ส่วนเกินทำเป็นงานเพิ่ม VO)`
			: `เกิน 100% (ทำแล้ว ${pct(prev_pct(row))}%)`;
	}
	return null;
}

const project_percent = computed(() =>
	(doc.value?.items || []).reduce(
		(sum, row) => sum + (row_percent(row) * (Number(task_of(row).weight) || 0)) / 100,
		0
	)
);

function new_row(task) {
	return { wbs: task.wbs, qty: 0, percent: 0, remarks: "", location: "", item_name: task.item_name };
}

function toggle_task(task) {
	vibrate(8);
	const index = doc.value.items.findIndex((r) => r.wbs === task.wbs);
	if (index >= 0) doc.value.items.splice(index, 1);
	else doc.value.items.push(new_row(task));
}

function remove_row(row) {
	doc.value.items = doc.value.items.filter((r) => r !== row);
}

function fill_rest(row) {
	if (is_qty(row)) row.qty = Math.round(remaining(row) * 1e6) / 1e6;
	else row.percent = Math.round((100 - prev_pct(row)) * 1e6) / 1e6;
}

const planned_to_add = computed(() =>
	(setup.value?.tasks || []).filter(
		(t) => t.in_plan && t.previous_percent < 100 && !chosen.value.has(t.wbs)
	)
);
function add_planned() {
	const rows = planned_to_add.value.map(new_row);
	doc.value.items.push(...rows);
	toast(`เพิ่มงานตามแผน ${rows.length} งาน`, "info");
}

function task_matches(t, filter) {
	if (filter === "plan") return t.in_plan && t.previous_percent < 100;
	if (filter === "open") return t.previous_percent < 100;
	return true;
}
const task_count = (filter) => (setup.value?.tasks || []).filter((t) => task_matches(t, filter)).length;
const task_groups = computed(() => {
	const q = task_txt.value.trim().toLowerCase();
	const groups = [];
	for (const t of setup.value?.tasks || []) {
		if (!chosen.value.has(t.wbs) && !task_matches(t, q ? "all" : task_filter.value)) continue;
		if (q && !`${t.wbs} ${t.item_name} ${t.group_path}`.toLowerCase().includes(q)) continue;
		const last = groups[groups.length - 1];
		if (last?.path === t.group_path) last.tasks.push(t);
		else groups.push({ path: t.group_path, tasks: [t] });
	}
	return groups;
});
// เปิดครั้งแรกไม่มีงานตามแผนวันนี้: แสดงงานที่ยังไม่ครบแทน
watch(task_sheet, (open) => {
	if (open && task_filter.value === "plan" && !task_count("plan")) task_filter.value = "open";
});

// ---------------------------------------------------------------- คน / เครื่องจักร

const labour_total = computed(() => (doc.value?.labour || []).reduce((s, r) => s + (Number(r.qty) || 0), 0));
const equipment_total = computed(() =>
	(doc.value?.equipment || []).reduce((s, r) => s + (Number(r.qty) || 0), 0)
);

function add_role() {
	const role = new_role.value.trim();
	if (!role) return;
	if (!doc.value.labour.some((r) => r.role === role)) doc.value.labour.push({ role, qty: 1 });
	new_role.value = "";
}
function add_equipment() {
	const equipment = new_equipment.value.trim();
	if (!equipment) return;
	if (!doc.value.equipment.some((r) => r.equipment === equipment))
		doc.value.equipment.push({ equipment, qty: 1, hours: 0 });
	new_equipment.value = "";
}

// ---------------------------------------------------------------- อื่นๆ

const same_day = computed(() => {
	const s = setup.value?.same_day || {};
	return [...(s["Daily Report"] || []), ...(s["Daily Request"] || [])];
});
const approver_options = computed(() =>
	(setup.value?.approvers || []).map((a) => ({
		value: a.value,
		label: a.label || a.value,
		description: a.value,
	}))
);
const approver_label = computed(
	() => approver_options.value.find((a) => a.value === doc.value?.approver)?.label || doc.value?.approver
);

// สรุปสั้นๆ ใต้ชื่อขั้น (แถบขั้นตอนด้านซ้ายบนจอกว้าง)
function step_hint(key) {
	const d = doc.value;
	if (!d) return "";
	if (key === "general") {
		const day = thai_date(d.date);
		return is_report ? [day, d.weather].filter(Boolean).join(" · ") : day;
	}
	if (key === "items")
		return d.items.length
			? `${d.items.length} งาน · +${pct(project_percent.value)}%`
			: "ยังไม่ได้เลือกงาน";
	if (key === "resources") return `${labour_total.value} คน · ${equipment_total.value} เครื่อง`;
	return `ตรวจทานแล้ว${is_report ? "ส่ง" : "ขออนุมัติ"}`;
}

// Ctrl/⌘ + Enter = ถัดไป (ขั้นสุดท้าย = ส่ง/ขออนุมัติ) สำหรับคีย์บอร์ดบนจอใหญ่
function on_shortcut(event) {
	if (!(event.ctrlKey || event.metaKey) || event.key !== "Enter" || !setup.value || saving.value) return;
	if (task_sheet.value) return;
	event.preventDefault();
	if (step.value < steps.length - 1) move(1);
	else save(is_report && setup.value.can_submit ? 1 : 0);
}
window.addEventListener("keydown", on_shortcut);
onBeforeUnmount(() => window.removeEventListener("keydown", on_shortcut));

function weather_icon(text) {
	if (/พายุ/.test(text)) return "storm";
	if (/ฝน/.test(text)) return "rain";
	if (/เมฆมาก/.test(text)) return "cloud";
	if (/เมฆ/.test(text)) return "cloud-sun";
	return "sun";
}

async function save(submit) {
	for (let i = 0; i < steps.length; i++) {
		const error = step_error(i);
		if (error) {
			show_errors.value = true;
			toast(error, "error");
			direction.value = i < step.value ? "prev" : "next";
			step.value = i;
			return;
		}
	}
	saving.value = true;
	try {
		const d = doc.value;
		const data = {
			...d,
			// งานมีปริมาณส่งปริมาณ งานเหมาส่ง % (ระบบคำนวณอีกค่าให้)
			items: d.items.map((row) => ({
				wbs: row.wbs,
				qty: is_qty(row) ? Number(row.qty) || 0 : 0,
				percent: is_qty(row) ? 0 : Number(row.percent) || 0,
				remarks: row.remarks || null,
				location: row.location || null,
			})),
		};
		const result = await post("consbiz.site_app.save_report", {
			project: state.project.name,
			doctype: kind.doctype,
			data,
			submit,
		});
		clear_draft();
		reload_summary();
		await celebrate(
			is_report ? (submit ? "ส่งรายงานแล้ว" : "บันทึกร่างแล้ว") : "ส่งขออนุมัติแล้ว",
			result.name
		);
		go("report-view", { kind: params.kind, name: result.name }, { replace: true });
	} catch (error) {
		show_error(error);
	} finally {
		saving.value = false;
	}
}

load();
</script>
