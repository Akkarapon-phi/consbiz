<!-- ปุ่มแจ้งเตือนบนแถบบน: จำนวนที่ยังไม่อ่าน + รายการล่าสุด (shared/notifications.js)
     กดรายการ = อ่านแล้วเปิดเอกสาร (open_document: มีหน้าในแอปเปิดในแอป ที่เหลือเปิดระบบเต็ม) -->
<template>
	<button
		ref="button"
		type="button"
		class="ss-icon-btn ss-bell"
		:class="{ 'is-on': open }"
		aria-label="การแจ้งเตือน"
		title="การแจ้งเตือน"
		aria-haspopup="dialog"
		:aria-expanded="open"
		@click="toggle"
	>
		<Icon name="bell" :size="18" />
		<span v-if="unread" class="ss-bell-count">{{ unread > 9 ? "9+" : unread }}</span>
	</button>
	<Teleport to="body">
		<Transition name="ss-pop-menu">
			<div v-if="open" ref="panel" class="ss-bell-pop" role="dialog" aria-label="การแจ้งเตือน" :style="position">
				<div class="ss-bell-head">
					<b>การแจ้งเตือน</b>
					<button v-if="unread" type="button" @click="mark_all_read">อ่านทั้งหมด</button>
				</div>
				<ul v-if="notifications.items.length" class="ss-bell-list">
					<li v-for="item in notifications.items" :key="item.name">
						<button type="button" class="ss-bell-item" :class="{ 'is-unread': !item.read }" @click="open_item(item)">
							<span class="ss-bell-dot"></span>
							<span class="ss-bell-text">
								<span>{{ strip_html(item.subject) }}</span>
								<small>{{ time_ago(item.creation) }}</small>
							</span>
						</button>
					</li>
				</ul>
				<div v-else class="ss-bell-empty">{{ notifications.loaded ? "ไม่มีการแจ้งเตือน" : "กำลังโหลด..." }}</div>
			</div>
		</Transition>
	</Teleport>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import Icon from "./Icon.vue";
import { strip_html, time_ago } from "../api.js";
import {
	mark_all_read,
	mark_read,
	notifications,
	open_document,
	refresh_notifications,
	start_notifications,
} from "../notifications.js";

const button = ref(null);
const panel = ref(null);
const open = ref(false);
const position = ref({});
const unread = computed(() => notifications.items.filter((item) => !item.read).length);

function toggle() {
	if (open.value) {
		open.value = false;
		return;
	}
	const rect = button.value.getBoundingClientRect();
	// กว้างตาม .ss-bell-pop: ชิดขวาตามปุ่ม แต่ไม่ล้นจอด้านซ้าย (มีปุ่มของหน้าอยู่ขวาของกระดิ่ง)
	const width = Math.min(340, window.innerWidth - 16);
	const right = Math.min(window.innerWidth - rect.right, window.innerWidth - width - 8);
	position.value = { top: `${rect.bottom + 8}px`, right: `${Math.max(8, right)}px` };
	open.value = true;
	refresh_notifications();
}

function open_item(item) {
	mark_read(item);
	open.value = false;
	if (item.link) {
		window.open(item.link, "_blank", "noopener");
		return;
	}
	if (item.document_type && item.document_name) open_document(item.document_type, item.document_name);
}

function on_outside(event) {
	if (!open.value || panel.value?.contains(event.target) || button.value?.contains(event.target)) return;
	open.value = false;
}
function on_key(event) {
	if (event.key === "Escape") open.value = false;
}

onMounted(() => {
	start_notifications();
	document.addEventListener("pointerdown", on_outside, true);
	document.addEventListener("keydown", on_key);
});
onBeforeUnmount(() => {
	document.removeEventListener("pointerdown", on_outside, true);
	document.removeEventListener("keydown", on_key);
});
</script>
