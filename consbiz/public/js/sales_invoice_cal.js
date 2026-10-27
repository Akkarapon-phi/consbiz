// Script for DocType: Sales Invoice

// ฟังก์ชันประกาศแบบ Hoisted
function fetch_company_settings(frm) {
    if (!frm.doc.company) return;
    frappe.db.get_value('Company', frm.doc.company, ['abbr', 'custom_wht_receivable', 'custom_retention_receivable', 'cost_center'], (r) => {
        if (r) {
            frm.custom_abbr = r.abbr;
            frm.custom_wht_acc = r.custom_wht_receivable;
            frm.custom_ret_acc = r.custom_retention_receivable;
            frm.custom_company_cc = r.cost_center;
            calculate_paid_amount(frm);
        }
    });
}

function calculate_paid_amount(frm) {
    // --- แก้ไข: ใช้ net_total เป็นฐานคำนวณ เพื่อรองรับกรณี VAT Inclusive ---
    let net_total = flt(frm.doc.net_total);

    let grand_total = flt(frm.doc.grand_total);
    let total_advance = flt(frm.doc.total_advance);
    let rounding_adjustment = flt(frm.doc.rounding_adjustment);

    // ตั้งค่าเริ่มต้น
    let abbr = frm.custom_abbr || "";
    let wht_account = frm.custom_wht_acc ? frm.custom_wht_acc : `ถูกหัก ณ ที่จ่าย - ${abbr}`;
    let ret_account = frm.custom_ret_acc ? frm.custom_ret_acc : `เงินประกันผลงาน - ${abbr}`;

    let wht_cost_center = frm.custom_company_cc;
    let ret_cost_center = frm.doc.cost_center ? frm.doc.cost_center : wht_cost_center;

    // 1. คำนวณยอดหัก (จากยอด net_total)
    let wht_amt_local = 0;
    if (frm.doc.custom_subject_to_wht && flt(frm.doc.custom_wht_percent) > 0) {
        wht_amt_local = flt((net_total * flt(frm.doc.custom_wht_percent) / 100), 2);
    }

    let ret_amt_local = 0;
    if (frm.doc.custom_subject_to_retention && flt(frm.doc.custom_retention_percent) > 0) {
        ret_amt_local = flt((net_total * flt(frm.doc.custom_retention_percent) / 100), 2);
    }

    // เช็คค่าเดิมก่อน set_value เพื่อป้องกัน Loop
    if (flt(frm.doc.custom_wht_amount) !== wht_amt_local) {
        frm.set_value('custom_wht_amount', wht_amt_local);
    }
    if (flt(frm.doc.custom_retention_amount) !== ret_amt_local) {
        frm.set_value('custom_retention_amount', ret_amt_local);
    }

    // 2. Sync ลงตาราง
    if (abbr || (frm.custom_wht_acc && frm.custom_ret_acc)) {
        if (frm.fields_dict['custom_payment_entry_deduction']) {
            let need_refresh_table = false;

            if (wht_amt_local > 0) {
                if (!wht_cost_center) frappe.msgprint(__('กรุณาตั้งค่า Default Cost Center ในหน้า Company'));
                else if (sync_deduction_to_table(frm, wht_account, wht_amt_local, "ภาษีหัก ณ ที่จ่าย", wht_cost_center)) need_refresh_table = true;
            } else {
                if (sync_deduction_to_table(frm, wht_account, 0, "ภาษีหัก ณ ที่จ่าย", null)) need_refresh_table = true;
            }

            if (ret_amt_local > 0) {
                if (!ret_cost_center) frappe.msgprint(__('กรุณาเลือก Cost Center'));
                else if (sync_deduction_to_table(frm, ret_account, ret_amt_local, "เงินประกันผลงาน", ret_cost_center)) need_refresh_table = true;
            } else {
                if (sync_deduction_to_table(frm, ret_account, 0, "เงินประกันผลงาน", null)) need_refresh_table = true;
            }

            if (need_refresh_table) {
                frm.refresh_field('custom_payment_entry_deduction');
            }
        }
    }

    // 3. คำนวณยอดรวมจากตาราง
    let total_deduction_table = 0;
    if (frm.doc.custom_payment_entry_deduction) {
        (frm.doc.custom_payment_entry_deduction || []).forEach(d => {
            total_deduction_table += flt(d.amount);
        });
    }

    if (flt(frm.doc.custom_total_deductions) !== flt(total_deduction_table, 2)) {
        frm.set_value('custom_total_deductions', flt(total_deduction_table, 2));
    }

    // 4. คำนวณยอดสุทธิ
    let paid_amount = grand_total - total_advance - total_deduction_table + rounding_adjustment;
    paid_amount = flt(paid_amount, 2);

    if (flt(frm.doc.custom_net_paid_amount) !== paid_amount) {
        frm.set_value('custom_net_paid_amount', paid_amount);
    }

    // 5. คำอ่านภาษาไทย
    if (typeof thai_baht_text === 'function') {
        update_thai_labels(frm, paid_amount, grand_total);
    }
}

