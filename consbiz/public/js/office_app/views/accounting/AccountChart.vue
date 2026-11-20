<template>
	<div><TopBar title="บัญชีแยกประเภท" />
		<div class="ss-content">
			<ListHead v-if="wide" v-model:search="search" search_placeholder="ค้นหาเลขที่หรือชื่อบัญชี" @refresh="load">
				<template #lead><h2 class="ss-section-title">ผังบัญชี</h2></template>
				<template #filters><label class="ss-tool"><input v-model="hide_zero" type="checkbox" /> ซ่อนบัญชียอดศูนย์</label><ProjectFilter /></template>
			</ListHead>
			<template v-else>
				<label class="ss-search"><Icon name="search" :size="16" /><input v-model="search" type="search" placeholder="ค้นหาเลขที่หรือชื่อบัญชี" /></label>
				<div class="chart-filters"><label class="ss-tool"><input v-model="hide_zero" type="checkbox" /> ซ่อนบัญชียอดศูนย์</label><ProjectFilter /></div>
			</template>
			<ListCard :on="wide">
				<Empty v-if="failed" icon="alert" title="โหลดผังบัญชีไม่สำเร็จ" /><Skeleton v-else-if="!data" />
				<Empty v-else-if="!rows.length" icon="list" title="ไม่พบบัญชี" />
				<div v-else-if="wide" class="ss-table-wrap"><table class="ss-table ss-table--list">
					<thead><tr><th>เลขที่ / ชื่อบัญชี</th><th>ประเภท</th><th class="is-num">คงเหลือ ณ วันนี้</th><th class="col-modified"></th></tr></thead>
					<tbody><template v-for="(r,i) in rows" :key="r.name">
						<tr v-if="!i || rows[i-1].company !== r.company" class="is-static"><th colspan="4">{{ r.company }}</th></tr>
						<tr :class="{'is-static':r.is_group}" :tabindex="r.is_group ? undefined : 0" @click="open(r)" @keydown.enter="open(r)">
							<td><span class="tree-label" :style="indent(r)"><Icon :name="r.is_group ? 'layers':'file'" :size="15" /><component :is="r.is_group?'b':'span'">{{ label(r) }}</component></span></td>
							<td>{{ roots[r.root_type] }}</td><td class="is-num">{{ money(r.balance) }}</td><ModifiedCell :value="r.modified" :row="r" />
						</tr>
					</template></tbody></table></div>
				<div v-else class="ss-list"><template v-for="(r,i) in rows" :key="r.name">
					<h3 v-if="!i || rows[i-1].company !== r.company" class="ss-section-title">{{ r.company }}</h3>
					<component :is="r.is_group?'div':'button'" class="ss-card chart-card" :style="indent(r)" @click="open(r)">
						<div class="tree-label"><Icon :name="r.is_group?'layers':'file'" :size="15" /><b>{{ label(r) }}</b></div>
						<div class="ss-card-head"><small>{{ roots[r.root_type] }}</small><b>{{ money(r.balance) }}</b></div>
					</component>
				</template></div>
			</ListCard>
		</div>
	</div>
</template>
<script setup>
import { computed, ref } from "vue";
import { go, money } from "../../../shared/api.js";
import { matches,use_wide } from "../../../shared/table.js";
import ListHead from "../../../shared/components/ListHead.vue";
import ListCard from "../../../shared/components/ListCard.vue";
import TopBar from "../../../shared/components/TopBar.vue";
import Empty from "../../../shared/components/Empty.vue";
import Skeleton from "../../../shared/components/Skeleton.vue";
import ModifiedCell from "../../../shared/components/ModifiedCell.vue";
import Icon from "../../../shared/components/Icon.vue";
import ProjectFilter from "../../../shared/docs/ProjectFilter.vue";
import { report_scope, use_report } from "./report_data.js";
const wide=use_wide(), search=ref(""), hide_zero=ref(false);
const {data,failed,load}=use_report("consbiz.account_ledger.chart",report_scope);
const roots={Asset:"สินทรัพย์",Liability:"หนี้สิน",Equity:"ส่วนของเจ้าของ",Income:"รายได้",Expense:"ค่าใช้จ่าย"};
const rows=computed(()=>(data.value||[]).filter(r=>(!hide_zero.value || Math.abs(r.balance)>=0.005) && matches(search.value,r.account_number,r.account_name,r.company)));
const label=r=>[r.account_number,r.account_name].filter(Boolean).join(" · ");
const indent=r=>({"--depth":r.depth});
const open=r=>{if(!r.is_group) go("acc-ledger-account",{name:r.name});};
</script>
<style scoped>
.chart-filters{display:flex;flex-wrap:wrap;gap:6px}
.tree-label{display:flex;align-items:center;gap:8px;padding-inline-start:calc(var(--depth,0) * 14px)}
.chart-card{--ind:calc(min(var(--depth), 5) * 5px);margin-inline-start:var(--ind);width:calc(100% - var(--ind));box-sizing:border-box;text-align:start}.chart-card .tree-label{padding:0}
</style>
