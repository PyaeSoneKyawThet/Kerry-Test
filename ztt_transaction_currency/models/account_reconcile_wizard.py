from odoo import api, Command, fields, models, _


class AccountReconcileWizard(models.TransientModel):
    _inherit = 'account.reconcile.wizard'

    def create_write_off(self):
        write_off_move = super(AccountReconcileWizard, self).create_write_off()
        if self.reco_currency_id.id != self.company_id.currency_id.id:
            currency_rate = abs(self.amount) / abs(self.amount_currency)
            write_off_move.update({
                'currency_rate': currency_rate
            })
        return write_off_move