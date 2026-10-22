import frappe


def execute():
	"""Drop the consbiz Dock that was created on the server under a hash name.

	The app now ships its dock as `consbiz/dock/consbiz/consbiz.json` (record name `consbiz`).
	A site can hold only one standard dock per app, so the old row blocks that import.
	Its two items are the same ones the file brings back.
	"""
	if not frappe.db.table_exists("Dock"):
		return

	names = frappe.get_all("Dock", filters={"app": "consbiz", "standard": 1, "name": ("!=", "consbiz")}, pluck="name")
	if not names:
		return

	frappe.db.delete("Dock Item", {"parenttype": "Dock", "parent": ("in", names)})
	frappe.db.delete("Dock", {"name": ("in", names)})
