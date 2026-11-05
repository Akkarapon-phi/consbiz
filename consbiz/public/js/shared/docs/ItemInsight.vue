<template>
	<!-- แผงขวาของฟอร์มจัดซื้อ/ขาย (จอ ≥1480): ข้อมูลประกอบของรายการที่เลือก/กำลังกรอก
	     คงเหลือ / แผนวัสดุเทียบที่ขอ-สั่ง-รับ / ราคาล่าสุด / PO ค้างรับ (site_docs.get_item_insight) -->
	<aside class="ss-insight" aria-live="polite">
		<div v-if="!row" class="ss-insight-empty">
			<Icon name="search-check" :size="26" />
			<b>ข้อมูลประกอบรายการ</b>
			<span>คลิกแถวในตารางเพื่อดูคงเหลือ แผนวัสดุ ราคาล่าสุด และใบสั่งซื้อที่ยังค้างรับ</span>
		</div>
		<template v-else>
			<header class="ss-insight-head">
				<small
					>{{ row.item_code
					}}<template v-if="info?.item_group"> · {{ info.item_group }}</template></small
				>
				<b>{{ row.item_name || row.item_code }}</b>
			</header>
			<Skeleton v-if="!info" :rows="3" />
			<template v-else>
				<section v-if="info.stock" class="ss-insight-block">
					<h3>คงเหลือ</h3>
					<div class="ss-insight-stats">
						<div v-if="info.stock.project !== null">
							<small>คลังโครงการนี้</small>
							<b>{{ num(info.stock.project) }}</b>
						</div>
						<div>
							<small>ทุกคลัง</small>
							<b>{{ num(info.stock.all) }}</b>
						</div>
					</div>
					<p class="ss-insight-unit">หน่วย {{ info.stock_uom }}</p>
				</section>

				<section v-if="info.buying" class="ss-insight-block">
					<h3>แผนวัสดุของโครงการ</h3>
					<template v-if="info.plan?.in_plan">
						<div class="ss-insight-bars">
							<div v-for="b in plan_bars" :key="b.label" class="ss-insight-bar">
								<span>{{ b.label }}</span>
								<i><b :class="b.tone" :style="{ width: `${Math.min(100, b.pct)}%` }"></b></i>
								<em>{{ num(b.value) }}</em>
							</div>
						</div>
						<p class="ss-insight-note" :class="{ 'is-warn': over_plan > 0 }">
							<Icon :name="over_plan > 0 ? 'alert' : 'info'" :size="14" />
							<template v-if="over_plan > 0">
								รวมใบนี้แล้วเกินแผน {{ num(over_plan) }} {{ info.stock_uom }}
							</template>
							<template v-else>
								ขอได้อีก {{ num(Math.max(0, info.plan.planned - info.plan.requested)) }}
								{{ info.stock_uom }}
							</template>
						</p>
					</template>
					<p v-else class="ss-insight-muted">
						{{ project ? "ไม่อยู่ในแผนวัสดุของโครงการนี้" : "ยังไม่ได้เลือกโครงการ" }}
					</p>
				</section>

				<section class="ss-insight-block">
					<h3>{{ info.buying ? "ราคาซื้อล่าสุด" : "ราคาขายล่าสุด" }}</h3>
					<ul v-if="info.prices.length" class="ss-insight-list">
						<li v-for="p in info.prices" :key="p.name + p.rate">
							<span>
								<b>{{ p.party || "–" }}</b>
								<small>{{ p.name }} · {{ thai_date(p.date, { year: true }) }}</small>
							</span>
							<span class="is-num">
								<b>{{ money(p.rate) }}</b>
								<small>/{{ p.uom }}</small>
							</span>
						</li>
					</ul>
					<p v-else class="ss-insight-muted">ยังไม่มีประวัติราคา</p>
					<p
						v-if="price_diff !== null"
						class="ss-insight-note"
						:class="{ 'is-warn': price_diff > 0 }"
					>
						<Icon :name="price_diff > 0 ? 'trending' : 'info'" :size="14" />
						ราคาในใบนี้{{
							price_diff === 0 ? "เท่ากับ" : price_diff > 0 ? "สูงกว่า" : "ต่ำกว่า"
						}}ครั้งล่าสุด
						<template v-if="price_diff !== 0">{{ Math.abs(price_diff).toFixed(1) }}%</template>
					</p>
				</section>

				<section v-if="info.open_orders" class="ss-insight-block">
					<h3>ใบสั่งซื้อค้างรับ</h3>
					<ul v-if="info.open_orders.length" class="ss-insight-list">
						<li v-for="o in info.open_orders" :key="o.name">
							<span>
								<b>{{ o.name }}</b>
								<small
									>{{ o.party
									}}<template v-if="o.due"> · ส่ง {{ thai_date(o.due) }}</template></small
								>
							</span>
							<span class="is-num">
								<b>{{ num(o.pending) }}</b>
								<small>{{ info.stock_uom }}</small>
							</span>
						</li>
					</ul>
					<p v-else class="ss-insight-muted">ไม่มีใบสั่งซื้อค้างรับ</p>
				</section>
			</template>
		</template>
	</aside>