function sync_deduction_to_table(frm, account_name, amount, description, target_cost_center) {
    let table_name = 'custom_payment_entry_deduction';
    if (!frm.doc[table_name]) frm.doc[table_name] = [];

    let existing_rows = frm.doc[table_name].filter(d => d.account === account_name);
    let changed = false;

    if (amount > 0) {
        if (existing_rows.length > 0) {
            let row = existing_rows[0];
            if (flt(row.amount) !== flt(amount, 2)) {
                frappe.model.set_value(row.doctype, row.name, 'amount', flt(amount, 2));
                changed = true;
            }
            if (target_cost_center && row.cost_center !== target_cost_center) {
                frappe.model.set_value(row.doctype, row.name, 'cost_center', target_cost_center);
                changed = true;
            }
        } else {
            if (target_cost_center) {
                let row = frm.add_child(table_name);
                row.account = account_name;
                row.amount = flt(amount, 2);
                row.description = description;
                row.cost_center = target_cost_center;
                changed = true;
            }
        }
    } else {
        if (existing_rows.length > 0) {
            existing_rows.forEach(row => {
                frappe.model.clear_doc(row.doctype, row.name);
            });
            frm.doc[table_name] = frm.doc[table_name].filter(d => d.account !== account_name);
            changed = true;
        }
    }
    return changed;
}

function update_thai_labels(frm, paid_amount, grand_total) {
    let text_paid = paid_amount !== 0 ?
        (paid_amount > 0 ? thai_baht_text(paid_amount) : 'ติดลบ' + thai_baht_text(Math.abs(paid_amount))) : 'ศูนย์บาทถ้วน';

    if (frm.doc.custom_paid_amount_in_words !== text_paid) {
        frm.set_value('custom_paid_amount_in_words', text_paid);
        frm.refresh_field('custom_paid_amount_in_words');
    }

    let text_grand = grand_total !== 0 ?
        (grand_total > 0 ? thai_baht_text(grand_total) : 'ติดลบ' + thai_baht_text(Math.abs(grand_total))) : 'ศูนย์บาทถ้วน';

    if (frm.doc.custom_in_words_th !== text_grand) {
        frm.set_value('custom_in_words_th', text_grand);
        frm.refresh_field('custom_in_words_th');
    }
}

// Function to create Transmittal Entry manually from Sales Invoice
function create_transmittal_entry(frm) {
    frappe.model.with_doctype('Transmittal Entry', function() {
        var doc = frappe.model.get_new_doc('Transmittal Entry');

        // Map Fields
        doc.type = 'รายรับ';
        doc.document_no = frm.doc.name;
        doc.posting_date = frm.doc.posting_date;
        doc.company = frm.doc.company;
        doc.customer = frm.doc.customer;
        doc.project = frm.doc.project;
        doc.subject = `นำส่งเอกสารวางบิล ${frm.doc.name}`;
        
        // Map Checkboxes
        doc.receipt = 1;
        doc.tax = frm.doc.total_taxes_and_charges > 0 ? 1 : 0;
        doc.wht = frm.doc.custom_subject_to_wht ? 1 : 0;
        doc.retention = frm.doc.custom_subject_to_retention ? 1 : 0;

        frappe.set_route('Form', 'Transmittal Entry', doc.name);
    });
}

