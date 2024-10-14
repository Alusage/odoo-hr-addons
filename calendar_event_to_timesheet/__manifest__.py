{
    "name": "Calendar event to timesheet",
    "version": "16.0.1.0.1",
    "description": "Calendar event to timesheet",
    "summary": "Calendar event to timesheet",
    "author": "Nicolas JEUDY",
    "website": "https://github.com/Alusage/odoo-hr-addons",
    "license": "LGPL-3",
    "category": "Human Resources",
    "depends": ["base", "calendar", "hr_timesheet", "project_type"],
    "data": [
        "views/calendar_event_view.xml",
        "data/actions.xml",
    ],
    "installable": True,
    "application": False,
}
