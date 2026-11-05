<template>
	<div :class="{ 'ss-has-bar': tab === 'new' && cart.length }">
		<TopBar title="เบิกวัสดุ" :subtitle="state.project?.project_name">
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
			<Segmented
				v-model="tab"
				:options="[
					{ value: 'new', label: 'เบิกใหม่' },
					{ value: 'history', label: 'ประวัติการเบิก' },
				]"
			/>

			<Transition name="ss-fade" mode="out-in">
				<div v-if="tab === 'new'" key="new">
					<div class="ss-search ss-search--sticky">
						<Icon name="search" :size="18" />
						<input v-model="txt" type="search" placeholder="ค้นหาวัสดุในคลัง" />
						<button v-if="txt" type="button" class="ss-search-clear" @click="txt = ''">
							<Icon name="x" :size="16" />
						</button>
					</div>
					<Skeleton v-if="stock === null" />
					<Empty
						v-else-if="!available.length"
						icon="warehouse"
						:title="txt ? 'ไม่พบวัสดุ' : 'คลังว่าง'"
						:text="txt ? 'ลองค้นด้วยคำอื่น' : 'ยังไม่มีวัสดุคงเหลือในคลังของโครงการ'"
					/>
					<div v-else class="ss-list">
						<button
							v-for="(item, i) in available.slice(0, limit)"
							:key="item.item_code"
							type="button"
							class="ss-card ss-card--row"
							:class="{ 'is-in-cart': in_cart(item) }"
							:style="{ '--i': Math.min(i, 12) }"
							@click="pick(item)"
						>
							<span class="ss-thumb">
								<img v-if="item.image" :src="item.image" alt="" loading="lazy" />
								<Icon v-else name="package" :size="22" />
							</span>
							<span class="ss-card-main">
								<span class="ss-card-title">{{ item.item_name }}</span>
								<span class="ss-card-meta">
									<span v-if="item.employer" class="ss-tag tone-violet"
										>ผู้ว่าจ้าง {{ num(item.employer) }}</span
									>
									{{ item.item_code }}
								</span>
							</span>
							<span class="ss-qty">
								<b>{{ num(item.balance) }}</b
								><small>{{ item.uom }}</small>
							</span>
							<Transition name="ss-pop">
								<span v-if="in_cart(item)" class="ss-in-cart">{{
									num(in_cart(item).qty)
								}}</span>
							</Transition>
						</button>
						<button
							v-if="available.length > limit"
							type="button"
							class="ss-btn ss-btn--ghost ss-btn--block"
							@click="limit += 50"
						>
							แสดงเพิ่ม ({{ available.length - limit }})
						</button>
					</div>
				</div>

				<div v-else key="history">
					<Skeleton v-if="history_rows === null" />
					<Empty
						v-else-if="!history_rows.length"
						icon="history"
						title="ยังไม่มีการเบิก"
						text="ใบเบิก 90 วันล่าสุดจะแสดงที่นี่"
					/>
					<template v-else>
						<template v-for="group in history_groups" :key="group.date">
							<div class="ss-day">{{ relative_date(group.date) }}</div>
							<div class="ss-list">
								<div
									v-for="(d, i) in group.rows"
									:key="d.name"
									class="ss-card"
									:style="{ '--i': i }"
								>
									<div class="ss-card-head">
										<span class="ss-avatar tone-teal"
											><Icon name="issue" :size="18"
										/></span>
										<span class="ss-card-main">
											<span class="ss-card-title">{{ issuer(d) }}</span>
											<span class="ss-card-meta">{{ d.name }} · {{ d.owner }}</span>
										</span>
										<span class="ss-time">{{ short_time(d.time) }}</span>
									</div>
									<div class="ss-lines">
										<div v-for="(r, j) in d.items" :key="j" class="ss-line">
											<span
												>{{ r.item_name
												}}<em v-if="r.wbs" class="ss-wbs">{{ r.wbs }}</em></span
											>
											<b
												>{{ num(r.qty) }} <small>{{ r.uom }}</small></b
											>
										</div>
									</div>
								</div>
							</div>
						</template>
					</template>
				</div>
			</Transition>
		</div>

		<Teleport to="#ss-layer">
			<Transition name="ss-bar">
				<div v-if="tab === 'new' && cart.length" class="ss-bottom-bar">
					<button type="button" class="ss-cart-summary" @click="cart_open = true">
						<span class="ss-cart-icon"
							><Icon name="cart" :size="20" /><span class="ss-badge">{{
								cart.length
							}}</span></span
						>
						<span>รายการเบิก</span>
						<Icon name="chevron-down" :size="18" style="transform: rotate(180deg)" />
					</button>
					<button type="button" class="ss-btn ss-btn--primary ss-btn--lg" @click="cart_open = true">
						ตรวจและเบิก
					</button>
				</div>
			</Transition>
		</Teleport>

		<!-- ใส่จำนวน -->
		<Sheet
			:open="!!editing"
			:title="editing?.item_name"
			:subtitle="editing && `คงเหลือ ${num(editing.balance)} ${editing.uom}`"
			@close="editing = null"
		>
			<div v-if="editing" class="ss-qty-sheet">
				<Stepper v-model="edit_qty" :max="editing.balance" :min="0" class="ss-stepper--xl" />
				<div class="ss-quick">
					<button
						v-for="q in quick_qty"
						:key="q"
						type="button"
						class="ss-reason"
						@click="edit_qty = Math.min(q, editing.balance)"
					>
						{{ num(q) }}
					</button>
					<button type="button" class="ss-reason" @click="edit_qty = editing.balance">
						ทั้งหมด
					</button>
				</div>
			</div>
			<template #footer>
				<div class="ss-sheet-actions">
					<button
						v-if="in_cart(editing)"
						type="button"
						class="ss-btn ss-btn--ghost-danger"
						@click="remove(editing)"
					>
						<Icon name="trash" :size="18" />
					</button>
					<button
						type="button"
						class="ss-btn ss-btn--primary ss-btn--block ss-btn--lg"
						:disabled="!edit_qty"
						@click="save_line"
					>
						{{ in_cart(editing) ? "อัปเดต" : "เพิ่มในรายการเบิก" }}
					</button>
				</div>
			</template>
		</Sheet>

		<!-- ตะกร้า -->
		<Sheet
			:open="cart_open"
			title="รายการเบิก"
			:subtitle="`${cart.length} รายการ`"
			full
			@close="cart_open = false"
		>
			<div class="ss-list">
				<TransitionGroup name="ss-list">
					<div v-for="line in cart" :key="line.item_code" class="ss-card ss-card--row">
						<span class="ss-card-main">
							<span class="ss-card-title">{{ line.item_name }}</span>
							<span class="ss-card-meta">คงเหลือ {{ num(line.balance) }} {{ line.uom }}</span>
						</span>
						<Stepper v-model="line.qty" :max="line.balance" :min="0" />
					</div>
				</TransitionGroup>
			</div>
			<div class="ss-form">
				<Picker
					v-model="wbs"
					label="ใช้กับงาน (WBS)"
					:options="wbs_options"
					placeholder="ไม่ระบุ"
					clearable
				/>
				<label class="ss-field">
					<span class="ss-field-label">ผู้เบิก / ผู้รับเหมา</span>
					<input v-model="issued_to" class="ss-input" placeholder="ชื่อผู้มารับของ" />
				</label>
				<label class="ss-field">
					<span class="ss-field-label">หมายเหตุ</span>
					<input v-model="remarks" class="ss-input" placeholder="ถ้ามี" />
				</label>
			</div>
			<template #footer>
				<button
					type="button"
					class="ss-btn ss-btn--primary ss-btn--block ss-btn--lg"
					:disabled="saving || !cart.some((l) => l.qty > 0)"
					@click="submit"
				>
					<span v-if="saving" class="ss-spinner"></span>
					<template v-else>ยืนยันเบิก {{ cart.filter((l) => l.qty > 0).length }} รายการ</template>
				</button>
			</template>
		</Sheet>
	</div>
