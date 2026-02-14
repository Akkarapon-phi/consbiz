// Script for DocType: Retention Invoice

// Config ชื่อ Field ตาราง (ต้องตรงกับในหน้าจอ)
const TABLE_FIELD_NAME = 'retention_items';
// ชื่อ Child DocType ที่ใช้ใน Events
const CHILD_DOCTYPE_NAME = 'Retention Items';

frappe.ui.form.on('Retention Invoice', {
    refresh: function (frm) {
        // Fix: Amend Status and clear No Copy fields manually if they carry over
        if (frm.doc.amended_from && frm.doc.docstatus === 0) {
            if (frm.doc.status !== 'Draft') frm.set_value('status', 'Draft');
            if (frm.doc.mode_of_payment) frm.set_value('mode_of_payment', '');
            if (frm.doc.account) frm.set_value('account', '');
            if (frm.doc.bank) frm.set_value('bank', '');
            if (frm.doc.bank_account_no) frm.set_value('bank_account_no', '');
        }

        // ปุ่มสำหรับดึงข้อมูล (แสดงตอน Draft)
        if (frm.doc.docstatus === 0) {
            frm.add_custom_button(__('Get All Retentions'), function () {
                get_all_retentions(frm);
            }, __('Get Items'));

            frm.add_custom_button(__('Select Retentions'), function () {
                select_retentions(frm);
            }, __('Get Items'));
        }

        // Create Payment / View Journal Entry Logic
        if (frm.doc.docstatus === 1) {
            frappe.call({
                method: 'consbiz.api.get_linked_journal_entry',
                args: { retention_invoice: frm.doc.name },
                callback: function (r) {
                    if (r.message) {
                        frm.add_custom_button(__('View Journal Entry'), function () {
                            frappe.set_route('Form', 'Journal Entry', r.message);
                        });
                    } else {
                        if (frm.doc.status !== 'Paid') {
                            frm.add_custom_button(__('Payment'), function () {
                                create_payment_entry(frm);
                            }, __('Create'));
                        }
                    }
                }
            });
        }
    },
    validate: function (frm) {
        calculate_totals(frm);
    },
    
    // Trigger เมื่อเปลี่ยน Credit Day (คำนวณ Due Date ใหม่)
    credit_day: function(frm) {
        calculate_due_date(frm);
    },
    
    // Trigger เมื่อเปลี่ยนวันที่เอกสาร (คำนวณ Due Date ใหม่)
    posting_date: function(frm) {
        calculate_due_date(frm);
    }
});

frappe.ui.form.on(CHILD_DOCTYPE_NAME, {
    base_amount: function (frm, cdt, cdn) {
        calculate_row_amount(frm, cdt, cdn);
    },
    retention_percent: function (frm, cdt, cdn) {
        calculate_row_amount(frm, cdt, cdn);
    },
    amount: function (frm, cdt, cdn) {
        calculate_totals(frm);
    },
    retention_items_remove: function (frm) {
        calculate_totals(frm);
    }
});

// ฟังก์ชันคำนวณ Due Date จาก Credit Day (Posting Date + Credit Day)
function calculate_due_date(frm) {
    if (frm.doc.posting_date) {
        let days = flt(frm.doc.credit_day || 0); // ใช้ 0 หากไม่มีค่า
        let new_due_date = frappe.datetime.add_days(frm.doc.posting_date, days);
        frm.set_value('due_date', new_due_date);
    }
}

