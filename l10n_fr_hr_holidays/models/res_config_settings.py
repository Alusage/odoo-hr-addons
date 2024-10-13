# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_fr_reference_leave_type = fields.Many2one(
        'hr.leave.type',
        related='company_id.l10n_fr_reference_leave_type',
        readonly=False)

    # backport from V170
    company_country_code = fields.Char(related="company_id.country_id.code", string="Company Country Code", readonly=True)
    