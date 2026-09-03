from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

class JobLocation(models.Model):
    _name = 'job.location'
    _description = 'Job Location'

    code = fields.Char(string="Code")
    name = fields.Char(string="Name", required=True)
    remark = fields.Text(string="Remark")
