// Copyright (c) 2026, Siricons and contributors
// For license information, please see license.txt

// แผนตัดเหล็ก
// - ปุ่ม "เพิ่มรายการจากรูป" ใต้ตาราง: เลือกรูปทรงจากภาพ กรอกด้าน A-D เห็นความยาวตัดก่อนเพิ่ม
// - ฟอร์มของแต่ละแถวแสดงรูปพร้อมขนาดจริง
// - แผนภาพการตัด (cut_diagram) วาดจากตาราง patterns ที่ server คำนวณตอนบันทึก

const BCP_API = "consbiz.consbiz.doctype.bar_cut_plan.bar_cut_plan";
const BCP_DIMS = ["a", "b", "c", "d"];
const BCP_SETTINGS = [
	"use_bend_deduction",
	"bend_45",
	"bend_90",
	"bend_135",
	"bend_180",
	"hook_135",
	"hook_180",
	"round_up",
];

frappe.ui.form.on("Bar Cut Plan", {
	refresh(frm) {
		const grid = frm.fields_dict.items.grid;
		if (!grid.bcp_button_added) {
			grid.add_custom_button(__("เพิ่มรายการจากรูป"), () => open_add_dialog(frm));
			grid.bcp_button_added = true;
		}
		render_cut_diagram(frm);
	},
});

frappe.ui.form.on("Bar Cut Item", {
	form_render(frm, cdt, cdn) {
		render_row_preview(frm, locals[cdt][cdn]);
	},
	shape: on_row_change,
	a: on_row_change,
	b: on_row_change,
	c: on_row_change,
	d: on_row_change,
});

function on_row_change(frm, cdt, cdn) {
	render_row_preview(frm, locals[cdt][cdn]);
}

// ---------- รูปทรง ----------

let shapes_promise;
function get_shapes() {
	shapes_promise =
		shapes_promise ||
		frappe.db
			.get_list("Bar Shape", {
				fields: ["name", "shape_name", "dimensions", "svg"],
				order_by: "shape_code asc",
				limit: 200,
			})
			.then((shapes) =>
				shapes.map((shape) => ({
					...shape,
					dims: (shape.dimensions || "A").split(",").map((d) => d.trim().toLowerCase()),
				}))
			);
	return shapes_promise;
}

// รูป SVG ที่แทนป้าย A B C D ด้วยค่าจริง เช่น A=1,200
function shape_svg(svg, values = {}) {
	const $wrapper = $("<div>").html(svg || "");
	$wrapper.find("[data-dim]").each(function () {
		const value = values[this.dataset.dim.toLowerCase()];
		if (!value) return;
		this.textContent = `${this.dataset.dim}=${format_number(value, null, 0)}`;
		// ป้ายด้านซ้าย/ขวาของรูปยาวขึ้นเมื่อมีค่า ให้ชิดออกนอกรูปจะได้ไม่ทับเส้น
		const x = Number(this.getAttribute("x"));
		if (x < 40) {
			this.setAttribute("text-anchor", "end");
			this.setAttribute("x", x + 8);
		} else if (x > 120) {
			this.setAttribute("text-anchor", "start");
			this.setAttribute("x", x - 8);
		}
	});
	return $wrapper.html();
}

function render_row_preview(frm, row) {
	const field =
		frm.fields_dict.items.grid.grid_rows_by_docname[row.name]?.grid_form?.fields_dict
			?.shape_preview;
	if (!field) return;
	get_shapes().then((shapes) => {
		const shape = shapes.find((s) => s.name === row.shape);
		field.$wrapper.html(
			shape
				? `<div class="consbiz-shape-preview">${shape_svg(shape.svg, row)}</div>
				   <div class="text-muted small">${__("ด้านที่ต้องกรอก")}: ${shape.dims.join(", ").toUpperCase()}${
						row.cut_length
							? ` · ${__("ความยาวตัด")} <b>${format_number(
									row.cut_length,
									null,
									0
							  )}</b> ${__("มม.")}`
							: ""
				  }</div>`
				: ""
		);
	});
}

// ---------- เพิ่มรายการจากรูป ----------

