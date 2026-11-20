<!-- รายละเอียดเอกสารจัดซื้อ/ขาย: หัวเอกสาร, ความคืบหน้า, รายการ, ยอดรวม, เอกสารต้นทาง/ปลายทาง, PDF, ส่งเอกสาร -->
<template>
<div>
		<TopBar :title="config.label" :subtitle="params.name" :back_to="list_view">
			<template #status>
				<span v-if="doc" class="ss-tag" :class="`tone-${doc.status_tone}`">{{ doc.status_label }}</span>
			</template>
			<template #actions>
				<!-- เปิด/ปิด sidebar ขวา (มอบหมาย ไฟล์แนบ ความคิดเห็น ความเคลื่อนไหว) -->
				<button
					v-if="doc"
					type="button"
					class="ss-icon-btn"
					:class="{ 'is-on': side_open }"
					:aria-pressed="side_open"
					aria-label="แผงข้อมูลเอกสาร"
					title="แผงข้อมูลเอกสาร (มอบหมาย ไฟล์แนบ ความคิดเห็น)"
					@click="toggle_side"
				>
					<Icon name="panel-right" :size="19" />
				</button>
			</template>
		</TopBar>

		<div class="ss-content ss-docview">
			<!-- แท็บ (ติดบนจอ) + การ์ดเนื้อหาเป็นชิ้นเดียวกัน (ตกลง 2026-11-18) -->
			<div class="ss-doc-frame">
			<!-- ติดบนจอ: กล่องเหลี่ยมพื้นหน้ารองแถวแท็บ มุมโค้งจึงไม่เห็นเนื้อหาที่เลื่อนผ่าน -->
			<div v-if="doc" class="ss-doc-stick">
				<FormHead
					v-if="doc"
					model-value="main"
					:tabs="[{ value: 'main', label: config.label }]"
					:actions="actions"
					:menu="menu"
					:busy="busy"
					:on-print="print"
				/>
			</div>
			<Skeleton v-if="!doc" :rows="3" />
			<div v-else class="ss-doc-sheet">
				<MiniSteps :steps="doc.steps" />
				<!-- หัวเอกสารแบบการ์ด (ตกลง 2026-11-18): ข้อมูลเอกสาร | รายละเอียดการจัดซื้อ/ขาย เลขที่/สถานะอยู่แถบบน ขั้นตอนอยู่ใต้แท็บ -->
				<div class="ss-doc-cards">
					<section class="ss-doc-card">
						<h2 class="ss-doc-card-title"><Icon name="file" :size="18" /> ข้อมูลเอกสาร</h2>
						<dl class="ss-doc-fields">
							<div class="is-wide">
								<dt>{{ config.party || "เรื่อง" }}</dt>
								<dd>
									<InlineEdit
										v-if="!config.party && edit.title"
										:model-value="doc.title"
										:label="edit.title.label"
										:display="doc.title || doc.name"
										editable
										:save="(v) => save_field('title', v)"
									/>
									<template v-else>{{ doc.party || doc.title || doc.name }}</template>
								</dd>
							</div>
							<div>
								<dt>วันที่เอกสาร</dt>
								<dd>{{ thai_date(doc.date, { year: true }) }}</dd>
							</div>
							<div v-if="doc.po_no && !edit.po_no">
								<dt>เลขที่ใบสั่งซื้อลูกค้า</dt>
								<dd>{{ doc.po_no }}</dd>
							</div>
							<div v-if="doc.bill_no">
								<dt>เลขที่บิลผู้ขาย</dt>
								<dd>{{ doc.bill_no }}</dd>
							</div>
							<div class="is-wide">
								<dt>โครงการ</dt>
								<dd :class="{ 'is-empty': !doc.project }" :title="doc.project_name">
									<template v-if="doc.project"
										>{{ doc.project_name || doc.project }}
										<small>({{ doc.project }})</small></template
									>
									<template v-else>–</template>
								</dd>
							</div>
						</dl>
					</section>
					<section class="ss-doc-card">
						<h2 class="ss-doc-card-title">
							<Icon :name="config.section === 'buy' ? 'cart' : 'briefcase'" :size="18" />
							{{ detail_title }}
						</h2>
						<dl class="ss-doc-fields">
							<div v-if="doc.purpose">
								<dt>วัตถุประสงค์</dt>
								<dd>{{ doc.purpose }}</dd>
							</div>
							<div v-if="doc.due || edit[due_field]">
								<dt>{{ config.due || "วันที่ต้องการ" }}</dt>
								<dd :class="{ 'is-due': overdue }">
									<InlineEdit
										v-if="edit[due_field]"
										fieldtype="Date"
										:model-value="doc.due"
										:label="edit[due_field].label"
										:display="thai_date(doc.due, { year: true })"
										:min="doc.date"
										:apply_label="
											item_date_field === due_field ? 'ใช้วันนี้กับทุกรายการ' : null
										"
										required
										editable
										:save="(v, apply) => save_field(due_field, v, apply)"
									/>
									<template v-else>{{ thai_date(doc.due, { year: true }) }}</template>
								</dd>
							</div>
							<div>
								<dt>{{ is_mr ? "ผู้ขอซื้อ" : "ผู้จัดทำ" }}</dt>
								<dd class="ss-doc-person">
									<Icon name="user" :size="15" />{{ doc.request_by || doc.owner_name }}
								</dd>
							</div>
							<div v-if="is_mr || doc.approval">
								<dt>{{ doc.approval?.words.who || "ผู้อนุมัติ" }}</dt>
								<dd :class="{ 'is-empty': !signer_name }">{{ signer_name || "–" }}</dd>
							</div>
							<!-- ช่องที่แก้ได้หลังส่ง (เลขที่ใบกำกับภาษี, เลขที่ PO ลูกค้า ฯลฯ) ที่ไม่ได้แสดงที่อื่น -->
							<div v-for="f in extra_fields" :key="f.fieldname">
								<dt>{{ f.label }}</dt>
								<dd>
									<InlineEdit
										:model-value="f.value"
										:label="f.label"
										add_label=""
										:fieldtype="f.fieldtype"
										:display="
											f.fieldtype === 'Date' ? thai_date(f.value, { year: true }) : f.value
										"
										editable
										:save="(v) => save_field(f.fieldname, v)"
									/>
								</dd>
							</div>
						</dl>
					</section>
				</div>

				<!-- ขั้นอนุมัติ/ลงนาม (consbiz/doc_approval.py): รออยู่ / ส่งกลับแก้ไข + เหตุผล / ลงนามแล้ว (บันทึกแทน + ไฟล์ที่เซ็น) -->
				<div v-if="approval_banner" class="ss-banner" :class="`tone-${approval_banner.tone}`">
					<Icon :name="approval_banner.icon" :size="22" />
					<div class="ss-grow">
						<div class="ss-banner-title">{{ approval_banner.title }}</div>
						<div class="ss-banner-text">
							{{ approval_banner.text }}
							<template v-if="doc.approval.proof">
								· <a :href="doc.approval.proof" target="_blank">เอกสารที่ลงนาม</a>
							</template>
						</div>
					</div>
				</div>

				<!-- PO ที่แก้ตามใบงานเพิ่ม ผรม.: Rev. ปัจจุบัน + รอส่งผู้รับเหมา (ใครในฝ่ายจัดซื้อก็กดส่งได้) + PDF ฉบับก่อนๆ -->
				<div v-if="doc.revision" class="ss-banner" :class="doc.revision.pending ? 'tone-amber' : 'tone-blue'">
					<Icon :name="doc.revision.pending ? 'alert' : 'check'" :size="22" />
					<div class="ss-grow">
						<div class="ss-banner-title">
							Rev.{{ doc.revision.revision }}
							{{ doc.revision.pending ? "รอส่งฉบับนี้ให้ผู้รับเหมา" : "ส่งผู้รับเหมาแล้ว" }}
						</div>
						<div class="ss-banner-text">
							{{ doc.revision.note || "ฉบับตามสัญญาเดิม" }}
							<template v-if="!doc.revision.pending && doc.revision.sent_by_name">
								· ส่งโดย {{ doc.revision.sent_by_name }}
								{{ thai_date(doc.revision.sent_on, { year: true }) }}
							</template>
							<template v-for="f in doc.revision.snapshots" :key="f.file_url">
								· <a :href="f.file_url" target="_blank">{{ f.file_name }}</a>
							</template>
						</div>
					</div>
					<button
						v-if="doc.revision.can_mark_sent"
						type="button"
						class="ss-btn ss-btn--primary"
						:disabled="busy"
						@click="mark_sent"
					>
						ส่งผู้รับเหมาแล้ว
					</button>
				</div>

				<section class="ss-doc-card ss-doc-card--items">
					<h2 class="ss-doc-card-title">
						<Icon name="layers" :size="18" /> {{ items_title }}
						<span class="ss-count">{{ doc.items.length }}</span>
					</h2>

					<!-- จอกว้าง: ตารางรายการ -->
					<div v-if="wide" class="ss-doc-table-wrap">
						<table class="ss-table ss-table--doc ss-doc-table">
							<thead>
								<tr>
									<th class="is-idx">#</th>
									<th>รายการ</th>
									<th class="is-num">จำนวน</th>
									<th>หน่วย</th>
									<th class="is-num">หน่วยละ</th>
									<th class="is-num">เป็นเงิน</th>
									<th v-if="has_item_date">{{ item_date_head }}</th>
								</tr>
							</thead>
							<tbody>
								<tr v-for="(it, i) in doc.items" :key="i" class="is-static">
									<td class="is-idx">{{ i + 1 }}</td>
									<td class="is-item">
										<b>{{ it.item_name || it.item_code }}</b>
										<small
											>{{ it.item_code
											}}<template v-if="item_progress(it)">
												· {{ item_progress(it) }}</template
											><template v-if="is_mr && it.custom_vat_nocal">
												· ไม่คิดภาษี</template
											></small
										>
										<RichText
											v-if="has_desc(it)"
											:html="it.description"
											class="ss-item-desc"
										/>
									</td>
									<td class="is-num">{{ num(it.qty) }}</td>
									<td>{{ it.uom }}</td>
									<td class="is-num">{{ money(it.rate) }}</td>
									<td class="is-num is-strong">{{ money(it.amount) }}</td>
									<td v-if="has_item_date" class="is-date">
										<InlineEdit
											v-if="item_date_field"
											fieldtype="Date"
											:model-value="it[item_date_field]"
											:label="item_date_label"
											:subtitle="it.item_name || it.item_code"
											:display="thai_date(it[item_date_field], { year: true })"
											:min="doc.date"
											required
											editable
											:save="(v) => save_item(it, v)"
										/>
										<template v-else>{{
											thai_date(it.schedule_date || it.delivery_date, {
												year: true,
											})
										}}</template>
									</td>
								</tr>
							</tbody>
						</table>
					</div>

					<!-- มือถือ: แถวรายการในการ์ด -->
					<div v-else class="ss-doc-lines">
						<div v-for="(it, i) in doc.items" :key="i" class="ss-doc-line">
							<div class="ss-doc-row">
								<span class="ss-doc-title">{{ it.item_name || it.item_code }}</span>
								<b class="ss-doc-money">{{ money(it.amount) }}</b>
							</div>
							<span class="ss-card-meta ss-item-code">{{ it.item_code }}</span>
							<span class="ss-card-meta"
								>{{ num(it.qty) }} {{ it.uom }} × {{ money(it.rate)
								}}<template
									v-if="!item_date_field && (it.schedule_date || it.delivery_date)"
								>
									· ต้องการ
									{{ thai_date(it.schedule_date || it.delivery_date) }}</template
								></span
							>
							<span v-if="item_date_field" class="ss-card-meta"
								>{{ item_date_label }}
								<InlineEdit
									fieldtype="Date"
									:model-value="it[item_date_field]"
									:label="item_date_label"
									:subtitle="it.item_name || it.item_code"
									:display="thai_date(it[item_date_field])"
									:min="doc.date"
									required
									editable
									:save="(v) => save_item(it, v)"
							/></span>
							<RichText
								v-if="has_desc(it)"
								:html="it.description"
								:lines="4"
								class="ss-item-desc"
							/>
							<div v-if="item_progress(it) || it.custom_vat_nocal" class="ss-chips">
								<span v-if="item_progress(it)" class="ss-chip">{{
									item_progress(it)
								}}</span>
								<span v-if="it.custom_vat_nocal" class="ss-chip">ไม่คิดภาษี</span>
							</div>
						</div>
					</div>

					<!-- ใต้ตาราง: ปุ่มของรายการ -->
					<div class="ss-doc-items-foot">
						<button
							type="button"
							class="ss-btn ss-btn--ghost ss-doc-items-btn"
							title="ดาวน์โหลดรายการเป็นไฟล์ Excel (CSV)"
							@click="export_items"
						>
							<Icon name="receive" :size="15" /> ดาวน์โหลด
						</button>
					</div>
				</section>

				<!-- ท้ายเอกสาร: ตัวเลือกภาษี + หมายเหตุ (ซ้าย) / สรุปยอด (ขวา) -->
				<div class="ss-doc-foot">
					<div class="ss-doc-notes">
						<div v-if="is_mr" class="ss-dv-flags">
							<span class="ss-flag" :class="{ 'is-on': doc.included_vat }">
								<span class="ss-checkmark" :class="{ 'is-on': doc.included_vat }"
									><Icon v-if="doc.included_vat" name="check" :size="12" :stroke="3.2"
								/></span>
								มูลค่ารวมภาษี
							</span>
							<span class="ss-flag" :class="{ 'is-on': doc.vat_override }">
								<span class="ss-checkmark" :class="{ 'is-on': doc.vat_override }"
									><Icon v-if="doc.vat_override" name="check" :size="12" :stroke="3.2"
								/></span>
								แก้ไขภาษี
							</span>
						</div>
						<div v-if="doc.remarks || edit[remarks_field] || is_mr" class="ss-doc-remarks">
							<span class="ss-doc-remarks-label"><Icon name="message" :size="17" /> หมายเหตุ</span>
							<InlineEdit
								v-if="edit[remarks_field]"
								:model-value="doc.remarks"
								label="หมายเหตุ"
								add_label=""
								multiline
								editable
								:save="(v) => save_field(remarks_field, v)"
								><div class="ss-text-block">{{ doc.remarks || "–" }}</div></InlineEdit
							>
							<div v-else class="ss-text-block" :class="{ 'is-empty': !doc.remarks }">
								{{ doc.remarks || "–" }}
							</div>
						</div>
					</div>
					<div class="ss-doc-totals">
						<span class="ss-doc-totals-icon"><Icon name="calculator" :size="20" /></span>
						<div class="ss-totals">
							<div v-for="r in doc.summary.rows" :key="r.label">
								<span>{{ r.label }}</span
								><b>{{ money(r.value) }}</b>
							</div>
							<div class="is-grand">
								<span>{{ doc.summary.grand_label }}</span
								><b>{{ money(doc.summary.grand) }}</b>
							</div>
							<div v-if="doc.summary.in_words" class="ss-totals-words">
								({{ doc.summary.in_words }})
							</div>
							<template v-if="doc.summary.net !== undefined">
								<div v-for="d in doc.summary.deductions" :key="d.label" class="is-deduct">
									<span>{{ d.label }}</span
									><b>{{ money(d.value) }}</b>
								</div>
								<div class="is-net">
									<span>{{ doc.summary.net_label }}</span
									><b>{{ money(doc.summary.net) }}</b>
								</div>
							</template>
							<div v-if="doc.totals.outstanding_amount" class="is-due">
								<span>ค้าง{{ due_word }}</span
								><b>{{ money(doc.totals.outstanding_amount) }}</b>
							</div>
						</div>
					</div>
				</div>
			</div>
			</div>
		</div>

		<!-- sidebar ขวาแยกจากเนื้อหา: จอ ≥1480 กางค้างและดันเนื้อหา (html[data-rside]) จอเล็กกว่าเลื่อนทับพร้อมพื้นหลังมืด -->
		<Teleport to="#ss-layer">
			<Transition name="ss-rside-fade">
				<div v-if="side_open && !xl" class="ss-rside-backdrop" @click="side_open = false"></div>
			</Transition>
			<Transition name="ss-rside">
				<aside
					v-if="side_open && doc"
					class="ss-rside"
					:class="{ 'is-overlay': !xl }"
					aria-label="ข้อมูลเอกสาร"
				>
					<header class="ss-rside-head">
						<b>ข้อมูลเอกสาร</b>
						<button
							type="button"
							class="ss-icon-btn ss-icon-btn--sm"
							aria-label="ปิดแผง"
							@click="toggle_side"
						>
							<Icon name="x" :size="18" />
						</button>
					</header>
					<div class="ss-rside-body">
						<DocActivity
							ref="activity"
							:kind="params.kind"
							:name="params.name"
							:doctype="config.doctype"
						>
							<section v-if="related.length" class="ss-act-block">
								<h3>เอกสารที่เกี่ยวข้อง</h3>
								<div class="ss-flow">
									<button
										v-for="l in related"
										:key="l.doctype + l.name"
										type="button"
										class="ss-flow-item"
										@click="open_link(l)"
									>
										<Icon
											:name="l.dir === 'before' ? 'chevron-left' : 'chevron-right'"
											:size="16"
										/>
										<span class="ss-flow-main">
											<small>{{ link_label(l.doctype) }}</small>
											<b>{{ l.name }}</b>
										</span>
										<span class="ss-tag" :class="`tone-${l.status_tone}`">{{
											l.status_label
										}}</span>
									</button>
								</div>
							</section>
						</DocActivity>
					</div>
				</aside>
			</Transition>
		</Teleport>


		<Sheet :open="confirm" :title="`${submit_word}${config.label}`" :subtitle="params.name" @close="confirm = false">
			<p v-if="doc?.approval" class="ss-muted">
				{{ submit_word }}แล้วเอกสารมีผล ({{ doc.approval.mode === "sign" ? "ชื่อและลายเซ็นของคุณขึ้นในช่องผู้อนุมัติของแบบพิมพ์" : "สั่งซื้อต่อได้" }})
				แก้ได้เฉพาะบางช่อง (มีรูปดินสอ)
			</p>
			<p v-else class="ss-muted">
				ยืนยันแล้วแก้ได้เฉพาะบางช่อง (มีรูปดินสอ) เช่น กำหนดส่ง เลขที่อ้างอิง
				ที่เหลือต้องยกเลิกแล้วแก้ในระบบเต็ม
			</p>
			<div v-if="doc" class="ss-facts ss-facts--grid">
				<div class="ss-fact">
					<span>{{ config.party || "เรื่อง" }}</span
					><b>{{ doc.party || doc.title }}</b>
				</div>
				<div class="ss-fact">
					<span>ยอดรวม</span><b>{{ money(doc.summary.grand) }}</b>
				</div>
			</div>
			<template #footer>
				<button
					type="button"
					class="ss-btn ss-btn--primary ss-btn--block ss-btn--lg"
					:disabled="busy"
					@click="submit"
				>
					<span v-if="busy" class="ss-spinner"></span>
					<template v-else>{{ submit_word }}</template>
				</button>
			</template>
		</Sheet>

		<!-- ไม่อนุมัติ / ส่งกลับแก้ไข: ต้องมีเหตุผล (แจ้งผู้ส่ง) -->
		<Sheet
			v-if="doc?.approval"
			:open="rejecting"
			:title="doc.approval.words[reject_mode]"
			:subtitle="params.name"
			@close="rejecting = false"
		>
			<div class="ss-form">
				<label class="ss-field">
					<span class="ss-field-label">เหตุผล<em>*</em></span>
					<textarea v-model="reject_reason" class="ss-input" rows="3"></textarea>
				</label>
				<p class="ss-muted">
					{{
						reject_mode === "decline"
							? "ปิดเอกสารนี้ ผู้ส่งแก้ไขหรือส่งใหม่ไม่ได้ (เก็บไว้เป็นประวัติ ทำซ้ำเป็นใบใหม่ได้)"
							: "เอกสารกลับเป็นร่าง ผู้ส่งแก้ไขแล้วส่งใหม่ได้"
					}}
				</p>
			</div>
			<template #footer>
				<button
					type="button"
					class="ss-btn ss-btn--danger ss-btn--block ss-btn--lg"
					:disabled="busy || !reject_reason.trim()"
					@click="reject"
				>
					<span v-if="busy" class="ss-spinner"></span>
					<template v-else>{{ doc.approval.words[reject_mode] }}</template>
				</button>
			</template>
		</Sheet>

		<!-- บันทึกการลงนามแทน (เมนู ⋯): ผู้ลงนามเซ็นบนกระดาษแล้ว เจ้าหน้าที่บันทึกให้ + ไฟล์สแกน/รูป (บังคับ) -->
		<Sheet
			v-if="doc?.approval?.can_record"
			:open="recording"
			title="ลงนามแทน"
			:subtitle="params.name"
			@close="recording = false"
		>
			<div class="ss-form">
			<p class="ss-muted">
				สำหรับเอกสารที่ผู้ลงนามเซ็นบนกระดาษแล้ว บันทึกในระบบแทน (ผู้ลงนามได้รับแจ้งเตือน และประวัติเอกสารระบุชื่อผู้บันทึก)
			</p>
			<div class="ss-form-row">
				<div class="ss-field">
					<span class="ss-field-label">ผู้ลงนาม<em>*</em></span>
					<SelectBox v-model="record.signer" label="ผู้ลงนาม" :options="signers" placeholder="เลือกผู้ลงนาม" />
				</div>
				<div class="ss-field">
					<span class="ss-field-label">วันที่ลงนาม<em>*</em></span>
					<DateInput v-model="record.date" label="วันที่ลงนาม" />
				</div>
			</div>
			<div class="ss-field">
				<span class="ss-field-label">ไฟล์เอกสารที่ลงนามแล้ว (สแกน/รูปถ่าย)<em>*</em></span>
				<label class="ss-btn ss-btn--soft ss-record-file">
					<Icon name="file" :size="16" />
					<span>{{ record.file ? record.file.name : "เลือกไฟล์" }}</span>
					<input type="file" accept="image/*,application/pdf" hidden @change="pick_proof" />
				</label>
			</div>
			<label class="ss-field">
				<span class="ss-field-label">หมายเหตุ</span>
				<textarea v-model="record.note" class="ss-input" rows="2"></textarea>
			</label>
			</div>
			<template #footer>
				<button
					type="button"
					class="ss-btn ss-btn--primary ss-btn--block ss-btn--lg"
					:disabled="busy || !record.signer || !record.date || !record.file"
					@click="save_record"
				>
					<span v-if="busy" class="ss-spinner"></span>
					<template v-else>บันทึกการลงนาม</template>
				</button>
			</template>
		</Sheet>

		<DeleteSheet
			:open="deleting"
			:label="config.label"
			:name="params.name"
			method="consbiz.site_docs.delete_doc"
			:args="{ kind: params.kind, name: params.name }"
			@close="deleting = false"
			@deleted="after_delete"
		/>

		<PaymentSheet
			v-if="doc?.can_pay"
			:open="paying"
			:kind="params.kind"
			:name="params.name"
			@close="paying = false"
			@done="after_pay"
		/>

		<HtmlViewer
			v-if="doc?.print_html"
			:open="html_open"
			:html="print_html"
			:width="PRINT_W"
			:height="1123"
			:document_kind="config.doctype"
			fit_height
			:name="params.name"
			:title="config.label"
			:fetch_file="fetch_pdf"
			:file_key="copies.join(',')"
			@close="html_open = false"
		>
			<template #tools>
				<label v-for="c in COPY_OPTIONS" :key="c.value" class="ss-checkline ss-pdf-check">
					<input
						type="checkbox"
						:checked="copies.includes(c.value)"
						:disabled="copies.length === 1 && copies.includes(c.value)"
						@change="toggle_copy(c.value)"
					/>
					<span>{{ c.label }}</span>
				</label>
			</template>
		</HtmlViewer>

		<PdfViewer
			:open="pdf"
			:url="doc?.pdf_url"
			:name="params.name"
			:title="config.label"
			@close="pdf = false"
		/>
	</div>
