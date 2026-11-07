<!-- ตัวอย่างเอกสารข้างตารางรายการ (จอ ≥1480, DocList.vue) ดูได้โดยไม่เปลี่ยนหน้า
     ข้อมูลเดียวกับหน้าดู (site_docs.get_doc) แบบย่อ + ปุ่ม PDF / แก้ไข / ส่ง / สร้างเอกสารถัดไป / เปิดเต็มหน้า -->
<template>
	<aside class="ss-preview" :aria-label="`ตัวอย่าง ${name}`">
		<header class="ss-preview-head">
			<div class="ss-preview-title">
				<b>{{ name }}</b>
				<span v-if="doc" class="ss-tag" :class="`tone-${doc.status_tone}`">{{ doc.status_label }}</span>
			</div>
			<button
				type="button"
				class="ss-icon-btn ss-icon-btn--sm"
				aria-label="ปิดตัวอย่าง"
				@click="$emit('close')"
			>
				<Icon name="x" :size="17" />
			</button>
		</header>

		<Skeleton v-if="!doc" :rows="3" />
		<div v-else class="ss-preview-body">
			<div class="ss-preview-party">
				<b>{{ doc.party || doc.title || doc.name }}</b>
			</div>

			<ol class="ss-preview-steps">
				<li v-for="(st, i) in doc.steps" :key="i" :class="`is-${st.state}`" :title="st.label">
					<i></i>
					<span
						>{{ st.label
						}}<template v-if="st.note && st.state === 'current'"> {{ st.note }}</template></span
					>
				</li>
			</ol>

			<!-- แถวบน 3 ช่อง: วัตถุประสงค์ | วันที่ | วันที่ต้องการ, แถวล่าง 2 ช่อง: ผู้จัดทำ | ผู้อนุมัติ -->
			<dl class="ss-preview-facts">
				<div v-if="doc.purpose">
					<dt>วัตถุประสงค์</dt>
					<dd>{{ doc.purpose }}</dd>
				</div>
				<div>
					<dt>วันที่</dt>
					<dd>{{ thai_date(doc.date, { year: true }) }}</dd>
				</div>
				<div v-if="doc.due">
					<dt>{{ config.due || "วันที่ต้องการ" }}</dt>
					<dd>{{ thai_date(doc.due, { year: true }) }}</dd>
				</div>
				<div class="is-person">
					<dt>ผู้จัดทำ</dt>
					<dd>{{ doc.request_by || doc.owner_name }}</dd>
				</div>
				<div v-if="doc.approve_by" class="is-person">
					<dt>ผู้อนุมัติ</dt>
					<dd>{{ doc.approve_by }}</dd>
				</div>
			</dl>

			<section>
				<h3 class="ss-preview-h">
					รายการ <span class="ss-count">{{ doc.items.length }}</span>
				</h3>
				<ul class="ss-preview-items">
					<li v-for="(it, i) in doc.items.slice(0, SHOW)" :key="i">
						<span class="ss-preview-item">
							<b>{{ it.item_name || it.item_code }}</b>
							<small
								>{{ it.item_code }} · {{ num(it.qty) }} {{ it.uom }} ×
								{{ money(it.rate) }}</small
							>
						</span>
						<b class="is-num">{{ money(it.amount) }}</b>
					</li>
				</ul>
				<button v-if="doc.items.length > SHOW" type="button" class="ss-link" @click="open_full">
					ดูอีก {{ doc.items.length - SHOW }} รายการ
				</button>
			</section>

			<!-- ยอดสำคัญเท่านั้น (รายละเอียดภาษี/ยอดหักดูในหน้าเต็ม) แผงต้องพอดีจอโดยไม่เลื่อน -->
			<div class="ss-totals ss-preview-totals">
				<div class="is-grand">
					<span>{{ doc.summary.grand_label }}</span
					><b>{{ money(doc.summary.grand) }}</b>
				</div>
				<div v-if="doc.summary.net !== undefined" class="is-net">
					<span>{{ doc.summary.net_label }}</span
					><b>{{ money(doc.summary.net) }}</b>
				</div>
				<div v-if="doc.totals.outstanding_amount" class="is-due">
					<span>ค้าง{{ config.section === "buy" ? "จ่าย" : "รับ" }}</span
					><b>{{ money(doc.totals.outstanding_amount) }}</b>
				</div>
			</div>
		</div>

		<footer v-if="doc" class="ss-preview-foot">
			<template v-if="confirm">
				<span class="ss-preview-confirm">ส่งแล้วแก้ไขไม่ได้ ยืนยัน?</span>
				<button type="button" class="ss-btn ss-btn--ghost ss-btn--sm" @click="confirm = false">
					ยกเลิก
				</button>
				<button
					type="button"
					class="ss-btn ss-btn--primary ss-btn--sm"
					:disabled="busy"
					@click="submit"
				>
					<span v-if="busy" class="ss-spinner"></span>
					<template v-else>ยืนยันส่ง</template>
				</button>
			</template>
			<template v-else>
				<button
					type="button"
					class="ss-icon-btn"
					title="เปิดเต็มหน้า"
					aria-label="เปิดเต็มหน้า"
					@click="open_full"
				>
					<Icon name="maximize" :size="17" />
				</button>
				<button
					type="button"
					class="ss-icon-btn"
					title="PDF / พิมพ์"
					aria-label="PDF / พิมพ์"
					@click="pdf = true"
				>
					<Icon name="printer" :size="18" />
				</button>
				<a
					class="ss-icon-btn"
					:href="desk_url(config.doctype, name)"
					title="เปิดในระบบเต็ม"
					aria-label="เปิดในระบบเต็ม"
				>
					<Icon name="external" :size="18" />
				</a>
				<span class="ss-toolbar-gap"></span>
				<button
					v-if="doc.can_edit"
					type="button"
					class="ss-btn ss-btn--ghost ss-btn--sm"
					@click="go(`${config.section}-form`, { kind, name })"
				>
					<Icon name="pen" :size="15" /> แก้ไข
				</button>
				<button
					v-if="doc.can_submit"
					type="button"
					class="ss-btn ss-btn--primary ss-btn--sm"
					@click="confirm = true"
				>
					ส่ง{{ config.label }}
				</button>
				<button
					v-else-if="doc.next_kind && in_app(doc.next_kind)"
					type="button"
					class="ss-btn ss-btn--primary ss-btn--sm"
					@click="go(`${config.section}-form`, { kind: doc.next_kind, name: 'new', source: name })"
				>
					<Icon name="plus" :size="15" :stroke="2.6" /> สร้าง{{ DOC_KINDS[doc.next_kind].label }}
				</button>
			</template>
		</footer>

		<PdfViewer :open="pdf" :url="doc?.pdf_url" :name="name" :title="config.label" @close="pdf = false" />
	</aside>
