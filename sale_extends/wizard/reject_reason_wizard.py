from odoo import fields, api, models, _

class RejectReason(models.TransientModel):
    _name = 'wizard.reject.reason'   
    _description ="Wizard Reject Reason"

    sale_order_id = fields.Many2one('sale.order', string='Sale order', required=True)
    reject_reason = fields.Text(string="Reject Reason")    
        
    def action_confirm(self):
        self.sale_order_id.write({
            'reject_reason': self.reject_reason,
            'approval_state': 'rejected'           
        })