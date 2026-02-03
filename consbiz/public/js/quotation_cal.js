frappe.ui.form.on('Quotation', {
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
        if (frm.doc.transaction_date) {
            // 1. อัปเดตวันยืนยันราคา (Valid Till) เป็น +30 วันจากวันที่เอกสาร
            let new_valid_till = frappe.datetime.add_days(frm.doc.transaction_date, 30);
            frm.set_value('valid_till', new_valid_till);

            // 2. อัปเดตวันครบกำหนดชำระ (Due Date) ในตาราง Payment Schedule
            // แก้ไข: อิงตาม payment_terms_template เท่านั้น หากไม่มีไม่ต้องทำอะไร
            if (frm.doc.payment_terms_template) {
                // เรียกใช้ Event มาตรฐานของ ERPNext เพื่อคำนวณตารางใหม่ตาม Template และวันที่ใหม่
                if (frm.events.payment_terms_template) {
                    frm.events.payment_terms_template(frm);
                } else {
                    // Fallback: ถ้าหา event ไม่เจอ ให้ลอง Trigger field change
                    frm.trigger('payment_terms_template');
                }
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
    // 1. ดึงค่าพื้นฐาน
    let net_total = flt(frm.doc.net_total);
    let grand_total = flt(frm.doc.grand_total);
    let rounding = flt(frm.doc.rounding_adjustment);
    
    let wht_amount = 0;
    let retention_amount = 0;

    // 2. คำนวณ WHT (จากยอดก่อนภาษี) และปัดเศษ 2 ตำแหน่งทันที
    if (frm.doc.custom_subject_to_wht && flt(frm.doc.custom_wht_percent) > 0) {
        wht_amount = flt((net_total * flt(frm.doc.custom_wht_percent) / 100), 2);
    }
    
    // 3. คำนวณ Retention (จากยอดก่อนภาษี) และปัดเศษ 2 ตำแหน่งทันที
    if (frm.doc.custom_subject_to_retention && flt(frm.doc.custom_retention_percent) > 0) {
        retention_amount = flt((net_total * flt(frm.doc.custom_retention_percent) / 100), 2);
    }

    // อัปเดตฟิลด์ยอดหัก
    frm.set_value('custom_wht_amount', wht_amount);
    frm.set_value('custom_retention_amount', retention_amount);

    // 4. คำนวณยอดจ่ายสุทธิ
    // ตอนนี้ wht_amount และ retention_amount ถูกปัดเศษมาแล้ว การลบจึงแม่นยำขึ้น
    let paid_amount = grand_total - wht_amount - retention_amount + rounding;
    paid_amount = flt(paid_amount, 2);

    frm.set_value('custom_paid_amount', paid_amount);

    // --- ส่วนแสดงคำอ่านภาษาไทย (เรียกใช้ Global Function) ---
    if (typeof thai_baht_text === 'function') {
        // ยอดจ่ายสุทธิ
        if (paid_amount !== 0) {
            let text = paid_amount > 0 ? thai_baht_text(paid_amount) : 'ติดลบ' + thai_baht_text(Math.abs(paid_amount));
            frm.set_value('custom_paid_amount_in_words', text);
        } else {
            frm.set_value('custom_paid_amount_in_words', 'ศูนย์บาทถ้วน');
        }

        // ยอดรวมทั้งสิ้น
        if (grand_total !== 0) {
            let text_grand = grand_total > 0 ? thai_baht_text(grand_total) : 'ติดลบ' + thai_baht_text(Math.abs(grand_total));
            frm.set_value('custom_in_words_th', text_grand);
        } else {
            frm.set_value('custom_in_words_th', 'ศูนย์บาทถ้วน');
        }
    }

    // Refresh หน้าจอ
    frm.refresh_field('custom_wht_amount');
    frm.refresh_field('custom_retention_amount');
    frm.refresh_field('custom_paid_amount');
    frm.refresh_field('custom_paid_amount_in_words');
    frm.refresh_field('custom_in_words_th');
};