<!-- ข้อมูลหลัก 1 รายการ (หมวดข้อมูลหลัก): พนักงาน / สินค้า / ลูกค้า / ผู้ขาย / โครงการ params.kind = หน้ารายการ
     ดูและแก้ในหน้าเดียวกัน ฟอร์มสร้างจาก sections ที่ server ส่งมา (KINDS ใน consbiz/master_data.py) tab = หมวดของฟอร์ม
     ลอกหน้าตาจากเอกสารพนักงาน (HrDocPage.vue) -->
<template>
	<div>
		<TopBar :title="title" :subtitle="doc?.name || 'ใหม่'" :back_to="params.kind" no_project />

		<div class="ss-content">
			<FormHead v-if="doc" many v-model="tab" :tabs="tabs" :actions="actions" :menu="menu" :busy="busy" />

			<Skeleton v-if="!doc" :rows="6" />
			<template v-else>
				<section v-for="s in shown_sections" :key="s.label" class="ss-card ss-form">
					<div v-if="doc.name && s === view.sections[0]" class="ss-doc-head-top">
						<span class="ss-tag" :class="`tone-${doc.status_tone}`">{{
							doc.status_label
						}}</span>
						<span class="ss-doc-date">{{ doc.name }}</span>
					</div>
					<p v-if="view.note && s === view.sections[0]" class="ss-note-line">
						{{ view.note }}
					</p>
					<p v-if="s.note" class="ss-muted">{{ s.note }}</p>
					<div class="ss-form-row">
						<template v-for="f in s.fields" :key="f.fieldname">
							<div
								v-if="visible(f)"
								class="ss-md-field"
								:class="{ 'is-wide': f.wide || f.type === 'check' }"
							>
								<!-- สวิตช์ -->
								<label
									v-if="f.type === 'check'"
									class="ss-toggle"
									:class="{
										'is-on': doc[f.fieldname],
										'is-readonly': !editable(f),
									}"
								>
									<input
										v-model="doc[f.fieldname]"
										type="checkbox"
										:true-value="1"
										:false-value="0"
										:disabled="!editable(f)"
									/>
									<span class="ss-toggle-track"><span></span></span>
									<span>
										<b>{{ f.label }}</b>
										<small v-if="f.note">{{ f.note }}</small>
									</span>
								</label>

								<!-- Link -->
								<template v-else-if="f.type === 'link'">
									<Picker
										v-model="doc[f.fieldname]"
										:label="f.label"
										:display_value="titles[f.fieldname] || doc[f.fieldname]"
										:remote_fn="(q) => search(f, q)"
										:class="{ 'is-locked': !editable(f) }"
										:required="!!f.reqd"
										:clearable="!f.reqd && editable(f)"
										@select="(o) => pick(f, o)"
									/>
									<small v-if="f.note" class="ss-muted">{{ f.note }}</small>
									<!-- จุดลงเวลา: ตั้ง/แก้ด้วย GPS (Shift Location) -->
									<CheckinLocation
										v-if="f.widget === 'checkin_location' && editable(f)"
										v-model="doc[f.fieldname]"
										:kind="params.kind"
										:docname="doc.name"
										:label="doc.project_name || doc.title || doc.first_name || ''"
										@saved="(r) => (titles[f.fieldname] = r.location_name)"
									/>
								</template>

								<!-- ตาราง (หน่วยแปลงของสินค้า) -->
								<template v-else-if="f.type === 'table'">
									<div class="ss-table-wrap">
										<table class="ss-table ss-table--list">
											<thead>
												<tr>
													<th
														v-for="c in f.columns"
														:key="c.fieldname"
														:class="{ 'is-num': is_num(c) }"
													>
														{{ c.label }}
													</th>
													<th v-if="editable(f)"></th>
												</tr>
											</thead>
											<tbody>
												<tr
													v-for="r in doc[f.fieldname]"
													:key="r._key"
													class="is-static"
												>
													<td
														v-for="c in f.columns"
														:key="c.fieldname"
														:class="{ 'is-num': is_num(c) }"
													>
														<template v-if="!editable(f)">{{
															is_num(c)
																? num(r[c.fieldname])
																: r[c.fieldname]
														}}</template>
														<Picker
															v-else-if="c.type === 'link'"
															class="ss-md-cell-picker"
															v-model="r[c.fieldname]"
															:label="c.label"
															:remote_fn="(q) => search(c, q)"
														/>
														<input
															v-else-if="is_num(c)"
															v-model.number="r[c.fieldname]"
															class="ss-input"
															type="number"
															inputmode="decimal"
														/>
														<input
															v-else
															v-model="r[c.fieldname]"
															class="ss-input"
														/>
													</td>
													<td v-if="editable(f)" class="col-nowrap">
														<button
															type="button"
															class="ss-icon-btn"
															title="ลบแถว"
															aria-label="ลบแถว"
															@click="
																doc[f.fieldname] = doc[
																	f.fieldname
																].filter((x) => x !== r)
															"
														>
															<Icon name="trash" :size="16" />
														</button>
													</td>
												</tr>
												<tr v-if="!doc[f.fieldname].length">
													<td
														:colspan="
															f.columns.length +
															(editable(f) ? 1 : 0)
														"
														class="ss-muted"
													>
														ยังไม่มี{{ f.label }}
													</td>
												</tr>
											</tbody>
										</table>
									</div>
									<button
										v-if="editable(f)"
										type="button"
										class="ss-btn ss-btn--soft"
										@click="add_row(f)"
									>
										<Icon name="plus" :size="16" /> เพิ่ม{{ f.label }}
									</button>
								</template>

								<!-- ช่องทั่วไป -->
								<label v-else class="ss-field">
									<span class="ss-field-label"
										>{{ f.label }}<em v-if="f.reqd">*</em></span
									>
									<SelectBox
										v-if="f.type === 'select'"
										v-model="doc[f.fieldname]"
										:options="select_options(f)"
										:label="f.label"
										:placeholder="f.reqd ? 'เลือก' : 'ไม่ระบุ'"
										:disabled="!editable(f)"
									/>
									<DateInput
										v-else-if="f.type === 'date'"
										v-model="doc[f.fieldname]"
										:label="f.label"
										:disabled="!editable(f)"
										:clearable="!f.reqd"
									/>
									<MoneyInput
										v-else-if="f.type === 'money'"
										v-model="doc[f.fieldname]"
										class="ss-input"
										:disabled="!editable(f)"
									/>
									<input
										v-else-if="f.type === 'int' || f.type === 'float'"
										v-model.number="doc[f.fieldname]"
										class="ss-input"
										type="number"
										inputmode="decimal"
										:disabled="!editable(f)"
									/>
									<textarea
										v-else-if="f.type === 'textarea'"
										v-model="doc[f.fieldname]"
										class="ss-input"
										rows="3"
										:disabled="!editable(f)"
									></textarea>
									<input
										v-else
										v-model="doc[f.fieldname]"
										class="ss-input"
										:inputmode="f.digits ? 'numeric' : undefined"
										:maxlength="f.digits || undefined"
										:disabled="!editable(f)"
									/>
									<small v-if="digits_wrong(f)" class="ss-field-error"
										>ต้องเป็นตัวเลข {{ f.digits }} หลัก</small
									>
									<small v-else-if="f.note" class="ss-muted">{{ f.note }}</small>
								</label>
							</div>
						</template>
					</div>
				</section>
			</template>
		</div>

		<DeleteSheet
			:open="deleting"
			:label="kind.label"
			:name="doc?.name"
			:method="`${API}.delete_doc`"
			:args="{ kind: params.kind, name: doc?.name }"
			@close="deleting = false"
			@deleted="go(params.kind, {}, { replace: true })"
		/>
	</div>
