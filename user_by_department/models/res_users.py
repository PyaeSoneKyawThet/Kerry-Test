from odoo import fields, models, api

class ResUsers(models.Model):
    _inherit = "res.users"

    department_ids = fields.Many2many('hr.department',string="Allowed Departments")

    @api.onchange('department_ids')
    def _clear_rule_cache_dept(self):
        self.env.registry.clear_cache()