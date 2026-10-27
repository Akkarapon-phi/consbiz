// Script for DocType: Purchase Order

frappe.ui.form.on('Purchase Order', {
    // Trigger คำนวณเมื่อฟิลด์เงื่อนไขเปลี่ยน
    custom_subject_to_wht: (frm) => calculate_paid_amount(frm),
    custom_wht_percent: (frm) => calculate_paid_amount(frm),
    custom_subject_to_retention: (frm) => calculate_paid_amount(frm),
    custom_retention_percent: (frm) => calculate_paid_amount(frm),
    
    // Trigger เมื่อยอดเงินเปลี่ยน
    net_total: (frm) => calculate_paid_amount(frm),
    grand_total: (frm) => calculate_paid_amount(frm),

    // Trigger เมื่อเปลี่ยนวันที่เอกสาร (transaction_date)
    transaction_date: function(frm) {
        // หากมี Template ให้ Trigger เพื่อคำนวณวันครบกำหนด (Due Date) ในตารางใหม่ตามวันที่เอกสาร
        if (frm.doc.payment_terms_template) {
            frm.trigger('payment_terms_template');
        }
    },

    // Trigger เมื่อ Payment Terms Template เปลี่ยน
    payment_terms_template: function(frm) {
        // ถ้าค่าว่าง (ถูกลบออก) ให้ลบตาราง Payment Schedule ทิ้ง
        if (!frm.doc.payment_terms_template) {
            frm.clear_table('payment_schedule');
            frm.refresh_field('payment_schedule');
        }
    },
    
    refresh: function(frm) {
        calculate_paid_amount(frm);
    },
    validate: function(frm) {
        calculate_paid_amount(frm);
    }
});

var calculate_paid_amount = function(frm) {
    let net_total = flt(frm.doc.net_total);
    let grand_total = flt(frm.doc.grand_total);
    let rounding = flt(frm.doc.rounding_adjustment);
    
    // ตั้งค่าตัวแปร
    let wht_amount = 0;
    let retention_amount = 0;

    // 1. คำนวณ WHT (จากยอดก่อนภาษี) และปัดเศษ 2 ตำแหน่งทันที
    if (frm.doc.custom_subject_to_wht && flt(frm.doc.custom_wht_percent) > 0) {
        wht_amount = flt((net_total * flt(frm.doc.custom_wht_percent) / 100), 2);
    }
    
    // 2. คำนวณ Retention (จากยอดก่อนภาษี) และปัดเศษ 2 ตำแหน่งทันที
    if (frm.doc.custom_subject_to_retention && flt(frm.doc.custom_retention_percent) > 0) {
        retention_amount = flt((net_total * flt(frm.doc.custom_retention_percent) / 100), 2);
    }

    // อัปเดตฟิลด์ยอดหัก (เช็คค่าเดิมก่อน Set เพื่อป้องกัน Loop)
    if (flt(frm.doc.custom_wht_amount) !== wht_amount) {
        frm.set_value('custom_wht_amount', wht_amount);
    }
    if (flt(frm.doc.custom_retention_amount) !== retention_amount) {
        frm.set_value('custom_retention_amount', retention_amount);
    }

    // 3. คำนวณยอดจ่ายสุทธิ
    // สูตร: ยอดรวม - หัก ณ ที่จ่าย - ประกันผลงาน + ปัดเศษ
    let paid_amount = grand_total - wht_amount - retention_amount + rounding;
    paid_amount = flt(paid_amount, 2);

    if (flt(frm.doc.custom_paid_amount) !== paid_amount) {
        frm.set_value('custom_paid_amount', paid_amount);
    }

    // --- ส่วนแสดงคำอ่านภาษาไทย (เรียกใช้ Global Function) ---
    if (typeof thai_baht_text === 'function') {
        update_thai_labels(frm, paid_amount, grand_total);
    }

    // Refresh เฉพาะฟิลด์ที่เกี่ยวข้อง (ลดการกระตุกของหน้าจอ)
    frm.refresh_field('custom_wht_amount');
    frm.refresh_field('custom_retention_amount');
    frm.refresh_field('custom_paid_amount');
};

function update_thai_labels(frm, paid_amount, grand_total) {
    let text_paid = paid_amount !== 0 ? 
        (paid_amount > 0 ? thai_baht_text(paid_amount) : 'ติดลบ' + thai_baht_text(Math.abs(paid_amount))) : 'ศูนย์บาทถ้วน';
    
    // เช็คค่าเดิมก่อน Set
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

// ---- ย้ายจาก Client Script "Print Purchase Order" ----

// 1. โหลด Library สำหรับจัดการ PDF (pdf-lib)
if (!window.PDFLib) {
    $.getScript('https://unpkg.com/pdf-lib/dist/pdf-lib.min.js');
}

frappe.ui.form.on('Purchase Order', {
    refresh: function(frm) {
        frm.add_custom_button(__('Purchase Order'), function() {
            open_print_multi_dialog(frm, 'Purchase Order');
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
