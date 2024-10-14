import logging

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class CalendarEvent(models.Model):
    _inherit = "calendar.event"

    timesheet_ids = fields.One2many(
        "account.analytic.line", "calendar_event_id", string="Timesheets"
    )
    project_id = fields.Many2one("project.project", string="Project")
    task_id = fields.Many2one("project.task", string="Task")

    @api.onchange('project_id', 'task_id')
    def _onchange_timesheet_data(self):
        if self.project_id.analytic_account_id.code and self.task_id.type_id.code:
            self.name = '[%s/%s] ' %(self.project_id.analytic_account_id.code, self.task_id.type_id.code) + self.name[
                self.name.find("]") + 1 :
            ].lstrip()
        elif self.project_id.analytic_account_id.code:
            self.name = '[%s] ' % self.project_id.analytic_account_id.code + self.name[
                self.name.find("]") + 1 :
            ].lstrip()
        else:
            self.task_id = False
            self.name = self.name[
                self.name.find("]") + 1 :
            ].lstrip()