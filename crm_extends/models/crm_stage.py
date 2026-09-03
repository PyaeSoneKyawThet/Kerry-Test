from odoo import api, fields, models

class Stage(models.Model):
    _inherit = "crm.stage"

    due_date = fields.Integer(string="Due Date(days)")