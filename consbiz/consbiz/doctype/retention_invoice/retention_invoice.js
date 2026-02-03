// Script for DocType: Retention Invoice

// Config ชื่อ Field ตาราง (ต้องตรงกับในหน้าจอ)
const TABLE_FIELD_NAME = 'retention_items'; 
// ชื่อ Child DocType ที่ใช้ใน Events
const CHILD_DOCTYPE_NAME = 'Retention Items'; 

frappe.ui.form.on('Retention Invoice', {
    refresh: function(frm) {
        // ปุ่มสำหรับดึงข้อมูล (แสดงตอน Draft)
        if (frm.doc.docstatus === 0) {
            frm.add_custom_button(__('Get All Retentions'), function() {
                get_all_retentions(frm);
            }, __('Get Items'));

            frm.add_custom_button(__('Select Retentions'), function() {
                select_retentions(frm);
            }, __('Get Items'));
        }

        // ปุ่ม Create Payment (แสดงตอน Submit แล้ว)
        if (frm.doc.docstatus === 1) {
            frm.add_custom_button(__('Payment Entry'), function() {
                create_payment_entry(frm);
            }, __('Create'));
        }
    },
    validate: function(frm) {
        calculate_totals(frm);
    }
});

frappe.ui.form.on(CHILD_DOCTYPE_NAME, {
    base_amount: function(frm, cdt, cdn) {
        calculate_row_amount(frm, cdt, cdn);
    },
    retention_percent: function(frm, cdt, cdn) {
        calculate_row_amount(frm, cdt, cdn);
    },
    amount: function(frm, cdt, cdn) {
        calculate_totals(frm);
    },
    retention_items_remove: function(frm) {
        calculate_totals(frm);
    }
});

// ฟังก์ชันสร้าง Payment Entry (รอรับ Logic Mapping)
function create_payment_entry(frm) {
    // TODO: ใส่ Logic การ Map ค่าตามที่ผู้ใช้จะแจ้งมา
    frappe.msgprint("ฟังก์ชันนี้พร้อมใช้งาน รอข้อมูลการ Map ค่าครับ");
}

function calculate_row_amount(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    if (row.base_amount && row.retention_percent) {
        let new_amount = (flt(row.base_amount) * flt(row.retention_percent)) / 100;
        frappe.model.set_value(cdt, cdn, 'amount', new_amount);
    }
}

function get_all_retentions(frm) {
    if (!frm.doc.customer) {
        frappe.msgprint(__('กรุณาเลือก Customer ก่อน'));
        return;
    }

    // ปรับ Filter: เอาเฉพาะ Active หรือ Overdue
    let filters = [
        ['customer', '=', frm.doc.customer],
        ['docstatus', '=', 1],
        ['status', 'in', ['Active', 'Overdue']] 
    ];
    if (frm.doc.company) filters.push(['company', '=', frm.doc.company]);
    if (frm.doc.project) filters.push(['project', '=', frm.doc.project]);

    frappe.call({
        method: 'frappe.client.get_list',
        args: {
            doctype: 'Retention Receivable',
            filters: filters,
            fields: ['name']
        },
        callback: function(r) {
            if (r.message && r.message.length > 0) {
                let names = r.message.map(d => d.name);
                fetch_from_parents(frm, names);
            } else {
                frappe.msgprint(__('ไม่พบเอกสาร Retention Receivable ที่ Active หรือ Overdue'));
            }
        }
    });
}

function select_retentions(frm) {
    if (!frm.doc.customer) {
        frappe.msgprint(__('กรุณาเลือก Customer ก่อน'));
        return;
    }

    // ปรับ Filter: เอาเฉพาะ Active หรือ Overdue
    let filters = {
        'customer': frm.doc.customer,
        'docstatus': 1,
        'status': ['in', ['Active', 'Overdue']]
    };
    if (frm.doc.company) filters['company'] = frm.doc.company;
    if (frm.doc.project) filters['project'] = frm.doc.project;

    new frappe.ui.form.MultiSelectDialog({
        doctype: "Retention Receivable",
        target: frm,
        setters: {
            customer: frm.doc.customer,
            company: frm.doc.company,
            project: frm.doc.project
        },
        add_filters_group: 1,
        get_query: function() {
            return { filters: filters };
        },
        action: function(selections) {
            if (selections.length > 0) {
                fetch_from_parents(frm, selections);
                cur_dialog.hide();
            }
        }
    });
}

