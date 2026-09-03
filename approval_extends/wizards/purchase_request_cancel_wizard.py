from odoo import api, Command, fields, models, _
from odoo.exceptions import UserError

class PurchaseRequestCancelWizard(models.TransientModel):
    _name = 'purchase.request.cancel.wizard'
    _description = "Purchase Request Cancel Wizard"

    is_request_cancel = fields.Boolean(string="Auto Cancel Purchase Request")
    approval_expense_ids = fields.Many2many('approval.expense', string="Expense")
    request_ids = fields.Many2many('approval.request', string="Approval Request")
    approval_payment_request_ids = fields.Many2many('approval.payment.request', string="Payment Request")
    cash_advance_ids = fields.Many2many('cash.advance.form', string="Cash Advance")

    def action_cancel_expense(self):
        self.approval_expense_ids._action_cancel()
        if self.is_request_cancel:
            request_cancel_expense = self.approval_expense_ids.filtered(lambda l: l.request_id in self.request_ids)
            request_cancel_expense.is_request_cancel = True
            for rec in self.request_ids:
                rec.action_cancel()

    def action_cancel_payment_request(self):
        self.approval_payment_request_ids._action_cancel()
        if self.is_request_cancel:
            request_cancel_payment = self.approval_payment_request_ids.filtered(lambda p: p.request_id in self.request_ids)
            request_cancel_payment.is_request_cancel = True
            for rec in self.request_ids:
                rec.action_cancel()

    def action_cancel_cash_advance(self):
        self.cash_advance_ids._action_cancel()
        if self.is_request_cancel:
            request_cancel_cash_advance = self.cash_advance_ids.filtered(lambda c: c.request_id in self.request_ids)
            request_cancel_cash_advance.is_request_cancel = True
            for rec in self.request_ids:
                rec.action_cancel()