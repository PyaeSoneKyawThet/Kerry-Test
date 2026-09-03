from odoo import fields, api, models , _

class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    model_serial_no = fields.Char(string="Model Serial No")

    def _prepare_stock_move_vals(self, picking, price_unit, product_uom_qty, product_uom):
        vals = super()._prepare_stock_move_vals(picking, price_unit, product_uom_qty, product_uom)
        vals['model_serial_no'] = self.model_serial_no
        return vals

    