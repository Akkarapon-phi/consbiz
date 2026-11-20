# Copyright (c) 2026, Siricons and contributors
# For license information, please see license.txt

"""แม่แบบสัญญาจ้าง: ตัวแปรและการแทนค่าอยู่ consbiz/contract_terms.py (ใช้ทั้ง Print Format และตัวอย่างในแอป)"""

import frappe
from frappe import _
from frappe.model.document import Document


class EmploymentContractTemplate(Document):
	def validate(self):
		from consbiz.contract_terms import unknown_variables

		unknown = unknown_variables(self.terms)
		if unknown:
			frappe.throw(_("ไม่รู้จักตัวแปร: {0}").format(", ".join(unknown)))
		if self.is_default:
			self.disabled = 0
			# แม่แบบเริ่มต้นมีได้อันเดียวต่อบริษัท (ว่าง = ทุกบริษัท)
			for name in frappe.get_all(
				"Employment Contract Template",
				filters={"is_default": 1, "name": ("!=", self.name), "company": self.company or ("is", "not set")},
				pluck="name",
			):
				frappe.db.set_value("Employment Contract Template", name, "is_default", 0)
