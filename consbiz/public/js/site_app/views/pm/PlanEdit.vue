<!-- แก้แผนงานในแอป: หน้าเต็มจอของแอปเอง (ไม่ใช้ desk) โครง = แถบบน / แถบเครื่องมือแบ่งแท็บ / ตาราง + Gantt / แผงงาน / แถบสถานะ
     state + การคำนวณ = planner/planner.js (schedule.js ชุดเดียวกับหน้า Gantt ของระบบเต็ม, API เดิม get_schedule_data / save_tasks)
     ตาราง + Gantt = planner/PlanSheet.vue, รายละเอียดงาน = planner/PlanInspector.vue (จอ ≥1100 แผงขวา, เล็กกว่า = Sheet)
     ออกจากหน้า: บันทึกงานค้างก่อน (planner.flush) บันทึกไม่ได้ถามก่อนทิ้ง
     readonly = หน้า "แผนงาน" (Plan.vue) ใช้หน้าจอชุดนี้แบบดูอย่างเดียว: ไม่มีลากแถบ/แก้ค่า/บันทึก (p.can_write = false) -->
<template>
	<div class="ss-planner" :class="{ 'has-side': side_task }">
		<TopBar
			:title="readonly ? 'แผนงาน' : 'แก้ไขแผนงาน'"
			:subtitle="p.data?.project_name || state.project?.project_name"
			:back_to="readonly ? undefined : 'plan'"
			:no_project="!readonly"
		>
			<template #actions>
				<template v-if="readonly">
					<!-- มีแถวแท็บ = ปุ่มอยู่ขวาของแท็บ ไม่มีแผนงาน (ไม่มีแถวแท็บ) ยังต้องโหลดใหม่ได้ -->
					<button
						v-if="error"
						type="button"
						class="ss-icon-btn"
						:class="{ 'is-spinning': p.loading }"
						aria-label="โหลดใหม่"
						@click="reload"
					>
						<Icon name="refresh" :size="20" />
					</button>
				</template>
				<template v-else>
					<span
						v-if="p.data"
						class="ss-tag pl-save-state"
						:class="`tone-${p.save_status.tone}`"
						:title="p.save_status.label"
						>{{ p.save_status.label }}</span
					>
					<button
						type="button"
						class="ss-icon-btn"
						aria-label="ย้อนกลับการแก้ไข"
						title="ย้อนกลับ (Ctrl+Z)"
						:disabled="!p.history.past.length"
						@click="p.undo()"
					>
						<Icon name="undo" :size="20" />
					</button>
					<button
						type="button"
						class="ss-icon-btn"
						aria-label="ทำซ้ำ"
						title="ทำซ้ำ (Ctrl+Y)"
						:disabled="!p.history.future.length"
						@click="p.redo()"
					>
						<Icon name="redo" :size="20" />
					</button>
					<button
						v-if="p.can_write"
						type="button"
						class="ss-btn ss-btn--primary pl-save"
						:disabled="!p.dirty || p.saving"
						@click="p.save()"
					>
						<Icon name="save" :size="14" /> <span>บันทึก</span>
					</button>
				</template>
			</template>
		</TopBar>

		<template v-if="error">
			<div class="ss-content">
				<Empty icon="layers" :title="error" :text="readonly ? 'สร้างแผนงานก่อสร้างของโครงการในระบบเต็มก่อน' : 'แก้แผนงานได้เฉพาะผู้ที่มีสิทธิ์แก้ไขแผนงานก่อสร้าง'" />
			</div>
		</template>

		<template v-else>
			<div class="pl-ribbon">
				<div class="pl-tabs-row">
					<div class="pl-tabs" role="tablist">
						<button
							v-for="tab in TABS"
							:key="tab.value"
							type="button"
							role="tab"
							:aria-selected="settings.tab === tab.value"
							:class="{ 'is-active': settings.tab === tab.value }"
							@click="settings.tab = tab.value"
						>
							{{ tab.label }}
						</button>
					</div>
					<div v-if="readonly" class="pl-tabs-actions">
						<button
							v-if="p.data?.can_write"
							type="button"
							class="ss-btn ss-btn--soft ss-plan-edit-btn"
							aria-label="แก้ไขแผนงาน"
							title="แก้ไขแผนงาน"
							@click="go('plan-edit', { cm: p.name })"
						>
							<Icon name="pen" :size="15" /> <span>แก้ไขแผนงาน</span>
						</button>
						<button
							type="button"
							class="ss-icon-btn"
							:class="{ 'is-spinning': p.loading }"
							aria-label="โหลดใหม่"
							title="โหลดใหม่"
							@click="reload"
						>
							<Icon name="refresh" :size="17" />
						</button>
					</div>
				</div>

				<div v-if="settings.tab === 'plan'" class="pl-tools">
					<div v-if="!readonly" class="pl-group">
						<div class="pl-group-body">
							<span
								class="ss-tag"
								:class="plan_confirmed ? 'tone-green' : 'tone-blue'"
								:title="plan_confirmed ? 'มีแผนสัญญาแล้ว โครงสร้างงานล็อก งานเพิ่ม-ลดใช้ Variation Order' : 'แก้โครงสร้างงานได้จนกว่าจะบันทึกแผนสัญญาชุดแรก'"
							>{{ plan_confirmed ? "ยืนยันแล้ว" : "กำลังวางแผน" }}</span>
						</div>
					</div>
					<div v-if="p.can_write && !readonly && plan_confirmed && p.data?.can_unconfirm" class="pl-group">
						<div class="pl-group-body">
							<button type="button" class="pl-tool" title="ลบแผนสัญญาทุกชุด แล้วกลับไปแก้โครงสร้างงาน" aria-label="ยกเลิกการยืนยัน" :disabled="p.saving" @click="open_structure('unconfirm')">
								<Icon name="undo" :size="18" /><span>ยกเลิกการยืนยัน</span>
							</button>
						</div>
					</div>
					<div v-if="p.can_write && !readonly && !plan_confirmed" class="pl-group">
						<div class="pl-group-body">
							<button type="button" class="pl-tool" title="เพิ่มงาน" aria-label="เพิ่มงาน" :disabled="p.saving" @click="open_structure('add')">
								<Icon name="plus" :size="18" /><span>เพิ่มงาน</span>
							</button>
							<button type="button" class="pl-tool" title="เพิ่มงานย่อยใต้งานที่เลือก" aria-label="เพิ่มงานย่อย" :disabled="p.saving || targets.length !== 1" @click="open_structure('add_child')">
								<Icon name="corner-down-right" :size="18" /><span>เพิ่มงานย่อย</span>
							</button>
							<button type="button" class="pl-tool" title="Indent (เลือกหลายงานด้วย Shift)" aria-label="Indent" :disabled="p.saving || !targets.length" @click="run_structure('indent')">
								<Icon name="indent" :size="18" /><span>Indent</span>
							</button>
							<button type="button" class="pl-tool" title="Outdent (เลือกหลายงานด้วย Shift)" aria-label="Outdent" :disabled="p.saving || !targets.length" @click="run_structure('outdent')">
								<Icon name="outdent" :size="18" /><span>Outdent</span>
							</button>
							<button type="button" class="pl-tool" title="ลบงานที่เลือก" aria-label="ลบงาน" :disabled="p.saving || !targets.length" @click="open_structure('delete')">
								<Icon name="trash" :size="18" /><span>ลบงาน</span>
							</button>
						</div>
					</div>
					<div class="pl-group">
						<span class="pl-group-label">Cut-off</span>
						<div class="pl-group-body">
							<span class="pl-date"><DateInput v-model="p.cutoff" variant="cell" label="วัน Cut-off" /></span>
							<button type="button" class="pl-tool" title="Cut-off = วันนี้" aria-label="Cut-off = วันนี้" @click="cutoff_today">
								<Icon name="calendar" :size="18" /><span>วันนี้</span>
							</button>
						</div>
					</div>
					<div v-if="p.baselines.length" class="pl-group">
						<div class="pl-group-body">
							<SelectBox
								:model-value="p.viewed_baseline"
								:options="baseline_options"
								variant="tool"
								label="แผนสัญญาที่เปิดดู"
								@update:model-value="p.show_baseline"
							/>
						</div>
					</div>
					<div class="pl-group">
						<div class="pl-group-body">
							<button
								type="button"
								class="pl-tool"
								title="เลื่อนไปวัน Cut-off"
								aria-label="เลื่อนไปวัน Cut-off"
								@click="timeline?.scroll_to_day(p.cutoff_day)"
							>
								<Icon name="crosshair" :size="18" /><span>วัน Cut-off</span>
							</button>
							<button
								type="button"
								class="pl-tool"
								title="เลื่อนไปงานที่เลือก"
								aria-label="เลื่อนไปงานที่เลือก"
								:disabled="!selected"
								@click="sheet?.scroll_to_task(selected)"
							>
								<Icon name="gantt" :size="18" /><span>งานที่เลือก</span>
							</button>
						</div>
					</div>
					<div v-if="p.can_write" class="pl-group">
						<div class="pl-group-body">
							<label class="pl-switch" :class="{ 'is-on': p.auto_save }">
								<input v-model="p.auto_save" type="checkbox" />
								<span class="pl-switch-track"><i></i></span>
								<span>อัตโนมัติ</span>
							</label>
						</div>
					</div>
					<div class="pl-group">
						<div class="pl-group-body">
							<a
								class="pl-tool"
								:href="desk_href"
								target="_blank"
								rel="noopener"
								title="Excel / แผนสัญญา / แผนทรัพยากร (เปิดระบบเต็ม)"
								aria-label="Excel / แผนสัญญา / แผนทรัพยากร (เปิดระบบเต็ม)"
							>
								<Icon name="external" :size="18" /><span>Excel · แผนสัญญา</span>
							</a>
						</div>
					</div>
				</div>

				<div v-else-if="settings.tab === 'view'" class="pl-tools">
					<div class="pl-group">
						<div class="pl-group-body">
							<button
								ref="columns_btn"
								type="button"
								class="pl-tool is-toggle"
								:class="{ 'is-on': columns_open }"
								title="คอลัมน์"
								aria-label="คอลัมน์"
								aria-haspopup="menu"
								:aria-expanded="columns_open"
								@click="toggle_columns"
							>
								<Icon name="panel" :size="18" /><span>คอลัมน์</span><Icon name="chevron-down" :size="12" />
							</button>
						</div>
					</div>
					<div class="pl-group">
						<div class="pl-group-body">
							<Segmented v-model="settings.board" :options="BOARD_OPTIONS" class="pl-seg pl-seg--board" />
						</div>
					</div>
					<div class="pl-group">
						<div class="pl-group-body">
							<SelectBox v-model="settings.scale" :options="SCALE_OPTIONS" variant="tool" label="มาตราส่วนเวลา" />
						</div>
					</div>
					<div class="pl-group">
						<div class="pl-group-body">
							<button type="button" class="pl-tool is-icon" title="ย่อ" aria-label="ย่อ" @click="zoom(-1)">
								<Icon name="minus" :size="18" />
							</button>
							<span class="pl-zoom">{{ Math.round(settings.zoom * 100) }}%</span>
							<button type="button" class="pl-tool is-icon" title="ขยาย" aria-label="ขยาย" @click="zoom(1)">
								<Icon name="plus" :size="18" />
							</button>
						</div>
					</div>
					<div class="pl-group">
						<div class="pl-group-body">
							<SelectBox
								v-model="settings.level"
								:options="level_options"
								variant="tool"
								label="แสดงถึงระดับ"
								@update:model-value="(v) => sheet?.set_level(v)"
							/>
						</div>
					</div>
						<div class="pl-group">
							<div class="pl-group-body">
								<SelectBox v-model="filter" :options="filter_options" variant="tool" label="ตัวกรองงาน" />
							</div>
						</div>
					<div class="pl-group">
						<div class="pl-group-body">
							<button
								ref="curve_btn"
								type="button"
								class="pl-tool is-toggle"
								:class="{ 'is-on': curve_open }"
								title="เส้น S-Curve และตารางสรุป"
								aria-label="เส้น S-Curve และตารางสรุป"
								aria-haspopup="menu"
								:aria-expanded="curve_open"
								@click="toggle_curve_menu"
							>
								<Icon name="trending" :size="18" /><span>S-Curve / ตารางสรุป</span><Icon name="chevron-down" :size="12" />
							</button>
							<button
								v-for="toggle in TOGGLES"
								:key="toggle.key"
								type="button"
								class="pl-tool is-toggle"
								:class="{ 'is-on': settings.show[toggle.key] }"
								:title="toggle.label"
								:aria-label="toggle.label"
								:aria-pressed="settings.show[toggle.key]"
								@click="settings.show[toggle.key] = !settings.show[toggle.key]"
							>
								<Icon :name="toggle.icon" :size="18" /><span>{{ toggle.label }}</span>
							</button>
						</div>
					</div>
				</div>
			</div>

			<div class="pl-main">
				<div class="pl-canvas">
					<div v-if="!p.data" class="pl-loading"><Skeleton :rows="8" /></div>
					<ResourceBoard
						v-else-if="settings.board === 'resources'"
						ref="board"
						:p="p"
						:settings="settings"
						@open="open_from_board"
					/>
					<ResourceMonthly v-else-if="settings.board === 'monthly'" :p="p" />
					<PlanSheet
						v-else
						ref="sheet"
						:p="p"
						:settings="settings"
						:selected="selected"
						:multi="multi"
						:context="menu?.task"
						:filter="filter"
						@select="select"
						@context="open_menu"
						@resources="(task) => open_task(task, 'resources')"
					/>
				</div>
				<!-- ทับตาราง ย่อ-หุบของงานพิมพ์แยกจากตาราง ตัวกรองใช้ร่วมกัน -->
				<PlanPrint v-if="settings.tab === 'print' && p.data" :p="p" :settings="settings" :kept="sheet?.filtered_names ?? null" :is_table_collapsed="sheet?.is_collapsed" />
				<Transition name="pl-side">
					<aside v-if="side_task && settings.tab !== 'print'" class="pl-side">
						<PlanInspector v-model:tab="inspector_tab" :p="p" :task="side_task" @close="selected = null" />
					</aside>
				</Transition>
			</div>

			<footer v-if="p.data" class="pl-statusbar">
				<span><b>{{ s.tasks }}</b> งาน</span>
				<span v-if="settings.show.critical" class="is-rose"><b>{{ s.critical }}</b> วิกฤต</span>
				<span :class="{ 'is-amber': s.late }"><b>{{ s.late }}</b> ช้ากว่าแผน</span>
				<span class="pl-sb-hide-sm">จบ <b>{{ s.finish ? thai_date(s.finish, { year: true }) : "-" }}</b></span>
				<span class="pl-sb-sep"></span>
				<span class="pl-sb-pct is-plan">แผน <b>{{ s.plan.toFixed(3) }}%</b></span>
				<span class="pl-sb-pct is-actual">จริง <b>{{ s.actual.toFixed(3) }}%</b></span>
				<span v-if="s.baseline !== null" class="pl-sb-pct is-base pl-sb-hide-sm"
					>แผนสัญญา <b>{{ s.baseline.toFixed(3) }}%</b></span
				>
				<span class="pl-sb-hide-sm" :class="s.actual - s.plan < -0.005 ? 'is-rose' : 'is-green'">
					<b>{{ s.actual - s.plan >= 0 ? "+" : "" }}{{ (s.actual - s.plan).toFixed(3) }}</b>
				</span>
				<span class="pl-sb-grow"></span>
				<span v-if="p.data.can_view_value" class="pl-sb-hide-sm">มูลค่า <b>{{ money(s.amount) }}</b></span>
			</footer>
		</template>

		<Teleport to="#ss-layer">
			<Transition name="ss-pop-menu">
				<div v-if="curve_open" ref="curve_menu" class="ss-select-menu pl-curve-menu" :style="curve_pos">
					<b>เส้น S-Curve</b>
					<label v-for="item in curve_items" :key="item.key" class="ss-toggle" :class="{ 'is-on': curves_on[item.key] }">
						<input type="checkbox" :checked="curves_on[item.key]" @change="settings.curve_lines[item.key] = $event.target.checked" />
						<span class="ss-toggle-track"><span></span></span>
						<span>{{ item.label }}</span>
					</label>
					<b>ตารางสรุป</b>
					<label v-for="row in summary_items" :key="row.key" class="ss-toggle" :class="{ 'is-on': summary_on[row.key] }">
						<input type="checkbox" :checked="summary_on[row.key]" @change="settings.summary_rows[row.key] = $event.target.checked" />
						<span class="ss-toggle-track"><span></span></span>
						<span>{{ row.label }}</span>
					</label>
				</div>
			</Transition>
			<Transition name="ss-pop-menu">
				<ul v-if="columns_open" ref="columns_menu" class="ss-select-menu pl-columns-menu" :style="columns_pos">
					<li
						v-for="(col, i) in settings.column_order"
						:key="col"
						:class="{
							'is-dragging': drag_column === i,
							'is-drop-before': drag_column !== null && drop_column === i && drag_column > i,
							'is-drop-after': drag_column !== null && drop_column === i && drag_column < i,
						}"
					>
						<button
							type="button"
							class="pl-column-move"
							:aria-label="`ย้าย ${COLUMNS[col].label} (ลูกศรขึ้น/ลง)`"
							title="ลากเพื่อย้ายตำแหน่ง"
							@pointerdown="column_drag_start($event, i)"
							@pointermove="column_drag_move"
							@pointerup="column_drag_end"
							@pointercancel="column_drag_cancel"
							@keydown.up.prevent="move_column(i, i - 1)"
							@keydown.down.prevent="move_column(i, i + 1)"
						>
							<Icon name="grip" :size="14" :stroke="2.6" />
						</button>
						<label>
							<input type="checkbox" :checked="settings.columns.includes(col)" @change="toggle_column(col)" />
							<span>{{ COLUMNS[col].label }}</span>
						</label>
					</li>
				</ul>
			</Transition>
		</Teleport>

		<Sheet :open="!!structure_mode" :title="structure_title" @close="structure_mode = null">
			<p v-if="structure_mode === 'delete'" class="ss-muted">
				ลบ {{ targets.length }} งานที่เลือก ลบแล้วย้อนกลับไม่ได้ และลบได้เฉพาะงานที่เพิ่มในแผนและยังไม่ถูกใช้
			</p>
			<p v-else-if="structure_mode === 'unconfirm'" class="ss-muted">
				ลบแผนสัญญาทั้ง {{ p.baselines.length }} ชุด แล้วกลับไปแก้โครงสร้างงานได้ ลบแล้วย้อนกลับไม่ได้ ต้องบันทึกแผนสัญญาใหม่ที่หน้า Gantt ของระบบเต็ม
			</p>
			<div v-else class="ss-form">
				<label class="ss-field">
					<span class="ss-field-label">ชื่องาน</span>
					<input ref="structure_input" v-model="structure_name" class="ss-input" @keydown.enter="confirm_structure" />
				</label>
				<p class="ss-muted">งานที่เพิ่มในแผนมีมูลค่า 0 ไม่มีผลต่อ % ความคืบหน้ารวม บันทึกทันทีและย้อนกลับด้วย Undo ไม่ได้</p>
			</div>
			<template #footer>
				<button
					type="button"
					class="ss-btn ss-btn--block ss-btn--lg"
					:class="structure_needs_name ? 'ss-btn--primary' : 'ss-btn--ghost-danger'"
					:disabled="p.saving || (structure_needs_name && !structure_name.trim())"
					@click="confirm_structure"
				>
					{{ structure_mode === "unconfirm" ? "ยกเลิกการยืนยัน" : structure_mode === "delete" ? "ลบงาน" : "เพิ่มงาน" }}
				</button>
			</template>
		</Sheet>

		<Sheet v-if="!wide" :open="!!selected_task" :title="selected_task?.item_name" @close="selected = null">
			<PlanInspector v-if="selected_task" v-model:tab="inspector_tab" :p="p" :task="selected_task" :closable="false" />
		</Sheet>

		<PlanMenu :menu="menu" @close="menu = null" />

		<Sheet :open="!!leaving" title="ยังไม่ได้บันทึก" @close="answer(false)">
			<p class="ss-muted">แผนงานมีการแก้ไขที่ยังไม่ได้บันทึก ออกจากหน้านี้แล้วการแก้ไขจะหาย</p>
			<div class="ss-sheet-actions pl-leave">
				<button type="button" class="ss-btn ss-btn--ghost" @click="answer(false)">อยู่ต่อ</button>
				<button type="button" class="ss-btn ss-btn--ghost-danger" @click="answer(true)">ทิ้งการแก้ไข</button>
			</div>
		</Sheet>
	</div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from "vue";