</template>

<script setup>
import { computed, ref } from "vue";
import DateInput from "../../../shared/components/DateInput.vue";
import DeleteSheet from "../../../shared/components/DeleteSheet.vue";
import CheckinLocation from "./CheckinLocation.vue";
import Icon from "../../../shared/components/Icon.vue";
import MoneyInput from "../../../shared/components/MoneyInput.vue";
import Picker from "../../../shared/components/Picker.vue";
import SelectBox from "../../../shared/components/SelectBox.vue";
import Skeleton from "../../../shared/components/Skeleton.vue";
import TopBar from "../../../shared/components/TopBar.vue";
import FormHead from "../../../shared/components/FormHead.vue";
import { LABELS, doc_menu, step_actions } from "../../../shared/form_actions.js";
import {
	back,
	call,
	celebrate,
	desk_url,
	go,
	num,
	post,
	scope_args,
	show_error,
	state,
} from "../../../shared/api.js";
import { API, MASTER_KINDS } from "./kinds.js";

const DOCTYPES = {
	"md-employees": "Employee",
	"md-items": "Item",
	"md-customers": "Customer",
	"md-suppliers": "Supplier",
	"md-projects": "Project",
};

const params = state.route.params;
const kind = MASTER_KINDS[params.kind] || MASTER_KINDS["md-employees"];

let key = 0;
const tab = ref("0");
const view = ref({ sections: [] });
const doc = ref(null);
const titles = ref({});
const saved = ref("");
const busy = ref(false);
const deleting = ref(false);

const fields = computed(() => view.value.sections.flatMap((s) => s.fields));
const tabs = computed(() =>
	view.value.sections.map((s, i) => ({ value: String(i), label: s.label })),
);
const shown_sections = computed(() =>
	view.value.sections.filter((_s, i) => String(i) === tab.value),
);
const title = computed(() =>
	doc.value?.title
		? `${kind.label} · ${doc.value.title}`
		: kind.create_label || `${kind.label}ใหม่`,
);

const visible = (f) =>
	!f.show || Object.entries(f.show).every(([field, value]) => doc.value[field] === value);
