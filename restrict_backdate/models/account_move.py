from odoo import api, models, fields, _
from odoo.exceptions import UserError
from datetime import datetime
from dateutil.relativedelta import relativedelta

class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.constrains('invoice_date')
    def check_date_order(self):
        for account_move in self:
            invoice_date = account_move.invoice_date
            if not invoice_date:
                continue
            today = fields.Date.today()
            company = self.env.company
            allowed_backdate = self.env.user.has_group('restrict_backdate.group_allowed_backdate_access')
            limit_day = company.backdate_limit_day or 0
            backdate_limit = today - relativedelta(days=limit_day)
            if account_move.move_type != 'entry':
                if invoice_date < today and (not allowed_backdate or invoice_date < backdate_limit):
                    raise UserError(_('You are not allowed to do backdate transaction or your backdate is beyond limit.'))

    @api.constrains('date')
    def check_accounting_date(self):
        for account_move in self:
            accounting_date = account_move.date
            if not accounting_date:
                continue
            today = fields.Date.today()
            company = self.env.company
            allowed_backdate = self.env.user.has_group('restrict_backdate.group_allowed_backdate_access')
            limit_day = company.backdate_limit_day or 0
            backdate_limit = today - relativedelta(days=limit_day)
            if account_move.move_type == 'entry':
                if accounting_date < today and (not allowed_backdate or accounting_date < backdate_limit):
                    raise UserError(_('You are not allowed to do backdate transaction or your backdate is beyond limit!'))
