from odoo import fields, api, models, _
from odoo.exceptions import UserError, ValidationError

class HrEmployee(models.Model):
    _inherit = 'hr.employee'
    _parent_store = True
    
    parent_path = fields.Char(index=True, unaccent=False) 
    parent_ids = fields.Many2many('hr.employee', compute='_compute_parent_ids', compute_sudo=True)
    user_ids = fields.Many2many('res.users', compute='_compute_user_ids', string="Users")
    
    @api.depends('parent_path')
    def _compute_parent_ids(self):
        for rec in self:
            rec.parent_ids = self.browse(int(id) for id in rec.parent_path.split('/') if id).ids[:-1] if rec.parent_path else rec
                       
    @api.depends('parent_ids')
    def _compute_user_ids(self):
        for rec in self: 
            rec.user_ids = rec.parent_ids.filtered(lambda x: x.user_id).mapped('user_id').ids       