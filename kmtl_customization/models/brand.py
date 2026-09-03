from odoo import fields, models, api
from odoo.exceptions import UserError

class PurchaseBrand(models.Model):
    _name = "purchase.brand"
    _description = 'Brand'   

    code = fields.Char(string="Code")
    name = fields.Char(string="Name")
    remark = fields.Char(string="Remark")