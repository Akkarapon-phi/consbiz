<!-- ค้นหาทั้งระบบ: ปุ่มค้นหาบนแถบบน หรือ Ctrl/⌘ + G (AppShell)
     ค้นเลขที่/ชื่อเรื่องของเอกสารตาม GLOBAL_SEARCH_DOCTYPES ใน site_app.py แล้วเปิดด้วย open_document()
     ↑ ↓ เลือก, Enter เปิด, Esc ปิด (ค้นหาในหน้ารายการแต่ละหน้าอยู่ในหัวรายการของหน้านั้น: ListHead) -->
<template>
	<Sheet
		:open="open"
		title="ค้นหาทั้งระบบ"
		subtitle="เลขที่เอกสารหรือชื่อเรื่อง เช่น DR-2026, ใบสั่งซื้อ, ชื่อผู้ขาย"
		half
		@close="$emit('close')"
	>
		<div class="ss-search">
			<Icon name="search" :size="18" />
			<input
				ref="input"
				v-model="txt"
				type="search"
				placeholder="พิมพ์อย่างน้อย 2 ตัวอักษร"
				enterkeyhint="search"
				@keydown.down.prevent="move(1)"
				@keydown.up.prevent="move(-1)"
				@keydown.enter.prevent="pick(flat[active])"
			/>
		</div>
		<div v-if="loading && !groups.length" class="ss-options-note"><span class="ss-spinner"></span></div>
		<div v-else-if="txt.trim().length >= 2 && !loading && !groups.length" class="ss-options-note">
			ไม่พบเอกสารที่ตรงกับ “{{ txt.trim() }}”
		</div>
		<div v-else class="ss-global-results">
			<section v-for="group in groups" :key="group.doctype">
				<div class="ss-global-group">{{ group.label }}</div>
				<button
					v-for="row in group.rows"
					:key="row.name"
					type="button"
					class="ss-option"
					:class="{ 'is-active': flat[active] === row }"
					@mouseenter="active = flat.indexOf(row)"
					@click="pick(row)"
				>
					<span class="ss-option-main">
						<span class="ss-option-label">{{ row.name }}</span>
						<span v-if="row.title || row.project" class="ss-option-desc">
							{{ [row.title, row.project].filter(Boolean).join(" · ") }}
						</span>
					</span>
					<span v-if="row.docstatus !== 1" class="ss-global-state" :class="`is-${row.docstatus}`">
						{{ row.docstatus === 2 ? "ยกเลิก" : "ร่าง" }}
					</span>
				</button>
			</section>
		</div>
	</Sheet>
</template>

<script setup>
import { computed, nextTick, ref, watch } from "vue";
import Icon from "./Icon.vue";
import Sheet from "./Sheet.vue";
import { call } from "../api.js";
import { open_document } from "../notifications.js";

const props = defineProps({ open: Boolean });
const emit = defineEmits(["close"]);

const input = ref(null);
const txt = ref("");
const groups = ref([]);
const loading = ref(false);
const active = ref(0);

// ผลลัพธ์ทุกกลุ่มเรียงเป็นแถวเดียว ให้ลูกศรขึ้น-ลงข้ามกลุ่มได้
const flat = computed(() =>
	groups.value.flatMap((group) => group.rows.map((row) => Object.assign(row, { doctype: group.doctype })))
);

watch(
	() => props.open,
	async (open) => {
		if (!open) return;
		await nextTick();
		input.value?.focus();
		input.value?.select();
	}
);

let timer = null;
let seq = 0;
watch(txt, (value) => {
	clearTimeout(timer);
	const q = value.trim();
	if (q.length < 2) {
		groups.value = [];
		loading.value = false;
		return;
	}
	loading.value = true;
	timer = setTimeout(async () => {
		const mine = ++seq;
		try {
			const result = await call("consbiz.site_app.global_search", { txt: q });
			if (mine !== seq) return; // พิมพ์ต่อแล้ว ทิ้งผลเก่า
			groups.value = result || [];
			active.value = 0;
		} catch {
			if (mine === seq) groups.value = [];
		} finally {
			if (mine === seq) loading.value = false;
		}
	}, 250);
});

function move(step) {
	const count = flat.value.length;
	if (!count) return;
	active.value = (active.value + step + count) % count;
	nextTick(() => document.querySelector(".ss-global-results .is-active")?.scrollIntoView({ block: "nearest" }));
}

function pick(row) {
	if (!row) return;
	emit("close");
	open_document(row.doctype, row.name);
}
</script>
