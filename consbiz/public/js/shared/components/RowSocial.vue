<template>
	<span v-if="doctype && name && row._comment_count != null" class="ss-row-social">
		<template v-if="icons_only">
			<span role="img" aria-label="ความคิดเห็น"><Icon name="message" :size="14" /></span>
			<span role="img" :aria-label="liked ? 'ถูกใจแล้ว' : 'ถูกใจ'" :class="{ 'is-liked': liked }">
				<Icon name="heart" :size="14" />
			</span>
		</template>
		<template v-else>
			<button
				ref="trigger"
				type="button"
				class="ss-icon-btn ss-icon-btn--sm"
				title="ความคิดเห็น"
				aria-label="ความคิดเห็น"
				aria-haspopup="dialog"
				:aria-expanded="opened"
				@click.stop="open"
				@keydown.stop
			>
				<Icon name="message" :size="14" />
			</button>
			<button
				type="button"
				class="ss-icon-btn ss-icon-btn--sm"
				:class="{ 'is-liked': liked }"
				title="ถูกใจ"
				aria-label="ถูกใจ"
				:aria-pressed="liked"
				:disabled="liking"
				@click.stop="toggle"
				@keydown.stop
			>
				<Icon name="heart" :size="14" />
			</button>
			<Sheet v-if="opened" open title="ความคิดเห็น" :subtitle="name" @close="close">
				<p v-if="loading" role="status">กำลังโหลดความคิดเห็น…</p>
				<template v-else-if="comments">
					<p v-if="!comments.length" class="ss-row-social-empty">ยังไม่มีความคิดเห็น</p>
					<article v-for="comment in comments" :key="comment.name" class="ss-row-comment">
						<header>
							<b>{{
								comment.comment_by || comment.comment_email || comment.owner
							}}</b>
							<time :datetime="comment.creation.replace(' ', 'T')">{{
								modified_title(comment.creation)
							}}</time>
						</header>
						<RichText :html="comment.content" />
					</article>
				</template>
				<form class="ss-row-comment-form" @submit.prevent="add_comment">
					<label>
						<span class="ss-field-label">เพิ่มความคิดเห็น</span>
						<textarea ref="input" v-model="draft" class="ss-input" rows="3" />
					</label>
					<p v-if="error" class="ss-row-social-error" role="alert">{{ error }}</p>
					<button
						type="submit"
						class="ss-btn ss-btn--primary"
						:disabled="!draft.trim() || saving || !comments"
					>
						<Icon name="send" :size="16" />
						{{ saving ? "กำลังส่ง…" : "ส่งความคิดเห็น" }}
					</button>
				</form>
			</Sheet>
		</template>
	</span>
</template>

<script setup>
import { computed, nextTick, ref } from "vue";
import Icon from "./Icon.vue";
import RichText from "./RichText.vue";
import Sheet from "./Sheet.vue";
import { boot, call, modified_title, post, show_error } from "../api.js";

const props = defineProps({ row: { type: Object, required: true }, icons_only: Boolean });
const doctype = computed(() => props.row.doctype);
const name = computed(() => props.row.docname || props.row.name);
const likes = computed(() => {
	const value = props.row._liked_by;
	try {
		const list = typeof value === "string" ? JSON.parse(value) : value;
		return Array.isArray(list) ? list : [];
	} catch {
		return [];
	}
});
const liked = computed(() => likes.value.includes(boot.user));
const liking = ref(false);
const opened = ref(false);
const loading = ref(false);
const saving = ref(false);
const comments = ref(null);
const error = ref("");
const draft = ref("");
const input = ref(null);
const trigger = ref(null);
let comment_request = 0;

async function toggle() {
	if (liking.value) return;
	const row = props.row;
	const before = row._liked_by;
	const add = !liked.value;
	row._liked_by = add
		? [...likes.value, boot.user]
		: likes.value.filter((user) => user !== boot.user);
	liking.value = true;
	try {
		await post("frappe.desk.like.toggle_like", {
			doctype: doctype.value,
			name: name.value,
			add: add ? "Yes" : "No",
		});
	} catch (failure) {
		row._liked_by = before;
		show_error(failure);
	} finally {
		liking.value = false;
	}
}

async function open() {
	const request = ++comment_request;
	opened.value = true;
	loading.value = true;
	error.value = "";
	comments.value = null;
	try {
		const rows = await call("consbiz.row_social.comments", {
			doctype: doctype.value,
			name: name.value,
		});
		if (request !== comment_request) return;
		comments.value = rows;
		props.row._comment_count = comments.value.length;
	} catch (failure) {
		if (request !== comment_request) return;
		error.value = failure.message;
	} finally {
		if (request === comment_request) loading.value = false;
	}
	await nextTick();
	if (opened.value) input.value?.focus();
}

function close() {
	if (saving.value) return;
	comment_request++;
	opened.value = false;
	trigger.value?.focus();
}

async function add_comment() {
	const text = draft.value.trim();
	if (!text || saving.value || !comments.value) return;
	const content = document.createElement("div");
	content.textContent = text;
	error.value = "";
	saving.value = true;
	try {
		const comment = await post("frappe.desk.form.utils.add_comment", {
			reference_doctype: doctype.value,
			reference_name: name.value,
			content: content.innerHTML.replace(/\r?\n/g, "<br>"),
			comment_email: boot.user,
			comment_by: boot.user,
		});
		comments.value.push(comment);
		props.row._comment_count = comments.value.length;
		draft.value = "";
	} catch (failure) {
		error.value = failure.message;
	} finally {
		saving.value = false;
	}
}
</script>

<style scoped>
.ss-row-social {
	display: inline-flex;
	align-items: center;
	gap: 4px;
	color: var(--ss-muted);
}
.ss-row-social > button {
	width: 24px;
	height: 28px;
}
.ss-row-social > span {
	display: inline-flex;
}
.ss-row-social .is-liked {
	color: var(--ss-danger);
}
.is-liked .ss-icon {
	fill: currentColor;
}
.ss-row-comment {
	padding-block: 8px;
	border-bottom: 1px solid var(--ss-line);
	overflow-wrap: anywhere;
}
.ss-row-comment header {
	display: flex;
	flex-wrap: wrap;
	justify-content: space-between;
	gap: 4px 12px;
}
.ss-row-comment time,
.ss-row-social-empty {
	color: var(--ss-muted);
}
.ss-row-comment-form {
	display: grid;
	gap: 8px;
	margin-top: 12px;
}
.ss-row-comment-form textarea {
	display: block;
	width: 100%;
}
.ss-row-comment-form button {
	justify-self: end;
}
.ss-row-social-error {
	color: var(--ss-danger);
}
</style>