</template>

<script setup>
import { computed, ref, watch } from "vue";
import Icon from "../components/Icon.vue";
import Skeleton from "../components/Skeleton.vue";
import PdfViewer from "../components/PdfViewer.vue";
import { DOC_KINDS, in_app } from "./kinds.js";
import { call, celebrate, desk_url, go, money, num, post, show_error, thai_date } from "../api.js";

const props = defineProps({ kind: String, name: String });
// แสดงรายการแค่ 3 แถวแรก (แผงต้องพอดีจอโน้ตบุ๊กโดยไม่ต้องเลื่อน) ที่เหลือดูในหน้าเต็ม
const SHOW = 3;
const emit = defineEmits(["close", "changed"]);

const config = computed(() => DOC_KINDS[props.kind]);
const doc = ref(null);
const pdf = ref(false);
const confirm = ref(false);
const busy = ref(false);
let request = 0;

async function load() {
	const id = ++request;
	doc.value = null;
	confirm.value = false;
	try {
		const data = await call("consbiz.site_docs.get_doc", { kind: props.kind, name: props.name });
		if (id === request) doc.value = data;
	} catch (error) {
		if (id === request) show_error(error);
	}
}

const open_full = () => go(`${config.value.section}-doc`, { kind: props.kind, name: props.name });

async function submit() {
	busy.value = true;
	try {
		await post("consbiz.site_docs.submit_doc", { kind: props.kind, name: props.name });
		await celebrate(`ส่ง${config.value.label}แล้ว`, props.name);
		emit("changed");
		await load();
	} catch (error) {
		show_error(error);
	} finally {
		busy.value = false;
	}
}

watch(() => props.name, load, { immediate: true });
</script>
