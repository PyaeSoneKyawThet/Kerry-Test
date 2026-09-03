from odoo import api, fields, models, _
from odoo.exceptions import UserError

class AccountAccount(models.Model):
    _inherit = 'account.account'

    is_wht_tax = fields.Boolean(string="WHT Tax", store=True)