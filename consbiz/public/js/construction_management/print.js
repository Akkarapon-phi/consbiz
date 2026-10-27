// พิมพ์หน้า Gantt: สร้าง HTML + SVG แยกจากหน้าจอแล้วสั่งพิมพ์ผ่าน iframe ที่ซ่อนไว้
// - fit:   ทั้งแผนใน 1 หน้า ย่อเฉพาะเมื่อแถวสูงเกินหน้า (ไม่ขยาย) timeline ยืดเต็มความกว้างที่เหลือ
//          งานน้อยแถว พื้นที่ timeline/S-Curve ยืดลงจนเต็มหน้า
// - pages: แต่ละช่องเวลากว้างคงที่ (PERIOD_PX) แบ่งเป็นหลายหน้า เรียงตามเวลาก่อน (ซ้ายไปขวา) แล้วจึงแถวถัดไป
//          ทุกหน้าซ้ำหัวตาราง คอลัมน์ WBS และตารางสรุปของช่วงเวลานั้น
// ช่องเวลา (วัน/สัปดาห์/เดือน/ปี) เลือกในหน้าต่างพิมพ์ ค่าเริ่มต้นตามที่ดูบนจอ
// คอลัมน์ เส้น S-Curve แถบ baseline ข้อความบนแถบ ตารางสรุป และการย่อ/ขยายกลุ่ม ใช้ตามที่แสดงบนจอ
// ความกว้างคอลัมน์ตารางในงานพิมพ์ใช้ค่าไม่เกิน PRINT_WIDTH (บนจอมักกว้างกว่าที่กระดาษต้องการ)
import {
	cell_text,
	format_money,
	format_percent,
	format_share,
	period_label,
	progress_status,
	text_width,
} from "./columns";
import {
	distribution_fits,
	floor_to,
	next_of,
	parse_distribution,
	period_shares,
	periods,
	sample_curve,
	smooth_path,
	summary_values,
	to_day,
} from "./schedule";

const MM = 96 / 25.4; // พิกเซล CSS ต่อมิลลิเมตร
const PAPER = { A4: [210, 297], A3: [297, 420] };
const MARGIN_MM = 8;
const HEAD_MM = 20;

const ROW = 18;
const HEADER = 34;
const SUMMARY_ROW = 15;

const PRINT_WIDTH = {
	wbs: 40,
	item_name: 170,
	quantity: 50,
	uom: 36,
	amount: 66,
	weight: 40,
	start_date: 56,
	end_date: 56,
	duration: 34,
	baseline_start_date: 56,
	baseline_end_date: 56,
	plan_pct: 40,
	actual_qty: 50,
	actual_pct: 40,
};

// โหมดหลายหน้า: ความกว้างของ 1 ช่องเวลา (px) และจำนวนวันเฉลี่ยต่อช่อง
const PERIOD_PX = { day: 18, week: 42, mweek: 42, month: 56, quarter: 64 };
const PERIOD_DAYS = { day: 1, week: 7, mweek: 7.6, month: 30.4, quarter: 91.3 };
const CURVE_MARGIN = 8;

// สีของงานพิมพ์ใช้ค่าคงที่ (ไม่ตามธีมมืด) เส้นตาราง #BFBFBF ตามมาตรฐานเอกสารพิมพ์ของแอป
const COLOR = {
	text: "#383838",
	muted: "#6b6b6b",
	line: "#BFBFBF",
	header: "#f3f3f3",
	group_row: "#E8F0FE",
	holiday: "#f3f3f3",
	bar: "#0d8ef8",
	group: "#525252",
	today: "#e03434",
	status: "#9c45e3",
};

// สีกรอบท้ายแถบ [พื้น, ตัวอักษร] = --bg-* / --text-on-* ของ Frappe ธีมสว่าง
const PILL = {
	green: ["#e4faeb", "#14804d"],
	blue: ["#e6f4ff", "#0375d3"],
};
// สีแถบตามสถานะ = --green-500 / --orange-500 / --red-500 ของ Frappe
const STATUS_COLOR = { green: "#43ac79", orange: "#e86c13", red: "#e03434" };
const PRINT_FONT = `"Noto Sans Thai", system-ui, -apple-system, sans-serif`;

