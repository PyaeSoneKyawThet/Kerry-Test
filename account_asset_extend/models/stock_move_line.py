from odoo import fields, api, models , _

class StockMove(models.Model):
    _inherit = "stock.move.line"

    asset_id = fields.Many2one('account.asset', string='Asset')
    created_asset = fields.Boolean(string='Asset Created', compute='_compute_asset_created')
    model_serial_no = fields.Char(string="Model Serial No")

    @api.depends('asset_id', 'move_id.state')
    def _compute_asset_created(self):
        for rec in self:
            rec.created_asset = (rec.move_id.state == 'done' and rec.asset_id and rec.asset_id.state != 'cancel')

    def _prepare_asset_value(self):
        vals = {'name': self.product_id.name,                    
                'product_id': self.product_id.id,
                'model_id': self.product_id.asset_model_id.id,
                'method': self.product_id.asset_model_id.method,
                'method_number': self.product_id.asset_model_id.method_number,
                'method_progress_factor': self.product_id.asset_model_id.method_progress_factor,
                'method_period': self.product_id.asset_model_id.method_period,
                'prorata_computation_type': self.product_id.asset_model_id.prorata_computation_type,
                'account_asset_id': self.product_id.asset_model_id.account_asset_id.id,
                'account_depreciation_id': self.product_id.asset_model_id.account_depreciation_id.id,
                'account_depreciation_expense_id': self.product_id.asset_model_id.account_depreciation_expense_id.id,
                'journal_id': self.product_id.asset_model_id.journal_id.id,
                'picking_id': self.move_id.picking_id.id,
                'location_dest_id': self.location_dest_id.id,
                'staff_location_id': self.move_id.picking_id.staff_location_id.id,
                'original_value': self.move_id.price_unit,
                'lot_name': self.lot_name,
                'model_serial_no': self.model_serial_no,
                }
        return vals

    def action_create_asset(self):
        for rec in self:
            if rec.product_id.asset_model_id and rec.product_id.tracking == 'serial' and rec.move_id.state == 'done' and not rec.created_asset:
                # vals = {'name': rec.product_id.name,                    
                #         'product_id': rec.product_id.id,
                #         'model_id': rec.product_id.asset_model_id.id,
                #         'account_asset_id': rec.product_id.asset_model_id.account_asset_id.id,
                #         'account_depreciation_id': rec.product_id.asset_model_id.account_depreciation_id.id,
                #         'account_depreciation_expense_id': rec.product_id.asset_model_id.account_depreciation_expense_id.id,
                #         'journal_id': rec.product_id.asset_model_id.journal_id.id,
                #         'picking_id': rec.move_id.picking_id.id,
                #         'location_dest_id': rec.location_dest_id.id,
                #         'staff_location_id': rec.move_id.picking_id.staff_location_id.id,
                #         'original_value': rec.move_id.price_unit}
                asset_vals = rec._prepare_asset_value()
                asset = self.env['account.asset'].create(asset_vals)
                rec.asset_id = asset.id
        return True
    
    # pass model_serial_no in create
    # since new move_line is created when lot generate
    @api.model_create_multi
    def create(self, vals_list):
        recs = super().create(vals_list)
        for rec in recs:
            if rec.move_id:
                rec.model_serial_no = rec.move_id.model_serial_no
        return recs