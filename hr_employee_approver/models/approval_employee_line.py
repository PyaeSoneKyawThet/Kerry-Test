from odoo import api, fields, models, _
from odoo.exceptions import UserError

class ApprovalEmployeeLine(models.Model):
    _name = 'approval.employee.line'
    _description = "Approval Employee Line"
    
    employee_id = fields.Many2one('hr.employee', string='Employee')
    approval_user_ids = fields.Many2many('res.users', string="Approvers")
    approval_employee_id = fields.Many2one('res.users', string="Approver", 
                                           default=lambda self: self.env.user)
    approver_type = fields.Selection([('approver', 'Approver'), ('checker', 'Checker')])
    sequence = fields.Integer(default=1)

    @api.onchange('approval_user_ids')
    def onchange_approval_user_ids(self):
        for rec in self:
            app_user_len = len(rec.approval_user_ids)
            if app_user_len > 0:
                rec.approval_employee_id = rec.approval_user_ids[app_user_len-1]