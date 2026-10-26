// Copyright (c) 2026, Siricons and contributors
// For license information, please see license.txt

const BOQ_EXCEL_METHOD = "consbiz.consbiz.doctype.boq.boq_excel";

frappe.ui.form.on("BOQ", {
	refresh(frm) {
		add_excel_buttons(frm);
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
// ดึงทับทุกครั้งที่บันทึก ค่าที่แก้หรือนำเข้าจาก Excel จะหาย) ราคาดึงใน Client Script "BOQ Calulation"
frappe.ui.form.on("BOQ Item Detail", {
	item_code(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (!row.item_code) return;
		frappe.db
			.get_value("BOQ Item", row.item_code, ["item_name", "uom", "item_group"])
			.then(({ message }) => message && frappe.model.set_value(cdt, cdn, message));
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
