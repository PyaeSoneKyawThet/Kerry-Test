from odoo import api, fields, models, _
from odoo.exceptions import UserError

class AccountJournal(models.Model):
    _inherit = 'account.journal'

    bank_account_no = fields.Char('Account No') 
    code = fields.Char(
        string='Short Code',
        size=10,
        compute='_compute_code', readonly=False, store=True,
        required=True, precompute=True,
        help="Shorter name used for display. "
             "The journal entries of this journal will also be named using this prefix by default."
    )

    payment_short_code = fields.Char(
        string='Payment Short Code',
        size=10,
        readonly=False, store=True,
        help="Shorter name used for display. "
             "The journal entries(Customer Payments) of this journal will also be named using this prefix."
    )