// ข้อมูลของ Gantt ทรัพยากร (ResourceBoard.vue) และสรุปรายเดือน (ResourceMonthly.vue) คำนวณจาก planner.js ชุดเดียวกับแผงทรัพยากร
// วันต้องสั่ง/ของต้องถึง/ต้องจอง ใช้ฟังก์ชันใน schedule.js ชุดเดียวกับหน้า Gantt ทรัพยากรของระบบเต็ม (ResourceGantt.vue)
import { num, thai_date } from "../../../../shared/api.js";
import {
	book_by,
	day_to_date,
	from_day,
	is_requested,
	material_dates,
	material_key,
	parse_distribution,
	resource_daily,
	task_daily,
	to_day,
} from "../../../../construction_management/schedule.js";
import { MONTHS } from "./time_axis.js";

// ตรงกับ PREP_DUE_DAYS ใน construction_management/columns.js (ไฟล์นั้นใช้ __ ของ desk จึง import ในแอปไม่ได้)
export const PREP_DUE_DAYS = 14;

const TYPES = [
	{ key: "Material", label: "วัสดุ", icon: "cart" },
	{ key: "Labour", label: "แรงงาน", icon: "users", unit: "คน/วัน", total_unit: "คน-วัน" },
	{ key: "Equipment", label: "เครื่องจักร", icon: "truck", unit: "คัน/วัน", total_unit: "คัน-วัน" },
];

const date_text = (day) => (day === null || day === undefined ? "-" : thai_date(from_day(day), { year: true }));

function due_tone(target, pending, day) {
	if (!pending) return "green";
	if (target === null) return "gray";
	if (target <= day) return "rose";
	return target - day <= PREP_DUE_DAYS ? "amber" : "gray";
}

// ป้ายจำนวนวันที่เหลือก่อนถึงวันต้องจอง/ต้องสั่ง (day = วันที่ใช้เทียบ)
export function due_pill(target, day) {
	if (target === null) return { tone: "gray", label: "ยังไม่มีวันเริ่มงาน" };
	const days = target - day;
	if (days < 0) return { tone: "rose", label: `เลยกำหนด ${-days} วัน` };
	if (days === 0) return { tone: "rose", label: "วันนี้" };
	return { tone: days <= PREP_DUE_DAYS ? "amber" : "gray", label: `อีก ${days} วัน` };
}

// ขอครบแล้วแสดงขั้นล่าสุด (ผู้ว่าจ้างจัดหาใช้คำของผู้ว่าจ้าง) ไม่งั้นนับวันถึงวันต้องสั่ง
export function material_pill(row, coverage, order_by, day) {
	const owner = Boolean(row.customer_provided);
	switch (coverage?.state) {
		case "received":
			return { tone: "green", label: owner ? "ผู้ว่าจ้างส่งแล้ว" : "รับแล้ว" };
		case "ordered":
			return { tone: "green", label: owner ? "ขอผู้ว่าจ้างแล้ว" : "สั่งซื้อแล้ว" };
		case "requested":
			return { tone: "blue", label: owner ? "ขอผู้ว่าจ้างแล้ว" : "ขอซื้อแล้ว" };
		default:
			return due_pill(order_by, day);
	}
}

function rows_of(p, type) {
	return type.key === "Material" ? p.materials : p.resources.filter((row) => row.resource_type === type.key);
}