// ฟังก์ชันสร้าง Payment Entry
function create_payment_entry(frm) {
    let allowed_accounts = null;

    const dialog = new frappe.ui.Dialog({
        title: __('Create Payment'),
        fields: [
            {
                label: 'Mode of Payment',
                fieldname: 'mode_of_payment',
                fieldtype: 'Link',
                options: 'Mode of Payment',
                reqd: 1,
                change: function () {
                    let mop = dialog.get_value('mode_of_payment');
                    dialog.set_value('account', ''); 

                    if (mop) {
                        allowed_accounts = [];
                        frappe.call({
                            method: 'frappe.client.get',
                            args: { doctype: 'Mode of Payment', name: mop },
                            callback: function (r) {
                                if (r.message && r.message.accounts) {
                                    let valid_rows = r.message.accounts.filter(d => d.company === frm.doc.company);
                                    allowed_accounts = valid_rows.map(d => d.default_account);
                                    if (allowed_accounts.length === 1) {
                                        dialog.set_value('account', allowed_accounts[0]);
                                    }
                                }
                            }
                        });
                    } else {
                        allowed_accounts = null;
                    }
                }
            },
            {
                label: 'Account',
                fieldname: 'account',
                fieldtype: 'Link',
                options: 'Account',
                reqd: 1,
                get_query: function () {
                    let filters = {
                        'company': frm.doc.company,
                        'is_group': 0
                    };
                    if (allowed_accounts !== null) {
                        if (allowed_accounts.length > 0) {
                            filters['name'] = ['in', allowed_accounts];
                        } else {
                            filters['name'] = '#######';
                        }
                    }
                    return { filters: filters };
                }
            }
        ],
        primary_action_label: __('Create Journal Entry'),
        primary_action: function (values) {
            frappe.call({
                method: 'consbiz.consbiz.doctype.retention_invoice.retention_invoice.create_payment_entry',
                args: {
                    docname: frm.doc.name,
                    mode_of_payment: values.mode_of_payment,
                    account: values.account
                },
                freeze: true,
                callback: function (r) {
                    if (r.message) {
                        dialog.hide();
                        frappe.model.sync(r.message);
                        frappe.set_route('Form', 'Journal Entry', r.message.name);
                    }
                }
            });
        }
    });

    dialog.show();
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

    let filters = [
        ['customer', '=', frm.doc.customer],
        ['docstatus', '=', 1],
        ['status', 'in', ['Active', 'Overdue']]
    ];
    if (frm.doc.company) filters.push(['company', '=', frm.doc.company]);
    if (frm.doc.project) filters.push(['project', '=', frm.doc.project]);
    if (frm.doc.customer_po) filters.push(['customer_po', '=', frm.doc.customer_po]); 

    frappe.call({
        method: 'frappe.client.get_list',
        args: {
            doctype: 'Retention Receivable',
            filters: filters,
            fields: ['name']
        },
        callback: function (r) {
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

    let filters = {
        'customer': frm.doc.customer,
        'docstatus': 1,
        'status': ['in', ['Active', 'Overdue']]
    };
    if (frm.doc.company) filters['company'] = frm.doc.company;
    if (frm.doc.project) filters['project'] = frm.doc.project;
    
    // --- Filter Customer PO ---
    if (frm.doc.customer_po) {
        filters['customer_po'] = frm.doc.customer_po;
    }

    new frappe.ui.form.MultiSelectDialog({
        doctype: "Retention Receivable",
        target: frm,
        setters: {
            customer: frm.doc.customer,
            company: frm.doc.company,
            project: frm.doc.project
        },
        add_filters_group: 1,
        get_query: function () {
            return { filters: filters };
        },
        action: function (selections) {
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
        if (d.reference_no) existing_keys.push(d.reference_no);
        if (d.sales_invoice) existing_keys.push(d.sales_invoice);
        if (d.purchase_invoice) existing_keys.push(d.purchase_invoice);
        if (d.supplier_invoice) existing_keys.push(d.supplier_invoice);
    });

    parent_names.forEach(parent_name => {
        frappe.call({
            method: 'frappe.client.get',
            args: {
                doctype: 'Retention Receivable',
                name: parent_name
            },
            callback: function (r) {
                if (r.message) {
                    let parent_doc = r.message;
                    let source_items = parent_doc[TABLE_FIELD_NAME] || [];

                    source_items.forEach(item => {
                        let is_duplicate = false;
                        if (item.reference_no && existing_keys.includes(item.reference_no)) is_duplicate = true;
                        if (item.sales_invoice && existing_keys.includes(item.sales_invoice)) is_duplicate = true;
                        if (item.purchase_invoice && existing_keys.includes(item.purchase_invoice)) is_duplicate = true;
                        if (item.supplier_invoice && existing_keys.includes(item.supplier_invoice)) is_duplicate = true;
                        if (parent_doc.name && existing_keys.includes(parent_doc.name)) is_duplicate = true;

                        if (!is_duplicate) {
                            let row = frappe.model.add_child(frm.doc, target_child_doctype, TABLE_FIELD_NAME);

                            row.posting_date = item.posting_date;
                            row.due_date = item.due_date;
                            row.reference_no = parent_doc.name; 
                            row.sales_invoice = item.sales_invoice_no || item.sales_invoice; 
                            row.purchase_invoice = item.purchase_invoice;
                            row.supplier_invoice = item.supplier_invoice;
                            row.description = item.description;
                            row.base_amount = item.base_amount;
                            row.retention_percent = item.retention_percent;
                            row.amount = item.amount;

                            if (parent_doc.name) existing_keys.push(parent_doc.name);
                            if (item.sales_invoice_no) existing_keys.push(item.sales_invoice_no);

                            added_count++;
                        }
                    });
                }

                processed_count++;
                if (processed_count === parent_names.length) {
                    frm.refresh_field(TABLE_FIELD_NAME);
                    calculate_totals(frm);

                    if (added_count > 0) {
                        frappe.show_alert({ message: __('เพิ่มรายการใหม่ ' + added_count + ' รายการ'), indicator: 'green' });
                    } else {
                        frappe.show_alert({ message: __('ไม่มีรายการใหม่ หรือรายการซ้ำกันทั้งหมด'), indicator: 'orange' });
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

    frm.set_value('grand_total', total_amount);

    if (frm.fields_dict['in_words']) {
        let text_val = total_amount !== 0 ?
            (total_amount > 0 ? thai_baht_text(total_amount) : 'ติดลบ' + thai_baht_text(Math.abs(total_amount))) : 'ศูนย์บาทถ้วน';
        frm.set_value('in_words', text_val);
    }
}