function create_retention_receivable(frm) {
    frappe.model.with_doctype('Retention Receivable', function () {
        var doc = frappe.model.get_new_doc('Retention Receivable');

        doc.company = frm.doc.company;
        doc.customer = frm.doc.customer;
        doc.posting_date = frm.doc.posting_date;
        doc.due_date = frm.doc.due_date;
        doc.project = frm.doc.project;
        doc.customer_po = frm.doc.po_no;

        var child = frappe.model.add_child(doc, 'Retention Items', 'retention_items');
        child.sales_invoice_no = frm.doc.name;
        child.posting_date = frm.doc.posting_date;
        child.due_date = frm.doc.due_date;
        child.description = "Retention from " + frm.doc.name;
        child.base_amount = frm.doc.net_total;
        child.retention_percent = frm.doc.custom_retention_percent;
        child.amount = frm.doc.custom_retention_amount;

        frappe.set_route('Form', 'Retention Receivable', doc.name);
    });
}

// Main Trigger
frappe.ui.form.on('Sales Invoice', {
    setup: function (frm) {
        if (frm.doc.company) fetch_company_settings(frm);
    },
    company: function (frm) {
        fetch_company_settings(frm);
    },

    custom_subject_to_wht: (frm) => calculate_paid_amount(frm),
    custom_wht_percent: (frm) => calculate_paid_amount(frm),
    custom_subject_to_retention: (frm) => calculate_paid_amount(frm),
    custom_retention_percent: (frm) => calculate_paid_amount(frm),
    total_advance: (frm) => calculate_paid_amount(frm),

    posting_date: function (frm) {
        if (frm.doc.posting_date && frm.doc.payment_terms_template) {
            if (frm.events.payment_terms_template) {
                frm.events.payment_terms_template(frm);
            } else {
                frm.trigger('payment_terms_template');
            }
        }
    },

    payment_terms_template: function (frm) {
        if (!frm.doc.payment_terms_template) {
            frm.clear_table('payment_schedule');
            frm.refresh_field('payment_schedule');
        }
    },

    validate: function (frm) { calculate_paid_amount(frm); },

    refresh: function (frm) {
        calculate_paid_amount(frm);

        // Logic ปุ่ม Create/View Retention
        if (frm.doc.docstatus === 1 && frm.doc.custom_subject_to_retention && frm.doc.custom_retention_amount > 0) {
            frappe.call({
                method: 'consbiz.api.check_retention_exists',
                args: { invoice_name: frm.doc.name },
                callback: function (r) {
                    if (r.message) {
                        frm.add_custom_button(__('View Retention'), function () {
                            frappe.set_route('Form', 'Retention Receivable', r.message);
                        }, __('View'));
                    } else {
                        frm.add_custom_button(__('Retention Receivable'), function () {
                            create_retention_receivable(frm);
                        }, __('Create'));
                    }
                }
            });
        }

            // --- 2. Logic ปุ่ม Transmittal Entry (Create/View) ---
            // สร้างปุ่มเสมอสำหรับ Sales Invoice ที่ Submit แล้ว
            if (frm.doc.docstatus === 1) {
            frappe.call({
                method: 'consbiz.api.check_transmittal_exists',
                args: { document_no: frm.doc.name },
                callback: function (r) {
                    if (r.message) {
                        // ถ้ามีแล้ว -> View
                        frm.add_custom_button(__('Transmittal Entry'), function () {
                            frappe.set_route('Form', 'Transmittal Entry', r.message);
                        }, __('View'));
                    } else {
                        // ถ้ายังไม่มี (หรือถูกลบไป) -> Create
                        frm.add_custom_button(__('Transmittal Entry'), function () {
                            create_transmittal_entry(frm);
                        }, __('Create'));
                    }
                }
            });
        }
    }
});

// ---- ย้ายจาก Client Script "FIx Retention Receivable Grand Total" ----

