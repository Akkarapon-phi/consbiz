// Copyright (c) 2026, Siricons and contributors
// For license information, please see license.txt

const BOQ_EXCEL_METHOD = "consbiz.consbiz.doctype.boq.boq_excel";

frappe.ui.form.on("BOQ", {
	refresh(frm) {
		add_excel_buttons(frm);
		const grid = frm.fields_dict.boq_details.grid;
		if (!frm.select_banner_bound) {
			// Frappe เก็บสถานะการเลือกไว้ที่ row.__checked แล้วอัปเดตตอนคลิกในตาราง
			// (ติ๊กแถว, ติ๊กทั้งหมด, ปุ่ม Delete) จึงรอให้ Frappe จัดการก่อนแล้วค่อยอ่าน
			grid.wrapper.on("click touchend", () => setTimeout(() => update_select_banner(frm), 150));
			frm.select_banner_bound = true;
		}
		setup_category_tools(frm);
		update_select_banner(frm);

		if (frm.is_new() || frm.doc.docstatus === 2) return;

		frappe.db
			.get_value("Construction Management", { boq: frm.doc.name, status: "Active" }, "name")
			.then(({ message }) => {
				const schedule = message && message.name;
				if (schedule) {
					frm.add_custom_button(__("แผนงานก่อสร้าง"), () =>
						frappe.set_route("construction-gantt", schedule)
					);
				} else if (frappe.model.can_create("Construction Management")) {
					frm.add_custom_button(__("สร้างแผนงาน"), () =>
						frappe
							.call({
								method: "consbiz.consbiz.doctype.construction_management.construction_management.create_from_boq",
								args: { boq: frm.doc.name },
								freeze: true,
							})
							.then((r) => frappe.set_route("construction-gantt", r.message))
					);
				}
			});
	},
});

// ดึงชื่อ หน่วย กลุ่ม จาก BOQ Item ครั้งเดียวตอนเลือกรหัส (ไม่ใช้ fetch_from เพราะ fetch_from
// ดึงทับทุกครั้งที่บันทึก ค่าที่แก้หรือนำเข้าจาก Excel จะหาย) ราคาดึงในส่วน "BOQ Calulation" ท้ายไฟล์
frappe.ui.form.on("BOQ Item Detail", {
	item_code(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (!row.item_code) return;
		frappe.db
			.get_value("BOQ Item", row.item_code, ["item_name", "uom", "item_group"])
			.then(({ message }) => message && frappe.model.set_value(cdt, cdn, message));
	},

	// WBS รันอัตโนมัติทุกครั้งที่แถวเปลี่ยน พิมพ์ WBS เองได้เพื่อกำหนดระดับ (เช่น 1.1.1 = ระดับ 3)
	wbs(frm) {
		refresh_wbs(frm);
	},

	boq_details_add(frm) {
		refresh_wbs(frm);
	},

	boq_details_move(frm) {
		refresh_wbs(frm);
	},

	boq_details_remove(frm) {
		refresh_wbs(frm);
		update_select_banner(frm);
	},
});

function add_excel_buttons(frm) {
	const group = __("Excel");
	if (frm.doc.docstatus === 0) {
		frm.add_custom_button(__("นำเข้าจาก Excel"), () => import_boq_items(frm), group);
	}
	frm.add_custom_button(
		__("ส่งออก Excel"),
		() => {
			if (frm.is_new() || frm.is_dirty()) {
				frappe.msgprint(__("กรุณาบันทึกเอกสารก่อนส่งออก"));
				return;
			}
			open_url_post(`/api/method/${BOQ_EXCEL_METHOD}.export_boq_items`, { boq: frm.doc.name });
		},
		group
	);
}

const BOQ_IMPORT_MAX_MB = 10; // ตรงกับ MAX_FILE_SIZE ใน boq_excel.py

