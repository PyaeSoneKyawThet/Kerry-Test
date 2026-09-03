from odoo import fields, api, models , _

class StockMove(models.Model):
    _inherit = "stock.move"

    model_serial_no = fields.Char(string="Model Serial No")

    def _prepare_move_line_vals(self, quantity=None, reserved_quant=None):
        vals = super()._prepare_move_line_vals(quantity=quantity, reserved_quant=reserved_quant)
        vals['model_serial_no'] = self.model_serial_no
        return vals
    
    # for backorder
    def _prepare_move_split_vals(self, qty):
        vals = super()._prepare_move_split_vals(qty)
        vals.update({
            'model_serial_no': self.model_serial_no,
        })
        return vals

    
