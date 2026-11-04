<template>
	<Teleport to="body">
		<Transition name="ss-backdrop">
			<div v-if="open" class="ss-backdrop" @click="close"></div>
		</Transition>
		<Transition name="ss-sheet">
			<div
				v-if="open"
				class="ss-sheet"
				:class="{ 'ss-sheet--full': full }"
				:style="drag ? { transform: `translateY(${drag}px)`, transition: 'none' } : null"
				role="dialog"
				aria-modal="true"
			>
				<div class="ss-sheet-grip" @pointerdown="start_drag">
					<span></span>
				</div>
				<div v-if="title || $slots.header" class="ss-sheet-head">
					<slot name="header">
						<div class="ss-sheet-title">{{ title }}</div>
						<div v-if="subtitle" class="ss-sheet-sub">{{ subtitle }}</div>
					</slot>
					<button type="button" class="ss-icon-btn ss-sheet-close" aria-label="ปิด" @click="close">
						<Icon name="x" />
					</button>
				</div>
				<div class="ss-sheet-body">
					<slot />
				</div>
				<div v-if="$slots.footer" class="ss-sheet-foot">
					<slot name="footer" />
				</div>
			</div>
		</Transition>
	</Teleport>
</template>

<script setup>
// Bottom sheet: ลากแถบด้านบนลงเพื่อปิด
import { onBeforeUnmount, ref, watch } from "vue";
import Icon from "./Icon.vue";

const props = defineProps({
	open: Boolean,
	title: String,
	subtitle: String,
	full: Boolean,
});
const emit = defineEmits(["close"]);
const drag = ref(0);

function close() {
	emit("close");
}

function start_drag(event) {
	const start = event.clientY;
	const move = (e) => (drag.value = Math.max(0, e.clientY - start));
	const end = () => {
		window.removeEventListener("pointermove", move);
		window.removeEventListener("pointerup", end);
		if (drag.value > 90) close();
		drag.value = 0;
	};
	window.addEventListener("pointermove", move);
	window.addEventListener("pointerup", end);
}

// ล็อกการเลื่อนหน้าหลังขณะเปิด, จอใหญ่กด Esc ปิดได้
const on_key = (event) => event.key === "Escape" && close();
watch(
	() => props.open,
	(open) => {
		document.body.classList.toggle("ss-locked", open);
		window[open ? "addEventListener" : "removeEventListener"]("keydown", on_key);
	},
	{ immediate: true }
);
onBeforeUnmount(() => {
	document.body.classList.remove("ss-locked");
	window.removeEventListener("keydown", on_key);
});
</script>
