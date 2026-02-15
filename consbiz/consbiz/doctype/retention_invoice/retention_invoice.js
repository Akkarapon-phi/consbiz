// Script for DocType: Retention Invoice

// ============================================================
// 1. Function Declarations (ฟังก์ชันหลักสำหรับ Dialog)
// ============================================================

function get_retention_receivable_dialog(frm) {
    let raw_data = [];

    let d = new frappe.ui.Dialog({
        title: __('Select Retention Receivables'),
        size: 'extra-large',
        fields: [
            { fieldtype: 'Section Break', label: __('Filters') },
            { fieldname: 'col1', fieldtype: 'Column Break' },
            { fieldname: 'company', fieldtype: 'Link', options: 'Company', label: 'Company', default: frm.doc.company, read_only: 1 },
            { fieldname: 'customer', fieldtype: 'Link', options: 'Customer', label: 'Customer', default: frm.doc.customer, read_only: 1 },
            { fieldname: 'col2', fieldtype: 'Column Break' },
            { fieldname: 'project', fieldtype: 'Link', options: 'Project', label: 'Project', default: frm.doc.project, read_only: 1 },
            { fieldname: 'customer_po', fieldtype: 'Data', label: "Customer's Purchase Order", default: frm.doc.customer_po, read_only: 1 },
            { fieldtype: 'Section Break' },
            { 
                fieldname: 'search_term', fieldtype: 'Data', 
                label: __('Search'),
                placeholder: 'Search Ref No / Invoice No / Retention No...',
                onchange: function() { render_table(); }
            },
            { fieldname: 'results_area', fieldtype: 'HTML' }
        ],
        primary_action_label: __('Add Selected'),
        primary_action: function() {
            add_selected_items(d, frm);
        }
    });

    function fetch_data() {
        d.fields_dict.results_area.$wrapper.html('<div class="text-center text-muted p-4">' + __('Loading...') + '</div>');

        let filters = {
            customer: frm.doc.customer,
            company: frm.doc.company,
            docstatus: 1,
            status: ['in', ['Active', 'Overdue']]
        };
        if (frm.doc.project) filters.project = frm.doc.project;
        if (frm.doc.customer_po) filters.customer_po = frm.doc.customer_po;

        frappe.call({
            method: 'frappe.client.get_list',
            args: {
                doctype: 'Retention Receivable',
                filters: filters,
                fields: ['name']
            },
            callback: function(r) {
                let parent_names = (r.message || []).map(p => p.name);
                if (parent_names.length === 0) {
                    raw_data = [];
                    render_table();
                    return;
                }

                let processed = 0;
                let all_items = [];

                parent_names.forEach(name => {
                    frappe.call({
                        method: 'frappe.client.get',
                        args: { doctype: 'Retention Receivable', name: name },
                        callback: function(res) {
                            if (res.message) {
                                let doc = res.message;
                                (doc.retention_items || []).forEach(item => {
                                    all_items.push({
                                        ...item,
                                        reference_no: doc.name,
                                        retention_no: item.retention_no,
                                        posting_date: doc.posting_date,
                                        due_date: doc.due_date
                                    });
                                });
                            }
                            processed++;
                            if (processed === parent_names.length) {
                                // เรียงตามเลขเอกสาร Reference No
                                raw_data = all_items.sort((a, b) => a.reference_no.localeCompare(b.reference_no));
                                render_table();
                            }
                        }
                    });
                });
            }
        });
    }

    function render_table() {
        let search_val = (d.get_value('search_term') || '').toLowerCase();
        
        // --- ส่วนป้องกันข้อมูลซ้ำ: ดึง Key ปัจจุบันจากหน้าฟอร์มมาเช็คทุกครั้งที่ Render ---
        let existing_keys = (frm.doc.retention_items || []).map(row => 
            `${row.reference_no}_${row.sales_invoice_no}_${row.retention_no}`
        );

        let filtered_data = raw_data.filter(item => {
            let key = `${item.reference_no}_${item.sales_invoice_no}_${item.retention_no}`;
            
            // ถ้ามีในตารางหลักแล้ว ไม่ต้องแสดงใน List
            if (existing_keys.includes(key)) return false;
            
            if (search_val) {
                return (item.reference_no || '').toLowerCase().includes(search_val) || 
                       (item.sales_invoice_no || '').toLowerCase().includes(search_val) ||
                       (item.retention_no || '').toLowerCase().includes(search_val);
            }
            return true;
        });

        let html = `
            <style>
                .ret-table-container { max-height: 450px; overflow-y: auto; border: 1px solid #d1d8dd; border-radius: 8px; }
                .ret-table { margin-bottom: 0; font-size: 13px; }
                .ret-table thead th { position: sticky; top: 0; background-color: #f4f5f6; z-index: 2; border-bottom: 2px solid #d1d8dd !important; }
                .text-bold { font-weight: 600; color: #1d1e1f; }
            </style>
            <div class="ret-table-container">
                <table class="table table-bordered table-hover ret-table">
                    <thead>
                        <tr>
                            <th width="40px" class="text-center"><input type="checkbox" id="select-all-rets"></th>
                            <th>${__('Reference No')}</th>
                            <th>${__('Sales Invoice No')}</th>
                            <th>${__('Retention No')}</th>
                            <th>${__('Due Date')}</th>
                            <th class="text-right">${__('Amount')}</th>
                        </tr>
                    </thead>
                    <tbody>`;

        if (filtered_data.length > 0) {
            filtered_data.forEach(row => {
                let row_json = encodeURIComponent(JSON.stringify(row));
                html += `
                    <tr class="clickable-row" style="cursor: pointer;">
                        <td class="text-center"><input type="checkbox" class="ret-checkbox" data-row="${row_json}"></td>
                        <td class="text-bold">${row.reference_no}</td>
                        <td>${row.sales_invoice_no || '-'}</td>
                        <td><span class="label label-default">${row.retention_no || '-'}</span></td>
                        <td>${frappe.datetime.str_to_user(row.due_date)}</td>
                        <td class="text-right text-bold">${format_currency(row.amount, frm.doc.currency)}</td>
                    </tr>`;
            });
        } else {
            html += `<tr><td colspan="6" class="text-center text-muted p-5">${__('No matching records found')}</td></tr>`;
        }
        html += `</tbody></table></div>`;
        
        d.fields_dict.results_area.$wrapper.html(html);

        let $wrapper = d.fields_dict.results_area.$wrapper;
        $wrapper.find('#select-all-rets').on('change', function() {
            $wrapper.find('.ret-checkbox').prop('checked', $(this).is(':checked'));
        });
        $wrapper.find('.clickable-row').on('click', function(e) {
            if (e.target.type !== 'checkbox') {
                let $cb = $(this).find('.ret-checkbox');
                $cb.prop('checked', !$cb.prop('checked'));
            }
        });
    }

    d.show();
    fetch_data();
}

