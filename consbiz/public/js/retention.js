// เงินประกันผลงาน: ปุ่ม/dialog ที่ใช้ร่วมกันใน Retention Receivable / Payable / Invoice / Release และใบแจ้งหนี้
// logic ฝั่ง server อยู่ที่ consbiz/retention.py (ยอดคงเหลือและสถานะคำนวณที่ server เสมอ)

frappe.provide("consbiz.retention");

consbiz.retention.SIDES = {
	"Retention Receivable": {
		claim: "Retention Invoice",
		party: "customer",
		invoice: "Sales Invoice",
		make: "consbiz.retention.make_retention_invoice",
		pay_label: __("Receive Payment"),
	},
	"Retention Payable": {
		claim: "Retention Release",
		party: "supplier",
		invoice: "Purchase Invoice",
		make: "consbiz.retention.make_retention_release",
		pay_label: __("Make Payment"),
	},
};
consbiz.retention.SOURCE_OF_CLAIM = {
	"Retention Invoice": "Retention Receivable",
	"Retention Release": "Retention Payable",
};
consbiz.retention.OPEN_STATUSES = ["Active", "Overdue", "Partly Billed"];

consbiz.retention.set_totals = function (frm) {
	let total = 0;
	(frm.doc.retention_items || []).forEach((row) => (total += flt(row.amount)));
	total = flt(total, 2);
	frm.set_value("grand_total", total);
	if (typeof thai_baht_text === "function") {
		let text = total < 0 ? "ติดลบ" + thai_baht_text(Math.abs(total)) : thai_baht_text(total);
		frm.set_value("in_words", text);
	}
};

// ---------- RR / RP ----------

consbiz.retention.source_refresh = function (frm) {
	const side = consbiz.retention.SIDES[frm.doctype];
	if (frm.doc.docstatus === 0) {
		consbiz.retention.set_totals(frm);
		return;
	}
	if (frm.doc.docstatus === 1 && flt(frm.doc.outstanding_amount) > 0) {
		frm.add_custom_button(
			__(side.claim),
			() => frappe.model.open_mapped_doc({ method: side.make, frm: frm }),
			__("Create")
		);
	}
};

frappe.ui.form.on("Retention Items", {
	base_amount: (frm, cdt, cdn) => consbiz.retention.row_amount(frm, cdt, cdn),
	retention_percent: (frm, cdt, cdn) => consbiz.retention.row_amount(frm, cdt, cdn),
	amount: (frm) => consbiz.retention.set_totals(frm),
	retention_items_remove: (frm) => consbiz.retention.set_totals(frm),
});

consbiz.retention.row_amount = function (frm, cdt, cdn) {
	const row = locals[cdt][cdn];
	if (flt(row.base_amount) && flt(row.retention_percent)) {
		frappe.model.set_value(
			cdt,
			cdn,
			"amount",
			flt((flt(row.base_amount) * flt(row.retention_percent)) / 100, 2)
		);
	}
};

// ---------- RI / Release ----------

consbiz.retention.claim_setup = function (frm) {
	const source = consbiz.retention.SOURCE_OF_CLAIM[frm.doctype];
	const side = consbiz.retention.SIDES[source];
	frm.set_query("retention_reference", "retention_items", () => {
		let filters = {
			docstatus: 1,
			company: frm.doc.company,
			status: ["in", consbiz.retention.OPEN_STATUSES],
		};
		filters[side.party] = frm.doc[side.party];
		if (frm.doc.project) filters.project = frm.doc.project;
		return { filters: filters };
	});
	frm.set_query("account", () => ({
		filters: { company: frm.doc.company, account_type: ["in", ["Bank", "Cash"]], is_group: 0 },
	}));
};

consbiz.retention.claim_refresh = function (frm) {
	const source = consbiz.retention.SOURCE_OF_CLAIM[frm.doctype];
	const side = consbiz.retention.SIDES[source];

	if (frm.doc.docstatus === 0) {
		frm.add_custom_button(
			__(source),
			() => {
				if (!frm.doc.company || !frm.doc[side.party]) {
					frappe.msgprint(__("กรุณาเลือกบริษัทและคู่ค้าก่อน"));
					return;
				}
				consbiz.retention.select_dialog(frm);
			},
			__("Get Items")
		);
	}

	if (frm.doc.journal_entry) {
		frm.add_custom_button(
			__("Journal Entry"),
			() => frappe.set_route("Form", "Journal Entry", frm.doc.journal_entry),
			__("View")
		);
	}

	if (frm.doc.docstatus === 1 && ["Unpaid", "Overdue"].includes(frm.doc.status)) {
		frm.add_custom_button(side.pay_label, () => consbiz.retention.payment(frm)).addClass(
			"btn-primary"
		);
	}
};

