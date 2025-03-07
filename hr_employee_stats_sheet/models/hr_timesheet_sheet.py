from datetime import timedelta

from odoo import _, api, fields, models


class HrTimesheetSheet(models.Model):
    _inherit = "hr_timesheet.sheet"

    employee_stats_ids = fields.One2many(
        "hr.employee.stats", "sheet_id", "Employee Stats"
    )
    total_recovery_hours = fields.Float(
        compute="_compute_total_recovery_hours", string="Total Recovery Hours"
    )

    def search_and_create_employee_stats(self):
        for sheet in self:
            if sheet.employee_id:
                for day in range((sheet.date_end - sheet.date_start).days + 1):
                    date = sheet.date_start + timedelta(days=day)
                    stats = self.env["hr.employee.stats"].search(
                        [
                            ("employee_id", "=", sheet.employee_id.id),
                            ("date", "=", date),
                        ]
                    )
                    if stats and not stats.sheet_id:
                        stats.write({"sheet_id": sheet.id})
                    if not stats:
                        self.env["hr.employee.stats"].create(
                            {
                                "employee_id": sheet.employee_id.id,
                                "date": date,
                                "sheet_id": sheet.id,
                                "company_id": sheet.company_id.id,
                            }
                        )
        return True

    @api.model
    def create(self, vals):
        res = super().create(vals)
        res.search_and_create_employee_stats()
        return res

    def write(self, vals):
        res = super().write(vals)
        if "date_end" in vals or "date_start" in vals or "employee_id" in vals:
            self.search_and_create_employee_stats()
        return res

    def unlink(self):
        for sheet in self:
            sheet.employee_stats_ids.unlink()
        return super().unlink()

    @api.depends("employee_stats_ids.gap_hours", "employee_id")
    def _compute_total_recovery_hours(self):
        recovery_type_id = self.env.company.recovery_type_id
        for sheet in self:
            recovery_ids = self.env["hr.leave"].search(
                [
                    ("holiday_status_id", "=", recovery_type_id.id),
                    ("employee_id", "=", sheet.employee_id.id),
                ]
            )
            recovery_allocation_ids = self.env["hr.leave.allocation"].search(
                [
                    ("holiday_status_id", "=", recovery_type_id.id),
                    ("employee_id", "=", sheet.employee_id.id),
                ]
            )
            total_allocation_ids = sum(
                recovery_allocation_ids.mapped("number_of_hours_display")
            )
            total_recovery_ids = sum(recovery_ids.mapped("number_of_hours_display"))
            sheet.total_recovery_hours = total_allocation_ids + total_recovery_ids + sum(
                sheet.employee_stats_ids.filtered(
                    lambda stat: stat.date <= fields.Date.today()
                ).mapped("gap_hours")
            )