export function open_print_dialog(get_model, saved, on_save) {
	const { scales, scale } = get_model();
	const dialog = new frappe.ui.Dialog({
		title: __("พิมพ์แผนงาน"),
		fields: [
			{
				fieldname: "mode",
				fieldtype: "Select",
				label: __("รูปแบบ"),
				options: [
					{ value: "fit", label: __("พอดี 1 หน้า") },
					{ value: "pages", label: __("แบ่งหลายหน้า") },
				],
				default: saved.mode || "fit",
			},
			{
				fieldname: "scale",
				fieldtype: "Select",
				label: __("ช่องเวลา"),
				options: Object.entries(scales).map(([value, config]) => ({
					value,
					label: config.label,
				})),
				default: scale,
			},
			{
				fieldname: "paper",
				fieldtype: "Select",
				label: __("ขนาดกระดาษ"),
				options: ["A4", "A3"],
				default: saved.paper || "A3",
			},
			{
				fieldname: "orientation",
				fieldtype: "Select",
				label: __("แนวกระดาษ"),
				options: [
					{ value: "landscape", label: __("แนวนอน") },
					{ value: "portrait", label: __("แนวตั้ง") },
				],
				default: saved.orientation || "landscape",
			},
			{
				fieldtype: "HTML",
				options: `<p class="text-muted small">${__(
					"คอลัมน์ เส้น S-Curve แถบ Baseline ข้อความบนแถบ ตารางสรุป และการย่อ/ขยายหัวข้อ จะพิมพ์ตามที่แสดงบนจออยู่ตอนนี้"
				)}</p>`,
			},
		],
		primary_action_label: __("พิมพ์"),
		primary_action(options) {
			dialog.hide();
			// ช่องเวลาตั้งตามจอทุกครั้ง ไม่จำ
			const { scale: _, ...remembered } = options;
			on_save(remembered);
			print_gantt(get_model(), options);
		},
	});
	dialog.show();
}

export function print_gantt(model, options) {
	const [short, long] = PAPER[options.paper];
	const [paper_w, paper_h] = options.orientation === "landscape" ? [long, short] : [short, long];
	const content_w = (paper_w - 2 * MARGIN_MM) * MM;
	const content_h = (paper_h - 2 * MARGIN_MM - HEAD_MM) * MM;

	const { top, bottom } = model.scales[options.scale] || model.scales[model.scale];
	model = {
		...model,
		columns: model.columns.map((c) => ({
			...c,
			width: Math.min(c.width, PRINT_WIDTH[c.key] || 60),
		})),
	};
	// งานพิมพ์ใช้ช่วงเวลาเท่าที่มีงาน (บนจอปัดเป็นทั้งเดือน/ทั้งปีเผื่อเลื่อนดู)
	model = with_range(model, { top, bottom });
	let pages;
	let layout;
	if (options.mode === "pages") {
		model.ppd = PERIOD_PX[bottom] / PERIOD_DAYS[bottom];
		layout = new Layout(model);
		pages = layout.paginate(content_w, content_h);
		if (!pages) return;
	} else {
		const fit = fit_model(model, content_w, content_h);
		model = fit.model;
		layout = new Layout(model);
		pages = [
			{
				rows: [0, model.rows.length],
				days: [model.range.start, model.range.end],
				band_h: fit.band_h,
			},
		];
	}

	const html = page_html(
		model,
		pages.map((page, i) => ({
			head: page_head(model, page, i, pages.length),
			svg: layout.render(page, i),
		})),
		paper_w,
		paper_h
	);
	print_html(html);
}

// พอดี 1 หน้า: ย่อ (scale) เท่าที่แถวต้องใช้ให้ลงความสูงหน้า ไม่ขยายเกินขนาดพิมพ์ปกติ
// ความกว้างที่เหลือจากคอลัมน์เป็นของ timeline ทั้งหมด และแถบงานยืดลงเต็มหน้า (S-Curve ได้ความสูงเต็ม)
function fit_model(model, content_w, content_h) {
	const grid_width = model.columns.reduce((sum, c) => sum + c.width, 0);
	const summary_h = model.summary_rows.length * SUMMARY_ROW;
	const height = HEADER + Math.max(model.rows.length, 1) * ROW + summary_h;
	const scale = Math.min(content_h / height, 1);
	const days = model.range.end - model.range.start;
	const ppd = Math.max((content_w / scale - grid_width) / days, 0.3);
	return {
		model: { ...model, ppd },
		band_h: content_h / scale - HEADER - summary_h,
	};
}

