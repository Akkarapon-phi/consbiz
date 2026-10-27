// คำนวณวันที่และ % ของแผนงานฝั่งหน้าจอ (ตรงกับ construction_management.py)
// วันที่ทั้งหมดเก็บเป็นเลขวัน (จำนวนวันนับจาก 1970-01-01 แบบ UTC) เพื่อไม่ต้องสนใจ timezone

const DAY_MS = 86400000;

export function to_day(date) {
	if (!date) return null;
	const [y, m, d] = String(date).slice(0, 10).split("-").map(Number);
	return Date.UTC(y, m - 1, d) / DAY_MS;
}

export function from_day(day) {
	return new Date(day * DAY_MS).toISOString().slice(0, 10);
}

export function day_to_date(day) {
	return new Date(day * DAY_MS);
}

// จำนวนวันรวมวันเริ่มและวันจบ ไม่นับวันใน holidays (Set ของเลขวัน)
export function count_days(start, end, holidays) {
	const days = end - start + 1;
	if (days <= 0) return 0;
	if (!holidays.size) return days;
	let count = 0;
	for (let d = start; d <= end; d++) if (!holidays.has(d)) count++;
	return count;
}

// วันจบของงานที่เริ่ม start และใช้เวลา duration วัน
export function end_of(start, duration, holidays) {
	let remaining = Math.max(duration, 1);
	for (let d = start; ; d++) {
		if (!holidays.has(d) && --remaining <= 0) return d;
	}
}

// วันเริ่ม/จบ/จำนวนวันของแถวกลุ่มจากงานย่อย
export function roll_up(tasks, holidays) {
	tasks.forEach((task, i) => {
		if (!task.is_group) return;
		let start = null;
		let end = null;
		for (const child of tasks.slice(i + 1)) {
			if (child.indent <= task.indent) break;
			if (child.is_group) continue;
			const s = to_day(child.start_date);
			const e = to_day(child.end_date);
			if (s !== null && (start === null || s < start)) start = s;
			if (e !== null && (end === null || e > end)) end = e;
		}
		task.start_date = start === null ? null : from_day(start);
		task.end_date = end === null ? null : from_day(end);
		task.duration = start === null || end === null ? 0 : count_days(start, end, holidays);
	});
}

// ---------- งานก่อนหน้า (ตรงกับ apply_dependencies ใน construction_management.py) ----------
// predecessors ของงานเก็บเป็น JSON [{ task, type, lag }] task = name ของแถวงานก่อนหน้า, type = FS/SS/FF/SF
// lag = วันทำงาน (ติดลบ = ซ้อนกันได้) งานที่มีงานก่อนหน้าเริ่มวันเร็วสุดที่ความสัมพันธ์ยอมเสมอ (ASAP)
// อยากให้เริ่มช้ากว่านั้นใช้ lag: ลาก/แก้วันเริ่มของงานที่มีงานก่อนหน้าแปลงเป็น lag ด้วย hold_start

export function parse_predecessors(value) {
	if (!value) return [];
	try {
		const parsed = typeof value === "string" ? JSON.parse(value) : value;
		return Array.isArray(parsed) ? parsed : [];
	} catch {
		return [];
	}
}

// เลื่อนวันไป days วันทำงาน (ติดลบ = ย้อนหลัง) ข้ามวันใน holidays 0 = วันเดิม
export function shift_days(day, days, holidays) {
	const step = days > 0 ? 1 : -1;
	for (let i = 0; i < Math.abs(days); i++) {
		day += step;
		while (holidays.has(day)) day += step;
	}
	return day;
}

// งานย่อยเรียงให้งานก่อนหน้ามาก่อนเสมอ คืน null ถ้าผูกกันเป็นวง
export function dependency_order(tasks) {
	const leaves = tasks.filter((t) => !t.is_group);
	const names = new Set(leaves.map((t) => t.name));
	const waiting = new Map();
	const successors = new Map();
	for (const task of leaves) {
		const links = parse_predecessors(task.predecessors).filter((link) => names.has(link.task));
		waiting.set(task.name, links.length);
		for (const link of links) {
			if (!successors.has(link.task)) successors.set(link.task, []);
			successors.get(link.task).push(task);
		}
	}
	const ordered = leaves.filter((t) => !waiting.get(t.name));
	// ต่อท้ายระหว่างวน: งานที่งานก่อนหน้าครบแล้ว
	for (let i = 0; i < ordered.length; i++) {
		for (const next of successors.get(ordered[i].name) || []) {
			waiting.set(next.name, waiting.get(next.name) - 1);
			if (!waiting.get(next.name)) ordered.push(next);
		}
	}
	return ordered.length === leaves.length ? ordered : null;
}

