import frappe
from frappe.custom.doctype.property_setter.property_setter import make_property_setter

def execute():
    doctype = "Journal Entry Account"
    fieldname = "reference_type"
    
    # 1. Get the field to check its current valid options
    docfield = frappe.db.get_value("DocField", {"parent": doctype, "fieldname": fieldname}, "options")
    
    # Fallback to defaults if custom field not used, but DocField options should be there
    if not docfield:
        # Maybe it's a hardcoded standard field and not in DocField (some older versions)? 
        # But 'make_property_setter' should work anyway.
        # Let's check meta
        meta = frappe.get_meta(doctype)
        field = meta.get_field(fieldname)
        if field and field.fieldtype == "Select":
            docfield = field.options
    
    current_options = docfield or ""
    
    if "Retention Invoice" in current_options:
        print("Retention Invoice is already in options.")
        return

    # 2. Add New Option
    new_options = current_options + "\nRetention Invoice"
    
    # 3. Create Property Setter
    # Check if PS exists
    ps_exists = frappe.db.exists("Property Setter", {
        "doc_type": doctype,
        "field_name": fieldname,
        "property": "options"
    })

    if ps_exists:
        ps = frappe.get_doc("Property Setter", ps_exists)
        ps.value = new_options
        ps.module = "ConsBiz" # Force module
        ps.save()
        print(f"Updated existing Property Setter for {fieldname}")
    else:
        make_property_setter(doctype, fieldname, "options", new_options, "Select", for_doctype=False)
        
        # Update Module for the newly created PS
        new_ps = frappe.db.get_value("Property Setter", {
            "doc_type": doctype,
            "field_name": fieldname,
            "property": "options"
        })
        if new_ps:
            frappe.db.set_value("Property Setter", new_ps, "module", "ConsBiz")
            
        print(f"Created new Property Setter for {fieldname}")

    frappe.db.commit()
