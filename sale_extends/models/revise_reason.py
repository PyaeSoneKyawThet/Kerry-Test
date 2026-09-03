from odoo import api, fields, models, SUPERUSER_ID, _

class ReviseReason(models.Model):
    _name = 'revise.reason'
    _description = 'Revise Reason'
    
    so_id = fields.Many2one('sale.order', string="Sale Order")
    reason = fields.Char(string="Reason")
    state = fields.Selection([('revise_requested', 'Requested'), 
                            ('revise_approved', 'Revised'), 
                            ('revise_rejected', 'Rejected')], default='') 