function open_add_dialog(frm) {
	get_shapes().then((shapes) => {
		if (!shapes.length) {
			frappe.msgprint(__("ยังไม่มีรูปทรง ให้เพิ่มที่ Bar Shape ก่อน"));
			return;
		}
		let selected = shapes[0];
		const last = (frm.doc.items || []).at(-1);

		const dialog = new frappe.ui.Dialog({
			title: __("เพิ่มรายการตัด"),
			size: "extra-large",
			fields: [
				{ fieldname: "gallery", fieldtype: "HTML" },
				{ fieldtype: "Section Break" },
				{ fieldname: "preview", fieldtype: "HTML" },
				{ fieldtype: "Column Break" },
				{ fieldname: "mark", fieldtype: "Data", label: __("เลขเหล็ก / ตำแหน่ง") },
				{
					fieldname: "rebar_type",
					fieldtype: "Link",
					options: "Rebar Type",
					label: __("ประเภทเหล็ก"),
					reqd: 1,
					default: last?.rebar_type,
					change: () => update_preview(),
				},
				{
					fieldname: "qty",
					fieldtype: "Int",
					label: __("จำนวน (ชิ้น)"),
					reqd: 1,
					default: 1,
				},
				{ fieldtype: "Column Break" },
				...BCP_DIMS.map((dim) => ({
					fieldname: dim,
					fieldtype: "Float",
					label: `${dim.toUpperCase()} (${__("มม.")})`,
					change: () => update_preview(),
				})),
			],
			primary_action_label: __("เพิ่ม"),
			primary_action(values) {
				const missing = selected.dims.filter((dim) => !(values[dim] > 0));
				if (missing.length) {
					frappe.msgprint(__("กรอกด้าน {0}", [missing.join(", ").toUpperCase()]));
					return;
				}
				// เอกสารใหม่มีแถวว่างที่ Frappe ใส่ให้ ลบทิ้งก่อนเพิ่ม
				frm.doc.items = (frm.doc.items || []).filter((item) => item.shape);
				frm.doc.items.forEach((item, i) => (item.idx = i + 1));
				const row = frm.add_child("items", {
					mark: values.mark,
					shape: selected.name,
					rebar_type: values.rebar_type,
					qty: values.qty,
					cut_length: dialog.cut_length,
					...Object.fromEntries(selected.dims.map((dim) => [dim, values[dim]])),
				});
				frm.refresh_field("items");
				frm.dirty();
				frappe.show_alert({
					message: __("เพิ่มแถว {0} แล้ว บันทึกเพื่อคำนวณการตัด", [row.idx]),
					indicator: "green",
				});
				// เพิ่มต่อได้ทันที: คงรูปทรงและประเภทเหล็กไว้ ล้างค่าอื่น
				dialog.set_values({ mark: "", qty: 1, a: null, b: null, c: null, d: null });
				dialog.fields_dict.mark.$input.trigger("focus");
			},
			secondary_action_label: __("ปิด"),
			secondary_action() {
				dialog.hide();
			},
		});

		const $gallery = dialog.fields_dict.gallery.$wrapper;
		$gallery.html(
			`<div class="consbiz-shape-gallery">${shapes
				.map(
					(
						shape
					) => `<button type="button" class="consbiz-shape-card" data-shape="${escape_html(
						shape.name
					)}">
						${shape_svg(shape.svg)}
						<span>${escape_html(shape.name)} · ${escape_html(shape.shape_name)}</span>
					</button>`
				)
				.join("")}</div>`
		);
		$gallery.on("click", ".consbiz-shape-card", function () {
			selected = shapes.find((shape) => shape.name === this.dataset.shape);
			select_shape();
		});

		function select_shape() {
			$gallery
				.find(".consbiz-shape-card")
				.each((_, card) =>
					card.classList.toggle("active", card.dataset.shape === selected.name)
				);
			BCP_DIMS.forEach((dim) =>
				dialog.set_df_property(dim, "hidden", !selected.dims.includes(dim))
			);
			update_preview();
		}

		const fetch_length = frappe.utils.debounce(() => {
			const values = dialog.get_values(true);
			const ready = values.rebar_type && selected.dims.every((dim) => values[dim] > 0);
			if (!ready) {
				dialog.cut_length = null;
				render_preview(null);
				return;
			}
			frappe
				.call(`${BCP_API}.preview_cut_length`, {
					shape: selected.name,
					rebar_type: values.rebar_type,
					dimensions: Object.fromEntries(selected.dims.map((dim) => [dim, values[dim]])),
					settings: Object.fromEntries(BCP_SETTINGS.map((key) => [key, frm.doc[key]])),
				})
				.then(({ message }) => {
					dialog.cut_length = message?.cut_length || null;
					render_preview(message);
				});
		}, 300);

		function render_preview(result) {
			const values = dialog.get_values(true);
			const qty = values.qty || 0;
			const info = result
				? `${__("ความยาวตัด")} <b>${format_number(result.cut_length, null, 0)}</b> ${__(
						"มม."
				  )} · ${__("รวม")} ${format_number(
						(result.cut_length * qty) / 1000,
						null,
						2
				  )} ${__("ม.")} · ${format_number(
						((result.cut_length * qty) / 1000) * result.unit_weight,
						null,
						2
				  )} ${__("กก.")}`
				: __("กรอกประเภทเหล็กและด้าน {0} เพื่อดูความยาวตัด", [
						selected.dims.join(", ").toUpperCase(),
				  ]);
			dialog.fields_dict.preview.$wrapper.html(
				`<div class="consbiz-shape-preview">${shape_svg(selected.svg, values)}</div>
				 <div class="text-muted small text-center">${escape_html(selected.shape_name)}</div>
				 <div class="consbiz-cut-length">${info}</div>`
			);
		}

		function update_preview() {
			render_preview(null);
			fetch_length();
		}

		dialog.show();
		select_shape();
	});
}

