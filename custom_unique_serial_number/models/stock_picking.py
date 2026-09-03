from odoo import fields, api, models
from datetime import date, timedelta

class StockPicking(models.Model):    
    _inherit = "stock.picking"

    staff_location_id = fields.Many2one('staff.location', string="Document Location")
