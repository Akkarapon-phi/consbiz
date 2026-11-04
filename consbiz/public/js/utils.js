//================================================================
// Bahttext Fuction
//================================================================

window.thai_baht_text = function(num) {
    if (num === null || num === undefined || num === '') return '';
    
    num = parseFloat(num).toFixed(2);
    let parts = num.split('.');
    let baht = parseInt(parts[0]);
    let satang = parseInt(parts[1]);

    let result = text_num_thai(baht);
    if (result === '') result = 'ศูนย์';
    result += 'บาท';

    if (satang === 0) {
        result += 'ถ้วน';
    } else {
        result += text_num_thai(satang) + 'สตางค์';
    }
    return result;
};

window.text_num_thai = function(num) {
    const thai_num = ["ศูนย์", "หนึ่ง", "สอง", "สาม", "สี่", "ห้า", "หก", "เจ็ด", "แปด", "เก้า"];
    const thai_unit = ["", "สิบ", "ร้อย", "พัน", "หมื่น", "แสน", "ล้าน"];
    
    let res = "";
    let num_str = num.toString();
    let len = num_str.length;

    for (let i = 0; i < len; i++) {
        let n = parseInt(num_str[i]);
        let pos = len - i - 1;
        let unit_pos = pos % 6;

        if (n !== 0) {
            // Logic "เอ็ด"
            if (unit_pos === 0 && n === 1 && i > 0) { 
                res += 'เอ็ด'; 
            } else if (unit_pos === 1 && n === 2) {
                res += 'ยี่';
            } else if (unit_pos === 1 && n === 1) {
                // สิบ
            } else {
                res += thai_num[n];
            }
            res += thai_unit[unit_pos];
        }
        
        // เติม "ล้าน"
        if (pos > 0 && pos % 6 === 0) {
            res += 'ล้าน';
        }
    }
    return res;
};

//================================================================
// BOQ Item price trend (BOQ Item form)
//================================================================

window.consbiz = window.consbiz || {};

// ราคาของรายการใน BOQ แต่ละใบ: สรุปราคามาตรฐาน/ต่ำสุด/สูงสุด + กราฟเส้น + ตาราง 10 ใบล่าสุด
consbiz.render_price_history = function (wrapper, item_code) {
    const $wrapper = $(wrapper).html(`<p class="text-muted">${__("กำลังโหลด...")}</p>`);
    return frappe
        .call("consbiz.consbiz.doctype.boq_item.boq_item.get_price_history", { item_code })
        .then(({ message: data }) => {
            const money = (value) => format_number(value, null, 2);
            const history = data.history;
            if (!history.length) {
                $wrapper.html(`<p class="text-muted">${__("ยังไม่มีรายการนี้ใน BOQ")}</p>`);
                return;
            }

            const summary = (label, field) => {
                const values = history.map((row) => flt(row[field]));
                return `<div class="col-sm-6">
                    <div class="text-muted">${label}</div>
                    <div>${__("มาตรฐาน")} <b>${money(data[field])}</b>
                        <span class="text-muted ml-2">${__("ต่ำสุด")} ${money(Math.min(...values))}
                        · ${__("สูงสุด")} ${money(Math.max(...values))}</span></div>
                </div>`;
            };
            const recent = history
                .slice(-10)
                .reverse()
                .map(
                    (row) => `<tr>
                        <td>${frappe.datetime.str_to_user(row.date)}</td>
                        <td><a href="/app/boq/${encodeURIComponent(row.boq)}">${frappe.utils.escape_html(row.boq)}</a></td>
                        <td>${frappe.utils.escape_html(row.project || "")}</td>
                        <td class="text-right">${money(row.material_rate)}</td>
                        <td class="text-right">${money(row.labour_rate)}</td>
                    </tr>`
                )
                .join("");

            $wrapper.html(`
                <div class="row small mb-3">
                    ${summary(__("ค่าวัสดุต่อหน่วย"), "material_rate")}
                    ${summary(__("ค่าแรงต่อหน่วย"), "labour_rate")}
                </div>
                <div class="price-history-chart"></div>
                <table class="table table-sm small mt-2 mb-0">
                    <thead><tr>
                        <th>${__("วันที่")}</th><th>${__("BOQ")}</th><th>${__("โครงการ")}</th>
                        <th class="text-right">${__("ค่าวัสดุ")}</th><th class="text-right">${__("ค่าแรง")}</th>
                    </tr></thead>
                    <tbody>${recent}</tbody>
                </table>`);

            new frappe.Chart($wrapper.find(".price-history-chart")[0], {
                type: "line",
                height: 220,
                data: {
                    labels: history.map((row) => frappe.datetime.str_to_user(row.date)),
                    datasets: [
                        { name: __("ค่าวัสดุ"), values: history.map((row) => flt(row.material_rate)) },
                        { name: __("ค่าแรง"), values: history.map((row) => flt(row.labour_rate)) },
                    ],
                },
                lineOptions: { dotSize: 5 },
                axisOptions: { xIsSeries: 1 },
                tooltipOptions: { formatTooltipY: (value) => money(value) },
            });
        });
};

