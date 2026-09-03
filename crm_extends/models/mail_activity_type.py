from odoo import api, fields, models


class MailActivityType(models.Model):
    _inherit = 'mail.activity.type'

    is_follow_up_activity = fields.Boolean(string="Follow-up Activity", default=False)
    follow_up_message = fields.Char(string="Follow-up Message")