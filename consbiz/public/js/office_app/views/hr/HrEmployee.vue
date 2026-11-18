<!-- หน้าเต็มของพนักงาน (hr-employee/<รหัส>, API consbiz.hr_people.get_employee) ข้อมูลชุดเดียวกับแผงตัวอย่าง (EmployeePanel.vue) -->
<template>
	<div>
		<TopBar :title="data?.info.employee_name || 'พนักงาน'" back_to="hr-employees" />
		<div class="ss-content">
			<section class="ss-work-card hr-emp-page">
				<EmployeePanel :data="data" />
			</section>
		</div>
	</div>
</template>

<script setup>
import { ref } from "vue";
import TopBar from "../../../shared/components/TopBar.vue";
import EmployeePanel from "./EmployeePanel.vue";
import { call, show_error, state } from "../../../shared/api.js";

const data = ref(null);
call("consbiz.hr_people.get_employee", { name: state.route.params.name })
	.then((result) => (data.value = result))
	.catch(show_error);
</script>

<style scoped>
.hr-emp-page { max-width: 1100px; }
</style>
