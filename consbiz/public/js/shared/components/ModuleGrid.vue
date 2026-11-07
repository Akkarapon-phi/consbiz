<!-- ตารางหมวดงาน: ไอคอน + ชื่อ จัดกลุ่มตามแอป
     หน้าแรก (Desktop.vue) = ทุกแอป, ตารางหมวดของมือถือ (SectionLauncher.vue) = local_only เฉพาะกลุ่มแอปนี้
     หมวดของแอปนี้สลับในแอป หมวดของแอปอื่นเป็นลิงก์ (โหลด bundle ของแอปนั้น) -->
<template>
	<div class="ss-modules">
		<section v-for="g in groups" :key="g.app" class="ss-module-group">
			<h2 v-if="groups.length > 1" class="ss-module-group-title">{{ g.label }}</h2>
			<div class="ss-module-grid">
				<component
					:is="m.local ? 'button' : 'a'"
					v-for="(m, i) in g.modules"
					:key="m.key"
					:type="m.local ? 'button' : undefined"
					:href="m.local ? undefined : m.url"
					class="ss-module"
					:class="{ 'is-active': m.local && m.section === state.section }"
					:style="{ '--i': i, '--sw': m.colors[0], '--sw2': m.colors[1] }"
					:title="m.note"
					@click="m.local && choose(m.section)"
				>
					<span class="ss-module-icon">
						<Icon :name="m.icon" :size="24" :stroke="2" />
						<span v-if="badge(m)" class="ss-module-badge">{{ badge(m) }}</span>
					</span>
					<span class="ss-module-label">{{ m.label }}</span>
				</component>
			</div>
		</section>
		<section v-if="boot.desk && !local_only" class="ss-module-group">
			<h2 v-if="groups.length > 1" class="ss-module-group-title">อื่นๆ</h2>
			<div class="ss-module-grid">
				<a
					class="ss-module"
					href="/app"
					title="เอกสารและรายงานทั้งหมด"
					:style="{ '--sw': '#64748b', '--sw2': '#334155' }"
				>
					<span class="ss-module-icon"><Icon name="monitor" :size="24" :stroke="2" /></span>
					<span class="ss-module-label">ระบบเต็ม</span>
				</a>
			</div>
		</section>
	</div>
</template>

<script setup>
import Icon from "./Icon.vue";
import { app } from "../app.js";
import { boot, state, vibrate } from "../api.js";
import { module_badge, module_groups } from "../modules.js";

const props = defineProps({ local_only: Boolean });
const emit = defineEmits(["choose"]);
const groups = module_groups().filter((g) => !props.local_only || g.app === app.key);
const badge = (m) => module_badge(m, state);

function choose(section) {
	vibrate(10);
	emit("choose", section);
}
</script>