</template>

<script setup>
import { computed, inject, ref, watch } from "vue";
import Icon from "../../../shared/components/Icon.vue";
import TopBar from "../../../shared/components/TopBar.vue";
import Segmented from "../../../shared/components/Segmented.vue";
import Skeleton from "../../../shared/components/Skeleton.vue";
import Empty from "../../../shared/components/Empty.vue";
import Sheet from "../../../shared/components/Sheet.vue";
import Stepper from "../../../shared/components/Stepper.vue";
import Picker from "../../../shared/components/Picker.vue";
import {
	call,
	celebrate,
	num,
	post,
	relative_date,
	remember_tab,
	short_time,
	show_error,
	state,
	vibrate,
} from "../../../shared/api.js";

const reload_summary = inject("reload_summary");
const tab = ref(state.route.params.tab === "history" ? "history" : "new");
const stock = ref(null);
const history_rows = ref(null);
const wbs_options = ref([]);
const loading = ref(false);
const txt = ref("");
const limit = ref(60);

const cart = ref([]);
const cart_open = ref(false);
const editing = ref(null);
const edit_qty = ref(1);
const wbs = ref(null);
const issued_to = ref("");
const remarks = ref("");
const saving = ref(false);

const available = computed(() => {
	const q = txt.value.trim().toLowerCase();
	return (stock.value || []).filter(
		(i) => i.balance > 0 && (!q || `${i.item_name} ${i.item_code}`.toLowerCase().includes(q))
	);
});
const quick_qty = computed(() => [1, 5, 10, 50].filter((q) => q < (editing.value?.balance || 0)));

