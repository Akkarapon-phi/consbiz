// Script for DocType: Material Request

// ---- ย้ายจาก Client Script "Material Request Print" ----

frappe.ui.form.on("Material Request", {
	refresh(frm) {
		// ลบไอคอนเดิมก่อน กันปุ่มซ้ำทุกครั้งที่ refresh
		if (frm._pr_print_icon) {
			frm._pr_print_icon.remove();
			frm._pr_print_icon = null;
		}

		if (
			frm.is_new() ||
			!["Purchase", "Customer Provided"].includes(frm.doc.material_request_type) ||
			frm.doc.docstatus === 2 ||
			!frappe.model.can_print(frm.doctype, frm)
		) {
			return;
		}

		frm._pr_print_icon = frm.page.add_action_icon(
			"printer",
			() => {
				if (frm.is_dirty()) {
					frappe.msgprint(__("กรุณา Save เอกสารก่อนพิมพ์"));
					return;
				}
				show_pr_pdf(frm);
			},
			"",
			// tooltip เมื่อเอาเมาส์ชี้
			frm.doc.material_request_type === "Customer Provided" ? __("ใบสั่งวัสดุ (ผู้ว่าจ้างจัดหา)") : __("Purchase Request")
		);
	},
});

function show_pr_pdf(frm) {
	// docstatus 0 = Draft, 1 = Submitted / ผู้ว่าจ้างจัดหาใช้ใบสั่งวัสดุ (Print Format standard ของ consbiz)
	let print_format = frm.doc.docstatus === 1 ? "Purchase Request (Sign)" : "Purchase Request";
	if (frm.doc.material_request_type === "Customer Provided") print_format = "Employer Material Order";

	const params = new URLSearchParams({
		doctype: frm.doctype,
		name: frm.doc.name,
		format: print_format,
		no_letterhead: 1,
		settings: "{}",
		_lang: "th",
		pdf_generator: "wkhtmltopdf",
	});

	const pdf_url = frappe.urllib.get_full_url(
		`/api/method/frappe.utils.print_format.download_pdf?${params.toString()}`
	);

	const dialog = new frappe.ui.Dialog({
		title: __("{0}: {1}", [print_format, frm.doc.name]),
		size: "extra-large",
		fields: [
			{
				fieldtype: "HTML",
				fieldname: "pdf_preview",
				options: `<iframe src="${pdf_url}"
                        style="width:100%; height:75vh; border:none;"></iframe>`,
			},
		],
		primary_action_label: __("เปิดในแท็บใหม่"),
		primary_action() {
			window.open(pdf_url, "_blank");
		},
	});

	dialog.show();
}

// ---- ย้ายจาก Client Script "Material Request - Calulation" ----

// Client Script — DocType: Material Request (Apply To: Form)
// รวมยอดจาก items.amount, แยกยอดที่ไม่คิด VAT, คำนวณ VAT 7%, รองรับราคารวม VAT
// และ override VAT จากนั้นแปลง custom_grand_total เป็นตัวอักษรไทยใน custom_in_words

const VAT_RATE = 7;

frappe.ui.form.on("Material Request", {
	validate(frm) {
		calculate_totals(frm, true); // ตอน save ใส่ค่าตรงลง doc เพื่อให้บันทึกแน่นอน
	},
	custom_included_vat(frm) {
		calculate_totals(frm);
	},
	custom_vat_override(frm) {
		calculate_totals(frm);
	},
	custom_vat(frm) {
		// ถ้าไม่ได้ override ค่า VAT มาจากการคำนวณอยู่แล้ว ไม่ต้องคำนวณซ้ำ (กัน loop)
		if (frm.doc.custom_vat_override) calculate_totals(frm);
	},
	custom_grand_total(frm) {
		update_thai_baht_text(frm);
	},
});

