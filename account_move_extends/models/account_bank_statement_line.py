# -*- coding: utf-8 -*-
from odoo import api, fields, models


class AccountBankStatementLine(models.Model):
    _inherit = 'account.bank.statement.line'

    staff_location_id = fields.Many2one(
        'staff.location',
        related='move_id.staff_location_id',
        string='Doc Location',
        readonly=False,
    )

    @api.model_create_multi
    def create(self, vals_list):
        # Keep Doc Location from New Transaction on the created journal entry
        location_ids = [vals.get('staff_location_id') for vals in vals_list]
        lines = super().create(vals_list)
        for line, location_id in zip(lines, location_ids):
            if location_id and line.move_id.staff_location_id.id != location_id:
                line.move_id.staff_location_id = location_id
        return lines
