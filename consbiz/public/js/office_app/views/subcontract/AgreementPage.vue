<!-- สัญญาจ้างเหมาช่วง 1 หน้า (ต้นแบบ BOQ: หัวแท็บ + ปุ่มขวา) ร่าง = แก้ได้, Submit แล้ว = ดู + สร้าง PO / จ่ายเงินล่วงหน้า / ใบเบิกงวด
     / ใบงานเพิ่ม / ปิดสัญญา (ไม่มีงานลด: งานจบต่ำกว่าสัญญาหรือ ผรม. ไม่ทำต่อ = ปิดสัญญา ระบบปิด PO ให้)
     รายการงานและงวดงานแก้ทีละแถวใน sheet API consbiz/subcontract_app.py -->
<template>
	<div>
		<TopBar :title="title" :subtitle="doc?.supplier_name" back_to="agreements" />

		<div class="ss-content">
			<div v-if="doc" class="ss-list-head">
				<StatusTabs v-model="tab" :options="tabs" />
				<div class="ss-list-tools">
					<a
						v-if="doc.name"
						class="ss-icon-btn"
						:href="desk_url('Subcontract Agreement', doc.name)"
						title="เปิดในระบบเต็ม"
						aria-label="เปิดในระบบเต็ม"
						><Icon name="external" :size="17"
					/></a>
					<template v-if="editable">
						<button
							v-if="view.can_delete && doc.name"
							type="button"
							class="ss-btn ss-btn--ghost-danger ss-list-create"
							:disabled="busy"
							@click="deleting = true"
						>
							ลบ
						</button>
						<button
							v-if="view.can_submit && doc.name"
							type="button"
							class="ss-btn ss-btn--soft ss-list-create"
							:disabled="busy || dirty"
							:title="dirty ? 'บันทึกก่อน Submit' : ''"
							@click="confirm_submit = true"
						>
							Submit
						</button>
						<button
							type="button"
							class="ss-btn ss-btn--primary ss-list-create"
							:disabled="busy || !dirty"
							@click="save()"
						>
							<Icon name="save" :size="18" /> <span>บันทึก</span>
						</button>
					</template>
					<template v-else>
						<button
							v-if="view.can_cancel"
							type="button"
							class="ss-btn ss-btn--ghost-danger ss-list-create"
							:disabled="busy"
							@click="confirm_cancel = true"
						>
							ยกเลิก
						</button>
						<button
							v-if="view.can_close"
							type="button"
							class="ss-btn ss-btn--ghost-danger ss-list-create"
							:disabled="busy"
							@click="closing = { reason: '' }"
						>
							ปิดสัญญา
						</button>
						<button
							v-if="view.can_reopen"
							type="button"
							class="ss-btn ss-btn--soft ss-list-create"
							:disabled="busy"
							@click="confirm_reopen = true"
						>
							เปิดสัญญาอีกครั้ง
						</button>
						<button
							v-if="view.can_share_link"
							type="button"
							class="ss-btn ss-btn--soft ss-list-create"
							:disabled="busy"
							@click="open_link"
						>
							ลิงก์ผู้รับเหมา
						</button>
						<button
							v-if="view.can_vary"
							type="button"
							class="ss-btn ss-btn--soft ss-list-create"
							:disabled="busy"
							@click="go('variation', { name: 'new', agreement: doc.name })"
						>
							ใบงานเพิ่ม
						</button>
						<button
							v-if="view.can_make_po"
							type="button"
							class="ss-btn ss-btn--soft ss-list-create"
							:disabled="busy"
							@click="action('purchase_order')"
						>
							สร้างใบสั่งซื้อ (PO)
						</button>
						<button
							v-if="view.can_pay_advance"
							type="button"
							class="ss-btn ss-btn--soft ss-list-create"
							:disabled="busy"
							@click="action('advance')"
						>
							จ่ายเงินล่วงหน้า
						</button>
						<button
							v-if="view.can_claim"
							type="button"
							class="ss-btn ss-btn--primary ss-list-create"
							@click="go('claim', { name: 'new', agreement: doc.name })"
						>
							<Icon name="plus" :size="18" :stroke="2.6" /> <span>ใบเบิกงวด</span>
						</button>
					</template>
				</div>
			</div>

			<Skeleton v-if="!doc" :rows="6" />
			<template v-else>
				<!-- ข้อมูลสัญญา -->
				<section v-if="tab === 'main'" class="ss-card ss-form">
					<div v-if="!editable" class="ss-doc-head-top">
						<span class="ss-tag" :class="`tone-${doc.status_tone}`">{{
							doc.status_label
						}}</span>
						<span class="ss-doc-date">{{ doc.name }}</span>
					</div>
					<label class="ss-field">
						<span class="ss-field-label">งานที่จ้าง<em>*</em></span>
						<input v-model="doc.title" class="ss-input" :disabled="!editable" />
					</label>
					<div class="ss-form-row">
						<Picker
							v-model="doc.supplier"
							label="ผู้รับเหมาช่วง"
							:display_value="doc.supplier_name"
							:remote_fn="(q) => search('Supplier', q)"
							:class="{ 'is-locked': !editable }"
							required
							@select="(o) => (doc.supplier_name = o?.label)"
						/>
						<Picker
							v-model="doc.project"
							label="โครงการ"
							:display_value="doc.project_name || doc.project"
							:remote_fn="(q) => search('Project', q)"
							:class="{ 'is-locked': !editable }"
							required
							@select="on_project"
						/>
					</div>
					<div class="ss-form-row">
						<label class="ss-field">
							<span class="ss-field-label">เลขที่สัญญา</span>
							<input
								v-model="doc.contract_no"
								class="ss-input"
								:disabled="!editable"
							/>
						</label>
						<label class="ss-field">
							<span class="ss-field-label">วันทำสัญญา<em>*</em></span>
							<DateInput
								v-model="doc.contract_date"
								label="วันทำสัญญา"
								:disabled="!editable"
							/>
						</label>
					</div>
					<div class="ss-form-row">
						<label class="ss-field">
							<span class="ss-field-label">วันเริ่มงาน</span>
							<DateInput
								v-model="doc.start_date"
								label="วันเริ่มงาน"
								clearable
								:disabled="!editable"
							/>
						</label>
						<label class="ss-field">
							<span class="ss-field-label">วันสิ้นสุดสัญญา</span>
							<DateInput
								v-model="doc.end_date"
								label="วันสิ้นสุดสัญญา"
								clearable
								:disabled="!editable"
							/>
						</label>
					</div>
					<div class="ss-field">
						<span class="ss-field-label">วิธีเบิก</span>
						<Segmented
							v-if="editable"
							v-model="doc.billing_method"
							:options="BILLING_METHODS"
						/>
						<b v-else>{{ billing_label(doc.billing_method) }}</b>
					</div>

					<h2 class="ss-section-title">เงื่อนไขการจ่ายเงิน</h2>
					<div class="ss-form-row">
						<label v-for="f in PERCENTS" :key="f.field" class="ss-field">
							<span class="ss-field-label">{{ f.label }}</span>
							<input
								v-model.number="doc[f.field]"
								class="ss-input"
								type="number"
								inputmode="decimal"
								min="0"
								max="100"
								:placeholder="f.placeholder"
								:disabled="!editable"
							/>
						</label>
					</div>
					<div class="ss-form-row">
						<label class="ss-field">
							<span class="ss-field-label">ค่าปรับต่อวัน</span>
							<MoneyInput
								v-model="doc.penalty_per_day"
								class="ss-input"
								:disabled="!editable"
							/>
						</label>
						<label class="ss-field">
							<span class="ss-field-label">ระยะรับประกันผลงาน (วัน)</span>
							<input
								v-model.number="doc.warranty_days"
								class="ss-input"
								type="number"
								inputmode="numeric"
								min="0"
								:disabled="!editable"
							/>
						</label>
					</div>
					<label class="ss-field">
						<span class="ss-field-label">หมายเหตุ</span>
						<textarea
							v-model="doc.remarks"
							class="ss-input"
							rows="2"
							:disabled="!editable"
						></textarea>
					</label>

					<div class="ss-facts ss-facts--grid">
						<div v-for="f in facts" :key="f.label" class="ss-fact">
							<span>{{ f.label }}</span
							><b>{{ f.value }}</b>
						</div>
					</div>
				</section>

				<!-- รายการงาน -->
				<section v-else-if="tab === 'items'" class="ss-card">
					<div class="ss-table-wrap">
						<table class="ss-table ss-table--list">
							<thead>
								<tr>
									<th>WBS</th>
									<th>รายการ</th>
									<th class="is-num">ปริมาณ</th>
									<th>หน่วย</th>
									<th class="is-num">ราคา/หน่วย</th>
									<th class="is-num">มูลค่า</th>
									<th v-if="!editable" class="is-num">เบิกแล้ว</th>
								</tr>
							</thead>
							<tbody>
								<template v-for="(r, i) in doc.items" :key="r._key">
									<!-- งานเพิ่มแนบท้าย: หัวกลุ่มตามใบงานเพิ่ม (แถวงานหลักอยู่ก่อนเสมอ) -->
									<tr
										v-if="
											r.variation &&
											r.variation !== doc.items[i - 1]?.variation
										"
										class="is-static"
									>
										<td :colspan="editable ? 6 : 7">
											<button
												type="button"
												class="ss-link"
												@click.stop="
													go('variation', { name: r.variation })
												"
											>
												<b>งานเพิ่ม (แนบท้าย) {{ r.variation }}</b>
											</button>
										</td>
									</tr>
									<tr
										:class="{ 'is-static': !editable }"
										@click="editable && edit_row('items', r)"
									>
										<td class="col-nowrap">{{ r.wbs || "—" }}</td>
										<td>{{ r.item_name }}</td>
										<td class="is-num">{{ num(r.qty) }}</td>
										<td>{{ r.uom || "" }}</td>
										<td class="is-num">{{ money(r.rate) }}</td>
										<td class="is-num">
											<b>{{ money(row_amount(r)) }}</b>
										</td>
										<td v-if="!editable" class="is-num">
											{{ num(r.claimed_qty) }}
											<small>({{ pct(r.claimed_qty, r.qty) }}%)</small>
										</td>
									</tr>
								</template>
								<tr v-if="!doc.items.length">
									<td :colspan="editable ? 6 : 7" class="ss-muted">
										ยังไม่มีรายการ
									</td>
								</tr>
							</tbody>
							<tfoot>
								<tr>
									<td colspan="5"><b>มูลค่าสัญญา (ก่อน VAT)</b></td>
									<td class="is-num">
										<b>{{ money(total) }}</b>
									</td>
									<td v-if="!editable"></td>
								</tr>
							</tfoot>
						</table>
					</div>
					<button
						v-if="editable"
						type="button"
						class="ss-btn ss-btn--soft"
						@click="new_row('items')"
					>
						<Icon name="plus" :size="16" /> เพิ่มรายการ
					</button>
				</section>

				<!-- งวดงาน -->
				<section v-else-if="tab === 'milestones'" class="ss-card">
					<div class="ss-table-wrap">
						<table class="ss-table ss-table--list">
							<thead>
								<tr>
									<th>งวด</th>
									<th class="is-num">%</th>
									<th class="is-num">มูลค่า</th>
									<th>กำหนด</th>
									<th>เงื่อนไขการเบิก</th>
									<th v-if="!editable">ใบเบิก</th>
								</tr>
							</thead>
							<tbody>
								<tr
									v-for="(m, i) in doc.milestones"
									:key="m._key"
									:class="{ 'is-static': !editable }"
									@click="editable && edit_row('milestones', m)"
								>
									<td>{{ i + 1 }}. {{ m.description }}</td>
									<td class="is-num">{{ num(m.percent) }}</td>
									<td class="is-num">
										{{ money((main_total * (Number(m.percent) || 0)) / 100) }}
									</td>
									<td>
										{{
											m.target_date
												? thai_date(m.target_date, { year: true })
												: "—"
										}}
									</td>
									<td>{{ m.condition || "" }}</td>
									<td v-if="!editable">
										<button
											v-if="m.subcontract_claim"
											type="button"
											class="ss-link"
											@click.stop="
												go('claim', { name: m.subcontract_claim })
											"
										>
											{{ m.subcontract_claim }}
										</button>
										<span v-else class="ss-muted">ยังไม่เบิก</span>
									</td>
								</tr>
							</tbody>
							<tfoot>
								<tr>
									<td><b>รวม</b></td>
									<td
										class="is-num"
										:class="{
											'is-danger': Math.abs(milestone_percent - 100) > 0.01,
										}"
									>
										<b>{{ num(milestone_percent) }}%</b>
									</td>
									<td colspan="4"></td>
								</tr>
							</tfoot>
						</table>
					</div>
					<button
						v-if="editable"
						type="button"
						class="ss-btn ss-btn--soft"
						@click="new_row('milestones')"
					>
						<Icon name="plus" :size="16" /> เพิ่มงวด
					</button>
				</section>

				<!-- ใบงานเพิ่ม -->
				<section v-else-if="tab === 'variations'" class="ss-card">
					<Empty
						v-if="!view.variations?.length"
						icon="plus"
						title="ยังไม่มีใบงานเพิ่ม"
					/>
					<div v-else class="ss-list">
						<button
							v-for="v in view.variations"
							:key="v.name"
							type="button"
							class="ss-card"
							@click="go('variation', { name: v.name })"
						>
							<div class="ss-card-head">
								<span class="ss-card-main">
									<span class="ss-card-title"
										>แก้ไขครั้งที่ {{ v.revision_no }}</span
									>
									<span class="ss-card-meta"
										>{{ v.name }} ·
										{{ thai_date(v.posting_date, { year: true }) }}</span
									>
								</span>
								<span class="ss-qty"
									><b>+{{ money(v.addition_amount) }}</b></span
								>
								<span class="ss-tag" :class="`tone-${v.status_tone}`">{{
									v.status_label
								}}</span>
							</div>
						</button>
					</div>
				</section>

				<!-- ใบเบิก -->
				<section v-else class="ss-card">
					<Empty v-if="!view.claims?.length" icon="receive" title="ยังไม่มีใบเบิก" />
					<div v-else class="ss-list">
						<button
							v-for="c in view.claims"
							:key="c.name"
							type="button"
							class="ss-card"
							@click="go('claim', { name: c.name })"
						>
							<div class="ss-card-head">
								<span class="ss-card-main">
									<span class="ss-card-title">งวดที่ {{ c.claim_no }}</span>
									<span class="ss-card-meta"
										>{{ c.name }} ·
										{{ thai_date(c.posting_date, { year: true }) }}</span
									>
								</span>
								<span class="ss-qty"
									><b>{{ money(c.gross_amount) }}</b></span
								>
								<span class="ss-tag" :class="`tone-${c.status_tone}`">{{
									c.status_label
								}}</span>
							</div>
						</button>
					</div>
				</section>
			</template>
		</div>

		<!-- แก้แถว -->
		<Sheet :open="!!row" :title="row?._new ? 'เพิ่มแถว' : 'แก้แถว'" @close="row = null">
			<div v-if="row" class="ss-form">
				<template v-if="row._table === 'items'">
					<Picker
						v-model="row.wbs"
						label="งานในแผน (WBS)"
						:options="wbs"
						clearable
						empty_text="โครงการนี้ยังไม่มีแผนงาน"
						@select="pick_wbs"
					/>
					<label class="ss-field">
						<span class="ss-field-label">รายการ<em>*</em></span>
						<input v-model="row.item_name" class="ss-input" />
					</label>
					<div class="ss-form-row">
						<label class="ss-field">
							<span class="ss-field-label">ปริมาณ<em>*</em></span>
							<input
								v-model.number="row.qty"
								class="ss-input"
								type="number"
								inputmode="decimal"
								min="0"
							/>
						</label>
						<Picker
							v-model="row.uom"
							label="หน่วย"
							:display_value="row.uom"
							:remote_fn="(q) => search('UOM', q)"
							clearable
						/>
					</div>
					<label class="ss-field">
						<span class="ss-field-label">ราคาต่อหน่วย</span>
						<MoneyInput v-model="row.rate" class="ss-input" />
					</label>
				</template>
				<template v-else>
					<label class="ss-field">
						<span class="ss-field-label">งวดงาน<em>*</em></span>
						<input
							v-model="row.description"
							class="ss-input"
							placeholder="เช่น งวดที่ 1 งานฐานราก"
						/>
					</label>
					<div class="ss-form-row">
						<label class="ss-field">
							<span class="ss-field-label">% ของมูลค่าสัญญา<em>*</em></span>
							<input
								v-model.number="row.percent"
								class="ss-input"
								type="number"
								inputmode="decimal"
								min="0"
								max="100"
							/>
						</label>
						<label class="ss-field">
							<span class="ss-field-label">กำหนด</span>
							<DateInput v-model="row.target_date" label="กำหนด" clearable />
						</label>
					</div>
					<label class="ss-field">
						<span class="ss-field-label">เงื่อนไขการเบิก</span>
						<input
							v-model="row.condition"
							class="ss-input"
							placeholder="เช่น เทฐานรากครบทุกต้น"
						/>
					</label>
				</template>
			</div>
			<template #footer>
				<div class="ss-sheet-actions">
					<button
						v-if="!row?._new"
						type="button"
						class="ss-btn ss-btn--ghost-danger ss-btn--lg"
						@click="remove_row"
					>
						ลบ
					</button>
					<button
						type="button"
						class="ss-btn ss-btn--primary ss-btn--lg ss-grow"
						@click="save_row"
					>
						ตกลง
					</button>
				</div>
			</template>
		</Sheet>

		<Sheet :open="!!link" title="ลิงก์ผู้รับเหมา" :subtitle="doc?.supplier_name" @close="link = null">
			<p class="ss-muted">
				ส่งลิงก์นี้ให้ผู้รับเหมา (เช่น ทาง LINE) เปิดแล้วดูสัญญานี้และส่งใบเบิกงวดได้โดยไม่ต้องเข้าสู่ระบบ
				ใช้ได้จนกว่าจะปิดสัญญา ใครได้ลิงก์ไปก็ใช้ได้ ถ้าลิงก์หลุดให้กด "สร้างลิงก์ใหม่"
			</p>
			<label v-if="link" class="ss-field">
				<span class="ss-field-label">ลิงก์</span>
				<input class="ss-input" :value="link.url" readonly @focus="$event.target.select()" />
			</label>
			<template #footer>
				<button
					v-if="link?.can_reset"
					type="button"
					class="ss-btn ss-btn--ghost-danger ss-btn--lg"
					:disabled="busy"
					@click="reset_link"
				>
					สร้างลิงก์ใหม่
				</button>
				<button
					type="button"
					class="ss-btn ss-btn--primary ss-btn--block ss-btn--lg"
					:disabled="!link?.url"
					@click="copy_link"
				>
					<Icon name="copy" :size="18" /> <span>คัดลอกลิงก์</span>
				</button>
			</template>
		</Sheet>
		<Sheet :open="!!closing" title="ปิดสัญญา" :subtitle="doc?.name" @close="closing = null">
			<p class="ss-note-line">
				ใช้เมื่องานจบต่ำกว่าสัญญาหรือผู้รับเหมาไม่ทำต่อ (ไม่ต้องทำงานลด)
				หลังปิดเบิกและทำใบงานเพิ่มไม่ได้ ระบบปิดใบสั่งซื้อ (PO) ให้
				และปริมาณที่ยังไม่เบิกคืนให้งานในแผน
			</p>
			<div v-if="closing" class="ss-facts ss-facts--grid">
				<div class="ss-fact">
					<span>มูลค่าสัญญา</span><b>{{ money(doc.total_amount) }}</b>
				</div>
				<div class="ss-fact">
					<span>เบิกแล้ว</span><b>{{ money(doc.claimed_amount) }}</b>
				</div>
			</div>
			<label v-if="closing" class="ss-field">
				<span class="ss-field-label">เหตุผล<em>*</em></span>
				<textarea
					v-model="closing.reason"
					class="ss-input"
					rows="3"
					placeholder="เช่น งานจบตามที่วัดได้จริง / ผู้รับเหมาทิ้งงาน"
				></textarea>
			</label>
			<template #footer>
				<button
					type="button"
					class="ss-btn ss-btn--danger ss-btn--block ss-btn--lg"
					:disabled="busy || !closing?.reason?.trim()"
					@click="close_agreement"
				>
					ยืนยันปิดสัญญา
				</button>
			</template>
		</Sheet>
		<Sheet
			:open="confirm_reopen"
			title="เปิดสัญญาอีกครั้ง"
			:subtitle="doc?.name"
			@close="confirm_reopen = false"
		>
			<p class="ss-note-line">
				สัญญากลับมาเบิกได้ และเปิดใบสั่งซื้อ (PO) อีกครั้ง
				ปริมาณเต็มสัญญาต้องยังไม่เกินแผนงาน
			</p>
			<template #footer>
				<button
					type="button"
					class="ss-btn ss-btn--primary ss-btn--block ss-btn--lg"
					:disabled="busy"
					@click="reopen_agreement"
				>
					ยืนยันเปิดสัญญา
				</button>
			</template>
		</Sheet>
		<Sheet
			:open="confirm_submit"
			title="Submit สัญญา"
			:subtitle="doc?.name"
			@close="confirm_submit = false"
		>
			<p class="ss-note-line">
				Submit แล้วแก้สัญญาไม่ได้ (ต้องยกเลิกแล้วแก้ไขฉบับใหม่) จากนั้นสร้าง PO
				และใบเบิกงวดได้
			</p>
			<template #footer>
				<button
					type="button"
					class="ss-btn ss-btn--primary ss-btn--block ss-btn--lg"
					:disabled="busy"
					@click="submit"
				>
					ยืนยัน Submit
				</button>
			</template>
		</Sheet>
		<Sheet
			:open="confirm_cancel"
			title="ยกเลิกสัญญา"
			:subtitle="doc?.name"
			@close="confirm_cancel = false"
		>
			<p class="ss-note-line">ต้องยกเลิกใบเบิกและ PO ของสัญญานี้ก่อน</p>
			<template #footer>
				<button
					type="button"
					class="ss-btn ss-btn--danger ss-btn--block ss-btn--lg"
					:disabled="busy"
					@click="cancel"
				>
					ยืนยันยกเลิก
				</button>
			</template>
		</Sheet>
		<DeleteSheet
			:open="deleting"
			label="สัญญา"
			:name="doc?.name"
			:method="`${API}.delete_doc`"
			:args="{ kind: 'agreements', name: doc?.name }"
			@close="deleting = false"
			@deleted="go('agreements', {}, { replace: true })"
		/>
	</div>