import Icon from "../../../shared/components/Icon.vue";
import TopBar from "../../../shared/components/TopBar.vue";
import Skeleton from "../../../shared/components/Skeleton.vue";
import Empty from "../../../shared/components/Empty.vue";
import Sheet from "../../../shared/components/Sheet.vue";
import Segmented from "../../../shared/components/Segmented.vue";
import SelectBox from "../../../shared/components/SelectBox.vue";
import DateInput from "../../../shared/components/DateInput.vue";
import PlanSheet from "./planner/PlanSheet.vue";
import PlanInspector from "./planner/PlanInspector.vue";
import PlanMenu from "./planner/PlanMenu.vue";
import PlanPrint from "./planner/PlanPrint.vue";
import ResourceBoard from "./planner/ResourceBoard.vue";
import ResourceMonthly from "./planner/ResourceMonthly.vue";
import {
	COLUMNS,
	CURVE_ITEMS,
	DEFAULT_COLUMNS,
	SUMMARY_ROWS,
	TASK_FILTERS,
	create_planner,
	task_matches,
	view_curves,
	view_summary,
} from "./planner/planner.js";
import { call, go, money, set_leave_guard, show_error, state, thai_date } from "../../../shared/api.js";
import { from_day, today } from "../../../construction_management/schedule.js";