frappe.ui.form.on("Retention Claim Item", {
	retention_items_add(frm, cdt, cdn) {
		const source = consbiz.retention.SOURCE_OF_CLAIM[frm.doctype];
		if (source) frappe.model.set_value(cdt, cdn, "retention_doctype", source);
	},
	async retention_reference(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		const source = consbiz.retention.SOURCE_OF_CLAIM[frm.doctype];
		if (!row.retention_reference || !source) return;
		const side = consbiz.retention.SIDES[source];
		const open = await consbiz.retention.get_open(frm, side);
		const found = open.find((r) => r.name === row.retention_reference);
		if (!found) {
			frappe.msgprint(__("{0} ไม่มียอดคงเหลือให้เบิกคืน", [row.retention_reference]));
			frappe.model.set_value(cdt, cdn, "retention_reference", "");
			return;
		}
		consbiz.retention.fill_row(row, found);
		frm.refresh_field("retention_items");
		consbiz.retention.set_totals(frm);
	},
	amount: (frm) => consbiz.retention.set_totals(frm),
	retention_items_remove: (frm) => consbiz.retention.set_totals(frm),
});

consbiz.retention.get_open = async function (frm, side) {
	const r = await frappe.call({
		method: "consbiz.retention.get_open_retentions",
		args: {
			doctype: frm.doctype,
			company: frm.doc.company,
			party: frm.doc[side.party],
			project: frm.doc.project || null,
			exclude: frm.is_new() ? null : frm.doc.name,
		},
	});
	return r.message || [];
};

consbiz.retention.fill_row = function (row, data) {
	row.retention_doctype = consbiz.retention.SOURCE_OF_CLAIM[row.parenttype];
	row.retention_reference = data.name;
	row.invoice_no = data.invoice_no;
	row.posting_date = data.posting_date;
	row.due_date = data.due_date;
	row.retention_amount = data.grand_total;
	row.outstanding_amount = data.remaining;
	row.amount = data.remaining;
};

consbiz.retention.select_dialog = async function (frm) {
	const source = consbiz.retention.SOURCE_OF_CLAIM[frm.doctype];
	const side = consbiz.retention.SIDES[source];
	const in_table = (frm.doc.retention_items || []).map((r) => r.retention_reference);
	const rows = (await consbiz.retention.get_open(frm, side)).filter(
		(r) => !in_table.includes(r.name)
	);
	if (!rows.length) {
		frappe.msgprint(__("ไม่มี {0} ที่ยังเบิกคืนได้", [__(source)]));
		return;
	}

	const esc = frappe.utils.escape_html;
	const body = rows
		.map(
			(r, i) => `<tr>
				<td class="text-center"><input type="checkbox" data-idx="${i}"></td>
				<td><a href="/app/${frappe.router.slug(source)}/${encodeURIComponent(r.name)}" target="_blank">${esc(r.name)}</a></td>
				<td>${esc(r.invoice_no || "")}</td>
				<td>${esc(r.project || "")}</td>
				<td>${r.due_date ? frappe.datetime.str_to_user(r.due_date) : ""}</td>
				<td>${__(r.status)}</td>
				<td class="text-right">${format_currency(r.grand_total)}</td>
				<td class="text-right">${format_currency(r.remaining)}</td>
			</tr>`
		)
		.join("");

	const d = new frappe.ui.Dialog({
		title: __("Select {0}", [__(source)]),
		size: "extra-large",
		fields: [{ fieldname: "table", fieldtype: "HTML" }],
		primary_action_label: __("Add"),
		primary_action() {
			const picked = d.$wrapper
				.find("tbody input:checked")
				.map((_, el) => rows[cint($(el).attr("data-idx"))])
				.get();
			if (!picked.length) return;
			picked.forEach((data) => {
				const row = frm.add_child("retention_items");
				consbiz.retention.fill_row(row, data);
			});
			frm.refresh_field("retention_items");
			consbiz.retention.set_totals(frm);
			d.hide();
		},
	});
	d.fields_dict.table.$wrapper.html(`
		<div class="table-responsive" style="max-height: 60vh">
			<table class="table table-bordered table-hover">
				<thead><tr>
					<th class="text-center"><input type="checkbox" class="select-all"></th>
					<th>${__(source)}</th>
					<th>${__("Invoice No")}</th>
					<th>${__("Project")}</th>
					<th>${__("Return Due Date")}</th>
					<th>${__("Status")}</th>
					<th class="text-right">${__("Retention Amount")}</th>
					<th class="text-right">${__("Outstanding Amount")}</th>
				</tr></thead>
				<tbody>${body}</tbody>
			</table>
		</div>
		<p class="text-muted small">${__("ยอดเบิกเริ่มต้น = ยอดคงเหลือ แก้เป็นยอดบางส่วนได้ในตาราง")}</p>`);
	d.$wrapper.find(".select-all").on("change", function () {
		d.$wrapper.find("tbody input[type=checkbox]").prop("checked", $(this).is(":checked"));
	});
	d.show();
};