//================================================================
// ปริมาณที่กรอกตามคงเหลือที่แสดง (Daily Report, Daily Request)
//================================================================

// คงเหลือจริง 0.5488 แสดงเป็น 0.55 กรอกตามที่เห็นแล้วเกินไม่ถึงครึ่งหน่วยของทศนิยมที่แสดง = ทำครบพอดี
// ปรับเป็นคงเหลือจริง (ต้องตรงกับ fit_to_remaining ใน daily_report.py)
consbiz.fit_to_remaining = function (row, source) {
    const field = row.boq_qty > 0 ? "qty" : "percent";
    if (field !== source || !row[field]) return;
    const total = field === "qty" ? row.boq_qty : 100;
    const previous = (field === "qty" ? row.previous_qty : row.previous_percent) || 0;
    const over = previous + row[field] - total;
    if (over > 0 && over < 0.5 / Math.pow(10, cint(precision(field, row)) || 3)) {
        row[field] = total - previous;
    }
};

//================================================================
// Manpower / Equipment ตั้งต้น (Daily Report, Daily Request)
//================================================================

// เอกสารใหม่: ใส่รายชื่อตั้งต้นให้กรอกแค่จำนวน (รายชื่อจากเอกสารล่าสุดของแผนงานเดียวกัน + รายการมาตรฐาน)
// เปลี่ยนแผนงานแล้วโหลดใหม่ได้ตราบที่ยังไม่กรอกจำนวน แถวที่ไม่กรอกจำนวนถูกลบตอนบันทึก
consbiz.fill_default_resources = function (frm) {
    if (!frm.is_new()) return;
    const untouched = (field) => !(frm.doc[field] || []).some((row) => row.qty || row.hours);
    const fill_labour = untouched("labour");
    const fill_equipment = untouched("equipment");
    if (!fill_labour && !fill_equipment) return;
    frappe
        .call("consbiz.consbiz.doctype.daily_report.daily_report.get_default_resources", {
            doctype: frm.doctype,
            construction_management: frm.doc.construction_management,
        })
        .then(({ message }) => {
            if (fill_labour) {
                frm.clear_table("labour");
                message.labour.forEach((role) => frm.add_child("labour", { role }));
                frm.refresh_field("labour");
            }
            if (fill_equipment) {
                frm.clear_table("equipment");
                message.equipment.forEach((equipment) => frm.add_child("equipment", { equipment }));
                frm.refresh_field("equipment");
            }
        });
};

// Daily Report / Daily Request สร้างได้หลายฉบับต่อวัน (แบ่งกันลงหลายคน): แถบบนฟอร์มบอกว่าวันนั้นมีใครสร้างอะไรไปแล้ว
// เรียกใน refresh / construction_management / date ของทั้งสองฟอร์ม (ข้อมูลจาก daily_report.get_same_day_documents)
consbiz.show_same_day = async function (frm) {
	frm.dashboard.clear_comment();
	const { construction_management, date } = frm.doc;
	if (!construction_management || !date || frm.doc.docstatus === 2) return;
	const key = `${construction_management}|${date}|${frm.doc.name}`;
	frm._same_day_key = key;
	const { message } = await frappe.call({
		method: "consbiz.consbiz.doctype.daily_report.daily_report.get_same_day_documents",
		args: { construction_management, date, exclude: frm.is_new() ? null : frm.doc.name },
	});
	if (frm._same_day_key !== key) return;
	const parts = Object.entries(message || {})
		.filter(([, rows]) => rows.length)
		.map(
			([doctype, rows]) =>
				`${__(doctype)}: ` +
				rows
					.map(
						(row) =>
							`<a href="/app/${frappe.router.slug(doctype)}/${encodeURIComponent(row.name)}">${frappe.utils.escape_html(row.name)}</a>` +
							` (${frappe.utils.escape_html(row.owner_name)}${row.docstatus === 0 ? `, ${__("ร่าง")}` : ""})`
					)
					.join(", ")
		);
	if (!parts.length) return;
	frm.dashboard.add_comment(
		`${__("วันที่ {0} มีเอกสารแล้ว", [frappe.datetime.str_to_user(date)])} · ${parts.join(" · ")}`,
		"blue",
		true
	);
};

//================================================================
// WBS ของรายการสต็อก (Stock Entry, Material Request)
//================================================================