// วันเริ่มเร็วสุดของงานตามลิงก์เดียว (null = งานก่อนหน้ายังไม่มีวันที่)
// FS: เริ่มวันทำงานถัดจากวันจบ, SS: เริ่มวันเดียวกัน, FF: จบวันเดียวกัน, SF: จบวันทำงานก่อนวันเริ่ม แล้วเลื่อนอีก lag
export function link_start(task, link, by_name, holidays) {
	const predecessor = by_name.get(link.task);
	const start = to_day(predecessor?.start_date);
	const end = to_day(predecessor?.end_date);
	if (start === null || end === null) return null;
	const lag = link.lag || 0;
	if (link.type === "SS") return shift_days(start, lag, holidays);
	if (link.type === "FF" || link.type === "SF") {
		const finish =
			link.type === "FF"
				? shift_days(end, lag, holidays)
				: shift_days(start, lag - 1, holidays);
		return shift_days(finish, 1 - Math.max(task.duration || 0, 1), holidays);
	}
	return shift_days(end, lag + 1, holidays);
}

// วันเริ่มเร็วสุดของงานตามงานก่อนหน้าทุกงาน (null = ไม่มีความสัมพันธ์ที่ใช้ได้)
export function earliest_start(task, by_name, holidays) {
	const days = parse_predecessors(task.predecessors)
		.map((link) => link_start(task, link, by_name, holidays))
		.filter((day) => day !== null);
	return days.length ? Math.max(...days) : null;
}

// ปรับ lag ให้งานเริ่มวันเริ่มปัจจุบันพอดี (ผู้ใช้ลากหรือแก้วันที่ของงานที่มีงานก่อนหน้า)
// ลิงก์ที่บังคับให้เริ่มช้ากว่าวันนั้นลด lag ลงมา ถ้าทุกลิงก์ยอมให้เริ่มเร็วกว่า เพิ่ม lag ของลิงก์ที่กำหนดวันเริ่มอยู่
// คืน true ถ้า lag เปลี่ยน
export function hold_start(task, by_name, holidays) {
	const start = to_day(task.start_date);
	if (start === null) return false;
	const links = parse_predecessors(task.predecessors);
	const days = links.map((link) => link_start(task, link, by_name, holidays));
	const placed = days.filter((day) => day !== null);
	if (!placed.length) return false;
	const latest = Math.max(...placed);
	let changed = false;
	links.forEach((link, i) => {
		const day = days[i];
		if (day === null || !(day > start || (latest < start && day === latest))) return;
		// จำนวนวันทำงานจาก day ถึง start (ติดลบถ้า start มาก่อน)
		link.lag =
			(link.lag || 0) +
			(start > day
				? count_days(day + 1, start, holidays)
				: -count_days(start, day - 1, holidays));
		changed = true;
	});
	if (changed) task.predecessors = JSON.stringify(links);
	return changed;
}

// งานที่มีงานก่อนหน้าเริ่มวันเร็วสุดที่ความสัมพันธ์ยอม (คงจำนวนวันเดิม) คืนงานที่ถูกเลื่อน หรือ null ถ้าผูกกันเป็นวง
export function apply_dependencies(tasks, holidays) {
	const order = dependency_order(tasks);
	if (!order) return null;
	const by_name = new Map(tasks.map((t) => [t.name, t]));
	const moved = [];
	for (const task of order) {
		const required = earliest_start(task, by_name, holidays);
		const start = to_day(task.start_date);
		if (required === null || start === required) continue;
		const end = end_of(required, Math.max(task.duration || 0, 1), holidays);
		task.start_date = from_day(required);
		task.end_date = from_day(end);
		task.duration = count_days(required, end, holidays);
		moved.push(task);
	}
	return moved;
}

