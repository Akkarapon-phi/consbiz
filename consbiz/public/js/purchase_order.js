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