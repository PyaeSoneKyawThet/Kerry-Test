from odoo import fields, api, models, _,Command
from itertools import groupby
from operator import itemgetter
from odoo.exceptions import UserError, ValidationError
from datetime import date, timedelta


class AccountMove(models.Model):     
    _inherit = "account.move"

    reverse_journal = fields.Boolean(string="Auto Reverse", default=False, copy=False)
    reverse_date = fields.Date(string="Reverse Date", default=False, copy=False)
    is_reversed = fields.Boolean(string="Is Reversed", default=False, copy=False)

    def auto_reverse_journal(self):
        today = date.today()
        journals = self.env['account.move'].search([
            ('move_type', '=', 'entry'),
            ('reverse_journal','=', True),
            ('reverse_date','=', today),
            ('is_reversed','=', False),
            ('state','=', 'posted'),
        ])
        for journal in journals:
            reverse_journal = journal._reverse_moves()
            reverse_journal.update({'ref': f'Reversal of: {journal.name}'})
            reverse_journal.action_post()

            journal.update({'is_reversed': True})
    
    # def _prepare_reverse_journal_vals(self, journal):
    #     """prepare dictionary value to create move entry 
    #     """
    #     l_vals = []  

    #     for line in journal.line_ids:
    #         l_vals.append([0,0,{
    #                     'account_id': line.account_id.id,
    #                     'partner_id': line.partner_id.id,
    #                     'name': line.name,
    #                     'analytic_distribution': line.analytic_distribution,
    #                     'amount_currency': -1 * line.amount_currency,
    #                     'currency_id': line.currency_id.id,
    #                     'debit': line.credit,
    #                     'credit': line.debit,
    #                     'tax_tag_ids': line.tax_tag_ids.ids,
    #                     'tax_ids': line.tax_ids.ids,
    #                     'discount_date': line.discount_date,
    #                 }])
        
    #     vals = { 
    #              'ref': journal.name,
    #              'attention_to': journal.attention_to,
    #              'account_payment_type_id': journal.account_payment_type_id.id,
    #              'approval_payment_request_id': journal.approval_payment_request_id.id,
    #              'request_id': journal.request_id.id,
    #              'pay_to_id': journal.pay_to_id.id,
    #              'pay_to_external': journal.pay_to_external,
    #              'journal_id': journal.journal_id.id,
    #              'currency_rate': journal.currency_rate,
    #              'staff_location_id': journal.staff_location_id.id,
    #              'line_ids': l_vals
    #             } 
    #     return vals
            
    
            

