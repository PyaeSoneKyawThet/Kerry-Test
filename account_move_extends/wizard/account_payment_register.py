from odoo import api, fields, models, _
from odoo.tools.misc import format_date

class AccountPaymentRegister(models.TransientModel):
    _name = "account.payment.register"
    _inherit = ['account.payment.register','analytic.mixin']

    account_payment_type_id = fields.Many2one('account.payment.type', string="Custom Type", copy=False, 
                                    store=True, readonly=False, compute='_compute_payment_type')
    cheque_no = fields.Char(string="Cheque No")
    payment_available_journal_ids = fields.Many2many(
                                        comodel_name='account.journal',
                                        compute='_compute_payment_available_journal_ids' 
                                    )
    journal_id = fields.Many2one(
        comodel_name='account.journal',
        compute='_compute_journal_id', store=True, readonly=False, precompute=True,
        check_company=True,
        domain="[('id', 'in', payment_available_journal_ids)]")

    @api.onchange('account_payment_type_id')
    def onchange_account_payment_type(self):
        if self.account_payment_type_id.journal_ids:
            self.journal_id = self.account_payment_type_id.journal_ids.ids[0]
        elif self.available_journal_ids:
            self.journal_id = self.available_journal_ids.ids[0]
        else:
            self.journal_id = False
    
    @api.depends('account_payment_type_id')
    def _compute_payment_available_journal_ids(self):
        for rec in self:
            if rec.account_payment_type_id:
                rec.payment_available_journal_ids = rec.account_payment_type_id.journal_ids.ids
            else:
                rec.payment_available_journal_ids = rec.available_journal_ids.ids
    
    @api.depends('can_edit_wizard')
    def _compute_payment_type(self):
        for wizard in self:
            if wizard.can_edit_wizard:
                batches = wizard._get_batches()
                wizard.account_payment_type_id = wizard._get_batch_payment_type(batches[0])
            else:
                wizard.account_payment_type_id = False
                                
    @api.model
    def _get_batch_payment_type(self, batch_result):
        custom_payment_type = [line.move_id.account_payment_type_id for line in batch_result['lines']][0]
        return custom_payment_type
                
    def _create_payment_vals_from_wizard(self, batch_result):
        res = super(AccountPaymentRegister,self)._create_payment_vals_from_wizard(batch_result)
        res['account_payment_type_id'] = self.account_payment_type_id.id
        res['cheque_no'] = self.cheque_no
        if res.get('write_off_line_vals'):
            res['write_off_line_vals'][0]['analytic_distribution'] = self.analytic_distribution or {}
        return res
    
    
