from collections import defaultdict
from datetime import timedelta
from odoo import api, Command, fields, models, _
from odoo.exceptions import UserError

class AccountReconcileWizard(models.TransientModel):
    _name = 'account.reconcile.wizard'
    _inherit = ['account.reconcile.wizard','analytic.mixin']

    partner_id = fields.Many2one('res.partner', string="Partner", compute="_compute_partner_id")

    @api.depends('move_line_ids.move_id')
    def _compute_partner_id(self):
        for wizard in self:
            wizard.partner_id = wizard.move_line_ids[0].move_id.partner_id

    def _create_write_off_lines(self, partner=None):
        res = super()._create_write_off_lines(partner=None)
        for command, _, line in res:
            line.update({
                'partner_id': self.partner_id.id,
                'is_write_off': True
            }) 
            if self.account_id and self.account_id.id == line.get('account_id'):
                line.update({'analytic_distribution': self.analytic_distribution})
        return res