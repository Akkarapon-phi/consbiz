<!-- หน้าแรกของแอปผู้รับเหมา: สัญญาของผู้รับเหมาที่ผู้ใช้ผูกอยู่ (contractor_app.get_home) กดแล้วดูสัญญา -->
<template>
	<div>
		<TopBar title="สัญญาของฉัน" no_project>
			<template #actions>
				<button
					type="button"
					class="ss-icon-btn"
					:class="{ 'is-spinning': loading }"
					aria-label="โหลดใหม่"
					@click="load"
				>
					<Icon name="refresh" :size="20" />
				</button>
			</template>
		</TopBar>

		<div class="ss-content">
			<Empty
				v-if="boot.link_error"
				icon="alert"
				title="ลิงก์ใช้ไม่ได้"
				:text="boot.link_error"
			/>
			<Empty
				v-else-if="!boot.suppliers?.length"
				icon="user"
				title="บัญชีนี้ยังไม่ได้ผูกกับผู้รับเหมา"
				text="ติดต่อเจ้าหน้าที่ของบริษัทให้เพิ่มบัญชีของคุณในข้อมูลผู้รับเหมา"
			/>
			<Skeleton v-else-if="data === null" :rows="3" />
			<template v-else>
				<div v-if="returned.length" class="ss-banner tone-rose">
					<Icon name="alert" :size="22" />
					<div>
						<div class="ss-banner-title">ใบเบิกถูกส่งกลับให้แก้ {{ returned.length }} ใบ</div>
						<div class="ss-banner-text">
							<a
								v-for="c in returned"
								:key="c.name"
								href="#"
								@click.prevent="go('contractor-claim', { name: c.name })"
								>งวดที่ {{ c.claim_no }} · {{ c.title }}<br
							/></a>
						</div>
					</div>
				</div>
				<Empty
					v-if="!data.agreements.length"
					icon="file"
					title="ยังไม่มีสัญญา"
					text="สัญญาจะแสดงเมื่อบริษัทอนุมัติสัญญาจ้างเหมาช่วงของคุณแล้ว"
				/>
				<div v-else class="ss-list">
					<button
						v-for="(a, i) in data.agreements"
						:key="a.name"
						type="button"
						class="ss-card ss-card--row"
						:style="{ '--i': i }"
						@click="go('contractor-agreement', { name: a.name })"
					>
						<span class="ss-avatar" :class="`tone-${a.status_tone}`"
							><Icon name="file" :size="18"
						/></span>
						<span class="ss-card-main">
							<span class="ss-card-title">{{ a.title }}</span>
							<span class="ss-card-meta"
								>{{ a.project_name }}
								<template v-if="suppliers > 1"> · {{ a.supplier_name }}</template></span
							>
							<span class="ss-progress">
								<span :style="{ width: `${Math.min(a.progress_percent || 0, 100)}%` }"></span>
								<em>เบิกแล้ว {{ num(a.progress_percent) }}%</em>
							</span>
						</span>
						<span class="ss-qty"
							><b>{{ money(a.total_amount, { short: true }) }}</b
							><small>{{ a.status_label }}</small></span
						>
					</button>
				</div>
			</template>
		</div>
	</div>
</template>

<script setup>
import { computed, ref } from "vue";
import Empty from "../../shared/components/Empty.vue";
import Icon from "../../shared/components/Icon.vue";
import Skeleton from "../../shared/components/Skeleton.vue";
import TopBar from "../../shared/components/TopBar.vue";
import { boot, go, money, num, show_error } from "../../shared/api.js";
import { capi } from "../api.js";

const data = ref(null);
const loading = ref(false);
const suppliers = (boot.suppliers || []).length;
const returned = computed(() => (data.value?.claims || []).filter((c) => c.status === "Returned"));

async function load() {
	if (!suppliers) return;
	loading.value = true;
	try {
		data.value = await capi("get_home");
	} catch (error) {
		show_error(error);
		data.value ??= { agreements: [], claims: [] };
	} finally {
		loading.value = false;
	}
}
load();
</script>
