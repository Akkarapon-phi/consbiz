<!--
	ลงเวลาคนงานรายวัน (หมวดธุรการ, API consbiz/labour.py) 1 หน้า = 1 รอบ (Labour Timesheet ของโครงการ)
	ช่อง = ชั่วโมงทำงานจริง 8 = เต็มวัน เกิน 8 = OT ว่าง = ไม่มา กดหัววันที่ = สลับวันหยุดของทั้งวัน
	จอ ≥ 768 = ตารางคน x วัน (พิมพ์ตัวเลข Enter/ลูกศรเลื่อนช่อง, วางจาก Excel ได้) มือถือ = ทีละวัน
	จัดกลุ่มตามทีม (Daily Worker.team, ว่าง = ชื่อ ผรม.) แถวหัวทีมพับได้ ช่องของแถวหัวทีม = ใส่ชั่วโมงให้ทั้งทีมในวันนั้น
	แท็บด้านบน = กรองทีม จุดแดง = ทีมที่ยังไม่มีชั่วโมงเลยในวันที่เลือก (ว่าง = ไม่มา จึงเตือนรายคนไม่ได้)
	บันทึกเฉพาะช่องที่แก้ (คนอื่นที่ลงรอบเดียวกันไม่ถูกทับ) ค่าแรงคำนวณที่ server หลังบันทึก
