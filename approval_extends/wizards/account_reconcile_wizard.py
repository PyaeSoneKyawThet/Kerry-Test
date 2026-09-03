from collections import defaultdict
from datetime import timedelta
from odoo import api, Command, fields, models, _
from odoo.exceptions import UserError

class AccountReconcileWizard(models.TransientModel):
    _inherit = 'account.reconcile.wizard'

    expense_id = fields.Many2one('approval.expense', string="Petty Cash")
    payment_request_id = fields.Many2one('approval.payment.request', string="Payment Request")

    @api.depends('expense_id','payment_request_id')
    def _onchange_approval_info(self):
        if self.expense_id:
            self.payment_request_id = False
        if self.payment_request_id:
            self.expense_id = False


    def create_write_off(self):
        write_off_move = super().create_write_off()
        write_off_move.sudo().write({'expense_id' : self.expense_id.id,
                                    'payment_request_id' : self.payment_request_id.id,
                                    'request_id': self.expense_id.request_id.id or self.payment_request_id.request_id.id,
                                    'staff_location_id': self.expense_id.staff_location_id.id or self.payment_request_id.staff_location_id.id, 
                                    'pay_to_id': self.expense_id.request_id.pay_to_id.id or self.payment_request_id.request_id.pay_to_id.id,
                                    'pay_to_external': self.expense_id.request_id.pay_to_external or self.payment_request_id.request_id.pay_to_external,
                                    })
        return write_off_move
