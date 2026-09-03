from odoo import fields, models, api
from odoo.exceptions import UserError

class CrmLead(models.Model):
    _name = "crm.unit"
    _description = 'Unit set up for crm'   

    code = fields.Char(string="Unit Code")
    name = fields.Char(string="Name")
    remark = fields.Char(string="Remark")
