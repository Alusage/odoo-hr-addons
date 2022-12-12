import base64
import re
import logging

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class HrExpense(models.Model):
    _inherit = "hr.expense"


    force_tax_amount = fields.Boolean('Force Tax Amount')
    manual_tax_amount = fields.Monetary(
        "Taxed amount",
        digits="Product Price",
        currency_field="currency_id",
    )

    @api.depends('quantity', 'unit_amount', 'tax_ids', 'currency_id', 'force_tax_amount', 'manual_tax_amount')
    def _compute_amount(self):
        for expense in self:
            if expense.force_tax_amount:
                expense.untaxed_amount = expense.unit_amount * expense.quantity
                taxes = expense.manual_tax_amount
                expense.total_amount = taxes + expense.untaxed_amount
            else:
                super(HrExpense, self)._compute_amount()