// Script for DocType: Payment Entry

// --- 1. ปิดปาก Error เรื่อง Precision ---
if (typeof cur_frm !== 'undefined') {
    cur_frm.get_field_precision = function(df, doc) {
        if (df && df.fieldname === "amount" && df.parent === "Payment Entry Deduction") {
            return 2;
        }
        return df && df.precision ? df.precision : (frappe.boot.sysdefaults.float_precision || 2);
    };
}

frappe.ui.form.on('Payment Entry', {
    onload: function(frm) {
        if (frm.is_new() && frm.doc.references && frm.doc.references.length > 0) {
            if (frm.doc.payment_type === 'Receive') {
                fetch_deductions_from_doc(frm, 'Sales Invoice');
            }
            else if (frm.doc.payment_type === 'Pay') {
                fetch_deductions_from_doc(frm, 'Purchase Invoice');
            }
        }
    },
    
    paid_amount: function(frm) {
        if (frm.doc.payment_type === 'Pay' && frm.doc.paid_amount && frm.doc.received_amount === 0) {
             frm.set_value('received_amount', frm.doc.paid_amount);
        }
        else if (frm.doc.payment_type === 'Receive' && frm.doc.received_amount && frm.doc.paid_amount === 0) {
             frm.set_value('paid_amount', frm.doc.received_amount);
        }
        
        // ล็อก Allocated Amount ให้เท่าเดิมเสมอ
        force_update_allocated_amount(frm);
    }
});

// --- 2. ดัก Event ตารางลูก ---
frappe.ui.form.on('Payment Entry Deduction', {
    amount: function(frm) {
        // ถ้ามีการแก้ในตาราง ให้คำนวณกลับไปหา Paid Amount
        calculate_paid_amount_keep_allocated(frm);
    },
    deductions_remove: function(frm) {
        calculate_paid_amount_keep_allocated(frm);
    }
});

var fetch_deductions_from_doc = function(frm, source_doctype) {
    let ref_row = frm.doc.references.find(d => d.reference_doctype === source_doctype);
    
    if (ref_row) {
        // 1. จำยอดหนี้เต็มไว้ (Outstanding)
        // ถ้าเป็น Pay เราจะใช้ยอด Outstanding เป็นหลักในการ Allocated
        let target_allocated = flt(ref_row.outstanding_amount);
        if (target_allocated === 0) target_allocated = flt(ref_row.allocated_amount);

        frappe.call({
            method: "frappe.client.get",
            args: {
                doctype: source_doctype,
                name: ref_row.reference_name
            },
            callback: function(r) {
                if (r.message) {
                    let source_doc = r.message;
                    let new_deductions = [];
                    let total_deductions_abs = 0; // ยอดรวมแบบบวก (เพื่อคำนวณ Fallback)

                    let source_table = source_doc.custom_payment_entry_deduction || [];

                    // ตรวจสอบว่าเป็นฝั่ง Pay หรือไม่
                    let is_pay = frm.doc.payment_type === 'Pay';
                    let multiplier = is_pay ? -1 : 1; // *** Pay ให้ติดลบตามสั่ง ***

                    if (source_table.length > 0) {
                        source_table.forEach(d => {
                            if (d.account && flt(d.amount) > 0) {
                                new_deductions.push({
                                    'account': d.account,
                                    'cost_center': d.cost_center || source_doc.cost_center, 
                                    'amount': flt(d.amount, 2) * multiplier, // คูณ -1 ถ้าเป็น Pay
                                    'description': d.description || ""
                                });
                                total_deductions_abs += flt(d.amount, 2);
                            }
                        });
                    }

                    // 2. ใส่ข้อมูล Deduction
                    frm.set_value('deductions', new_deductions);
                    frm.refresh_field('deductions');

                    // 3. กำหนดยอด Paid Amount (ยอดจ่ายจริง)
                    let new_net_amount = 0;

                    if (is_pay && source_doc.custom_net_paid_amount) {
                        // ถ้าเป็น Pay ให้ดึงจาก Net Paid Amount ที่คำนวณไว้ใน PI เลย
                        new_net_amount = flt(source_doc.custom_net_paid_amount);
                    } else {
                        // Fallback: คำนวณเอง (หนี้เต็ม - ยอดหัก)
                        new_net_amount = target_allocated - total_deductions_abs;
                    }
                    
                    frm.set_value('paid_amount', flt(new_net_amount, 2));
                    frm.set_value('received_amount', flt(new_net_amount, 2));

                    // 4. *** บังคับ Allocated Amount ให้เป็นยอดเต็ม (Outstanding) ***
                    setTimeout(() => {
                        let current_ref = frm.doc.references.find(d => d.reference_name === ref_row.reference_name);
                        if (current_ref) {
                            current_ref.allocated_amount = target_allocated; // คืนค่ายอดหนี้เต็ม
                            frm.refresh_field('references');
                            
                            // สั่งคำนวณ Difference (ระบบอาจจะโวยวายเรื่อง Difference แต่เราบังคับค่าตามนี้)
                            frm.events.set_unallocated_amount(frm); 
                        }
                        
                        // แจ้งเตือน
                        if(new_deductions.length > 0) {
                             frappe.show_alert({
                                message: __('ดึงรายการหักเรียบร้อย (ยอดจ่าย {0}, ตัดหนี้ {1})', [new_net_amount.toFixed(2), target_allocated.toFixed(2)]),
                                indicator: 'green'
                            });
                        }
                    }, 500); 
                }
            }
        });
    }
};

