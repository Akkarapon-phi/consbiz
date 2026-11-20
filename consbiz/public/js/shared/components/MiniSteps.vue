<!-- แถบขั้นตอนขนาดเล็ก (สถานะเอกสาร) บนสุดของการ์ดเนื้อหาใต้แท็บหัวฟอร์ม (ตกลง 2026-11-18)
     steps = [{ label, state: done|current|todo|error, note? }] จาก site_docs.steps_of -->
<template>
	<ol v-if="steps && steps.length" class="ss-mini-steps" :aria-label="label">
		<li v-for="(st, i) in steps" :key="i" :class="`is-${st.state}`">
			<span class="ss-mini-step-dot">
				<Icon v-if="st.state === 'done'" name="check" :size="11" :stroke="3.4" />
				<Icon v-else-if="st.state === 'error'" name="x" :size="11" :stroke="3.4" />
				<template v-else>{{ i + 1 }}</template>
			</span>
			<span class="ss-mini-step-label">{{ st.label }}</span>
			<small v-if="st.note && st.state !== 'todo'">{{ st.note }}</small>
		</li>
	</ol>
</template>

<script setup>
import { computed } from "vue";
import Icon from "./Icon.vue";

const props = defineProps({ steps: Array });
const label = computed(() => {
	const cur = (props.steps || []).find((s) => s.state === "current" || s.state === "error");
	return `ขั้นตอน${cur ? `: ${cur.label}` : ""}`;
});
</script>