</template>

<script setup>
import { computed, inject, ref, watch } from "vue";
import DateInput from "../../../shared/components/DateInput.vue";
import DeleteSheet from "../../../shared/components/DeleteSheet.vue";
import Empty from "../../../shared/components/Empty.vue";
import Icon from "../../../shared/components/Icon.vue";
import MoneyInput from "../../../shared/components/MoneyInput.vue";
import Picker from "../../../shared/components/Picker.vue";
import Segmented from "../../../shared/components/Segmented.vue";
import Sheet from "../../../shared/components/Sheet.vue";
import Skeleton from "../../../shared/components/Skeleton.vue";
import StatusTabs from "../../../shared/components/StatusTabs.vue";
import TopBar from "../../../shared/components/TopBar.vue";
import {
	back,
	call,
	celebrate,
	desk_url,
	go,
	money,
	num,
	post,
	scope_args,
	show_error,
	state,
	thai_date,
	toast,
	today,
} from "../../../shared/api.js";
import { API, BILLING_METHODS, billing_label } from "./kinds.js";

const PERCENTS = [
	{ field: "retention_percent", label: "เงินประกันผลงาน (%)" },
	{
		field: "retention_cap_percent",
		label: "เพดานเงินประกัน (% สัญญา)",
		placeholder: "ไม่มีเพดาน",
	},
	{ field: "wht_percent", label: "หัก ณ ที่จ่าย (%)" },
	{ field: "advance_percent", label: "เงินล่วงหน้า (%)" },
	{ field: "advance_recovery_percent", label: "หักคืนเงินล่วงหน้าต่องวด (%)" },
];
const DEFAULTS = {
	billing_method: "Measured",
	retention_percent: 5,
	wht_percent: 3,
	items: [],
	milestones: [],
};