// ฟังก์ชันคำนวณยอดจ่าย เมื่อมีการแก้ตัวเลข Deduction
var calculate_paid_amount_keep_allocated = function(frm) {
    let total_deductions_val = 0;
    (frm.doc.deductions || []).forEach(d => {
        // เอาค่าตามจริง (ถ้าเป็นลบก็เอาลบมาบวก)
        total_deductions_val += flt(d.amount); 
    });

    let total_allocated = 0;
    (frm.doc.references || []).forEach(d => {
        let base = d.outstanding_amount > 0 ? d.outstanding_amount : d.allocated_amount;
        total_allocated += flt(base);
        
        if (flt(d.allocated_amount) !== flt(base)) {
            d.allocated_amount = base;
        }
    });
    frm.refresh_field('references');

    if (total_allocated > 0) {
        // สูตร Adjustment: ถ้า Deduction เป็นลบ (-8)
        // Paid Amount = Allocated (107) + Deductions (-8) = 99
        let new_net = total_allocated + total_deductions_val;
        
        // กรณีไม่ใช่ Pay (เป็น Receive) สูตรคือ Allocated - Deduction (ค่าบวก) 
        // ซึ่ง total_deductions_val เป็นบวก -> 107 - 8 = 99 (ใช้ลบปกติ)
        // แต่โค้ดนี้เขียนแบบ Generic: 
        // ถ้า Pay: 107 + (-8) = 99 (ถูก)
        // ถ้า Receive: 107 + (8) = 115 (ผิดสำหรับ Receive ปกติ)
        
        // ดังนั้นแยก Case
        if (frm.doc.payment_type === 'Receive') {
             new_net = total_allocated - total_deductions_val;
        }

        frm.set_value('paid_amount', flt(new_net, 2));
        frm.set_value('received_amount', flt(new_net, 2));
    }
};

// ฟังก์ชันบังคับ Allocated ให้ถูกต้อง
var force_update_allocated_amount = function(frm) {
    let changed = false;
    (frm.doc.references || []).forEach(d => {
        // ดึงค่ากลับมาเป็น Outstanding เสมอ ถ้ามันลดลง
        if (flt(d.allocated_amount) < flt(d.outstanding_amount)) {
             d.allocated_amount = d.outstanding_amount;
             changed = true;
        }
    });
    
    if(changed) {
        frm.refresh_field('references');
        frm.trigger('set_unallocated_amount');
    }
};