// ข้อความงานก่อนหน้า เช่น "1.2, 1.3SS+2, 2.1FF-1" (FS ที่ไม่มี lag แสดงแค่ WBS)
export function format_predecessors(value, by_name) {
	return parse_predecessors(value)
		.map((link) => {
			const wbs = by_name.get(link.task)?.wbs;
			if (!wbs) return null;
			const lag = link.lag > 0 ? `+${link.lag}` : link.lag < 0 ? `${link.lag}` : "";
			return `${wbs}${link.type !== "FS" || lag ? link.type : ""}${lag}`;
		})
		.filter(Boolean)
		.join(", ");
}

// S-Curve จากวันที่ของงาน (แผนปัจจุบันหรือ baseline) แล้วสะสม
// งานปกติกระจายน้ำหนักเท่าๆ กันทุกวันทำงาน งานที่กำหนด % เองกระจายตาม % ของแต่ละช่วง (task_daily)
// น้ำหนัก = มูลค่าที่นับ / มูลค่าสัญญาปรับปรุง (baseline ใช้น้ำหนักที่เก็บไว้ตอนตั้ง baseline)
// คืน { start, cumulative } โดย cumulative[i] = % สะสม ณ สิ้นวัน start + i
export function curve_of(
	tasks,
	holidays,
	start_key = "start_date",
	end_key = "end_date",
	distribution_key = "plan_distribution",
	weight_key = "weight"
) {
	const leaves = tasks
		.filter((t) => !t.is_group && t[start_key] && t[end_key] && t[weight_key])
		.map((t) => ({
			start: to_day(t[start_key]),
			end: to_day(t[end_key]),
			weight: t[weight_key],
			distribution: parse_distribution(t[distribution_key]),
		}));
	if (!leaves.length) return null;

	const start = Math.min(...leaves.map((t) => t.start));
	const end = Math.max(...leaves.map((t) => t.end));
	const daily = new Array(end - start + 1).fill(0);
	for (const task of leaves) {
		for (const [day, fraction] of task_daily(
			task.start,
			task.end,
			task.distribution,
			holidays
		)) {
			daily[day - start] += task.weight * fraction;
		}
	}
	return { start, cumulative: accumulate(daily) };
}

// ---------- กำหนด % แผนเองรายช่วง ----------
// plan_distribution ของงานเก็บเป็น JSON { unit, weights } เช่น { unit: "week", weights: [10, 20, 30, 40] }
// weights[i] = % ของช่วงที่ i ของงาน (ช่วงตัดตามขอบ unit ดู segments) รวมกันได้ 100

export function parse_distribution(value) {
	if (!value) return null;
	try {
		const parsed = typeof value === "string" ? JSON.parse(value) : value;
		return parsed && parsed.unit && Array.isArray(parsed.weights) ? parsed : null;
	} catch {
		return null;
	}
}

// ตัดช่วงงาน [start, end] ตามขอบของ unit เช่นงาน 5-20 แบ่งสัปดาห์ 7-7-7 ได้ [5-7], [8-14], [15-20]
export function segments(start, end, unit) {
	const result = [];
	let from = start;
	while (from <= end) {
		const to = Math.min(next_of(floor_to(from, unit), unit) - 1, end);
		result.push({ start: from, end: to });
		from = to + 1;
	}
	return result;
}

// สัดส่วนงานรายวัน [[วัน, สัดส่วน]] รวมกันได้ 1
// ไม่ได้กำหนดเอง (หรือจำนวนช่วงไม่ตรงกับวันที่ปัจจุบัน) = เท่ากันทุกวันทำงาน
// กำหนดเอง = % ของแต่ละช่วงกระจายเท่าๆ กันในวันทำงานของช่วงนั้น
export function task_daily(start, end, distribution, holidays) {
	const parts = distribution ? segments(start, end, distribution.unit) : null;
	if (!parts || parts.length !== distribution.weights.length) {
		const days = working_days_of(start, end, holidays);
		return days.map((d) => [d, 1 / days.length]);
	}
	const result = [];
	parts.forEach((part, i) => {
		const days = working_days_of(part.start, part.end, holidays);
		const fraction = (distribution.weights[i] || 0) / 100 / days.length;
		for (const d of days) result.push([d, fraction]);
	});
	return result;
}