// ลากไฟล์มาวางหรือคลิกเลือก แล้วส่งเนื้อไฟล์ไปอ่านที่ server ตรงๆ (ไม่สร้าง File ไม่เปลืองพื้นที่)
function import_boq_items(frm) {
	const dialog = new frappe.ui.Dialog({
		title: __("นำเข้ารายการจาก Excel"),
		fields: [
			{
				fieldtype: "HTML",
				options: `<p class="text-muted">${__(
					"ใช้ไฟล์ตามแม่แบบ ระบบจะดึงลูกค้า โครงการ สถานที่ และวันที่จากหัวเอกสารด้วย ชื่อรายการพิมพ์อิสระได้ หลังอ่านไฟล์จะให้ตรวจการจับคู่กับ BOQ Item ก่อนนำเข้า"
				)} <a class="download-template">${__("ดาวน์โหลดแม่แบบ")}</a></p>`,
			},
			{
				fieldname: "mode",
				fieldtype: "Select",
				label: __("วิธีนำเข้า"),
				options: [
					{ value: "append", label: __("เพิ่มต่อท้ายรายการเดิม") },
					{ value: "replace", label: __("แทนที่รายการเดิมทั้งหมด") },
				],
				default: "append",
			},
			{
				fieldtype: "HTML",
				fieldname: "drop_zone",
				options: `<div class="boq-drop-zone text-center" style="border: 1px dashed var(--gray-400);
					border-radius: var(--border-radius-md); padding: var(--padding-xl); cursor: pointer">
					<div>${__("ลากไฟล์ Excel มาวางที่นี่ หรือคลิกเพื่อเลือกไฟล์")}</div>
					<div class="text-muted small">.xlsx, .csv · ${__("ไม่เกิน {0} MB", [BOQ_IMPORT_MAX_MB])}</div>
					<input type="file" accept=".xlsx,.csv" hidden>
				</div>`,
			},
		],
	});

	const read_file = (file) => {
		if (!file) return;
		if (!/\.(xlsx|csv)$/i.test(file.name)) {
			frappe.msgprint(__("รองรับเฉพาะไฟล์ .xlsx หรือ .csv"));
			return;
		}
		if (file.size > BOQ_IMPORT_MAX_MB * 1024 * 1024) {
			frappe.msgprint(__("ไฟล์ใหญ่เกิน {0} MB", [BOQ_IMPORT_MAX_MB]));
			return;
		}
		const reader = new FileReader();
		reader.onload = () => {
			const mode = dialog.get_value("mode");
			frappe
				.call({
					method: `${BOQ_EXCEL_METHOD}.import_boq_items`,
					// data URL = "data:<type>;base64,<เนื้อไฟล์>"
					args: { filename: file.name, content: reader.result.split(",")[1] },
					freeze: true,
					freeze_message: __("กำลังอ่านไฟล์..."),
				})
				.then(({ message: result }) => {
					dialog.hide();
					const finish = (items) => apply_boq_import(frm, result, items, mode);
					const review = result.items.filter((item) => ["suggest", "none"].includes(item.match));
					if (review.length) review_boq_matches(result.items, review, finish);
					else finish(result.items);
				});
		};
		reader.readAsDataURL(file);
	};

	const $zone = dialog.fields_dict.drop_zone.$wrapper.find(".boq-drop-zone");
	const $input = $zone.find("input");
	const highlight = (on) => $zone.css("border-color", on ? "var(--primary)" : "var(--gray-400)");
	$zone
		.on("click", () => $input[0].click())
		.on("dragover", (e) => {
			e.preventDefault();
			highlight(true);
		})
		.on("dragleave", () => highlight(false))
		.on("drop", (e) => {
			e.preventDefault();
			highlight(false);
			read_file(e.originalEvent.dataTransfer.files[0]);
		});
	$input.on("click", (e) => e.stopPropagation()).on("change", (e) => {
		read_file(e.target.files[0]);
		e.target.value = "";
	});
	dialog.$wrapper
		.find(".download-template")
		.on("click", () => open_url_post(`/api/method/${BOQ_EXCEL_METHOD}.export_boq_items`, {}));
	dialog.show();
}