const reload_summary = inject("reload_summary");
const params = state.route.params;
let key = 0;
const view = ref({});
const doc = ref(null);
const saved = ref("");
const tab = ref("main");
const busy = ref(false);
const row = ref(null);
const wbs = ref([]);
const deleting = ref(false);
const confirm_submit = ref(false);
const confirm_cancel = ref(false);
const closing = ref(null);
// ลิงก์ผู้รับเหมา (แอป /contractor ไม่ต้อง login) {path, url, valid, can_reset} url = โดเมนที่เปิดอยู่ + path
const link = ref(null);
const with_url = (info) => ({ ...info, url: info.path ? location.origin + info.path : "" });
async function open_link() {
	try {
		link.value = with_url(await post(`${API}.contractor_link`, { name: doc.value.name }));
	} catch (e) {
		show_error(e);
	}
}
async function reset_link() {
	busy.value = true;
	try {
		link.value = with_url(await post(`${API}.reset_contractor_link`, { name: doc.value.name }));
		toast("สร้างลิงก์ใหม่แล้ว ลิงก์เดิมใช้ไม่ได้แล้ว", "success");
	} catch (e) {
		show_error(e);
	} finally {
		busy.value = false;
	}
}
async function copy_link() {
	try {
		await navigator.clipboard.writeText(link.value.url);
		toast("คัดลอกลิงก์แล้ว", "success");
	} catch {
		// http (ไม่ใช่ https) ใช้ clipboard API ไม่ได้: ให้ผู้ใช้คัดลอกจากช่องเอง
		toast("คัดลอกอัตโนมัติไม่ได้ กดค้างที่ช่องลิงก์แล้วคัดลอกเอง", "warning");
	}
}
const confirm_reopen = ref(false);