function fetch_from_parents(frm, parent_names) {
    let target_child_doctype = frm.fields_dict[TABLE_FIELD_NAME].grid.doctype;
    let processed_count = 0;
    let added_count = 0;
    
    let existing_keys = [];
    (frm.doc[TABLE_FIELD_NAME] || []).forEach(d => {
        if(d.sales_invoice) existing_keys.push(d.sales_invoice);
        if(d.purchase_invoice) existing_keys.push(d.purchase_invoice);
        if(d.supplier_invoice) existing_keys.push(d.supplier_invoice);
    });

    parent_names.forEach(parent_name => {
        frappe.call({
            method: 'frappe.client.get',
            args: {
                doctype: 'Retention Receivable',
                name: parent_name
            },
            callback: function(r) {
                if (r.message) {
                    let parent_doc = r.message;
                    let source_items = parent_doc[TABLE_FIELD_NAME] || [];

                    source_items.forEach(item => {
                        let is_duplicate = false;
                        if (item.sales_invoice && existing_keys.includes(item.sales_invoice)) is_duplicate = true;
                        if (item.purchase_invoice && existing_keys.includes(item.purchase_invoice)) is_duplicate = true;
                        if (item.supplier_invoice && existing_keys.includes(item.supplier_invoice)) is_duplicate = true;

                        if (!is_duplicate) {
                            let row = frappe.model.add_child(frm.doc, target_child_doctype, TABLE_FIELD_NAME);
                            
                            row.posting_date = item.posting_date;
                            row.due_date = item.due_date;
                            row.sales_invoice = item.sales_invoice;
                            row.purchase_invoice = item.purchase_invoice;
                            row.supplier_invoice = item.supplier_invoice;
                            row.description = item.description;
                            row.base_amount = item.base_amount;
                            row.retention_percent = item.retention_percent;
                            row.amount = item.amount;

                            if(item.sales_invoice) existing_keys.push(item.sales_invoice);
                            if(item.purchase_invoice) existing_keys.push(item.purchase_invoice);
                            if(item.supplier_invoice) existing_keys.push(item.supplier_invoice);
                            
                            added_count++;
                        }
                    });
                }
                
                processed_count++;
                if (processed_count === parent_names.length) {
                    frm.refresh_field(TABLE_FIELD_NAME);
                    calculate_totals(frm);
                    
                    if (added_count > 0) {
                        frappe.show_alert({message: __('เพิ่มรายการใหม่ ' + added_count + ' รายการ'), indicator: 'green'});
                    } else {
                        frappe.show_alert({message: __('ไม่มีรายการใหม่ หรือรายการซ้ำกันทั้งหมด'), indicator: 'orange'});
                    }
                }
            }
        });
    });
}

function calculate_totals(frm) {
    let total_amount = 0;
    (frm.doc[TABLE_FIELD_NAME] || []).forEach(d => {
        total_amount += flt(d.amount);
    });
    
    // 1. อัปเดตยอดรวมตัวเลข
    frm.set_value('grand_total', total_amount);
    
    // 2. อัปเดตคำอ่านภาษาไทย (ใช้ฟังก์ชันที่ปรับปรุงแล้ว)
    if (frm.fields_dict['in_words']) {
        let text_val = total_amount !== 0 ? 
            (total_amount > 0 ? thai_baht_text(total_amount) : 'ติดลบ' + thai_baht_text(Math.abs(total_amount))) : 'ศูนย์บาทถ้วน';
        frm.set_value('in_words', text_val);
    }
}

// --- ฟังก์ชันอ่านค่าเงินภาษาไทย (Improved Version) ---
function thai_baht_text(num) {
    num = parseFloat(num).toFixed(2);
    let parts = num.split('.');
    let baht = parseInt(parts[0]);
    let satang = parseInt(parts[1]);

    let result = text_num_thai(baht);
    if (result === '') result = 'ศูนย์';
    result += 'บาท';

    if (satang === 0) {
        result += 'ถ้วน';
    } else {
        result += text_num_thai(satang) + 'สตางค์';
    }
    return result;
}

function text_num_thai(num) {
    const thai_num = ["ศูนย์", "หนึ่ง", "สอง", "สาม", "สี่", "ห้า", "หก", "เจ็ด", "แปด", "เก้า"];
    const thai_unit = ["", "สิบ", "ร้อย", "พัน", "หมื่น", "แสน", "ล้าน"];
    
    let res = "";
    let num_str = num.toString();
    let len = num_str.length;

    for (let i = 0; i < len; i++) {
        let n = parseInt(num_str[i]);
        let pos = len - i - 1;
        let unit_pos = pos % 6;

        if (n !== 0) {
            // กรณี "เอ็ด": ต้องเป็นหลักหน่วย (unit_pos 0) และไม่ใช่เลขหลักเดียว (len > 1) หรือกรณีหลักล้าน
            // แก้ไข logic ให้รองรับ 101, 201 ได้ถูกต้อง
            if (unit_pos === 0 && n === 1 && (pos === 0 && len > 1)) { 
                res += 'เอ็ด'; 
            } else if (unit_pos === 1 && n === 2) {
                res += 'ยี่';
            } else if (unit_pos === 1 && n === 1) {
                // ไม่ต้องทำอะไร (สิบ)
            } else {
                res += thai_num[n];
            }
            res += thai_unit[unit_pos];
        }
        
        // เติม "ล้าน" เมื่อครบรอบ 6 หลัก
        if (pos > 0 && pos % 6 === 0) {
            res += 'ล้าน';
        }
    }
    return res;
}