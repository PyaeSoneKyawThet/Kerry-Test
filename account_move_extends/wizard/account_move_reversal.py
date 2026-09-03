from odoo import api, fields, models, _
from odoo.exceptions import UserError

class AccountMoveReversal(models.TransientModel):
    _inherit = 'account.move.reversal'

    is_internal_wrong = fields.Boolean(string="Internal Wrong", default=False)

    def _prepare_default_reversal(self, move):
        vals = super()._prepare_default_reversal(move)
        if move.move_type == 'in_invoice':
            if move.bill_type in ['vendor_bill']:
                vals['debit_note_type'] = 'debit_note'
            elif move.bill_type in ['petty_cash','petty_cash_with_ca']:
                vals['debit_note_type'] = 'petty_cash_debit_note'
            
        vals['is_internal_wrong'] = self.is_internal_wrong
        return vals
    
    """ when journal entry is linked to payment,
        can't reverse the entry.
    """
    @api.model
    def default_get(self, fields):
        res = super(AccountMoveReversal, self).default_get(fields)
        move_ids = self.env['account.move'].browse(self.env.context['active_ids']) if self.env.context.get('active_model') == 'account.move' else self.env['account.move']

        if any(move.payment_id for move in move_ids):
            raise UserError(_("Some journal entries are linked to payments and cannot be reversed."))
        
        return res
    
    

    