function with_range(model, units) {
	const { first, last } = model.extent;
	return {
		...model,
		units,
		range: {
			start: floor_to(first - 1, units.bottom),
			end: next_of(floor_to(last + 1, units.bottom), units.bottom),
		},
	};
}

class Layout {
	constructor(model) {
		this.model = model;
		this.summary_height = model.summary_rows.length
			? model.summary_rows.length * SUMMARY_ROW
			: 0;
		this.bottom_periods = periods(model.range.start, model.range.end, model.units.bottom);
		this.top_periods = periods(model.range.start, model.range.end, model.units.top);
	}

	// แบ่งหน้า: คืน [{ rows: [จาก, ถึง), days: [จาก, ถึง), columns, slice_w }] หรือ null ถ้ากระดาษแคบเกินคอลัมน์
	// หน้าแรกของแต่ละช่วงแถวแสดงทุกคอลัมน์ที่เลือก หน้าถัดไปทางขวาแสดงแค่ WBS + รายการ จะได้เห็น timeline มากขึ้น
	paginate(content_w, content_h) {
		const full = this.model.columns;
		const compact = full.filter((c) => ["wbs", "item_name"].includes(c.key));
		const width_of = (columns) => columns.reduce((sum, c) => sum + c.width, 0);
		if (content_w - width_of(full) < 150) {
			frappe.msgprint(
				__(
					"คอลัมน์ที่เลือกกว้างเกินหน้ากระดาษ ให้ลดคอลัมน์ ลดความกว้างคอลัมน์ หรือเลือกกระดาษแนวนอน/A3"
				)
			);
			return null;
		}
		const rows_per_page = Math.max(
			Math.floor((content_h - HEADER - this.summary_height) / ROW),
			1
		);

		// ตัดช่วงเวลาตามขอบช่องของหัวแถวล่าง ไม่ให้ช่องขาดกลางหน้า
		const slices = [];
		let columns = full;
		let from = this.model.range.start;
		const close = (to) => {
			slices.push({ days: [from, to], columns, slice_w: content_w - width_of(columns) });
			columns = compact;
			from = to;
		};
		for (const period of this.bottom_periods) {
			const slice_w = content_w - width_of(columns);
			if ((period.end - from) * this.model.ppd > slice_w && period.start > from) {
				close(period.start);
			}
		}
		close(this.model.range.end);

		const pages = [];
		const total = this.model.rows.length;
		for (let row = 0; row < Math.max(total, 1); row += rows_per_page) {
			for (const slice of slices) {
				pages.push({ rows: [row, Math.min(row + rows_per_page, total)], ...slice });
			}
		}
		return pages;
	}

