from odoo import fields, api, models, _
from itertools import groupby
from operator import itemgetter
from odoo.exceptions import UserError, ValidationError

class AccountMoveLine(models.Model):     
    _inherit = "account.move.line" 

    staff_location_id = fields.Many2one('staff.location', related="move_id.staff_location_id", string="Doc Location", store=True)
    is_write_off = fields.Boolean(string="is_write_off", default=False, copy=False) #for reporting purpose, only use in account_payment_report
    internal_reference = fields.Char(string="Internal Reference", related="move_id.internal_reference", store=True)
    payment_reference = fields.Char(string="Payment Reference", related="move_id.payment_reference", store=True)
    invoice_payment_term_id = fields.Many2one('account.payment.term', related="move_id.invoice_payment_term_id", string="Payment Terms", store=True)
    attention_to = fields.Char(string="Attention To", related="move_id.attention_to", store=True)

    def _get_report_data(self):
        result = []
        for line in self:
            if line.analytic_distribution:
                for key, percentage in line.analytic_distribution.items():
                    analytic_ids = [int(analytic_id) for analytic_id in key.split(',')]
                    analytic_accounts = self.env['account.analytic.account'].browse(analytic_ids)
                    for analytic_account in analytic_accounts:
                        account_name = analytic_account.name
                        plan_name = analytic_account.plan_id.name

                        if analytic_account.partner_id:
                            account_name = f"{analytic_account.name} - {analytic_account.partner_id.name}"
                        if analytic_account.plan_id.name == 'Job Location':
                            plan_name = 'Job Loc'
                        if analytic_account.plan_id.name == 'Job Department':
                            plan_name = 'Dept'
                        
                        result.append({
                            'plan_name': plan_name,
                            'account_name': account_name
                        })
        return result
    
    def _get_report_data_ar_invoice(self):
        result = []
        for line in self:
            if line.analytic_distribution:
                for key, percentage in line.analytic_distribution.items():
                    analytic_ids = [int(analytic_id) for analytic_id in key.split(',')]
                    analytic_accounts = self.env['account.analytic.account'].browse(analytic_ids)
                    for analytic_account in analytic_accounts:
                        account_name = analytic_account.name
                        plan_name = analytic_account.plan_id.name

                        if analytic_account.partner_id:
                            account_name = f"{analytic_account.name} - {analytic_account.partner_id.name}"
                        if analytic_account.plan_id.name == 'Job Location':
                            plan_name = 'Job Loc'
                        if analytic_account.plan_id.name == 'Job Department':
                            plan_name = 'Dept'
                        
                        if not analytic_account.plan_id.name == 'Projects':
                            result.append({
                                'plan_name': plan_name,
                                'account_name': account_name
                            })
        return result