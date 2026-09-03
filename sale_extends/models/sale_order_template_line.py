from odoo import api, fields, models, _

class SaleOrderTemplateLine(models.Model):
    _inherit = 'sale.order.template.line'
    
    categ_id = fields.Many2one('product.category', string="Product Category")   

    def _prepare_order_line_values(self):
        res = super(SaleOrderTemplateLine, self)._prepare_order_line_values()
        res['categ_id'] = self.categ_id.id
        return res