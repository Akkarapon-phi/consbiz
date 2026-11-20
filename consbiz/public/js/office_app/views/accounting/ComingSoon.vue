<template>
	<div>
		<TopBar :title="page.label" />
		<div class="ss-content">
			<h1 v-if="wide" class="ss-section-title">{{ page.label }}</h1>
			<Empty :icon="page.icon" title="เร็วๆ นี้" />
		</div>
	</div>
</template>

<script setup>
import { state } from "../../../shared/api.js";
import Empty from "../../../shared/components/Empty.vue";
import TopBar from "../../../shared/components/TopBar.vue";
import { use_wide } from "../../../shared/table.js";
import { ACCOUNTING_PLACEHOLDERS } from "../../sections.js";

const page = ACCOUNTING_PLACEHOLDERS[state.route.view];
const wide = use_wide();
</script>