// หน้าตรวจการจับคู่: แสดงเฉพาะแถวที่ต้องตรวจ (มีตัวเลือก / ไม่พบ) แถวที่ตรงกันพอดีและหัวข้องานผ่านไปเลย
function review_boq_matches(all_items, review, finish) {
	const count = (match) => all_items.filter((item) => item.match === match).length;
	const esc = frappe.utils.escape_html;
	const dialog = new frappe.ui.Dialog({
		title: __("ตรวจการจับคู่รายการกับ BOQ Item"),
		size: "extra-large",
		fields: [{ fieldtype: "HTML", fieldname: "review" }],
		primary_action_label: __("นำเข้า {0} รายการ", [all_items.length]),
		primary_action() {
			review.forEach((item) => {
				item.create = item.$create.prop("checked") ? 1 : 0;
				item.item_code = item.create ? null : item.control.get_value() || null;
			});
			dialog.hide();
			finish(all_items);
		},
	});
	const $body = dialog.fields_dict.review.$wrapper.html(`
		<p class="small">
			<span class="indicator-pill green">${__("ตรงกันพอดี {0}", [count("exact")])}</span>
			<span class="indicator-pill orange">${__("มีตัวเลือก {0}", [count("suggest")])}</span>
			<span class="indicator-pill red">${__("ไม่พบ {0}", [count("none")])}</span>
			<span class="indicator-pill gray">${__("หัวข้องาน {0}", [count("heading")])}</span>
		</p>
		<p class="text-muted small">${__(
			"เลือก BOQ Item ให้แต่ละแถว (กดชื่อที่แนะนำ หรือพิมพ์ค้นในช่อง) ถ้าไม่ใช่รายการมาตรฐานให้เว้นว่าง หรือติ๊กสร้างเป็น BOQ Item ใหม่ ราคาใช้ค่าจาก Excel"
		)}</p>
		<div style="max-height: 60vh; overflow-y: auto">
			<table class="table table-sm small">
				<thead><tr>
					<th>${__("แถว")}</th><th>${__("รายการในไฟล์")}</th>
					<th style="width: 35%">${__("BOQ Item")}</th>
					<th><label class="mb-0"><input type="checkbox" class="create-all"> ${__("สร้างใหม่")}</label></th>
				</tr></thead>
				<tbody></tbody>
			</table>
		</div>`);

	const $tbody = $body.find("tbody");
	review.forEach((item) => {
		const row = item.row;
		const $tr = $(`<tr>
			<td>${item.row_no}</td>
			<td>
				<b>${esc(row.item_name || "")}</b>
				<div class="text-muted">${format_number(row.quantity, null, 2)} ${esc(row.uom || "")}
					${item.note ? ` · ${esc(item.note)}` : ""}</div>
			</td>
			<td>
				<div class="match-control"></div>
				<div class="match-name text-muted"></div>
				<div class="match-suggestions mt-1"></div>
			</td>
			<td><input type="checkbox" class="create-item"></td>
		</tr>`).appendTo($tbody);

		const names = Object.fromEntries(item.suggestions.map((s) => [s.item_code, s.item_name]));
		const show_name = (code) => {
			if (!code) return $tr.find(".match-name").text("");
			const set = (name) => $tr.find(".match-name").text(name || "");
			if (names[code]) set(names[code]);
			else frappe.db.get_value("BOQ Item", code, "item_name").then(({ message }) => set(message?.item_name));
		};
		item.control = frappe.ui.form.make_control({
			df: {
				fieldtype: "Link",
				options: "BOQ Item",
				fieldname: `item_${item.row_no}`,
				placeholder: __("ค้นหา BOQ Item"),
				onchange: () => show_name(item.control.get_value()),
			},
			parent: $tr.find(".match-control"),
			render_input: true,
			only_input: true,
		});
		item.control.set_value(item.item_code || "");

		item.suggestions.forEach((s) => {
			$(`<button class="btn btn-xs btn-default mr-1 mb-1"></button>`)
				.text(`${s.item_name} (${Math.round(s.score * 100)}%)`)
				.attr("title", s.number_conflict ? __("ตัวเลขในชื่อไม่ตรงกัน") : s.item_code)
				.toggleClass("text-muted", s.number_conflict)
				.on("click", () => {
					item.$create.prop("checked", false);
					item.control.set_value(s.item_code);
				})
				.appendTo($tr.find(".match-suggestions"));
		});

		item.$create = $tr.find(".create-item").on("change", (e) => {
			if (e.target.checked) item.control.set_value("");
		});
	});

	// ติ๊กหัวคอลัมน์: สร้างใหม่ทุกแถวที่ยังไม่ได้เลือก BOQ Item
	$body.find(".create-all").on("change", (e) => {
		review.forEach((item) => {
			if (!e.target.checked) item.$create.prop("checked", false);
			else if (!item.control.get_value()) item.$create.prop("checked", true);
		});
	});
	dialog.show();
}

function apply_boq_import(frm, { info, warnings }, items, mode) {
	frappe
		.call({
			method: `${BOQ_EXCEL_METHOD}.apply_boq_matches`,
			args: {
				items: items.map(({ row, missing, item_code, create }) => ({ row, missing, item_code, create })),
			},
			freeze: true,
			freeze_message: __("กำลังนำเข้า..."),
		})
		.then(({ message: rows }) => {
			// หัวเอกสาร: แบบแทนที่ใช้ค่าจากไฟล์ทั้งหมด แบบต่อท้ายเติมเฉพาะช่องที่ยังว่าง
			Object.entries(info).forEach(([fieldname, value]) => {
				if (mode === "replace" || !frm.doc[fieldname]) frm.set_value(fieldname, value);
			});
			if (mode === "replace") frm.clear_table("boq_details");
			rows.forEach((row) => frm.add_child("boq_details", row));
			renumber_wbs(frm);
			set_boq_totals(frm);
			frm.refresh_field("boq_details");
			frappe.show_alert({ message: __("นำเข้า {0} รายการ", [rows.length]), indicator: "green" });
			if (warnings.length) frappe.msgprint(warnings.join("<br>"), __("คำเตือน"));
		});
}

