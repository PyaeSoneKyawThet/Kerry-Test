from odoo import api, fields, models, _

class SaleOrderTemplate(models.Model):
    _inherit = 'sale.order.template'
    
    quotation_header = fields.Html(string="Quotation Header")