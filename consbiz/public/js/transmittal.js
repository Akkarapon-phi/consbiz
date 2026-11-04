// ใบนำส่งเอกสาร (DocType Transmittal) ในฟอร์มเอกสารต้นทาง
// - ปุ่ม Create > ใบนำส่งเอกสาร (เอกสารนี้เป็นแถวแรก)
// - แถบแจ้งว่าเอกสารนี้อยู่ในใบนำส่งใบไหน ส่งให้ใคร สถานะอะไร
// รายชื่อต้องตรงกับ SOURCES ใน consbiz/consbiz/doctype/transmittal/transmittal.py

frappe.provide("consbiz.transmittal");

consbiz.transmittal.SOURCE_DOCTYPES = [
	"Sales Tax Invoice",
	"Purchase Tax Invoice",
	"Withholding Tax Cert",
	"Sales Invoice",
	"Purchase Invoice",
	"Retention Invoice",
];

consbiz.transmittal.STATUS_COLORS = {
	Draft: "gray",
	"To Send": "orange",
	Sent: "blue",
	Received: "green",
};

consbiz.transmittal.create = function (frm) {
	frappe
		.xcall("consbiz.consbiz.doctype.transmittal.transmittal.get_reference_details", {
			reference_doctype: frm.doctype,
			reference_name: frm.doc.name,
		})
		.then((row) => {
			frappe.model.with_doctype("Transmittal", () => {
				const doc = frappe.model.get_new_doc("Transmittal");
				doc.company = frm.doc.company;
				if (frm.doc.project) doc.project = frm.doc.project;
				doc.title = __("Documents for {0}", [row.description || frm.doc.name]);
				const child = frappe.model.add_child(doc, "Transmittal List", "transmittal_list");
				Object.assign(child, row);
				frappe.set_route("Form", "Transmittal", doc.name);
			});
		});
};

consbiz.transmittal.show_status = function (frm) {
	frappe
		.xcall("consbiz.consbiz.doctype.transmittal.transmittal.get_transmittals_for", {
			reference_doctype: frm.doctype,
			reference_name: frm.doc.name,
		})
		.then((rows) => {
			if (!rows || !rows.length) return;
			const parts = rows.map((r) => {
				const color = consbiz.transmittal.STATUS_COLORS[r.status] || "gray";
				const to = frappe.utils.escape_html(r.recipient_name || __(r.recipient_type));
				const date = r.received_date || r.sent_date;
				return `<a href="/app/transmittal/${encodeURIComponent(r.name)}">${r.name}</a>
					${__("to")} ${to}
					<span class="indicator-pill ${color}">${__(r.status)}</span>
					${date ? frappe.datetime.str_to_user(date) : ""}`;
			});
			frm.dashboard.set_headline(
				`${__("Transmittal")}: ${parts.join(" &nbsp;·&nbsp; ")}`,
				"blue"
			);
		});
};

consbiz.transmittal.SOURCE_DOCTYPES.forEach((doctype) => {
	frappe.ui.form.on(doctype, {
		refresh(frm) {
			if (frm.doc.docstatus !== 1 || !frappe.model.can_create("Transmittal")) return;
			frm.add_custom_button(
				__("Transmittal"),
				() => consbiz.transmittal.create(frm),
				__("Create")
			);
			consbiz.transmittal.show_status(frm);
		},
	});
});
