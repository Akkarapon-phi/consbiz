// Script for DocType: Purchase Invoice

// ============================================================
// Helper Functions (Calculations & Settings)
// ============================================================

function fetch_company_settings(frm) {
    if(!frm.doc.company) return;
    frappe.db.get_value('Company', frm.doc.company, ['abbr', 'custom_wht_payable', 'custom_retention_payable', 'cost_center'], (r) => {
        if (r) {
            frm.custom_abbr = r.abbr;
            frm.custom_wht_acc = r.custom_wht_payable;
            frm.custom_ret_acc = r.custom_retention_payable;
            frm.custom_company_cc = r.cost_center;
            calculate_paid_amount(frm); 
        }
    });
}

function calculate_paid_amount(frm) {
    // --- ใช้ net_total เป็นฐานคำนวณ ---
    let net_total = flt(frm.doc.net_total);
    
    let grand_total = flt(frm.doc.grand_total);
    let total_advance = flt(frm.doc.total_advance);
    let rounding_adjustment = flt(frm.doc.rounding_adjustment);
    
    let abbr = frm.custom_abbr || ""; 
    let wht_account = frm.custom_wht_acc ? frm.custom_wht_acc : `ภาษีหัก ณ ที่จ่ายรอจ่าย - ${abbr}`;
    let ret_account = frm.custom_ret_acc ? frm.custom_ret_acc : `เจ้าหนี้เงินประกันผลงาน - ${abbr}`;

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

    if (flt(frm.doc.custom_wht_amount) !== wht_amt_local) {
        frm.set_value('custom_wht_amount', wht_amt_local);
    }
    if (flt(frm.doc.custom_retention_amount) !== ret_amt_local) {
        frm.set_value('custom_retention_amount', ret_amt_local);
    }

    // 2. Sync ลงตาราง Deduction
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

// ============================================================
// Action Functions (Buttons)
// ============================================================

// ฟังก์ชันสร้าง Retention Payable (Manual from Button)
function create_retention_payable(frm) {
    frappe.model.with_doctype('Retention Payable', function() {
        var doc = frappe.model.get_new_doc('Retention Payable');
        
        doc.company = frm.doc.company;
        doc.supplier = frm.doc.supplier;
        doc.project = frm.doc.project;
        doc.posting_date = frm.doc.posting_date;
        
        if (frm.doc.items && frm.doc.items.length > 0) {
            // ดึงค่าจาก column purchase_order ในตาราง items ของ PI
            doc.po = frm.doc.items[0].purchase_order; 
        }

        var row = frappe.model.add_child(doc, 'Retention Items', 'retention_items');
        
        // --- FIXED: ใช้ purchase_invoice_no ให้ตรงกับชื่อฟิลด์ใน Doctype ---
        row.purchase_invoice_no = frm.doc.name; 
        row.reference_no = frm.doc.bill_no;
        row.posting_date = frm.doc.posting_date
        row.description = "Retention from Invoice " + frm.doc.name;
        row.base_amount = frm.doc.net_total; 
        row.retention_percent = frm.doc.custom_retention_percent;
        row.amount = frm.doc.custom_retention_amount;

        frappe.set_route('Form', 'Retention Payable', doc.name);
    });
}

// ฟังก์ชันสร้าง Transmittal Entry (Manual from Button)
function create_transmittal_entry(frm) {
    frappe.model.with_doctype('Transmittal Entry', function() {
        var doc = frappe.model.get_new_doc('Transmittal Entry');

        doc.type = 'รายจ่าย'; // PI เป็นรายจ่าย
        doc.document_no = frm.doc.name;
        doc.posting_date = frm.doc.posting_date;
        doc.company = frm.doc.company;
        doc.supplier = frm.doc.supplier;
        doc.project = frm.doc.project;
        doc.subject = `นำส่งเอกสารเจ้าหนี้ ${frm.doc.name}`;
        
        doc.receipt = 1;
        doc.tax = frm.doc.total_taxes_and_charges > 0 ? 1 : 0;
        doc.wht = frm.doc.custom_subject_to_wht ? 1 : 0;
        doc.retention = frm.doc.custom_subject_to_retention ? 1 : 0;

        frappe.set_route('Form', 'Transmittal Entry', doc.name);
    });
}

// ============================================================
// Main Triggers
// ============================================================

frappe.ui.form.on('Purchase Invoice', {
    setup: function(frm) {
        if (frm.doc.company) fetch_company_settings(frm);
    },
    company: function(frm) {
        fetch_company_settings(frm);
    },
    
    // Triggers for calculation
    custom_subject_to_wht: (frm) => calculate_paid_amount(frm),
    custom_wht_percent: (frm) => calculate_paid_amount(frm),
    custom_subject_to_retention: (frm) => calculate_paid_amount(frm),
    custom_retention_percent: (frm) => calculate_paid_amount(frm),
    total_advance: (frm) => calculate_paid_amount(frm),
    
    posting_date: function(frm) {
        if (frm.doc.posting_date && frm.doc.payment_terms_template) {
            if (frm.events.payment_terms_template) {
                frm.events.payment_terms_template(frm);
            } else {
                frm.trigger('payment_terms_template');
            }
        }
    },

    payment_terms_template: function(frm) {
        if (!frm.doc.payment_terms_template) {
            frm.clear_table('payment_schedule');
            frm.refresh_field('payment_schedule');
        }
    },
    
    validate: function(frm) { calculate_paid_amount(frm); },
    
    refresh: function(frm) { 
        calculate_paid_amount(frm); 

        // --- Logic ปุ่ม Create/View Retention Payable & Transmittal Entry ---
        if (frm.doc.docstatus === 1) {
            
            // 1. Retention Payable Button
            if (frm.doc.custom_subject_to_retention && frm.doc.custom_retention_amount > 0) {
                frappe.call({
                    method: 'consbiz.api.check_retention_payable_exists',
                    args: { invoice_name: frm.doc.name },
                    callback: function (r) {
                        if (r.message) {
                            frm.add_custom_button(__('View Retention'), function () {
                                frappe.set_route('Form', 'Retention Payable', r.message);
                            }, __('View'));
                        } else {
                            frm.add_custom_button(__('Retention Payable'), function () {
                                create_retention_payable(frm);
                            }, __('Create'));
                        }
                    }
                });
            }

            // 2. Transmittal Entry Button
            frappe.call({
                method: 'consbiz.api.check_transmittal_exists',
                args: { document_no: frm.doc.name },
                callback: function (r) {
                    if (r.message) {
                        frm.add_custom_button(__('Transmittal Entry'), function () {
                            frappe.set_route('Form', 'Transmittal Entry', r.message);
                        }, __('View'));
                    } else {
                        frm.add_custom_button(__('Transmittal Entry'), function () {
                            create_transmittal_entry(frm);
                        }, __('Create'));
                    }
                }
            });
        }
    }
});

// ---- ย้ายจาก Client Script "Print Purchase Invoice" ----

// 1. โหลด Library สำหรับจัดการ PDF (pdf-lib)
if (!window.PDFLib) {
    $.getScript('https://unpkg.com/pdf-lib/dist/pdf-lib.min.js');
}

frappe.ui.form.on('Purchase Invoice', {
    refresh: function(frm) {
        frm.add_custom_button(__('Payment Voucher'), function() {
            open_print_multi_dialog(frm, 'Payment Voucher');
        }, __("Print"));

        frm.add_custom_button(__('Substitute Receipt'), function() {
            open_print_multi_dialog(frm, 'Substitute Receipt');
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

// ---- ย้ายจาก Client Script "Purchase Invoice Is Cash" ----

frappe.ui.form.on('Purchase Invoice', {
    custom_is_cash: function(frm) {
        // ดึงค่าปัจจุบันของ custom_is_cash (จะเป็น 1 หรือ 0)
        let is_cash = frm.doc.custom_is_cash;
        
        // เซ็ตค่าให้ is_paid และ update_stock ตามค่า custom_is_cash
        frm.set_value('is_paid', is_cash);
        frm.set_value('update_stock', is_cash);
        
        // (ตัวเลือกเสริม) แจ้งเตือนผู้ใช้เล็กน้อย
        if (is_cash == 1) {
            frappe.show_alert({
                message: __('เปลี่ยนเป็นบิลเงินสดเรียบร้อย'),
                indicator: 'green'
            });
        }
    }
});