function set_boq_totals(frm) {
	const sum = (fieldname) =>
		(frm.doc.boq_details || []).reduce((total, row) => total + flt(row[fieldname]), 0);
	frm.set_value({
		total_material_cost: sum("material_amount"),
		total_labour_cost: sum("labour_amount"),
		grand_total: sum("total_amount"),
	});
}

// ---------------------------------------------------------------------------
// WBS อัตโนมัติ, หมวด และแถบลอยเมื่อเลือกแถว
// ระดับของแถว = จำนวนส่วนใน WBS (1 = ระดับ 1, 1.1.1 = ระดับ 3) เลขรันใหม่ตามลำดับแถวเสมอ
// โดยคงระดับไว้ ต้องตรงกับ assign_wbs() ใน boq.py
// หัวข้องาน (หมวด) = แถวที่ไม่มี Item Code จำนวน และราคา (กฎเดียวกับ boq_excel.py)
// field ที่ขึ้นต้น __ ไม่ถูกบันทึก: __level = ระดับที่ต้องการ (แถวใหม่/เลื่อนระดับ)
// __boq_item = แถวว่างที่เพิ่มผ่าน "เพิ่มแถวในหมวด" ให้นับเป็นรายการ ไม่ใช่หมวด

function is_category(row) {
	if (row.__boq_item) return false;
	return !(row.item_code || flt(row.quantity) || flt(row.material_rate) || flt(row.labour_rate));
}

function wbs_level(row) {
	return row.__level || (row.wbs || "").split(".").filter((part) => part.trim()).length;
}

// แถวที่ยังไม่มีระดับ (แถวใหม่) อยู่ระดับเดียวกับแถวก่อนหน้า และลึกกว่าแถวก่อนหน้าได้ไม่เกิน 1 ระดับ
function renumber_wbs(frm) {
	let counters = [];
	(frm.doc.boq_details || []).forEach((row) => {
		const level = Math.max(1, Math.min(wbs_level(row) || counters.length || 1, counters.length + 1));
		counters = counters.slice(0, level);
		counters[level - 1] = (counters[level - 1] || 0) + 1;
		row.wbs = counters.join(".");
		delete row.__level;
	});
}

function refresh_wbs(frm) {
	renumber_wbs(frm);
	frm.refresh_field("boq_details");
}

// แถวลูกทั้งหมดของ row (แถวถัดไปที่ระดับลึกกว่า) นับรวม row เอง
function subtree(rows, row) {
	const start = rows.indexOf(row);
	const level = wbs_level(row);
	let end = start + 1;
	while (end < rows.length && wbs_level(rows[end]) > level) end++;
	return rows.slice(start, end);
}

function category_label(row) {
	const indent = "  ".repeat(Math.max(0, wbs_level(row) - 1));
	return `${indent}${row.wbs || ""} ${row.item_name || __("(ไม่มีชื่อหมวด)")}`.trim();
}

function category_options(frm, exclude = new Set()) {
	return (frm.doc.boq_details || [])
		.filter((row) => is_category(row) && !exclude.has(row.name))
		.map((row) => ({ label: category_label(row), value: row.name }));
}

function setup_category_tools(frm) {
	const grid = frm.fields_dict.boq_details.grid;
	// ฟอร์มเดียวถูกใช้ซ้ำกับทุกเอกสาร ซ่อนปุ่มก่อน แล้วแสดงเฉพาะตอนเป็น Draft
	grid.clear_custom_buttons();
	if (frm.doc.docstatus !== 0) return;

	grid.add_custom_button(__("เพิ่มแถวในหมวด"), () => {
		const options = category_options(frm);
		if (!options.length) {
			frappe.msgprint(
				__("ยังไม่มีหมวด: เพิ่มแถวที่มีแค่ WBS และชื่อ (ไม่ใส่ Item Code จำนวน ราคา) เป็นหัวหมวดก่อน")
			);
			return;
		}
		pick_category(
			__("เพิ่มแถวในหมวด"),
			__("เพิ่ม"),
			options,
			[{ fieldname: "count", fieldtype: "Int", label: __("จำนวนแถว"), default: 1, reqd: 1 }],
			({ category, count }) => {
				if (count < 1 || count > 500) {
					frappe.msgprint(__("จำนวนแถวต้องอยู่ระหว่าง 1 ถึง 500"));
					return false;
				}
				const rows = Array.from({ length: count }, () =>
					frm.add_child("boq_details", { __boq_item: 1 })
				);
				place_rows(frm, rows, category);
			}
		);
	});
}

