from odoo import fields, api, models , _
from odoo.exceptions import ValidationError

class ProductTemplate(models.Model):
    _inherit = "product.template"

    item_code = fields.Char(string="Item Code", index=True)
    next_serial_number = fields.Integer(string="Next Serial Number", default=1, copy=False)
    count = fields.Boolean("Count")
    
    def action_generate_item_code(self):
        for rec in self:
            if not rec.count:
                new_code = self.env['ir.sequence'].next_by_code('product.item.code')
                rec.item_code = new_code
                rec.count = True

    @api.constrains('item_code')
    def _check_unique_item_code(self):
        for rec in self:
            if rec.item_code and self.search_count([('item_code', '=', rec.item_code), ('id', '!=', rec.id)]):
                raise ValidationError("This Item Code already exists. Please use a unique code.")