function usage_of(p, type, row) {
	const task = p.by_name.get(row.task);
	const start = to_day(task?.start_date);
	const end = to_day(task?.end_date);
	const material = type.key === "Material";
	const buffer = p.data?.material_plan?.buffer_days;
	const dates = material ? material_dates(start, buffer, row.lead_time_days) : null;
	const target = material ? dates.order_by : book_by(start, row.lead_time_days);
	const coverage = material ? p.material_coverage.get(material_key(row)) || null : null;
	const pending = material ? !is_requested(coverage) : start === null || start > p.cutoff_day;
	const qty_text = material
		? `${num(row.qty)} ${row.uom || ""}`.trim()
		: `${num(row.qty_per_day)} ${type.unit}`;
	const label = task ? `${task.wbs || ""} ${task.item_name || ""}`.trim() : "(ไม่พบงาน)";
	return {
		key: `u:${row.name || row.key}`,
		kind: "usage",
		type,
		task,
		row,
		start,
		end,
		target,
		required_by: material ? dates.required_by : null,
		tone: due_tone(target, pending, p.cutoff_day),
		coverage,
		shortfall: coverage ? coverage.shortfall : row.qty || 0,
		pill: material ? material_pill(row, coverage, target, p.cutoff_day) : null,
		// ติ๊กขอซื้อได้: วัสดุที่บันทึกในแผนแล้ว ยังขอไม่ครบ และงานมีวันเริ่ม
		requestable: material && pending && Boolean(row.name) && target !== null,
		label,
		qty_text,
		title: [
			label,
			qty_text,
			material ? `ต้องทำเรื่องสั่ง: ${date_text(target)} (Lead Time ${row.lead_time_days || 0} วัน)` : `ต้องจอง: ${date_text(target)}`,
			material ? `ของต้องถึง: ${date_text(dates.required_by)}` : "",
			start === null ? "งานยังไม่มีวันเริ่ม" : `ใช้งาน: ${date_text(start)} – ${date_text(end)}`,
			material && coverage?.requested > 0
				? `ขอแล้ว ${num(coverage.requested)} · สั่งซื้อ ${num(coverage.ordered)} · รับ ${num(coverage.received)}${
						coverage.state === "partial" ? ` · ขาด ${num(coverage.shortfall)}` : ""
				  }`
				: material
				? "ยังไม่ได้ขอซื้อ"
				: pending
				? ""
				: "เริ่มงานแล้ว",
		]
			.filter(Boolean)
			.join("\n"),
	};
}

// ยอดของโครงการแยกซื้อเอง / ผู้ว่าจ้างจัดหา (ตรงกับ supply_text ใน ResourceGantt.vue)
function supply_text(supply, uom) {
	const line = (label, s, ordered) =>
		`${label}: ขอ ${num(s.requested)}${s.draft ? ` (ร่าง ${num(s.draft)})` : ""}${ordered ? ` · สั่งซื้อ ${num(s.ordered)}` : ""} · รับ ${num(s.received)} ${uom}`;
	return [
		supply.purchase?.requested ? line("ซื้อเอง", supply.purchase, true) : "",
		supply.customer?.requested ? line("ผู้ว่าจ้างจัดหา", supply.customer, false) : "",
	]
		.filter(Boolean)
		.join("\n");
}

// สรุปท้ายชื่อของแต่ละ Item: วัสดุ = ยอดรวมและกำหนดสั่งถัดไป, คน/เครื่องจักร = สูงสุดต่อวันและยอดรวม
function item_summary(p, item) {
	if (item.type.key === "Material") {
		const by_uom = new Map();
		for (const row of item.list) by_uom.set(row.uom || "", (by_uom.get(row.uom || "") || 0) + (row.qty || 0));
		const open = item.usages.filter((usage) => usage.tone !== "green");
		const targets = open.filter((usage) => usage.target !== null).map((usage) => usage.target);
		const next = targets.length ? Math.min(...targets) : null;
		const supply = p.data?.material_plan?.supply?.[item.name];
		return {
			summary: [...by_uom].map(([uom, qty]) => `${num(qty)} ${uom}`.trim()).join(" + "),
			tone: due_tone(next, open.length > 0, p.cutoff_day),
			summary_title: [
				item.label,
				open.length ? (next !== null ? `ต้องสั่งครั้งถัดไป: ${date_text(next)}` : "") : "ขอครบแล้ว",
				supply ? supply_text(supply, item.list[0].stock_uom || "") : "",
			]
				.filter(Boolean)
				.join("\n"),
		};
	}
	const values = [...item_daily(p, item).values()];
	const peak = values.length ? Math.max(...values) : 0;
	const total = values.reduce((sum, value) => sum + value, 0);
	return {
		summary: `สูงสุด ${num(peak)} ${item.type.unit}`,
		peak,
		total,
		summary_title: `${item.label}\nรวม ${num(total)} ${item.type.total_unit}`,
	};
}

