<template>
	<!-- ตารางเอกสารจัดซื้อ/ขาย (แท็บเล็ต/จอใหญ่) มือถือใช้การ์ด (DocCard.vue)
	     คอลัมน์ตามชนิดเอกสาร (COLUMNS) ท้ายตาราง: ผู้รับมอบหมาย / แก้ไขล่าสุด / ถูกใจ แบบรายการของระบบเต็ม
	     หัวคอลัมน์กดเรียงได้ (emit sort) ช่องเลือกหลายแถว (toggle / toggle-all)
	     สถานะอยู่ใต้เลขที่ทุกขนาด, แท็บเล็ต (<1180): ซ่อน .col-wide -->
	<div class="ss-table-wrap">
		<table class="ss-table ss-table--list" :class="{ 'is-compact': preview }">
			<thead>
				<tr>
					<th class="col-check">
						<input
							type="checkbox"
							class="ss-check"
							aria-label="เลือกทั้งหมด"
							:checked="all_checked"
							:indeterminate.prop="some_checked && !all_checked"
							@change="$emit('toggle-all')"
						/>
					</th>
					<th v-for="c in columns" :key="c.key" :class="c.class" :aria-sort="aria_sort(c)">
						<button v-if="c.sort" type="button" class="ss-th-sort" @click="$emit('sort', c.sort)">
							{{ c.label }}
							<Icon
								:name="
									sort === c.sort
										? order === 'asc'
											? 'chevron-up'
											: 'chevron-down'
										: 'arrow-up-down'
								"
								:size="13"
								:stroke="2.4"
								:class="{ 'is-idle': sort !== c.sort }"
							/>
						</button>
						<template v-else>{{ c.label }}</template>
					</th>
				</tr>
			</thead>
			<tbody>
				<tr
					v-for="(row, i) in rows"
					:key="row.name"
					:class="{
						'is-late': row.overdue,
						'is-selected': selected.has(row.name),
						'is-active': preview && row.name === active,
					}"
					:style="{ '--i': Math.min(i, 20) }"
					tabindex="0"
					@click="preview ? $emit('select', row) : open(row)"
					@dblclick="open(row)"
					@keydown.enter="open(row)"
					@keydown.down.prevent="step($event, 1)"
					@keydown.up.prevent="step($event, -1)"
				>
					<td class="col-check" @click.stop>
						<input
							type="checkbox"
							class="ss-check"
							:aria-label="`เลือก ${row.name}`"
							:checked="selected.has(row.name)"
							@change="$emit('toggle', row.name)"
						/>
					</td>
					<td v-for="c in columns" :key="c.key" :class="c.class">
						<template v-if="c.key === 'name'">
							<span class="ss-doc-no">{{ row.name }}</span>
							<!-- สถานะอยู่ใต้เลขที่ (ไม่มีคอลัมน์สถานะ: ประหยัดความกว้าง กรองสถานะที่แท็บ) -->
							<span class="ss-doc-meta">
								<span class="ss-tag" :class="`tone-${row.status_tone}`">{{
									row.status_label
								}}</span>
								<small v-if="row.bill_no" class="ss-doc-bill" :title="`บิล ${row.bill_no}`"
									>บิล {{ row.bill_no }}</small
								>
							</span>
						</template>
						<template v-else-if="c.key === 'subject'">
							<span class="ss-cell-main" :title="subject(row)">{{ subject(row) }}</span>
							<small v-if="row.project" :title="row.project_name">{{
								row.project_name || row.project
							}}</small>
						</template>
						<template v-else-if="c.key === 'date'">{{
							thai_date(row.date, { year: true })
						}}</template>
						<template v-else-if="c.key === 'due'">
							<span v-if="row.due" :class="{ 'is-due': row.overdue }">{{
								thai_date(row.due, { year: true })
							}}</span>
						</template>
						<span
							v-else-if="c.pct"
							class="ss-table-pct"
							:class="{ 'is-muted': row.docstatus !== 1 }"
						>
							<i><b :style="{ width: `${Math.min(100, row[c.pct] || 0)}%` }"></b></i>
							{{ Math.round(row[c.pct] || 0) }}%
						</span>
						<template v-else-if="c.key === 'amount'">{{ money(row.amount) }}</template>
						<template v-else-if="c.key === 'outstanding'">
							<span v-if="row.outstanding" :class="{ 'is-due': row.overdue }">{{
								money(row.outstanding)
							}}</span>
						</template>
						<template v-else-if="c.key === 'purpose'">{{ row.purpose }}</template>
						<span
							v-else-if="c.key === 'assigned'"
							class="ss-avatars"
							:title="row.assigned.map((a) => a.name).join(', ')"
						>
							<span
								v-for="a in row.assigned.slice(0, 2)"
								:key="a.user"
								class="ss-avatar ss-avatar--xs"
								:class="`tone-${tone(a.user)}`"
								>{{ initials(a.name) }}</span
							>
							<span
								v-if="row.assigned.length > 2"
								class="ss-avatar ss-avatar--xs ss-avatar--more"
								>+{{ row.assigned.length - 2 }}</span
							>
						</span>
						<span v-else-if="c.key === 'modified'" :title="row.modified">{{
							time_ago(row.modified)
						}}</span>
						<button
							v-else-if="c.key === 'like'"
							type="button"
							class="ss-like"
							:class="{ 'is-on': row.liked }"
							:aria-pressed="row.liked"
							:aria-label="row.liked ? 'เลิกถูกใจ' : 'ถูกใจ'"
							:title="row.likes ? `ถูกใจ ${row.likes} คน` : 'ถูกใจ'"
							@click.stop="like(row)"
						>
							<Icon name="heart" :size="16" :stroke="2.2" />
						</button>
					</td>
				</tr>
			</tbody>
		</table>
	</div>
