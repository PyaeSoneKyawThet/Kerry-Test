from odoo import api, fields, models, _
from odoo.tools import formatLang, json
from datetime import date

from odoo.tools.misc import formatLang

class AccountMove(models.Model):
    _inherit = "account.move"

    report_invoice_payments_widget = fields.Char(
        compute='_compute_report_invoice_payments_widget', 
        string="Report Payments Widget"
    )

    linked_payment_id = fields.Many2one(
                            'account.payment',
                            string="Linked Payment (Credit/Refund)",
                            store=True
                        )

    @api.depends('move_type', 'line_ids.amount_residual')
    def _compute_report_invoice_payments_widget(self):
        for move in self:
            payments_widget_vals = {'title': _('Less Payment'), 'outstanding': False, 'content': []}

            if move.state == 'posted' and move.is_invoice(include_receipts=True):
                reconciled_vals = []
                reconciled_partials = move.sudo()._get_all_reconciled_invoice_partials()
                
                no = 0
                for reconciled_partial in reconciled_partials:
                    counterpart_line = reconciled_partial['aml'] 
                    no = no + 1
                    
                    if counterpart_line.move_id.ref:
                        reconciliation_ref = '%s (%s)' % (counterpart_line.move_id.name, counterpart_line.move_id.ref)
                    else:
                        reconciliation_ref = counterpart_line.move_id.name
                    
                    if counterpart_line.amount_currency and counterpart_line.currency_id != counterpart_line.company_id.currency_id:
                        foreign_currency = counterpart_line.currency_id
                    else:
                        foreign_currency = False

                    # Add reconciled values with invoice_id 
                    reconciled_vals.append({
                        'index_no': no,
                        'name': counterpart_line.name,
                        'journal_name': counterpart_line.journal_id.name,
                        'company_name': counterpart_line.journal_id.company_id.name if counterpart_line.journal_id.company_id != move.company_id else False,
                        'amount': reconciled_partial['amount'],
                        'currency_id': move.company_id.currency_id.id if reconciled_partial['is_exchange'] else reconciled_partial['currency'].id,
                        'date': counterpart_line.date.strftime('%Y-%m-%d') if counterpart_line.date else '',
                        'partial_id': reconciled_partial['partial_id'],
                        'account_payment_id': counterpart_line.payment_id.id,
                        'payment_method_name': counterpart_line.payment_id.payment_method_line_id.name,
                        'move_id': counterpart_line.move_id.id,
                        'move_type': counterpart_line.move_id.move_type,
                        'ref': reconciliation_ref,
                        'is_exchange': reconciled_partial['is_exchange'],
                        'amount_company_currency': formatLang(self.env, abs(counterpart_line.balance), currency_obj=counterpart_line.company_id.currency_id),
                        'amount_foreign_currency': foreign_currency and formatLang(self.env, abs(counterpart_line.amount_currency), currency_obj=foreign_currency),
                        'invoice_id': move.id  # Add invoice_id 
                    })
                
                payments_widget_vals['content'] = reconciled_vals

            # Store data in JSON format for report
            move.report_invoice_payments_widget = json.dumps(payments_widget_vals) if payments_widget_vals['content'] else False
    
    def _get_write_off_journal(self,payment_id):
        self.ensure_one()
        if self.state == 'posted' and self.is_invoice(include_receipts=True):
            reconciled_partials = self.sudo()._get_all_reconciled_invoice_partials()
            
            write_off_moves = self.env['account.move']
            if self.move_type == 'out_invoice':
                for reconciled_partial in reconciled_partials:
                    if not reconciled_partial['aml'].move_id.payment_id and reconciled_partial['aml'].move_id.move_type != 'out_refund':
                        write_off_moves |= reconciled_partial['aml'].move_id
                        return {'write_off_moves': write_off_moves} 

            if self.move_type == 'in_invoice':
                for reconciled_partial in reconciled_partials:
                    if not reconciled_partial['aml'].move_id.payment_id and reconciled_partial['aml'].move_id.move_type != 'in_refund':
                        write_off_moves |= reconciled_partial['aml'].move_id
                        return {'write_off_moves': write_off_moves}

        return {'write_off_moves': self.env['account.move']} 
    
    def _is_show_wirte_off_value(self):
        self.ensure_one()
        show_write_off = False
        if self.state == 'posted' and self.is_invoice(include_receipts=True):
            reconciled_partials = self.sudo()._get_all_reconciled_invoice_partials()
            
            write_off_moves = self.env['account.move']
            for reconciled_partial in reconciled_partials:
                if not reconciled_partial['aml'].move_id.payment_id and reconciled_partial['aml'].move_id.move_type != 'out_refund':
                    line_from_wizard = reconciled_partial['aml'].move_id.line_ids.filtered(lambda l: l.account_id != reconciled_partial['aml'].account_id)
                    # if line_from_wizard and not line_from_wizard.account_id.is_wht_tax:
                    #     show_write_off = False
                    is_write_off_line = line_from_wizard.filtered(lambda l: l.is_write_off)
                    is_wht_tax_account = any(is_write_off_line.mapped('account_id.is_wht_tax'))
                    if is_wht_tax_account:
                        show_write_off = True
                        
        return show_write_off

        