// --- ฟังก์ชันนำข้อมูลที่เลือกเข้าสู่ตารางหลัก ---
function add_selected_items(d, frm) {
    let count = 0;
    let current_keys = (frm.doc.retention_items || []).map(row => 
        `${row.reference_no}_${row.sales_invoice_no}_${row.retention_no}`
    );

    d.$wrapper.find('.ret-checkbox:checked').each(function() {
        let data = JSON.parse(decodeURIComponent($(this).attr('data-row')));
        let new_key = `${data.reference_no}_${data.sales_invoice_no}_${data.retention_no}`;

        if (!current_keys.includes(new_key)) {
            let row = frm.add_child('retention_items');
            row.reference_no = data.reference_no;
            row.sales_invoice_no = data.sales_invoice_no;
            row.retention_no = data.retention_no; 
            row.amount = data.amount;
            row.base_amount = data.base_amount;
            row.retention_percent = data.retention_percent;
            row.posting_date = data.posting_date;
            row.due_date = data.due_date;
            row.description = data.description || `Retention from ${data.reference_no}`;
            
            current_keys.push(new_key);
            count++;
        }
    });

    if (count > 0) {
        frm.refresh_field('retention_items');
        calculate_totals(frm);
        
        // บังคับปิด Dialog
        if (d) d.hide();
        else if (cur_dialog) cur_dialog.hide();
        
        frappe.show_alert({ message: __('Added ' + count + ' items'), indicator: 'green' });
    } else {
        frappe.msgprint(__('ไม่มีรายการใหม่ถูกเพิ่ม หรือรายการถูกเลือกไปหมดแล้ว'));
    }
}

// --- ฟังก์ชันคำนวณยอดรวมและตัวอักษรภาษาไทย ---
var calculate_totals = function(frm) {
    let total = 0;
    (frm.doc.retention_items || []).forEach(d => { total += flt(d.amount); });
    
    frm.set_value('grand_total', total);
    
    if (typeof thai_baht_text === 'function') {
        let text_val = total !== 0 ? 
            (total > 0 ? thai_baht_text(total) : 'ติดลบ' + thai_baht_text(Math.abs(total))) : 
            'ศูนย์บาทถ้วน';
        frm.set_value('in_words', text_val);
    }
};

// ============================================================
// 2. Form Events
// ============================================================

frappe.ui.form.on('Retention Invoice', {
    refresh: function(frm) {
        // แสดงปุ่มเฉพาะสถานะ Draft
        if (frm.doc.docstatus === 0) {
            frm.add_custom_button(__('Get Retention Receivables'), function() {
                if (!frm.doc.customer) {
                    frappe.msgprint(__('กรุณาเลือก Customer ก่อน'));
                    return;
                }
                get_retention_receivable_dialog(frm);
            }, __('Get Items'));
        }
    },
    validate: function(frm) {
        calculate_totals(frm);
    }
});

frappe.ui.form.on('Retention Items', {
    amount: function(frm, cdt, cdn) { calculate_totals(frm); },
    retention_items_remove: function(frm) { calculate_totals(frm); }
});