const props = defineProps({
	params: { type: Object, default: () => ({}) },
	readonly: Boolean,
});

const STORAGE = "consbiz.planner.settings";
const REFRESH_INTERVAL = 30000;
const TABS = [
	{ value: "plan", label: "แผนงาน" },
	{ value: "view", label: "มุมมอง" },
	{ value: "print", label: "พิมพ์" },
];
const SCALE_OPTIONS = [
	{ value: "day", label: "วัน" },
	{ value: "week", label: "สัปดาห์" },
	{ value: "month", label: "เดือน" },
];
const BOARD_OPTIONS = [
	{ value: "tasks", label: "งาน" },
	{ value: "resources", label: "ทรัพยากร" },
	{ value: "monthly", label: "สรุปรายเดือน" },
];
const ZOOMS = [0.5, 0.67, 0.8, 1, 1.25, 1.5, 2];
const TOGGLES = [
	{ key: "links", label: "งานก่อนหน้า", icon: "link" },
	{ key: "critical", label: "สายงานวิกฤต", icon: "flag" },
	{ key: "baseline", label: "แถบแผนสัญญา", icon: "layers" },
	{ key: "labels", label: "ชื่อบนแถบ", icon: "list" },
	{ key: "split", label: "% แผนที่แบ่ง", icon: "hash" },
	{ key: "progress", label: "% แผน/จริงท้ายแถบ", icon: "pin" },
];
const OPTIONAL_COLUMNS = ["boq_wbs", "start_date", "end_date", "duration", "predecessors", "plan_pct", "actual_pct", "diff", "status", "total_float"];

