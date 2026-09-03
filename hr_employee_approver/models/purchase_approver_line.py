from odoo import api, fields, models, _
from odoo.exceptions import UserError

class PurchaseApproverLine(models.Model):
    _name = 'purchase.approver.line'
    _description = "Purchase Approver Line"
    
    employee_id = fields.Many2one('hr.employee', string='Employee')
    approval_user_ids = fields.Many2many('res.users', string="Approvers")
    approval_employee_id = fields.Many2one('res.users',string="Approver",
                                           default=lambda self: self.env.user)
    approver_type = fields.Selection([('approver', 'Approver'), ('checker', 'Checker')])
    sequence = fields.Integer(default=1)
    purchase_id = fields.Many2one('purchase.order', string="Purchase Order",
        ondelete='cascade', check_company=True)
    
    status = fields.Selection([
        ('new', 'New'),
        ('to_check', 'To Check'), 
        ('checked', 'Checked'),
        ('pending', 'To Approve'), 
        ('waiting', 'Waiting'),
        ('approved', 'Approved'),
        ('refused', 'Refused'),
        ('cancel', 'Cancel')], string="Status", default="new", readonly=True) 
    
    def _create_activity(self):
        for po_approver in self:
            for user in po_approver.approval_user_ids:
                po_approver.purchase_id.activity_schedule(
                    'purchase_extends.mail_activity_data_purchase_kmtl',
                    user_id=user.id
                )
    