from odoo import api, fields, models, SUPERUSER_ID, _ 

class ApprovalReason(models.Model):
    _name = 'invoice.approval.reason'
    _description = 'Invoice Approval Reason'
    
    invoice_id = fields.Many2one('account.move', string="Invoice")
    reason = fields.Char(string="Reason") 
    state = fields.Selection([('submitted', 'Submitted'), 
                                       ('re-submitted', 'Re-Submitted'), 
                                       ('approved', 'Approved'), 
                                       ('rejected', 'Rejected')], default='')  