// Copyright (c) 2026, Siricons and contributors
// For license information, please see license.txt

// ---- ย้ายจาก Client Script "Letter In - Approval" ----

// =====================================================================
// Client Script : Letter In  (Apply To: Form)
// Flow: Submit -> เสนออนุมัติ -> พิจารณาอนุมัติ (อนุมัติ / ไม่อนุมัติ)
//       ระหว่างรอ: เปลี่ยนผู้อนุมัติ / ถอนเรื่อง
// =====================================================================

const LI = {
	ROLE: "Approver", // Role ที่เลือกเป็นผู้อนุมัติได้
	F_STATUS: "status",
	F_STEPPER: "stepper_html", // HTML field สำหรับแสดง Stepper
	F_APPROVER: "approver",
	F_DATE: "approve_date",
	F_REMARK: "approve_remark",
	F_PROPOSER: "proposed_by", // (ไม่บังคับ) ถ้ามี field นี้ จะจำกัด เปลี่ยนผู้อนุมัติ/ถอนเรื่อง ให้เฉพาะผู้เสนอ
	S_WAIT: "รอเสนอ",
	S_PROPOSE: "เสนออนุมัติ",
	S_APPROVED: "อนุมัติ",
	S_REJECTED: "ไม่อนุมัติ",
	S_WITHDRAWN: "รอเสนอ", // สถานะหลังถอนเรื่อง
	NOTIFY: true, // แจ้งเตือนผู้อนุมัติผ่าน Assign To
	ICON_SEND: "send",
	ICON_SIGN: "signature",
};

frappe.ui.form.on("Letter In", {
	refresh(frm) {
		li_render_stepper(frm);
		li_setup_buttons(frm);
	},
});

// ---------------------------------------------------------------------
// Stepper : รอเสนอ → เสนออนุมัติ → พิจารณาอนุมัติ (อนุมัติ / ไม่อนุมัติ)
// ---------------------------------------------------------------------
function li_render_stepper(frm) {
	const field = frm.fields_dict[LI.F_STEPPER];
	if (!field) return;
	const $wrap = field.$wrapper.empty();

	// เอกสารที่ยกเลิก (Cancel) ไม่ต้องแสดง Stepper
	if (frm.doc.docstatus === 2) return;

	const status = frm.doc[LI.F_STATUS];
	const is_approved = status === LI.S_APPROVED;
	const is_rejected = status === LI.S_REJECTED;
	const steps = [
		{ label: __("รอเสนอ") },
		{ label: __("เสนออนุมัติ") },
		{
			label: is_approved
				? __("อนุมัติ")
				: is_rejected
				? __("ไม่อนุมัติ")
				: __("พิจารณาอนุมัติ"),
		},
	];

	let current = 0; // รอเสนอ / ร่าง / ว่าง
	if (status === LI.S_PROPOSE) current = 1;
	else if (is_approved || is_rejected) current = steps.length; // ครบทุกขั้น

	li_inject_stepper_css();

	if (frappe.ui.stepper) {
		const result_class = is_rejected
			? "li-stepper--rejected"
			: is_approved
			? "li-stepper--approved"
			: "";
		const $stepper = frappe.ui.stepper({
			steps,
			current,
			label: __("ขั้นตอนการอนุมัติ"),
			css_class: ["li-stepper", result_class].filter(Boolean).join(" "),
		});
		// ไม่อนุมัติ: เปลี่ยนเครื่องหมายขั้นสุดท้ายจาก ✓ เป็น ✕
		if (is_rejected) {
			$stepper
				.find(".es-stepper__step")
				.last()
				.find(".es-stepper__marker")
				.html(frappe.utils.icon("x", "sm", "", "", "", true));
		}
		$wrap.append($stepper);
	} else {
		// Frappe เวอร์ชันที่ยังไม่มี frappe.ui.stepper
		const text = steps
			.map((s, i) =>
				i === Math.min(current, steps.length - 1) ? `<b>${s.label}</b>` : s.label
			)
			.join(" → ");
		$wrap.append(`<div class="li-stepper">${text}</div>`);
	}

	const note = li_stepper_note(frm, status);
	if (note) $wrap.append(`<div class="li-stepper-note text-muted">${note}</div>`);
}

