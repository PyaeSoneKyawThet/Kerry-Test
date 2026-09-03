from odoo import fields, api, models, _

class ReviseReason(models.TransientModel):
    _name = 'wizard.revise.reason'   
    _description ="Wizard Revise Reason"

    sale_order_id = fields.Many2one('sale.order', string='Sale order', required=True)
    state = fields.Selection([('revise_requested', 'Requested'), 
                            ('revise_approved', 'Revised'), 
                            ('revise_rejected', 'Rejected')], default='') 
    reason = fields.Text(string="Reason")    
    
    def action_confirm(self):
        self.sale_order_id.revise_state = self.state
        self.env['revise.reason'].create({
            'so_id': self.sale_order_id.id,
            'reason': self.reason,
            'state': self.state
        }) 
        if self.state == 'revise_requested':
            if self.sale_order_id.prepared_by_id and self.sale_order_id.prepared_by_id.employee_id.quotation_approver_id:
                to_approver = self.sale_order_id.prepared_by_id.employee_id.quotation_approver_id.id
                self.sale_order_id.activity_schedule('account_move_extends.mail_activity_data_account_kmtl',
                                        user_id=to_approver)  