-->
<template>
	<div>
		<TopBar title="ลงเวลาคนงาน" :subtitle="state.project?.project_name">
			<template #search>
				<HeaderSearch v-if="wide" v-model="txt" placeholder="ค้นหาชื่อ ตำแหน่ง ทีม" />
			</template>
			<template #actions>
				<button
					v-if="!wide"
					type="button"
					class="ss-icon-btn"
					:class="{ 'is-spinning': loading }"
					aria-label="โหลดใหม่"
					@click="load(anchor)"
				>
					<Icon name="refresh" :size="20" />
				</button>
			</template>
		</TopBar>

		<div class="ss-content">
			<Skeleton v-if="data === null" :rows="6" />
			<template v-else>
				<div class="ss-stats ss-stats--3">
					<div class="ss-stat lb-tone" style="--i: 0">
						<span class="ss-stat-icon"><Icon name="users" :size="20" /></span>
						<span class="ss-stat-value">{{ fmt(totals.days) }}</span>
						<span class="ss-stat-label">แรง (คน-วัน)</span>
					</div>
					<div class="ss-stat lb-tone" style="--i: 1">
						<span class="ss-stat-icon"><Icon name="clock" :size="20" /></span>
						<span class="ss-stat-value">{{ fmt(totals.ot) }}</span>
						<span class="ss-stat-label">OT (ชม.)</span>
					</div>
					<div class="ss-stat lb-tone" style="--i: 2" :class="{ 'lb-stale': dirty_count }">
						<span class="ss-stat-icon"><Icon name="calculator" :size="20" /></span>
						<span class="ss-stat-value">{{ money(data.totals.gross) }}</span>
						<span class="ss-stat-label">{{ dirty_count ? "ค่าแรง (บันทึกแล้วจะคำนวณใหม่)" : "ค่าแรงรวม" }}</span>
					</div>
				</div>

				<div v-if="wide" class="ss-list-head">
					<StatusTabs v-if="!many_teams" v-model="team_tab" :options="team_tabs" />
					<!-- ทีมเยอะ (เกิน TAB_LIMIT) แท็บล้นแถบ: เหลือ "ทั้งหมด" + ทีมที่เลือก แล้วเลือกทีมจากรายการค้นหาได้ -->
					<div v-else class="lb-team-switch">
						<StatusTabs v-model="team_tab" :options="compact_tabs" />
						<button type="button" class="ss-btn ss-btn--soft ss-list-create" @click="team_picker = true">
							<Icon name="users" :size="16" />
							<span>เลือกทีม ({{ all_teams.length }})</span>
							<span v-if="idle_teams" class="ss-tab-count lb-idle" :title="`ยังไม่ได้ลงวันที่ ${day_no(fill_day)}`">{{ idle_teams }}</span>
						</button>
					</div>
					<div class="ss-list-tools">
						<button
							type="button"
							class="ss-icon-btn"
							:title="all_collapsed ? 'กางทุกทีม' : 'พับทุกทีม'"
							:aria-label="all_collapsed ? 'กางทุกทีม' : 'พับทุกทีม'"
							@click="toggle_all"
						>
							<Icon :name="all_collapsed ? 'chevrons-down' : 'chevrons-up'" :size="17" />
						</button>
						<span class="lb-period">
							<button type="button" class="ss-icon-btn" title="รอบก่อน" aria-label="รอบก่อน" @click="go_period(-1)">
								<Icon name="chevron-left" :size="17" />
							</button>
							<span class="lb-period-label">{{ period_label }}</span>
							<button
								type="button"
								class="ss-icon-btn"
								title="รอบถัดไป"
								aria-label="รอบถัดไป"
								:disabled="data.to_date >= data.today"
								@click="go_period(1)"
							>
								<Icon name="chevron-right" :size="17" />
							</button>
						</span>
						<span v-if="data.timesheet" class="lb-doc">
							{{ data.timesheet }}
							<span class="ss-tag" :class="data.docstatus === 1 ? 'tone-green' : 'tone-amber'">{{
								data.docstatus === 1 ? "อนุมัติแล้ว" : "ร่าง"
							}}</span>
						</span>
						<button
							v-if="wide && data.can_edit && data.workers.length"
							type="button"
							class="ss-btn ss-btn--soft ss-list-create"
							:title="`เติม 8 ชม. ในช่องว่างของวันที่ ${thai_date(fill_day)} (เฉพาะคนที่แสดงอยู่)`"
							@click="fill(fill_day)"
						>
							<Icon name="check" :size="16" /> เติม 8 ชม. ({{ day_no(fill_day) }})
						</button>
						<button
							v-if="data.can_add_worker && data.can_edit"
							type="button"
							class="ss-btn ss-btn--soft ss-list-create"
							@click="open_add"
						>
							<Icon name="plus" :size="16" /> คนงานใหม่
						</button>
						<button
							v-if="wide"
							type="button"
							class="ss-icon-btn"
							:class="{ 'is-spinning': loading }"
							aria-label="โหลดใหม่"
							title="โหลดใหม่"
							@click="load(anchor)"
						>
							<Icon name="refresh" :size="17" />
						</button>
						<button
							v-if="data.can_print"
							type="button"
							class="ss-icon-btn"
							title="พิมพ์ใบลงเวลา/ใบเซ็นรับเงิน"
							aria-label="พิมพ์"
							@click="print_open = true"
						>
							<Icon name="printer" :size="17" />
						</button>
						<button
							v-if="data.can_submit"
							type="button"
							class="ss-btn ss-btn--primary ss-list-create"
							:disabled="busy || dirty_count > 0"
							:title="dirty_count ? 'บันทึกก่อนอนุมัติ' : 'อนุมัติค่าแรงของรอบนี้ หลังจากนี้แก้ไม่ได้'"
							@click="approve"
						>
							<Icon name="check" :size="18" :stroke="2.6" />
							<span>อนุมัติรอบนี้</span>
						</button>
					</div>
				</div>

				<div v-if="!wide" class="lb-mobile-head">
					<span class="lb-period">
						<button type="button" class="ss-icon-btn" aria-label="รอบก่อน" @click="go_period(-1)">
							<Icon name="chevron-left" :size="20" />
						</button>
						<span class="lb-period-label">{{ period_label }}</span>
						<button type="button" class="ss-icon-btn" aria-label="รอบถัดไป" :disabled="data.to_date >= data.today" @click="go_period(1)">
							<Icon name="chevron-right" :size="20" />
						</button>
					</span>
					<SelectBox v-model="team_tab" :options="team_tabs.map((t) => ({ value: t.value, label: `${t.label} (${t.count})${t.alert ? ' •' : ''}` }))" label="ทีม" />
					<input v-model="txt" class="ss-input" placeholder="ค้นหาชื่อ ตำแหน่ง" />
					<div class="lb-mobile-actions">
						<span v-if="data.timesheet" class="lb-doc">
							{{ data.timesheet }}
							<span class="ss-tag" :class="data.docstatus === 1 ? 'tone-green' : 'tone-amber'">{{
								data.docstatus === 1 ? "อนุมัติแล้ว" : "ร่าง"
							}}</span>
						</span>
						<button v-if="data.can_add_worker && data.can_edit" type="button" class="ss-icon-btn" aria-label="คนงานใหม่" @click="open_add">
							<Icon name="plus" :size="20" />
						</button>
						<button v-if="data.can_print" type="button" class="ss-icon-btn" aria-label="พิมพ์" @click="print_open = true">
							<Icon name="printer" :size="20" />
						</button>
						<button
							v-if="data.can_submit"
							type="button"
							class="ss-btn ss-btn--primary"
							:disabled="busy || dirty_count > 0"
							@click="approve"
						>
							อนุมัติรอบนี้
						</button>
					</div>
				</div>

				<Empty
					v-if="!data.workers.length"
					icon="users"
					title="ยังไม่มีคนงานในโครงการนี้"
					text="กด คนงานใหม่ หรือตั้งโครงการที่ประจำในทะเบียนคนงาน"
				/>

				<Empty v-else-if="!groups.length" icon="search" title="ไม่พบคนงาน" />

				<!-- จอ ≥ 768: ตารางคน x วัน จัดกลุ่มตามทีม -->
				<div v-else-if="wide" class="lb-grid-wrap">
					<table class="lb-grid">
						<thead>
							<tr>
								<th class="lb-name">คนงาน</th>
								<th
									v-for="d in days"
									:key="d.iso"
									class="lb-day"
									:class="{
										'is-holiday': holidays.has(d.iso),
										'is-today': d.iso === data.today,
										'is-future': d.future,
										'can-click': data.can_edit,
									}"
									:title="data.can_edit ? (holidays.has(d.iso) ? 'วันหยุด (กดเพื่อยกเลิก)' : 'กดเพื่อตั้งเป็นวันหยุด') : ''"
									@click="toggle_holiday(d.iso)"
								>
									<span>{{ d.day }}</span>
									<small>{{ holidays.has(d.iso) ? "หยุด" : d.dow }}</small>
								</th>
								<th class="lb-total" title="แรงงาน (วัน) = ชั่วโมงปกติ ÷ 8">วัน</th>
								<th class="lb-total" title="ชั่วโมงเกิน 8 ของแต่ละวัน">OT</th>
								<th class="lb-money">ค่าแรง</th>
								<th class="lb-money">สุทธิ</th>
							</tr>
						</thead>
						<tbody v-for="g in groups" :key="g.team">
							<tr class="lb-team" :class="{ 'is-collapsed': collapsed.has(g.team) }">
								<th class="lb-name" :title="collapsed.has(g.team) ? 'กาง' : 'พับ'" @click="toggle_team(g.team)">
									<span class="lb-team-name">
										<Icon :name="collapsed.has(g.team) ? 'chevron-right' : 'chevron-down'" :size="14" />
										<b>{{ g.team }}</b>
										<span class="ss-tab-count">{{ g.workers.length }}</span>
									</span>
									<small>{{ team_sub(g) }}</small>
								</th>
								<td
									v-for="d in days"
									:key="d.iso"
									class="lb-cell lb-team-cell"
									:class="{ 'is-holiday': holidays.has(d.iso) }"
								>
									<input
										:value="team_value(g, d.iso)"
										:placeholder="team_count(g, d.iso) ? String(team_count(g, d.iso)) : ''"
										:disabled="!data.can_edit || d.future"
										:title="`ใส่ชั่วโมงให้ทั้งทีม ${g.team} วันที่ ${d.day} (ตัวเลขจาง = จำนวนคนที่มา)`"
										inputmode="decimal"
										autocomplete="off"
										@focus="on_focus($event, d.iso)"
										@change="set_team_day(g, d.iso, $event.target.value)"
										@keydown.enter.prevent="$event.target.blur()"
									/>
								</td>
								<td class="lb-total">{{ fmt(group_sum(g).days) }}</td>
								<td class="lb-total">{{ fmt(group_sum(g).ot) }}</td>
								<td class="lb-money" :class="{ 'lb-stale': g.workers.some(row_dirty) }">{{ money(group_sum(g).gross) }}</td>
								<td class="lb-money" :class="{ 'lb-stale': g.workers.some(row_dirty) }">{{ money(group_sum(g).net) }}</td>
							</tr>
							<template v-if="!collapsed.has(g.team)">
								<tr v-for="w in g.workers" :key="w.worker">
									<th class="lb-name is-link" title="ดูค่าแรง / หักอื่นๆ" @click="open_detail(w)">
										<span class="ss-cell-main">{{ w.worker_name }}</span>
										<small>{{ worker_sub(w) }}</small>
									</th>
									<td
										v-for="(d, c) in days"
										:key="d.iso"
										class="lb-cell"
										:class="{
											'is-holiday': holidays.has(d.iso),
											'is-changed': is_changed(w.worker, d.iso),
											'is-bad': is_bad(w.worker, d.iso),
											'is-ot': hours_of(w.worker, d.iso) > 8,
										}"
									>
										<input
											:ref="(el) => set_ref(row_index.get(w.worker), c, el)"
											:value="cell_text(w.worker, d.iso)"
											:disabled="!data.can_edit || d.future"
											inputmode="decimal"
											autocomplete="off"
											:aria-label="`${w.worker_name} วันที่ ${d.day}`"
											@focus="on_focus($event, d.iso)"
											@input="edit(w.worker, d.iso, $event.target.value)"
											@keydown="on_key($event, row_index.get(w.worker), c)"
											@paste="on_paste($event, row_index.get(w.worker), c)"
										/>
									</td>
									<td class="lb-total">{{ fmt(sum_of(w).days) }}</td>
									<td class="lb-total">{{ fmt(sum_of(w).ot) }}</td>
									<td class="lb-money" :class="{ 'lb-stale': row_dirty(w) }">{{ w.pay ? money(w.pay.gross) : "" }}</td>
									<td class="lb-money" :class="{ 'lb-stale': row_dirty(w) }">
										<b v-if="w.pay">{{ money(w.pay.net) }}</b>
									</td>
								</tr>
							</template>
						</tbody>
					</table>
				</div>

				<!-- มือถือ: ทีละวัน -->
				<template v-else>
					<div class="lb-mobile-day">
						<button type="button" class="ss-icon-btn" aria-label="วันก่อน" @click="shift_day(-1)">
							<Icon name="chevron-left" :size="20" />
						</button>
						<DateInput :model-value="mobile_day" :max="data.today" @update:model-value="pick_day" />
						<button
							type="button"
							class="ss-icon-btn"
							aria-label="วันถัดไป"
							:disabled="mobile_day >= data.today"
							@click="shift_day(1)"
						>
							<Icon name="chevron-right" :size="20" />
						</button>
					</div>
					<div class="lb-mobile-tools">
						<label v-if="data.can_edit" class="ss-toggle" :class="{ 'is-on': holidays.has(mobile_day) }">
							<input type="checkbox" :checked="holidays.has(mobile_day)" @change="toggle_holiday(mobile_day)" />
							<span class="ss-toggle-track"><span></span></span>
							<span>วันหยุด</span>
						</label>
						<button
							v-if="data.can_edit"
							type="button"
							class="ss-btn ss-btn--soft"
							@click="fill(mobile_day)"
						>
							<Icon name="check" :size="16" /> ที่เหลือ 8 ชม.
						</button>
					</div>
					<template v-for="g in groups" :key="g.team">
					<div class="ss-day lb-mobile-team">
						<span>{{ g.team }} · {{ g.workers.length }} คน</span>
						<button v-if="data.can_edit" type="button" class="ss-link" @click="set_team_day(g, mobile_day, '8')">ทั้งทีม 8 ชม.</button>
					</div>
					<div class="ss-list">
						<div
							v-for="w in g.workers"
							:key="w.worker"
							class="ss-card lb-card"
							:class="{ 'is-changed': is_changed(w.worker, mobile_day) }"
						>
							<button type="button" class="ss-card-main lb-card-name" @click="open_detail(w)">
								<span class="ss-card-title">{{ w.worker_name }}</span>
								<span class="ss-card-meta">
									{{ worker_sub(w) }}
									<template v-if="w.pay"> · สุทธิ {{ money(w.pay.net) }}</template>
								</span>
							</button>
							<div class="lb-card-input">
								<div class="ss-quick ss-quick--left">
									<button
										v-for="q in QUICK"
										:key="q.value"
										type="button"
										class="ss-reason"
										:class="{ 'is-active': hours_of(w.worker, mobile_day) === q.value }"
										:disabled="!data.can_edit"
										@click="edit(w.worker, mobile_day, q.value ? String(q.value) : '')"
									>
										{{ q.label }}
									</button>
								</div>
								<Stepper
									:model-value="hours_of(w.worker, mobile_day)"
									:min="0"
									:max="data.max_hours"
									:step="0.5"
									@update:model-value="(v) => data.can_edit && edit(w.worker, mobile_day, v ? String(v) : '')"
								/>
							</div>
						</div>
					</div>
					</template>
				</template>

				<p v-if="wide && data.workers.length" class="lb-legend ss-muted">
					ช่อง = ชั่วโมงทำงานจริง (หักพักแล้ว) 8 = เต็มวัน เกิน 8 = OT ว่าง = ไม่มา ·
					กดหัววันที่เพื่อตั้งวันหยุด (ค่าแรง x 2, OT x 3) · ช่องแถวทีม = ใส่ให้ทั้งทีม · Enter / ลูกศร = เลื่อนช่อง ·
					คัดลอกจาก Excel แล้ว Ctrl+V ที่ช่องแรก = วางหลายช่อง · Ctrl+S = บันทึก
				</p>
			</template>
		</div>

		<Teleport to="#ss-layer">
			<Transition name="ss-bar">
				<div v-if="data?.can_edit && dirty_count" class="ss-bottom-bar">
					<span v-if="bad_count" class="ss-text-danger lb-bar-note">ช่องที่ไม่ถูกต้อง {{ bad_count }} ช่อง (0-{{ data.max_hours }} ชม.)</span>
					<button type="button" class="ss-btn ss-btn--ghost ss-btn--lg" @click="reset">ยกเลิก</button>
					<button
						type="button"
						class="ss-btn ss-btn--primary ss-btn--lg ss-grow"
						:disabled="busy || bad_count > 0"
						@click="save"
					>
						<span v-if="busy" class="ss-spinner"></span>
						<template v-else>บันทึก {{ dirty_count }} ช่อง</template>
					</button>
				</div>
			</Transition>
		</Teleport>

		<Sheet
			:open="!!detail"
			:title="detail?.worker_name"
			:subtitle="detail && `รอบ ${period_label}`"
			@close="detail = null"
		>
			<div v-if="detail" class="lb-detail">
				<button type="button" class="ss-link lb-edit-worker" @click="editing = detail.worker">
					<Icon name="pen" :size="14" /> แก้ข้อมูลคนงาน (ทีม ค่าแรง บัญชีธนาคาร)
				</button>
				<p v-if="!detail.pay" class="ss-muted">ยังไม่มีค่าแรงในรอบนี้ (ลงเวลาแล้วกดบันทึก)</p>
				<template v-else>
					<p v-if="row_dirty(detail)" class="ss-note ss-note--warn">มีชั่วโมงที่ยังไม่บันทึก ยอดด้านล่างยังเป็นของเดิม</p>
					<dl class="lb-pay">
						<dt>วันทำงาน</dt>
						<dd>{{ fmt(detail.pay.days_worked) }} แรง<template v-if="detail.pay.holiday_days"> (วันหยุด {{ fmt(detail.pay.holiday_days) }})</template></dd>
						<dt>ค่าแรง</dt>
						<dd>{{ money(detail.pay.wage) }}</dd>
						<dt>OT {{ fmt(detail.pay.ot_hours) }} ชม.</dt>
						<dd>{{ money(detail.pay.ot_amount) }}</dd>
						<dt class="is-total">รวมค่าแรง</dt>
						<dd class="is-total">{{ money(detail.pay.gross) }}</dd>
						<dt>หักเบิกล่วงหน้า</dt>
						<dd>{{ detail.pay.advance ? `-${money(detail.pay.advance)}` : "–" }}</dd>
						<dt>หักประกันสังคม</dt>
						<dd>{{ detail.pay.sso ? `-${money(detail.pay.sso)}` : "–" }}</dd>
						<dt>หักอื่นๆ</dt>
						<dd>{{ detail.pay.other_deduction ? `-${money(detail.pay.other_deduction)}` : "–" }}</dd>
						<dt class="is-total">รับสุทธิ</dt>
						<dd class="is-total">{{ money(detail.pay.net) }}</dd>
					</dl>
					<p v-if="detail.pay.employer_sso" class="ss-muted lb-small">
						ประกันสังคมส่วนนายจ้าง {{ money(detail.pay.employer_sso) }} (บริษัทจ่ายเพิ่ม ไม่หักจากคนงาน)
					</p>
					<p v-if="detail.pay.purchase_invoice" class="ss-muted lb-small">
						จ่ายผ่าน ผรม. ใน Purchase Invoice {{ detail.pay.purchase_invoice }}
					</p>
					<template v-if="data.can_edit && data.timesheet">
						<h3 class="ss-section-title">หักอื่นๆ</h3>
						<label class="ss-field">
							<span class="ss-field-label">จำนวนเงิน</span>
							<MoneyInput v-model="deduction.amount" />
						</label>
						<label class="ss-field">
							<span class="ss-field-label">เหตุผล</span>
							<input v-model="deduction.remark" class="ss-input" placeholder="เช่น ค่าอุปกรณ์ชำรุด" />
						</label>
					</template>
				</template>
			</div>
			<template v-if="detail?.pay && data.can_edit && data.timesheet" #footer>
				<div class="ss-sheet-actions">
					<button
						type="button"
						class="ss-btn ss-btn--primary ss-btn--block ss-btn--lg"
						:disabled="busy || row_dirty(detail)"
						@click="save_deduction"
					>
						บันทึกหักอื่นๆ
					</button>
				</div>
			</template>
		</Sheet>

		<PdfViewer
			:open="print_open"
			:fetch_file="fetch_print"
			:name="data?.timesheet"
			:file_name="data?.timesheet"
			title="ใบลงเวลาคนงาน"
			@close="print_open = false"
		/>

		<WorkerSheet
			:open="adding || !!editing"
			:name="editing"
			:project="state.project?.name"
			:teams="team_names"
			@close="close_worker"
			@saved="on_saved"
		/>

		<Sheet :open="team_picker" title="เลือกทีม" :subtitle="`${all_teams.length} ทีม`" @close="team_picker = false">
			<input v-model="team_txt" class="ss-input" placeholder="ค้นหาทีม" />
			<div class="lb-team-list">
				<button
					v-for="t in picker_teams"
					:key="t.value"
					type="button"
					class="lb-team-option"
					:class="{ 'is-active': t.value === team_tab }"
					@click="pick_team(t.value)"
				>
					<span>{{ t.label }}</span>
					<span v-if="t.alert" class="ss-tab-dot" :title="t.alert"></span>
					<span class="ss-tab-count">{{ t.count }}</span>
				</button>
			</div>
		</Sheet>
	</div>
