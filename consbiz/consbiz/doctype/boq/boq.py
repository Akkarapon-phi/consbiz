# Copyright (c) 2026, Siricons and contributors
# For license information, please see license.txt

from frappe.model.document import Document
from frappe.utils import flt


class BOQ(Document):
	def validate(self):
		self.calculate_totals()

	def calculate_totals(self):
		self.total_material_cost = self.total_labour_cost = self.grand_total = 0
		for row in self.boq_details:
			calculate_row(row)
			self.total_material_cost += row.material_amount
			self.total_labour_cost += row.labour_amount
			self.grand_total += row.total_amount


def calculate_row(row):
	row.material_amount = flt(row.quantity) * flt(row.material_rate)
	row.labour_amount = flt(row.quantity) * flt(row.labour_rate)
	row.total_amount = row.material_amount + row.labour_amount
