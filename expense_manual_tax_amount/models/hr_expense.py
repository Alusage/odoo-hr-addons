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

    def _get_account_move_line_values(self):
        move_line_values_by_expense = {}
        for expense in self:
            move_line_name = expense.employee_id.name + ': ' + expense.name.split('\n')[0][:64]
            account_src = expense._get_expense_account_source()
            account_dst = expense._get_expense_account_destination()
            account_date = expense.sheet_id.accounting_date or expense.date or fields.Date.context_today(expense)

            company_currency = expense.company_id.currency_id

            move_line_values = []
            taxes = expense.tax_ids.with_context(round=True).compute_all(expense.unit_amount, expense.currency_id, expense.quantity, expense.product_id)
            if expense.force_tax_amount:
                taxes['total_excluded'] = expense.total_amount - expense.manual_tax_amount
                taxes['total_included'] = expense.total_amount
                taxes['total_void'] = expense.total_amount - expense.manual_tax_amount
            total_amount = 0.0
            total_amount_currency = 0.0
            partner_id = expense.employee_id.sudo().address_home_id.commercial_partner_id.id

            # source move line
            balance = expense.currency_id._convert(taxes['total_excluded'], company_currency, expense.company_id, account_date)
            amount_currency = taxes['total_excluded']
            move_line_src = {
                'name': move_line_name,
                'quantity': expense.quantity or 1,
                'debit': balance if balance > 0 else 0,
                'credit': -balance if balance < 0 else 0,
                'amount_currency': amount_currency,
                'account_id': account_src.id,
                'product_id': expense.product_id.id,
                'product_uom_id': expense.product_uom_id.id,
                'analytic_account_id': expense.analytic_account_id.id,
                'analytic_tag_ids': [(6, 0, expense.analytic_tag_ids.ids)],
                'expense_id': expense.id,
                'partner_id': partner_id,
                'tax_ids': [(6, 0, expense.tax_ids.ids)],
                'tax_tag_ids': [(6, 0, taxes['base_tags'])],
                'currency_id': expense.currency_id.id,
            }
            move_line_values.append(move_line_src)
            total_amount -= balance
            total_amount_currency -= move_line_src['amount_currency']

            # taxes move lines
            if expense.force_tax_amount:
                balance = expense.currency_id._convert(expense.manual_tax_amount, company_currency, expense.company_id, account_date)
                amount_currency = expense.manual_tax_amount
                move_line_tax_values = {
                    'name': move_line_name,
                    'quantity': 1,
                    'debit': balance if balance > 0 else 0,
                    'credit': -balance if balance < 0 else 0,
                    'amount_currency': amount_currency,
                    'account_id': taxes['taxes'][0]['account_id'] or move_line_src['account_id'],
                    'expense_id': expense.id,
                    'partner_id': partner_id,
                    'tax_ids': [(6, 0, expense.tax_ids.ids)],
                    'tax_tag_ids': [(6, 0, taxes['taxes'][0]['tag_ids'])],
                    'currency_id': expense.currency_id.id,
                    'analytic_account_id': expense.analytic_account_id.id,
                    'analytic_tag_ids': [(6, 0, expense.analytic_tag_ids.ids)],
                }
                move_line_values.append(move_line_tax_values)
                total_amount -= balance
                total_amount_currency += move_line_tax_values['amount_currency']


            else:
                for tax in taxes['taxes']:
                    balance = expense.currency_id._convert(tax['amount'], company_currency, expense.company_id, account_date)
                    amount_currency = tax['amount']

                    if tax['tax_repartition_line_id']:
                        rep_ln = self.env['account.tax.repartition.line'].browse(tax['tax_repartition_line_id'])
                        base_amount = self.env['account.move']._get_base_amount_to_display(tax['base'], rep_ln)
                        base_amount = expense.currency_id._convert(base_amount, company_currency, expense.company_id, account_date)
                    else:
                        base_amount = None

                    move_line_tax_values = {
                        'name': tax['name'],
                        'quantity': 1,
                        'debit': balance if balance > 0 else 0,
                        'credit': -balance if balance < 0 else 0,
                        'amount_currency': amount_currency,
                        'account_id': tax['account_id'] or move_line_src['account_id'],
                        'tax_repartition_line_id': tax['tax_repartition_line_id'],
                        'tax_tag_ids': tax['tag_ids'],
                        'tax_base_amount': base_amount,
                        'expense_id': expense.id,
                        'partner_id': partner_id,
                        'currency_id': expense.currency_id.id,
                        'analytic_account_id': expense.analytic_account_id.id if tax['analytic'] else False,
                        'analytic_tag_ids': [(6, 0, expense.analytic_tag_ids.ids)] if tax['analytic'] else False,
                    }
                    total_amount -= balance
                    total_amount_currency -= move_line_tax_values['amount_currency']
                    move_line_values.append(move_line_tax_values)

            # destination move line
            move_line_dst = {
                'name': move_line_name,
                'debit': total_amount > 0 and total_amount,
                'credit': total_amount < 0 and -total_amount,
                'account_id': account_dst,
                'date_maturity': account_date,
                'amount_currency': total_amount_currency,
                'currency_id': expense.currency_id.id,
                'expense_id': expense.id,
                'partner_id': partner_id,
            }

            move_line_values.append(move_line_dst)

            move_line_values_by_expense[expense.id] = move_line_values
        return move_line_values_by_expense