</template>

<script setup>
import { computed, onBeforeUnmount, reactive, ref } from "vue";
import Icon from "../../../shared/components/Icon.vue";
import TopBar from "../../../shared/components/TopBar.vue";
import Skeleton from "../../../shared/components/Skeleton.vue";
import Empty from "../../../shared/components/Empty.vue";
import StatusTabs from "../../../shared/components/StatusTabs.vue";
import Stepper from "../../../shared/components/Stepper.vue";
import DateInput from "../../../shared/components/DateInput.vue";
import WorkerSheet from "./WorkerSheet.vue";
import HeaderSearch from "../../../shared/components/HeaderSearch.vue";
import SelectBox from "../../../shared/components/SelectBox.vue";
import { matches } from "../../../shared/table.js";
import Sheet from "../../../shared/components/Sheet.vue";
import MoneyInput from "../../../shared/components/MoneyInput.vue";
import PdfViewer from "../../../shared/components/PdfViewer.vue";
import { use_wide } from "../../../shared/table.js";
import {
	call,
	money,
	post,
	replace_params,
	set_leave_guard,
	show_error,
	state,
	thai_date,
	toast,
	today,
} from "../../../shared/api.js";

const API = "consbiz.labour.";
const DOW = ["อา", "จ", "อ", "พ", "พฤ", "ศ", "ส"];
const HOURS_PER_DAY = 8;
const QUICK = [
	{ value: 0, label: "ไม่มา" },
	{ value: 4, label: "4" },
	{ value: 8, label: "8" },
	{ value: 10, label: "10" },
];

