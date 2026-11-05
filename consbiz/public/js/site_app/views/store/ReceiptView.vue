<template>
	<div>
		<TopBar
			:title="data?.party || 'ใบรับของ'"
			:subtitle="params.name"
			back_to="receive"
			:back_params="{ tab: 'done' }"
		>
			<template #actions>
				<a
					v-if="boot.desk"
					class="ss-icon-btn"
					:href="desk_url(params.doctype, params.name)"
					aria-label="เปิดในระบบ"
				>
					<Icon name="external" :size="20" />
				</a>
			</template>
		</TopBar>

		<div class="ss-content">
			<Skeleton v-if="!data" :rows="3" />
			<template v-else>
				<div class="ss-receipt-hero">
					<div class="ss-receipt-stamp"><Icon name="check" :size="28" :stroke="3" /></div>
					<div class="ss-receipt-title">รับเข้าคลังแล้ว</div>
					<div class="ss-receipt-sub">
						{{ thai_date(data.date, { year: true }) }} · {{ short_time(data.time) }} น. ·
						{{ data.owner }}
					</div>
				</div>

				<div class="ss-facts">
					<div v-if="data.source" class="ss-fact">
						<span>อ้างอิง</span><b>{{ data.source }}</b>
					</div>
					<div v-if="data.delivery_note" class="ss-fact">
						<span>ใบส่งของ</span><b>{{ data.delivery_note }}</b>
					</div>
					<div v-if="data.delivered_by" class="ss-fact">
						<span>ผู้ส่ง</span><b>{{ data.delivered_by }}</b>
					</div>
					<div v-if="data.vehicle_no" class="ss-fact">
						<span>ทะเบียนรถ</span><b>{{ data.vehicle_no }}</b>
					</div>
				</div>

				<h2 class="ss-section-title">รายการ ({{ data.items.length }})</h2>
				<div class="ss-list">
					<div
						v-for="(row, i) in data.items"
						:key="i"
						class="ss-card ss-card--row"
						:style="{ '--i': i }"
					>
						<span class="ss-thumb">
							<img v-if="row.image" :src="row.image" alt="" loading="lazy" />
							<Icon v-else name="package" :size="22" />
						</span>
						<span class="ss-card-main">
							<span class="ss-card-title">{{ row.item_name }}</span>
							<span v-if="row.rejected_qty" class="ss-card-meta ss-text-danger">
								ตีกลับ {{ num(row.rejected_qty) }} {{ row.uom
								}}<template v-if="row.reason"> · {{ row.reason }}</template>
							</span>
						</span>
						<span class="ss-qty"
							><b>{{ num(row.qty) }}</b
							><small>{{ row.uom }}</small></span
						>
					</div>
				</div>

				<template v-if="data.remarks">
					<h2 class="ss-section-title">หมายเหตุ</h2>
					<div class="ss-card ss-pre">{{ data.remarks }}</div>
				</template>

				<template v-if="data.files.length">
					<h2 class="ss-section-title">รูปถ่าย</h2>
					<div class="ss-gallery">
						<a
							v-for="f in data.files"
							:key="f.file_url"
							:href="f.file_url"
							target="_blank"
							rel="noopener"
						>
							<img :src="f.file_url" :alt="f.file_name" loading="lazy" />
						</a>
					</div>
				</template>
			</template>
		</div>
	</div>
</template>

<script setup>
import { ref } from "vue";
import Icon from "../../../shared/components/Icon.vue";
import TopBar from "../../../shared/components/TopBar.vue";
import Skeleton from "../../../shared/components/Skeleton.vue";
import {
	back,
	boot,
	call,
	desk_url,
	num,
	short_time,
	show_error,
	state,
	thai_date,
} from "../../../shared/api.js";

const params = state.route.params;
const data = ref(null);

call("get_receipt", { doctype: params.doctype, name: params.name })
	.then((value) => (data.value = value))
	.catch((error) => {
		show_error(error);
		back("receive");
	});
</script>
