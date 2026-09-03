from odoo import fields, api, models , _

class HrEmployee(models.Model): 
    _inherit = 'hr.employee'  

    digital_signature = fields.Binary(string="Digital Signature")
    