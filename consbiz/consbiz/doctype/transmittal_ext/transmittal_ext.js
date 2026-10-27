// Copyright (c) 2026, Siricons and contributors
// For license information, please see license.txt

// ---- ย้ายจาก Client Script "Transmittal Ext Update Sent Date" ----

frappe.ui.form.on("Transmittal Ext", {
	refresh: function (frm) {
		// ดักจับหลังจากที่เอกสารโหลดเสร็จ หรือ Workflow บันทึกเปลี่ยนสถานะเสร็จเรียบร้อยแล้ว

		// เคสที่ 1: ถ้าสถานะเปลี่ยนเป็น Sent และในช่องยังไม่มีวันที่ ให้ใส่และเซฟทันที
		if (frm.doc.workflow_state === "Sent" && !frm.doc.sent_date) {
			frm.set_value("sent_date", frappe.datetime.get_today());
			frm.save(); // สั่งบันทึกค่าลงฐานข้อมูลให้ถาวรเลย
		}

		// เคสที่ 2: ถ้าสถานะถูกดึงกลับเป็น Unsent แต่ยังมีวันที่ค้างอยู่ ให้ลบออกและเซฟ
		else if (frm.doc.workflow_state === "Unsent" && frm.doc.sent_date) {
			frm.set_value("sent_date", "");
			frm.save(); // สั่งบันทึกเพื่อเคลียร์ค่าในฐานข้อมูล
		}
	},
});

// ---- ย้ายจาก Client Script "Transmittal Ext Arrange" ----

frappe.ui.form.on("Transmittal Ext", {
	refresh: function (frm) {
		// เพิ่มปุ่ม Arrange ในหน้า Form
		frm.add_custom_button(__("Arrange"), function () {
			// ตรวจสอบว่ามีข้อมูลในตาราง transmittal_list หรือไม่
			if (frm.doc.transmittal_list && frm.doc.transmittal_list.length > 0) {
				// จัดเรียงข้อมูลตาม document_no (เรียงจากน้อยไปมาก A-Z, 0-9)
				frm.doc.transmittal_list.sort(function (a, b) {
					let valA = (a.document_no || "").toString().toLowerCase();
					let valB = (b.document_no || "").toString().toLowerCase();

					if (valA < valB) return -1;
					if (valA > valB) return 1;
					return 0;
				});

				// อัปเดตลำดับ (idx) ของแถวใหม่เพื่อให้แสดงผลถูกต้อง
				frm.doc.transmittal_list.forEach((row, index) => {
					row.idx = index + 1;
				});

				// สั่งให้ตารางรีเฟรชการแสดงผลบนหน้าจอ
				frm.refresh_field("transmittal_list");

				// แจ้งเตือนผู้ใช้เบาๆ
				frappe.show_alert({
					message: __("จัดเรียงข้อมูลตาม Document No. เรียบร้อยแล้ว"),
					indicator: "green",
				});
			} else {
				frappe.msgprint(__("ไม่พบข้อมูลในตาราง Transmittal List"));
			}
		});
	},
});

// ---- ย้ายจาก Client Script "Transmittal Ext Import" ----

frappe.ui.form.on("Transmittal Ext", {
	refresh: function (frm) {
		// เพิ่มปุ่ม Download Template ในกลุ่มเมนู Import
		frm.add_custom_button(
			__("Download Template"),
			function () {
				download_excel_template();
			},
			__("Import")
		);

		// เพิ่มปุ่ม Import Excel ในกลุ่มเมนู Import
		frm.add_custom_button(
			__("Import Excel"),
			function () {
				upload_and_import_excel(frm);
			},
			__("Import")
		);
	},
});

// โหลด XLSX Library จาก CDN ถ้าในระบบยังไม่มี
function load_xlsx_lib(callback) {
	if (typeof XLSX === "undefined") {
		frappe.require("https://cdn.jsdelivr.net/npm/xlsx@0.18.5/dist/xlsx.full.min.js", callback);
	} else {
		callback();
	}
}

// -------------------------------------------------------------------------
// 1. ฟังก์ชันสร้างและดาวน์โหลดไฟล์ Excel Template
// -------------------------------------------------------------------------
function download_excel_template() {
	load_xlsx_lib(function () {
		// กำหนด Header คอลัมน์ และข้อมูลตัวอย่าง (1-2 แถว)
		const templateData = [
			{
				Date: "2026-07-27",
				"Document No.": "DOC-2026-001",
				Description: "ตัวอย่างรายการเอกสาร 1",
				Amount: 100,
				Unit: "ลบ.ม.",
				Remark: "หมายเหตุ (ถ้ามี)",
			},
			{
				Date: "2026-07-28",
				"Document No.": "DOC-2026-002",
				Description: "ชื่อเรื่องเอกสาร 2",
				Amount: 5,
				Unit: "ฉบับ",
				Remark: "",
			},
		];

		// สร้าง Worksheet และ Workbook
		const worksheet = XLSX.utils.json_to_sheet(templateData);

		// กำหนดความกว้างคอลัมน์ให้อ่านง่าย
		worksheet["!cols"] = [
			{ wch: 12 }, // Date
			{ wch: 18 }, // Document No.
			{ wch: 35 }, // Description
			{ wch: 10 }, // Amount
			{ wch: 10 }, // Unit
			{ wch: 20 }, // Remark
		];

		const workbook = XLSX.utils.book_new();
		XLSX.utils.book_append_sheet(workbook, worksheet, "Transmittal List");

		// ส่งออกไฟล์ .xlsx
		XLSX.writeFile(workbook, "Transmittal_List_Template.xlsx");
	});
}

