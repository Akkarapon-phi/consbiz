<!--
	เมนูลอยข้าง Dock หน้าตาและตำแหน่งตาม frappe.ui.Dropdown (es-menu, side: right, align: end)
	หน้าแอปไม่โหลด desk จึงใช้ของ Frappe ตรงๆ ไม่ได้
	groups = [{ label?, items: [{ key, label, sub?, avatar?: { image?, text, tone }, icon?, image?, href?, selected?, onclick? }] }]
-->
<template>
	<Transition name="ss-menu">
		<div v-if="open && anchor" ref="panel" class="ss-menu" role="menu" :style="position">
			<div v-for="(group, g) in groups" :key="g" class="ss-menu-group" role="group">
				<div v-if="group.label" class="ss-menu-label">{{ group.label }}</div>
				<component
					:is="item.href ? 'a' : 'button'"
					v-for="item in group.items"
					:key="item.key"
					:type="item.href ? undefined : 'button'"
					:href="item.href"
					class="ss-menu-item"
					:class="{ 'is-selected': item.selected }"
					role="menuitem"
					@click="activate(item)"
				>
					<span
						v-if="item.avatar"
						class="ss-avatar ss-user-avatar ss-menu-avatar"
						:class="`tone-${item.avatar.tone}`"
					>
						<img
							v-if="item.avatar.image && !broken.has(item.key)"
							:src="item.avatar.image"
							alt=""
							@error="broken.add(item.key)"
						/>
						<template v-else>{{ item.avatar.text }}</template>
					</span>
					<img
						v-else-if="item.image && !broken.has(item.key)"
						class="ss-menu-image"
						:src="item.image"
						alt=""
						@error="broken.add(item.key)"
					/>
					<Icon v-else-if="item.icon" :name="item.icon" :size="16" />
					<span v-if="item.sub" class="ss-menu-text ss-menu-text--two">
						<span>{{ item.label }}</span>
						<small>{{ item.sub }}</small>
					</span>
					<span v-else class="ss-menu-text">{{ item.label }}</span>
				</component>
			</div>
		</div>
	</Transition>
</template>

<script setup>
import { onBeforeUnmount, reactive, ref, watch } from "vue";
import Icon from "./Icon.vue";

const props = defineProps({
	open: Boolean,
	anchor: { type: Object, default: null },
	groups: { type: Array, required: true },
});
const emit = defineEmits(["close"]);

// ระยะจากขอบขวาของปุ่มถึงเมนู = ระยะขอบใน Dock (8px) + ระยะห่าง Dropdown ของ Frappe (4px)
const OFFSET = 12;

const panel = ref(null);
const position = ref({});
const broken = reactive(new Set());

function activate(item) {
	item.onclick?.();
	emit("close");
}

function on_pointerdown(event) {
	// ปุ่มที่เปิดเมนูสลับเปิด-ปิดเองตอนคลิก
	if (panel.value?.contains(event.target) || props.anchor?.contains(event.target)) return;
	emit("close");
}

function on_keydown(event) {
	if (event.key === "Escape") {
		emit("close");
		props.anchor?.focus({ preventScroll: true });
		return;
	}
	if (!["ArrowDown", "ArrowUp", "Home", "End"].includes(event.key) || !panel.value) return;
	event.preventDefault();
	const rows = [...panel.value.querySelectorAll(".ss-menu-item")];
	const current = rows.indexOf(document.activeElement);
	const next = {
		ArrowDown: current + 1 >= rows.length ? 0 : current + 1,
		ArrowUp: current <= 0 ? rows.length - 1 : current - 1,
		Home: 0,
		End: rows.length - 1,
	}[event.key];
	rows[next]?.focus();
}

function on_resize() {
	emit("close");
}

function unbind() {
	document.removeEventListener("pointerdown", on_pointerdown);
	document.removeEventListener("keydown", on_keydown);
	window.removeEventListener("resize", on_resize);
}

watch(
	() => props.open,
	(open) => {
		unbind();
		if (!open || !props.anchor) return;
		const rect = props.anchor.getBoundingClientRect();
		position.value = {
			left: `${rect.right + OFFSET}px`,
			bottom: `${window.innerHeight - rect.bottom}px`,
			// เมนูชิดล่างของปุ่ม รายการยาวเลื่อนในเมนู ไม่ล้นขอบจอบน
			maxHeight: `${rect.bottom - 8}px`,
		};
		document.addEventListener("pointerdown", on_pointerdown);
		document.addEventListener("keydown", on_keydown);
		window.addEventListener("resize", on_resize);
	}
);
onBeforeUnmount(unbind);
</script>