</template>

<script setup>
import { computed } from "vue";
import Icon from "../components/Icon.vue";
import { DOC_KINDS } from "./kinds.js";
import { go, initials, money, post, show_error, thai_date, time_ago, tone } from "../api.js";

const props = defineProps({
	rows: Array,
	kind: String,
	sort: String,
	order: String,
	selected: { type: Set, default: () => new Set() },
	// จอ ≥1480: คลิก = เลือกดูตัวอย่างข้างตาราง (emit select) ดับเบิลคลิก/Enter = เปิดเต็มหน้า
	preview: Boolean,
	active: String,
});
const emit = defineEmits(["sort", "toggle", "toggle-all", "select"]);

const config = computed(() => DOC_KINDS[props.kind]);

// คอลัมน์ต่อชนิดเอกสาร sort = key ของ site_docs.SORTS, pct = ช่อง % ความคืบหน้า
// class: col-wide = ซ่อนบนแท็บเล็ต (<1180) is-num = ชิดขวา
// กรอบตารางแคบ (container query ใน site.css): ย่อแถบ % → ซ่อน col-meta (มอบหมาย/แก้ไขล่าสุด) → ซ่อน col-pct
const columns = computed(() => {
	const c = config.value;
	const head = [
		{ key: "name", label: "เลขที่", sort: "name", class: "col-no" },
		{ key: "subject", label: c.party || "เรื่อง", sort: c.party ? "party" : null, class: "col-subject" },
		{ key: "date", label: "วันที่เอกสาร", sort: "date", class: "col-date is-date" },
		...(c.due ? [{ key: "due", label: c.due, sort: "due", class: "col-date is-date col-wide" }] : []),
		...(c.progress || []).map(([field, label]) => ({
			key: field,
			label: props.kind === "mr" && field === "per_ordered" ? "สั่งซื้อ" : label,
			pct: field,
			class: "col-pct col-wide",
		})),
	];
	const money_cols =
		props.kind === "mr"
			? [{ key: "purpose", label: "วัตถุประสงค์", class: "col-purpose col-wide" }]
			: [
					{ key: "amount", label: "ยอดเงิน", sort: "amount", class: "is-num" },
					...(["pi", "si"].includes(props.kind)
						? [
								{
									key: "outstanding",
									label: "ค้าง",
									sort: "outstanding",
									class: "is-num col-wide",
								},
						  ]
						: []),
			  ];
	return [
		...head,
		...money_cols,
		{ key: "assigned", label: "มอบหมาย", class: "col-assign col-meta col-wide" },
		{ key: "modified", label: "แก้ไขล่าสุด", class: "col-modified col-meta col-wide" },
		{ key: "like", label: "", class: "col-like" },
	];
});

const all_checked = computed(() => props.rows.length && props.rows.every((r) => props.selected.has(r.name)));
const some_checked = computed(() => props.rows.some((r) => props.selected.has(r.name)));

const subject = (row) => row.party || row.title || row.name;

function aria_sort(column) {
	if (!column.sort || props.sort !== column.sort) return undefined;
	return props.order === "asc" ? "ascending" : "descending";
}

// ถูกใจแบบระบบเต็ม (frappe.desk.like.toggle_like) เปลี่ยนในตารางทันที ผิดพลาดแล้วคืนค่า
async function like(row) {
	const on = !row.liked;
	row.liked = on;
	row.likes = Math.max(0, (row.likes || 0) + (on ? 1 : -1));
	try {
		await post("frappe.desk.like.toggle_like", {
			doctype: config.value.doctype,
			name: row.name,
			add: on ? "Yes" : "No",
		});
	} catch (error) {
		row.liked = !on;
		row.likes = Math.max(0, row.likes + (on ? -1 : 1));
		show_error(error);
	}
}

// ↑↓ เลื่อนแถว (โหมดตัวอย่าง: เลือกแถวใหม่ด้วย)
function step(event, delta) {
	const tr =
		delta > 0
			? event.target.closest("tr").nextElementSibling
			: event.target.closest("tr").previousElementSibling;
	if (!tr) return;
	tr.focus();
	const index = [...tr.parentElement.children].indexOf(tr);
	if (props.preview && props.rows[index]) emit("select", props.rows[index]);
}

const open = (row) => go(`${config.value.section}-doc`, { kind: props.kind, name: row.name });
</script>
