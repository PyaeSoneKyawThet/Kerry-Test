from odoo import models, fields, _
from odoo.addons.account.models.exceptions import TaxClosingNonPostedDependingMovesError
from odoo.exceptions import UserError


class ValidateAccountMove(models.TransientModel):
    _inherit = "validate.account.move"

    """ when journal entry is linked to payment,
        can't post the entry.
    """
    def validate_move(self):
        if self._context.get('active_model') == 'account.move':
            domain = [('id', 'in', self._context.get('active_ids', [])), ('state', '=', 'draft')]
            moves = self.env['account.move'].search(domain).filtered('line_ids')
            payments = moves.filtered(lambda move: move.move_type == 'entry').mapped('payment_id')
            if payments:
                raise UserError(_("Some journal entries are linked to payments and cannot be posted."))
            else:
                return super().validate_move()
        else:
            return super().validate_move()

