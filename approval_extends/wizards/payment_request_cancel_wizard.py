from odoo import api, Command, fields, models, _

class PaymentRequestCancelWizard(models.TransientModel):
    _name = 'payment.request.cancel.wizard'
    _description = "Payment Request Cancel Wizard"

    is_payment_request_cancel = fields.Boolean(string="Cancel Payment Request")
    move_id = fields.Many2one('account.move', string="Bill")
    approval_payment_request_id = fields.Many2one('approval.payment.request', string="Payment Request")

    def action_cancel_bill(self):
        if self.is_payment_request_cancel:
            self.approval_payment_request_id.is_payment_request_cancel = True
            self.move_id.is_payment_request_cancel = True
       
        return self.move_id.button_cancel()