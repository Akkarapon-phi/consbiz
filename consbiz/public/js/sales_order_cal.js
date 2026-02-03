frappe.ui.form.on('Sales Order', {
    custom_subject_to_wht: (frm) => calculate_paid_amount(frm),
    custom_wht_percent: (frm) => calculate_paid_amount(frm),
    custom_subject_to_retention: (frm) => calculate_paid_amount(frm),
    custom_retention_percent: (frm) => calculate_paid_amount(frm),
    advance_paid: (frm) => calculate_paid_amount(frm),
    net_total: (frm) => calculate_paid_amount(frm),
    grand_total: (frm) => calculate_paid_amount(frm),

    // 1. Trigger เมื่อเปลี่ยนวันที่เอกสาร (transaction_date)
    // เพื่ออัปเดตวันครบกำหนดชำระใน Payment Schedule ให้สัมพันธ์กัน
    transaction_date: function(frm) {
        if (frm.doc.transaction_date && frm.doc.payment_terms_template) {
            // เรียกใช้ Event มาตรฐานของ ERPNext เพื่อคำนวณตารางใหม่ตาม Template และวันที่ใหม่
            if (frm.events.payment_terms_template) {
                frm.events.payment_terms_template(frm);
            } else {
                frm.trigger('payment_terms_template');
            }
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
    let advance_paid = flt(frm.doc.advance_paid);
    
    let wht_amount = 0;
    let retention_amount = 0;

    // 2. แก้เรื่องทศนิยมคำนวน (ปัดเศษ 2 ตำแหน่งทันที)
    if (frm.doc.custom_subject_to_wht && flt(frm.doc.custom_wht_percent) > 0) {
        wht_amount = flt((net_total * flt(frm.doc.custom_wht_percent) / 100), 2);
    }
    
    if (frm.doc.custom_subject_to_retention && flt(frm.doc.custom_retention_percent) > 0) {
        retention_amount = flt((net_total * flt(frm.doc.custom_retention_percent) / 100), 2);
    }

    frm.set_value('custom_wht_amount', wht_amount);
    frm.set_value('custom_retention_amount', retention_amount);

    let paid_amount = grand_total - wht_amount - retention_amount - advance_paid + rounding;
    paid_amount = flt(paid_amount, 2);

    frm.set_value('custom_paid_amount', paid_amount);

    // --- เรียกใช้ Global Function ---
    if (typeof thai_baht_text === 'function') {
        if (paid_amount !== 0) {
            let text = paid_amount > 0 ? thai_baht_text(paid_amount) : 'ติดลบ' + thai_baht_text(Math.abs(paid_amount));
            frm.set_value('custom_paid_amount_in_words', text);
        } else {
            frm.set_value('custom_paid_amount_in_words', 'ศูนย์บาทถ้วน');
        }

        if (grand_total !== 0) {
            let text_grand = grand_total > 0 ? thai_baht_text(grand_total) : 'ติดลบ' + thai_baht_text(Math.abs(grand_total));
            frm.set_value('custom_in_words_th', text_grand);
        } else {
            frm.set_value('custom_in_words_th', 'ศูนย์บาทถ้วน');
        }
    }

    frm.refresh_field('custom_wht_amount');
    frm.refresh_field('custom_retention_amount');
    frm.refresh_field('custom_paid_amount');
    frm.refresh_field('custom_paid_amount_in_words');
    frm.refresh_field('custom_in_words_th');
};