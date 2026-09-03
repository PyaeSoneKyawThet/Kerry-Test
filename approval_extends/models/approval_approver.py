# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError

class ApprovalApprover(models.Model):
    _inherit = 'approval.approver'
    
    user_ids = fields.Many2many('res.users', 'approver_approval_req_rel', string="Users")
    user_id = fields.Many2one('res.users', string="User", required=False, check_company=True)
    status = fields.Selection(selection_add=[('to_check', 'To Checked'), ('checked', 'Checked')])
    level = fields.Integer(string="Level", default=1)

    def _create_activity(self):
        for approver in self:
            if approver.request_id.category_id.approval_type != 'purchase_req':
                approver.request_id.activity_schedule(
                    'approvals.mail_activity_data_approval',
                    user_id=approver.user_id.id
                )
            else:
                for user in approver.user_ids:
                    approver.request_id.activity_schedule(
                        'approvals.mail_activity_data_approval',
                        user_id=user.id
                    ) 
       
class CashExpenseApprover(models.Model):
    _name = 'cash.advance.approver'
    _description = 'Cash Advance Approver'
    _order = 'sequence, id'

    _check_company_auto = True

    sequence = fields.Integer('Sequence', default=10)
    level = fields.Integer(string="Level", default=1)
    user_ids = fields.Many2many('res.users', 'cash_addvance_approver_users_rel', string="Users")
    user_id = fields.Many2one('res.users', string="User", required=False, check_company=True, domain="[('id', 'not in', existing_request_user_ids)]")
    existing_request_user_ids = fields.Many2many('res.users', compute='_compute_existing_request_user_ids')
    status = fields.Selection([
        ('new', 'New'),
        ('to_check', 'To Checked'), 
        ('checked', 'Checked'),
        ('pending', 'To Approve'), 
        ('waiting', 'Waiting'),
        ('approved', 'Approved'),
        ('refused', 'Refused'),
        ('cancel', 'Cancel')], string="Status", default="new", readonly=True)
    request_id = fields.Many2one('approval.request', string="Request",
        ondelete='cascade', check_company=True)
    company_id = fields.Many2one(
        string='Company', related='cash_advance_id.company_id',
        store=True, readonly=True, index=True)
    required = fields.Boolean(default=False, readonly=True)
    category_approver = fields.Boolean(compute='_compute_category_approver')
    can_edit = fields.Boolean(compute='_compute_can_edit')
    can_edit_user_id = fields.Boolean(compute='_compute_can_edit', help="Simple users should not be able to remove themselves as approvers because they will lose access to the record if they misclick.")
    cash_advance_id = fields.Many2one('cash.advance.form', string="Cash Advance",
        ondelete='cascade', check_company=True)
    

    def action_approve(self):
        self.cash_advance_id.action_approve(self)

    def action_refuse(self):
        self.cash_advance_id.action_refuse(self)

    def _create_activity(self):
        for cash_approver in self:
            for user in cash_approver.user_ids:
                cash_approver.cash_advance_id.activity_schedule(
                    'approval_extends.mail_activity_data_cash_advance_kmtl',
                    user_id=user.id
                ) 

    @api.depends('cash_advance_id.request_owner_id', 'cash_advance_id.approver_ids.user_id')
    def _compute_existing_request_user_ids(self):
        for approver in self:
            approver.existing_request_user_ids = \
                self.mapped('cash_advance_id.approver_ids.user_id')._origin \
              | self.cash_advance_id.request_owner_id._origin

    @api.depends('category_approver', 'user_id')
    def _compute_category_approver(self):
        for approval in self:
            approval.category_approver = approval.user_id in approval.cash_advance_id.category_id.approver_ids.user_id

    @api.depends_context('uid')
    @api.depends('user_id', 'category_approver')
    def _compute_can_edit(self):
        is_user = self.env.user.has_group('approvals.group_approval_user')
        for approval in self:
            approval.can_edit = not approval.user_id or not approval.category_approver or is_user
            approval.can_edit_user_id = is_user or approval.cash_advance_id.request_owner_id == self.env.user or not approval.user_id