// ข้อความใต้ Stepper: รอใคร / ใครอนุมัติเมื่อไร / เหตุผลที่ไม่อนุมัติ
function li_stepper_note(frm, status) {
	if (frm.doc.docstatus !== 1) return "";
	const esc = frappe.utils.escape_html;
	const approver = frm.doc[LI.F_APPROVER];
	const name = approver ? esc(frappe.user.full_name(approver) || approver) : "";
	const date = frm.doc[LI.F_DATE] ? frappe.datetime.str_to_user(frm.doc[LI.F_DATE]) : "";
	const remark = frm.doc[LI.F_REMARK] ? esc(frm.doc[LI.F_REMARK]) : "";

	if (status === LI.S_PROPOSE && name) {
		return __("รออนุมัติจาก {0}", [`<b>${name}</b>`]);
	}
	if (status === LI.S_APPROVED || status === LI.S_REJECTED) {
		let txt = `${status}${name ? ` ${__("โดย")} <b>${name}</b>` : ""}${
			date ? ` ${__("วันที่")} ${date}` : ""
		}`;
		if (remark) txt += `<br>${__("หมายเหตุ")}: ${remark}`;
		return txt;
	}
	return "";
}

function li_inject_stepper_css() {
	if (document.getElementById("li-stepper-css")) return;
	$("head").append(`<style id="li-stepper-css">
        .li-stepper { margin-bottom: var(--margin-sm, 8px); }
        .li-stepper--rejected .es-stepper__step:last-of-type { color: var(--red-600, #e03636); }
        .li-stepper--rejected .es-stepper__step:last-of-type .es-stepper__marker {
            background: var(--red-500, #e03636); color: #fff;
        }
        .li-stepper--approved .es-stepper__step:last-of-type { color: var(--green-700, #16794c); }
        .li-stepper--approved .es-stepper__step:last-of-type .es-stepper__marker {
            background: var(--green-500, #30a66d); color: #fff;
        }
        .li-stepper-note { font-size: var(--text-sm, 13px); }
    </style>`);
}

// ---------------------------------------------------------------------
// ปุ่มบน header
// ---------------------------------------------------------------------
function li_setup_buttons(frm) {
	if (frm.doc.docstatus !== 1) return;

	const status = frm.doc[LI.F_STATUS];
	const me = frappe.session.user;

	// 1) ยังไม่เสนอ / ถอนเรื่องแล้ว / ไม่อนุมัติ -> เสนออนุมัติ (ใหม่) ได้
	if (![LI.S_PROPOSE, LI.S_APPROVED].includes(status)) {
		const label = __("เสนออนุมัติ");
		const btn = frm.add_custom_button(label, () => li_approver_dialog(frm, "propose"));
		frm.change_custom_button_type(label, null, "primary");
		li_add_icon(btn, LI.ICON_SEND);
		return;
	}

	if (status !== LI.S_PROPOSE) return;

	// 2) ผู้อนุมัติที่ถูกกำหนด -> พิจารณาอนุมัติ + เปลี่ยนผู้อนุมัติ (กรณีไม่ว่าง)
	if (me === frm.doc[LI.F_APPROVER]) {
		const label = __("พิจารณาอนุมัติ");
		const btn = frm.add_custom_button(label, () => li_decision_dialog(frm));
		frm.change_custom_button_type(label, null, "primary");
		li_add_icon(btn, LI.ICON_SIGN);
		frm.add_custom_button(__("เปลี่ยนผู้อนุมัติ"), () => li_approver_dialog(frm, "change"));
		return;
	}

	// 3) ผู้เสนอ / คนอื่น -> ถอนเรื่อง (ปุ่มปกติ)
	if (li_can_manage(frm)) {
		frm.add_custom_button(__("ถอนเรื่อง"), () => li_withdraw(frm));
	}

	// 4) ผู้เสนอ / คนอื่น / Role Approver -> เปลี่ยนผู้อนุมัติ (ปุ่มปกติ)
	if (li_can_manage(frm) || frappe.user.has_role(LI.ROLE)) {
		frm.add_custom_button(__("เปลี่ยนผู้อนุมัติ"), () => li_approver_dialog(frm, "change"));
	}
}