	render(page, index) {
		const m = this.model;
		const [row_from, row_to] = page.rows;
		const [day_from, day_to] = page.days;
		const columns = page.columns || m.columns;
		const slice_w = page.slice_w || (day_to - day_from) * m.ppd;
		const gx = columns.reduce((sum, c) => sum + c.width, 0);
		const clip = `tl${index}`;
		const band_h = Math.max((row_to - row_from) * ROW, ROW, page.band_h || 0);
		const body_y = HEADER;
		const summary_y = body_y + band_h;
		const width = gx + slice_w;
		const height = summary_y + this.summary_height;
		const x = (day) => gx + (day - day_from) * m.ppd;
		const rows = m.rows.slice(row_from, row_to);
		const out = [];

		out.push(
			`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${width} ${height}" preserveAspectRatio="xMidYMin meet">`,
			`<defs><clipPath id="${clip}"><rect x="${gx}" y="0" width="${slice_w}" height="${height}"/></clipPath></defs>`,
			`<rect x="0" y="0" width="${width}" height="${HEADER}" fill="${COLOR.header}"/>`
		);

		// ---------- ตารางซ้าย ----------
		let cx = 0;
		for (const column of columns) {
			out.push(cell(cx, 0, column.width, HEADER, column.label, column.align, true, true));
			cx += column.width;
		}
		rows.forEach((task, i) => {
			const y = body_y + i * ROW;
			if (task.is_group) out.push(rect(0, y, gx, ROW, COLOR.group_row));
			let cx = 0;
			for (const column of columns) {
				const value = cell_text(task, column.key, m.metrics);
				const indent = column.key === "item_name" ? task.indent * 10 : 0;
				out.push(
					cell(
						cx,
						y,
						column.width,
						ROW,
						value,
						column.align,
						task.is_group,
						false,
						indent
					)
				);
				cx += column.width;
			}
		});

		// ---------- timeline ----------
		out.push(`<g clip-path="url(#${clip})">`);
		for (const period of this.top_periods) {
			if (period.end <= day_from || period.start >= day_to) continue;
			const px = Math.max(x(period.start), gx);
			out.push(
				`<rect x="${x(period.start)}" y="0" width="${
					(period.end - period.start) * m.ppd
				}" height="${HEADER / 2}" fill="none" stroke="${COLOR.line}" stroke-width="0.5"/>`,
				text(px + 4, HEADER / 2 - 6, period_label(period, m.units.top, true), {
					size: 9,
					weight: 600,
				})
			);
		}
		const narrow = (this.bottom_periods[0]?.end - this.bottom_periods[0]?.start) * m.ppd < 18;
		for (const period of this.bottom_periods) {
			if (period.end <= day_from || period.start >= day_to) continue;
			const w = (period.end - period.start) * m.ppd;
			out.push(
				`<rect x="${x(period.start)}" y="${HEADER / 2}" width="${w}" height="${
					HEADER / 2
				}" fill="none" stroke="${COLOR.line}" stroke-width="0.5"/>`
			);
			if (!narrow) {
				out.push(
					text(
						x(period.start) + w / 2,
						HEADER - 6,
						period_label(period, m.units.bottom, false),
						{
							size: 8,
							anchor: "middle",
						}
					)
				);
			}
			out.push(line(x(period.start), body_y, x(period.start), summary_y, COLOR.line, "2 3"));
		}
		if (m.ppd >= 3) {
			for (const day of m.holidays) {
				if (day >= day_from && day < day_to) {
					out.push(rect(x(day), body_y, m.ppd, band_h, COLOR.holiday));
				}
			}
		}

		rows.forEach((task, i) => {
			const y = body_y + i * ROW;
			out.push(line(gx, y + ROW, gx + slice_w, y + ROW, COLOR.line));
			const start = to_day(task.start_date);
			const end = to_day(task.end_date);
			const base_start = to_day(task.baseline_start_date);
			const base_end = to_day(task.baseline_end_date);
			if (m.show_baseline_bars && base_start !== null && base_end !== null) {
				out.push(
					rect(
						x(base_start),
						y + ROW - 6,
						(base_end - base_start + 1) * m.ppd,
						3,
						m.colors.baseline
					)
				);
			}
			if (start === null || end === null) return;
			const w = Math.max((end - start + 1) * m.ppd, 1.5);
			const top = m.show_baseline_bars ? 4 : 5;
			const h = m.show_baseline_bars ? 9 : ROW - 10;
			const status_color = bar_status_color(task, m);
			if (task.is_group) {
				const fill = status_color || COLOR.group;
				out.push(
					rect(x(start), y + top + 1, w, 5, fill),
					rect(x(start), y + top + 1, 3, 9, fill),
					rect(x(start) + w - 3, y + top + 1, 3, 9, fill)
				);
			} else {
				const fill = status_color || COLOR.bar;
				const actual = Math.min(m.metrics.get(task.name)?.actual_pct || 0, 100);
				out.push(
					`<rect x="${x(start)}" y="${
						y + top
					}" width="${w}" height="${h}" rx="2" fill="${fill}" fill-opacity="0.45"/>`
				);
				if (actual) {
					out.push(
						`<rect x="${x(start)}" y="${y + top}" width="${
							(w * actual) / 100
						}" height="${h}" rx="2" fill="${fill}"/>`
					);
				}
				out.push(...split_texts(task, start, end, x, y + top + h / 2 + 3, m));
			}
			out.push(...end_texts(task, x(end + 1) + 4, y, m));
		});

		for (const [day, color] of [
			[m.today + 1, COLOR.today],
			[m.status_day + 1, COLOR.status],
		]) {
			if (day >= day_from && day < day_to) {
				out.push(
					line(
						x(day),
						body_y,
						x(day),
						summary_y,
						color,
						day === m.today + 1 ? "" : "6 3",
						1.2
					)
				);
			}
		}

		// S-Curve สเกลตามความสูงของแถวในหน้านั้น
		if (m.curves.length) {
			const cy = (value) =>
				body_y + CURVE_MARGIN + (1 - value / 100) * (band_h - 2 * CURVE_MARGIN);
			for (const tick of [0, 25, 50, 75, 100]) {
				out.push(line(gx, cy(tick), gx + slice_w, cy(tick), "#999999", "4 4", 0.4));
			}
			for (const curve of m.curves) {
				const points = sample_curve(curve.curve, this.bottom_periods);
				if (!points.length) continue;
				const d = smooth_path(points.map((p) => [x(p.day + 1), cy(p.value)]));
				out.push(
					`<path d="${d}" fill="none" stroke="${curve.color}" stroke-width="1.6"/>`
				);
				for (const p of points) {
					out.push(
						`<circle cx="${x(p.day + 1)}" cy="${cy(
							p.value
						)}" r="2" fill="#fff" stroke="${curve.color}" stroke-width="1.2"/>`
					);
				}
			}
			for (const tick of [0, 25, 50, 75, 100]) {
				out.push(
					text(gx + slice_w - 3, cy(tick) + 3, `${tick}%`, {
						size: 8,
						anchor: "end",
						weight: 600,
						halo: true,
					})
				);
			}
		}

		// ตารางสรุปของช่วงเวลาในหน้านี้
		if (this.summary_height) {
			m.summary_rows.forEach((row, i) => {
				const y = summary_y + i * SUMMARY_ROW;
				out.push(rect(gx, y, slice_w, SUMMARY_ROW, COLOR.header));
			});
			for (const period of this.bottom_periods) {
				if (period.end <= day_from || period.start >= day_to) continue;
				const w = (period.end - period.start) * m.ppd;
				const values = summary_values(period, m.all_curves, m.total_amount);
				m.summary_rows.forEach((row, i) => {
					const y = summary_y + i * SUMMARY_ROW;
					const value = row.money
						? format_money(values[row.key], w < 70)
						: format_percent(values[row.key]);
					out.push(
						`<rect x="${x(
							period.start
						)}" y="${y}" width="${w}" height="${SUMMARY_ROW}" fill="none" stroke="${
							COLOR.line
						}" stroke-width="0.5"/>`
					);
					// ช่องที่แคบกว่าตัวเลขไม่แสดง ไม่ให้ตัวเลขล้นทับช่องข้างๆ (เหมือนหน้าจอ)
					if (value && text_width(value, `7px ${PRINT_FONT}`) <= w - 2) {
						out.push(
							text(x(period.start) + w / 2, y + SUMMARY_ROW - 5, value, {
								size: 7,
								anchor: "middle",
							})
						);
					}
				});
			}
		}
		out.push(`</g>`);

		if (this.summary_height) {
			m.summary_rows.forEach((row, i) => {
				const y = summary_y + i * SUMMARY_ROW;
				out.push(
					rect(0, y, gx, SUMMARY_ROW, COLOR.header),
					`<rect x="0" y="${y}" width="${gx}" height="${SUMMARY_ROW}" fill="none" stroke="${COLOR.line}" stroke-width="0.5"/>`,
					`<circle cx="9" cy="${y + SUMMARY_ROW / 2}" r="3" fill="${row.color}"/>`,
					text(16, y + SUMMARY_ROW - 5, row.label, { size: 8, weight: 600 })
				);
			});
		}

		out.push(
			line(gx, 0, gx, height, COLOR.text, "", 0.8),
			line(0, HEADER, width, HEADER, COLOR.text, "", 0.8),
			`<rect x="0" y="0" width="${width}" height="${height}" fill="none" stroke="${COLOR.text}" stroke-width="0.8"/>`,
			`</svg>`
		);
		return out.join("");
	}
}