const editable = (f) =>
	!!view.value.can_edit &&
	!f.read_only &&
	(f.permlevel === undefined || view.value.writable_levels.includes(f.permlevel)) &&
	!(f.create_only && doc.value.name);
const is_num = (c) => ["int", "float", "money"].includes(c.type);
const empty = (v) => v === null || v === undefined || v === "";
const digits_wrong = (f) => {
	const v = doc.value[f.fieldname];
	return f.digits && !empty(v) && !new RegExp(`^\\d{${f.digits}}$`).test(String(v).trim());
};
const select_options = (f) =>
	f.reqd ? f.options : [{ value: "", label: "ไม่ระบุ" }, ...f.options];
// ที่อยู่: กรอกช่องใดก็ต้องกรอกช่องบังคับของที่อยู่ให้ครบ (ไม่กรอกเลย = ไม่สร้างที่อยู่)
const address_used = computed(() =>
	fields.value.some(
		(f) => f.fieldname.startsWith("address.") && !empty(doc.value?.[f.fieldname]),
	),
);
const missing = computed(() => {
	if (!doc.value) return [];
	return fields.value
		.filter((f) => {
			if (!f.reqd || f.type === "check" || !visible(f) || !editable(f)) return false;
			if (f.fieldname.startsWith("address.") && !address_used.value) return false;
			return empty(doc.value[f.fieldname]);
		})
		.map((f) => f.label)
		.concat(fields.value.filter(digits_wrong).map((f) => f.label));
});

const payload = () => {
	const out = { name: doc.value.name, modified: doc.value.modified };
	for (const f of fields.value) {
		const v = doc.value[f.fieldname];
		out[f.fieldname] =
			f.type === "table"
				? v.map((r) =>
						Object.fromEntries(
							f.columns.map((c) => [c.fieldname, r[c.fieldname] ?? null]),
						),
					)
				: empty(v)
					? null
					: v;
	}
	return JSON.stringify(out);
};
const dirty = computed(() => !!doc.value && (!doc.value.name || payload() !== saved.value));

function link_filters(f) {
	const out = {};
	for (const [field, source] of Object.entries(f.filters || {})) {
		// ค่าคงที่ (เช่น is_group: 0, status: "Active") หรือค่าจากช่องในฟอร์ม (company)
		out[field] =
			typeof source === "string" && source in doc.value ? doc.value[source] : source;
	}
	return out;
}
const search = (f, txt) =>
	call(`${API}.search`, {
		kind: params.kind,
		doctype: f.doctype,
		txt,
		filters: JSON.stringify(link_filters(f)),
	});
function pick(f, option) {
	titles.value[f.fieldname] =
		option && option.label !== option.value
			? `${option.label} (${option.value})`
			: option?.value;
}
function add_row(f) {
	doc.value[f.fieldname].push({
		_key: ++key,
		...Object.fromEntries(f.columns.map((c) => [c.fieldname, is_num(c) ? 1 : null])),
	});
}

function apply(result) {
	view.value = { ...result, doctype: DOCTYPES[params.kind] };
	titles.value = { ...result.titles };
	const d = { ...result.doc };
	for (const f of result.sections.flatMap((s) => s.fields)) {
		if (f.type === "table")
			d[f.fieldname] = (d[f.fieldname] || []).map((r) => ({ ...r, _key: ++key }));
		if (f.type === "select" && empty(d[f.fieldname])) d[f.fieldname] = f.reqd ? null : "";
	}
	doc.value = d;
	saved.value = payload();
	if (Number(tab.value) >= result.sections.length) tab.value = "0";
}

async function save() {
	const is_new = !doc.value.name;
	busy.value = true;
	try {
		const result = await post(`${API}.save_doc`, { kind: params.kind, data: payload() });
		apply(result);
		await celebrate("บันทึกแล้ว", result.doc.name);
		if (is_new) go("md-doc", { kind: params.kind, name: result.doc.name }, { replace: true });
	} catch (e) {
		show_error(e);
	} finally {
		busy.value = false;
	}
}

async function load() {
	try {
		const name = params.name && params.name !== "new" ? params.name : undefined;
		apply(
			await call(`${API}.get_doc`, {
				kind: params.kind,
				name,
				company: scope_args().company,
			}),
		);
	} catch (e) {
		show_error(e);
		back(params.kind);
	}
}
// หัวฟอร์ม: ข้อมูลหลักไม่มีขั้นอนุมัติ มีแค่บันทึก
const actions = computed(() =>
	step_actions({
		stage: "draft",
		is_new: !doc.value.name,
		dirty: dirty.value,
		save: view.value.can_edit && {
			run: save,
			disabled: !!missing.value.length,
			title: missing.value.length ? `ยังไม่ได้กรอก: ${missing.value.join(", ")}` : "",
		},
	})
);
const menu = computed(() =>
	doc_menu({
		refresh: doc.value.name && load,
		desk: [view.value.doctype, doc.value.name],
		remove: view.value.can_delete && (() => (deleting.value = true)),
	})
);

load();
</script>
