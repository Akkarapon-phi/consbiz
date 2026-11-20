# Copyright (c) 2026, Siricons and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class EmploymentContract(Document):
	def validate(self):
		from consbiz.contract_terms import unknown_variables

		unknown = unknown_variables(self.terms)
		if unknown:
			frappe.throw(_("ไม่รู้จักตัวแปรในเนื้อหาสัญญา: {0}").format(", ".join(unknown)))
