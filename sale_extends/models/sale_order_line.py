from odoo import models, fields, api

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    cost = fields.Float(string='Cost')
    gross_profit = fields.Float(string='Gross Profit', compute='_compute_gross_profit', store=True)
    remark = fields.Html(string="Remark") 
    sequence_no = fields.Integer(string="No", compute="_compute_sequence_no", store=False)

    @api.depends('order_id', 'order_id.order_line')
    def _compute_sequence_no(self):
        for line in self:
            line.sequence_no = 0
        for order in self.mapped('order_id'):
            line_no = 1
            for order_line in order.order_line:
                if order_line.display_type == 'line_section':
                    line_no = 1
                    order_line.sequence_no = 0
                else:
                    order_line.sequence_no = line_no
                    line_no += 1

    @api.depends('price_unit', 'cost')
    def _compute_gross_profit(self):
        for line in self:
            line.gross_profit = line.price_unit - line.cost 

