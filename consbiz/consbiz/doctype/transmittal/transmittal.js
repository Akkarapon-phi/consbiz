// Copyright (c) 2026, Siricons and contributors
// For license information, please see license.txt

// ใบนำส่งเอกสาร: ดึงเอกสารในระบบ (transmittal.py: get_documents) หรือพิมพ์/นำเข้า Excel เอง
// สถานะคำนวณจากวันที่ส่ง/วันที่รับที่ server (set_status)

const PARTY_TYPES = { Customer: "Customer", Supplier: "Supplier" };

frappe.ui.form.on("Transmittal", {
	setup(frm) {
		frm.set_query("reference_doctype", "transmittal_list", () => ({
			filters: { istable: 0, issingle: 0, is_submittable: 1 },
		}));
	},

	refresh(frm) {
		const open = frm.doc.docstatus === 0 || (frm.doc.docstatus === 1 && !frm.doc.sent_date);
		if (open) {
			frm.add_custom_button(__("Get Documents"), () => get_documents_dialog(frm));
		}

		if (frm.doc.docstatus === 1) {
			frm.add_custom_button(__("Envelope"), () => consbiz.make_envelope(frm), __("Create"));

			if (!frm.doc.sent_date) {
				frm.add_custom_button(__("Mark as Sent"), () => mark_sent(frm)).addClass(
					"btn-primary"
				);
			} else if (!frm.doc.received_date) {
				frm.add_custom_button(__("Mark as Received"), () => mark_received(frm)).addClass(
					"btn-primary"
				);
				frm.add_custom_button(__("Undo Sent"), () => {
					frm.set_value("sent_date", null);
					frm.save("Update");
				});
			} else {
				frm.add_custom_button(__("Undo Received"), () => {
					frm.set_value({ received_date: null, received_by: null });
					frm.save("Update");
				});
			}
		}

		if (frm.doc.docstatus < 2) {
			frm.add_custom_button(__("Arrange"), () => arrange_rows(frm));
			frm.add_custom_button(__("Download Template"), download_excel_template, __("Import"));
			frm.add_custom_button(
				__("Import Excel"),
				() => upload_and_import_excel(frm),
				__("Import")
			);
		}
	},

	recipient_type(frm) {
		const party_type = PARTY_TYPES[frm.doc.recipient_type] || null;
		if (party_type !== frm.doc.party_type) {
			frm.set_value({ party_type: party_type, party: null, recipient_name: null });
		}
	},

	party(frm) {
		if (!frm.doc.party) return;
		const field = frm.doc.party_type === "Customer" ? "customer_name" : "supplier_name";
		frappe.db.get_value(frm.doc.party_type, frm.doc.party, field).then((r) => {
			frm.set_value("recipient_name", (r.message && r.message[field]) || frm.doc.party);
		});
	},
});

frappe.ui.form.on("Transmittal List", {
	reference_doctype(frm, cdt, cdn) {
		frappe.model.set_value(cdt, cdn, "reference_name", null);
	},

	reference_name(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (!row.reference_doctype || !row.reference_name) return;
		frappe.call({
			method: "consbiz.consbiz.doctype.transmittal.transmittal.get_reference_details",
			args: { reference_doctype: row.reference_doctype, reference_name: row.reference_name },
			callback(r) {
				if (!r.message) return;
				const values = Object.assign({}, r.message);
				delete values.reference_doctype;
				delete values.reference_name;
				frappe.model.set_value(cdt, cdn, values);
			},
		});
	},
});