frappe.ui.form.on('Sales Invoice', {
    on_submit: function(frm) {
        // รอ 1 วินาทีให้ระบบสร้าง Doc ปลายทางเสร็จก่อน
        setTimeout(() => {
            if (frm.doc.custom_retention_amount) {
                // ขั้นตอนที่ 1: ไปหา "ชื่อ" ของ Retention Receivable ก่อน
                frappe.db.get_value('Retention Receivable', 
                    { reference_type: 'Sales Invoice', reference_name: frm.doc.name }, 
                    'name', 
                    (r) => {
                        if (r && r.name) {
                            // ขั้นตอนที่ 2: เมื่อได้ชื่อ (name) แล้ว ค่อยสั่ง set_value
                            frappe.call({
                                method: 'frappe.client.set_value',
                                args: {
                                    doctype: 'Retention Receivable',
                                    name: r.name, // ใส่ชื่อที่หาได้ลงไปตรงนี้ (แก้ Error missing name)
                                    fieldname: 'grand_total',
                                    value: frm.doc.custom_retention_amount
                                },
                                callback: function(res) {
                                    if(!res.exc) {
                                        frappe.show_alert({
                                            message: __('อัปเดตยอด Retention เรียบร้อยแล้ว'),
                                            indicator: 'green'
                                        });
                                    }
                                }
                            });
                        }
                    }
                );
            }
        }, 1500); // เพิ่มดีเลย์นิดหน่อยเพื่อความชัวร์
    }
});

// ---- ย้ายจาก Client Script "Print Sales Invoice" ----

// 1. โหลด Library สำหรับจัดการ PDF (pdf-lib)
if (!window.PDFLib) {
    $.getScript('https://unpkg.com/pdf-lib/dist/pdf-lib.min.js');
}

frappe.ui.form.on('Sales Invoice', {
    refresh: function(frm) {
        frm.add_custom_button(__('Sales Invoice'), function() {
            open_print_multi_dialog(frm, 'Sales Invoice');
        }, __("Print"));

	frm.add_custom_button(__('Receipt/Tax Invoice'), function() {
            open_print_multi_dialog(frm, 'Receipt/Tax Invoice');
        }, __("Print"));

        frm.add_custom_button(__('Receipt Voucher'), function() {
            open_print_multi_dialog(frm, 'Receipt Voucher');
        }, __("Print"));

    }
});

function open_print_multi_dialog(frm, base_format) {
    let d = new frappe.ui.Dialog({
        title: `${base_format}`,
        fields: [
            {
                fieldtype: 'HTML',
                options: `
                    <style>
                        .modal-footer { display: flex !important; justify-content: flex-end !important; }
                        .modal-footer .btn { margin-left: 12px !important; }
                        .stepper-row { display: flex; align-items: center; justify-content: space-between; padding: 18px 0; border-bottom: 1px solid #f0f0f0; }
                        .stepper-control { display: flex; align-items: center; gap: 15px; }
                        .qty-input { width: 45px; text-align: center; border: none; background: transparent; font-weight: bold; font-size: 18px; color: #333; }
                        .btn-stepper { width: 35px; height: 35px; border-radius: 8px; display: flex; align-items: center; justify-content: center; }
                    </style>
                    <div style="padding: 10px 0;">
                        <div class="stepper-row">
                            <div style="font-weight: bold; font-size: 1.1em;">ต้นฉบับ</div>
                            <div class="stepper-control">
                                <button class="btn btn-default btn-xs btn-stepper" onclick="update_qty_val('orig', -1)">-</button>
                                <input type="number" id="qty_orig" value="1" readonly class="qty-input">
                                <button class="btn btn-default btn-xs btn-stepper" onclick="update_qty_val('orig', 1)">+</button>
                            </div>
                        </div>
                        <div class="stepper-row" style="border-bottom: none;">
                            <div style="font-weight: bold; font-size: 1.1em;">สำเนา</div>
                            <div class="stepper-control">
                                <button class="btn btn-default btn-xs btn-stepper" onclick="update_qty_val('copy', -1)">-</button>
                                <input type="number" id="qty_copy" value="1" readonly class="qty-input">
                                <button class="btn btn-default btn-xs btn-stepper" onclick="update_qty_val('copy', 1)">+</button>
                            </div>
                        </div>
                    </div>
                `
            }
        ]
    });

    d.set_primary_action(__('Preview'), async () => {
        const blobUrl = await merge_process(frm, base_format);
        if (blobUrl) show_final_view(frm, blobUrl, 'preview');
        d.hide();
    });

    d.add_custom_action(__('Print'), async () => {
        const blobUrl = await merge_process(frm, base_format);
        if (blobUrl) show_final_view(frm, blobUrl, 'print');
        d.hide();
    });

    d.add_custom_action(__('Download'), async () => {
        const blobUrl = await merge_process(frm, base_format);
        if (blobUrl) show_final_view(frm, blobUrl, 'download');
        d.hide();
    });

    window.update_qty_val = function(id, delta) {
        let input = $(`#qty_${id}`);
        let next = parseInt(input.val()) + delta;
        if (next >= 0) input.val(next);
    };

    d.show();
}