function pick_category(title, action_label, options, extra_fields, callback) {
	const dialog = new frappe.ui.Dialog({
		title,
		fields: [
			{
				fieldname: "category",
				fieldtype: "Select",
				label: __("หมวด"),
				options,
				default: options[0].value,
				reqd: 1,
			},
			...extra_fields,
		],
		primary_action_label: action_label,
		primary_action(values) {
			if (callback(values) !== false) dialog.hide();
		},
	});
	dialog.show();
}

// ย้าย rows (พร้อมแถวลูก) ไปต่อท้ายหมวด category เป็นระดับใต้หมวดนั้น แล้วรันเลข WBS ใหม่
function place_rows(frm, rows, category) {
	const all = frm.doc.boq_details;
	const target = all.find((row) => row.name === category);
	const target_level = wbs_level(target);

	// แถวใหม่ยังไม่มีระดับ ถือเป็นระดับเดียวกับรายการในหมวด
	const moving = [];
	rows.forEach((row) => {
		if (moving.includes(row)) return;
		const root_level = wbs_level(row) || target_level + 1;
		const branch = row.wbs ? subtree(all, row) : [row];
		branch.forEach((child) => {
			child.__level = target_level + 1 + ((wbs_level(child) || root_level) - root_level);
			moving.push(child);
		});
	});

	const remaining = all.filter((row) => !moving.includes(row));
	const insert_at = remaining.indexOf(target) + subtree(remaining, target).length;
	remaining.splice(insert_at, 0, ...moving);
	remaining.forEach((row, i) => (row.idx = i + 1));
	frm.doc.boq_details = remaining;

	refresh_wbs(frm);
	frm.dirty();
}

// เลื่อนระดับแถวที่เลือก (พร้อมแถวลูก) step = 1 ย่อเข้า, -1 ดึงออก
function shift_level(frm, step) {
	const all = frm.doc.boq_details;
	const shifting = new Set();
	frm.fields_dict.boq_details.grid.get_selected_children().forEach((row) => {
		subtree(all, row).forEach((child) => shifting.add(child));
	});

	// อ่านระดับเดิมทุกแถวก่อนแก้ แถวที่ไม่ได้เลือกคงระดับเดิม
	const levels = new Map(all.map((row) => [row, wbs_level(row)]));
	all.forEach((row) => {
		row.__level = shifting.has(row) ? Math.max(1, levels.get(row) + step) : levels.get(row);
	});

	refresh_wbs(frm);
	frm.dirty();
}

function clear_selection(frm) {
	const grid = frm.fields_dict.boq_details.grid;
	(frm.doc.boq_details || []).forEach((row) => (row.__checked = 0));
	grid.wrapper.find(".grid-row-check").prop("checked", false);
	grid.refresh();
	update_select_banner(frm);
}

function update_select_banner(frm) {
	const grid = frm.fields_dict.boq_details.grid;
	const selected = frm.doc.docstatus === 0 ? grid.get_selected_children() : [];

	if (!frm.select_banner) {
		frm.select_banner = $(`
			<div class="consbiz-select-banner hidden">
				<span class="banner-count"></span>
				<button class="btn btn-default btn-sm" data-action="outdent" title="${__("ดึงออก 1 ระดับ")}">
					← ${__("ลดระดับ")}
				</button>
				<button class="btn btn-default btn-sm" data-action="indent" title="${__("ย่อเข้า 1 ระดับ")}">
					${__("เพิ่มระดับ")} →
				</button>
				<button class="btn btn-default btn-sm" data-action="move">${__("ย้ายไปหมวด")}</button>
				<button class="btn btn-danger btn-sm" data-action="delete">${__("ลบ")}</button>
				<button class="btn btn-link btn-sm text-muted" data-action="clear" title="${__("ยกเลิกการเลือก")}">
					${frappe.utils.icon("x", "sm")}
				</button>
			</div>
		`).appendTo(frm.wrapper);

		// เลื่อนระดับแล้วยังเลือกไว้ กดซ้ำได้
		frm.select_banner.on("click", "[data-action=indent]", () => shift_level(frm, 1));
		frm.select_banner.on("click", "[data-action=outdent]", () => shift_level(frm, -1));
		frm.select_banner.on("click", "[data-action=move]", () => move_selected(frm));
		frm.select_banner.on("click", "[data-action=delete]", () => {
			grid.delete_rows();
			setTimeout(() => update_select_banner(frm), 300);
		});
		frm.select_banner.on("click", "[data-action=clear]", () => clear_selection(frm));
	}

	frm.select_banner.toggleClass("hidden", !selected.length);
	frm.select_banner.find(".banner-count").text(__("เลือก {0} แถว", [selected.length]));
}

