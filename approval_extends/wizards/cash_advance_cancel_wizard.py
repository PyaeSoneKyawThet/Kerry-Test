from odoo import api, Command, fields, models, _

class CashAdvanceCancelWizard(models.TransientModel):
    _name = 'cash.advance.cancel.wizard'
    _description = 'Cash Advance Cancel Wizard'

    is_cash_advance_cancel = fields.Boolean(string="Cancel Cash Advance")
    payment_id = fields.Many2one('account.payment', string="Payment")
    cash_advance_id = fields.Many2one('cash.advance.form', string='Cash Advance', copy=False)

    def action_cancel_payment(self):
        if self.is_cash_advance_cancel:
            self.payment_id.is_cash_advance_cancel = True
            self.cash_advance_id.is_cash_advance_cancel = True
       
        return self.payment_id.move_id.button_cancel()
