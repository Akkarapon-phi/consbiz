<template>
	<div><TopBar title="บัญชีแยกประเภท" back_to="acc-general-ledger" />
		<div class="ss-content">
			<ListHead @refresh="load">
				<template #lead><h2 class="ss-section-title">{{ account }}</h2></template>
				<template #tools><a v-if="data" class="ss-btn ss-btn--soft" :href="excel"><Icon name="file" :size="16" /> Excel</a></template>
				<template #filters>
					<DateInput v-model="from" variant="tool" label="ตั้งแต่วันที่" /><span>ถึง</span><DateInput v-model="to" variant="tool" label="ถึงวันที่" />
					<SelectBox :model-value="period" :options="presets" variant="tool" label="ช่วงเวลา" @update:model-value="preset" />
					<ProjectFilter /><input v-model.lazy.trim="party" class="ss-tool party-input" type="search" aria-label="กรองคู่ค้า" placeholder="ชื่อหรือรหัสคู่ค้า" />
				</template>
			</ListHead>
			<ListCard :on="wide">
				<Empty v-if="from>to" title="วันที่สิ้นสุดต้องไม่ก่อนวันที่เริ่ม" icon="calendar" />
				<Empty v-else-if="failed" title="โหลดรายการบัญชีไม่สำเร็จ" icon="alert" /><Skeleton v-else-if="!data" />
				<template v-else>
					<div v-if="wide" class="ss-table-wrap"><table class="ss-table ss-table--list"><thead><tr>
						<th>วันที่</th><th>เอกสาร</th><th>คู่ค้า / หมายเหตุ</th><th class="is-num">เดบิต</th><th class="is-num">เครดิต</th><th class="is-num">คงเหลือ</th><th class="col-modified"></th>
					</tr></thead><tbody>
						<tr class="is-static"><td colspan="5">ยอดยกมา · {{ date(from) }}</td><td class="is-num"><b>{{ money(data.opening) }}</b></td><td></td></tr>
						<tr v-for="r in data.rows" :key="r.name" class="is-static">
							<td class="col-nowrap">{{ date(r.posting_date) }}</td>
							<td class="col-nowrap"><button v-if="linked(r)" class="ss-link" @click="open(r)">{{ r.voucher_no }}</button><b v-else>{{ r.voucher_no }}</b><small>{{ r.voucher_type }}</small></td>
							<td class="party-cell">{{ r.party || '—' }}<small class="remark" :title="r.remarks">{{ r.remarks }}</small></td>
							<td class="is-num">{{ money(r.debit) }}</td><td class="is-num">{{ money(r.credit) }}</td><td class="is-num"><b>{{ money(r.balance) }}</b></td><ModifiedCell :value="r.modified" :row="r" />
						</tr>
					</tbody></table></div>
					<div v-else class="ss-list">
						<div class="ss-card ss-card-head"><span>ยอดยกมา · {{ date(from) }}</span><b>{{ money(data.opening) }}</b></div>
						<div v-for="r in data.rows" :key="r.name" class="ss-card">
							<div class="ss-card-head"><button v-if="linked(r)" class="ss-link" @click="open(r)">{{ r.voucher_no }}</button><b v-else>{{ r.voucher_no }}</b><small>{{ date(r.posting_date) }}</small></div>
							<small class="ss-card-meta">{{ r.voucher_type }} · {{ r.party || '—' }}</small><small class="remark" :title="r.remarks">{{ r.remarks }}</small>
							<div class="ss-chips"><span class="ss-chip">เดบิต {{ money(r.debit) }}</span><span class="ss-chip">เครดิต {{ money(r.credit) }}</span></div>
							<div class="ss-card-head"><span>คงเหลือ</span><b>{{ money(r.balance) }}</b></div>
						</div>
					</div>
					<Empty v-if="!data.rows.length" title="ไม่มีรายการในช่วงนี้" icon="list" />
					<button v-if="data.has_more" class="ss-btn ss-btn--soft" :disabled="busy" @click="load(true)">โหลดเพิ่ม</button>
					<footer class="ss-list-foot">ยอดปลายงวด · {{ date(to) }}<span class="ss-toolbar-gap"></span><b>{{ money(data.closing) }}</b></footer>
				</template>
			</ListCard>
		</div>
	</div>
