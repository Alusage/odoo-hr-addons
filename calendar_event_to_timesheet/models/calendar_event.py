import logging

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class CalendarEvent(models.Model):
    _inherit = "calendar.event"

    timesheet_ids = fields.One2many(
        "account.analytic.line", "calendar_event_id", string="Timesheets"
    )