</template>

<script setup>
import { computed, inject, onBeforeUnmount, ref, watch } from "vue";
import Icon from "../components/Icon.vue";
import FormHead from "../components/FormHead.vue";
import MiniSteps from "../components/MiniSteps.vue";
import { LABELS, can_duplicate, doc_menu, duplicate_doc, step_actions } from "../form_actions.js";
import TopBar from "../components/TopBar.vue";
import Skeleton from "../components/Skeleton.vue";
import Sheet from "../components/Sheet.vue";
import PdfViewer from "../components/PdfViewer.vue";
import HtmlViewer from "../components/HtmlViewer.vue";
import DeleteSheet from "../components/DeleteSheet.vue";
import RichText from "../components/RichText.vue";
import DocActivity from "./DocActivity.vue";
import PaymentSheet from "./PaymentSheet.vue";
import InlineEdit from "../components/InlineEdit.vue";
import SelectBox from "../components/SelectBox.vue";
import DateInput from "../components/DateInput.vue";
import { use_shortcuts } from "../shortcuts.js";
import { DOC_KINDS, doc_kind, doc_list_view, doc_target, go_doc, in_app, open_doc } from "./kinds.js";
import {
	boot,
	call,
	celebrate,
	desk_url,
	go,
	html_text,
	money,
	num,
	post,
	show_error,
	state,
	thai_date,
	toast,
	today,
	upload,
} from "../api.js";

