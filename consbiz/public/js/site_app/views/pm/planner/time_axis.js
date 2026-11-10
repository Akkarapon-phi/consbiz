// แกนเวลาของหน้าแผนงาน: ใช้ร่วมกันระหว่างตารางงาน (PlanSheet.vue) และ Gantt ทรัพยากร (ResourceBoard.vue)
// คิดตำแหน่งผ่าน x() / axis.day_at() เสมอ ห้ามคูณ ppd ตรงๆ เพราะบางมุมมองทุกช่องกว้างเท่ากัน
import { computed } from "vue";
import { floor_to, next_of, periods, to_day, today } from "../../../../construction_management/schedule.js";

export const MONTHS = ["ม.ค.", "ก.พ.", "มี.ค.", "เม.ย.", "พ.ค.", "มิ.ย.", "ก.ค.", "ส.ค.", "ก.ย.", "ต.ค.", "พ.ย.", "ธ.ค."];
// จำนวนวันเฉลี่ยต่อช่อง ของมุมมองที่ให้ทุกช่องกว้างเท่ากัน
const EQUAL_CELL_DAYS = { mweek: 7.6, month: 30.4 };
const SCALES = {
	day: { px: 48, top: "month", bottom: "day", pad: 5 },
	week: { px: 14, top: "month", bottom: "week", pad: 14 },
	month: { px: 4.4, top: "year", bottom: "month", pad: 31 },
};

// p = ref/computed ของ planner, settings = { scale, zoom }, extra_days = วันที่ต้องอยู่บนแกนเพิ่ม (เช่นวันต้องสั่งวัสดุ)
export function use_time_axis(p, settings, extra_days = () => []) {
	const today_day = today();

	const scale = computed(() => {
		const config = SCALES[settings.scale] || SCALES.week;
		const bottom = config.bottom === "week" && p.value.data?.week_by_month ? "mweek" : config.bottom;
		return { ...config, bottom };
	});
	const ppd = computed(() => scale.value.px * settings.zoom);
	const range = computed(() => {
		const days = p.value.tasks
			.flatMap((t) => [t.start_date, t.end_date, t.baseline_start_date, t.baseline_end_date])
			.map(to_day)
			.filter((d) => d !== null);
		days.push(...extra_days());
		const first = days.length ? Math.min(...days) : to_day(p.value.data?.start_date) ?? today_day;
		const last = days.length ? Math.max(...days, today_day) : first + 60;
		const { top, pad } = scale.value;
		return { start: floor_to(Math.min(first, today_day) - pad, top), end: next_of(floor_to(last + pad, top), top) };
	});
	// แกนเวลา: รายวัน/สัปดาห์จันทร์-อาทิตย์ = วันละเท่ากัน, สัปดาห์แบ่งในเดือน/รายเดือน = ทุกช่องกว้างเท่ากัน (ในช่องแบ่งตามจำนวนวันของช่องนั้น)
	// คิดตำแหน่งผ่าน x() / axis.day_at() เสมอ ห้ามคูณ ppd ตรงๆ
	const axis = computed(() => {
		const { start, end } = range.value;
		const px = ppd.value;
		const { bottom } = scale.value;
		const key = `${bottom}|${px}|${start}`;
		if (!EQUAL_CELL_DAYS[bottom]) {
			return { key, width: (end - start) * px, x: (day) => (day - start) * px, day_at: (left) => left / px + start };
		}
		const cells = periods(start, end, bottom);
		const cell_w = Math.round(EQUAL_CELL_DAYS[bottom] * px);
		const index_of = (day) => {
			let low = 0;
			let high = cells.length - 1;
			while (low < high) {
				const mid = Math.ceil((low + high) / 2);
				if (cells[mid].start <= day) low = mid;
				else high = mid - 1;
			}
			return low;
		};
		return {
			key,
			width: cells.length * cell_w,
			x(day) {
				const i = index_of(day);
				return (i + (day - cells[i].start) / (cells[i].end - cells[i].start)) * cell_w;
			},
			day_at(left) {
				const i = Math.min(Math.max(Math.floor(left / cell_w), 0), cells.length - 1);
				return cells[i].start + (left / cell_w - i) * (cells[i].end - cells[i].start);
			},
		};
	});
	const timeline_w = computed(() => axis.value.width);
	const x = (day) => axis.value.x(day);
	const day_mid = (day) => (x(day) + x(day + 1)) / 2;
	const span = (start, end) => ({ left: `${x(start)}px`, width: `${Math.max(x(end + 1) - x(start), 4)}px` });

	function label(period, unit, top) {
		const date = period.date;
		const m = date.getUTCMonth();
		const y = date.getUTCFullYear() + 543;
		switch (unit) {
			case "day":
				return date.getUTCDate();
			case "week":
				return `${date.getUTCDate()}/${m + 1}`;
			case "mweek":
				return `W${Math.min(Math.floor((date.getUTCDate() - 1) / 7), 3) + 1}`;
			case "month":
				return top ? `${MONTHS[m]} ${y}` : MONTHS[m];
			default:
				return String(y);
		}
	}
	const top_periods = computed(() =>
		periods(range.value.start, range.value.end, scale.value.top).map((period) => ({
			...period,
			label: label(period, scale.value.top, true),
		}))
	);
	const bottom_periods = computed(() =>
		periods(range.value.start, range.value.end, scale.value.bottom).map((period) => ({
			...period,
			label: label(period, scale.value.bottom, false),
			today: today_day >= period.start && today_day < period.end && scale.value.bottom === "day",
			off: scale.value.bottom === "day" && p.value.holidays.has(period.start),
		}))
	);

	// วันหยุดแรเงาเมื่อช่องวันกว้างพอ
	const off_days = computed(() =>
		ppd.value < 6
			? []
			: [...p.value.holidays].filter((day) => day >= range.value.start && day < range.value.end)
	);

	return { scale, ppd, range, axis, timeline_w, x, day_mid, span, top_periods, bottom_periods, off_days };
}
