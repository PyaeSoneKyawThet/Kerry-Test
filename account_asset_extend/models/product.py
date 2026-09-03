from odoo import fields, api, models , _


class ProductProduct(models.Model):
    _inherit = "product.product"

    asset_model_id = fields.Many2one('account.asset', string="Asset Model")

class ProductTemplate(models.Model):
    _inherit = "product.template"

    asset_model_id = fields.Many2one('account.asset', string="Asset Model")
