import { computed, ref, watch } from "vue";
import { call, iso_date, show_error, state } from "../../../shared/api.js";
import { API } from "./kinds.js";
import { report_scope } from "./report_data.js";

const month_of = (date) => iso_date(date).slice(0, 7);

export function use_tax_period() {
	const saved = state.route.params.month || "";
	const month = ref(
		/^(20\d\d|2[1-6]\d\d|2700)-(0[1-9]|1[0-2])$/.test(saved) ? saved : month_of(new Date())
	);
	const address = ref(state.route.params.address || null);
	const addresses = ref([]);
	const ym = computed(() => month.value.split("-").map(Number));
	const list_params = computed(() => ({
		year: ym.value[0],
		month: ym.value[1],
		company_address: address.value,
	}));
	const period = computed(() =>
		new Intl.DateTimeFormat("th-TH", { month: "long", year: "numeric" }).format(
			new Date(ym.value[0], ym.value[1] - 1, 1)
		)
	);

	function shift(step) {
		const [year, m] = ym.value;
		month.value = month_of(new Date(year, m - 1 + step, 1));
	}

	watch(
		() => report_scope().company,
		async (company, _previous, on_cleanup) => {
			let current = true;
			on_cleanup(() => {
				current = false;
			});
			try {
				const { addresses: options } = await call(`${API}.report_options`, { company });
				if (!current) return;
				addresses.value = [{ value: null, label: "ทุกสาขา" }, ...options];
				if (!options.some((option) => option.value === address.value)) address.value = null;
			} catch (error) {
				if (current) show_error(error);
			}
		},
		{ immediate: true }
	);

	return { month, address, addresses, list_params, period, shift };
}