frappe.ui.form.on("Material Request Item", {
	qty(frm) {
		schedule_calculate(frm);
	},
	rate(frm) {
		schedule_calculate(frm);
	},
	amount(frm) {
		schedule_calculate(frm);
	},
	custom_vat_nocal(frm) {
		schedule_calculate(frm);
	},
	items_remove(frm) {
		schedule_calculate(frm);
	},
});

// รวม event ที่ยิงติดกัน (qty → amount) ให้คำนวณครั้งเดียวหลังค่าในแถวนิ่งแล้ว
let _calc_timer = null;
function schedule_calculate(frm) {
	clearTimeout(_calc_timer);
	_calc_timer = setTimeout(() => calculate_totals(frm), 150);
}

function calculate_totals(frm, direct = false) {
	let sum_vat = 0; // ยอดที่ต้องคิด VAT
	let sum_novat = 0; // ยอดที่ไม่คิด VAT (custom_vat_nocal = 1)

	(frm.doc.items || []).forEach((row) => {
		// คำนวณจาก qty * rate โดยตรง เพราะตอน event qty/rate ทำงาน
		// row.amount อาจยังเป็นค่าเก่า (ERPNext อัปเดตทีหลัง)
		let amount = flt(row.rate) ? flt(row.qty) * flt(row.rate) : flt(row.amount);
		if (cint(row.custom_vat_nocal)) {
			sum_novat += amount;
		} else {
			sum_vat += amount;
		}
	});

	let net_total, vat;

	if (frm.doc.material_request_type === CUSTOMER_PROVIDED) {
		// ผู้ว่าจ้างจัดหา: ไม่มี VAT (ช่อง VAT ซ่อนอยู่)
		net_total = sum_vat;
		vat = 0;
	} else if (cint(frm.doc.custom_vat_override)) {
		// ใช้ค่า VAT ที่ผู้ใช้กรอกเอง
		vat = flt(frm.doc.custom_vat, 2);
		net_total = cint(frm.doc.custom_included_vat) ? sum_vat - vat : sum_vat;
	} else if (cint(frm.doc.custom_included_vat)) {
		// amount รวม VAT แล้ว → ถอดยอดก่อนภาษี
		net_total = (sum_vat * 100) / (100 + VAT_RATE);
		vat = sum_vat - net_total;
	} else {
		net_total = sum_vat;
		vat = (sum_vat * VAT_RATE) / 100;
	}

	net_total = flt(net_total, 2);
	vat = flt(vat, 2);
	sum_novat = flt(sum_novat, 2);

	let grand_total = flt(net_total + vat + sum_novat, 2);

	let values = {
		custom_net_total: net_total,
		custom_net_total_novat: sum_novat,
		custom_grand_total: grand_total,
		custom_in_words: thai_baht_text(grand_total),
	};
	if (!cint(frm.doc.custom_vat_override) || frm.doc.material_request_type === CUSTOMER_PROVIDED) {
		values.custom_vat = vat;
	}

	apply_values(frm, values, direct);
}

function update_thai_baht_text(frm) {
	let text = thai_baht_text(frm.doc.custom_grand_total);
	if (frm.doc.custom_in_words !== text) {
		frm.set_value("custom_in_words", text);
	}
}

// ตั้งค่าเฉพาะ field ที่เปลี่ยนจริง เพื่อไม่ให้ฟอร์ม dirty โดยไม่จำเป็น
function apply_values(frm, values, direct) {
	let changed = {};
	Object.keys(values).forEach((f) => {
		if (frm.doc[f] !== values[f]) changed[f] = values[f];
	});
	if (!Object.keys(changed).length) return;

	if (direct) {
		Object.assign(frm.doc, changed);
		Object.keys(changed).forEach((f) => frm.refresh_field(f));
	} else {
		frm.set_value(changed);
	}
}

// ---------- แปลงตัวเลขเป็นคำอ่านภาษาไทย ----------

