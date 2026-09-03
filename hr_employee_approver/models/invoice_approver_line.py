from odoo import api, fields, models, _
from odoo.exceptions import UserError

class InvoiceApproverLine(models.Model):
    _name = 'invoice.approver.line'
    _description = "Invoice Approver Line"
    
    employee_id = fields.Many2one('hr.employee', string='Employee')
    approval_user_ids = fields.Many2many('res.users', string="Approvers")
    approval_employee_id = fields.Many2one('res.users',string="Approver",
                                           default=lambda self: self.env.user)
    approver_type = fields.Selection([('approver', 'Approver'), ('checker', 'Checker')])
    sequence = fields.Integer(default=1)
    account_move_id = fields.Many2one('account.move', string="Invoice",
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
    
    @api.onchange('approval_user_ids')
    def onchange_approval_user_ids(self):
        for rec in self:
            app_user_len = len(rec.approval_user_ids)
            if app_user_len > 0:
                rec.approval_employee_id = rec.approval_user_ids[app_user_len-1]
    
    def _create_activity(self):
        for inv_approver in self:
            for user in inv_approver.approval_user_ids:
                inv_approver.account_move_id.activity_schedule(
                    'account_move_extends.mail_activity_data_account_move_kmtl',
                    user_id=user.id
                )