const p = create_planner({ readonly: props.readonly });
const filter = ref("all");
const sheet = ref(null);
const board = ref(null);
const timeline = computed(() => sheet.value || board.value);
const error = ref("");
const selected = ref(null);
const inspector_tab = ref("main");
const menu = ref(null);
const leaving = ref(null);
const s = computed(() => p.summary);

function saved_settings() {
	try {
		return JSON.parse(localStorage.getItem(STORAGE) || "{}");
	} catch {
		return {};
	}
}
const initial = saved_settings();
const settings = reactive({
	tab: "plan",
	scale: "week",
	zoom: 1,
	level: null,
	columns: [...DEFAULT_COLUMNS],
	// board = มุมมองหลัก: tasks / resources (Gantt ทรัพยากร) / monthly (สรุปรายเดือน)
	board: "tasks",
	// widths = ความกว้างคอลัมน์ที่ลากเอง, pane_w = ความกว้างฝั่งตารางที่ลากตัวแบ่ง (null = พอดีคอลัมน์)
	widths: {},
	pane_w: null,
	...initial,
	// เส้น S-Curve / แถวตารางสรุป: เก็บเฉพาะที่ผู้ใช้เปลี่ยน ที่เคยปิดทั้งหมดด้วยปุ่มเดิมยังปิดอยู่
	curve_lines: initial.curve_lines ?? (initial.show?.curve === false ? { baseline: false, plan: false, actual: false } : {}),
	summary_rows:
		initial.summary_rows ??
		(initial.show?.summary === false ? Object.fromEntries(SUMMARY_ROWS.map((row) => [row.key, false])) : {}),
	// column_order = ลำดับคอลัมน์ทั้งหมดในเมนู (รวมที่ซ่อนอยู่ เปิดกลับแล้วอยู่ที่เดิม) wbs/ชื่องาน อยู่ต้นตารางเสมอ
	column_order: [
		...(initial.column_order || []).filter((key) => OPTIONAL_COLUMNS.includes(key)),
		...OPTIONAL_COLUMNS.filter((key) => !(initial.column_order || []).includes(key)),
	],
	show: { links: true, critical: true, baseline: true, labels: true, split: true, progress: true, ...(initial.show || {}) },
});
watch(
	settings,
	() => {
		try {
			localStorage.setItem(STORAGE, JSON.stringify(settings));
		} catch {
			// โหมดส่วนตัว: ไม่จำ
		}
	},
	{ deep: true }
);

