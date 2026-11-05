<template>
	<!-- แผงขวาของหน้าดูเอกสาร (แบบ sidebar + timeline ของระบบเต็ม): ถูกใจ / มอบหมาย / ไฟล์แนบ / ความคิดเห็น + ความเคลื่อนไหว
	     ข้อมูลจาก site_docs.get_activity  มือถือ/แท็บเล็ตอยู่ใต้เนื้อหาเอกสาร -->
	<div class="ss-activity">
		<Skeleton v-if="!data" :rows="2" />
		<template v-else>
			<!-- มอบหมาย + ถูกใจ -->
			<section class="ss-act-block">
				<div class="ss-act-head">
					<h3>มอบหมาย</h3>
					<button
						type="button"
						class="ss-like"
						:class="{ 'is-on': data.liked }"
						:aria-pressed="data.liked"
						:title="data.likes ? `ถูกใจ ${data.likes} คน` : 'ถูกใจ'"
						@click="like"
					>
						<Icon name="heart" :size="16" :stroke="2.2" />
						<small v-if="data.likes">{{ data.likes }}</small>
					</button>
				</div>
				<div class="ss-act-people">
					<span v-for="a in data.assigned" :key="a.user" class="ss-act-person">
						<span class="ss-avatar ss-avatar--xs" :class="`tone-${tone(a.user)}`">{{
							initials(a.name)
						}}</span>
						{{ a.name }}
						<button
							v-if="data.can.assign"
							type="button"
							:aria-label="`ยกเลิกมอบหมาย ${a.name}`"
							@click="unassign(a.user)"
						>
							<Icon name="x" :size="12" :stroke="2.6" />
						</button>
					</span>
					<span v-if="!data.assigned.length" class="ss-act-muted">ยังไม่ได้มอบหมาย</span>
				</div>
				<Picker
					v-if="data.can.assign"
					:model-value="null"
					class="ss-act-assign"
					label="มอบหมายให้"
					placeholder="+ มอบหมายให้…"
					:remote_fn="search_users"
					@select="assign"
				/>
			</section>

			<!-- ไฟล์แนบ -->
			<section class="ss-act-block">
				<div class="ss-act-head">
					<h3>
						ไฟล์แนบ <span v-if="data.files.length" class="ss-count">{{ data.files.length }}</span>
					</h3>
					<label
						v-if="data.can.attach"
						class="ss-link ss-act-upload"
						:class="{ 'is-busy': uploading }"
					>
						<input type="file" multiple :disabled="uploading" @change="attach" />
						<span v-if="uploading" class="ss-spinner ss-spinner--sm"></span>
						<template v-else>+ แนบไฟล์</template>
					</label>
				</div>
				<ul v-if="data.files.length" class="ss-act-files">
					<li v-for="f in data.files" :key="f.name">
						<Icon :name="is_image(f) ? 'camera' : 'file'" :size="16" />
						<a :href="f.file_url" target="_blank" rel="noopener" :title="f.file_name">{{
							f.file_name
						}}</a>
						<small>{{ size(f.file_size) }}</small>
						<button
							v-if="data.can.remove_file"
							type="button"
							class="ss-icon-btn ss-icon-btn--sm"
							:aria-label="`เอา ${f.file_name} ออก`"
							title="เอาออก"
							@click="remove_file(f)"
						>
							<Icon name="x" :size="14" />
						</button>
					</li>
				</ul>
				<p v-else class="ss-act-muted">ยังไม่มีไฟล์แนบ</p>
			</section>

			<slot></slot>

			<!-- ความคิดเห็น + ความเคลื่อนไหว -->
			<section class="ss-act-block">
				<h3>ความเคลื่อนไหว</h3>
				<div class="ss-act-compose">
					<textarea
						v-model="text"
						class="ss-input"
						rows="2"
						placeholder="เขียนความคิดเห็น… (Ctrl+Enter ส่ง)"
						aria-label="ความคิดเห็น"
						@keydown.ctrl.enter.prevent="comment"
						@keydown.meta.enter.prevent="comment"
					></textarea>
					<button
						v-if="text.trim()"
						type="button"
						class="ss-btn ss-btn--primary ss-btn--sm"
						:disabled="sending"
						@click="comment"
					>
						<span v-if="sending" class="ss-spinner"></span>
						<template v-else>ส่งความคิดเห็น</template>
					</button>
				</div>
				<ol class="ss-act-timeline">
					<li v-for="(t, i) in data.timeline" :key="i" :class="`is-${t.type}`">
						<span class="ss-avatar ss-avatar--xs" :class="`tone-${tone(t.by?.user || '')}`">{{
							initials(t.by?.name || "?")
						}}</span>
						<div class="ss-act-item">
							<div class="ss-act-meta">
								<b>{{ t.by?.name || "ระบบ" }}</b>
								<small :title="t.at">{{ time_ago(t.at) }}</small>
								<button
									v-if="t.type === 'comment' && t.mine"
									type="button"
									class="ss-link is-muted ss-act-del"
									@click="remove_comment(t)"
								>
									ลบ
								</button>
							</div>
							<RichText v-if="t.type === 'comment'" :html="t.html" class="ss-act-comment" />
							<span v-else class="ss-act-text">{{ t.text }}</span>
						</div>
					</li>
				</ol>
			</section>
		</template>
	</div>
