from odoo import _, api, fields, models


class HrAttendance(models.Model):
    _inherit = "hr.attendance"

    transport = fields.Boolean("Transport", default=False)
    note = fields.Char("Note")
    lunch_paid_company = fields.Boolean("Lunch paid by company", default=False)