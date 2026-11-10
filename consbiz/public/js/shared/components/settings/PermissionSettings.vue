<!-- ตั้งค่าสิทธิ์ต่อหมวดในแอป (API consbiz/app_settings.py): เลือกหมวด แล้วเพิ่ม Role และกำหนดว่าแต่ละ Role ทำอะไรได้
     ค่าเดียวกับ Role Permission Manager ของระบบเต็ม สวิตช์มีผลทันที และ server เปิด/ปิดสิทธิ์ที่ต้องไปด้วยกันให้
     Role ที่เพิ่มใหม่ยังไม่บันทึกอะไรจนกว่าจะเปิดสวิตช์ -->
<template>
	<div class="ss-perm">
		<Skeleton v-if="!setup || !rules" :rows="6" />
		<template v-else>
			<div class="ss-list-head ss-list-head--many">
				<StatusTabs v-model="active" :options="tabs" />
				<div class="ss-list-tools">
					<div ref="adder" class="ss-perm-add">
						<button type="button" class="ss-btn ss-btn--primary ss-list-create" @click="open_picker">
							<Icon name="plus" :size="18" :stroke="2.6" />
							<span>เพิ่ม Role</span>
						</button>
						<div v-if="picking" class="ss-perm-picker">
							<input
								ref="search"
								v-model="txt"
								class="ss-input"
								type="search"
								placeholder="ค้นหา Role"
								aria-label="ค้นหา Role"
								@keydown.esc.stop="picking = false"
							/>
							<div class="ss-perm-options">
								<button v-for="r in choices" :key="r.value" type="button" @click="add_role(r.value)">
									{{ r.label }}
								</button>
								<p v-if="!choices.length" class="ss-muted">ไม่พบ Role</p>
							</div>
						</div>
					</div>
				</div>
			</div>

			<p class="ss-muted ss-perm-note">มีผลทันทีทั้งแอปและระบบเต็ม ผู้ใช้ต้องโหลดหน้าใหม่จึงจะเห็นเมนูและปุ่มที่เปลี่ยน</p>

			<Empty v-if="!current_roles.length" icon="shield" title="ยังไม่มี Role ในหมวดนี้" text="กดเพิ่ม Role เพื่อกำหนดสิทธิ์" />
			<div v-else class="ss-perm-scroll">
				<table class="ss-perm-table">
					<thead>
						<tr>
							<th class="ss-perm-name">Role / เอกสาร</th>
							<th v-for="ptype in setup.columns" :key="ptype">{{ PTYPES[ptype] }}</th>
						</tr>
					</thead>
					<tbody v-for="role in current_roles" :key="role">
						<tr class="ss-perm-module">
							<th class="ss-perm-name" :colspan="setup.columns.length + 1">
								<div class="ss-perm-role-head">
									<span>{{ role_label(role) }}</span>
									<button
										type="button"
										class="ss-icon-btn"
										:aria-label="`เอา ${role_label(role)} ออกจากหมวดนี้`"
										:title="`เอา ${role_label(role)} ออกจากหมวดนี้`"
										:disabled="saving"
										@click="remove_role(role)"
									>
										<Icon name="trash" :size="15" />
									</button>
								</div>
							</th>
						</tr>
						<tr v-for="row in module.rows" :key="row.key">
							<td class="ss-perm-name">
								<span>{{ row.label }}</span>
								<small v-if="rules[role]?.[row.key]?.if_owner">มีกฎเฉพาะเอกสารที่ตนสร้างด้วย แก้ในระบบเต็ม</small>
							</td>
							<td v-for="ptype in setup.columns" :key="ptype" class="ss-perm-cell">
								<label
									v-if="row.columns.includes(ptype)"
									class="ss-toggle"
									:class="{ 'is-on': is_on(role, row, ptype) }"
								>
									<input
										type="checkbox"
										:checked="is_on(role, row, ptype)"
										:disabled="saving"
										:aria-label="`${role_label(role)} ${row.label}: ${PTYPES[ptype]}`"
										@change="toggle(role, row, ptype, $event)"
									/>
									<span class="ss-toggle-track"><span></span></span>
								</label>
							</td>
						</tr>
					</tbody>
				</table>
			</div>
		</template>
	</div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, reactive, ref } from "vue";
