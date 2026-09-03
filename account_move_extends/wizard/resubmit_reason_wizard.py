from odoo import fields, api, models, _

class RejectReason(models.TransientModel):
    _name = 'wizard.invoice.resubmit.reason'   
    _description ="Wizard Resubmit Reason"

    invoice_id = fields.Many2one('account.move', string='Invoice', required=True)
    resubmit_reason = fields.Char(string="Resubmit Reason")    
        
    def action_confirm(self):
        self.invoice_id.approval_state = 're-submitted'
        self.env['invoice.approval.reason'].create({
            'invoice_id': self.invoice_id.id,
            'reason': self.resubmit_reason,
            'state': 're-submitted'
        })
        if self.invoice_id.approved_by_id:
            to_approver = self.invoice_id.approved_by_id.id
            self.invoice_id.activity_schedule('account_move_extends.mail_activity_data_account_kmtl',
                                        user_id=to_approver)