from odoo import fields, models, api
from odoo.exceptions import UserError

class CrmLead(models.Model):
    _name = "crm.industry"
    _description = 'Industry set up for crm'   

    code = fields.Char(string="Industry Code")
    name = fields.Char(string="Name")
    remark = fields.Char(string="Remark")