const editable = computed(() => !!doc.value && (!doc.value.name || view.value.can_edit));
const title = computed(() => (doc.value?.name ? doc.value.title || doc.value.name : "สัญญาใหม่"));
const row_amount = (r) => (Number(r.qty) || 0) * (Number(r.rate) || 0);
const total = computed(() => (doc.value?.items || []).reduce((s, r) => s + row_amount(r), 0));
// งานหลัก (ไม่รวมงานเพิ่มแนบท้าย) = ฐานของ % งวดงาน
const main_total = computed(() =>
	(doc.value?.items || []).filter((r) => !r.variation).reduce((s, r) => s + row_amount(r), 0)
);
const milestone_percent = computed(() =>
	(doc.value?.milestones || []).reduce((s, m) => s + (Number(m.percent) || 0), 0)
);
const pct = (a, b) => (Number(b) ? Math.round(((Number(a) || 0) / Number(b)) * 100) : 0);
const payload = () => JSON.stringify(strip(doc.value));
const dirty = computed(() => !!doc.value && payload() !== saved.value);

const tabs = computed(() => [
	{ value: "main", label: "สัญญา" },
	{ value: "items", label: "รายการงาน", count: doc.value?.items.length },
	...(doc.value?.billing_method === "Milestone"
		? [{ value: "milestones", label: "งวดงาน", count: doc.value?.milestones.length }]
		: []),
	...(doc.value?.name && doc.value.docstatus > 0
		? [{ value: "claims", label: "ใบเบิก", count: view.value.claims?.length }]
		: []),
	...(doc.value?.name && doc.value.docstatus > 0 && view.value.variations
		? [{ value: "variations", label: "งานเพิ่ม", count: view.value.variations.length }]
		: []),
]);

