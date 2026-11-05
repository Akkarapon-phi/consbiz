<!-- ขอบเขตเอกสารจัดซื้อ/ขาย: โครงการที่เลือก / ทุกโครงการ (จำในเครื่อง) -->
<template>
	<Segmented
		:model-value="state.doc_scope"
		:options="[
			{ value: 'project', label: disabled ? 'โครงการนี้ (ไม่มีช่องโครงการ)' : 'โครงการนี้' },
			{ value: 'all', label: 'ทุกโครงการ' },
		]"
		class="ss-scope"
		@update:model-value="set_doc_scope"
	/>
</template>

<script setup>
import Segmented from "../components/Segmented.vue";
import { set_doc_scope, state } from "../api.js";

defineProps({ disabled: Boolean });
</script>