// จอ ≥1100 = แผงขวา, เล็กกว่า = Sheet
const wide_query = window.matchMedia("(min-width: 1100px)");
const wide = ref(wide_query.matches);
const on_wide = () => (wide.value = wide_query.matches);

const selected_task = computed(() => (selected.value && p.by_name.get(selected.value)) || null);
const side_task = computed(() => (wide.value ? selected_task.value : null));
const desk_href = computed(() => `/app/construction-gantt/${encodeURIComponent(p.name || "")}`);
const baseline_options = computed(() =>
	p.baselines.map((b) => ({
		value: b.name,
		label: b.title,
		description: b.name === p.data?.active_baseline ? "ใช้เทียบในรายงาน" : thai_date(b.baseline_date, { year: true }),
	}))
);
const filter_options = computed(() => {
	const leaves = p.tasks.filter((t) => !t.is_group);
	return TASK_FILTERS.map((option) => ({
		...option,
		description: `${leaves.filter((t) => task_matches(p.metrics.get(t.name) || {}, option.value)).length} งาน`,
	}));
});
const level_options = computed(() => {
	const depth = Math.max(0, ...p.tasks.map((t) => t.indent || 0));
	return [
		{ value: null, label: "ทุกระดับ" },
		...Array.from({ length: depth }, (_, i) => ({ value: i + 1, label: `ระดับ ${i + 1}` })),
	];
});