</template>

<script setup>
import { ref, watch } from "vue";
import Icon from "../components/Icon.vue";
import Skeleton from "../components/Skeleton.vue";
import Picker from "../components/Picker.vue";
import RichText from "../components/RichText.vue";
import { call, initials, post, show_error, time_ago, toast, tone, upload } from "../api.js";

const props = defineProps({ kind: String, name: String, doctype: String });

const data = ref(null);
const text = ref("");
const sending = ref(false);
const uploading = ref(false);

async function load() {
	try {
		data.value = await call("consbiz.site_docs.get_activity", { kind: props.kind, name: props.name });
	} catch (error) {
		show_error(error);
	}
}

const search_users = (txt) => call("consbiz.site_docs.search_users", { txt });

async function assign(option) {
	if (!option?.value) return;
	try {
		// ส่งเป็นพารามิเตอร์ชั้นบน (args ว่าง = ฟังก์ชันอ่านจาก form_dict) assign_to เป็น JSON list
		await post("frappe.desk.form.assign_to.add", {
			assign_to: [option.value],
			doctype: props.doctype,
			name: props.name,
		});
		toast(`มอบหมายให้ ${option.label || option.value} แล้ว`, "success");
		load();
	} catch (error) {
		show_error(error);
	}
}

async function unassign(user) {
	try {
		await post("frappe.desk.form.assign_to.remove", {
			doctype: props.doctype,
			name: props.name,
			assign_to: user,
		});
		load();
	} catch (error) {
		show_error(error);
	}
}

async function like() {
	const on = !data.value.liked;
	data.value.liked = on;
	data.value.likes += on ? 1 : -1;
	try {
		await post("frappe.desk.like.toggle_like", {
			doctype: props.doctype,
			name: props.name,
			add: on ? "Yes" : "No",
		});
	} catch (error) {
		data.value.liked = !on;
		data.value.likes += on ? -1 : 1;
		show_error(error);
	}
}

async function attach(event) {
	const files = [...(event.target.files || [])];
	event.target.value = "";
	if (!files.length) return;
	uploading.value = true;
	try {
		for (const file of files) await upload(file, { doctype: props.doctype, docname: props.name });
		toast(`แนบ ${files.length} ไฟล์แล้ว`, "success");
		load();
	} catch (error) {
		show_error(error);
	} finally {
		uploading.value = false;
	}
}

async function remove_file(file) {
	if (!window.confirm(`เอา ${file.file_name} ออกจากเอกสาร?`)) return;
	try {
		await post("consbiz.site_docs.remove_attachment", {
			kind: props.kind,
			name: props.name,
			file: file.name,
		});
		load();
	} catch (error) {
		show_error(error);
	}
}

async function comment() {
	if (!text.value.trim() || sending.value) return;
	sending.value = true;
	try {
		// ข้อความธรรมดา → HTML (ขึ้นบรรทัดใหม่ = <br>) แบบกล่องความคิดเห็นของระบบเต็ม
		const div = document.createElement("div");
		div.textContent = text.value.trim();
		await post("consbiz.site_docs.add_comment", {
			kind: props.kind,
			name: props.name,
			text: `<p>${div.innerHTML.replace(/\n/g, "<br>")}</p>`,
		});
		text.value = "";
		load();
	} catch (error) {
		show_error(error);
	} finally {
		sending.value = false;
	}
}

async function remove_comment(t) {
	if (!window.confirm("ลบความคิดเห็นนี้?")) return;
	try {
		await post("consbiz.site_docs.delete_comment", {
			kind: props.kind,
			name: props.name,
			comment: t.name,
		});
		load();
	} catch (error) {
		show_error(error);
	}
}

const is_image = (f) => /\.(png|jpe?g|gif|webp|heic)$/i.test(f.file_name || "");
function size(bytes) {
	const n = Number(bytes) || 0;
	if (n >= 1048576) return `${(n / 1048576).toFixed(1)} MB`;
	if (n >= 1024) return `${Math.round(n / 1024)} KB`;
	return n ? `${n} B` : "";
}

watch(() => props.name, load, { immediate: true });
defineExpose({ reload: load });
</script>