function thai_baht_text(number) {
	number = flt(number);
	let negative = number < 0;
	// ปัดเป็นสตางค์ด้วยจำนวนเต็ม เลี่ยงปัญหาทศนิยม float
	let total_satang = Math.round(Math.abs(number) * 100);
	let baht = Math.floor(total_satang / 100);
	let satang = total_satang % 100;

	if (baht === 0 && satang === 0) return "ศูนย์บาทถ้วน";

	let result = "";
	if (baht > 0) result += read_thai_number(String(baht)) + "บาท";
	result += satang > 0 ? read_thai_number(String(satang)) + "สตางค์" : "ถ้วน";

	return (negative ? "ลบ" : "") + result;
}

// อ่านจำนวนเต็มทุกขนาด (รองรับเกินล้าน เช่น หนึ่งล้านล้าน)
function read_thai_number(str) {
	str = str.replace(/^0+/, "");
	if (!str) return "";

	if (str.length > 6) {
		let head = str.slice(0, -6);
		let tail = str.slice(-6);
		return read_thai_number(head) + "ล้าน" + read_six_digits(tail, true);
	}
	return read_six_digits(str, false);
}

function read_six_digits(str, has_higher) {
	const digits = ["", "หนึ่ง", "สอง", "สาม", "สี่", "ห้า", "หก", "เจ็ด", "แปด", "เก้า"];
	const positions = ["", "สิบ", "ร้อย", "พัน", "หมื่น", "แสน"];

	str = str.replace(/^0+/, "");
	let text = "";
	let len = str.length;

	for (let i = 0; i < len; i++) {
		let d = parseInt(str[i], 10);
		let pos = len - i - 1;
		if (d === 0) continue;

		if (pos === 0 && d === 1 && (len > 1 || has_higher)) {
			text += "เอ็ด"; // 11, 101, 1,000,001
		} else if (pos === 1 && d === 1) {
			text += "สิบ"; // 10–19
		} else if (pos === 1 && d === 2) {
			text += "ยี่สิบ"; // 20–29
		} else {
			text += digits[d] + positions[pos];
		}
	}
	return text;
}

// ---- ย้ายจาก Client Script "Material Request - Stepper" ----

// ---- ตัวช่วย: สร้าง frappe.ui.stepper ----
frappe.ui.stepper =
	frappe.ui.stepper ||
	function ({ steps, current = 0, status = "normal" }) {
		return `
    <div style="display:flex;gap:8px;margin:8px 0 16px">
      ${steps
			.map((step, i) => {
				const done = i < current || (i === current && status === "complete");
				const active = i === current;
				let bg = "var(--gray-300)";
				if (active && status === "error") bg = "var(--red-500)";
				else if (done) bg = "var(--green-500)";
				else if (active) bg = "var(--primary)";

				return `<div style="flex:1;text-align:center">
          <div style="height:6px;border-radius:3px;background:${bg}"></div>
          <div style="font-size:12px;margin-top:6px;${
				active ? "font-weight:600" : "color:var(--text-muted)"
			}">
            ${i + 1}. ${__(step.label)}
          </div>
        </div>`;
			})
			.join("")}
    </div>`;
	};

// ---- ใช้งานในฟอร์ม ----
frappe.ui.form.on("Material Request", {
	refresh(frm) {
		render_stepper(frm);
	},
	after_save(frm) {
		render_stepper(frm);
	},
});

function render_stepper(frm) {
	const cancelled = frm.doc.docstatus === 2;
	let current = frm.doc.docstatus >= 1 ? 2 : frm.is_new() ? 0 : 1;

	const html = frappe.ui.stepper({
		steps: [
			{ label: "Draft" },
			{ label: "Review" },
			{ label: cancelled ? "Cancelled" : "Done" },
		],
		current: current,
		status: cancelled ? "error" : current === 2 ? "complete" : "normal",
	});

	frm.fields_dict.custom_stepper_html.$wrapper.html(html);
}

