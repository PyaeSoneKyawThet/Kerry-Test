from odoo import fields, models, api 

class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"    

    purchase_request_line_id = fields.Many2one('approval.product.line', string="Purchase Request Line", copy=False)  

    @api.onchange('purchase_request_line_id')
    def _onchange_purchase_request_line(self):
        for rec in self:
            if rec.purchase_request_line_id:
                rec.update({
                    'product_id': rec.purchase_request_line_id.product_id,
                    'name': rec.purchase_request_line_id.description,
                    'brand_id': rec.purchase_request_line_id.brand_id,
                    'product_qty': rec.purchase_request_line_id.quantity,
                    'price_unit': rec.purchase_request_line_id.unit_price,
                    'analytic_distribution': rec.purchase_request_line_id.analytic_distribution,
                    'bl_no': rec.purchase_request_line_id.bl_no,
                    'vehicle_no': rec.purchase_request_line_id.vehicle_no,
                    'reference_key': rec.purchase_request_line_id.reference_key,
                    'product_uom': rec.purchase_request_line_id.product_uom_id
                })

    def _set_po_created(self, values):
        purchase_request_line = self.env['approval.product.line'].browse(values.get('purchase_request_line_id'))
        purchase_request_line.sudo().write({'created_po': True})
                
    @api.model_create_multi
    def create(self, vals_list):
        recs = super().create(vals_list)
        for values in vals_list:
            if 'purchase_request_line_id' in values:
                self._set_po_created(values)
        return recs

    def write(self, vals):
        if 'purchase_request_line_id' in vals:
            self.purchase_request_line_id.sudo().write({'created_po': False})
            self._set_po_created(vals)
        res = super().write(vals)
        return res
    
    def unlink(self):
        for rec in self:
            if rec.purchase_request_line_id:
                self.purchase_request_line_id.sudo().write({'created_po': False})
        return super(PurchaseOrderLine, self).unlink()
    
    def _prepare_stock_move_vals(self, picking, price_unit, product_uom_qty, product_uom):
        vals = super()._prepare_stock_move_vals(picking, price_unit, product_uom_qty, product_uom)
        vals['purchase_request_line_id'] = self.purchase_request_line_id.id
        return vals