// PO ที่แก้ตามใบงานเพิ่ม: ฝ่ายจัดซื้อส่งฉบับใหม่ให้ผู้รับเหมาแล้วหรือยัง
const po_note = computed(() => {
	const r = view.value.po_revision;
	if (!r) return "";
	return r.pending
		? ` Rev.${r.revision} · รอฝ่ายจัดซื้อส่งผู้รับเหมา`
		: ` Rev.${r.revision} · ส่งแล้ว${r.sent_by_name ? ` (${r.sent_by_name})` : ""}`;
});
const facts = computed(() => {
	const d = doc.value;
	const advance = (total.value * (Number(d.advance_percent) || 0)) / 100;
	return [
		["มูลค่าสัญญา (ก่อน VAT)", money(total.value)],
		...(d.revision
			? [
					["มูลค่างานหลัก", money(d.original_amount)],
					[`งานเพิ่มแนบท้าย (${d.revision} ครั้ง)`, money(d.variation_amount)],
			  ]
			: []),
		...(d.status === "Closed"
			? [
					["ปิดสัญญาเมื่อ", thai_date(d.closed_on, { year: true })],
					["เหตุผลที่ปิด", d.close_reason],
					...(d.warranty_end
						? [["สิ้นสุดรับประกันผลงาน", thai_date(d.warranty_end, { year: true })]]
						: []),
			  ]
			: []),
		["เงินล่วงหน้า", money(advance)],
		...(d.docstatus === 1
			? [
					[
						"เบิกแล้ว",
						`${money(d.claimed_amount)} (${Math.round(d.progress_percent || 0)}%)`,
					],
					["เงินประกันที่หักไว้", money(d.retention_held)],
					["จ่ายเงินล่วงหน้าแล้ว", money(view.value.advance_paid)],
					["หักคืนเงินล่วงหน้าแล้ว", money(d.advance_recovered)],
					["ค่าปรับรวม", money(d.penalty_total)],
					[
						"ใบสั่งซื้อ (PO)",
						d.purchase_order
							? `${d.purchase_order}${view.value.po_status === 0 ? " (ร่าง)" : ""}${
									po_note.value
							  }`
							: "ยังไม่สร้าง",
					],
			  ]
			: []),
	].map(([label, value]) => ({ label, value }));
});