// -------------------------------------------------------------------------
// ดึงเอกสาร: เลือกประเภท + ช่วงวันที่ แล้วติ๊กเลือกรายการ
// -------------------------------------------------------------------------
function get_documents_dialog(frm) {
	if (!frm.doc.company || !frm.doc.recipient_type) {
		frappe.msgprint(__("Please select Company and Recipient Type first"));
		return;
	}

	frappe
		.xcall("consbiz.consbiz.doctype.transmittal.transmittal.get_source_doctypes")
		.then((sources) => {
			const dialog = new frappe.ui.Dialog({
				title: __("Get Documents"),
				size: "extra-large",
				fields: [
					{
						fieldname: "source",
						fieldtype: "Select",
						label: __("Document Type"),
						options: sources.map((dt) => ({ value: dt, label: __(dt) })),
						default: sources[0],
						reqd: 1,
						onchange: () => load(),
					},
					{
						fieldname: "include_sent",
						fieldtype: "Check",
						label: __("Include documents already sent to this recipient"),
						onchange: () => load(),
					},
					{ fieldtype: "Column Break" },
					{
						fieldname: "from_date",
						fieldtype: "Date",
						label: __("From Date"),
						default: frappe.datetime.month_start(frm.doc.to_date || frm.doc.date),
						onchange: () => load(),
					},
					{
						fieldname: "to_date",
						fieldtype: "Date",
						label: __("To Date"),
						default: frm.doc.to_date || frm.doc.date,
						onchange: () => load(),
					},
					{ fieldtype: "Section Break" },
					{
						fieldname: "docs",
						fieldtype: "Table",
						label: __("Documents"),
						cannot_add_rows: 1,
						cannot_delete_rows: 1,
						in_place_edit: false,
						data: [],
						fields: [
							{
								fieldname: "document_no",
								fieldtype: "Data",
								label: __("Document No."),
								in_list_view: 1,
								read_only: 1,
								columns: 2,
							},
							{
								fieldname: "date",
								fieldtype: "Date",
								label: __("Date"),
								in_list_view: 1,
								read_only: 1,
								columns: 2,
							},
							{
								fieldname: "description",
								fieldtype: "Data",
								label: __("Description"),
								in_list_view: 1,
								read_only: 1,
								columns: 4,
							},
							{
								fieldname: "amount",
								fieldtype: "Currency",
								label: __("Amount"),
								in_list_view: 1,
								read_only: 1,
								columns: 2,
							},
							{ fieldname: "reference_doctype", fieldtype: "Data", hidden: 1 },
							{ fieldname: "reference_name", fieldtype: "Data", hidden: 1 },
						],
					},
				],
				primary_action_label: __("Add Selected"),
				primary_action() {
					const grid = dialog.fields_dict.docs.grid;
					const selected = grid.get_selected_children();
					if (!selected.length) {
						frappe.msgprint(__("Please select at least one document"));
						return;
					}
					add_rows(frm, selected);
					dialog.hide();
				},
			});

			// ไม่ใส่แถวที่อยู่ในใบนี้แล้ว
			const existing = new Set(
				(frm.doc.transmittal_list || [])
					.filter((d) => d.reference_name)
					.map((d) => `${d.reference_doctype}::${d.reference_name}`)
			);

			let token = 0;
			function load() {
				const v = dialog.get_values(true);
				if (!v.source) return;
				const current = ++token;
				frappe
					.xcall("consbiz.consbiz.doctype.transmittal.transmittal.get_documents", {
						source: v.source,
						company: frm.doc.company,
						recipient_type: frm.doc.recipient_type,
						party: frm.doc.party,
						from_date: v.from_date,
						to_date: v.to_date,
						project: frm.doc.project,
						include_sent: v.include_sent ? 1 : 0,
						exclude: frm.is_new() ? null : frm.doc.name,
					})
					.then((rows) => {
						if (current !== token) return;
						const field = dialog.fields_dict.docs;
						field.df.data = rows.filter(
							(r) => !existing.has(`${r.reference_doctype}::${r.reference_name}`)
						);
						field.grid.refresh();
					});
			}

			dialog.show();
			load();
		});
}

function add_rows(frm, rows) {
	rows.forEach((r) => {
		const child = frm.add_child("transmittal_list");
		[
			"reference_doctype",
			"reference_name",
			"document_no",
			"date",
			"description",
			"amount",
		].forEach((f) => (child[f] = r[f]));
	});
	frm.refresh_field("transmittal_list");
	frm.dirty();
	frappe.show_alert({
		message: __("Added {0} documents", [rows.length]),
		indicator: "green",
	});
}

// -------------------------------------------------------------------------
// ส่ง / รับ (ช่อง allow_on_submit บันทึกด้วย Update)
// -------------------------------------------------------------------------
function mark_sent(frm) {
	frappe.prompt(
		[
			{
				fieldname: "sent_date",
				fieldtype: "Date",
				label: __("Sent Date"),
				default: "Today",
				reqd: 1,
			},
		],
		(v) => {
			frm.set_value("sent_date", v.sent_date);
			frm.save("Update");
		},
		__("Mark as Sent"),
		__("Save")
	);
}

function mark_received(frm) {
	frappe.prompt(
		[
			{ fieldname: "received_by", fieldtype: "Data", label: __("Received By") },
			{
				fieldname: "received_date",
				fieldtype: "Date",
				label: __("Received Date"),
				default: "Today",
				reqd: 1,
			},
		],
		(v) => {
			frm.set_value(v);
			frm.save("Update");
		},
		__("Mark as Received"),
		__("Save")
	);
}

// -------------------------------------------------------------------------
// เรียงตามเลขที่เอกสาร
// -------------------------------------------------------------------------
function arrange_rows(frm) {
	const rows = frm.doc.transmittal_list || [];
	if (!rows.length) {
		frappe.msgprint(__("There are no documents to arrange"));
		return;
	}
	rows.sort((a, b) =>
		(a.document_no || "")
			.toString()
			.localeCompare((b.document_no || "").toString(), undefined, {
				numeric: true,
			})
	);
	rows.forEach((row, index) => (row.idx = index + 1));
	frm.refresh_field("transmittal_list");
	frm.dirty();
	frappe.show_alert({ message: __("Sorted by Document No."), indicator: "green" });
}

