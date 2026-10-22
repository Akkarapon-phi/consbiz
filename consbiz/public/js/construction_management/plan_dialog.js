// หน้าต่างกำหนด % แผนของงานเดียวเป็นรายวัน/สัปดาห์/เดือน (เปิดจากการคลิกแถบงานใน Gantt)
// ค่าเริ่มต้นในตารางคือแผนที่ใช้อยู่ (ไม่ได้กำหนดเอง = ตามสัดส่วนวันทำงาน)
// บันทึกเป็น plan_distribution = { unit, weights } ของงาน หรือ null เมื่อกลับไปคิดตามจำนวนวัน
import { from_day, parse_distribution, segments, to_day } from "./schedule";

export function open_plan_dialog({ task, holidays, week_unit, default_unit }, on_save) {
	const units = [
		{ value: "day", label: __("รายวัน") },
		{ value: week_unit, label: __("รายสัปดาห์") },
		{ value: "month", label: __("รายเดือน") },
	];
	const start = to_day(task.start_date);
	const end = to_day(task.end_date);
	const current = parse_distribution(task.plan_distribution);
	const unit_values = units.map((u) => u.value);
	let unit = current && unit_values.includes(current.unit) ? current.unit : default_unit;
	if (!unit_values.includes(unit)) unit = week_unit;

	let rows = [];

	const dialog = new frappe.ui.Dialog({
		title: __("กำหนด % แผน: {0} {1}", [task.wbs, task.item_name]),
		size: "large",
		fields: [
			{
				fieldname: "unit",
				fieldtype: "Select",
				label: __("แบ่งเป็น"),
				options: units,
				default: unit,
				change() {
					const value = dialog.get_value("unit");
					if (value && value !== unit) {
						unit = value;
						rows = build_rows(null);
						render();
					}
				},
			},
			{ fieldtype: "Column Break" },
			{
				fieldtype: "HTML",
				options: `<div class="text-muted small" style="padding-top: 26px">${__(
					"{0} - {1} · % ของช่วงกระจายเท่าๆ กันในวันทำงานของช่วงนั้น",
					[
						frappe.datetime.str_to_user(task.start_date),
						frappe.datetime.str_to_user(task.end_date),
					]
				)}</div>`,
			},
			{ fieldtype: "Section Break" },
			{ fieldname: "table", fieldtype: "HTML" },
			{
				fieldname: "even",
				fieldtype: "Button",
				label: __("เฉลี่ยเท่ากัน"),
				click() {
					const share = Math.floor((100 / rows.length) * 100) / 100;
					rows.forEach((row) => (row.percent = share));
					rows.at(-1).percent = flt(100 - share * (rows.length - 1), 2);
					render();
				},
			},
		],
		primary_action_label: __("บันทึก"),
		primary_action() {
			const total = rows.reduce((sum, row) => sum + (row.percent || 0), 0);
			if (Math.abs(total - 100) > 0.01) {
				frappe.msgprint(
					__("รวมได้ {0}% ต้องรวมได้ 100%", [format_number(total, null, 2)])
				);
				return;
			}
			dialog.hide();
			on_save(JSON.stringify({ unit, weights: rows.map((row) => flt(row.percent, 6)) }));
		},
		secondary_action_label: __("คิดตามจำนวนวัน (ล้างค่า)"),
		secondary_action() {
			dialog.hide();
			on_save(null);
		},
	});

	// ค่าเริ่มต้น: ใช้ % เดิมถ้ากำหนดไว้ด้วยหน่วยนี้และจำนวนช่วงตรงกัน ไม่งั้นแบ่งตามสัดส่วนวันทำงาน
	function build_rows(distribution) {
		const parts = segments(start, end, unit).map((part) => ({
			...part,
			days: working_days(part.start, part.end),
		}));
		const fits =
			distribution &&
			distribution.unit === unit &&
			distribution.weights.length === parts.length;
		const total_days = parts.reduce((sum, part) => sum + part.days, 0) || 1;
		return parts.map((part, i) => ({
			...part,
			percent: fits ? distribution.weights[i] : flt((part.days / total_days) * 100, 2),
		}));
	}

	function working_days(from, to) {
		let count = 0;
		for (let d = from; d <= to; d++) if (!holidays.has(d)) count++;
		return count;
	}

	function label(part) {
		const fmt = (day) => frappe.datetime.str_to_user(from_day(day));
		return part.start === part.end ? fmt(part.start) : `${fmt(part.start)} - ${fmt(part.end)}`;
	}

	function render() {
		let cumulative = 0;
		const body = rows
			.map((row, i) => {
				cumulative += row.percent || 0;
				return `<tr>
					<td>${i + 1}</td>
					<td>${label(row)}</td>
					<td class="text-right">${row.days}</td>
					<td><input type="number" step="any" min="0" class="form-control input-xs text-right" data-index="${i}" value="${flt(
					row.percent,
					4
				)}"></td>
					<td class="text-right text-muted" data-cumulative="${i}">${format_number(cumulative, null, 2)}</td>
				</tr>`;
			})
			.join("");
		const $wrapper = dialog.fields_dict.table.$wrapper;
		$wrapper.html(`
			<div style="max-height: 50vh; overflow-y: auto">
				<table class="table table-bordered table-sm" style="margin: 0">
					<thead><tr>
						<th style="width: 40px">#</th>
						<th>${__("ช่วง")}</th>
						<th class="text-right" style="width: 90px">${__("วันทำงาน")}</th>
						<th class="text-right" style="width: 130px">${__("% ของงาน")}</th>
						<th class="text-right" style="width: 100px">${__("% สะสม")}</th>
					</tr></thead>
					<tbody>${body}</tbody>
				</table>
			</div>
			<div class="text-right" style="margin-top: 8px">${__("รวม")} <b class="cs-plan-total"></b></div>`);
		$wrapper.find("input").on("input", function () {
			rows[cint(this.dataset.index)].percent = flt(this.value);
			update_totals($wrapper);
		});
		update_totals($wrapper);
	}

	function update_totals($wrapper) {
		let cumulative = 0;
		rows.forEach((row, i) => {
			cumulative += row.percent || 0;
			$wrapper.find(`[data-cumulative="${i}"]`).text(format_number(cumulative, null, 2));
		});
		const ok = Math.abs(cumulative - 100) <= 0.01;
		$wrapper
			.find(".cs-plan-total")
			.text(`${format_number(cumulative, null, 2)}%`)
			.toggleClass("text-danger", !ok)
			.toggleClass("text-success", ok);
	}

	rows = build_rows(current);
	dialog.show();
	render();
}
