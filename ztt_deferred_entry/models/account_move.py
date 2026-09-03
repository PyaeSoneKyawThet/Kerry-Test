from odoo import fields, models, SUPERUSER_ID, _, api, Command
from odoo.exceptions import UserError

class AccountMove(models.Model):
    _inherit = 'account.move'
    

    total_deferred_value = fields.Float(string="Total Deferred Booked Value", compute="_compute_total_deferred_balance")
    total_deferred_value_currency = fields.Float(string="Total Deferred Booked Value Currency", compute="_compute_total_deferred_balance")
    total_depreciated_value = fields.Float(string="Total Depreciated Value", compute="_compute_total_deferred_balance")
    total_depreciated_value_currency = fields.Float(string="Total Depreciated Value Currency", compute="_compute_total_deferred_balance")
    
    @api.depends('invoice_line_ids.deferred_booked_value', 'invoice_line_ids.depreciated_value', 'invoice_line_ids.deferred_booked_value_currency', 'invoice_line_ids.depreciated_value_currency')
    def _compute_total_deferred_balance(self):
        for rec in self:
            rec.total_deferred_value = sum(rec.invoice_line_ids.mapped('deferred_booked_value'))
            rec.total_deferred_value_currency = sum(rec.invoice_line_ids.mapped('deferred_booked_value_currency'))
            rec.total_depreciated_value = sum(rec.invoice_line_ids.mapped('depreciated_value'))
            rec.total_depreciated_value_currency = sum(rec.invoice_line_ids.mapped('depreciated_value_currency'))

    #update custom fields for KMTL
    def _generate_deferred_entries(self):
        res = super()._generate_deferred_entries()
        self.deferred_move_ids.write({
                                    'currency_id': self.currency_id.id,
                                    'attention_to': self.attention_to,
                                    'account_payment_type_id': self.account_payment_type_id,
                                    'staff_location_id': self.staff_location_id.id,
                                    'pay_to_id': self.pay_to_id.id,
                                    'pay_to_external': self.pay_to_external,
                                    'approval_payment_request_id': self.approval_payment_request_id.id,
                                    'request_id': self.request_id.id,
                                    })
        return res

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    deferred_account_id = fields.Many2one('account.account', string="Deferred Account", check_company=True)
    original_move_line_id = fields.Many2one('account.move.line', string="Original Move Line")
    deferred_booked_value = fields.Float(string="Deferred Booked Value", compute="_compute_deferred_balance")
    deferred_booked_value_currency = fields.Float(string="Deferred Booked Value Currency", compute="_compute_deferred_balance")
    depreciated_value = fields.Float(string="Depreciated Value", compute="_compute_deferred_balance")
    depreciated_value_currency = fields.Float(string="Depreciated Value Currency", compute="_compute_deferred_balance")
    
    @api.depends('move_id.deferred_move_ids', 'price_total', 'price_subtotal', 'move_id.state')
    def _compute_deferred_balance(self):
        for rec in self:
            if rec.deferred_start_date and rec.deferred_end_date and rec.move_id.state == 'posted':
                rec.deferred_booked_value = sum(rec.move_id.deferred_move_ids.line_ids.filtered(lambda x: x.original_move_line_id.id == rec.id and x.move_id.state == 'draft').mapped('move_id.amount_total_signed'))
                rec.deferred_booked_value_currency = sum(rec.move_id.deferred_move_ids.line_ids.filtered(lambda x: x.original_move_line_id.id == rec.id and x.move_id.state == 'draft').mapped('move_id.amount_total_in_currency_signed'))
                if rec.move_id.move_type in ['out_invoice']:
                    total = rec.credit
                    total_currency = abs(rec.amount_currency)
                elif rec.move_id.move_type in ['in_invoice']:
                    total = rec.debit
                    total_currency = abs(rec.amount_currency)
                else:
                    total = 0
                rec.depreciated_value = total - rec.deferred_booked_value if total > 0 else 0
                if rec.currency_id != self.env.company.currency_id:
                    rec.depreciated_value_currency = total_currency - rec.deferred_booked_value_currency if total_currency > 0 else 0
                else:
                    rec.depreciated_value_currency = 0
            else:
                rec.deferred_booked_value = 0
                rec.deferred_booked_value_currency = 0
                rec.depreciated_value = 0
                rec.depreciated_value_currency = 0
    
    @api.model
    def _get_deferred_lines_values(self, account_id, balance, ref, analytic_distribution, line=None):
        res = super()._get_deferred_lines_values(account_id, balance, ref, analytic_distribution, line=line)
        if line:
            res['original_move_line_id'] = line.id
            res['currency_id'] = line.currency_id.id
            res['amount_currency'] = line.currency_rate * balance
        deferred_type = "expense" if line.move_id.is_purchase_document() else "revenue"
        deferred_account = line.move_id.company_id.deferred_expense_account_id if deferred_type == "expense" else line.move_id.company_id.deferred_revenue_account_id
        if account_id == deferred_account.id:
            res['account_id'] = line.deferred_account_id.id or account_id
            res['analytic_distribution'] = False
        return res

    