// -------------------------------------------------------------------------
// Excel: ดาวน์โหลดแม่แบบ / นำเข้า (คอลัมน์ Amount ของแม่แบบเก่า = จำนวน)
// -------------------------------------------------------------------------
function load_xlsx_lib(callback) {
	if (typeof XLSX === "undefined") {
		frappe.require("https://cdn.jsdelivr.net/npm/xlsx@0.18.5/dist/xlsx.full.min.js", callback);
	} else {
		callback();
	}
}

function download_excel_template() {
	load_xlsx_lib(() => {
		const templateData = [
			{
				Date: "2026-07-27",
				"Document No.": "DOC-2026-001",
				Description: "ตัวอย่างรายการเอกสาร 1",
				Qty: 100,
				Unit: "ลบ.ม.",
				Amount: 0,
				Remark: "หมายเหตุ (ถ้ามี)",
			},
			{
				Date: "2026-07-28",
				"Document No.": "DOC-2026-002",
				Description: "ชื่อเรื่องเอกสาร 2",
				Qty: 5,
				Unit: "ฉบับ",
				Amount: 12500,
				Remark: "",
			},
		];
		const worksheet = XLSX.utils.json_to_sheet(templateData);
		worksheet["!cols"] = [
			{ wch: 12 },
			{ wch: 18 },
			{ wch: 35 },
			{ wch: 10 },
			{ wch: 10 },
			{ wch: 12 },
			{ wch: 20 },
		];
		const workbook = XLSX.utils.book_new();
		XLSX.utils.book_append_sheet(workbook, worksheet, "Transmittal List");
		XLSX.writeFile(workbook, "Transmittal_List_Template.xlsx");
	});
}

function upload_and_import_excel(frm) {
	load_xlsx_lib(() => {
		const input = document.createElement("input");
		input.type = "file";
		input.accept = ".xlsx, .xls, .csv";
		input.onchange = (e) => {
			const file = e.target.files[0];
			if (!file) return;
			const reader = new FileReader();
			reader.onload = (ev) => {
				const workbook = XLSX.read(new Uint8Array(ev.target.result), { type: "array" });
				const sheetNames = workbook.SheetNames;
				if (!sheetNames || !sheetNames.length) {
					frappe.msgprint(__("No sheet found in this Excel file"));
					return;
				}
				if (sheetNames.length === 1) {
					process_sheet_data(frm, workbook, sheetNames[0]);
					return;
				}
				frappe.prompt(
					[
						{
							label: __("Sheet"),
							fieldname: "selected_sheet",
							fieldtype: "Select",
							options: sheetNames,
							default: sheetNames[0],
							reqd: 1,
						},
					],
					(v) => process_sheet_data(frm, workbook, v.selected_sheet),
					__("Select Sheet to Import"),
					__("Import")
				);
			};
			reader.readAsArrayBuffer(file);
		};
		input.click();
	});
}

function process_sheet_data(frm, workbook, sheetName) {
	const jsonData = XLSX.utils.sheet_to_json(workbook.Sheets[sheetName], { defval: "" });
	if (!jsonData.length) {
		frappe.msgprint(__("No data found in sheet {0}", [sheetName]));
		return;
	}
	const has_qty = jsonData.some((row) => "Qty" in row || "qty" in row);
	jsonData.forEach((row) => {
		const child = frm.add_child("transmittal_list");
		child.date = parse_excel_date(row["Date"] || row["date"]);
		child.document_no = row["Document No."] || row["document_no"] || "";
		child.description = row["Description"] || row["description"] || "";
		child.unit = row["Unit"] || row["unit"] || "";
		child.remark = row["Remark"] || row["remark"] || "";
		if (has_qty) {
			child.qty = flt(row["Qty"] || row["qty"]);
			child.amount = flt(row["Amount"] || row["amount"]);
		} else {
			child.qty = flt(row["Amount"] || row["amount"]);
		}
	});
	frm.refresh_field("transmittal_list");
	frm.dirty();
	frappe.show_alert({
		message: __("Imported data from sheet {0}", [sheetName]),
		indicator: "green",
	});
}

function parse_excel_date(dateVal) {
	if (!dateVal) return "";
	if (typeof dateVal === "number") {
		const date = new Date(Math.round((dateVal - 25569) * 86400 * 1000));
		return date.toISOString().split("T")[0];
	}
	const parsedDate = new Date(dateVal);
	if (!isNaN(parsedDate.getTime())) {
		return parsedDate.toISOString().split("T")[0];
	}
	return dateVal;
}
