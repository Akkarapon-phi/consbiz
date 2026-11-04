from frappe import _


def get_data():
	return {
		"fieldname": "retention_reference",
		"internal_links": {"Purchase Invoice": ["retention_items", "purchase_invoice_no"]},
		"transactions": [
			{"label": _("Reference"), "items": ["Purchase Invoice"]},
			{"label": _("Retention Claim"), "items": ["Retention Release"]},
		],
	}