// ถ้ามี field ผู้เสนอ -> เฉพาะผู้เสนอ (และ System Manager) | ถ้าไม่มี -> ทุกคนยกเว้นผู้อนุมัติ
function li_can_manage(frm) {
	const has_proposer_field = !!frappe.meta.get_docfield(frm.doctype, LI.F_PROPOSER);
	if (!has_proposer_field || !frm.doc[LI.F_PROPOSER]) return true;
	return (
		frm.doc[LI.F_PROPOSER] === frappe.session.user || frappe.user.has_role("System Manager")
	);
}

// ---------------------------------------------------------------------
// Dialog เลือกผู้อนุมัติ (เสนอ / เปลี่ยนผู้อนุมัติ)
// ---------------------------------------------------------------------
async function li_approver_dialog(frm, mode) {
	const current = frm.doc[LI.F_APPROVER];
	const is_propose = mode === "propose";

	let approvers = await li_get_approvers();
	if (!is_propose && current) approvers = approvers.filter((a) => a.name !== current);

	if (!approvers.length) {
		frappe.msgprint(__("ไม่พบผู้ใช้ที่มี Role {0}", [LI.ROLE]));
		return;
	}
	const name_map = Object.fromEntries(approvers.map((a) => [a.name, a.full_name || a.name]));

	const d = new frappe.ui.Dialog({
		title: is_propose ? __("เสนออนุมัติ") : __("เปลี่ยนผู้อนุมัติ"),
		fields: [
			...(!is_propose && current
				? [
						{
							fieldname: "current_html",
							fieldtype: "HTML",
							options: `<div class="text-muted mb-3">${__(
								"ผู้อนุมัติปัจจุบัน"
							)}: <b>${frappe.utils.escape_html(
								frappe.user.full_name(current) || current
							)}</b></div>`,
						},
				  ]
				: []),
			{
				fieldname: "approver",
				fieldtype: "Link",
				options: "User",
				label: __("ผู้อนุมัติ"),
				reqd: 1,
				get_query: () => ({ filters: { name: ["in", Object.keys(name_map)] } }),
				onchange: () => {
					const u = d.get_value("approver");
					d.set_value("full_name", u ? name_map[u] || "" : "");
				},
			},
			{
				fieldname: "full_name",
				fieldtype: "Data",
				label: __("ชื่อ-นามสกุล"),
				read_only: 1,
			},
		],
		primary_action_label: is_propose ? __("เสนอ") : __("บันทึก"),
		primary_action: async (values) => {
			const $btn = d.get_primary_btn().prop("disabled", true);
			try {
				const fields = {
					[LI.F_APPROVER]: values.approver,
					[LI.F_STATUS]: LI.S_PROPOSE,
				};
				if (is_propose) {
					// เสนอใหม่ (เช่น หลังไม่อนุมัติ) -> ล้างผลการพิจารณาเดิม
					fields[LI.F_DATE] = null;
					fields[LI.F_REMARK] = "";
					if (frappe.meta.get_docfield(frm.doctype, LI.F_PROPOSER)) {
						fields[LI.F_PROPOSER] = frappe.session.user;
					}
				}
				await li_set_values(frm, fields);

				if (LI.NOTIFY) {
					if (current && current !== values.approver) await li_unassign(frm, current);
					await li_assign(frm, values.approver);
				}

				d.hide();
				frappe.show_alert({
					message: __("เสนออนุมัติไปยัง {0} แล้ว", [
						values.full_name || values.approver,
					]),
					indicator: "green",
				});
				frm.reload_doc();
			} catch (e) {
				$btn.prop("disabled", false);
			}
		},
		secondary_action_label: __("ยกเลิก"),
		secondary_action: () => d.hide(),
	});

	d.show();
	li_normalize_footer(d);
}

