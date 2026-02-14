frappe.ui.form.on('Retention Receivable', {
    refresh: function (frm) {
        if (frm.doc.docstatus === 0) {
            calculate_totals(frm);
        }

        // เช็คสถานะเพื่อแสดงปุ่ม Create หรือ View
        if (frm.doc.docstatus === 1 && ['Active', 'Overdue'].includes(frm.doc.status)) {
            // เคลียร์ปุ่มเก่าออกก่อนเพื่อกันซ้ำ
            frm.remove_custom_button(__('Retention Invoice'), __('Create'));
            frm.remove_custom_button(__('Retention Invoice'), __('View'));

            frappe.call({
                method: 'consbiz.api.get_retention_invoice_from_rr',
                args: { rr_name: frm.doc.name },
                freeze: true,
                callback: function (r) {
                    if (r.message) {
                        // ถ้ามีแล้ว -> สร้างปุ่ม View
                        frm.add_custom_button(__('Retention Invoice'), function () {
                            frappe.set_route('Form', 'Retention Invoice', r.message);
                        }, __('View')); 
                    } else {
                        // ถ้ายังไม่มี -> สร้างปุ่ม Create
                        frm.add_custom_button(__('Retention Invoice'), function () {
                            create_retention_invoice(frm);
                        }, __('Create')); 
                    }
                }
            });
        }
    },
    validate: function (frm) {
        calculate_totals(frm);
    }
});

frappe.ui.form.on('Retention Items', {
    base_amount: function (frm, cdt, cdn) { calculate_row_amount(frm, cdt, cdn); },
    retention_percent: function (frm, cdt, cdn) { calculate_row_amount(frm, cdt, cdn); },
    amount: function (frm, cdt, cdn) { calculate_totals(frm); },
    retention_items_remove: function (frm) { calculate_totals(frm); }
});

function create_retention_invoice(frm) {
    frappe.model.with_doctype('Retention Invoice', function() {
        // 1. สร้างเอกสารใหม่ใน Memory
        var doc = frappe.model.get_new_doc('Retention Invoice');

        // 2. Map ข้อมูล Header
        doc.company = frm.doc.company;
        doc.customer = frm.doc.customer;
        doc.customer_po = frm.doc.customer_po; // ดึง Customer PO
        doc.project = frm.doc.project;
        doc.posting_date = frappe.datetime.get_today();
        
        // 3. Map ข้อมูล Child Table (Items)
        if (frm.doc.retention_items && frm.doc.retention_items.length > 0) {
            $.each(frm.doc.retention_items, function(i, item) {
                var row = frappe.model.add_child(doc, 'Retention Items', 'retention_items');
                
                // สำคัญ: เก็บชื่อ Retention Receivable ไว้ใน reference_no 
                // เพื่อให้ระบบรู้ว่ารายการนี้มาจาก RR ใบไหน (ใช้ตอน Update Status / Check Duplicate)
                row.reference_no = frm.doc.name; 
                
                // Map Field รายการ
                // sales_invoice_no จาก RR -> sales_invoice ใน RI
                row.sales_invoice_no = item.sales_invoice_no; 
                row.description = item.description || ("Retention from " + frm.doc.name);
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
        frappe.set_route('Form', 'Retention Invoice', doc.name);
    });
}

var calculate_row_amount = function (frm, cdt, cdn) {
    var row = locals[cdt][cdn];
    if (row.base_amount && row.retention_percent) {
        var new_amount = flt(row.base_amount) * flt(row.retention_percent) / 100;
        frappe.model.set_value(cdt, cdn, 'amount', new_amount);
    }
};

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