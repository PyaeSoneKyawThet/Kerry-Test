from odoo import api, fields, models, SUPERUSER_ID, _

class VASReason(models.Model):
    _name = 'vas.reason'
    _description = 'VAS Reason'
    
    so_id = fields.Many2one('sale.order', string="Sale Order")
    reason = fields.Char(string="Reason")
    state = fields.Selection([('vas_requested', 'Requested'), 
                            ('vas_approved', 'Approved'), 
                            ('vas_rejected', 'Rejected')], default='') 