function strip(d) {
	const clean = (rows) => rows.map(({ _key, _new, _table, ...r }) => r);
	return { ...d, items: clean(d.items), milestones: clean(d.milestones) };
}

async function load_wbs() {
	wbs.value = doc.value?.project
		? await call(`${API}.wbs_options`, { project: doc.value.project }).catch(() => [])
		: [];
}
function on_project(option) {
	doc.value.project_name = option?.label;
	load_wbs();
}
const search = (doctype, txt) => call(`${API}.search`, { doctype, txt });
// เลือกงานในแผน: เติมชื่อ/หน่วยตามแผน (การตรวจไม่ให้จ้างเกินแผนเทียบเฉพาะแถวที่หน่วยตรงกัน)
function pick_wbs(option) {
	if (!option) return;
	if (!row.value.item_name) row.value.item_name = option.label.replace(/^\S+\s/, "");
	if (!row.value.uom && option.uom) row.value.uom = option.uom;
}

function new_row(table) {
	row.value =
		table === "items"
			? {
					_table: table,
					_new: true,
					_key: ++key,
					wbs: null,
					item_name: "",
					uom: null,
					qty: null,
					rate: null,
			  }
			: {
					_table: table,
					_new: true,
					_key: ++key,
					description: "",
					percent: null,
					target_date: null,
					condition: "",
			  };
}
function edit_row(table, r) {
	row.value = { ...r, _table: table, _new: false };
}
function save_row() {
	const r = row.value;
	if (r._table === "items" && (!r.item_name?.trim() || !(Number(r.qty) > 0)))
		return show_error(new Error("กรอกรายการและปริมาณ"));
	if (r._table === "milestones" && (!r.description?.trim() || !(Number(r.percent) > 0)))
		return show_error(new Error("กรอกชื่องวดและ %"));
	const list = doc.value[r._table];
	const clean = { ...r, _new: false };
	const index = list.findIndex((x) => x._key === r._key);
	if (index >= 0) list.splice(index, 1, clean);
	else list.push(clean);
	row.value = null;
}
function remove_row() {
	doc.value[row.value._table] = doc.value[row.value._table].filter(
		(x) => x._key !== row.value._key
	);
	row.value = null;
}

