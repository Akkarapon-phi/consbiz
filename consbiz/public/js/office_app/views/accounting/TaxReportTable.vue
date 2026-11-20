<template>
	<div class="ss-table-wrap">
		<table ref="table" class="ss-table ss-table--list">
			<thead>
				<tr>
					<th v-for="c in data.columns" :key="c.fieldname" :class="{ 'is-num': is_num(c) }">
						{{ c.label }}
					</th>
					<th class="col-modified"></th>
				</tr>
			</thead>
			<tbody>
				<tr
					v-for="(r, i) in data.rows"
					:key="i"
					:class="{ 'is-static': !r.name }"
					@click="$emit('open', r)"
				>
					<td v-for="c in data.columns" :key="c.fieldname" :class="{ 'is-num': is_num(c) }">
						<template v-if="c.fieldtype === 'Date'">{{
							r[c.fieldname] ? thai_date(r[c.fieldname], { year: true }) : "—"
						}}</template>
						<template v-else-if="c.fieldtype === 'Currency'">{{
							money(r[c.fieldname])
						}}</template>
						<template v-else-if="c.fieldtype === 'Float'">{{ num(r[c.fieldname]) }}</template>
						<template v-else>{{ r[c.fieldname] ?? "—" }}</template>
					</td>
					<ModifiedCell :value="r.modified" :row="r" />
				</tr>
				<tr class="is-static">
					<td v-for="(c, i) in data.columns" :key="c.fieldname" :class="{ 'is-num': is_num(c) }">
						<b v-if="i === 0">รวม</b>
						<b v-else-if="c.fieldname === 'tax_base' || c.fieldname === 'tax_amount'">{{
							money(data.totals[c.fieldname])
						}}</b>
					</td>
					<td class="col-modified"></td>
				</tr>
			</tbody>
		</table>
	</div>
</template>

<script setup>
import { ref } from "vue";
import { money, num, thai_date } from "../../../shared/api.js";
import ModifiedCell from "../../../shared/components/ModifiedCell.vue";
defineProps({ data: Object });
defineEmits(["open"]);
const table = ref(null);
const is_num = (c) => ["Currency", "Float", "Int"].includes(c.fieldtype);
defineExpose({ table });
</script>