// [{ key, type, label, items: [{ key, type, label, summary, summary_title, tone, first, last, list, usages }] }]
export function plan_groups(p) {
	const groups = [];
	for (const type of TYPES) {
		const by_name = new Map();
		for (const row of rows_of(p, type)) {
			const name = type.key === "Material" ? row.item_code : row.resource;
			if (!name) continue;
			if (!by_name.has(name)) by_name.set(name, []);
			by_name.get(name).push(row);
		}
		if (!by_name.size) continue;
		const items = [...by_name.entries()]
			.map(([name, list]) => {
				const usages = list
					.map((row) => usage_of(p, type, row))
					.sort((a, b) => (a.start ?? Infinity) - (b.start ?? Infinity));
				const dated = usages.filter((usage) => usage.start !== null);
				const item = {
					key: `r:${type.key}:${name}`,
					kind: "item",
					type,
					name,
					label: type.key === "Material" ? list[0].item_label || name : name,
					list,
					usages,
					first: dated.length ? Math.min(...dated.map((usage) => usage.start)) : null,
					last: dated.length ? Math.max(...dated.map((usage) => usage.end)) : null,
				};
				return { ...item, ...item_summary(p, item) };
			})
			.sort((a, b) => (a.first ?? Infinity) - (b.first ?? Infinity) || a.label.localeCompare(b.label));
		groups.push({ key: `g:${type.key}`, kind: "group", type, label: type.label, items });
	}
	return groups;
}

// แถวของตาราง "วัสดุที่ต้องสั่ง" เรียงตามวันต้องสั่ง bucket: todo (ถึงกำหนดภายใน PREP_DUE_DAYS) / later / done (ขอครบแล้ว)
export function material_orders(p) {
	const usages = plan_groups(p)
		.filter((group) => group.type.key === "Material")
		.flatMap((group) => group.items.flatMap((item) => item.usages));
	return usages
		.map((usage) => ({
			...usage,
			bucket: is_requested(usage.coverage)
				? "done"
				: usage.target !== null && usage.target - p.cutoff_day <= PREP_DUE_DAYS
				? "todo"
				: "later",
		}))
		.sort((a, b) => (a.target ?? Infinity) - (b.target ?? Infinity));
}

// แถวของตารางคน/เครื่องจักร: กำหนดจองครั้งถัดไป = งานแรกที่ยังไม่เริ่ม เรียงที่ต้องจองก่อนขึ้นก่อน
export function people_rows(p) {
	return plan_groups(p)
		.filter((group) => group.type.key !== "Material")
		.flatMap((group) => group.items)
		.map((item) => {
			const next = item.usages
				.filter((usage) => usage.tone !== "green" && usage.target !== null)
				.sort((a, b) => a.target - b.target)[0];
			return { ...item, next, task_count: item.usages.length, pill: next ? due_pill(next.target, p.cutoff_day) : null };
		})
		.sort((a, b) => (a.next?.target ?? Infinity) - (b.next?.target ?? Infinity));
}