consbiz.retention.payment = async function (frm) {
	const source = consbiz.retention.SOURCE_OF_CLAIM[frm.doctype];
	const side = consbiz.retention.SIDES[source];

	if (frm.doc.journal_entry) {
		const status = await frappe.db.get_value("Journal Entry", frm.doc.journal_entry, "docstatus");
		if (cint(status.message && status.message.docstatus) === 0) {
			frappe.set_route("Form", "Journal Entry", frm.doc.journal_entry);
			return;
		}
	}

	const d = new frappe.ui.Dialog({
		title: side.pay_label,
		fields: [
			{
				fieldname: "posting_date",
				fieldtype: "Date",
				label: __("Posting Date"),
				default: frappe.datetime.get_today(),
				reqd: 1,
			},
			{
				fieldname: "mode_of_payment",
				fieldtype: "Link",
				label: __("Mode of Payment"),
				options: "Mode of Payment",
				default: frm.doc.mode_of_payment,
				async onchange() {
					const mop = d.get_value("mode_of_payment");
					if (!mop) return;
					const r = await frappe.call({
						method: "erpnext.accounts.doctype.sales_invoice.sales_invoice.get_bank_cash_account",
						args: { mode_of_payment: mop, company: frm.doc.company },
					});
					if (r.message && r.message.account) d.set_value("account", r.message.account);
				},
			},
			{
				fieldname: "account",
				fieldtype: "Link",
				label: __("Bank / Cash Account"),
				options: "Account",
				default: frm.doc.account,
				reqd: 1,
				get_query: () => ({
					filters: {
						company: frm.doc.company,
						account_type: ["in", ["Bank", "Cash"]],
						is_group: 0,
					},
				}),
			},
			{
				fieldname: "amount",
				fieldtype: "Currency",
				label: __("Amount"),
				default: frm.doc.grand_total,
				read_only: 1,
			},
		],
		primary_action_label: __("Create Journal Entry"),
		async primary_action(values) {
			const r = await frappe.call({
				method: "consbiz.retention.make_journal_entry",
				args: {
					doctype: frm.doctype,
					name: frm.doc.name,
					account: values.account,
					mode_of_payment: values.mode_of_payment || null,
					posting_date: values.posting_date,
				},
				freeze: true,
			});
			d.hide();
			if (r.message) frappe.set_route("Form", "Journal Entry", r.message);
		},
	});
	d.show();
};

// ---------- ปุ่มในใบแจ้งหนี้ (Sales Invoice / Purchase Invoice) ----------

consbiz.retention.invoice_buttons = async function (frm) {
	if (frm.doc.docstatus !== 1) return;
	if (!frm.doc.custom_subject_to_retention || flt(frm.doc.custom_retention_amount) <= 0) return;
	const source = frm.doctype === "Sales Invoice" ? "Retention Receivable" : "Retention Payable";
	const r = await frappe.call({
		method: "consbiz.retention.get_retention_for_invoice",
		args: { doctype: frm.doctype, name: frm.doc.name },
	});
	if (r.message) {
		frm.add_custom_button(
			__(source),
			() => frappe.set_route("Form", source, r.message),
			__("View")
		);
		return;
	}
	// ใบที่ Submit ก่อนระบบสร้างอัตโนมัติ
	frm.add_custom_button(
		__(source),
		async () => {
			const res = await frappe.call({
				method: "consbiz.retention.create_retention_for_invoice",
				args: { doctype: frm.doctype, name: frm.doc.name },
				freeze: true,
			});
			if (res.message) frappe.set_route("Form", source, res.message);
		},
		__("Create")
	);
};