import Icon from "../Icon.vue";
import Empty from "../Empty.vue";
import Skeleton from "../Skeleton.vue";
import StatusTabs from "../StatusTabs.vue";
import { MODULE_META } from "../../modules.js";
import { call, post, show_error } from "../../api.js";

const API = "consbiz.app_settings";
const PTYPES = {
	read: "อ่าน",
	create: "สร้าง",
	write: "แก้ไข",
	delete: "ลบ",
	submit: "ส่ง",
	cancel: "ยกเลิก",
	amend: "แก้ฉบับใหม่",
	export: "ส่งออก",
};

const setup = ref(null);
const rules = ref(null);
const active = ref(null);
const saving = ref(false);
// Role ของแต่ละหมวด คงแถวไว้ระหว่างเปิดหน้านี้ ปิดสวิตช์หมดแล้วแถวไม่หายไปกลางคัน
const members = reactive({});

const module_key = (m) => `${m.app}:${m.section}`;
const module = computed(() => setup.value.modules.find((m) => module_key(m) === active.value));
const current_roles = computed(() => members[active.value] || []);
const tabs = computed(() =>
	setup.value.modules.map((m) => ({
		value: module_key(m),
		label: MODULE_META[m.app][m.section].label,
		count: members[module_key(m)]?.length || 0,
	}))
);
const role_label = (role) => setup.value.roles.find((r) => r.value === role)?.label || role;
const is_on = (role, row, ptype) => !!rules.value[role]?.[row.key]?.[ptype];

async function load() {
	try {
		const [s, r] = await Promise.all([call(`${API}.get_permission_setup`), call(`${API}.get_all_rules`)]);
		for (const m of s.modules) {
			members[module_key(m)] = s.roles
				.filter((role) => m.rows.some((row) => r[role.value]?.[row.key]))
				.map((role) => role.value);
		}
		active.value = module_key(s.modules[0]);
		rules.value = r;
		setup.value = s;
	} catch (error) {
		show_error(error);
	}
}

async function toggle(role, row, ptype, event) {
	const value = event.target.checked ? 1 : 0;
	saving.value = true;
	try {
		rules.value[role] = await post(`${API}.set_role_permission`, {
			role,
			doctype: row.doctype,
			permlevel: row.permlevel,
			ptype,
			value,
		});
	} catch (error) {
		event.target.checked = !value;
		show_error(error);
	} finally {
		saving.value = false;
	}
}

async function remove_role(role) {
	const has_rules = module.value.rows.some((row) => rules.value[role]?.[row.key]);
	if (has_rules && !window.confirm(`เอา ${role_label(role)} ออกจากหมวดนี้? สิทธิ์ของเอกสารในหมวดจะถูกลบ มีผลทันที`)) return;
	saving.value = true;
	try {
		if (has_rules) {
			const { app, section } = module.value;
			rules.value[role] = await post(`${API}.remove_role_from_module`, { role, app, section });
		}
		members[active.value] = current_roles.value.filter((r) => r !== role);
	} catch (error) {
		show_error(error);
	} finally {
		saving.value = false;
	}
}

// ---------------------------------------------------------------- เพิ่ม Role
const picking = ref(false);
const txt = ref("");
const adder = ref(null);
const search = ref(null);
const choices = computed(() => {
	const q = txt.value.trim().toLowerCase();
	return setup.value.roles
		.filter((r) => !current_roles.value.includes(r.value))
		.filter((r) => !q || `${r.label} ${r.value}`.toLowerCase().includes(q));
});

function close_picker(event) {
	if (!adder.value?.contains(event.target)) picking.value = false;
}
document.addEventListener("pointerdown", close_picker);
onBeforeUnmount(() => document.removeEventListener("pointerdown", close_picker));

async function open_picker() {
	picking.value = !picking.value;
	txt.value = "";
	await nextTick();
	search.value?.focus();
}

function add_role(role) {
	members[active.value] = [role, ...current_roles.value];
	picking.value = false;
}

load();
</script>