// -------------------------------------------------------------------------
// 2. ฟังก์ชันอัปโหลดไฟล์ Excel และตรวจสอบ Sheet
// -------------------------------------------------------------------------
function upload_and_import_excel(frm) {
	load_xlsx_lib(function () {
		let input = document.createElement("input");
		input.type = "file";
		input.accept = ".xlsx, .xls, .csv";

		input.onchange = function (e) {
			let file = e.target.files[0];
			if (!file) return;

			let reader = new FileReader();
			reader.onload = function (e) {
				let data = new Uint8Array(e.target.result);
				let workbook = XLSX.read(data, { type: "array" });

				let sheetNames = workbook.SheetNames;

				if (!sheetNames || sheetNames.length === 0) {
					frappe.msgprint(__("ไม่พบ Sheet ในไฟล์ Excel นี้"));
					return;
				}

				// กรณีมี Sheet เดียว ให้ประมวลผลทันที
				if (sheetNames.length === 1) {
					process_sheet_data(frm, workbook, sheetNames[0]);
					return;
				}

				// กรณีมีหลาย Sheet: เปิด Pop-up แสดง Dropdown ชื่อ Sheet ให้ผู้ใช้เลือก
				let dialog = new frappe.ui.Dialog({
					title: __("เลือก Sheet ที่ต้องการ Import"),
					fields: [
						{
							label: __("ชื่อ Sheet"),
							fieldname: "selected_sheet",
							fieldtype: "Select",
							options: sheetNames,
							default: sheetNames[0],
							reqd: 1,
						},
					],
					primary_action_label: __("Import Data"),
					primary_action(values) {
						dialog.hide();
						process_sheet_data(frm, workbook, values.selected_sheet);
					},
				});

				dialog.show();
			};

			reader.readAsArrayBuffer(file);
		};

		input.click();
	});
}

// -------------------------------------------------------------------------
// 3. ฟังก์ชันแปลงข้อมูลใน Sheet ที่เลือกเข้า Child Table
// -------------------------------------------------------------------------
function process_sheet_data(frm, workbook, sheetName) {
	let worksheet = workbook.Sheets[sheetName];
	let jsonData = XLSX.utils.sheet_to_json(worksheet, { defval: "" });

	if (jsonData.length === 0) {
		frappe.msgprint(__("ไม่พบข้อมูลใน Sheet: {0}", [sheetName]));
		return;
	}

	// หากต้องการล้างข้อมูลเดิมในตารางก่อน ให้เปิดใช้งานบรรทัดล่างนี้ (ปลดคอมเมนต์)
	// frm.clear_table('transmittal_list');

	// นำข้อมูล Map เข้า Child Table (transmittal_list)
	jsonData.forEach((row) => {
		let child = frm.add_child("transmittal_list");

		child.date = parse_excel_date(row["Date"] || row["date"]);
		child.document_no = row["Document No."] || row["document_no"] || "";
		child.description = row["Description"] || row["description"] || "";
		child.amount = parseFloat(row["Amount"]) || 0;
		child.unit = row["Unit"] || row["unit"] || "";
		child.remark = row["Remark"] || row["remark"] || "";
	});

	// รีเฟรชตารางเพื่อให้ข้อมูลแสดงขึ้นหน้าจอ
	frm.refresh_field("transmittal_list");
	frappe.show_alert({
		message: __('นำเข้าข้อมูลจาก Sheet "{0}" เรียบร้อยแล้ว', [sheetName]),
		indicator: "green",
	});
}

// -------------------------------------------------------------------------
// 4. ฟังก์ชันจัดการรูปแบบวันที่ (Date Parser)
// -------------------------------------------------------------------------
function parse_excel_date(dateVal) {
	if (!dateVal) return "";

	// กรณี Excel ส่งมาเป็น Serial Number (ตัวเลข เช่น 45123)
	if (typeof dateVal === "number") {
		let date = new Date(Math.round((dateVal - 25569) * 86400 * 1000));
		return date.toISOString().split("T")[0];
	}

	// กรณีส่งมาเป็น String หรือ Date Object
	let parsedDate = new Date(dateVal);
	if (!isNaN(parsedDate.getTime())) {
		return parsedDate.toISOString().split("T")[0];
	}

	return dateVal;
}
