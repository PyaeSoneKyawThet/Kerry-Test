from odoo import api, fields, models, _
from odoo.tools import formatLang, json
from datetime import date

from odoo.tools.misc import formatLang
from odoo.tools import format_date


class AccountPayment(models.Model):
    _inherit = "account.payment"

    is_currency_change = fields.Boolean(string="Is Currency Change")
    report_currency_id = fields.Many2one('res.currency', compute='_compute_report_currency', string="Report Currency", store=True, readonly=False)
    report_amount = fields.Monetary(string="Pay Amount", currency_field="report_currency_id", compute="_compute_report_amount", store=True, readonly=False)
    amount_signed = fields.Monetary(
        currency_field='currency_id', compute='_compute_amount_signed', store=True, 
        help='Negative value of amount field if payment_type is outbound')
    
    credit_refund_move_ids = fields.Many2many(
                                'account.move',
                                'account_payment_credit_refund_rel' ,
                                'linked_payment_id', 'credit_refund_id' ,
                                string="Credit Notes / Refunds",
                                copy=False
                            )
    
    # method only use for table relation update
    def _update_linked_payment(self):
        old_moves = self.env['account.move'].search([('linked_payment_id', '=', self.id)])
        if old_moves:
            old_moves.write({'linked_payment_id': False})

        if self.credit_refund_move_ids:
            self.credit_refund_move_ids.write({'linked_payment_id': self.id})
    
    def write(self, vals):
        res = super().write(vals)
        if 'credit_refund_move_ids' in vals:
            self._update_linked_payment()
        return res

    #REPORT: Receipt Voucher & Payment Voucher
    #( eg: invoice used:3000, paymnet:5000, write-off:2000 )
    def _get_write_off_journal(self):
        reconciled_lines = self.move_id.line_ids._reconciled_lines()
        write_off_line = self.env['account.move.line'].search([('id','in', reconciled_lines)]).filtered(lambda line: line.is_write_off)
        write_off_lines = write_off_line.move_id.line_ids

        return write_off_lines
    
    @api.depends('is_currency_change', 'currency_id')
    def _compute_report_currency(self):
        for rec in self:
            if rec.is_currency_change:
                rec.report_currency_id = rec.company_currency_id
            else:
                rec.report_currency_id = rec.currency_id

    @api.depends('amount', 'currency_rate', 'is_currency_change', 'report_currency_id', 'currency_id')
    def _compute_report_amount(self):
        for rec in self:
            if rec.is_currency_change and rec.currency_id != rec.report_currency_id:
                rec.report_amount = rec.amount * rec.currency_rate
            else:
                rec.report_amount = rec.amount

    #REPORT: Offical Receipt, Receipt Voucher & Payment Voucher
    #---to show credit_note or refund values which are linked to this payment---
    def _get_credit_refund_value(self):
        """Return credit note info grouped by original invoice (reversed_entry_id) with total per invoice."""
        result = {}
        for move in self.credit_refund_move_ids:
            original_invoice = move.reversed_entry_id
            if not original_invoice:
                continue  # skip if no linked invoice
            
            # for credit note
            amount_total = 0
            if move.tax_totals and 'amount_total' in move.tax_totals:
                amount_total = move.tax_totals['amount_total']

            if original_invoice.id not in result:
                result[original_invoice.id] = {
                    'lines': [],
                    'total': 0.0,
                }

            result[original_invoice.id]['lines'].append({
                'name': move.name,
                'date': format_date(self.env, move.invoice_date),
                'amount_total': -abs(amount_total),
                'amount_untaxed': -abs(move.amount_untaxed),
                'amount_tax': -abs(move.amount_tax),
                'vendor_invoice_no': move.vendor_invoice_no,
                'reason': move.reason
            })

            # add to total
            result[original_invoice.id]['total'] += amount_total

        return result
    
    #REPORT: Offical Receipt, Receipt Voucher & Payment Voucher
    #---to show invoices grouped by currency---
    def _get_grouped_invoice(self):
        self.ensure_one()
        grouped = []
        for currency in self.reconciled_invoice_ids.mapped("currency_id"):
            invoices = self.reconciled_invoice_ids.filtered(lambda inv: inv.currency_id == currency)
            grouped.append({
                "currency": currency,
                "invoices": invoices,
            })
        return grouped
    
    #REPORT: Offical Receipt, Receipt Voucher & Payment Voucher
    #---to show bills grouped by currency---
    def _get_grouped_bill(self):
        self.ensure_one()
        grouped = []
        for currency in self.reconciled_bill_ids.mapped("currency_id"):
            bills = self.reconciled_bill_ids.filtered(lambda inv: inv.currency_id == currency)
            grouped.append({
                "currency": currency,
                "bills": bills,
            })
        return grouped




