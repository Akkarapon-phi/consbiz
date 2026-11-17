<!-- หน้าตั้งค่า (เปิดจากเมนู avatar): ซ้าย = เมนูแบ่งตามหัวข้อหลัก (group) ขวา = การตั้งค่า
     เพิ่มหน้าใหม่ที่ PAGES (group = หัวข้อหลัก เช่น ระบบ / บัญชี, when = เห็นตามสิทธิ์) -->
<template>
	<Sheet :open="open" title="ตั้งค่า" wide @close="emit('close')">
		<div v-if="open" class="ss-settings">
			<nav class="ss-settings-menu" aria-label="หัวข้อการตั้งค่า">
				<template v-for="g in groups" :key="g.label">
					<div class="ss-settings-group">{{ g.label }}</div>
					<button
						v-for="p in g.pages"
						:key="p.key"
						type="button"
						class="ss-settings-link"
						:class="{ 'is-active': p.key === page.key }"
						@click="active = p.key"
					>
						<Icon :name="p.icon" :size="16" />
						<span>{{ p.label }}</span>
					</button>
				</template>
			</nav>
			<div class="ss-settings-body">
				<component :is="page.component" :key="page.key" />
			</div>
		</div>
	</Sheet>
</template>

<script setup>
import { computed, ref } from "vue";
import Sheet from "./Sheet.vue";
import Icon from "./Icon.vue";
import PermissionSettings from "./settings/PermissionSettings.vue";
import LabourSettings from "./settings/LabourSettings.vue";
import { boot } from "../api.js";

defineProps({ open: Boolean });
const emit = defineEmits(["close"]);

const PAGES = [
	{
		key: "permissions",
		group: "ระบบ",
		label: "สิทธิ์การใช้งาน",
		icon: "shield",
		component: PermissionSettings,
		when: () => boot.can?.settings,
	},
	{
		key: "labour",
		group: "บัญชี",
		label: "ค่าแรงคนงาน",
		icon: "calculator",
		component: LabourSettings,
		when: () => boot.can?.labour_settings,
	},
];
const pages = PAGES.filter((p) => p.when());
const groups = pages.reduce((out, p) => {
	let g = out.find((x) => x.label === p.group);
	if (!g) out.push((g = { label: p.group, pages: [] }));
	g.pages.push(p);
	return out;
}, []);
const active = ref(pages[0]?.key);
const page = computed(() => pages.find((p) => p.key === active.value) || pages[0]);
</script>