const reload_summary = inject("reload_summary");
const params = { ...state.route.params, kind: doc_kind(state.route.params.kind) };
const list_view = doc_list_view(params.kind);
const form_target = doc_target(DOC_KINDS[params.kind] ? params.kind : "po", "form");
const config = DOC_KINDS[params.kind] || DOC_KINDS.po;

const doc = ref(null);
const busy = ref(false);
const confirm = ref(false);
const pdf = ref(false);

// แท็บเล็ต/จอใหญ่: ตารางรายการ + ช่องข้อมูลหลายคอลัมน์, มือถือ: การ์ด
const mq_wide = window.matchMedia("(min-width: 768px)");
const wide = ref(mq_wide.matches);
const on_media = () => (wide.value = mq_wide.matches);
mq_wide.addEventListener("change", on_media);
onBeforeUnmount(() => mq_wide.removeEventListener("change", on_media));

const is_mr = params.kind === "mr";
const detail_title = config.section === "buy" ? "รายละเอียดการจัดซื้อ" : "รายละเอียดการขาย";
const items_title = is_mr ? "รายการสินค้า/วัสดุ" : "รายการ";
// รายละเอียดที่ต่างจากชื่อรายการ (ERPNext ตั้ง description = ชื่อรายการเป็นค่าเริ่มต้น)
const has_desc = (it) => {
	const text = html_text(it.description);
	return !!text && text !== it.item_name;
};
const due_word = config.section === "buy" ? "จ่าย" : "รับ";
const overdue = computed(
	() =>
		doc.value?.docstatus === 1 &&
		doc.value.due &&
		new Date(doc.value.due) < new Date(new Date().toDateString()) &&
		(doc.value.totals.outstanding_amount > 0 || doc.value.status_tone === "amber")
);
const related = computed(() =>
	doc.value
		? [
				...doc.value.before.map((x) => ({ ...x, dir: "before" })),
				...doc.value.after.map((x) => ({ ...x, dir: "after" })),
		  ]
		: []
);
const has_item_date = computed(
	() => !!item_date_field.value || doc.value?.items.some((it) => it.schedule_date || it.delivery_date)
);