const wide = use_wide();
const is_day = (v) => /^\d{4}-\d{2}-\d{2}$/.test(v || "");
const anchor = ref(is_day(state.route.params.day) ? state.route.params.day : today());
const data = ref(null);
const loading = ref(false);
const busy = ref(false);
const detail = ref(null);
const deduction = reactive({ amount: 0, remark: "" });
const print_open = ref(false);
const txt = ref("");
const team_tab = ref("all");
const collapsed = ref(new Set());
// ทีมเกินนี้ = เปลี่ยนแท็บเป็นปุ่มเลือกทีม (แท็บล้นแถบเมื่อมี ผรม. หลายราย)
const TAB_LIMIT = 5;
const team_picker = ref(false);
const team_txt = ref("");
const editing = ref(null);
// ช่องที่แก้: "worker|date" → ข้อความที่พิมพ์
const edits = reactive({});
const holidays = ref(new Set());
const mobile_day = ref(today());
const focused_day = ref(null);
const adding = ref(false);

const iso = (d) =>
	`${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
const add_days = (value, n) => {
	const d = new Date(`${value}T00:00:00`);
	d.setDate(d.getDate() + n);
	return iso(d);
};
const fmt = (v) => (v ? Number(v.toFixed(2)).toLocaleString("th-TH") : "–");
const day_no = (value) => Number(String(value).slice(8, 10));

const days = computed(() => {
	if (!data.value) return [];
	const out = [];
	for (let value = data.value.from_date; value <= data.value.to_date; value = add_days(value, 1)) {
		const d = new Date(`${value}T00:00:00`);
		out.push({ iso: value, day: d.getDate(), dow: DOW[d.getDay()], future: value > data.value.today });
	}
	return out;
});
const period_label = computed(() => {
	if (!data.value) return "";
	const from = day_no(data.value.from_date);
	return `${from}-${thai_date(data.value.to_date, { year: true })}`;
});
const saved_holidays = computed(() => new Set(data.value?.holidays || []));
const holidays_changed = computed(
	() =>
		holidays.value.size !== saved_holidays.value.size ||
		[...holidays.value].some((d) => !saved_holidays.value.has(d))
);
const changed_keys = computed(() => Object.keys(edits).filter((key) => is_changed(...key.split("|"))));
const dirty_count = computed(() => changed_keys.value.length + (holidays_changed.value ? 1 : 0));
const bad_count = computed(() => changed_keys.value.filter((key) => is_bad(...key.split("|"))).length);
// วันที่ปุ่ม "เติม 8 ชม." ใช้: ช่องที่โฟกัสล่าสุด หรือวันนี้/วันสุดท้ายของรอบ
const fill_day = computed(() => {
	if (!data.value) return today();
	if (!wide.value) return mobile_day.value;
	if (focused_day.value) return focused_day.value;
	return data.value.today < data.value.to_date ? data.value.today : data.value.to_date;
});
// ทีมทั้งหมด (ตามลำดับจาก server: เรียงทีมแล้ว) และทีมที่แสดงหลังกรอง
const all_teams = computed(() => {
	const out = [];
	for (const w of data.value?.workers || []) {
		let g = out.find((x) => x.team === w.team);
		if (!g) out.push((g = { team: w.team, workers: [] }));
		g.workers.push(w);
	}
	return out;
});
const team_names = computed(() => all_teams.value.map((g) => g.team));
const team_idle = (g, date) => date <= (data.value?.today || "") && !holidays.value.has(date) && !g.workers.some((w) => hours_of(w.worker, date));
const team_tabs = computed(() => [
	{
		value: "all",
		label: "ทั้งหมด",
		count: data.value?.workers.length || 0,
		alert: all_teams.value.some((g) => team_idle(g, fill_day.value)) && `มีทีมที่ยังไม่ได้ลงวันที่ ${day_no(fill_day.value)}`,
	},
	...all_teams.value.map((g) => ({
		value: g.team,
		label: g.team,
		count: g.workers.length,
		alert: team_idle(g, fill_day.value) && `ยังไม่ได้ลงวันที่ ${day_no(fill_day.value)}`,
	})),
]);
const many_teams = computed(() => all_teams.value.length > TAB_LIMIT);
const compact_tabs = computed(() => team_tabs.value.filter((t) => t.value === "all" || t.value === team_tab.value));
const idle_teams = computed(() => all_teams.value.filter((g) => team_idle(g, fill_day.value)).length);
const picker_teams = computed(() => team_tabs.value.filter((t) => matches(team_txt.value, t.label)));
const all_collapsed = computed(() => groups.value.length > 0 && groups.value.every((g) => collapsed.value.has(g.team)));
const groups = computed(() =>
	all_teams.value
		.filter((g) => team_tab.value === "all" || g.team === team_tab.value)
		.map((g) => ({
			team: g.team,
			workers: g.workers.filter((w) => matches(txt.value, w.worker_name, w.position, w.team, w.payee)),
		}))
		.filter((g) => g.workers.length)
);
// แถวที่มองเห็น (ไม่นับทีมที่พับ) ลำดับนี้ใช้เลื่อนช่องด้วยลูกศร/วางหลายแถว
const visible = computed(() => groups.value.flatMap((g) => (collapsed.value.has(g.team) ? [] : g.workers)));
const row_index = computed(() => new Map(visible.value.map((w, i) => [w.worker, i])));
const shown_workers = computed(() => groups.value.flatMap((g) => g.workers));

const totals = computed(() => {
	const out = { days: 0, ot: 0 };
	for (const w of data.value?.workers || []) {
		const s = sum_of(w);
		out.days += s.days;
		out.ot += s.ot;
	}
	return out;
});

const key_of = (worker, date) => `${worker}|${date}`;
function saved_of(worker, date) {
	const w = data.value.workers.find((x) => x.worker === worker);
	return Number(w?.hours?.[date] || 0);
}
function parse_hours(text) {
	const value = String(text ?? "").trim();
	if (!value) return 0;
	const n = Number(value.replace(",", "."));
	return Number.isFinite(n) ? n : NaN;
}
function hours_of(worker, date) {
	const key = key_of(worker, date);
	if (key in edits) {
		const n = parse_hours(edits[key]);
		return Number.isNaN(n) ? 0 : n;
	}
	return saved_of(worker, date);
}
function cell_text(worker, date) {
	const key = key_of(worker, date);
	if (key in edits) return edits[key];
	const n = saved_of(worker, date);
	return n ? String(n) : "";
}
function is_changed(worker, date) {
	const key = key_of(worker, date);
	if (!(key in edits)) return false;
	const n = parse_hours(edits[key]);
	return Number.isNaN(n) || n !== saved_of(worker, date);
}
function is_bad(worker, date) {
	const key = key_of(worker, date);
	if (!(key in edits)) return false;
	const n = parse_hours(edits[key]);
	return Number.isNaN(n) || n < 0 || n > data.value.max_hours;
}
function sum_of(w) {
	let normal = 0;
	let ot = 0;
	for (const d of days.value) {
		const h = hours_of(w.worker, d.iso);
		normal += Math.min(h, HOURS_PER_DAY);
		ot += Math.max(h - HOURS_PER_DAY, 0);
	}
	return { days: normal / HOURS_PER_DAY, ot };
}
const row_dirty = (w) => changed_keys.value.some((key) => key.startsWith(`${w.worker}|`));
const worker_sub = (w) => [w.position, w.payee].filter(Boolean).join(" · ");

function edit(worker, date, text) {
	edits[key_of(worker, date)] = text;
}

function toggle_holiday(date) {
	if (!data.value.can_edit) return;
	const next = new Set(holidays.value);
	next.has(date) ? next.delete(date) : next.add(date);
	holidays.value = next;
}

function fill(date) {
	if (date > data.value.today) return toast("ยังไม่ถึงวันนั้น", "info");
	for (const w of shown_workers.value) if (!hours_of(w.worker, date)) edit(w.worker, date, "8");
}

function toggle_all() {
	collapsed.value = all_collapsed.value ? new Set() : new Set(groups.value.map((g) => g.team));
}
function pick_team(team) {
	team_tab.value = team;
	team_picker.value = false;
	team_txt.value = "";
	if (team !== "all") {
		const next = new Set(collapsed.value);
		next.delete(team);
		collapsed.value = next;
	}
}

function toggle_team(team) {
	const next = new Set(collapsed.value);
	next.has(team) ? next.delete(team) : next.add(team);
	collapsed.value = next;
}
// ค่าในช่องแถวทีม: ทุกคนในทีมเท่ากัน = แสดงค่านั้น ไม่งั้นว่าง (ตัวจาง = จำนวนคนที่มา)
function team_value(g, date) {
	const values = new Set(g.workers.map((w) => hours_of(w.worker, date)));
	const [only] = values;
	return values.size === 1 && only ? String(only) : "";
}
const team_count = (g, date) => g.workers.filter((w) => hours_of(w.worker, date) > 0).length;
function set_team_day(g, date, text) {
	if (!data.value.can_edit || date > data.value.today) return;
	const value = String(text ?? "").trim();
	if (value && Number.isNaN(parse_hours(value))) return toast("ใส่เป็นตัวเลขชั่วโมง", "info");
	for (const w of g.workers) edit(w.worker, date, value);
}
function group_sum(g) {
	const out = { days: 0, ot: 0, gross: 0, net: 0 };
	for (const w of g.workers) {
		const s = sum_of(w);
		out.days += s.days;
		out.ot += s.ot;
		out.gross += w.pay?.gross || 0;
		out.net += w.pay?.net || 0;
	}
	return out;
}
function team_sub(g) {
	const positions = [...new Set(g.workers.map((w) => w.position).filter(Boolean))];
	return positions.slice(0, 3).join(" · ") + (positions.length > 3 ? " ..." : "");
}

// วางจาก Excel: แถว = คนงานถัดลงไป (ตามที่มองเห็น) คอลัมน์ = วันถัดไป
function on_paste(event, r, c) {
	const text = event.clipboardData?.getData("text") || "";
	if (!/[\t\n]/.test(text.trim())) return;
	event.preventDefault();
	const lines = text.replace(/\r/g, "").replace(/\n$/, "").split("\n");
	let count = 0;
	lines.forEach((line, i) => {
		line.split("\t").forEach((value, j) => {
			const w = visible.value[r + i];
			const d = days.value[c + j];
			if (w && d && !d.future) {
				edit(w.worker, d.iso, value.trim());
				count += 1;
			}
		});
	});
	toast(`วาง ${count} ช่อง`, "success");
}

function clear_edits() {
	for (const key of Object.keys(edits)) delete edits[key];
}

function apply(result) {
	data.value = result;
	clear_edits();
	holidays.value = new Set(result.holidays);
	anchor.value = result.from_date;
	if (mobile_day.value < result.from_date || mobile_day.value > result.to_date) {
		mobile_day.value = result.today < result.to_date ? result.today : result.to_date;
	}
	focused_day.value = null;
}

async function load(date) {
	loading.value = true;
	try {
		apply(await call(API + "get_sheet", { project: state.project.name, date }));
		const current = data.value.from_date <= today() && today() <= data.value.to_date;
		replace_params("labour", { day: current ? undefined : data.value.from_date });
	} catch (error) {
		show_error(error);
		data.value ??= { workers: [], holidays: [], totals: {} };
	} finally {
		loading.value = false;
	}
}

function confirm_discard() {
	return !dirty_count.value || window.confirm("ยังไม่ได้บันทึกการลงเวลา ออกโดยไม่บันทึก?");
}

function go_period(step) {
	if (!confirm_discard()) return;
	load(step < 0 ? add_days(data.value.from_date, -1) : add_days(data.value.to_date, 1));
}

function pick_day(date) {
	if (!date) return;
	if (date >= data.value.from_date && date <= data.value.to_date) {
		mobile_day.value = date;
		return;
	}
	if (!confirm_discard()) return;
	mobile_day.value = date;
	load(date);
}
function shift_day(step) {
	const next = add_days(mobile_day.value, step);
	if (next <= data.value.today) pick_day(next);
}

async function save() {
	if (bad_count.value) return;
	busy.value = true;
	try {
		const cells = changed_keys.value.map((key) => {
			const [worker, date] = key.split("|");
			return { worker, date, hours: parse_hours(edits[key]) || null };
		});
		const result = await post(API + "save_sheet", {
			project: state.project.name,
			date: data.value.from_date,
			cells,
			holidays: holidays_changed.value ? [...holidays.value] : undefined,
		});
		apply(result);
		toast("บันทึกการลงเวลาแล้ว", "success");
	} catch (error) {
		show_error(error);
	} finally {
		busy.value = false;
	}
}

function reset() {
	clear_edits();
	holidays.value = new Set(data.value.holidays);
}

async function approve() {
	if (!window.confirm(`อนุมัติค่าแรงรอบ ${period_label.value} รวม ${money(data.value.totals.gross)} บาท? หลังอนุมัติแก้ไม่ได้`)) return;
	busy.value = true;
	try {
		apply(await post(API + "submit_sheet", { name: data.value.timesheet }));
		toast("อนุมัติค่าแรงของรอบแล้ว", "success");
	} catch (error) {
		show_error(error);
	} finally {
		busy.value = false;
	}
}

// เลื่อนช่องแบบตาราง: Enter/↓ ลง, ↑ ขึ้น, ←/→ เมื่อเคอร์เซอร์อยู่ขอบข้อความ
const refs = new Map();
function set_ref(r, c, el) {
	if (el) refs.set(`${r}:${c}`, el);
	else refs.delete(`${r}:${c}`);
}
function move(r, c) {
	const el = refs.get(`${r}:${c}`);
	if (el && !el.disabled) {
		el.focus();
		return true;
	}
	return false;
}
function on_focus(event, date) {
	focused_day.value = date;
	event.target.select();
}
function on_key(event, r, c) {
	const el = event.target;
	const at_start = el.selectionStart === 0 && el.selectionEnd === 0;
	const at_end = el.selectionStart === el.value.length;
	const all = el.selectionStart === 0 && el.selectionEnd === el.value.length;
	let moved = false;
	if (event.key === "Enter" || event.key === "ArrowDown") moved = move(r + 1, c);
	else if (event.key === "ArrowUp") moved = move(r - 1, c);
	else if (event.key === "ArrowRight" && (at_end || all)) moved = move(r, c + 1);
	else if (event.key === "ArrowLeft" && (at_start || all)) moved = move(r, c - 1);
	else return;
	if (moved || event.key === "Enter") event.preventDefault();
}

function on_global_key(event) {
	if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "s") {
		event.preventDefault();
		if (dirty_count.value && !busy.value) save();
	}
}
window.addEventListener("keydown", on_global_key);

function open_add() {
	adding.value = true;
}

// เติมคนใหม่ท้ายตาราง คงช่องที่แก้ไว้แต่ยังไม่บันทึก
function open_detail(w) {
	detail.value = w;
	deduction.amount = w.pay?.other_deduction || 0;
	deduction.remark = w.pay?.deduction_remark || "";
}

async function save_deduction() {
	busy.value = true;
	try {
		const worker = detail.value.worker;
		apply(
			await post(API + "set_deduction", {
				name: data.value.timesheet,
				worker,
				amount: deduction.amount || 0,
				remark: deduction.remark,
			})
		);
		detail.value = data.value.workers.find((w) => w.worker === worker) || null;
		toast("บันทึกหักอื่นๆ แล้ว", "success");
	} catch (error) {
		show_error(error);
	} finally {
		busy.value = false;
	}
}

// PDF ผ่าน Print Format "Labour Timesheet" (A4 แนวนอน) ดึงเป็นไฟล์ให้ PdfViewer วาดเอง (มือถือแสดง PDF ใน iframe ไม่ได้)
async function fetch_print() {
	const url = await call(API + "get_print_url", { name: data.value.timesheet });
	return fetch(url, { credentials: "same-origin" });
}

function close_worker() {
	adding.value = false;
	editing.value = null;
}

// เพิ่ม = แทรกท้ายทีม, แก้ = อัปเดตแถวเดิม (ย้ายทีม/ชื่อ) แล้วโหลดใหม่ให้ลำดับตรงกับ server
async function on_saved(worker) {
	const was_edit = !!editing.value;
	close_worker();
	if (was_edit) {
		if (detail.value?.worker === worker.worker) detail.value = null;
		if (!dirty_count.value) return load(anchor.value);
		const row = data.value.workers.find((w) => w.worker === worker.worker);
		if (row) Object.assign(row, { worker_name: worker.worker_name, position: worker.position, team: worker.team, payee: worker.payee });
		return;
	}
	on_added(worker);
}

function on_added(worker) {
	// แทรกท้ายทีมเดียวกัน (ไม่มีทีม = ท้ายตาราง)
	const row = { ...worker, hours: {}, pay: null };
	const list = data.value.workers;
	const last = list.map((w) => w.team).lastIndexOf(row.team);
	list.splice(last >= 0 ? last + 1 : list.length, 0, row);
}

set_leave_guard(async () => confirm_discard());
onBeforeUnmount(() => {
	set_leave_guard(null);
	window.removeEventListener("keydown", on_global_key);
});
load(anchor.value);
</script>

<style scoped>
/* การ์ดตัวเลขใช้สีของหมวด (ธุรการไม่มี tone-* ของตัวเอง) */
.lb-tone {
	--tone: var(--ss-brand);
	--tone-bg: var(--ss-brand-soft);
}
.lb-period {
	display: inline-flex;
	align-items: center;
	gap: 4px;
	white-space: nowrap;
}
.lb-period-label {
	min-width: 110px;
	text-align: center;
	font-weight: 600;
}
.lb-doc {
	display: inline-flex;
	align-items: center;
	gap: 6px;
	white-space: nowrap;
	color: var(--ss-muted);
	font-size: var(--ss-fs-sm);
}
.lb-stale {
	opacity: 0.45;
}
.lb-grid-wrap {
	overflow: auto;
	max-height: calc(100vh - 250px);
	background: var(--ss-surface);
	border: 1px solid var(--ss-border);
	border-top: 0;
	border-radius: 0 0 10px 10px;
}
.lb-grid {
	border-collapse: separate;
	border-spacing: 0;
	font-size: var(--ss-fs-sm);
	min-width: 100%;
}
.lb-grid thead th {
	position: sticky;
	top: 0;
	z-index: 2;
	height: 30px;
	background: var(--ss-th-bg, var(--ss-surface-2));
	color: var(--ss-th-fg, var(--ss-muted));
	font-weight: 600;
	text-align: center;
	border-bottom: 1px solid var(--ss-border);
	border-right: 1px solid var(--ss-th-line, var(--ss-border));
}
.lb-grid .lb-name {
	position: sticky;
	left: 0;
	z-index: 1;
	min-width: 200px;
	max-width: 240px;
	padding: 4px 10px;
	text-align: left;
	font-weight: 500;
	background: var(--ss-surface);
	border-right: 1px solid var(--ss-border);
	border-bottom: 1px solid var(--ss-border);
}
.lb-grid thead .lb-name {
	z-index: 3;
	background: var(--ss-th-bg, var(--ss-surface-2));
}
.lb-grid .lb-name small {
	display: block;
	color: var(--ss-muted);
	font-weight: 400;
	overflow: hidden;
	text-overflow: ellipsis;
	white-space: nowrap;
}
.lb-day {
	min-width: 38px;
	line-height: 1.1;
}
.lb-day small {
	display: block;
	font-weight: 400;
	opacity: 0.8;
}
.lb-day.can-click {
	cursor: pointer;
}
.lb-day.is-holiday,
.lb-cell.is-holiday {
	background-color: var(--ss-surface-2);
}
.lb-day.is-holiday small {
	color: var(--ss-text-danger, #be123c);
	opacity: 1;
	font-weight: 600;
}
.lb-day.is-today {
	box-shadow: inset 0 -2px 0 var(--ss-brand);
}
.lb-day.is-future {
	opacity: 0.5;
}
.lb-cell {
	height: 28px;
	padding: 0;
	border-right: 1px solid var(--ss-border);
	border-bottom: 1px solid var(--ss-border);
}
.lb-cell input {
	width: 100%;
	height: 28px;
	padding: 0 2px;
	border: 0;
	background: transparent;
	text-align: center;
	font: inherit;
	color: var(--ss-text);
	outline: none;
}
.lb-cell input:focus {
	box-shadow: inset 0 0 0 2px var(--ss-brand);
	background: var(--ss-surface);
}
.lb-cell input:disabled {
	color: var(--ss-muted);
}
.lb-cell.is-ot input {
	font-weight: 700;
}
.lb-cell.is-changed {
	background: var(--ss-brand-soft);
}
.lb-cell.is-bad input {
	box-shadow: inset 0 0 0 2px #be123c;
}
.lb-total,
.lb-money {
	padding: 0 8px;
	text-align: right;
	white-space: nowrap;
	border-bottom: 1px solid var(--ss-border);
	font-variant-numeric: tabular-nums;
}
.lb-grid thead .lb-total,
.lb-grid thead .lb-money {
	text-align: center;
}
.lb-total {
	min-width: 44px;
}
.lb-money {
	min-width: 90px;
}
.lb-legend {
	margin: 8px 0 0;
	font-size: var(--ss-fs-sm);
}
.lb-bar-note {
	align-self: center;
	font-size: var(--ss-fs-sm);
}
.lb-team th,
.lb-team td {
	background: var(--ss-surface-2);
}
.lb-grid .lb-team .lb-name {
	cursor: pointer;
	background: var(--ss-surface-2);
}
.lb-team-name {
	display: flex;
	align-items: center;
	gap: 6px;
	min-width: 0;
	color: var(--ss-text);
}
.lb-team-name b {
	min-width: 0;
	overflow: hidden;
	text-overflow: ellipsis;
	white-space: nowrap;
}
.lb-team-cell input {
	font-weight: 700;
}
.lb-team-cell input::placeholder {
	color: var(--ss-muted);
	font-weight: 400;
	opacity: 0.7;
}
.lb-mobile-head {
	display: flex;
	flex-direction: column;
	gap: 8px;
	margin-bottom: 8px;
}
.lb-mobile-head .lb-period {
	justify-content: space-between;
}
.lb-team-switch {
	display: flex;
	align-items: center;
	gap: 8px;
	min-width: 0;
}
.lb-idle {
	background: var(--tone-rose);
	color: #fff;
}
.lb-team-list {
	display: flex;
	flex-direction: column;
	gap: 2px;
	margin-top: 8px;
}
.lb-team-option {
	display: flex;
	align-items: center;
	gap: 8px;
	padding: 10px 12px;
	border: 0;
	border-radius: 10px;
	background: transparent;
	color: var(--ss-text);
	font: inherit;
	text-align: left;
	cursor: pointer;
}
.lb-team-option > :first-child {
	flex: 1;
	min-width: 0;
	overflow: hidden;
	text-overflow: ellipsis;
	white-space: nowrap;
}
.lb-team-option:hover {
	background: var(--ss-surface-2);
}
.lb-team-option.is-active {
	background: var(--ss-brand-soft);
	color: var(--ss-brand);
	font-weight: 600;
}
.lb-edit-worker {
	align-self: flex-start;
	display: inline-flex;
	align-items: center;
	gap: 4px;
}
.lb-mobile-actions {
	display: flex;
	align-items: center;
	justify-content: flex-end;
	gap: 8px;
}
.lb-mobile-actions .lb-doc {
	margin-right: auto;
}
.lb-mobile-team {
	display: flex;
	align-items: center;
	justify-content: space-between;
}
.lb-grid tbody .lb-name.is-link {
	cursor: pointer;
}
.lb-grid tbody .lb-name.is-link:hover .ss-cell-main {
	color: var(--ss-brand);
	text-decoration: underline;
}
.lb-card-name {
	padding: 0;
	border: 0;
	background: none;
	text-align: left;
	font: inherit;
	color: inherit;
}
.lb-detail {
	display: flex;
	flex-direction: column;
	gap: 10px;
}
.lb-pay {
	display: grid;
	grid-template-columns: 1fr auto;
	gap: 6px 16px;
	margin: 0;
}
.lb-pay dt {
	color: var(--ss-muted);
	font-weight: 400;
}
.lb-pay dd {
	margin: 0;
	text-align: right;
	font-variant-numeric: tabular-nums;
}
.lb-pay .is-total {
	color: var(--ss-text);
	font-weight: 700;
	border-top: 1px solid var(--ss-border);
	padding-top: 6px;
}
.lb-small {
	margin: 0;
	font-size: var(--ss-fs-sm);
}
.lb-mobile-day {
	display: flex;
	align-items: center;
	gap: 8px;
	margin: 8px 0;
}
.lb-mobile-day > :nth-child(2) {
	flex: 1;
	min-width: 0;
}
.lb-mobile-tools {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: 8px;
	margin-bottom: 8px;
}
.lb-card {
	display: flex;
	flex-direction: column;
	gap: 8px;
}
.lb-card.is-changed {
	border-color: var(--ss-brand);
}
.lb-card-input {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: 8px;
	flex-wrap: wrap;
}
</style>
