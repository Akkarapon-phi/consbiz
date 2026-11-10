// ข้อมูลของหน้าการเงิน: ทุก tab ใช้ชุดเดียวกัน สลับ tab ไม่โหลดใหม่ (โหลดซ้ำเมื่อเปลี่ยนโครงการ/วันที่ เกิน FRESH_MS หรือกดโหลดใหม่)
import { reactive } from "vue";
import { boot, call, iso_date, show_error } from "../../../shared/api.js";

const FRESH_MS = 60000;
export const today = () => boot.today || iso_date(new Date());

// data: undefined = ยังไม่โหลด, null = โครงการยังไม่มีแผนงาน
export const finance = reactive({ project: null, date: today(), data: undefined, loading: false, loaded_at: 0 });

export async function load_finance(project, { date = finance.date, force = false } = {}) {
	const same = finance.project === project && finance.date === date;
	if (same && !force && finance.data !== undefined && Date.now() - finance.loaded_at < FRESH_MS) return;
	if (finance.project !== project) finance.data = undefined;
	finance.project = project;
	finance.date = date;
	finance.loading = true;
	try {
		finance.data = await call("consbiz.site_app.get_project_finance", { project, date });
		finance.loaded_at = Date.now();
	} catch (error) {
		show_error(error);
		finance.data ??= null;
	} finally {
		finance.loading = false;
	}
}