// ---------------------------------------------------------------- แก้ไขหลังส่ง (ช่อง Allow on Submit, site_docs.AFTER_SUBMIT)
const activity = ref(null);
const after = computed(() => doc.value?.after_submit || null);
const edit = computed(() => Object.fromEntries((after.value?.fields || []).map((f) => [f.fieldname, f])));
const due_field = computed(() => after.value?.due_field);
const remarks_field = computed(() => after.value?.remarks_field);
// ช่องที่ไม่มีที่แสดงในหน้าดู: ต่อท้ายช่องข้อมูล
const extra_fields = computed(() =>
	(after.value?.fields || []).filter(
		(f) =>
			![due_field.value, remarks_field.value].includes(f.fieldname) &&
			!(f.fieldname === "title" && !config.party)
	)
);
const item_date_field = computed(
	() => (after.value?.items || []).find((f) => ["schedule_date", "delivery_date"].includes(f)) || null
);
const item_date_head = computed(() =>
	["po", "so"].includes(params.kind) ? (params.kind === "so" ? "กำหนดส่งมอบ" : "กำหนดส่ง") : "วันที่ต้องการ"
);
const item_date_label = computed(() => (item_date_field.value === "delivery_date" ? "กำหนดส่ง" : "ต้องการ"));

async function save_after(values, items, apply) {
	try {
		doc.value = await post("consbiz.site_docs.save_after_submit", {
			kind: params.kind,
			name: params.name,
			values,
			items,
			apply_items: apply ? 1 : 0,
			modified: after.value?.modified,
		});
		toast("บันทึกแล้ว", "success");
		activity.value?.reload();
	} catch (error) {
		show_error(error);
		throw error;
	}
}
const save_field = (field, value, apply) => save_after({ [field]: value }, null, apply);
const save_item = (it, value) => save_after({}, [{ name: it.name, [item_date_field.value]: value }]);
// ---------------------------------------------------------------- sidebar ขวา
const SIDE_KEY = "consbiz.site.doc_side";
const mq_xl = window.matchMedia("(min-width: 1480px)");
const xl = ref(mq_xl.matches);
const saved_side = (() => {
	try {
		return localStorage.getItem(SIDE_KEY);
	} catch {
		return null;
	}
})();
// จอใหญ่: ค่าเริ่มต้นเปิด (จำในเครื่อง) จอเล็ก: ปิดจนกดปุ่ม
const side_open = ref(xl.value && saved_side !== "closed");
function toggle_side() {
	side_open.value = !side_open.value;
	if (xl.value) {
		try {
			localStorage.setItem(SIDE_KEY, side_open.value ? "open" : "closed");
		} catch {
			/* เก็บไม่ได้: ใช้ค่าเริ่มต้น */
		}
	}
}
const on_xl = () => {
	xl.value = mq_xl.matches;
	side_open.value = xl.value && saved_side !== "closed";
};
mq_xl.addEventListener("change", on_xl);
const on_key = (e) => e.key === "Escape" && !xl.value && (side_open.value = false);
window.addEventListener("keydown", on_key);
watch(
	() => side_open.value && xl.value,
	(push) => {
		if (push) document.documentElement.dataset.rside = "open";
		else delete document.documentElement.dataset.rside;
	},
	{ immediate: true }
);
onBeforeUnmount(() => {
	mq_xl.removeEventListener("change", on_xl);
	window.removeEventListener("keydown", on_key);
	delete document.documentElement.dataset.rside;
});

