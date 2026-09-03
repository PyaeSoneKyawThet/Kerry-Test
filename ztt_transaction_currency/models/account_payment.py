# -*- coding: utf-8 -*-
from odoo import models, fields, api, _, Command
from odoo.exceptions import UserError, ValidationError
from odoo.tools.misc import format_date, formatLang


class AccountPayment(models.Model):
    _inherit = "account.payment"

    @api.depends('currency_id','date')
    def compute_currency_rate(self):
        for rec in self:
            if rec.company_id.currency_id.id!=rec.currency_id.id:
                currency_rate= self.env['res.currency']._get_conversion_rate(
                    from_currency=rec.currency_id,
                    to_currency=self.env.company.currency_id,
                    company=rec.company_id, 
                    date=rec.date,
                )
                rec.currency_rate = currency_rate
            else:
                rec.currency_rate = 1

    currency_rate = fields.Float('Currency Rate',compute='compute_currency_rate',store=True,readonly=False, tracking=True)

    @api.model
    def _get_trigger_fields_to_synchronize(self):
        return (
            'date', 'amount', 'payment_type', 'partner_type', 'payment_reference', 'is_internal_transfer',
            'currency_id', 'partner_id', 'destination_account_id', 'partner_bank_id', 'journal_id', 'currency_rate'
        )

    def _prepare_move_line_default_vals(self, write_off_line_vals=None, force_balance=None):
        lines = super(AccountPayment, self)._prepare_move_line_default_vals(write_off_line_vals=write_off_line_vals, force_balance=force_balance)
        
        write_off_line_vals = write_off_line_vals or []
        write_off_dict = write_off_line_vals[0]  if write_off_line_vals else {}
        journal_lines = [line for line in lines if line != write_off_dict]

        for val in journal_lines:
            write_off_line_vals_list = write_off_line_vals or []
            write_off_amount_currency = sum(x['amount_currency'] for x in write_off_line_vals_list)
            write_off_balance = sum(x['balance'] for x in write_off_line_vals_list)

            if self.payment_type == 'inbound':
                # Receive money.
                liquidity_amount_currency = self.amount
            elif self.payment_type == 'outbound':
                # Send money.
                liquidity_amount_currency = -self.amount
            else:
                liquidity_amount_currency = 0.0

            liquidity_balance = self.currency_id.with_context(currency_rate=self.currency_rate)._convert(
                                    liquidity_amount_currency,
                                    self.company_id.currency_id.with_context(currency_rate=1),
                                    self.company_id,
                                    self.date,
                                )
            counterpart_amount_currency = -liquidity_amount_currency - write_off_amount_currency
            counterpart_balance = -liquidity_balance - write_off_balance

            if val['account_id'] == self.outstanding_account_id.id:
                val.update({
                    'amount_currency': liquidity_amount_currency,
                    'debit': liquidity_balance if liquidity_balance > 0.0 else 0.0,
                    'credit': -liquidity_balance if liquidity_balance < 0.0 else 0.0,
                })
            elif val['account_id'] == self.destination_account_id.id:
                val.update({
                    'amount_currency': counterpart_amount_currency,
                    'debit': counterpart_balance if counterpart_balance > 0.0 else 0.0,
                    'credit': -counterpart_balance if counterpart_balance < 0.0 else 0.0,
                })
 
        return journal_lines + write_off_line_vals

    def action_post(self):
        res = super().action_post()
        for rec in self:
            rec.move_id.write({
                            'currency_rate': rec.currency_rate,
                            })
        return res





    