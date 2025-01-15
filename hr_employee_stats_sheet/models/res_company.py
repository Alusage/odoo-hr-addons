from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    recovery_type_id = fields.Many2one(
        "hr.leave.type", string="Leave recovery type"
    )