// เอกสารถัดไปสร้างได้เฉพาะชนิดที่แอปนี้ดูแล (หน้างานขอซื้อได้ สั่งซื้อทำที่แอปออฟฟิศ)
const next_kind = computed(() =>
	doc.value?.next_kind && in_app(doc.value.next_kind) ? doc.value.next_kind : null
);

// หัวฟอร์ม: ร่าง → ยืนยัน → สร้างเอกสารถัดไป (ขอซื้อ → สั่งซื้อ → แจ้งหนี้, เสนอราคา → สั่งขาย → แจ้งหนี้) / รับ-จ่ายชำระ
const actions = computed(() => {
	const d = doc.value;
	if (!d) return [];
	const form = (args) => go_doc(params.kind, "form", args);
	const ap = d.approval;
	return step_actions({
		stage: ap?.pending ? "pending" : d.docstatus === 0 ? "draft" : "done",
		submit: d.can_submit && { label: submit_word.value, run: () => (confirm.value = true) },
		// ขั้นอนุมัติ/ลงนาม (ใบขอซื้อ/สั่งซื้อ/แจ้งหนี้ซื้อ)
		send: ap?.can_send && { label: ap.words.send, icon: "send", run: () => approval_step("send") },
		withdraw: ap?.can_withdraw && { label: LABELS.withdraw, run: () => approval_step("withdraw") },
		// ส่งกลับแก้ไข = ปุ่มรอง (ไม่ปิดเอกสาร) ไม่อนุมัติ (ปิดเลย) = ปุ่มแดง
		reject: ap?.can_reject && { label: ap.words.reject, tone: "soft", run: () => open_reject("reject") },
		decline: ap?.can_decline && { label: ap.words.decline, run: () => open_reject("decline") },
		next: [
			d.can_pay && {
				label: params.kind === "si" ? "รับชำระ" : "จ่ายชำระ",
				icon: params.kind === "si" ? "receive" : "send",
				run: () => (paying.value = true),
			},
			next_kind.value && {
				label: `สร้าง${DOC_KINDS[next_kind.value].label}`,
				icon: "plus",
				run: () =>
					go_doc(next_kind.value, "form", { name: "new", source: params.name }),
			},
		],
		extra: [
			// ลงนามแทน (ตกลง 2026-11-19): ผู้ที่ไม่ใช่ผู้ลงนามที่ระบุ ใช้กับเอกสารที่ลงนามบนกระดาษแล้ว
			ap?.can_record && { key: "record", label: "ลงนามแทน", icon: "pen", run: open_record },
			d.can_edit && {
				label: "แก้ไข",
				icon: "pen",
				tone: d.can_submit || ap?.can_send ? "soft" : "primary",
				run: () => form({ name: params.name }),
			},
		],
	});
});
// ---------------------------------------------------------------- พิมพ์ (ตกลง 2026-11-19 ใช้จริง)
// แบบพิมพ์ที่ตั้งในแอปเป็น HTML ของ ConsERP (doc.print_html, ตั้งค่าจัดซื้อ > แบบฟอร์มพิมพ์ เช่น ใบสั่งซื้อรูปแบบที่ 4)
// = หน้าตัวอย่าง iframe ของหน้าพิมพ์ Frappe (/printview เอกสารแบ่งหน้าเองด้วย paginate.js) ติ๊กต้นฉบับ/สำเนา PDF แชร์/ดาวน์โหลด = แบบเดียวกันผ่าน Chrome
// แบบอื่น (Print Designer ฯลฯ) = PdfViewer ตามเดิม
const PRINT_W = 794;
function print() {
	if (!doc.value) return;
	if (doc.value.print_html) open_html();
	else pdf.value = true;
}
const html_open = ref(false);
const html_loading = ref(false);
const print_html = ref("");
const PRINT_FIX = `<style>
.action-banner { display: none !important; }
html, body { margin: 0 !important; padding: 0 !important; background: #fff !important; }
.print-format-gutter { margin: 0 !important; padding: 0 !important; background: #fff !important; }
@media screen {
	html, body, .print-format-gutter { background: #e9ebef !important; }
	.print-format { margin: 0 !important; padding: 0 !important; max-width: none !important; width: auto !important;
		min-height: 0 !important; box-shadow: none !important; border-radius: 0 !important; background: none !important; }
	.ec-sheet { margin: 0 0 14px; box-shadow: 0 1px 6px rgba(0,0,0,.18); }
}
</style>`;
// ฉบับที่พิมพ์ (ติ๊กในหน้าตัวอย่าง อย่างน้อย 1 ฉบับ) ต้นฉบับ + สำเนา = ไฟล์เดียว เลขหน้านับใหม่ต่อฉบับ (purchase_order_print.copies_of)
const COPY_OPTIONS = [
	{ value: "original", label: "ต้นฉบับ" },
	{ value: "copy", label: "สำเนา" },
];
const copies = ref(["original"]);
function toggle_copy(value) {
	const next = copies.value.includes(value) ? copies.value.filter((v) => v !== value) : [...copies.value, value];
	if (!next.length) return;
	copies.value = COPY_OPTIONS.map((c) => c.value).filter((v) => next.includes(v));
	open_html();
}
const print_args = () => ({
	doctype: config.doctype,
	name: params.name,
	format: doc.value.print_html.format,
	no_letterhead: "1",
	copies: copies.value.join(","),
});
const fetch_pdf = () =>
	fetch(
		`/api/method/frappe.utils.print_format.download_pdf?${new URLSearchParams({ ...print_args(), pdf_generator: "chrome" })}`,
		{ credentials: "same-origin" }
	);