function select(name, { shift = false } = {}) {
	if (shift && selected.value) {
		const order = p.tasks.map((task) => task.name);
		const [from, to] = [order.indexOf(selected.value), order.indexOf(name)].sort((a, b) => a - b);
		multi.value = order.slice(from, to + 1);
		return;
	}
	multi.value = [];
	selected.value = selected.value === name && !wide.value ? null : name;
}
// ---------- โครงสร้างงาน (เพิ่ม/ลบ/เลื่อนระดับ) ----------
const multi = ref([]);
const targets = computed(() => (multi.value.length ? multi.value : selected.value ? [selected.value] : []));
const structure_mode = ref(null);
const structure_name = ref("");
const structure_input = ref(null);
const structure_title = computed(
	() =>
		({ add: "เพิ่มงาน", add_child: "เพิ่มงานย่อย", delete: "ลบงาน", unconfirm: "ยกเลิกการยืนยันแผน" }[structure_mode.value] || "")
);
// บันทึก Baseline ชุดแรก = ยืนยันแผน ปิดการแก้โครงสร้างงาน (structure.py)
const plan_confirmed = computed(() => p.baselines.length > 0);
const structure_needs_name = computed(() => ["add", "add_child"].includes(structure_mode.value));
async function open_structure(mode) {
	structure_name.value = "";
	structure_mode.value = mode;
	await nextTick();
	structure_input.value?.focus();
}
async function run_structure(action, item_name = null) {
	const done = await p.change_structure(action, targets.value, item_name);
	if (done && action === "delete") {
		selected.value = null;
	}
	if (done) multi.value = multi.value.filter((name) => p.by_name.has(name));
	return done;
}
async function confirm_structure() {
	const mode = structure_mode.value;
	if (!mode || p.saving || (structure_needs_name.value && !structure_name.value.trim())) return;
	const done =
		mode === "unconfirm"
			? await p.unconfirm_plan()
			: await run_structure(mode, structure_needs_name.value ? structure_name.value.trim() : null);
	if (done) structure_mode.value = null;
}
function zoom(step) {
	const i = ZOOMS.findIndex((z) => z >= settings.zoom - 1e-6);
	settings.zoom = ZOOMS[Math.min(Math.max((i < 0 ? 3 : i) + step, 0), ZOOMS.length - 1)];
}
function apply_columns(visible) {
	settings.columns = ["wbs", "item_name", ...settings.column_order.filter((key) => visible.has(key))];
}
function toggle_column(key) {
	const visible = new Set(settings.columns);
	if (visible.has(key)) visible.delete(key);
	else visible.add(key);
	apply_columns(visible);
}
function move_column(from, to) {
	if (to < 0 || to >= settings.column_order.length || from === to) return;
	const order = [...settings.column_order];
	order.splice(to, 0, order.splice(from, 1)[0]);
	settings.column_order = order;
	apply_columns(new Set(settings.columns));
}
// ลากที่จับ: แสดงเส้นตำแหน่งระหว่างลาก ย้ายจริงตอนปล่อย (แถวไม่ขยับระหว่างลาก pointer capture จึงไม่หลุด)
const drag_column = ref(null);
const drop_column = ref(null);
function column_drag_start(event, index) {
	event.preventDefault();
	event.currentTarget.setPointerCapture(event.pointerId);
	drag_column.value = drop_column.value = index;
}
function column_drag_move(event) {
	if (drag_column.value === null) return;
	const rows = [...columns_menu.value.children];
	const index = rows.findIndex((row) => {
		const box = row.getBoundingClientRect();
		return event.clientY >= box.top && event.clientY < box.bottom;
	});
	if (index >= 0) drop_column.value = index;
	else drop_column.value = event.clientY < rows[0].getBoundingClientRect().top ? 0 : rows.length - 1;
}
function column_drag_end() {
	if (drag_column.value !== null) move_column(drag_column.value, drop_column.value);
	column_drag_cancel();
}
function column_drag_cancel() {
	drag_column.value = drop_column.value = null;
}
const columns_btn = ref(null);
const columns_menu = ref(null);
const columns_open = ref(false);
const columns_pos = ref({});
function toggle_columns() {
	if (columns_open.value) {
		columns_open.value = false;
		return;
	}
	const rect = columns_btn.value.getBoundingClientRect();
	columns_pos.value = {
		top: `${rect.bottom + 6}px`,
		left: `${Math.max(8, Math.min(rect.left, window.innerWidth - 228))}px`,
		width: "220px",
	};
	columns_open.value = true;
}
// ---------- เมนู S-Curve / ตารางสรุป ----------
const curve_btn = ref(null);
const curve_menu = ref(null);
const curve_open = ref(false);
const curve_pos = ref({});
const curves_on = computed(() => view_curves(settings, p));
const summary_on = computed(() => view_summary(settings, p));
const curve_items = computed(() => CURVE_ITEMS.filter((item) => item.key !== "baseline" || p.curves.baseline));
const summary_items = computed(() => SUMMARY_ROWS.filter((row) => row.curve !== "baseline" || p.curves.baseline));
function toggle_curve_menu() {
	if (curve_open.value) {
		curve_open.value = false;
		return;
	}
	const rect = curve_btn.value.getBoundingClientRect();
	curve_pos.value = {
		top: `${rect.bottom + 6}px`,
		left: `${Math.max(8, Math.min(rect.left, window.innerWidth - 248))}px`,
		width: "240px",
	};
	curve_open.value = true;
}
function close_columns(event) {
	if (curve_open.value && !curve_menu.value?.contains(event.target) && !curve_btn.value?.contains(event.target)) {
		curve_open.value = false;
	}
	if (!columns_open.value) return;
	if (columns_menu.value?.contains(event.target) || columns_btn.value?.contains(event.target)) return;
	columns_open.value = false;
}
// ---------- เมนูคลิกขวา ----------
const SEP = { sep: true };
function open_task(task, tab) {
	selected.value = task.name;
	inspector_tab.value = tab;
}
// คลิกแถวงานใน Gantt ทรัพยากร: กลับมุมมองงานแล้วเปิดแท็บทรัพยากรของงานนั้น
function open_from_board(task) {
	settings.board = "tasks";
	open_task(task, "resources");
	nextTick(() => sheet.value?.scroll_to_task(task.name));
}
function set_all_groups(level) {
	settings.level = level;
	sheet.value?.set_level(level);
}
function open_menu({ task, day, x, y }) {
	const cutoff_items =
		day === null
			? []
			: [
					{
						label: `ตั้ง Cut-off เป็น ${thai_date(from_day(day), { year: true })}`,
						icon: "calendar",
						action: () => (p.cutoff = from_day(day)),
					},
			  ];
	const history_items = !p.can_write ? [] : [
		SEP,
		{ label: "ย้อนกลับ", icon: "undo", hint: "Ctrl+Z", disabled: !p.history.past.length, action: () => p.undo() },
		{ label: "ทำซ้ำ", icon: "redo", hint: "Ctrl+Y", disabled: !p.history.future.length, action: () => p.redo() },
	];
	const items = task.is_group
		? [
				{
					label: sheet.value?.is_collapsed(task) ? "ขยายกลุ่มนี้" : "ย่อกลุ่มนี้",
					icon: sheet.value?.is_collapsed(task) ? "chevron-down" : "chevron-up",
					action: () => sheet.value?.toggle(task),
				},
				{ label: "ขยายทุกกลุ่ม", icon: "maximize", action: () => set_all_groups(null) },
				{ label: "ย่อทุกกลุ่ม", icon: "minus", action: () => set_all_groups(1) },
				SEP,
				{ label: "รายละเอียด", icon: "info", action: () => open_task(task, "main") },
				...cutoff_items,
				...history_items,
		  ]
		: [
				{ label: "รายละเอียดงาน", icon: "info", action: () => open_task(task, "main") },
				{ label: "กำหนด % แผน", icon: "hash", action: () => open_task(task, "plan") },
				{ label: "ทรัพยากร", icon: "users", action: () => open_task(task, "resources") },
				SEP,
				{ label: "เลื่อนไปที่แถบงาน", icon: "gantt", action: () => sheet.value?.scroll_to_task(task.name) },
				...cutoff_items,
				...(p.can_write
					? [
							SEP,
							{
								label: "ล้าง % แผนที่กำหนดเอง",
								icon: "x",
								danger: true,
								disabled: !task.plan_distribution,
								action: () => p.update_distribution(task, null),
							},
							{
								label: "ล้างงานก่อนหน้า",
								icon: "link",
								danger: true,
								disabled: !task.predecessors,
								action: () => p.update_links(task, []),
							},
					  ]
					: []),
				...history_items,
		  ];
	menu.value = { task: task.name, x, y, items };
}

