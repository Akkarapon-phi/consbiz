frappe.ui.form.on('Retention Receivable', {
    refresh: function(frm) {
        // 1. Logic เดิม: คำนวณยอดถ้าเป็น Draft
        if (frm.doc.docstatus === 0) {
            calculate_totals(frm);
        }

        // 2. Logic ใหม่: ปุ่ม Create Retention Claim
        // แสดงเมื่อ Submit แล้ว (docstatus=1) และสถานะยังไม่ถูกเก็บเงิน (Active หรือ Overdue)
        // ถ้าสถานะเป็น 'Billed' แปลว่าถูกเคลมไปแล้ว ปุ่มจะไม่ขึ้น
        if (frm.doc.docstatus === 1 && ['Active', 'Overdue'].includes(frm.doc.status)) {
            
            frm.add_custom_button(__('Retention Claim'), function() {
                create_retention_claim(frm);
            }, __('Create'));
        }
        
    },
    validate: function(frm) {
        calculate_totals(frm);
    }
});

// Event Triggers สำหรับ Child Table (Logic เดิม)
frappe.ui.form.on('Retention Items', {
    base_amount: function(frm, cdt, cdn) { calculate_row_amount(frm, cdt, cdn); },
    retention_percent: function(frm, cdt, cdn) { calculate_row_amount(frm, cdt, cdn); },
    amount: function(frm, cdt, cdn) { calculate_totals(frm); },
    retention_items_remove: function(frm) { calculate_totals(frm); }
});

// ฟังก์ชันสร้าง Retention Claim
function create_retention_claim(frm) {
    frappe.model.with_doctype('Retention Claim', function() {
        
        // 1. สร้างเอกสารใหม่ใน Memory
        var doc = frappe.model.get_new_doc('Retention Claim');
        
        // 2. Map ข้อมูล Header
        doc.company = frm.doc.company;
        doc.customer = frm.doc.customer;
        doc.project = frm.doc.project;
        doc.customer_po = frm.doc.customer_po;
        
        // วันที่ตั้งเบิก: ใช้วันปัจจุบัน
        doc.posting_date = frappe.datetime.get_today();
        
        // 3. Map ข้อมูล Child Table
        $.each(frm.doc.retention_items || [], function(i, d) {
            var row = frappe.model.add_child(doc, 'Retention Items', 'retention_items');
            
            // ดึงค่า Field ต่อ Field
            row.sales_invoice = d.sales_invoice;
            row.posting_date = d.posting_date;
            row.due_date = d.due_date;
            row.description = d.description;
            row.base_amount = d.base_amount;
            row.retention_percent = d.retention_percent;
            row.amount = d.amount;
            
            // เผื่อมีเคสอื่นๆ (ถ้าใช้กับฝั่งเจ้าหนี้ด้วย)
            if(d.purchase_invoice) row.purchase_invoice = d.purchase_invoice;
            if(d.supplier_invoice) row.supplier_invoice = d.supplier_invoice;
        });

        // 4. สั่งให้เด้งไปหน้าจอ Retention Claim
        frappe.set_route('Form', 'Retention Claim', doc.name);
    });
}

// --- ฟังก์ชันคำนวณ (Logic เดิม) ---
var calculate_row_amount = function(frm, cdt, cdn) {
    var row = locals[cdt][cdn];
    if (row.base_amount && row.retention_percent) {
        var new_amount = flt(row.base_amount) * flt(row.retention_percent) / 100;
        frappe.model.set_value(cdt, cdn, 'amount', new_amount);
    }
};

var calculate_totals = function(frm) {
    var total_amount = 0;
    $.each(frm.doc.retention_items || [], function(i, d) {
        total_amount += flt(d.amount);
    });
    
    frm.set_value('grand_total', total_amount);
    
    if (total_amount !== 0) {
        let text = total_amount > 0 ? thai_baht_text(total_amount) : 'ติดลบ' + thai_baht_text(Math.abs(total_amount));
        frm.set_value('in_words', text);
    } else {
        frm.set_value('in_words', 'ศูนย์บาทถ้วน');
    }
};

// --- ฟังก์ชันอ่านค่าเงินภาษาไทย ---
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
            if (unit_pos === 0 && n === 1 && i > 0) { 
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
        
        if (pos > 0 && pos % 6 === 0) {
            res += 'ล้าน';
        }
    }
    return res;
}