class ApprovalExpenseApprover(models.Model):
    _name = 'approval.expense.approver'
    _description = 'Approval Expense Approver'
    _order = 'sequence, id'

    _check_company_auto = True

    sequence = fields.Integer('Sequence', default=10)
    level = fields.Integer(string="Level", default=1)
    user_ids = fields.Many2many('res.users', 'approval_expense_approver_users_rel', string="Users")
    user_id = fields.Many2one('res.users', string="User", required=False, check_company=True, domain="[('id', 'not in', existing_request_user_ids)]")
    existing_request_user_ids = fields.Many2many('res.users', compute='_compute_existing_request_user_ids')
    status = fields.Selection([
        ('new', 'New'),
        ('pending', 'To Approve'), 
        ('waiting', 'Waiting'),
        ('to_check', 'To Check'),
        ('checked', 'Checked'),
        ('approved', 'Approved'),
        ('refused', 'Refused'),
        ('cancel', 'Cancel')
        ], string="Status", default="new", readonly=True)
    request_id = fields.Many2one('approval.request', string="Request",
        ondelete='cascade', check_company=True)
    company_id = fields.Many2one(
        string='Company', related='expense_id.company_id',
        store=True, readonly=True, index=True)
    required = fields.Boolean(default=False, readonly=True)
    category_approver = fields.Boolean(compute='_compute_category_approver')
    can_edit = fields.Boolean(compute='_compute_can_edit')
    can_edit_user_id = fields.Boolean(compute='_compute_can_edit', help="Simple users should not be able to remove themselves as approvers because they will lose access to the record if they misclick.")
    expense_id = fields.Many2one('approval.expense', string="Expense",
        ondelete='cascade', check_company=True)

    def action_approve(self):
        self.expense_id.action_approve(self) 

    def action_refuse(self):
        self.expense_id.action_refuse(self)

    def _create_activity(self):
        for exp_approver in self:
            for user in exp_approver.user_ids:
                exp_approver.expense_id.activity_schedule(
                    'approval_extends.mail_activity_data_approval_expense_kmtl',
                    user_id=user.id
                ) 

    @api.depends('expense_id.request_owner_id', 'expense_id.approver_ids.user_id')
    def _compute_existing_request_user_ids(self):
        for approver in self:
            approver.existing_request_user_ids = \
                self.mapped('expense_id.approver_ids.user_id')._origin \
              | self.expense_id.request_owner_id._origin

    @api.depends('category_approver', 'user_id')
    def _compute_category_approver(self):
        for approval in self:
            approval.category_approver = approval.user_id in approval.expense_id.category_id.approver_ids.user_id

    @api.depends_context('uid')
    @api.depends('user_id', 'category_approver')
    def _compute_can_edit(self):
        is_user = self.env.user.has_group('approvals.group_approval_user')
        for approval in self:
            approval.can_edit = not approval.user_id or not approval.category_approver or is_user
            approval.can_edit_user_id = is_user or approval.expense_id.request_owner_id == self.env.user or not approval.user_id

class ApprovalPaymentRequestApprover(models.Model):
    _name = 'approval.payment.request.approver'
    _description = 'Approval Payment Request Approver'
    _order = 'sequence, id'

    _check_company_auto = True

    sequence = fields.Integer('Sequence', default=10)
    level = fields.Integer(string="Level", default=1)
    user_ids = fields.Many2many('res.users', 'approval_payment_approver_users_rel', string="Users")
    user_id = fields.Many2one('res.users', string="User", required=True, check_company=True, domain="[('id', 'not in', existing_request_user_ids)]")
    existing_request_user_ids = fields.Many2many('res.users', compute='_compute_existing_request_user_ids')
    status = fields.Selection([
        ('new', 'New'),
        ('pending', 'To Approve'), 
        ('waiting', 'Waiting'),
        ('to_check', 'To Check'),
        ('checked', 'Checked'),
        ('approved', 'Approved'),
        ('refused', 'Refused'),
        ('cancel', 'Cancel')
        ], string="Status", default="new", readonly=True)
    request_id = fields.Many2one('approval.request', string="Request",
        ondelete='cascade', check_company=True)
    company_id = fields.Many2one(
        string='Company', related='approval_payment_request_id.company_id',
        store=True, readonly=True, index=True)
    required = fields.Boolean(default=False, readonly=True)
    category_approver = fields.Boolean(compute='_compute_category_approver')
    can_edit = fields.Boolean(compute='_compute_can_edit')
    can_edit_user_id = fields.Boolean(compute='_compute_can_edit', help="Simple users should not be able to remove themselves as approvers because they will lose access to the record if they misclick.")
    approval_payment_request_id = fields.Many2one('approval.payment.request', string="Payment Request",
        ondelete='cascade', check_company=True)

    def action_approve(self):
        self.approval_payment_request_id.action_approve(self) 

    def action_refuse(self):
        self.approval_payment_request_id.action_refuse(self)

    def _create_activity(self):
        for pay_approver in self:
            for user in pay_approver.user_ids:
                pay_approver.approval_payment_request_id.activity_schedule(
                    'approval_extends.mail_activity_data_approval_payment_request_kmtl',
                    user_id=user.id
                ) 

    @api.depends('approval_payment_request_id.request_owner_id', 'approval_payment_request_id.approver_ids.user_id')
    def _compute_existing_request_user_ids(self):
        for approver in self:
            approver.existing_request_user_ids = \
                self.mapped('approval_payment_request_id.approver_ids.user_id')._origin \
              | self.approval_payment_request_id.request_owner_id._origin

    @api.depends('category_approver', 'user_id')
    def _compute_category_approver(self):
        for approval in self:
            approval.category_approver = approval.user_id in approval.approval_payment_request_id.category_id.approver_ids.user_id

    @api.depends_context('uid')
    @api.depends('user_id', 'category_approver')
    def _compute_can_edit(self):
        is_user = self.env.user.has_group('approvals.group_approval_user')
        for approval in self:
            approval.can_edit = not approval.user_id or not approval.category_approver or is_user
            approval.can_edit_user_id = is_user or approval.approval_payment_request_id.request_owner_id == self.env.user or not approval.user_id