async function merge_process(frm, base_format) {
    if (!window.PDFLib) { 
        frappe.msgprint("กำลังเตรียมระบบ PDF..."); 
        return null; 
    }
    frappe.show_alert({message: __('กำลังรวมไฟล์...'), indicator: 'blue'});

    try {
        const { PDFDocument } = PDFLib;
        const combinedPdf = await PDFDocument.create();
        const tasks = [
            { name: base_format, qty: parseInt($('#qty_orig').val()) },
            { name: `${base_format} (Copy)`, qty: parseInt($('#qty_copy').val()) }
        ];

        let has_content = false;
        for (const t of tasks) {
            if (t.qty > 0) {
                let url = `/api/method/frappe.utils.print_format.download_pdf?doctype=${encodeURIComponent(frm.doc.doctype)}&name=${encodeURIComponent(frm.doc.name)}&format=${encodeURIComponent(t.name)}&no_letterhead=0&_lang=th`;
                const resp = await fetch(url);
                if (!resp.ok) continue;
                const donorPdf = await PDFDocument.load(await resp.arrayBuffer());
                for (let i = 0; i < t.qty; i++) {
                    const pages = await combinedPdf.copyPages(donorPdf, donorPdf.getPageIndices());
                    pages.forEach(p => combinedPdf.addPage(p));
                    has_content = true;
                }
            }
        }
        if (!has_content) return null;
        const bytes = await combinedPdf.save();
        return URL.createObjectURL(new Blob([bytes], { type: 'application/pdf' }));
    } catch (e) {
        console.error(e);
        return null;
    }
}

function show_final_view(frm, blobUrl, mode) {
    const is_mobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);

    if (is_mobile) {
        // มือถือ: ใช้เทคนิคสร้างลิงก์หลอกเพื่อเลี่ยง Pop-up Blocker
        const a = document.createElement('a');
        a.href = blobUrl;
        a.target = '_blank';
        // ถ้าเป็น iOS บางเวอร์ชันต้องการให้ต่อเข้ากับ DOM ก่อนคลิก
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        return;
    }

    // Desktop
    if (mode === 'download') {
        const a = document.createElement('a');
        a.href = blobUrl;
        a.download = `${frm.doc.name}.pdf`;
        a.click();
    } else if (mode === 'print') {
        const f = document.createElement('iframe');
        f.style.display = 'none';
        f.src = blobUrl;
        document.body.appendChild(f);
        f.onload = () => { f.contentWindow.focus(); f.contentWindow.print(); };
    } else {
        let d = new frappe.ui.Dialog({ title: __('PDF Preview'), size: 'large' });
        $(d.body).html(`<div style="height: 75vh;"><iframe src="${blobUrl}#view=FitH" width="100%" height="100%" style="border: none;"></iframe></div>`);
        d.add_custom_action(__('Download'), () => { 
            const a = document.createElement('a'); a.href = blobUrl; a.download = `${frm.doc.name}.pdf`; a.click(); 
        });
        d.set_primary_action(__('Print'), () => { 
            d.$body.find('iframe')[0].contentWindow.print(); 
        });
        d.show();
    }
}

