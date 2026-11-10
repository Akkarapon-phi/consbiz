// ข้อมูลของหมวดทรัพยากร: ทุกเมนูใช้ planner ตัวเดียว สลับเมนูไม่โหลดแผนใหม่ (โหลดซ้ำเมื่อเกิน FRESH_MS หรือกดโหลดใหม่)
// API get_resource_board ส่งแค่รายการและวันที่ ไม่มีมูลค่างาน จึงเปิดให้ทุกคนของหน้างานดูได้
import { effectScope, ref } from "vue";
import { call, show_error } from "../../../shared/api.js";
import { create_planner } from "../pm/planner/planner.js";

const FRESH_MS = 60000;
let board = null;

export function resource_board(project) {
	if (board?.project === project) return board;
	// planner อยู่นานกว่าหน้าที่สร้าง: แยก scope ไม่ให้ computed/watch หยุดตอนหน้าถูกปิด
	const planner = effectScope(true).run(() =>
		create_planner({
			readonly: true,
			loader: (name) => call("consbiz.site_app.get_resource_board", { project: name }),
		})
	);
	board = { project, planner, loaded: ref(false), loaded_at: 0 };
	return board;
}

export async function load_board(target, { force = false } = {}) {
	if (!force && Date.now() - target.loaded_at < FRESH_MS) return;
	try {
		await target.planner.load(target.project);
		target.loaded_at = Date.now();
	} catch (error) {
		show_error(error);
	} finally {
		target.loaded.value = true;
	}
}