// % ที่กำหนดเองบนแถบ ตามช่องเวลาของงานพิมพ์ (เฉพาะช่องที่กว้างพอ)
function split_texts(task, start, end, x, y, m) {
	const distribution = m.show_split ? parse_distribution(task.plan_distribution) : null;
	if (!distribution || !distribution_fits(start, end, distribution)) return [];
	return period_shares(start, end, distribution, m.counting_holidays, m.units.bottom)
		.filter((part) => (part.end - part.start + 1) * m.ppd >= 22)
		.map((part) =>
			text((x(part.start) + x(part.end + 1)) / 2, y, format_share(part.percent), {
				size: 7,
				anchor: "middle",
				weight: 600,
				halo: true,
			})
		);
}

// สีแถบตามสถานะ (ปุ่ม "สี Status" บนจอ): เสร็จ = เขียว, ช้าไม่เกินเกณฑ์ = ส้ม, ช้าเกินเกณฑ์ = แดง
function bar_status_color(task, m) {
	const metrics = m.show_status && m.metrics.get(task.name);
	if (!metrics) return null;
	return STATUS_COLOR[progress_status(metrics.plan_pct, metrics.actual_pct).color] || null;
}

// ท้ายแถบ: ชื่องาน แล้วตามด้วยกรอบ 2 ช่อง % แผน (ฟ้า) | % จริง (เขียว) เหมือนบนจอ
function end_texts(task, x0, y, m) {
	const out = [];
	const metrics = m.metrics.get(task.name);
	const weight = task.is_group ? 600 : 400;
	const label = m.show_labels ? `${task.wbs || ""} ${task.item_name || ""}`.trim() : "";
	let pill_x = x0;
	if (label) {
		out.push(text(x0, y + ROW / 2 + 3, label, { size: 8, weight }));
		pill_x += text_width(label, `${weight} 8px ${PRINT_FONT}`) + 6;
	}
	if (m.show_progress && metrics) {
		for (const [value, [fill, ink]] of [
			[`${__("แผน")} ${format_number(metrics.plan_pct, null, 1)}%`, PILL.blue],
			[`${__("จริง")} ${format_number(metrics.actual_pct, null, 1)}%`, PILL.green],
		]) {
			const width = text_width(value, `600 7px ${PRINT_FONT}`) + 10;
			out.push(
				`<rect x="${pill_x}" y="${
					y + ROW / 2 - 6
				}" width="${width}" height="12" fill="${fill}"/>`,
				`<text x="${pill_x + width / 2}" y="${
					y + ROW / 2 + 2.5
				}" font-size="7" font-weight="600" text-anchor="middle" fill="${ink}">${escape(
					value
				)}</text>`
			);
			pill_x += width;
		}
	}
	return out;
}

