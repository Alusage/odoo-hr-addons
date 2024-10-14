import logging

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class AnalyticAccountLine(models.Model):
    _inherit = "account.analytic.line"

    calendar_event_id = fields.Many2one(
        "calendar.event", string="Calendar Event", ondelete="set null"
    )

    def _prepare_timesheet(self, calendar_event):
        project_id = False
        task_id = False
        event_name = calendar_event.name[
            calendar_event.name.find("[") + 1 : calendar_event.name.find("]")
        ]
        _logger.info(
            "Calendar event name: %s (find: %s)" % (calendar_event.name, event_name)
        )
        if event_name:
            try:
                project_code, task_type = event_name.split("/")
                project_id = self.env["project.project"].search(
                    [("analytic_account_id.code", "=", project_code)]
                )
                task_id = self.env["project.task"].search(
                    [
                        ("project_id", "=", project_id.id),
                        ("user_ids", "in", [self.env.user.id]),
                        ("type_id.code", "=", task_type),
                    ]
                )
            except Exception as e:
                project_code = event_name
                project_id = self.env["project.project"].search(
                    [("analytic_account_id.code", "=", project_code)]
                )

        return {
            "name": calendar_event.name,
            "unit_amount": calendar_event.duration,
            "employee_id": self.env.user.employee_id.id,
            "date": calendar_event.start.date(),
            "calendar_event_id": calendar_event.id,
            "account_id": project_id.analytic_account_id.id,
            "project_id": project_id.id if project_id else 2,
            "task_id": task_id.id if task_id else False,
        }

    def _create_timesheets(self):
        timesheet_model = self.env["account.analytic.line"]
        my_events = self.env["calendar.event"].search(
            [
                ("partner_ids.user_ids", "in", [self.env.user.id]),
                ("start", "<=", fields.Datetime.now()),
            ]
        )
        for event in my_events:
            if not event.timesheet_ids.filtered(
                lambda ts: ts.employee_id.user_id == self.env.user
            ):
                vals = timesheet_model._prepare_timesheet(event)
                timesheet_model.create(vals)
        return True
