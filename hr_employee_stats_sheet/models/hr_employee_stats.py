import logging
from datetime import datetime

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class HrEmployeeStats(models.Model):
    _name = "hr.employee.stats"
    _description = "Employee Stats"
    _order = "date desc"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char("Name", compute="_compute_name", store=True)
    dayofweek = fields.Integer("Day of Week", compute="_compute_dayofweek")
    employee_id = fields.Many2one("hr.employee", "Employee", required=True)
    department_id = fields.Many2one("hr.department", "Department")
    attendance_ids = fields.One2many(
        "hr.attendance", "employee_id", "Attendances", compute="_compute_attendance_ids"
    )
    date = fields.Date("Date", required=True)
    company_id = fields.Many2one(
        "res.company",
        "Company",
        default=lambda self: self.env.company,
        required=True,
    )
    sheet_id = fields.Many2one("hr_timesheet.sheet", "Timesheet")
    total_hours_at = fields.Float(
        "Total Hours with transport", compute="_compute_hours"
    )
    total_hours_ht = fields.Float(
        "Total Hours without transport", compute="_compute_hours"
    )
    total_planned_hours = fields.Float("Total Planning Hours", compute="_compute_hours")
    total_leave_hours = fields.Float("Total Leave Hours", compute="_compute_hours")
    total_recovery_hours = fields.Float(
        "Total Recovery Hours", compute="_compute_hours"
    )
    gap_hours = fields.Float("Gap Hours", compute="_compute_hours")
    total_transport_hours = fields.Float(
        "Total Transport hours", compute="_compute_hours"
    )
    computed_transport_hours = fields.Float(
        "Computed Transport hours", compute="_compute_hours"
    )
    lunch_voucher = fields.Integer("Lunch Voucher", compute="_compute_hours")

    def _get_holiday_status_id(self):
        recovery_type_id = self.env.company.recovery_type_id
        if recovery_type_id:
            return recovery_type_id.id
        else:
            return False

    def _compute_attendance_ids(self):
        for stat in self:
            stat.attendance_ids = self.env["hr.attendance"].search(
                [
                    ("employee_id", "=", stat.employee_id.id),
                    ("check_in", ">=", stat.date.strftime("%Y-%m-%d 00:00:00")),
                    ("check_in", "<=", stat.date.strftime("%Y-%m-%d 23:59:59")),
                ]
            )

    def _get_intersects(
        self, datetime1_start, datetime1_end, datetime2_start, datetime2_end
    ):
        latest_start = max(datetime1_start, datetime2_start)
        earliest_end = min(datetime1_end, datetime2_end)
        delta = (earliest_end - latest_start).total_seconds() / 3600
        return max(0, delta)

    def _get_total_hours_ht(self):
        attendance = self.env["hr.attendance"]
        for stat in self:
            if stat.date and stat.employee_id:
                attendance_ids = attendance.search(
                    [
                        ("transport", "=", False),
                        ("employee_id", "=", stat.employee_id.id),
                        ("check_in", ">=", stat.date.strftime("%Y-%m-%d 00:00:00")),
                        ("check_in", "<=", stat.date.strftime("%Y-%m-%d 23:59:59")),
                    ]
                )
                total_hours_ht = sum(attendance_ids.mapped("worked_hours"))
            else:
                total_hours_ht = 0
            return total_hours_ht

    def _get_total_transport_hours(self):
        attendance = self.env["hr.attendance"]
        for stat in self:
            if stat.date and stat.employee_id:
                attendance_ids = attendance.search(
                    [
                        ("transport", "=", True),
                        ("employee_id", "=", stat.employee_id.id),
                        ("check_in", ">=", stat.date.strftime("%Y-%m-%d 00:00:00")),
                        ("check_in", "<=", stat.date.strftime("%Y-%m-%d 23:59:59")),
                    ]
                )
                total_transport_hours = sum(attendance_ids.mapped("worked_hours"))
            else:
                total_transport_hours = 0
            return total_transport_hours

    def _get_total_hours_at(self, total_hours_ht, total_transport_hours):
        for stat in self:
            if stat.date and stat.employee_id:
                total_hours_at = total_hours_ht + total_transport_hours
            else:
                total_hours_at = 0
            return total_hours_at

    def _get_total_planned_hours(self):
        for stat in self:
            if stat.employee_id and stat.date:
                dayofweek = int(stat.date.strftime("%u")) - 1
                calendar_id = stat.employee_id.resource_calendar_id
                week_number = (stat.date.isocalendar()[1] % 2)
                if calendar_id.two_weeks_calendar:
                    hours = calendar_id.attendance_ids.search(
                        [
                            ("dayofweek", "=", dayofweek),
                            ("calendar_id", "=", calendar_id.id),
                            ("week_type", "=", week_number),
                        ]
                    )
                else:
                    hours = calendar_id.attendance_ids.search(
                        [
                            ("dayofweek", "=", dayofweek),
                            ("calendar_id", "=", calendar_id.id),
                        ]
                    )
                total_planned_hours = sum(
                    hours.mapped(lambda r: r.hour_to - r.hour_from)
                )
            else:
                total_planned_hours = 0
        return total_planned_hours

    def _get_total_recovery_hours(self):
        recovery = self.env["hr.leave"]
        for stat in self:
            if stat.date and stat.employee_id and stat._get_holiday_status_id():
                recovery_ids = recovery.search(
                    [
                        ("employee_id", "=", stat.employee_id.id),
                        ("request_date_from", ">=", stat.date),
                        ("request_date_from", "<=", stat.date),
                        ("holiday_status_id", "=", stat._get_holiday_status_id()),
                    ]
                )
                total_recovery_hours = sum(
                    recovery_ids.mapped("number_of_hours_display")
                )
            else:
                total_recovery_hours = 0
            return total_recovery_hours

    def _get_lunch_voucher(self, total_hours_at):
        for stat in self:
            lunch_voucher = 0
            if stat.date and stat.employee_id:
                attendance_ids = self.env["hr.attendance"].search(
                    [
                        ("employee_id", "=", stat.employee_id.id),
                        ("check_in", ">=", stat.date.strftime("%Y-%m-%d 00:00:00")),
                        ("check_in", "<=", stat.date.strftime("%Y-%m-%d 23:59:59")),
                    ]
                )
                if total_hours_at >= 5 and not any(
                    i == True for i in attendance_ids.mapped("lunch_paid_company")
                ):
                    lunch_voucher = 1
            return lunch_voucher

    def _get_total_leave_hours(self):
        leave = self.env["hr.leave"]
        for stat in self:
            if stat.date and stat.employee_id:
                leave_ids = leave.search(
                    [
                        ("employee_id", "=", stat.employee_id.id),
                        ("holiday_status_id", "!=", stat._get_holiday_status_id()),
                        ("request_date_from", ">=", stat.date),
                        ("request_date_to", "<=", stat.date),
                    ]
                )
                intersect_hours = sum(leave_ids.mapped("number_of_hours_display"))
                for leave_id in leave_ids:
                    for attendance_id in stat.attendance_ids:
                        intersect_hours -= stat._get_intersects(
                            leave_id.date_from,
                            leave_id.date_to,
                            attendance_id.check_in,
                            attendance_id.check_out,
                        )
                total_leave_hours = intersect_hours
            else:
                total_leave_hours = 0
            return total_leave_hours

    @api.depends("employee_id", "date")
    def _compute_name(self):
        for stat in self:
            stat.name = "%s - %s" % (stat.employee_id.name, stat.date)

    @api.depends("date")
    def _compute_dayofweek(self):
        for stat in self:
            stat.dayofweek = int(stat.date.strftime("%u")) - 1

    @api.depends(
        "employee_id",
        "date",
        "total_hours_at",
        "total_hours_ht",
        "total_planned_hours",
        "attendance_ids.check_in",
        "attendance_ids.check_out",
        "attendance_ids.transport",
        "attendance_ids.lunch_paid_company",
    )
    def _compute_hours(self):
        for stat in self:
            total_hours_ht = stat._get_total_hours_ht()
            total_transport_hours = stat._get_total_transport_hours()
            computed_transport_hours = total_transport_hours
            total_recovery_hours = stat._get_total_recovery_hours()
            total_planned_hours = stat._get_total_planned_hours()
            total_leave_hours = stat._get_total_leave_hours()
            total_hours_at = stat._get_total_hours_at(
                total_hours_ht, total_transport_hours
            )
            balance = (
                total_hours_at
                + total_recovery_hours
                + total_leave_hours
                - total_planned_hours
            )

            if (
                balance < 0
                and total_transport_hours > 0
                and total_transport_hours >= balance
            ):
                computed_transport_hours = total_transport_hours + balance
            if (
                balance <= 0
                and total_transport_hours > 0
                and total_transport_hours < balance
            ):
                computed_transport_hours = 0

            stat.total_hours_ht = total_hours_ht
            stat.total_hours_at = total_hours_at
            stat.total_planned_hours = total_planned_hours
            stat.computed_transport_hours = computed_transport_hours
            stat.gap_hours = balance
            stat.total_transport_hours = total_transport_hours
            stat.total_recovery_hours = total_recovery_hours
            stat.total_leave_hours = total_leave_hours
            stat.lunch_voucher = stat._get_lunch_voucher(total_hours_at)