</template>

<script setup>
import { computed, ref, watch } from "vue";
import Icon from "../components/Icon.vue";
import Skeleton from "../components/Skeleton.vue";
import { call, money, num, thai_date } from "../api.js";

const props = defineProps({ kind: String, project: String, row: Object });

const cache = new Map();
const info = ref(null);

watch(
	() => props.row?.item_code,
	async (code) => {
		if (!code) return (info.value = null);
		const key = `${props.kind}:${code}:${props.project || ""}`;
		if (cache.has(key)) return (info.value = cache.get(key));
		info.value = null;
		try {
			const data = await call("consbiz.site_docs.get_item_insight", {
				kind: props.kind,
				item_code: code,
				project: props.project || null,
			});
			cache.set(key, data);
			if (props.row?.item_code === code) info.value = data;
		} catch {
			if (props.row?.item_code === code) info.value = { prices: [], stock_uom: "" };
		}
	},
	{ immediate: true }
);

// จำนวนของแถวนี้เป็นหน่วยสต็อก (เทียบแผน) เฉพาะเมื่อหน่วยตรงกัน
const row_stock_qty = computed(() =>
	props.row && props.row.uom === info.value?.stock_uom ? Number(props.row.qty) || 0 : 0
);

const plan_bars = computed(() => {
	const p = info.value?.plan;
	if (!p) return [];
	const base = Math.max(p.planned, p.requested, 1);
	return [
		{ label: "แผน", value: p.planned, pct: (p.planned / base) * 100, tone: "is-plan" },
		{ label: "ขอแล้ว", value: p.requested, pct: (p.requested / base) * 100, tone: "" },
		{ label: "สั่งแล้ว", value: p.ordered, pct: (p.ordered / base) * 100, tone: "" },
		{ label: "รับแล้ว", value: p.received, pct: (p.received / base) * 100, tone: "is-done" },
	];
});

// ใบขอซื้อใหม่: ยอดที่ขอแล้ว + แถวนี้ เกินแผนเท่าไร (เอกสารที่บันทึกแล้วนับอยู่ในยอดขอแล้ว)
const over_plan = computed(() => {
	const p = info.value?.plan;
	if (!p || props.kind !== "mr" || props.row?.key) return 0;
	return p.requested + row_stock_qty.value - p.planned;
});

const price_diff = computed(() => {
	const last = info.value?.prices?.[0];
	const rate = Number(props.row?.rate) || 0;
	if (!last || !rate || !last.rate || last.uom !== props.row.uom) return null;
	return ((rate - last.rate) / last.rate) * 100;
});
</script>
