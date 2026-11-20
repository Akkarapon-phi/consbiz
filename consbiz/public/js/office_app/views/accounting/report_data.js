import { ref, watch } from "vue";
import { call, scope_args, show_error } from "../../../shared/api.js";

export function report_scope() {
	const { company, project } = scope_args();
	return Object.fromEntries(Object.entries({ company, project }).filter(([, value]) => value));
}

export function use_report(method, args) {
	const data = ref(null);
	const failed = ref(false);
	let latest = 0;
	async function load() {
		const request = ++latest;
		data.value = null;
		failed.value = false;
		try {
			const result = await call(method, args());
			if (request === latest) data.value = result;
		} catch (error) {
			if (request === latest) {
				failed.value = true;
				show_error(error);
			}
		}
	}
	watch(() => JSON.stringify(args()), load, { immediate: true });
	return { data, failed, load };
}
