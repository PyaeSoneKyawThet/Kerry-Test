from odoo import api, fields, models, _
from odoo.exceptions import UserError

class PurchaseApprovalConfig(models.Model):
    _name = 'purchase.approval.config'
    _description = "Purchase Approval Config"
    
    name = fields.Char(string="Name")
    sequence = fields.Integer(string="Sequence")

    from_amount = fields.Float(string="From Amount")
    to_amount = fields.Float(string="To Amount")
    currency_id = fields.Many2one('res.currency', string="Currency")
     
    from_level = fields.Integer(string="From Level", default=1)
    to_level = fields.Integer(string="To Level", default=1) 
    
    need_approval = fields.Boolean(string="Need Approval", default=True)