async function open_html() {
	const q = new URLSearchParams(print_args());
	html_loading.value = true;
	try {
		const res = await fetch(`/printview?${q}`, { credentials: "same-origin" });
		if (!res.ok) throw new Error(`เปิดหน้าพิมพ์ไม่สำเร็จ (${res.status})`);
		let html = await res.text();
		// ลิงก์ CSS/ฟอนต์แบบ path ของไซต์ต้องอ้างจากไซต์ (iframe ที่เขียนด้วย document.write ไม่มี URL ของตัวเอง)
		html = html.replace(/<head([^>]*)>/i, `<head$1><base href="${location.origin}/">`);
		html = html.replace(/<\/head>/i, `${PRINT_FIX}</head>`);
		print_html.value = html;
		html_open.value = true;
	} catch (error) {
		show_error(error);
	} finally {
		html_loading.value = false;
	}
}

const menu = computed(() => {
	const d = doc.value;
	if (!d) return [];
	return doc_menu({
		duplicate:
			can_duplicate(config.doctype) &&
			(() => duplicate_doc(config.doctype, params.name, form_target.view, { kind: form_target.kind })),
		refresh: load,
		desk: boot.desk !== false ? [config.doctype, params.name] : null,
		remove: d.can_delete && (() => (deleting.value = true)),
	});
});