function apply(result) {
	view.value = result;
	const d = result.doc;
	d.items = (d.items || []).map((r) => ({ ...r, _key: ++key }));
	d.milestones = (d.milestones || []).map((m) => ({ ...m, _key: ++key }));
	doc.value = d;
	saved.value = payload();
}

async function run(task, message) {
	busy.value = true;
	try {
		const result = await task();
		reload_summary();
		if (message) await celebrate(message, result?.doc?.name || doc.value.name);
		return result;
	} catch (error) {
		show_error(error);
	} finally {
		busy.value = false;
	}
}

async function save(submit = 0) {
	const result = await run(
		() => post(`${API}.save_agreement`, { data: payload(), submit }),
		"บันทึกแล้ว"
	);
	if (!result) return;
	const is_new = !doc.value.name;
	apply(result);
	if (is_new) go("agreement", { name: result.doc.name }, { replace: true });
}
async function submit() {
	const result = await run(
		() => post(`${API}.submit_doc`, { kind: "agreements", name: doc.value.name }),
		"Submit แล้ว"
	);
	if (result) apply(result);
	confirm_submit.value = false;
}
async function cancel() {
	const result = await run(
		() => post(`${API}.cancel_doc`, { kind: "agreements", name: doc.value.name }),
		"ยกเลิกแล้ว"
	);
	if (result) apply(result);
	confirm_cancel.value = false;
}
async function close_agreement() {
	const result = await run(
		() =>
			post(`${API}.close_agreement`, { name: doc.value.name, reason: closing.value.reason }),
		"ปิดสัญญาแล้ว"
	);
	if (result) apply(result);
	closing.value = null;
}
async function reopen_agreement() {
	const result = await run(
		() => post(`${API}.reopen_agreement`, { name: doc.value.name }),
		"เปิดสัญญาแล้ว"
	);
	if (result) apply(result);
	confirm_reopen.value = false;
}
async function action(name) {
	const result = await run(() =>
		post(`${API}.run_action`, { kind: "agreements", name: doc.value.name, action: name })
	);
	if (!result) return;
	apply(result.view);
	await celebrate(`สร้าง ${result.name} แล้ว (ร่าง)`, "เปิดในระบบเต็มเพื่อตรวจและ Submit");
	window.open(desk_url(result.doctype, result.name), "_blank");
}

async function load() {
	try {
		const name = params.name && params.name !== "new" ? params.name : undefined;
		const { company, project } = scope_args();
		const result = await call(`${API}.get_agreement`, { name, company, project });
		if (!name)
			Object.assign(result.doc, {
				...DEFAULTS,
				...pick(result.doc),
				contract_date: today(),
			});
		apply(result);
		load_wbs();
	} catch (error) {
		show_error(error);
		back("agreements");
	}
}
// ค่าที่ server ตั้งให้สัญญาใหม่ (โครงการ/บริษัทตามตัวกรอง) ทับค่าตั้งต้น
const pick = (d) =>
	Object.fromEntries(
		Object.entries(d).filter(([, v]) => v !== null && v !== undefined && v !== "")
	);

watch(
	() => doc.value?.billing_method,
	(method) => method !== "Milestone" && tab.value === "milestones" && (tab.value = "main")
);
load();
</script>
