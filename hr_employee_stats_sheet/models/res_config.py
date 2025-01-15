from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    recovery_type_id = fields.Many2one(
        "hr.leave.type",
        related="company_id.recovery_type_id",
        string="Leave recovery type",
        readonly=False,
    )