function move_selected(frm) {
	const all = frm.doc.boq_details;
	const selected = frm.fields_dict.boq_details.grid.get_selected_children();
	// ห้ามย้ายไปหมวดที่อยู่ในกลุ่มที่กำลังย้าย (ย้ายไปใต้ตัวเอง)
	const moving = new Set();
	selected.forEach((row) => subtree(all, row).forEach((child) => moving.add(child.name)));

	const options = category_options(frm, moving);
	if (!options.length) {
		frappe.msgprint(__("ไม่มีหมวดให้ย้ายไป"));
		return;
	}

	pick_category(__("ย้าย {0} แถวไปหมวด", [selected.length]), __("ย้าย"), options, [], ({ category }) => {
		place_rows(frm, selected, category);
		clear_selection(frm);
	});
}

// ---- ย้ายจาก Client Script "BOQ Calulation" ----

// 1. Event ภายใน Child Table (BOQ Item Detail)
frappe.ui.form.on('BOQ Item Detail', {
    // ดึงราคา material_rate และ labour_rate ครั้งเดียวเมื่อเลือก item_code
    item_code: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];

        if (row.item_code) {
            frappe.db.get_value('BOQ Item', row.item_code, ['material_rate', 'labour_rate'])
                .then(r => {
                    if (r.message) {
                        Promise.all([
                            frappe.model.set_value(cdt, cdn, 'material_rate', flt(r.message.material_rate)),
                            frappe.model.set_value(cdt, cdn, 'labour_rate', flt(r.message.labour_rate))
                        ]).then(() => {
                            calculate_row_totals(frm, cdt, cdn);
                        });
                    }
                });
        }
    },

    quantity: function(frm, cdt, cdn) {
        calculate_row_totals(frm, cdt, cdn);
    },
    material_rate: function(frm, cdt, cdn) {
        calculate_row_totals(frm, cdt, cdn);
    },
    labour_rate: function(frm, cdt, cdn) {
        calculate_row_totals(frm, cdt, cdn);
    }
});

// 2. Event เมื่อมีการลบแถวออกจาก Child Table
// หมายเหตุ: แทนที่ 'boq_details' ด้วย Fieldname ของตาราง Child Table ในตัวแม่
frappe.ui.form.on('BOQ Item Detail', {
    boq_details_remove: function(frm) {
        calculate_grand_totals(frm);
    }
});

// ฟังก์ชันคำนวณแต่ละแถว (Child Table)
function calculate_row_totals(frm, cdt, cdn) {
    let row = locals[cdt][cdn];

    let qty = flt(row.quantity);
    let mat_rate = flt(row.material_rate);
    let lab_rate = flt(row.labour_rate);

    let mat_amount = qty * mat_rate;
    let lab_amount = qty * lab_rate;
    let tot_amount = mat_amount + lab_amount;

    frappe.model.set_value(cdt, cdn, 'material_amount', mat_amount);
    frappe.model.set_value(cdt, cdn, 'labour_amount', lab_amount);
    frappe.model.set_value(cdt, cdn, 'total_amount', tot_amount);

    // คำนวณยอดรวมส่งเข้า Parent ต่อทันที
    calculate_grand_totals(frm);
}

// ฟังก์ชันรวมยอดสรุปเข้า Parent DocType
function calculate_grand_totals(frm) {
    let total_material = 0;
    let total_labour = 0;
    let grand_total = 0;

    // หาตาราง Child Table ในฟอร์มให้อัตโนมัติ (รองรับ boq_details หรือชื่ออื่น)
    let child_rows = frm.doc.boq_details || frm.doc.items || [];
    
    // หากชื่อตารางไม่ตรง ให้ลองค้นหา Child Table ที่ใช้ DocType 'BOQ Item Detail'
    if (!child_rows.length && frm.meta.fields) {
        let table_field = frm.meta.fields.find(f => f.fieldtype === 'Table' && f.options === 'BOQ Item Detail');
        if (table_field && frm.doc[table_field.fieldname]) {
            child_rows = frm.doc[table_field.fieldname];
        }
    }

    // วนลูปบวกยอดจากทุกแถว
    (child_rows || []).forEach(row => {
        total_material += flt(row.material_amount);
        total_labour += flt(row.labour_amount);
        grand_total += flt(row.total_amount);
    });

    // อัปเดต 3 ฟิลด์สรุปเข้า Parent
    // มี if (frm.fields_dict[...]) ดักไว้ เพื่อไม่ให้ขึ้น Error สีแดงหากใน DocType ยังไม่ได้สร้างฟิลด์
    if (frm.fields_dict['total_material_cost']) {
        frm.set_value('total_material_cost', total_material);
    }
    if (frm.fields_dict['total_labour_cost']) {
        frm.set_value('total_labour_cost', total_labour);
    }
    if (frm.fields_dict['grand_total']) {
        frm.set_value('grand_total', grand_total);
    }

    frm.refresh_fields();
}

