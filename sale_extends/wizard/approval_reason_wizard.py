from odoo import fields, api, models, _

class ApprovalReason(models.TransientModel):
    _name = 'wizard.approval.reason'   
    _description ="Wizard Approval Reason"

    sale_order_id = fields.Many2one('sale.order', string='Sale order', required=True)
    state = fields.Selection([('submitted', 'Submitted'), 
                                       ('re-submitted', 'Re-Submitted'), 
                                       ('approved', 'Approved'),
                                       ('rejected', 'Rejected')], default='')  
    reason = fields.Text(string="Reason")    
    
    #2nd time remove    
    # def _get_user_approval_activities(self, user):
    #     domain = [
    #         ('res_model', '=', 'sale.order'),
    #         ('res_id', 'in', self.sale_order_id.ids),
    #         ('activity_type_id', '=', self.env.ref('approvals.mail_activity_data_approval').id),
    #         ('user_id', '=', user.id)
    #     ]
    #     activities = self.env['mail.activity'].search(domain)
    #     return activities
        
    def action_confirm(self):
        self.sale_order_id.approval_state = self.state
        self.env['approval.reason'].create({
            'so_id': self.sale_order_id.id,
            'reason': self.reason,
            'state': self.state
        })
        if self.state == 're-submitted':
            self.sale_order_id.action_submit()
        #2nd time remove
        # if self.state == 'approved':
        #     self.sale_order_id.sudo().write({'state': 'sale'})
        self.sudo().sale_order_id._get_user_approval_activities(user=self.env.user).action_feedback()        