// แถวของตาราง "ยอดวัสดุของโครงการ" 1 แถวต่อ Item หน่วยสต็อก (ตรงกับ supply_rows ใน resources.py)
export function material_supply(p) {
	const need = new Map();
	for (const row of p.materials) {
		if (!row.item_code) continue;
		if (!need.has(row.item_code))
			need.set(row.item_code, { item_code: row.item_code, item_label: row.item_label || row.item_code, stock_uom: row.stock_uom, need: 0 });
		need.get(row.item_code).need += (row.qty || 0) * (row.factor || 1);
	}
	const supply = p.data?.material_plan?.supply || {};
	return [...need.values()]
		.map((row) => {
			const { total, purchase, customer } = supply[row.item_code] || {};
			return { ...row, purchase, customer, short: Math.max(row.need - (total?.requested || 0), 0) };
		})
		.sort((a, b) => a.item_label.localeCompare(b.item_label));
}

// วันต้องสั่ง/ต้องจองอาจก่อนวันแรกของแผน: ให้แกนเวลาครอบคลุม
export function plan_extra_days(p) {
	const days = [];
	for (const group of plan_groups(p))
		for (const item of group.items)
			for (const usage of item.usages) if (usage.target !== null) days.push(usage.target);
	return days;
}

// จำนวนต่อวันของคน/เครื่องจักร: Map วัน → จำนวน
export const item_daily = (p, item) => resource_daily(item.list, p.by_name, p.counting);

const month_key = (day) => {
	const date = day_to_date(day);
	return date.getUTCFullYear() * 12 + date.getUTCMonth();
};
const month_label = (key) => `${MONTHS[key % 12]} ${(Math.floor(key / 12) + 543) % 100}`;

// ปริมาณต่อเดือน: วัสดุกระจายตามสัดส่วนงานรายวัน (รวม % แผนที่กำหนดเอง) ยอดรวมจึงเท่าจำนวนในแผน
// คน/เครื่องจักร = คน-วัน / คัน-วัน ตามวันทำงานของงาน (เกินหนึ่งงานในวันเดียวกันรวมกัน)
function add_month(values, day, amount) {
	const key = month_key(day);
	values.set(key, (values.get(key) || 0) + amount);
}

function material_rows(p, group) {
	const by_uom = new Map();
	for (const item of group.items) {
		for (const row of item.list) {
			const key = `${item.name}|${row.uom || ""}`;
			if (!by_uom.has(key)) by_uom.set(key, { key, label: item.label, code: item.name, unit: row.uom || "", values: new Map() });
			const task = p.by_name.get(row.task);
			const start = to_day(task?.start_date);
			const end = to_day(task?.end_date);
			if (start === null || end === null) continue;
			const daily = task_daily(start, end, parse_distribution(task.plan_distribution), p.counting);
			for (const [day, fraction] of daily) add_month(by_uom.get(key).values, day, (row.qty || 0) * fraction);
		}
	}
	return [...by_uom.values()];
}

function resource_rows(p, group) {
	return group.items.map((item) => {
		const values = new Map();
		const peaks = new Map();
		for (const [day, amount] of item_daily(p, item)) {
			add_month(values, day, amount);
			const key = month_key(day);
			peaks.set(key, Math.max(peaks.get(key) || 0, amount));
		}
		return { key: item.key, label: item.label, unit: item.type.total_unit, values, peaks };
	});
}

// { months: [{ key, label }], sections: [{ key, label, icon, rows: [{ key, label, unit, values: Map, peaks?: Map, total }] }] }
export function monthly_usage(p) {
	const sections = plan_groups(p).map((group) => {
		const rows = group.type.key === "Material" ? material_rows(p, group) : resource_rows(p, group);
		for (const row of rows) row.total = [...row.values.values()].reduce((sum, value) => sum + value, 0);
		return { key: group.key, label: group.label, icon: group.type.icon, rows };
	});
	const used = sections.flatMap((section) => section.rows.flatMap((row) => [...row.values.keys()]));
	if (!used.length) return { months: [], sections };
	const first = Math.min(...used);
	const last = Math.max(...used);
	const months = Array.from({ length: last - first + 1 }, (_, i) => ({ key: first + i, label: month_label(first + i) }));
	return { months, sections };
}
