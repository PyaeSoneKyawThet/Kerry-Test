from odoo import api, Command, fields, models, _
from odoo.exceptions import UserError

class ExpenseCancelWizard(models.TransientModel):
    _name = 'expense.cancel.wizard'
    _description = "Expense Cancel Wizard"

    is_expense_cancel = fields.Boolean(string="Cancel Expense")
    move_id = fields.Many2one('account.move', string="Bill")
    approval_expense_id = fields.Many2one('approval.expense', string="Expense")

    def action_cancel_bill(self):
        if self.is_expense_cancel:
            self.approval_expense_id.is_expense_cancel = True
            self.move_id.is_expense_cancel = True
       
        return self.move_id.button_cancel()
        