// ---------------------------------------------------------------------
// Dialog พิจารณาอนุมัติ : อนุมัติ (primary) | ไม่อนุมัติ (danger) | ยกเลิก
// ---------------------------------------------------------------------
function li_decision_dialog(frm) {
	const d = new frappe.ui.Dialog({
		title: __("พิจารณาอนุมัติ"),
		fields: [
			{
				fieldname: "msg",
				fieldtype: "HTML",
				options: `<p>${__("เอกสาร")} <b>${frappe.utils.escape_html(frm.docname)}</b></p>`,
			},
			{
				fieldname: "approve_date",
				fieldtype: "Date",
				label: __("วันที่"),
				reqd: 1,
				default: frappe.datetime.get_today(),
			},
			{
				fieldname: "remark",
				fieldtype: "Small Text",
				label: __("หมายเหตุ"),
				description: __("จำเป็นต้องระบุเหตุผลเมื่อไม่อนุมัติ"),
			},
		],
		primary_action_label: __("อนุมัติ"),
		primary_action: (values) => li_submit_decision(frm, d, LI.S_APPROVED, values),
		secondary_action_label: __("ยกเลิก"),
		secondary_action: () => d.hide(),
	});

	// ปุ่ม ไม่อนุมัติ (danger) วางไว้ก่อนปุ่ม อนุมัติ
	const $reject = li_danger_btn(__("ไม่อนุมัติ"));
	$reject.on("click", () => {
		const values = d.get_values(); // ตรวจ reqd (วันที่)
		if (!values) return;
		if (!(values.remark || "").trim()) {
			frappe.msgprint({
				message: __("กรุณาระบุหมายเหตุ/เหตุผลที่ไม่อนุมัติ"),
				indicator: "red",
			});
			d.fields_dict.remark.$input && d.fields_dict.remark.$input.focus();
			return;
		}
		li_submit_decision(frm, d, LI.S_REJECTED, values);
	});

	d.show();
	d.get_primary_btn().before($reject);
	li_normalize_footer(d);
}

async function li_submit_decision(frm, d, new_status, values) {
	const $btns = d.$wrapper.find(".modal-footer button").prop("disabled", true);
	try {
		await li_set_values(frm, {
			[LI.F_STATUS]: new_status,
			[LI.F_DATE]: values.approve_date,
			[LI.F_REMARK]: values.remark || "",
		});
		if (LI.NOTIFY) await li_close_assignment(frm, frm.doc[LI.F_APPROVER]);

		d.hide();
		frappe.show_alert({
			message: __("บันทึกผล: {0}", [new_status]),
			indicator: new_status === LI.S_APPROVED ? "green" : "red",
		});
		frm.reload_doc();
	} catch (e) {
		$btns.prop("disabled", false);
	}
}

// ---------------------------------------------------------------------
// ถอนเรื่อง
// ---------------------------------------------------------------------
function li_withdraw(frm) {
	const approver = frm.doc[LI.F_APPROVER];
	frappe.confirm(
		__("ต้องการถอนเรื่องเสนออนุมัติจาก {0} ใช่หรือไม่?", [
			`<b>${frappe.utils.escape_html(
				frappe.user.full_name(approver) || approver || ""
			)}</b>`,
		]),
		async () => {
			await li_set_values(frm, {
				[LI.F_STATUS]: LI.S_WITHDRAWN,
				[LI.F_APPROVER]: "",
			});
			if (LI.NOTIFY && approver) await li_unassign(frm, approver);
			frappe.show_alert({ message: __("ถอนเรื่องแล้ว"), indicator: "orange" });
			frm.reload_doc();
		}
	);
}

// ---------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------
function li_set_values(frm, fields) {
	return frappe.call({
		method: "frappe.client.set_value",
		args: { doctype: frm.doctype, name: frm.docname, fieldname: fields },
		freeze: true,
		freeze_message: __("กำลังบันทึก..."),
	});
}

