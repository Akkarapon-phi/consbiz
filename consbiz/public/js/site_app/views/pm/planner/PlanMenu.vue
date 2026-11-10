<!-- เมนูคลิกขวาของหน้าแก้แผน menu = { x, y, items } หรือ null, items: { label, icon, hint, disabled, danger, action } หรือ { sep: true }
     ปิดเมื่อคลิกนอกเมนู, Esc, เลื่อนจอ หรือเปลี่ยนขนาดจอ -->
<template>
	<Teleport to="#ss-layer">
		<Transition name="ss-pop-menu">
			<ul v-if="menu" ref="list" class="ss-select-menu pl-menu" role="menu" :style="position" @contextmenu.prevent>
				<template v-for="(item, i) in menu.items" :key="i">
					<li v-if="item.sep" class="pl-menu-sep" role="separator"></li>
					<li
						v-else
						role="menuitem"
						:aria-disabled="Boolean(item.disabled)"
						:class="{ 'is-disabled': item.disabled, 'is-danger': item.danger }"
						@click="run(item)"
					>
						<Icon :name="item.icon" :size="15" />
						<span class="pl-menu-label">{{ item.label }}</span>
						<small v-if="item.hint">{{ item.hint }}</small>
					</li>
				</template>
			</ul>
		</Transition>
	</Teleport>
</template>

<script setup>
import { nextTick, onBeforeUnmount, ref, watch } from "vue";
import Icon from "../../../../shared/components/Icon.vue";

const props = defineProps({ menu: { type: Object, default: null } });
const emit = defineEmits(["close"]);

const list = ref(null);
const position = ref({});
const MARGIN = 8;

function run(item) {
	if (item.disabled) return;
	emit("close");
	item.action();
}

const close = () => emit("close");
function outside(event) {
	if (!list.value?.contains(event.target)) close();
}
function on_key(event) {
	if (event.key === "Escape") close();
}
function listen(on) {
	const method = on ? "addEventListener" : "removeEventListener";
	document[method]("pointerdown", outside, true);
	document[method]("keydown", on_key);
	window[method]("scroll", close, true);
	window[method]("resize", close);
}

// เปิดที่ตำแหน่งเมาส์ แล้วขยับเข้าจอถ้าล้นขอบ
watch(
	() => props.menu,
	async (menu, previous) => {
		if (Boolean(menu) !== Boolean(previous)) listen(Boolean(menu));
		if (!menu) return;
		position.value = { left: `${menu.x}px`, top: `${menu.y}px` };
		await nextTick();
		const box = list.value?.getBoundingClientRect();
		if (!box) return;
		position.value = {
			left: `${Math.max(MARGIN, Math.min(menu.x, window.innerWidth - box.width - MARGIN))}px`,
			top: `${Math.max(MARGIN, Math.min(menu.y, window.innerHeight - box.height - MARGIN))}px`,
		};
	}
);
onBeforeUnmount(() => {
	if (props.menu) listen(false);
});
</script>
