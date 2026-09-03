from odoo import api, fields, models, SUPERUSER_ID, _

class ContainerType(models.Model):
    _name = 'container.type'
    _description = "Container Type"
    _rec_name = "name"
    
    name = fields.Char(string='Container Type')    