// ---- วัสดุผู้ว่าจ้างจัดหา (Customer Provided) ----
// ผู้ใช้เลือก Item หลัก ระบบเปลี่ยนเป็น Item คู่ (Customer Provided) ให้ ฝั่ง server ทำซ้ำตอนบันทึก
// (consbiz/employer_supplied.py) เลขที่ใช้ชุด OPO- ไม่มี VAT และพิมพ์เป็นใบสั่งวัสดุถึงผู้ว่าจ้าง

const CUSTOMER_PROVIDED = "Customer Provided";
const EMPLOYER_ITEM_API = "consbiz.employer_supplied.get_employer_item";
const VAT_FIELDS = ["custom_included_vat", "custom_vat", "custom_vat_override", "custom_net_total", "custom_net_total_novat"];

frappe.ui.form.on("Material Request", {
	refresh(frm) {
		wrap_item_query(frm);
		toggle_vat_fields(frm);
	},
	material_request_type(frm) {
		toggle_vat_fields(frm);
		set_series(frm);
		if (is_employer_supplied(frm)) {
			(frm.doc.items || []).forEach((row) => swap_to_employer_item(frm, row));
		}
		calculate_totals(frm);
	},
});

frappe.ui.form.on("Material Request Item", {
	item_code(frm, cdt, cdn) {
		if (is_employer_supplied(frm)) swap_to_employer_item(frm, locals[cdt][cdn]);
	},
});

function is_employer_supplied(frm) {
	return frm.doc.material_request_type === CUSTOMER_PROVIDED;
}

// ช่องเลือก Item ของ ERPNext ไม่กรอง Customer Provided ให้แสดงเฉพาะ Item หลัก (ประเภทอื่นคงตามเดิม)
function wrap_item_query(frm) {
	const field = frm.fields_dict.items.grid.get_field("item_code");
	const original = field.get_query;
	if (!original || original.consbiz) return;
	const query = (doc, cdt, cdn) => {
		const result = original(doc, cdt, cdn) || {};
		if (doc.material_request_type === CUSTOMER_PROVIDED) {
			result.filters = { ...(result.filters || {}), custom_base_item: ["is", "not set"] };
		}
		return result;
	};
	query.consbiz = true;
	field.get_query = query;
}

async function swap_to_employer_item(frm, row) {
	const code = row.item_code;
	if (!code) return;
	const { message } = await frappe.call({ method: EMPLOYER_ITEM_API, args: { item_code: code } });
	// ผู้ใช้เปลี่ยน Item ระหว่างรอ หรือเป็น Item คู่อยู่แล้ว
	if (message && message !== code && row.item_code === code) {
		await frappe.model.set_value(row.doctype, row.name, "item_code", message);
	}
}

function toggle_vat_fields(frm) {
	frm.toggle_display(VAT_FIELDS, !is_employer_supplied(frm));
}

// ผู้ว่าจ้างจัดหาใช้เลขชุด OPO- (เปลี่ยนได้เฉพาะเอกสารใหม่ ฝั่ง server ตั้งซ้ำตอนสร้าง)
function set_series(frm) {
	if (!frm.is_new()) return;
	const options = (frm.get_docfield("naming_series").options || "").split("\n");
	const employer = options.find((s) => s.startsWith("OPO-"));
	if (!employer) return;
	if (is_employer_supplied(frm)) {
		frm.set_value("naming_series", employer);
	} else if (frm.doc.naming_series === employer) {
		frm.set_value("naming_series", options[0]);
	}
}

// ---- WBS ของรายการ (งานย่อยของแผนงานของโครงการ custom_project) ----

frappe.ui.form.on("Material Request", {
	refresh(frm) {
		consbiz.set_wbs_options(frm, frm.doc.custom_project);
	},
	custom_project(frm) {
		consbiz.set_wbs_options(frm, frm.doc.custom_project);
		// ของส่งเข้าคลังของโครงการ
		consbiz.set_project_warehouse(frm, frm.doc.custom_project, ["set_warehouse"]);
	},
});
