from odoo import fields, api, models
from datetime import date, timedelta

class StockMove(models.Model):    
    _inherit = "stock.move"

    category_id = fields.Many2one('product.category', string="Product Category", related="product_id.categ_id", store=True)
    brand_id = fields.Many2one('purchase.brand', string="Brand Name", related="purchase_line_id.brand_id", store=True)
    vehicle_no = fields.Char(string="Vehicle No", related="purchase_line_id.vehicle_no", store=True)
    purchase_order_id = fields.Many2one('purchase.order', related='picking_id.purchase_order_id', store=True)
    vendor_invoice_no = fields.Char(related='picking_id.vendor_invoice_no', store=True)
    delivery_date = fields.Date(related='picking_id.delivery_date', store=True)
    owner_id = fields.Many2one('res.partner', related='picking_id.owner_id', store=True)

    analytic_precision = fields.Integer(
        related="purchase_line_id.analytic_precision",
        string="Analytic Precision",
        readonly=False
    )

    analytic_distribution = fields.Json(
        related="purchase_line_id.analytic_distribution",
        string="Analytic Distribution",
        readonly=False,
        store=True
    )

    # for backorder
    def _prepare_move_split_vals(self, qty):
        vals = super()._prepare_move_split_vals(qty)
        vals.update({
            'brand_id': self.brand_id.id,
            'analytic_distribution': self.analytic_distribution,
            'vehicle_no': self.vehicle_no,
        })
        return vals

class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    brand_id = fields.Many2one('purchase.brand', string="Brand Name", related="move_id.brand_id", store=True)
    vehicle_no = fields.Char(string="Vehicle No", related="move_id.vehicle_no", store=True)
    purchase_order_id = fields.Many2one('purchase.order', related='move_id.purchase_order_id', store=True)
    vendor_invoice_no = fields.Char(related='move_id.vendor_invoice_no', store=True)
    delivery_date = fields.Date(related='move_id.delivery_date', store=True)
    owner_id = fields.Many2one('res.partner', related='move_id.owner_id', store=True)

   