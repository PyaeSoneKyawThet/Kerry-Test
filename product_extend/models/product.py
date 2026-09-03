from odoo import fields, api, models , _


class ProductProduct(models.Model):
    _inherit = "product.product"

    is_advance = fields.Boolean(string="Advance",related="product_tmpl_id.is_advance")

class ProductTemplate(models.Model):
    _inherit = "product.template"

    is_advance = fields.Boolean(string="Advance")
