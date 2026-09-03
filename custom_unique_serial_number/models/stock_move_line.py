from odoo import fields, api, models , _


class StockMove(models.Model):    
    _inherit = "stock.move"

    staff_location_id = fields.Many2one('staff.location', related='picking_id.staff_location_id', string="Document Location")

class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    staff_location_id = fields.Many2one('staff.location', related='move_id.staff_location_id', string="Document Location")

    @api.model_create_multi
    def create(self, vals_list):
        mls = super().create(vals_list)
        for line in mls:
            product = line.product_id
            if product.tracking == 'serial' and line.lot_name:
                next_serial_number = product.next_serial_number + 1
                product.sudo().write({'next_serial_number': next_serial_number})
        return mls
    
    def write(self, vals):
        for line in self:
            if not line.lot_name and vals.get('lot_name'):
                product = line.product_id
                product.sudo().write({'next_serial_number': product.next_serial_number + 1})
        return super().write(vals)
    