// % ของงานในแต่ละช่องเวลาที่ดูอยู่ (unit) คิดจากสัดส่วนรายวันของ task_daily
// เช่นกำหนดไว้รายสัปดาห์ 20/30/50 แล้วดูรายวัน จะได้ % ของแต่ละวันที่รวมกันเป็นของสัปดาห์นั้น
export function period_shares(start, end, distribution, holidays, unit) {
	const daily = task_daily(start, end, distribution, holidays);
	return segments(start, end, unit).map((part) => ({
		...part,
		percent:
			daily
				.filter(([day]) => day >= part.start && day <= part.end)
				.reduce((sum, [, fraction]) => sum + fraction, 0) * 100,
	}));
}

// การกำหนดเองยังใช้กับวันที่ใหม่ได้ไหม (จำนวนช่วงต้องเท่าเดิม)
export function distribution_fits(start, end, distribution) {
	return (
		Boolean(distribution) &&
		segments(start, end, distribution.unit).length === distribution.weights.length
	);
}

// งานเดิมนับเสมอ งานเพิ่มนับเมื่อผู้ว่าจ้างอนุมัติแล้ว (ตรงกับ is_counted ใน construction_management.py)
export function is_counted(task) {
	return !task.is_variation || Boolean(task.counted_from);
}

// S-Curve จริงแบบ Earned Value: มูลค่างานที่ทำแล้วสะสม ÷ มูลค่าสัญญา ณ วันนั้น
// - มูลค่าของรายการ = % ของรายการ × มูลค่างาน (= ปริมาณ × ราคาต่อหน่วย)
// - งานเพิ่มนับตั้งแต่วันที่ผู้ว่าจ้างอนุมัติ (ทำก่อนอนุมัติ = นับ ณ วันอนุมัติ)
// - มูลค่าสัญญา = สัญญาเดิม + งานเพิ่ม-ลดของ VO ที่อนุมัติถึงวันนั้น (steps: [{ date, amount }])
//   % จึงขยับตอนอนุมัติ VO แต่ % ของวันก่อนหน้าไม่เปลี่ยน
// ลากเส้นถึงวัน until (ปกติคือวันนี้) หรือถึงรายการสุดท้ายถ้าเลยวันนี้
// คืน { start, cumulative, money } money[i] = มูลค่างานสะสม (บาท) ณ สิ้นวัน start + i
export function actual_curve(tasks, entries, until, contract_amount, steps = []) {
	const leaves = new Map(
		tasks.filter((t) => !t.is_group && is_counted(t)).map((t) => [t.name, t])
	);
	const items = entries
		.filter((e) => leaves.has(e.task) && e.percent)
		.map((e) => {
			const task = leaves.get(e.task);
			const day = to_day(e.date);
			const from = to_day(task.counted_from);
			return {
				day: from !== null && day < from ? from : day,
				value: ((task.amount || 0) * e.percent) / 100,
			};
		});
	if (!items.length) return null;

	const start = Math.min(...items.map((e) => e.day));
	const end = Math.max(until, ...items.map((e) => e.day));
	const daily = new Array(end - start + 1).fill(0);
	for (const item of items) daily[item.day - start] += item.value;
	const money = accumulate(daily);

	const changes = steps.map((s) => ({ day: to_day(s.date), amount: s.amount || 0 }));
	const cumulative = money.map((value, i) => {
		const total = changes
			.filter((c) => c.day !== null && c.day <= start + i)
			.reduce((sum, c) => sum + c.amount, contract_amount || 0);
		return total ? (value / total) * 100 : 0;
	});
	return { start, cumulative, money };
}

// ค่าสะสม ณ สิ้นวัน day (null = ไม่มีเส้น หรือวันนั้นเลยปลายเส้นจริงไปแล้ว)
export function value_at(curve, day, { clip_end = false } = {}) {
	if (!curve) return null;
	if (day < curve.start) return 0;
	const index = day - curve.start;
	if (index >= curve.cumulative.length) return clip_end ? null : curve.cumulative.at(-1);
	return curve.cumulative[index];
}

