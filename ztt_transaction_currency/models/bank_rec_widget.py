from odoo import _, api, fields, models, Command
from odoo.osv import expression
from odoo.tools.misc import formatLang, frozendict

class BankRecWidget(models.Model):
    _inherit = "bank.rec.widget"

    def _line_value_changed_currency_rate(self, line):
        if line.currency_rate:
            line.balance = line.amount_currency * line.currency_rate
            line.amount_transaction_currency = line.balance
        self._line_value_changed_amount_transaction_currency(line)

    def _line_value_changed_date(self, line):
        self.ensure_one()
        if line.flag == 'liquidity' and line.date:
            line.currency_rate = self.env['res.currency']._get_conversion_rate(
                    from_currency=line.currency_id,
                    to_currency=line.company_id.currency_id,
                    company=line.company_id, 
                    date=line.date,
                )
            self.st_line_id.currency_rate = line.currency_rate
        self._line_value_changed_currency_rate(line)
        return super()._line_value_changed_date(line)

    # if user manually set amount: recalcualte currency_rate
    def _line_value_changed_amount_transaction_currency(self, line):
        rec = super()._line_value_changed_amount_transaction_currency(line)
        self.ensure_one()
        if line.flag == 'liquidity':
            if line.transaction_currency_id != self.journal_currency_id:
                self.st_line_id.currency_rate = self.st_line_id.amount_currency / self.st_line_id.amount_total
        return rec
    
    def _line_value_changed_transaction_currency_id(self, line):
        if line.transaction_currency_id != self.journal_currency_id:
            line.currency_rate = self.env['res.currency']._get_conversion_rate(
                    from_currency=line.currency_id,
                    to_currency=line.company_id.currency_id,
                    company=line.company_id, 
                    date=line.date,
                )
            self.st_line_id.currency_rate = line.currency_rate
        return super()._line_value_changed_transaction_currency_id(line)
    
    def _action_validate(self):
        self.ensure_one()
        st_line = self.st_line_id
        move = st_line.move_id

        # Update the move.
        move_ctx = move.with_context(
            force_delete=True,
            skip_readonly_check=True,
        )
        move_ctx.write({'currency_rate': st_line.currency_rate})

        super()._action_validate()