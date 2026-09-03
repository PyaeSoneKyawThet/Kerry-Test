from odoo import fields, api, models
from datetime import date, timedelta

class StockMove(models.Model):    
    _inherit = "stock.move"

    purchase_request_line_id = fields.Many2one('approval.product.line', string="Purchase Request Line", copy=False) 

    # for backorder
    def _prepare_move_split_vals(self, qty):
        vals = super()._prepare_move_split_vals(qty)
        vals.update({
            'purchase_request_line_id': self.purchase_request_line_id.id,
        })
        return vals

class StockPicking(models.Model):    
    _inherit = "stock.picking"

    purchase_request_line_id = fields.Many2one('approval.product.line', string="PR No.", related='move_ids.purchase_request_line_id', readonly=True)