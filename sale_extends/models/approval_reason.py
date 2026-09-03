from odoo import api, fields, models, SUPERUSER_ID, _

class ApprovalReason(models.Model):
    _name = 'approval.reason'
    _description = 'Approval Reason'
    
    so_id = fields.Many2one('sale.order', string="Sale Order")
    reason = fields.Char(string="Reason")
    state = fields.Selection([('submitted', 'Submitted'), 
                                       ('re-submitted', 'Re-Submitted'), 
                                       ('approved', 'Approved'),
                                       ('rejected', 'Rejected')], default='')  