<template>
	<div>
		<TopBar title="Dashboard บัญชี" />
		<div class="ss-content">
			<ListHead @refresh="load"><template #lead><h2 class="ss-section-title">ภาพรวมบัญชี</h2></template><template #tools><ProjectFilter /></template></ListHead>
			<Empty v-if="failed" title="โหลดภาพรวมไม่สำเร็จ" icon="alert" />
			<Skeleton v-else-if="!data" />
			<template v-for="s in data" :key="s.currency">
				<div class="summary-grid">
					<button v-for="c in cards(s)" :key="c.view" class="ss-card metric" @click="go(c.view,c.params)">
						<span class="metric-label"><Icon :name="c.icon" :size="16" />{{ c.label }}</span>
						<b>{{ c.value }} <small v-if="!c.count">{{ s.currency }}</small></b>
						<span v-if="c.note" class="ss-card-meta">{{ c.note }}</span>
					</button>
				</div>
				<Empty v-if="!cards(s).length" icon="file" title="ไม่มีข้อมูลบัญชีที่เปิดดูได้" />
				<section v-if="s.si || s.pi" class="ss-card">
					<h2 class="ss-section-title">อายุหนี้ <small>{{ s.currency }}</small></h2>
					<table class="ss-table aging"><thead><tr><th>ระยะเวลา</th><th v-if="s.si" class="is-num">ลูกหนี้</th><th v-if="s.pi" class="is-num">เจ้าหนี้</th></tr></thead>
						<tbody><tr v-for="(label,i) in buckets" :key="label"><td>{{ label }}</td><td v-if="s.si" class="is-num">{{ money(s.si.buckets[i]) }}</td><td v-if="s.pi" class="is-num">{{ money(s.pi.buckets[i]) }}</td></tr></tbody>
						<tfoot><tr><th>รวม</th><th v-if="s.si" class="is-num">{{ money(s.si.amount) }}</th><th v-if="s.pi" class="is-num">{{ money(s.pi.amount) }}</th></tr></tfoot>
					</table>
				</section>
				<div v-if="s.receipts" class="recent-grid">
					<section v-for="(label,key) in {receipts:'รับชำระล่าสุด',payments:'จ่ายชำระล่าสุด'}" :key="key" class="ss-card">
						<h2 class="ss-section-title">{{ label }}</h2>
						<table v-if="s[key].length" class="ss-table ss-table--list"><thead><tr><th>เอกสาร / คู่ค้า</th><th class="is-num">ยอด</th><th class="col-modified"></th></tr></thead>
							<tbody><tr v-for="r in s[key]" :key="r.name" tabindex="0" @click="payment(key,r)" @keydown.enter="payment(key,r)">
								<td><b>{{ r.name }}</b><small>{{ r.party_name || r.party }}</small></td>
								<td class="is-num">{{ money(r.amount) }}<small>{{ thai_date(r.posting_date,{year:true}) }}</small></td>
								<ModifiedCell :value="r.modified" :row="r" />
							</tr></tbody>
						</table>
						<Empty v-else icon="list" title="ไม่มีรายการ" />
					</section>
				</div>
			</template>
		</div>
	</div>
</template>

<script setup>
import { go, money, thai_date } from "../../../shared/api.js";
import ListHead from "../../../shared/components/ListHead.vue";
import TopBar from "../../../shared/components/TopBar.vue";
import Empty from "../../../shared/components/Empty.vue";
import Skeleton from "../../../shared/components/Skeleton.vue";
import Icon from "../../../shared/components/Icon.vue";
import ModifiedCell from "../../../shared/components/ModifiedCell.vue";
import ProjectFilter from "../../../shared/docs/ProjectFilter.vue";
import { report_scope, use_report } from "./report_data.js";
const { data, failed, load } = use_report("consbiz.account_dashboard.dashboard", report_scope);
const buckets = ["ยังไม่ถึงกำหนด", "1–30 วัน", "31–60 วัน", "61–90 วัน", "เกิน 90 วัน"];
function cards(s) {
	const rows = [];
	for (const [key,label] of [["si","ลูกหนี้คงค้าง"],["pi","เจ้าหนี้คงค้าง"]]) {
		const n = s[key];
		if (n) rows.push({label,view:"acc-"+key,icon:"file",value:money(n.amount),note:n.count+" ใบ · เกินกำหนด "+n.overdue+" ใบ",params:{filter:"todo"}});
	}
	if ("bank" in s) rows.push({label:"เงินในบัญชีธนาคาร",view:"acc-bank-accounts",icon:"building",value:money(s.bank)});
	for (const [key,label,side,icon] of [["receipts_waiting","เช็ครับรอผ่าน","in","receive"],["payments_waiting","เช็คจ่ายรอผ่าน","out","send"]]) {
		const n = s[key];
		if (n) rows.push({label,view:"acc-cheques-"+side,icon,value:money(n.amount),note:n.count+" ฉบับ",params:{tab:"waiting"}});
	}
	for (const [side,label] of [["in","เงินประกันค้างรับ"],["out","เงินประกันค้างจ่าย"]]) {
		if ("retention_"+side in s) rows.push({label,view:"acc-retention-"+side,icon:"shield",value:money(s["retention_"+side]),params:{tab:"all"}});
	}
	if ("vat" in s) rows.push({label:"ภาษีขาย − ภาษีซื้อ เดือนนี้",view:"acc-sales-tax",icon:"trending",value:money(s.vat),note:"ประมาณการภาษีมูลค่าเพิ่ม",params:{tab:"month"}});
	if ("to_issue" in s) rows.push({label:"หัก ณ ที่จ่ายรอออกหนังสือ",view:"acc-payments",icon:"file",value:s.to_issue+" ฉบับ",count:true,params:{tab:"wht"}});
	return rows;
}
const payment = (key,r) => go("acc-payment",{kind:"acc-"+key,name:r.name});
</script>
<style scoped>
.summary-grid,.recent-grid{display:grid;gap:10px;grid-template-columns:repeat(3,minmax(0,1fr))}
.recent-grid{grid-template-columns:repeat(2,minmax(0,1fr))}
.metric{display:flex;justify-content:flex-start;align-items:flex-start;flex-direction:column;gap:4px;text-align:start}
.metric-label{display:flex;align-items:center;gap:7px}
.metric b{font-size:1.35rem;font-variant-numeric:tabular-nums}
.metric small,.ss-section-title small{font-size:.72rem;color:var(--ss-muted)}
.aging{width:100%}
@media(max-width:767px){.summary-grid{grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}.recent-grid{grid-template-columns:1fr}.metric b{font-size:1.05rem}.metric-label{font-size:.85rem}.metric-label svg{flex:none}.metric{min-width:0}}
</style>
