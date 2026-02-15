// Script for DocType: Retention Payable

frappe.ui.form.on('Retention Payable', {
    refresh: function (frm) {
        if (frm.doc.docstatus === 0) {
            calculate_totals(frm);
        }

        // เช็คสถานะเพื่อแสดงปุ่ม Create หรือ View สำหรับ Retention Release (การคืนเงินประกัน)
        if (frm.doc.docstatus === 1 && ['Active', 'Overdue'].includes(frm.doc.status)) {
            // เคลียร์ปุ่มเก่าออกก่อนเพื่อกันซ้ำ
            frm.remove_custom_button(__('Retention Release'), __('Create'));
            frm.remove_custom_button(__('Retention Release'), __('View'));

            // เรียก API เช็คว่ามีการทำ Release ไปหรือยัง
            frappe.call({
                method: 'consbiz.api.get_retention_invoice_from_rr', 
                args: { rr_name: frm.doc.name },
                freeze: true,
                callback: function (r) {
                    if (r.message) {
                        // ถ้ามีแล้ว -> สร้างปุ่ม View
                        frm.add_custom_button(__('Retention Release'), function () {
                            frappe.set_route('Form', 'Retention Release', r.message);
                        }, __('View')); 
                    } else {
                        // ถ้ายังไม่มี -> สร้างปุ่ม Create
                        frm.add_custom_button(__('Retention Release'), function () {
                            create_retention_release(frm);
                        }, __('Create')); 
                    }
                }
            });
        }
    },

    // --- Trigger 1: เมื่อแก้ Posting Date ---
    // 1. คำนวณ Due Date (จาก Period)
    // 2. อัปเดต Posting Date ลงใน Child Table
    posting_date: function(frm) {
        calculate_due_date(frm);
        
        if (frm.doc.posting_date && frm.doc.retention_items) {
            $.each(frm.doc.retention_items, function(i, d) {
                frappe.model.set_value(d.doctype, d.name, 'posting_date', frm.doc.posting_date);
            });
        }
    },

    // --- Trigger 2: เมื่อแก้ Period ---
    period: function(frm) {
        calculate_due_date(frm);
    },

    // --- Trigger 3: เมื่อแก้ Due Date (หรือถูก Set จาก calculate_due_date) ---
    // อัปเดต Due Date ลงใน Child Table
    due_date: function(frm) {
        if (frm.doc.due_date && frm.doc.retention_items) {
            $.each(frm.doc.retention_items, function(i, d) {
                frappe.model.set_value(d.doctype, d.name, 'due_date', frm.doc.due_date);
            });
        }
    },

    validate: function(frm) {
        calculate_totals(frm);
        calculate_due_date(frm);

        if (!frm.doc.posting_date) {
            frappe.throw(__('กรุณาระบุ Posting Date'));
        }
    }
});

frappe.ui.form.on('Retention Items', {
    amount: function (frm, cdt, cdn) {
        calculate_totals(frm);
    },
    
    retention_items_remove: function (frm) {
        calculate_totals(frm);
    }
});

// Helper Functions

// ฟังก์ชันคำนวณ Due Date = Posting Date + Period
var calculate_due_date = function(frm) {
    if (frm.doc.posting_date && frm.doc.period) {
        // ใช้ frappe.datetime.add_days เพื่อบวกวัน
        let new_due_date = frappe.datetime.add_days(frm.doc.posting_date, parseInt(frm.doc.period));
        // การ set_value ตรงนี้จะไปกระตุ้น Trigger 'due_date' ด้านบนให้ทำงานต่ออัตโนมัติ
        frm.set_value('due_date', new_due_date);
    }
};

function create_retention_release(frm) {
    frappe.model.with_doctype('Retention Release', function() {
        var doc = frappe.model.get_new_doc('Retention Release');
        
        doc.company = frm.doc.company;
        doc.supplier = frm.doc.supplier;
        doc.project = frm.doc.project;
        doc.posting_date = frappe.datetime.get_today();
        
        // Copy Retention Items to Release Items
        if (frm.doc.retention_items && frm.doc.retention_items.length > 0) {
            $.each(frm.doc.retention_items, function(i, item) {
                var row = frappe.model.add_child(doc, 'Retention Items', 'retention_items');
                row.reference_no = frm.doc.name;
                row.description = item.description || ("Retention Release from " + frm.doc.name);
                row.base_amount = item.base_amount;
                row.retention_percent = item.retention_percent;
                row.amount = item.amount;
                row.posting_date = item.posting_date;
                row.due_date = item.due_date;
            });
        }

        // 4. คำนวณยอดรวม (Grand Total)
        doc.grand_total = frm.doc.grand_total;
        if (typeof thai_baht_text === 'function') {
             doc.in_words = thai_baht_text(doc.grand_total);
        }

        // 5. เปิดหน้าเอกสารใหม่
        frappe.set_route('Form', 'Retention Release', doc.name);
    });
}

var calculate_totals = function (frm) {
    var total_amount = 0;
    $.each(frm.doc.retention_items || [], function (i, d) {
        total_amount += flt(d.amount);
    });

    frm.set_value('grand_total', total_amount);

    if (total_amount !== 0) {
        if (typeof thai_baht_text === 'function') {
            let text = total_amount > 0 ? thai_baht_text(total_amount) : 'ติดลบ' + thai_baht_text(Math.abs(total_amount));
            frm.set_value('in_words', text);
        }
    } else {
        frm.set_value('in_words', 'ศูนย์บาทถ้วน');
    }
};