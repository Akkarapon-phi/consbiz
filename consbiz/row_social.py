"""Frappe list metadata and comments for rows backed by readable documents."""

from collections import defaultdict

import frappe
from frappe.core.doctype.comment.comment import get_document_comments


def get_list(doctype, *, fields, **kwargs):
	rows = frappe.get_list(doctype, fields=list(dict.fromkeys([*fields, "_liked_by"])), with_comment_count=True, **kwargs)
	for row in rows:
		row.doctype = doctype
		row.setdefault("_comment_count", 0)
	return rows


def metadata(row):
	return {field: row.get(field) for field in ("doctype", "_comment_count", "_liked_by")}


def by_name(doctype, names):
	if not names or not frappe.has_permission(doctype, "read"):
		return {}
	return {
		row.name: row for row in get_list(
			doctype, filters={"name": ["in", sorted(names)]}, fields=["name"], limit_page_length=0
		)
	}


def attach(rows, doctype=None, *, doctype_field="doctype", name_field="name"):
	groups = defaultdict(list)
	for row in rows:
		if (dt := doctype or row.get(doctype_field)) and row.get(name_field):
			groups[dt].append(row)
	for dt, entries in groups.items():
		permitted = by_name(dt, {r[name_field] for r in entries})
		for row in entries:
			if (name := row[name_field]) in permitted:
				row.update(metadata(permitted[name]), docname=name)


@frappe.whitelist(methods=["GET"])
def comments(doctype: str, name: str):
	frappe.has_permission(doctype, "read", doc=name, throw=True)
	return get_document_comments(
		doctype, name,
		fields=["name", "comment_by", "comment_email", "owner", "creation", "content"],
		comment_types=["Comment"],
		order_by="creation asc, name asc",
	)
