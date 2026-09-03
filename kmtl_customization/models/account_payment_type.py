from odoo import api, fields, models, _
from odoo.exceptions import UserError

class AccountPaymentType(models.Model):
    _name = 'account.payment.type'
    _description = "Account Payment Type"

    code = fields.Char(string="Code")
    name = fields.Char(string="Name")
    journal_ids = fields.Many2many('account.journal',string="Journal", domain=[('type', 'in', ('bank','cash'))])
    remark = fields.Char(string="Remark")