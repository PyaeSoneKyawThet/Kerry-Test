from odoo import fields, api, models , _

class ProductCategroy(models.Model):
    _inherit = 'product.category' 
    _rec_name = 'name' 
    
    note = fields.Html(string="Notes") 
    show_in_quotation = fields.Boolean(string="Show in Quotation", default=False)

    @api.depends('name', 'parent_id.complete_name')
    def _compute_complete_name(self):
        for category in self:
            category.complete_name = category.name