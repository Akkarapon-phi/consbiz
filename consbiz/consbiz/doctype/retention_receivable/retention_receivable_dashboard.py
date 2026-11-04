from frappe import _


def get_data():
	return {
		"fieldname": "retention_reference",
		"internal_links": {"Sales Invoice": ["retention_items", "sales_invoice_no"]},
		"transactions": [
			{"label": _("Reference"), "items": ["Sales Invoice"]},
			{"label": _("Retention Claim"), "items": ["Retention Invoice"]},
		],
	}