export function curve_end(curve) {
	return curve ? curve.start + curve.cumulative.length - 1 : null;
}

// จุดของเส้น S-Curve ที่ปลายแต่ละช่องเวลา (และปลายเส้นจริง) ใช้วาดทั้งหน้าจอและงานพิมพ์
// day = วันที่จุดนั้นแทน (x คือปลายวันนั้น)
export function sample_curve(curve, periods) {
	if (!curve) return [];
	const end = curve_end(curve);
	const points = [];
	for (const period of periods) {
		if (period.end - 1 < curve.start) continue;
		if (!points.length) points.push({ day: curve.start - 1, value: 0 });
		const day = Math.min(period.end - 1, end);
		points.push({ day, value: value_at(curve, day) });
		if (period.end - 1 >= end) break;
	}
	return points;
}

// ค่าในตารางสรุปของช่วงเวลาหนึ่ง (ช่วงที่อยู่นอกเส้นได้ null = ช่องว่าง)
// - baseline / plan / actual: % สะสม ณ ปลายช่วง, *_period: % ที่เพิ่มในช่วงนั้น (ผลต่างของ % สะสม
//   เส้นจริงติดลบได้ในช่วงที่อนุมัติงานเพิ่ม เพราะมูลค่าสัญญาเพิ่ม)
// - cash_plan / cash_actual: มูลค่างาน (บาท) ตามแผน/ที่ทำจริงในช่วงนั้น, *_cum: มูลค่าสะสม ณ ปลายช่วง
//   เส้นจริงมีมูลค่าสะสม (money) ของตัวเอง เส้นแผนคิดจาก % × มูลค่าสัญญาปรับปรุง (total_amount)
export function summary_values(period, curves, total_amount) {
	const day = period.end - 1;
	const inside = (curve) => curve && day >= curve.start && period.start <= curve_end(curve);
	const percent = (curve) => (inside(curve) ? value_at(curve, day) : null);
	const money_at = (curve, d) =>
		curve.money
			? value_at({ start: curve.start, cumulative: curve.money }, d)
			: (value_at(curve, d) / 100) * (total_amount || 0);
	const money = (curve) => (inside(curve) ? money_at(curve, day) : null);
	const change = (curve) =>
		inside(curve) ? money_at(curve, day) - money_at(curve, period.start - 1) : null;
	const percent_change = (curve) =>
		inside(curve) ? value_at(curve, day) - value_at(curve, period.start - 1) : null;
	return {
		baseline: percent(curves.baseline),
		plan: percent(curves.plan),
		actual: percent(curves.actual),
		baseline_period: percent_change(curves.baseline),
		plan_period: percent_change(curves.plan),
		actual_period: percent_change(curves.actual),
		cash_plan: change(curves.plan),
		cash_plan_cum: money(curves.plan),
		cash_actual: change(curves.actual),
		cash_actual_cum: money(curves.actual),
	};
}

// เส้นโค้งผ่านทุกจุดแบบ monotone cubic (Fritsch-Carlson): โค้งนุ่มแต่ไม่เกินจุดจริงและไม่ย้อนลง
// points = [[x, y], ...] เรียงตาม x คืน path "M ... C ..." ของ SVG
export function smooth_path(points) {
	const n = points.length;
	if (n < 3) return points.map(([x, y], i) => `${i ? "L" : "M"}${x},${y}`).join(" ");
	const slopes = [];
	for (let i = 0; i < n - 1; i++) {
		const dx = points[i + 1][0] - points[i][0];
		slopes.push(dx ? (points[i + 1][1] - points[i][1]) / dx : 0);
	}
	const tangents = points.map((_, i) => {
		if (i === 0) return slopes[0];
		if (i === n - 1) return slopes[n - 2];
		return slopes[i - 1] * slopes[i] <= 0 ? 0 : (slopes[i - 1] + slopes[i]) / 2;
	});
	for (let i = 0; i < n - 1; i++) {
		if (!slopes[i]) {
			tangents[i] = tangents[i + 1] = 0;
			continue;
		}
		const a = tangents[i] / slopes[i];
		const b = tangents[i + 1] / slopes[i];
		const length = a * a + b * b;
		if (length > 9) {
			const t = 3 / Math.sqrt(length);
			tangents[i] = t * a * slopes[i];
			tangents[i + 1] = t * b * slopes[i];
		}
	}
	let path = `M${points[0][0]},${points[0][1]}`;
	for (let i = 0; i < n - 1; i++) {
		const [x0, y0] = points[i];
		const [x1, y1] = points[i + 1];
		const h = (x1 - x0) / 3;
		path += ` C${x0 + h},${y0 + tangents[i] * h} ${x1 - h},${
			y1 - tangents[i + 1] * h
		} ${x1},${y1}`;
	}
	return path;
}

