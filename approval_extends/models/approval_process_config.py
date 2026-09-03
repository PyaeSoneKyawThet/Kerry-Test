from odoo import api, fields, models, _
from odoo.exceptions import UserError

class ApprovalProcessConfig(models.Model):
    _name = 'approval.process.config'
    _description = "Approval Process Config"
    
    approval_categ_id = fields.Many2one('approval.category', string='Approval Types')   

    from_amount = fields.Float(string="From Amount")
    to_amount = fields.Float(string="To Amount")
    currency_id = fields.Many2one('res.currency', string="Currency")
    checker = fields.Integer(string="Checker")
    approver = fields.Integer(string="Approver")  
    from_level = fields.Integer(string="From Level", default=1)
    to_level = fields.Integer(string="To Level", default=1) 
    expense_range = fields.Selection([('under', 'Under'), 
                                       ('over', 'Over')],string="Expense Range") 
    # no_of_approval = fields.Integer(string="No. of Approval") 
    need_approval = fields.Boolean(string="Need Approval", default=True)
    department_ids = fields.Many2many("hr.department", 'config_id', 'dept_id', 'config_dept_rel', string="Departments")