async function li_get_approvers() {
	const roles = await frappe.db.get_list("Has Role", {
		filters: { role: LI.ROLE, parenttype: "User" },
		fields: ["parent"],
		parent_doctype: "User",
		limit: 0,
	});
	const ids = [...new Set(roles.map((r) => r.parent))].filter(
		(u) => !["Administrator", "Guest"].includes(u)
	);
	if (!ids.length) return [];

	return await frappe.db.get_list("User", {
		filters: { name: ["in", ids], enabled: 1 },
		fields: ["name", "full_name"],
		order_by: "full_name asc",
		limit: 0,
	});
}

function li_assign(frm, user) {
	return frappe
		.call({
			method: "frappe.desk.form.assign_to.add",
			args: {
				doctype: frm.doctype,
				name: frm.docname,
				assign_to: [user],
				description: __("เสนออนุมัติหนังสือรับ {0}", [frm.docname]),
				notify: 1,
			},
		})
		.catch(() => {});
}

function li_unassign(frm, user) {
	return frappe
		.call({
			method: "frappe.desk.form.assign_to.remove",
			args: { doctype: frm.doctype, name: frm.docname, assign_to: user },
		})
		.catch(() => {});
}

function li_close_assignment(frm, user) {
	if (!user) return Promise.resolve();
	return frappe
		.call({
			method: "frappe.desk.form.assign_to.close",
			args: { doctype: frm.doctype, name: frm.docname, assign_to: user },
		})
		.catch(() => li_unassign(frm, user));
}

// Frappe รุ่นใหม่ (v16+) ใช้ปุ่มแบบ es-button | v14/v15 ใช้ .btn แบบเดิม
function li_is_es() {
	return !!(frappe.ui.button && frappe.ui.button.dress);
}

// ปุ่มสีแดง ให้เป็นปุ่มชนิดเดียวกับปุ่มอื่นใน popup ของเวอร์ชันนั้น ๆ
function li_danger_btn(label) {
	if (li_is_es()) {
		return frappe.ui.button({ label, variant: "solid", theme: "red" });
	}
	return $(
		`<button type="button" class="btn btn-danger btn-sm">${frappe.utils.escape_html(
			label
		)}</button>`
	);
}

// ปุ่มใน popup: ไม่มีไอคอน และขนาดเท่ากันทุกปุ่ม (ระยะห่างใช้ CSS ของ Frappe)
function li_normalize_footer(d) {
	d.$wrapper.find(".modal-footer .standard-actions button").each(function () {
		const $b = $(this);
		if (li_is_es()) {
			// ขนาด sm คือค่าเริ่มต้น = ไม่มี data-size (ไม่แตะสีของปุ่ม)
			$b.children("svg").remove();
			$b.removeAttr("data-size");
		} else {
			$b.find("svg, .icon, kbd, .kbd, .li-icon").remove();
			$b.removeClass("btn-xs btn-md btn-lg").addClass("btn-sm");
		}
		$b.css("min-width", "80px");
	});
}

// ไอคอนบนปุ่ม header (ใช้สีตามตัวอักษรของปุ่ม)
function li_add_icon($btn, icon) {
	if (!$btn || !$btn.length) return;
	if (li_is_es()) {
		// ส่งสี/ขนาดเดิมกลับไปด้วย ไม่งั้น dress() จะล้างสีปุ่ม
		frappe.ui.button.dress($btn, {
			label: ($btn.find(".es-button__label").text() || $btn.text()).trim(),
			icon,
			variant: $btn.attr("data-variant") || "subtle",
			theme: $btn.attr("data-theme") || "gray",
			size: $btn.attr("data-size") || "sm",
		});
		return;
	}
	$btn.find(".li-icon").remove();
	$btn.prepend(
		`<span class="li-icon" style="margin-right:4px;display:inline-flex;vertical-align:middle;--icon-stroke:currentColor;">${frappe.utils.icon(
			icon,
			"sm"
		)}</span>`
	);
}