// % แผนของงานเดียว ณ สิ้นวัน day
export function plan_percent(start_date, end_date, day, holidays, distribution = null) {
	const start = to_day(start_date);
	const end = to_day(end_date);
	if (start === null || end === null || day < start) return 0;
	if (day >= end) return 100;
	let done = 0;
	for (const [d, fraction] of task_daily(
		start,
		end,
		parse_distribution(distribution),
		holidays
	)) {
		if (d <= day) done += fraction;
	}
	return done * 100;
}

// วันทำงานของช่วง ถ้าทั้งช่วงเป็นวันหยุดให้นับวันปฏิทินแทน
function working_days_of(start, end, holidays) {
	const all = [];
	for (let d = start; d <= end; d++) all.push(d);
	const working = all.filter((d) => !holidays.has(d));
	return working.length ? working : all;
}

function accumulate(daily) {
	let total = 0;
	return daily.map((value) => (total += value));
}

// แบ่งช่วงเวลาสำหรับหัว timeline
// unit: day | week (เริ่มวันจันทร์) | mweek (สัปดาห์ในเดือน 1-7, 8-14, 15-21, 22-สิ้นเดือน) | month | quarter | year
// คืน [{ start, end (ไม่รวม), date }]
export function periods(range_start, range_end, unit) {
	const result = [];
	let start = floor_to(range_start, unit);
	while (start < range_end) {
		const end = next_of(start, unit);
		result.push({ start, end, date: day_to_date(start) });
		start = end;
	}
	return result;
}

export function floor_to(day, unit) {
	const date = day_to_date(day);
	const y = date.getUTCFullYear();
	const m = date.getUTCMonth();
	switch (unit) {
		case "week":
			// สัปดาห์เริ่มวันจันทร์ (1970-01-01 เป็นวันพฤหัส)
			return day - ((day + 3) % 7);
		case "mweek":
			return (
				Date.UTC(y, m, Math.min(Math.floor((date.getUTCDate() - 1) / 7), 3) * 7 + 1) /
				DAY_MS
			);
		case "month":
			return Date.UTC(y, m, 1) / DAY_MS;
		case "quarter":
			return Date.UTC(y, m - (m % 3), 1) / DAY_MS;
		case "year":
			return Date.UTC(y, 0, 1) / DAY_MS;
		default:
			return day;
	}
}

export function next_of(day, unit) {
	const date = day_to_date(day);
	const y = date.getUTCFullYear();
	const m = date.getUTCMonth();
	switch (unit) {
		case "week":
			return day + 7;
		case "mweek": {
			// ช่วงสุดท้ายของเดือน (เริ่มวันที่ 22) ยาวถึงสิ้นเดือน
			const start = floor_to(day, "mweek");
			return day_to_date(start).getUTCDate() >= 22
				? Date.UTC(y, m + 1, 1) / DAY_MS
				: start + 7;
		}
		case "month":
			return Date.UTC(y, m + 1, 1) / DAY_MS;
		case "quarter":
			return Date.UTC(y, m + 3, 1) / DAY_MS;
		case "year":
			return Date.UTC(y + 1, 0, 1) / DAY_MS;
		default:
			return day + 1;
	}
}

export function today() {
	return to_day(frappe.datetime.get_today());
}
