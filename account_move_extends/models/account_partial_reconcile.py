from odoo import models

class AccountPartialReconcile(models.Model):
    _inherit = 'account.partial.reconcile'

    def write(self, vals):
        res = super().write(vals)

        if 'exchange_move_id' in vals:
            for partial in self:
                if partial.exchange_move_id:
                    ref_parts = []

                    if partial.debit_move_id.move_id.name:
                        ref_parts.append(partial.debit_move_id.move_id.name)
                    if partial.credit_move_id.move_id.name:
                        ref_parts.append(partial.credit_move_id.move_id.name)

                    if ref_parts:
                        ref_string = f"Exchange Diff from {' & '.join(sorted(set(ref_parts)))}"
                        partial.exchange_move_id.ref = ref_string
                        partial.exchange_move_id.line_ids.write({'name': ref_string})

        return res