// รับ/จ่ายชำระ: หน้ารายการของหมวดบัญชี (เปิดรายการที่สร้างในแอปถ้าเข้าหมวดบัญชีได้)
const PAYMENT_LIST = { si: "acc-receipts", pi: "acc-payments" };
const paying = ref(false);
const payment_list = (kind = params.kind) =>
	boot.sections?.includes("accounting") && boot.accounting?.[PAYMENT_LIST[kind]] ? PAYMENT_LIST[kind] : null;
async function after_pay(result) {
	paying.value = false;
	reload_summary();
	const list = payment_list();
	if (list) go("acc-payment", { kind: list, name: result.name });
	else await load();
}

const deleting = ref(false);
function after_delete() {
	reload_summary();
	go(list_view, {}, { replace: true });
}

const progress = computed(() =>
	doc.value?.docstatus === 1
		? (config.progress || [])
				// null = ไม่มีขั้นนี้ (สั่งซื้อของใบขอซื้อผู้ว่าจ้างจัดหา)
				.filter(([field]) => doc.value.progress[field] != null)
				.map(([field, label]) => ({ label, value: doc.value.progress[field] || 0 }))
		: []
);

const LINK_LABELS = {
	"Material Request": "ใบขอซื้อ",
	"Purchase Order": "ใบสั่งซื้อ",
	"Purchase Receipt": "ใบรับของ",
	"Purchase Invoice": "ใบแจ้งหนี้ซื้อ",
	Quotation: "ใบเสนอราคา",
	"Sales Order": "ใบสั่งขาย",
	"Delivery Note": "ใบส่งของ",
	"Sales Invoice": "ใบแจ้งหนี้ขาย",
	"Payment Entry": "รับ/จ่ายเงิน",
};
const link_label = (doctype) => LINK_LABELS[doctype] || doctype;

// ปริมาณที่ดำเนินการแล้วของแต่ละรายการ
// ช่องปริมาณที่เกี่ยวกับเอกสารแต่ละชนิด (แถวของ SO มี ordered_qty ของการผลิต ไม่ใช่การสั่งซื้อ)
const ITEM_PROGRESS = {
	mr: [
		["ordered_qty", "สั่งแล้ว"],
		["received_qty", "รับแล้ว"],
	],
	po: [["received_qty", "รับแล้ว"]],
	so: [["delivered_qty", "ส่งมอบแล้ว"]],
};
function item_progress(it) {
	const pairs = ITEM_PROGRESS[params.kind] || [];
	if (doc.value.docstatus !== 1) return "";
	return pairs
		.filter(([field]) => it[field] !== undefined && it[field] !== null)
		.map(([field, label]) => `${label} ${num(it[field])}/${num(it.qty)}`)
		.join(" · ");
}

// เอกสารจัดซื้อ/ขาย: ชนิดที่แอปนี้ดูแลเปิดในแอป ชนิดอื่นไปแอปที่ดูแล (open_doc) ที่เหลือ (ใบรับของ, ใบส่งของ, รับ/จ่ายเงิน) เปิดในระบบเต็ม
function open_link(l) {
	if (l.kind) open_doc(l.kind, l.name);
	else if (l.doctype === "Payment Entry" && payment_list()) go("acc-payment", { kind: payment_list(), name: l.name });
	else window.location.href = desk_url(l.doctype, l.name);
}