// ---- ย้ายจาก Client Script "Sales Invoice Edit WHT-Rentention" ----

// Client Script: Sales Invoice - Manual WHT / Retention Override
// DocType: Sales Invoice | Apply To: Form
//
// สคริปต์เสริมชั่วคราว — ไม่แก้สคริปต์เดิมใน custom app
//
// หลักการ:
// สคริปต์เดิมเรียก calculate_paid_amount() ทุกครั้งที่ validate / refresh
// แล้วเขียนค่าคำนวณทับ ค่าที่แก้เองจึงหายตอนกด Save
// สคริปต์นี้ "กัน" การเขียนทับ 2 จุด เมื่อติ๊ก custom_edit_wht / custom_edit_retention
//   1) frm.set_value('custom_wht_amount' | 'custom_retention_amount')  -> ไม่ให้ทับ
//   2) frappe.model.set_value(แถวในตาราง, 'amount')                     -> บังคับให้เท่ายอดที่กรอกเอง
// ส่วนยอดรวมหัก / ยอดสุทธิ / คำอ่านภาษาไทย ยังให้สคริปต์เดิมคำนวณจากตารางตามปกติ

(function () {
    const DOCTYPE = 'Sales Invoice';
    const TABLE = 'custom_payment_entry_deduction';

    // event ของสคริปต์เดิมที่เรียก calculate_paid_amount()
    // ใช้สั่งให้สคริปต์เดิมคำนวณยอดรวมใหม่ หลังยอดในตารางเปลี่ยน
    const RECALC_EVENT = 'custom_wht_percent';

    const OVERRIDES = [
        {
            edit: 'custom_edit_wht',
            subject: 'custom_subject_to_wht',
            percent: 'custom_wht_percent',
            amount: 'custom_wht_amount',
            // ต้องหาชื่อบัญชีแบบเดียวกับสคริปต์เดิม
            account: (frm) => frm.custom_wht_acc || `ถูกหัก ณ ที่จ่าย - ${frm.custom_abbr || ''}`,
        },
        {
            edit: 'custom_edit_retention',
            subject: 'custom_subject_to_retention',
            percent: 'custom_retention_percent',
            amount: 'custom_retention_amount',
            account: (frm) => frm.custom_ret_acc || `เงินประกันผลงาน - ${frm.custom_abbr || ''}`,
        },
    ];

    function calculated_amount(frm, o) {
        return flt(flt(frm.doc.net_total) * flt(frm.doc[o.percent]) / 100, 2);
    }

    // คืนยอดที่กรอกเอง (> 0) ถ้าโหมดแก้ไขเองทำงานอยู่ / คืน 0 ถ้าให้ใช้ค่าคำนวณตามปกติ
    function get_manual_amount(frm, o) {
        if (!frm.doc[o.edit] || !frm.doc[o.subject]) return 0;
        // ถ้าค่าคำนวณ <= 0 สคริปต์เดิมจะลบแถวในตารางทิ้ง จึงไม่ override
        if (calculated_amount(frm, o) <= 0) return 0;
        const manual = flt(frm.doc[o.amount], 2);
        // ถ้ายังไม่ได้กรอก (0) ปล่อยให้สคริปต์เดิมใส่ค่าคำนวณเป็นค่าเริ่มต้น
        return manual > 0 ? manual : 0;
    }

    // --- จุดกันที่ 1: ยอดที่หัวเอกสาร ---
    function install_form_guard(frm) {
        if (frm.__manual_deduction_guard) return;
        frm.__manual_deduction_guard = true;

        const set_value = frm.set_value;
        frm.set_value = function (field, ...args) {
            if (typeof field === 'string') {
                const o = OVERRIDES.find((x) => x.amount === field);
                if (o && get_manual_amount(frm, o) > 0) {
                    return Promise.resolve(); // ไม่ให้ค่าคำนวณทับค่าที่กรอกเอง
                }
            }
            return set_value.call(frm, field, ...args);
        };
    }

    // --- จุดกันที่ 2: ยอด amount ของแถวในตาราง ---
    function install_model_guard() {
        if (frappe.model.__manual_deduction_guard) return;
        frappe.model.__manual_deduction_guard = true;

        const set_value = frappe.model.set_value;
        frappe.model.set_value = function (doctype, docname, fieldname, value, ...rest) {
            if (fieldname === 'amount') {
                try {
                    const row = (locals[doctype] || {})[docname];
                    const frm = window.cur_frm;
                    if (
                        row && row.parenttype === DOCTYPE && row.parentfield === TABLE &&
                        frm && frm.doctype === DOCTYPE && frm.doc.name === row.parent
                    ) {
                        const o = OVERRIDES.find((x) => x.account(frm) === row.account);
                        const manual = o ? get_manual_amount(frm, o) : 0;
                        if (manual > 0) {
                            if (flt(row.amount) === manual) return Promise.resolve();
                            value = manual; // บังคับให้เท่ายอดที่กรอกเองเสมอ
                        }
                    }
                } catch (e) {
                    console.error('Manual deduction override:', e);
                }
            }
            return set_value.call(frappe.model, doctype, docname, fieldname, value, ...rest);
        };
    }

    // เปิด/ปิดการแก้ไขช่องยอดเงินตาม checkbox
    function toggle_editable(frm) {
        OVERRIDES.forEach((o) => {
            if (!frm.fields_dict[o.amount]) return;
            const editable = frm.doc[o.edit] && frm.doc[o.subject];
            frm.set_df_property(o.amount, 'read_only', editable ? 0 : 1);
        });
    }

    // ดันยอดที่กรอกเองลงแถวในตาราง (แถวแรกของบัญชีนั้น เหมือนสคริปต์เดิม)
    function sync_rows(frm) {
        if (frm.doc.docstatus !== 0) return false;
        let changed = false;

        OVERRIDES.forEach((o) => {
            const manual = get_manual_amount(frm, o);
            if (manual <= 0) return;

            const account = o.account(frm);
            const row = (frm.doc[TABLE] || []).find((d) => d.account === account);
            if (row && flt(row.amount) !== manual) {
                frappe.model.set_value(row.doctype, row.name, 'amount', manual);
                changed = true;
            }
        });
        return changed;
    }

    // ให้สคริปต์เดิมคำนวณ ยอดรวมหัก / ยอดสุทธิ / คำอ่าน ใหม่จากตาราง
    function recalculate(frm) {
        return frm.trigger(RECALC_EVENT);
    }

    function apply_manual(frm) {
        if (sync_rows(frm)) return recalculate(frm);
    }

    install_model_guard();

    const handlers = {
        setup(frm) {
            install_form_guard(frm);
        },
        onload(frm) {
            install_form_guard(frm);
        },
        refresh(frm) {
            install_form_guard(frm);
            toggle_editable(frm);
            return apply_manual(frm);
        },
        // ทำงานต่อจาก validate ของสคริปต์เดิม เป็นด่านสุดท้ายก่อนส่งไป Save
        validate(frm) {
            return apply_manual(frm);
        },
    };

    OVERRIDES.forEach((o) => {
        // ติ๊ก/ไม่ติ๊ก "แก้ไขเอง": ถ้าเอาติ๊กออก ยอดจะกลับเป็นค่าคำนวณ
        handlers[o.edit] = (frm) => {
            toggle_editable(frm);
            return recalculate(frm);
        };
        handlers[o.subject] = (frm) => toggle_editable(frm);
        // แก้ยอดที่หัวเอกสาร -> อัปเดตแถวในตาราง + ยอดรวม
        handlers[o.amount] = (frm) => {
            if (sync_rows(frm)) return recalculate(frm);
            // ลบยอดจนเป็น 0 ขณะติ๊กแก้ไขเอง = กลับไปใช้ค่าคำนวณทันที
            if (frm.doc.docstatus === 0 && frm.doc[o.edit] && flt(frm.doc[o.amount]) <= 0) {
                return recalculate(frm);
            }
        };
    });

    frappe.ui.form.on(DOCTYPE, handlers);
})();
