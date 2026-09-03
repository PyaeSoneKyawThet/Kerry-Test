from odoo import _, api, fields, models, Command
from odoo.osv import expression
from odoo.tools.misc import formatLang, frozendict

import markupsafe
import uuid


class BankRecWidgetLine(models.Model):
    _inherit = "bank.rec.widget.line"

    currency_rate = fields.Float(
        string='Currency Rate',
        digits=(16, 4),
        compute='_compute_currency_rate', 
        store=True,
        readonly=False,
    )

    @api.depends('source_aml_id')
    def _compute_currency_rate(self):
        for line in self:
            if line.flag in ('aml', 'new_aml', 'exchange_diff'):
                line.currency_rate = line.source_aml_id.currency_rate
            elif line.flag in ('liquidity', 'auto_balance', 'manual', 'early_payment', 'tax_line'):
                line.currency_rate = line.wizard_id.st_line_id.currency_rate
            else:
                line.currency_rate = line.currency_rate
        
    


    


            