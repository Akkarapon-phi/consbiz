<!-- รายการแบบการ์ด/แถว แบ่งหน้าในเครื่อง ความสูงคงที่ ปุ่มเลื่อนหน้าจึงไม่ขยับเมื่อหน้าสุดท้ายมีแถวน้อยกว่า
     แต่ละแถวใช้ slot เริ่มต้น (ได้ { row, index }) row_height = ความสูงต่อแถว (px) -->
<template>
	<div class="ss-paged">
		<div class="ss-paged-body" :style="body_style">
			<slot v-for="(row, index) in page_rows" :key="row[row_key]" :row="row" :index="index" />
		</div>
		<footer v-if="page_count > 1" class="ss-paged-foot">
			<span>
				<b>{{ start + 1 }}–{{ start + page_rows.length }}</b> จาก <b>{{ rows.length }}</b>
			</span>
			<div class="ss-pager">
				<button
					type="button"
					class="ss-icon-btn ss-icon-btn--sm"
					aria-label="หน้าก่อน"
					:disabled="current === 0"
					@click="page = current - 1"
				>
					<Icon name="chevron-left" :size="18" />
				</button>
				<span>{{ current + 1 }} / {{ page_count }}</span>
				<button
					type="button"
					class="ss-icon-btn ss-icon-btn--sm"
					aria-label="หน้าถัดไป"
					:disabled="current >= page_count - 1"
					@click="page = current + 1"
				>
					<Icon name="chevron-right" :size="18" />
				</button>
			</div>
		</footer>
	</div>
</template>

<script setup>
import { computed, ref } from "vue";
import Icon from "./Icon.vue";

const props = defineProps({
	rows: { type: Array, required: true },
	row_key: { type: String, required: true },
	page_size: { type: Number, required: true },
	row_height: { type: Number, required: true },
});

const GAP = 8;
const page = ref(0);
const page_count = computed(() => Math.max(1, Math.ceil(props.rows.length / props.page_size)));
// โหลดข้อมูลใหม่แล้วแถวลดลง: อยู่หน้าสุดท้ายที่ยังมีข้อมูล
const current = computed(() => Math.min(page.value, page_count.value - 1));
const start = computed(() => current.value * props.page_size);
const page_rows = computed(() => props.rows.slice(start.value, start.value + props.page_size));
const body_style = computed(() => {
	const count = Math.min(props.page_size, props.rows.length);
	return {
		gridAutoRows: `${props.row_height}px`,
		minHeight: `${count * props.row_height + (count - 1) * GAP}px`,
	};
});
</script>