// ส่งออกรายการเป็นไฟล์ที่เปิดใน Excel ได้ (CSV UTF-8 มี BOM ให้ภาษาไทยไม่เพี้ยน)
function export_items() {
	const d = doc.value;
	const head = ["#", "รหัส", "รายการ", "จำนวน", "หน่วย", "หน่วยละ", "เป็นเงิน"];
	if (has_item_date.value) head.push(item_date_head.value);
	const rows = d.items.map((it, i) => {
		const r = [i + 1, it.item_code, it.item_name || "", it.qty, it.uom, it.rate, it.amount];
		if (has_item_date.value)
			r.push(it[item_date_field.value] || it.schedule_date || it.delivery_date || "");
		return r;
	});
	const cell = (v) => {
		const t = v == null ? "" : String(v);
		return /[",\n]/.test(t) ? `"${t.replace(/"/g, '""')}"` : t;
	};
	const csv = "﻿" + [head, ...rows].map((r) => r.map(cell).join(",")).join("\r\n");
	const url = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
	const a = document.createElement("a");
	a.href = url;
	a.download = `${params.name}.csv`;
	a.click();
	setTimeout(() => URL.revokeObjectURL(url), 1000);
}

async function load() {
	try {
		doc.value = await call("consbiz.site_docs.get_doc", { kind: params.kind, name: params.name });
	} catch (error) {
		show_error(error);
	}
}

async function mark_sent() {
	busy.value = true;
	try {
		await post("consbiz.subcontract.mark_po_sent", { name: params.name });
		toast("บันทึกว่าส่งผู้รับเหมาแล้ว", "success");
		reload_summary();
		await load();
	} catch (error) {
		show_error(error);
	} finally {
		busy.value = false;
	}
}

// ---------------------------------------------------------------- อนุมัติ/ลงนาม (consbiz/doc_approval.py)
const submit_word = computed(() => doc.value?.approval?.words.do || LABELS.confirm);
const signer_name = computed(() => {
	const ap = doc.value?.approval;
	if (ap?.signed_by_name && doc.value.docstatus === 1) return ap.signed_by_name;
	return ap?.approver_name || (is_mr ? doc.value?.approve_by : null);
});
const when = (v) => (v ? thai_date(String(v).slice(0, 10), { year: true }) : "");
const approval_banner = computed(() => {
	const d = doc.value;
	const ap = d?.approval;
	if (!ap) return null;
	if (ap.pending)
		return {
			tone: "amber",
			icon: "clock",
			title: ap.words.pending,
			text: `ส่งโดย ${ap.sent_by_name || "-"} ${when(ap.sent_on)} · ระหว่างรอแก้ไขไม่ได้ (ผู้ส่งดึงกลับได้)`,
		};
	if (d.docstatus === 0 && ap.status === "Declined")
		return {
			tone: "rose",
			icon: "ban",
			title: `${ap.words.decline} (ปิดแล้ว)`,
			text: `${ap.review_note || ""} · แก้ไข/ส่งใหม่ไม่ได้ ทำซ้ำเป็นใบใหม่ได้ (เมนู ⋯)`,
		};
	if (d.docstatus === 0 && ap.status === "Rejected")
		return { tone: "rose", icon: "alert", title: ap.words.reject, text: ap.review_note || "" };
	if (d.docstatus === 1 && ap.signed_by_name)
		return {
			tone: "green",
			icon: "check",
			title: `${ap.words.done}โดย ${ap.signed_by_name}`,
			text:
				when(ap.signed_on) +
				(ap.proxy_name ? ` · บันทึกการลงนามแทนโดย ${ap.proxy_name}` : "") +
				(ap.sent_by_name ? ` · ส่งโดย ${ap.sent_by_name}` : ""),
		};
	return null;
});

const APPROVAL_DONE = {
	send: "ส่งแล้ว",
	withdraw: "ดึงเอกสารกลับแล้ว",
	reject: "ส่งกลับแล้ว",
	decline: "ไม่อนุมัติแล้ว",
};
async function approval_step(step, args = {}) {
	busy.value = true;
	try {
		doc.value = await post(`consbiz.doc_approval.${step}`, { kind: params.kind, name: params.name, ...args });
		toast(APPROVAL_DONE[step] || "บันทึกแล้ว", "success");
		reload_summary();
		activity.value?.reload();
		return true;
	} catch (error) {
		show_error(error);
		return false;
	} finally {
		busy.value = false;
	}
}

const rejecting = ref(false);
const reject_reason = ref("");
// reject = ส่งกลับแก้ไข (กลับเป็นร่าง) / decline = ไม่อนุมัติ (ปิดเลย)
const reject_mode = ref("reject");
function open_reject(mode) {
	reject_mode.value = mode;
	rejecting.value = true;
}
async function reject() {
	if (await approval_step(reject_mode.value, { reason: reject_reason.value })) {
		rejecting.value = false;
		reject_reason.value = "";
	}
}

const recording = ref(false);
const signers = ref([]);
const record = ref({ signer: null, date: null, file: null, note: "" });
async function open_record() {
	record.value = { signer: null, date: today(), file: null, note: "" };
	recording.value = true;
	try {
		const result = await call("consbiz.doc_approval.get_signers", { kind: params.kind, name: params.name });
		signers.value = result.options;
		record.value.signer ??= result.default;
	} catch (error) {
		show_error(error);
	}
}
function pick_proof(e) {
	record.value.file = e.target.files?.[0] || null;
	e.target.value = "";
}
async function save_record() {
	busy.value = true;
	try {
		const file = await upload(record.value.file, { doctype: config.doctype, docname: params.name });
		doc.value = await post("consbiz.doc_approval.record_signing", {
			kind: params.kind,
			name: params.name,
			signer: record.value.signer,
			signed_on: record.value.date,
			proof: file.file_url,
			note: record.value.note,
		});
		recording.value = false;
		await celebrate("บันทึกการลงนามแล้ว", params.name);
		reload_summary();
		activity.value?.reload();
	} catch (error) {
		show_error(error);
	} finally {
		busy.value = false;
	}
}

async function submit() {
	busy.value = true;
	try {
		// ขั้นอนุมัติ/ลงนาม: doc_approval.approve (แจ้งผู้ส่ง) อื่นๆ = submit_doc ตามเดิม
		if (doc.value?.approval) await post("consbiz.doc_approval.approve", { kind: params.kind, name: params.name });
		else await post("consbiz.site_docs.submit_doc", { kind: params.kind, name: params.name });
		confirm.value = false;
		await celebrate(`${submit_word.value}${config.label}แล้ว`, params.name);
		reload_summary();
		await load();
	} catch (error) {
		show_error(error);
	} finally {
		busy.value = false;
	}
}

load();

// คีย์ลัด (แอปออฟฟิศ): e แก้ไขร่าง, p PDF, i แผงข้อมูลเอกสาร
use_shortcuts({
	e: () => doc.value?.can_edit && go_doc(params.kind, "form", { name: params.name }),
	p: () => print(),
	i: () => doc.value && toggle_side(),
});
</script>
