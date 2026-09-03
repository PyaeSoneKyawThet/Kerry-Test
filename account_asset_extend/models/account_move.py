from odoo import api, fields, models, tools, _

class AccountMove(models.Model):
    _inherit = 'account.move'

    # fields for asset report
    new_asset_remaining_value = fields.Float(string="New Depreciable Value",compute="_compute_asset_remaining_value", store=True, help="For Asset Report")
    new_asset_depreciated_value = fields.Float(string="New Accumulated Depreciation",compute="_compute_asset_depreciated_value", store=True, help="For Asset Report")
    year_to_date = fields.Float(string="Year To Date", compute="_compute_year_to_date",store=True,copy=False, help="Cumulative Depreciation By Year")

    @api.depends('asset_id', 'depreciation_value', 'asset_id.total_depreciable_value', 'asset_id.already_depreciated_amount_import')
    def _compute_asset_remaining_value(self):
        for rec in self:
            rec.new_asset_remaining_value = rec.asset_remaining_value

    @api.depends('asset_id', 'depreciation_value', 'asset_id.total_depreciable_value', 'asset_id.already_depreciated_amount_import')
    def _compute_asset_depreciated_value(self):
        for rec in self:
            rec.new_asset_depreciated_value = rec.asset_depreciated_value

    @api.depends('asset_id', 'depreciation_value', 'asset_id.total_depreciable_value', 'asset_id.already_depreciated_amount_import')
    def _compute_year_to_date(self):
        for move in self:
            depreciated = 0
            target_year = move.date.year 
            target_date = move.date
            year_moves = move.asset_id.depreciation_move_ids.filtered(lambda mv: mv.date.year == target_year and mv.date <= target_date)
            for asset_move in year_moves.sorted(lambda mv: (mv.date, mv._origin.id)):
                depreciated += asset_move.depreciation_value
                move.year_to_date = depreciated

    def _prepare_move_for_asset_depreciation(self, vals):
        move_vals = super()._prepare_move_for_asset_depreciation(vals)
        asset = vals.get('asset_id')
        if asset:
            move_vals['staff_location_id'] = asset.staff_location_id.id if asset.staff_location_id else False

            for line in move_vals.get('line_ids', []):
                line_dict = line[2]

                if line_dict.get('account_id') != asset.account_depreciation_expense_id.id:
                    line_dict.pop('analytic_distribution', None)

        return move_vals