// ช่อง custom_wbs ในตาราง items เป็น Autocomplete ตัวเลือก = งานย่อยของแผนงานของโครงการ (site_stock.get_wbs_options)
// ฝั่ง server ตรวจซ้ำและเก็บชื่องานไว้ใน custom_task_name
consbiz.set_wbs_options = async function (frm, project) {
	const grid = frm.fields_dict.items?.grid;
	if (!grid || !grid.get_docfield("custom_wbs")) return;
	const { message } = project
		? await frappe.call("consbiz.site_stock.get_wbs_options", { project })
		: { message: [] };
	grid.update_docfield_property("custom_wbs", "options", message || []);
};

//================================================================
// รับคืนอุปกรณ์ (ฟอร์ม Equipment Borrowing และหน้าสโตร์หน้างาน)
//================================================================

// แสดงรายการที่ยังค้างคืน กรอกจำนวนที่คืนและสภาพ ผู้คืนเซ็นในกล่องลายเซ็น
// บันทึกด้วย equipment_borrowing.record_return (สร้าง Stock Entry ให้เอง) แล้วเรียก on_done
consbiz.equipment_return_dialog = async function (name, on_done) {
	const doc = await frappe.db.get_doc("Equipment Borrowing", name);
	const rows = (doc.items || [])
		.filter((row) => row.outstanding_qty > 0)
		.map((row) => ({
			item_code: row.item_code,
			item_name: row.item_name,
			outstanding_qty: row.outstanding_qty,
			qty: row.outstanding_qty,
			condition: "Good",
		}));
	const dialog = new frappe.ui.Dialog({
		title: __("รับคืนอุปกรณ์: {0}", [doc.borrower_name || name]),
		size: "large",
		fields: [
			{ fieldname: "date", fieldtype: "Date", label: __("วันที่คืน"), default: frappe.datetime.get_today(), reqd: 1 },
			{ fieldname: "returned_by", fieldtype: "Data", label: __("ผู้คืน"), default: doc.borrower_name },
			{
				fieldname: "items",
				fieldtype: "Table",
				label: __("รายการ"),
				cannot_add_rows: true,
				in_place_edit: true,
				data: rows,
				fields: [
					{ fieldname: "item_code", fieldtype: "Link", options: "Item", label: __("อุปกรณ์"), read_only: 1, in_list_view: 1, columns: 4 },
					{ fieldname: "outstanding_qty", fieldtype: "Float", label: __("ค้างคืน"), read_only: 1, in_list_view: 1, columns: 2 },
					{ fieldname: "qty", fieldtype: "Float", label: __("คืน"), in_list_view: 1, columns: 2 },
					{
						fieldname: "condition",
						fieldtype: "Select",
						label: __("สภาพ"),
						options: [
							{ value: "Good", label: __("ปกติ") },
							{ value: "Damaged", label: __("ชำรุด") },
							{ value: "Lost", label: __("สูญหาย") },
						],
						in_list_view: 1,
						columns: 2,
					},
				],
			},
			{ fieldname: "signature", fieldtype: "Signature", label: __("ลายเซ็นผู้คืน") },
			{ fieldname: "photo", fieldtype: "Attach Image", label: __("รูปถ่าย") },
			{ fieldname: "remarks", fieldtype: "Small Text", label: __("หมายเหตุ") },
		],
		primary_action_label: __("บันทึกรับคืน"),
		async primary_action(values) {
			const items = (values.items || []).map(({ item_code, qty, condition }) => ({ item_code, qty, condition }));
			await frappe.call({
				method: "consbiz.consbiz.doctype.equipment_borrowing.equipment_borrowing.record_return",
				args: { ...values, name, items: JSON.stringify(items) },
				freeze: true,
			});
			dialog.hide();
			frappe.show_alert({ message: __("บันทึกรับคืนแล้ว"), indicator: "green" });
			on_done && on_done();
		},
	});
	dialog.show();
};

//================================================================
// คลังของโครงการ (1 คลังต่อโครงการ สร้างให้ตอนสร้าง Project: site_stock.ensure_project_warehouse)
//================================================================

// ตั้งคลังของโครงการลงช่องที่ยังว่าง เช่น consbiz.set_project_warehouse(frm, frm.doc.project, ["from_warehouse"])
consbiz.set_project_warehouse = async function (frm, project, fields) {
	if (!project || !frm.is_new()) return;
	const empty = fields.filter((field) => !frm.doc[field]);
	if (!empty.length) return;
	const { message } = await frappe.call("consbiz.site_stock.get_project_warehouse", { project });
	if (!message) return;
	empty.forEach((field) => !frm.doc[field] && frm.set_value(field, message));
};

// หน้าซองจดหมายจากเอกสารต้นทาง (Transmittal / Sales Invoice: consbiz/consbiz/doctype/envelope/envelope.py)
consbiz.make_envelope = async function (frm) {
	const doc = await frappe.xcall("consbiz.consbiz.doctype.envelope.envelope.make_envelope", {
		source_doctype: frm.doctype,
		source_name: frm.doc.name,
	});
	frappe.model.sync(doc);
	frappe.set_route("Form", doc.doctype, doc.name);
};
