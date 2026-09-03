from odoo import fields, api, models
from odoo.tools.float_utils import float_compare, float_is_zero, float_round

class PurchaseOrderLine(models.Model):    
    _inherit = "purchase.order.line"

    category_id = fields.Many2one('product.category',string="Product Category")
    job_location_id = fields.Many2one('job.location',string="Job Location")

    brand_id = fields.Many2one('purchase.brand', string="Brand Name")
    vehicle_no = fields.Char(string="Vehicle No")
    bl_no = fields.Char(string="BL No")
    reference_key = fields.Char(string="Reference Key") 

    def _prepare_stock_move_vals(self, picking, price_unit, product_uom_qty, product_uom):
        vals = super()._prepare_stock_move_vals(picking, price_unit, product_uom_qty, product_uom)
        vals['product_uom'] = self.product_uom.id
        vals['product_uom_qty'] = self.product_qty
        return vals
    
    def _prepare_account_move_line(self,move=False):
        res = super()._prepare_account_move_line(move)
        res.update({
            'name': self.name,
        })
        return res
