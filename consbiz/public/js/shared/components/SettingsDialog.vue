<!-- หน้าตั้งค่า (เปิดจากเมนู avatar): ซ้าย = เมนู ขวา = การตั้งค่า เพิ่มหัวข้อใหม่ที่ PAGES (when = เห็นตามสิทธิ์) -->
<template>
	<Sheet :open="open" title="ตั้งค่า" wide @close="emit('close')">
		<div v-if="open" class="ss-settings">
			<nav class="ss-settings-menu" aria-label="หัวข้อการตั้งค่า">
				<button
					v-for="p in pages"
					:key="p.key"
					type="button"
					class="ss-settings-link"
					:class="{ 'is-active': p.key === page.key }"
					@click="active = p.key"
				>
					<Icon :name="p.icon" :size="16" />
					<span>{{ p.label }}</span>
				</button>
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
import { boot } from "../api.js";

defineProps({ open: Boolean });
const emit = defineEmits(["close"]);

const PAGES = [
	{
		key: "permissions",
		label: "สิทธิ์การใช้งาน",
		icon: "shield",
		component: PermissionSettings,
		when: () => boot.can?.settings,
	},
];
const pages = PAGES.filter((p) => p.when());
const active = ref(pages[0]?.key);
const page = computed(() => pages.find((p) => p.key === active.value) || pages[0]);
</script>
