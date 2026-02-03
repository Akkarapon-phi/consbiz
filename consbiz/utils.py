import frappe
from frappe.utils import getdate

def parse_naming_series_variable(doc, variable):
    if variable == "ABBR":
        if doc and doc.get("company"):
            return frappe.get_cached_value('Company', doc.company, 'abbr')
        return frappe.defaults.get_global_default("company_abbr") or "X"