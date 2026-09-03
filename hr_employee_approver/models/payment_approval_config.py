from odoo import api, fields, models, _
from odoo.exceptions import UserError

class PaymentApprovalConfig(models.Model):
    _name = 'payment.approval.config'
    _description = "Payment Approval Config"

    name = fields.Char(string="Name")
    sequence = fields.Integer(string="Sequence")
    from_amount = fields.Float(string="From Amount")
    to_amount = fields.Float(string="To Amount")
    currency_id = fields.Many2one('res.currency', string="Currency")    
    from_level = fields.Integer(string="From Level", default=1)
    to_level = fields.Integer(string="To Level", default=1)   
    need_approval = fields.Boolean(string="Need Approval", default=True)
    account_payment_type_ids = fields.Many2many('account.payment.type', string="Type")
    payment_type = fields.Selection([
                                    ('supplier_pay', 'Vendor Payment'),
                                    ('customer_pay', 'Customer Payment')
                                    ], string="Payment Type", default="supplier_pay")