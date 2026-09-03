from odoo import api, fields, models, SUPERUSER_ID, _

class VehicleType(models.Model):
    _name = 'vehicle.type'
    _description = "Vehicle Type"
    _rec_name = "name"
    
    name = fields.Char(string='Vehicle Type')       