const history_groups = computed(() => {
	const groups = [];
	for (const row of history_rows.value || []) {
		const date = String(row.date);
		let group = groups.find((g) => g.date === date);
		if (!group) groups.push((group = { date, rows: [] }));
		group.rows.push(row);
	}
	return groups;
});

const in_cart = (item) => item && cart.value.find((l) => l.item_code === item.item_code);
const issuer = (d) => (d.remarks || "").match(/ผู้เบิก: (.+)/)?.[1] || "เบิกวัสดุ";

function pick(item) {
	vibrate(8);
	editing.value = item;
	edit_qty.value = in_cart(item)?.qty || Math.min(1, item.balance);
}

function save_line() {
	const line = in_cart(editing.value);
	if (line) line.qty = edit_qty.value;
	else cart.value.push({ ...editing.value, qty: edit_qty.value });
	editing.value = null;
}

function remove(item) {
	cart.value = cart.value.filter((l) => l.item_code !== item.item_code);
	editing.value = null;
}

async function load() {
	loading.value = true;
	const project = state.project.name;
	try {
		if (tab.value === "new") {
			const [data, options] = await Promise.all([
				call("get_stock", { project }),
				wbs_options.value.length ? null : call("get_wbs", { project }),
			]);
			stock.value = data.items;
			if (options) wbs_options.value = options;
		} else {
			history_rows.value = await call("get_issue_history", { project });
		}
	} catch (error) {
		show_error(error);
		if (tab.value === "new") stock.value ??= [];
		else history_rows.value ??= [];
	} finally {
		loading.value = false;
	}
}

async function submit() {
	saving.value = true;
	try {
		const result = await post("submit_issue", {
			project: state.project.name,
			items: cart.value
				.filter((l) => l.qty > 0)
				.map((l) => ({ item_code: l.item_code, qty: l.qty, wbs: wbs.value })),
			issued_to: issued_to.value,
			remarks: remarks.value,
		});
		cart_open.value = false;
		cart.value = [];
		remarks.value = "";
		reload_summary();
		await celebrate("เบิกวัสดุแล้ว", result.name);
		stock.value = null;
		history_rows.value = null;
		tab.value = "history";
	} catch (error) {
		show_error(error);
	} finally {
		saving.value = false;
	}
}

watch(
	tab,
	(value) => {
		remember_tab("issue", value, "new");
		load();
	},
	{ immediate: true }
);
</script>