function cutoff_today() {
	p.cutoff = from_day(today());
	timeline.value?.scroll_to_day(p.cutoff_day);
}

// ---------- คีย์ลัด ----------
function on_key(event) {
	if (props.readonly) return;
	if (!(event.ctrlKey || event.metaKey) || event.altKey) return;
	const key = event.key.toLowerCase();
	if (key === "s") {
		event.preventDefault();
		p.save();
		return;
	}
	const is_undo = key === "z" && !event.shiftKey;
	const is_redo = key === "y" || (key === "z" && event.shiftKey);
	if (!is_undo && !is_redo) return;
	if (event.target.closest?.("input, textarea, [contenteditable='true']")) return;
	event.preventDefault();
	if (is_undo) p.undo();
	else p.redo();
}

// ---------- ออกจากหน้า ----------
let resolve_leave = null;
function answer(ok) {
	leaving.value = null;
	resolve_leave?.(ok);
	resolve_leave = null;
}
async function guard() {
	if (await p.flush()) return true;
	return new Promise((resolve) => {
		resolve_leave = resolve;
		leaving.value = true;
	});
}
function on_beforeunload(event) {
	if (p.dirty) {
		event.preventDefault();
		event.returnValue = "";
	}
}
const on_visibility = () => !document.hidden && p.check_remote();

