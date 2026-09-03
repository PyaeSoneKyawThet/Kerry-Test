# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

class StockAssignSerialNumbers(models.TransientModel):
    _inherit = 'stock.assign.serial'

    def _default_next_serial_number(self):
        move = self.env['stock.move'].browse(self.env.context.get('default_move_id'))
        if move.exists():
            # Get document location code
            document_location_code = move.picking_id.staff_location_id.code

            # Get document location line(fixed_asset') code
            document_location_line = self.env['document.location.line'].search([('staff_location_id','=',move.picking_id.staff_location_id.id),("operation_type", "=", 'fixed_asset')],limit=1)
            staff_location_prefix = document_location_line.staff_location_prefix
            
            # Get product's item_code and serial_number
            item_code = move.product_id.item_code
            next_serial_number = move.product_id.next_serial_number
            prefix_number = str(next_serial_number).zfill(5)

            unique_serial = f"{staff_location_prefix}-{document_location_code}-{item_code}-{prefix_number}"
            return unique_serial
        
    next_serial_number = fields.Char('First SN', default=_default_next_serial_number,required=True)