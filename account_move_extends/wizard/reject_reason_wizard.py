from odoo import fields, api, models, _

class RejectReason(models.TransientModel):
    _name = 'wizard.invoice.reject.reason'   
    _description ="Wizard Reject Reason"

    invoice_id = fields.Many2one('account.move', string='Invoice', required=True)
    reject_reason = fields.Char(string="Reject Reason")    
        
    def action_confirm(self):
        self.invoice_id.approval_state = 'rejected'
        self.env['invoice.approval.reason'].create({
            'invoice_id': self.invoice_id.id,
            'reason': self.reject_reason,
            'state': 'rejected'
        })
        