async function reload() {
	try {
		await p.load();
	} catch (e) {
		show_error(e);
	}
}

let timer = null;
async function start() {
	let cm = props.params.cm;
	try {
		if (!cm) {
			const plan = await call("consbiz.site_app.get_plan", { project: state.project?.name });
			if (!plan) {
				error.value = "โครงการนี้ยังไม่มีแผนงาน";
				return;
			}
			cm = plan.construction_management;
		}
		await p.load(cm);
		if (!props.readonly && !p.can_write) error.value = "ไม่มีสิทธิ์แก้แผนงาน";
	} catch (e) {
		show_error(e);
		error.value = "โหลดแผนงานไม่สำเร็จ";
		return;
	}
	if (settings.level) setTimeout(() => sheet.value?.set_level(settings.level));
	else if (props.readonly) setTimeout(() => sheet.value?.collapse_done());
	timer = setInterval(() => p.check_remote(), REFRESH_INTERVAL);
}

onMounted(() => {
	if (!props.readonly) set_leave_guard(guard);
	wide_query.addEventListener("change", on_wide);
	window.addEventListener("beforeunload", on_beforeunload);
	document.addEventListener("keydown", on_key);
	document.addEventListener("pointerdown", close_columns, true);
	document.addEventListener("visibilitychange", on_visibility);
	start();
});
onBeforeUnmount(() => {
	set_leave_guard(null);
	clearInterval(timer);
	wide_query.removeEventListener("change", on_wide);
	window.removeEventListener("beforeunload", on_beforeunload);
	document.removeEventListener("keydown", on_key);
	document.removeEventListener("pointerdown", close_columns, true);
	document.removeEventListener("visibilitychange", on_visibility);
});
</script>
