from odoo import _, api, fields, models

class Picking(models.Model):
    _inherit='stock.picking'
    
    total_quantity = fields.Float(string="Total Quantity", compute="_compute_total_quantity")
    total_demand_quantity = fields.Float(string="Total Demand", compute="_compute_total_quantity")

    @api.depends('move_ids_without_package.quantity', 'move_ids_without_package.product_uom_qty')
    def _compute_total_quantity(self):
        for record in self:
            record.total_quantity = sum(line.quantity for line in record.move_ids_without_package)
            record.total_demand_quantity = sum(line.product_uom_qty for line in record.move_ids_without_package)