</template>
<script setup>
import {computed, ref, watch} from "vue";
import {call,go,iso_date,money,show_error,state,thai_date} from "../../../shared/api.js";
import {use_wide} from "../../../shared/table.js";
import TopBar from "../../../shared/components/TopBar.vue";
import ListHead from "../../../shared/components/ListHead.vue";
import ListCard from "../../../shared/components/ListCard.vue";
import ModifiedCell from "../../../shared/components/ModifiedCell.vue";
import DateInput from "../../../shared/components/DateInput.vue";
import SelectBox from "../../../shared/components/SelectBox.vue";
import Empty from "../../../shared/components/Empty.vue";
import Skeleton from "../../../shared/components/Skeleton.vue";
import Icon from "../../../shared/components/Icon.vue";
import ProjectFilter from "../../../shared/docs/ProjectFilter.vue";
import {report_scope} from "./report_data.js";

const wide=use_wide();
const account=state.route.params.name;
const now=new Date(), year=now.getFullYear(), m=now.getMonth();
const month_range=[iso_date(new Date(year,m,1)), iso_date(new Date(year,m+1,0))];
const quarter=Math.floor(m/3)*3;
const quarter_range=[iso_date(new Date(year,quarter,1)),iso_date(new Date(year,quarter+3,0))];
const from=ref(month_range[0]), to=ref(month_range[1]), party=ref("");
const data=ref(null), failed=ref(false), busy=ref(false), fiscal=ref(null);
const presets=computed(()=>[{value:"month",label:"เดือนนี้"},{value:"quarter",label:"ไตรมาสนี้"},...(fiscal.value?[{value:"year",label:"ปีบัญชี"}]:[]),{value:"custom",label:"กำหนดเอง"}]);
const ranges=computed(()=>({month:month_range,quarter:quarter_range,year:fiscal.value}));
const period=computed(()=>Object.keys(ranges.value).find(k=>ranges.value[k]?.[0]===from.value && ranges.value[k]?.[1]===to.value)||"custom");
function preset(key) {if(ranges.value[key]) [from.value,to.value]=ranges.value[key];}
const args=computed(()=>({...report_scope(), account,from_date:from.value,to_date:to.value,...(party.value?{party:party.value}:{})}));
const excel=computed(()=>"/api/method/consbiz.account_ledger.export_ledger?"+new URLSearchParams(args.value));
const date=d=>thai_date(d,{year:true});
const linked=r=>r.payment_view || r.invoice_kind || r.voucher_type==="Journal Entry";
function open(r) {
	if(r.payment_view) go("acc-payment",{kind:r.payment_view,name:r.voucher_no});
	else if(r.invoice_kind) go("acc-invoice-doc",{kind:r.invoice_kind,name:r.voucher_no});
	else window.open("/app/journal-entry/"+encodeURIComponent(r.voucher_no),"_blank","noopener");
}
let latest=0;
async function load(more=false) {
	const id=++latest;
	const previous=more===true ? data.value?.rows || [] : [];
	if(!previous.length) data.value=null;
	failed.value=false;
	if(from.value>to.value) return;
	busy.value=true;
	try {
		const result=await call("consbiz.account_ledger.ledger",{...args.value,offset:previous.length});
		if(id!==latest) return;
		let balance=previous.at(-1)?.balance ?? result.opening;
		for(const r of result.rows) {balance+=r.debit-r.credit; r.balance=balance;}
		data.value={...result,rows:[...previous,...result.rows]};
		fiscal.value=result.fiscal_year;
	} catch(e) {if(id===latest){failed.value=!previous.length;show_error(e);}}
	finally {if(id===latest) busy.value=false;}
}
watch(()=>JSON.stringify(args.value),()=>load(),{immediate:true});
</script>
<style scoped>
.party-input{width:145px;min-width:0}
.party-cell{width:100%}.remark{display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
td .remark{width:0;min-width:100%}
</style>