// ---------- ชิ้นส่วน SVG ----------

function escape(value) {
	return String(value ?? "")
		.replace(/&/g, "&amp;")
		.replace(/</g, "&lt;")
		.replace(/>/g, "&gt;")
		.replace(/"/g, "&quot;");
}

function rect(x, y, w, h, fill) {
	return `<rect x="${x}" y="${y}" width="${w}" height="${h}" fill="${fill}"/>`;
}

function line(x1, y1, x2, y2, color, dash = "", width = 0.5) {
	const dasharray = dash ? ` stroke-dasharray="${dash}"` : "";
	return `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="${color}" stroke-width="${width}"${dasharray}/>`;
}

function text(x, y, value, { size = 9, anchor = "start", weight = 400, halo = false } = {}) {
	const outline = halo ? ` paint-order="stroke" stroke="#fff" stroke-width="3"` : "";
	return `<text x="${x}" y="${y}" font-size="${size}" font-weight="${weight}" text-anchor="${anchor}" fill="${
		COLOR.text
	}"${outline}>${escape(value)}</text>`;
}

// ช่องตาราง: svg ซ้อนเพื่อตัดข้อความที่ยาวเกินช่อง
function cell(x, y, w, h, value, align, bold, header, indent = 0) {
	const right = align === "right";
	const tx = right ? w - 4 : 4 + indent;
	const ty = header ? h - 6 : h - 6;
	return (
		`<rect x="${x}" y="${y}" width="${w}" height="${h}" fill="none" stroke="${COLOR.line}" stroke-width="0.5"/>` +
		`<svg x="${x}" y="${y}" width="${w}" height="${h}">` +
		`<text x="${tx}" y="${ty}" font-size="${header ? 7 : 8}" font-weight="${
			bold ? 600 : 400
		}" text-anchor="${right ? "end" : "start"}" fill="${
			header ? COLOR.muted : COLOR.text
		}">${escape(value)}</text></svg>`
	);
}

// ---------- หน้า HTML ----------

function page_head(model, page, index, total) {
	const legend = model.curves
		.map((c) => `<span><i style="background:${c.color}"></i>${escape(c.label)}</span>`)
		.join("");
	const detail =
		total > 1
			? ` · ${__("แถว {0}-{1}", [page.rows[0] + 1, page.rows[1]])} · ${escape(
					model.format_day(page.days[0])
			  )} - ${escape(model.format_day(page.days[1] - 1))}`
			: "";
	// ข้อมูลสัญญาจาก CM (กรอกเองในฟอร์ม) ช่องที่ว่างแสดง -
	const value = (text) => escape(text || "-");
	return `
		<div class="head">
			<div class="title">
				<h1>${__("แผนงานก่อสร้าง")}</h1>
				<div class="project">${escape(model.project_name)}</div>
				<div class="legend">${legend}</div>
			</div>
			<table class="info">
				<tr><th>${__("ผู้ว่าจ้าง")}</th><td>${value(model.employer)}</td>
					<th>${__("ระยะเวลาสัญญา")}</th><td>${value(model.contract_text)}</td></tr>
				<tr><th>${__("ผู้รับจ้าง")}</th><td>${value(model.contractor)}</td>
					<th>${__("ความคืบหน้า")}</th><td>${escape(model.status_text)}</td></tr>
				<tr><th>${__("ผู้ควบคุมงาน")}</th><td>${value(model.supervisor)}</td>
					<th>${__("หน้า")}</th><td>${index + 1}/${total}${detail}</td></tr>
			</table>
		</div>`;
}

function page_html(model, pages, paper_w, paper_h) {
	const font = `${window.location.origin}/assets/consbiz/fonts/noto-sans-thai/NotoSansThai-Variable-thai.woff2`;
	const body = pages
		.map((page) => `<section class="page">${page.head}${page.svg}</section>`)
		.join("");
	return `<!doctype html>
<html><head><meta charset="utf-8"><title>${escape(model.title)}</title>
<style>
@font-face {
	font-family: "Noto Sans Thai";
	font-weight: 100 900;
	src: url("${font}") format("woff2");
	unicode-range: U+02D7, U+0303, U+0331, U+0E01-0E5B, U+200C-200D, U+25CC;
}
@page { size: ${paper_w}mm ${paper_h}mm; margin: ${MARGIN_MM}mm; }
html, body { margin: 0; padding: 0; }
body {
	font-family: "Noto Sans Thai", system-ui, -apple-system, sans-serif;
	color: ${COLOR.text};
	-webkit-print-color-adjust: exact;
	print-color-adjust: exact;
}
svg text { font-family: "Noto Sans Thai", system-ui, -apple-system, sans-serif; }
.page {
	width: ${paper_w - 2 * MARGIN_MM}mm;
	height: ${paper_h - 2 * MARGIN_MM}mm;
	display: flex;
	flex-direction: column;
	overflow: hidden;
	break-after: page;
}
.page:last-child { break-after: auto; }
.head {
	flex: 0 0 ${HEAD_MM}mm;
	box-sizing: border-box;
	display: flex;
	justify-content: space-between;
	align-items: flex-end;
	gap: 8mm;
	padding-bottom: 1.5mm;
	font-size: 9px;
}
.head h1 { margin: 0; font-size: 18px; font-weight: 700; }
.head .project { font-size: 11px; font-weight: 600; }
.head .legend { margin-top: 2px; }
.info { border-collapse: collapse; font-size: 8.5px; }
.info th { padding: 1px 6px 1px 12px; text-align: left; font-weight: 600; color: #6b6b6b; white-space: nowrap; }
.info td { padding: 1px 0; max-width: 70mm; }
.legend span { margin-right: 10px; white-space: nowrap; }
.legend i { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 4px; }
.page > svg { flex: 1 1 auto; min-height: 0; width: 100%; height: 100%; }
</style></head><body>${body}</body></html>`;
}

function print_html(html) {
	const iframe = document.createElement("iframe");
	iframe.style.cssText = "position:fixed;right:0;bottom:0;width:0;height:0;border:0;";
	document.body.appendChild(iframe);
	const win = iframe.contentWindow;
	win.document.open();
	win.document.write(html);
	win.document.close();

	const cleanup = () => setTimeout(() => iframe.remove(), 1000);
	win.addEventListener("afterprint", cleanup, { once: true });
	// รอฟอนต์ไทยโหลดก่อนสั่งพิมพ์ ไม่งั้นหน้าแรกอาจใช้ฟอนต์สำรอง
	win.document.fonts.load('10px "Noto Sans Thai"', "ก").finally(() => {
		win.focus();
		win.print();
	});
}