// ---------- แผนภาพการตัด ----------

function render_cut_diagram(frm) {
	const $wrapper = frm.fields_dict.cut_diagram.$wrapper;
	const patterns = frm.doc.patterns || [];
	if (!patterns.length) {
		$wrapper.html(
			`<div class="text-muted small">${__(
				"เพิ่มรายการตัดแล้วกดบันทึก ระบบจะจัดการตัดให้เหลือเศษน้อยที่สุด"
			)}</div>`
		);
		return;
	}
	const m = (value, decimals = 2) => format_number(value || 0, null, decimals);
	const groups = {};
	patterns.forEach((p) => (groups[p.rebar_type] = groups[p.rebar_type] || []).push(p));

	const html = Object.entries(groups)
		.map(([rebar_type, rows]) => {
			const summary = (frm.doc.summary || []).filter((s) => s.rebar_type === rebar_type);
			const used = summary
				.map((s) => `${m(s.stock_length, 0)} ${__("ม.")} × ${s.bars} ${__("เส้น")}`)
				.join(" + ");
			const bars = rows.map((p) => pattern_bar(p, m)).join("");
			return `<div class="consbiz-cut-group">
				<div class="consbiz-cut-title"><b>${escape_html(rebar_type)}</b>
					<span class="text-muted">${__("ใช้")} ${used}</span></div>
				${bars}
			</div>`;
		})
		.join("");

	$wrapper.html(`
		<div class="consbiz-cut-totals">
			<span>${__("เหล็กที่ใช้")} <b>${m(frm.doc.total_stock_length)}</b> ${__("ม.")}
				(${m(frm.doc.total_weight)} ${__("กก.")})</span>
			<span>${__("ความยาวตัด")} <b>${m(frm.doc.total_required_length)}</b> ${__("ม.")}</span>
			<span><i class="consbiz-cut-swatch reusable"></i>${__("เศษเก็บ")} <b>${m(
		frm.doc.reusable_offcut
	)}</b> ${__("ม.")}</span>
			<span><i class="consbiz-cut-swatch scrap"></i>${__("เศษทิ้ง")} <b>${m(frm.doc.scrap)}</b> ${__(
		"ม."
	)}</span>
			<span>Loss <b>${m(frm.doc.loss_percent)}%</b></span>
		</div>
		${html}
		<div class="text-muted small">${__(
			"ผลคำนวณจากข้อมูลที่บันทึกล่าสุด แก้รายการแล้วกดบันทึกเพื่อคำนวณใหม่"
		)}</div>`);
}

// เหล็ก 1 เส้นของรูปแบบ: ช่องตามความยาวชิ้น แล้วปิดท้ายด้วยเศษ
function pattern_bar(pattern, m) {
	const stock = pattern.stock_length * 1000;
	const pieces =
		typeof pattern.pieces === "string"
			? JSON.parse(pattern.pieces || "[]")
			: pattern.pieces || [];
	const segments = pieces.flatMap((piece) =>
		Array.from({ length: piece.count }, () => {
			const width = (piece.length / stock) * 100;
			const title = `${m(piece.length / 1000, 3)} ${__("ม.")} (${piece.marks.join(", ")})`;
			return `<div class="consbiz-cut-piece" style="width: ${width}%" title="${escape_html(
				title
			)}">
				${width > 7 ? m(piece.length / 1000) : ""}</div>`;
		})
	);
	const offcut_width = (pattern.offcut / pattern.stock_length) * 100;
	const offcut_class = pattern.offcut_type === "Reusable" ? "reusable" : "scrap";
	if (pattern.offcut > 0) {
		segments.push(
			`<div class="consbiz-cut-offcut ${offcut_class}" style="width: ${offcut_width}%"
				title="${__("เศษ")} ${m(pattern.offcut, 3)} ${__("ม.")}">${
				offcut_width > 7 ? m(pattern.offcut) : ""
			}</div>`
		);
	}
	return `<div class="consbiz-cut-row">
		<div class="consbiz-cut-label">${m(pattern.stock_length, 0)} ${__("ม.")} × <b>${
		pattern.bars
	}</b></div>
		<div class="consbiz-cut-bar">${segments.join("")}</div>
	</div>`;
}

function escape_html(value) {
	return frappe.utils.escape_html(String(value ?? ""));
}
