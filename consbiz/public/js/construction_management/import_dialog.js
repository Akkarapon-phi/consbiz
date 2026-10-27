// หน้าต่างนำเข้าแผนงานจาก Excel: ลากไฟล์มาวางหรือคลิกเลือก แล้วส่งเนื้อไฟล์ไปอ่านที่ server (ไม่สร้าง File)
// server คืนค่าที่อ่านได้ทีละแถว (schedule_excel.import_schedule) on_read เป็นคนใส่ค่าลงแผน
const MAX_MB = 10; // ตรงกับ MAX_FILE_SIZE ใน boq_excel.py

export function open_import_dialog(method, schedule, on_read) {
	const dialog = new frappe.ui.Dialog({
		title: __("นำเข้าแผนงานจาก Excel"),
		fields: [
			{
				fieldtype: "HTML",
				options: `<p class="text-muted">${__(
					'ใช้ไฟล์จาก "ส่งออก Excel" ของแผนนี้ ระบบจับคู่งานด้วย WBS แล้วแก้ วันเริ่ม วันจบ จำนวนวัน และงานก่อนหน้า ช่องที่เว้นว่างไม่เปลี่ยน คอลัมน์อื่นไม่ถูกอ่าน ผลยังไม่บันทึกจนกว่าจะกดบันทึก'
				)}</p>`,
			},
			{
				fieldtype: "HTML",
				fieldname: "drop_zone",
				options: `<div class="cs-drop-zone text-center" style="border: 1px dashed var(--gray-400);
					border-radius: var(--border-radius-md); padding: var(--padding-xl); cursor: pointer">
					<div>${__("ลากไฟล์ Excel มาวางที่นี่ หรือคลิกเพื่อเลือกไฟล์")}</div>
					<div class="text-muted small">.xlsx, .csv · ${__("ไม่เกิน {0} MB", [MAX_MB])}</div>
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
		if (file.size > MAX_MB * 1024 * 1024) {
			frappe.msgprint(__("ไฟล์ใหญ่เกิน {0} MB", [MAX_MB]));
			return;
		}
		const reader = new FileReader();
		reader.onload = () => {
			frappe
				.call({
					method,
					// data URL = "data:<type>;base64,<เนื้อไฟล์>"
					args: {
						name: schedule,
						filename: file.name,
						content: reader.result.split(",")[1],
					},
					freeze: true,
					freeze_message: __("กำลังอ่านไฟล์..."),
				})
				.then(({ message }) => {
					dialog.hide();
					on_read(message);
				});
		};
		reader.readAsDataURL(file);
	};

	const $zone = dialog.fields_dict.drop_zone.$wrapper.find(".cs-drop-zone");
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
	$input
		.on("click", (e) => e.stopPropagation())
		.on("change", () => read_file($input[0].files[0]));
	dialog.show();
}