// ---- ย้ายจาก Client Script "Get Price History" ----

// เปลี่ยน 'BOQ Item Detail' เป็นชื่อ Child DocType ของคุณ
frappe.ui.form.on('BOQ Item Detail', {
    
    get_price_history: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];

        if (!row.item_code) {
            frappe.msgprint(__('กรุณาเลือกรหัสวัสดุ (Item Code) ก่อนดูประวัติราคา'));
            return;
        }

        let d = new frappe.ui.Dialog({
            title: 'ประวัติราคา: ' + row.item_code,
            fields: [{ fieldname: 'history_html', fieldtype: 'HTML' }],
            size: 'large', // ขยายหน้าต่างให้กว้างขึ้นเพื่อดูกราฟได้ชัดเจน
            primary_action_label: 'ปิดหน้าต่าง',
            primary_action: function() { d.hide(); }
        });

        d.fields_dict.history_html.$wrapper.html('<p class="text-muted">กำลังโหลดข้อมูลและสร้างกราฟ...</p>');
        d.show();

        frappe.call({
            method: 'frappe.client.get_list',
            args: {
                doctype: 'BOQ',
                filters: [
                    ['docstatus', '=', 0],
                    ['name', '!=', frm.doc.name],
                    ['BOQ Item Detail', 'item_code', '=', row.item_code]
                ],
                fields: [
                    'name',
                    'creation',
                    '`tabBOQ Item Detail`.material_rate as material_rate',
                    '`tabBOQ Item Detail`.labour_rate as labour_rate'
                ],
                limit_page_length: 1000, // ดึงข้อมูลเยอะหน่อยเพื่อหาค่า สูงสุด-ต่ำสุด ที่เคยมีมา
                order_by: 'creation desc'
            },
            callback: function(r) {
                if (r.message && r.message.length > 0) {
                    let all_data = r.message;

                    // 1. หาค่าสูงสุด-ต่ำสุด จากประวัติทั้งหมด (All time)
                    let max_mat = Math.max(...all_data.map(i => i.material_rate || 0));
                    let min_mat = Math.min(...all_data.map(i => i.material_rate || 0));
                    let max_lab = Math.max(...all_data.map(i => i.labour_rate || 0));
                    let min_lab = Math.min(...all_data.map(i => i.labour_rate || 0));

                    // 2. ตัดเอาเฉพาะ 20 รายการล่าสุด
                    let last_20 = all_data.slice(0, 20);

                    // 3. ฟังก์ชันแปลงวันที่ให้อยู่ในฟอร์แมต dd/mm/yyyy
                    const formatDate = (dateStr) => {
                        let dateObj = frappe.datetime.str_to_obj(dateStr);
                        let dd = String(dateObj.getDate()).padStart(2, '0');
                        let mm = String(dateObj.getMonth() + 1).padStart(2, '0');
                        let yyyy = dateObj.getFullYear();
                        return `${dd}/${mm}/${yyyy}`;
                    };

                    // 4. เตรียมข้อมูลสำหรับพล็อตกราฟ (ต้อง Reverse ให้ข้อมูลเก่าอยู่ซ้าย ใหม่สุดอยู่ขวา)
                    let chart_data = [...last_20].reverse();
                    let chart_labels = chart_data.map(i => formatDate(i.creation));
                    let chart_mat_series = chart_data.map(i => i.material_rate);
                    let chart_lab_series = chart_data.map(i => i.labour_rate);

// ฟังก์ชันช่วยจัดฟอร์แมตตัวเลข (ป้องกันการขึ้นบรรทัดใหม่จาก Currency ของ Frappe)
                    const formatNumber = (num) => Number(num || 0).toLocaleString('en', {minimumFractionDigits: 2, maximumFractionDigits: 2});

                    // 5. สร้างโครงสร้าง HTML (กราฟ -> สรุป -> ตาราง)
                    let html = `
                        <!-- พื้นที่สำหรับแสดงกราฟ -->
                        <div id="price-chart-container" style="margin-bottom: 20px;"></div>
                        
                        <!-- พื้นที่สรุปราคาสูงสุด-ต่ำสุด -->
                        <div style="display: flex; gap: 15px; margin-bottom: 20px;">
                            <!-- กล่อง Material Rate -->
                            <div style="flex: 1; background-color: #f4f5f6; padding: 15px; border-radius: 8px; border: 1px solid #d1d8dd;">
                                <div class="text-center text-muted text-uppercase text-small" style="margin-bottom: 10px; font-weight: 600;">
                                    Material Rate (ทั้งหมด)
                                </div>
                                <div style="display: flex; justify-content: space-around; font-size: 14px;">
                                    <span style="color: #e74c3c; font-weight: bold;">
                                        <i class="fa fa-arrow-down"></i> ต่ำสุด: ${formatNumber(min_mat)}
                                    </span>
                                    <span style="color: #27ae60; font-weight: bold;">
                                        <i class="fa fa-arrow-up"></i> สูงสุด: ${formatNumber(max_mat)}
                                    </span>
                                </div>
                            </div>

                            <!-- กล่อง Labour Rate -->
                            <div style="flex: 1; background-color: #f4f5f6; padding: 15px; border-radius: 8px; border: 1px solid #d1d8dd;">
                                <div class="text-center text-muted text-uppercase text-small" style="margin-bottom: 10px; font-weight: 600;">
                                    Labour Rate (ทั้งหมด)
                                </div>
                                <div style="display: flex; justify-content: space-around; font-size: 14px;">
                                    <span style="color: #e74c3c; font-weight: bold;">
                                        <i class="fa fa-arrow-down"></i> ต่ำสุด: ${formatNumber(min_lab)}
                                    </span>
                                    <span style="color: #2980b9; font-weight: bold;">
                                        <i class="fa fa-arrow-up"></i> สูงสุด: ${formatNumber(max_lab)}
                                    </span>
                                </div>
                            </div>
                        </div>

                        <!-- พื้นที่ตาราง -->
                        <table class="table table-bordered table-striped" style="font-size: 13px;">
                            <thead>
                                <tr>
                                    <th width="20%">วันที่</th>
                                    <th width="40%">เลขที่เอกสาร</th>
                                    <th class="text-right" width="20%">Material Rate</th>
                                    <th class="text-right" width="20%">Labour Rate</th>
                                </tr>
                            </thead>
                            <tbody>
                    `;

                    // วนลูปสร้างบรรทัดในตาราง (20 รายการ)
                    last_20.forEach(item => {
                        html += `
                            <tr>
                                <td>${formatDate(item.creation)}</td>
                                <td><strong>${item.name}</strong></td>
                                <td class="text-right">${frappe.format(item.material_rate, {fieldtype: 'Currency'})}</td>
                                <td class="text-right">${frappe.format(item.labour_rate, {fieldtype: 'Currency'})}</td>
                            </tr>
                        `;
                    });

                    html += `</tbody></table>`;
                    
                    // นำ HTML ใส่ลงใน Dialog
                    d.fields_dict.history_html.$wrapper.html(html);

                    // 6. เรียกใช้ Frappe Charts วาดกราฟ (ตั้งหน่วงเวลาเล็กน้อยเพื่อให้ HTML เรนเดอร์เสร็จก่อน)
                    setTimeout(() => {
                        new frappe.Chart(d.fields_dict.history_html.$wrapper.find("#price-chart-container")[0], {
                            title: `แนวโน้มราคา 20 ครั้งล่าสุด`,
                            data: {
                                labels: chart_labels,
                                datasets: [
                                    {
                                        name: "Material Rate",
                                        type: "line",
                                        values: chart_mat_series
                                    },
                                    {
                                        name: "Labour Rate",
                                        type: "line",
                                        values: chart_lab_series
                                    }
                                ]
                            },
                            type: 'axis-mixed', // กราฟเส้นแกนผสม
                            height: 250,
                            colors: ['#27ae60', '#2980b9'], // สีเขียว และ สีฟ้า
                            tooltipOptions: {
                                formatTooltipX: d => (d + '').toUpperCase(),
                                formatTooltipY: d => frappe.format(d, {fieldtype: 'Currency'})
                            }
                        });
                    }, 300);

                } else {
                    d.fields_dict.history_html.$wrapper.html('<p class="text-muted">ไม่พบประวัติราคาที่อนุมัติแล้วสำหรับวัสดุนี้</p>');
                }
            }
        });
    }
});
