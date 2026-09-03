from odoo import fields, api, models, _,Command
from itertools import groupby
from operator import itemgetter
from odoo.exceptions import UserError, ValidationError

class AccountMove(models.Model):     
    _inherit = "account.move"

    @api.model
    def _read_group_request_status(self, stages, domain, order):
        request_status_list = dict(self._fields['request_status'].selection).keys()
        return request_status_list

    name = fields.Char(
            string='Number',
            compute='_compute_name', inverse='_inverse_name', readonly=False, store=True,
            copy=False,
            tracking=True,
            index='trigram', default='/'
        )
    attention_to = fields.Char(string="Attention To", related="partner_id.contact_person")
    # contact_person = fields.Char(string="Contact Person", related="partner_id.contact_person")    
    advance_non_ct_total = fields.Monetary(string='Advance Non CT Total', compute='_compute_advance_non_ct_amount', store=True)
    non_ct_total = fields.Monetary(string='Non CT Total', compute='_compute_non_ct_amount', store=True)
    ct_total = fields.Monetary(string='CT Total',compute='_compute_ct_amount', store=True)

    advance_non_ct_tax_total = fields.Monetary(string='Advance non ct tax total', compute="_compute_advance_non_ct_tax_total")
    ct_tax_total = fields.Monetary(string='Advance ct tax total',compute="_compute_ct_tax_total")

    customer_invoice_format_line_ids = fields.One2many('account.customer.move.line', 'move_id', string='Invoice Print Lines', copy=True, readonly=True)
    account_payment_type_id = fields.Many2one('account.payment.type', string="Custom Payment Type", copy=False)
    is_internal_wrong = fields.Boolean(string="Internal Wrong", default=True, store=True)
    vendor_quotation_no = fields.Char(string="Vendor Quotation No")
    vendor_invoice_no = fields.Char(string="Vendor Invoice No")
    bill_type = fields.Selection([('vendor_bill', 'Vendor Bill'),  
                                       ('petty_cash', 'Petty Cash'), 
                                       ('petty_cash_with_ca', 'Petty Cash With CA'),
                                       ], default='vendor_bill', tracking=True, copy=False) 
    
    debit_note_type = fields.Selection([('debit_note', 'Debit Note'),  
                                       ('petty_cash_debit_note', 'Petty Cash Debit Note'), 
                                       ], default='debit_note') 
    internal_reference = fields.Char(string="Internal Reference")

    approved_by_id = fields.Many2one('res.users', string="Approved By", tracking=True, help="Approved user, show only in print.") 
    invoice_submit_date = fields.Date(string="Invoice Submit Date", help="Invoice Submitted date, show only in print.")
    invoice_check_date = fields.Date(string="Invoice Check Date", help="Invoice Checked date, show only in print.")
    invoice_approved_date = fields.Date(string="Invoice Approved Date", help="Invoice Approved date, show only in print.")
    request_status = fields.Selection([
                                    ('new', 'To Submit'),
                                    ('pending', 'Submitted'), 
                                    ('checked', 'Checking'),
                                    ('approved', 'Approved'),
                                    ('refused', 'Refused'),
                                    ('cancel', 'Cancel'),
                                    ], default="new", compute="_compute_request_status",
                                    store=True, index=True, tracking=True,
                                    group_expand='_read_group_request_status', string="Request Status")
    user_status = fields.Selection([
                                    ('new', 'New'),
                                    ('pending', 'To Approve'),
                                    ('waiting', 'Waiting'), 
                                    ('to_check','To Check'),
                                    ('checked','Checked'),
                                    ('approved', 'Approved'),
                                    ('refused', 'Refused'),
                                    ('cancel', 'Cancel')
                                    ], compute="_compute_user_status")
    bill_approver_ids = fields.One2many('bill.approver.line', 'account_move_id', compute="_compute_bill_approver_ids",store=True, readonly=False)
    minimal_approver = fields.Integer(string="Minimal Approvers", default=1)
    minimal_checker = fields.Integer(string="Minimal Checkers", compute="_compute_minimal_checker")
    invoice_approver_ids = fields.One2many('invoice.approver.line', 'account_move_id', compute="_compute_invoice_approver_ids",store=True, readonly=False)
    submit_user_id = fields.Many2one('res.users',string="Submit User", copy=False)
    staff_location_id = fields.Many2one('staff.location', string="Doc Location")
    available_reverse_ids = fields.Many2many('account.move', compute="_compute_available_reverse_ids", string="Available Reverses")

    @api.depends('move_type')
    def _compute_available_reverse_ids(self):
        for rec in self:
            if rec.move_type == 'out_refund':
                rec.available_reverse_ids = self.env['account.move'].search([('move_type', '=', 'out_invoice'), ('state', '=', 'posted')])
            elif rec.move_type == 'in_refund':
                rec.available_reverse_ids = self.env['account.move'].search([('move_type', '=', 'in_invoice'), ('state', '=', 'posted')])
            else:
                rec.available_reverse_ids = False
            
    
    @api.depends('submit_user_id')
    def _compute_bill_approver_ids(self):
        for rec in self:
            approver_id_vals = [Command.clear()]  
            approver_approvers = rec.submit_user_id.employee_id.bill_approver_ids.sorted(key=lambda a: a.sequence)
            for approver in approver_approvers:     
                if approver.approval_user_ids.ids:               
                    approver_id_vals.append(Command.create({
                        'approval_user_ids': [(6, 0, approver.approval_user_ids.ids)],
                        'approval_employee_id': approver.approval_user_ids[:1].id if approver.approval_user_ids else False,
                        'status': 'new',
                        'sequence': approver.sequence,
                        'account_move_id': rec.id,
                    }))
            rec.bill_approver_ids = approver_id_vals

    @api.depends('posted_before', 'state', 'journal_id', 'date', 'move_type', 'payment_id')
    def _compute_name(self):
        self = self.sorted(lambda m: (m.date, m.ref or '', m._origin.id))
        for move in self:
            if move.move_type == 'entry':
                if move.state == 'cancel':
                    continue

                move_has_name = move.name and move.name != '/'
                if move_has_name or move.state != 'posted':
                    if not move.posted_before and not move._sequence_matches_date():
                        if move._get_last_sequence():
                            # The name does not match the date and the move is not the first in the period:
                            # Reset to draft
                            move.name = False
                            continue
                    else:
                        if move_has_name and move.posted_before or not move_has_name and move._get_last_sequence():
                            # The move either
                            # - has a name and was posted before, or
                            # - doesn't have a name, but is not the first in the period
                            # so we don't recompute the name
                            continue
                if move.date and (not move_has_name or not move._sequence_matches_date()):
                    if move.journal_id.type not in ('purchase', 'sale', 'bank', 'cash'):
                        move._set_next_sequence()
                    else:
                        move.name = '/'
            else:
                move.name = '/' if move.name in ('draft', '/') else move.name

        self.filtered(lambda m: not m.name and not move.quick_edit_mode).name = '/'
        self._inverse_name()

    
    @api.depends('submit_user_id')
    def _compute_invoice_approver_ids(self):
        for rec in self:
            approver_id_vals = [Command.clear()]  
            approver_approvers = rec.submit_user_id.employee_id.invoice_approver_ids.sorted(key=lambda a: a.sequence)
            for approver in approver_approvers:    
                if approver.approval_user_ids.ids:                
                    approver_id_vals.append(Command.create({
                        'approval_user_ids': [(6, 0, approver.approval_user_ids.ids)],
                        'approval_employee_id': approver.approval_user_ids[:1].id if approver.approval_user_ids else False,
                        'status': 'new',
                        'sequence': approver.sequence,
                        'account_move_id': rec.id,
                    }))
            rec.invoice_approver_ids = approver_id_vals

    @api.depends('bill_approver_ids','invoice_approver_ids')
    def _compute_minimal_checker(self):
        for rec in self:  
            if rec.move_type in ['in_invoice', 'in_refund']:
                rec.minimal_checker = len(rec.bill_approver_ids[:-1]) if rec.bill_approver_ids else 0 
            elif rec.move_type in ['out_invoice', 'out_refund']:
                rec.minimal_checker = len(rec.invoice_approver_ids[:-1]) if rec.invoice_approver_ids else 0
            else:
                rec.minimal_checker = 0

    @api.depends_context('uid')
    @api.depends('bill_approver_ids.status','invoice_approver_ids.status')
    def _compute_user_status(self):
        for move in self:
            if move.move_type in ['in_invoice', 'in_refund']:
                approvers = move.bill_approver_ids.filtered(
                    lambda approver: self.env.user in approver.approval_user_ids
                )
                move.user_status = approvers[:1].status if approvers else False
            elif move.move_type in ['out_invoice', 'out_refund']:
                approvers = move.invoice_approver_ids.filtered(
                    lambda approver: self.env.user in approver.approval_user_ids
                )
                move.user_status = approvers[:1].status if approvers else False
            else:
                move.user_status = 'new'

    @api.depends('bill_approver_ids.status','invoice_approver_ids.status','state')
    def _compute_request_status(self):
        for request in self:
            if request.move_type in ['in_invoice', 'in_refund']:
                status_lst = request.mapped('bill_approver_ids.status')
            elif request.move_type in ['out_invoice', 'out_refund']:
                status_lst = request.mapped('invoice_approver_ids.status')
            else:
                status_lst = []
            minimal_approver = request.minimal_approver if len(status_lst) >= request.minimal_approver else len(status_lst)
            minimal_checker = request.minimal_checker if len(status_lst) >= request.minimal_checker else len(status_lst)
            if status_lst and request.state not in ['posted','cancel']:
                if status_lst.count('cancel'):
                    status = 'cancel'
                elif status_lst.count('refused'):
                    status = 'refused'
                elif status_lst.count('new'):
                    status = 'new'
                elif status_lst.count('approved') >= minimal_approver:
                    status = 'approved'
                elif status_lst.count('checked') >= minimal_checker:
                    status = 'checked'
                else:
                    status = 'pending'
            elif request.state == 'posted':
                 status = 'approved'
            elif request.state == 'cancel':
                 status = 'cancel'
            else:
                status = 'new'
            request.request_status = status
        self.filtered_domain([('request_status', 'in', ['approved', 'refused', 'cancel'])])._cancel_activities()
    
    #------------------------------------------------------------
    # helper method for multi approver in invoice,bill Task: 2775
    #------------------------------------------------------------
    def _cancel_activities(self):
        approval_activity = self.env.ref('approvals.mail_activity_data_approval')
        activities = self.activity_ids.filtered(lambda a: a.activity_type_id == approval_activity)
        activities.unlink()

    def _get_user_approval_activities(self, user):
        domain = [
            ('res_model', '=', 'account.move'),
            ('res_id', 'in', self.ids),
            ('activity_type_id', '=', self.env.ref('account_move_extends.mail_activity_data_account_move_kmtl').id),
            ('user_id', '=', user.id)
        ]
        activities = self.env['mail.activity'].search(domain)
        return activities 
    
    def _ensure_can_check(self):
        if any(approval.user_status == 'waiting' for approval in self):
            raise ValidationError(_('You cannot check before the previous checker.'))

    def _update_next_checkers(self, new_status, checker, only_next_checker, cancel_activities=False):
        if self.move_type in ['in_invoice', 'in_refund']:
            checkers_updated = self.env['bill.approver.line']
            for move in self:
                current_checker = move.bill_approver_ids & checker
                checkers_to_update = move.bill_approver_ids.filtered(lambda a: a.status not in ['approved', 'refused'] \
                                    and (a.sequence > current_checker.sequence \
                                    or (a.sequence == current_checker.sequence and a.id > current_checker.id)))

                if only_next_checker and checkers_to_update:
                    checkers_to_update = checkers_to_update[0]
                checkers_updated |= checkers_to_update
        elif self.move_type in ['out_invoice', 'out_refund']:
            checkers_updated = self.env['invoice.approver.line']
            for move in self:
                current_checker = move.invoice_approver_ids & checker
                checkers_to_update = move.invoice_approver_ids.filtered(lambda a: a.status not in ['approved', 'refused'] \
                                    and (a.sequence > current_checker.sequence \
                                    or (a.sequence == current_checker.sequence and a.id > current_checker.id)))

                if only_next_checker and checkers_to_update:
                    checkers_to_update = checkers_to_update[0]
                checkers_updated |= checkers_to_update

        checkers_updated.sudo().status = new_status
        checkers_updated.sudo()._create_activity()
        if cancel_activities:
            checkers_updated.account_move_id._cancel_activities()

    def _ensure_can_approve(self):
        if any(approval.user_status == 'waiting' for approval in self):
            raise ValidationError(_('You cannot approve before the previous approver.'))
        
    def _update_next_approvers(self, new_status, approver, only_next_approver, cancel_activities=False):
        if self.move_type in ['in_invoice', 'in_refund']:
            approvers_updated = self.env['bill.approver.line']
            for approval in self:
                current_approver = approval.bill_approver_ids & approver
                approvers_to_update = approval.bill_approver_ids.filtered(lambda a: a.status not in ['approved', 'refused'] and (a.sequence > current_approver.sequence or (a.sequence == current_approver.sequence and a.id > current_approver.id)))

                if only_next_approver and approvers_to_update:
                    approvers_to_update = approvers_to_update[0]
                approvers_updated |= approvers_to_update
        elif self.move_type in ['out_invoice', 'out_refund']:
            approvers_updated = self.env['invoice.approver.line']
            for approval in self:
                current_approver = approval.invoice_approver_ids & approver
                approvers_to_update = approval.invoice_approver_ids.filtered(lambda a: a.status not in ['approved', 'refused'] and (a.sequence > current_approver.sequence or (a.sequence == current_approver.sequence and a.id > current_approver.id)))

                if only_next_approver and approvers_to_update:
                    approvers_to_update = approvers_to_update[0]
                approvers_updated |= approvers_to_update

        approvers_updated.sudo().status = new_status
        if new_status == 'pending':
            approvers_updated._create_activity()
        if cancel_activities:
            approvers_updated.account_move_id._cancel_activities()
    
    #----------------------------------------------------------
    # main method for multi approver in invoice,bill Task: 2775
    #----------------------------------------------------------
    def action_submit(self):
        self.submit_user_id = self.env.user
        if not self.invoice_line_ids: 
                raise UserError(_("You need to add a line before posting."))
        
        if self.move_type in ['in_invoice', 'in_refund']:
            approvers = self.bill_approver_ids
        elif self.move_type in ['out_invoice', 'out_refund']:
            approvers = self.invoice_approver_ids

        approvers = approvers.filtered(lambda a: a.status in ['new', 'to_check', 'pending', 'waiting'])
        if not approvers:
            raise ValidationError(_("Can't submit without approver!"))
        
        status  = 'pending' if len(approvers) == 1 else 'to_check'
        approvers[1:].sudo().write({'status': 'waiting'})
        
        if self.move_type in ['in_invoice', 'in_refund']:
            approvers = approvers[0] if approvers and approvers[0].status != 'to_check' else self.env['bill.approver.line']
        elif self.move_type in ['out_invoice', 'out_refund']:
            approvers = approvers[0] if approvers and approvers[0].status != 'to_check' else self.env['invoice.approver.line']

        approvers._create_activity()
        approvers.sudo().write({'status': status})
        self.sudo().invoice_submit_date = fields.Date.today()
        # self.sudo()._get_user_approval_activities(user=self.env.user).action_feedback()
        return True

    def action_check(self, checker=None):
        self._ensure_can_check()   
        if self.move_type in ['in_invoice', 'in_refund']:     
            if not isinstance(checker, models.BaseModel):
                checker = self.mapped('bill_approver_ids').filtered(
                    lambda checker: self.env.user in checker.approval_user_ids)
            checker.status = 'checked'
            status_lst = self.mapped('bill_approver_ids.status')
            for user in checker.approval_user_ids:
                self.sudo()._get_user_approval_activities(user=user).action_feedback()

        if self.move_type in ['out_invoice', 'out_refund']:     
            if not isinstance(checker, models.BaseModel):
                checker = self.mapped('invoice_approver_ids').filtered(
                    lambda checker: self.env.user in checker.approval_user_ids)
            checker.status = 'checked'
            status_lst = self.mapped('invoice_approver_ids.status')
            for user in checker.approval_user_ids:
                self.sudo()._get_user_approval_activities(user=user).action_feedback()

        if status_lst.count('checked') >= (self.minimal_checker):
            self.sudo()._update_next_checkers('pending', checker, only_next_checker=True)
        else:
            self.sudo()._update_next_checkers('to_check', checker, only_next_checker=True)
        self.sudo().invoice_check_date = fields.Date.today()

    def action_approve(self, approver=None):
        self._ensure_can_approve()
        if not isinstance(approver, models.BaseModel):
            if self.move_type in ['in_invoice', 'in_refund']:
                if not self.invoice_date:
                    raise UserError(_("Bill Date is required to approve this bill."))
                approver = self.mapped('bill_approver_ids').filtered(
                    lambda approver: self.env.user in approver.approval_user_ids
                )    
            elif self.move_type in ['out_invoice', 'out_refund']: 
                approver = self.mapped('invoice_approver_ids').filtered(
                    lambda approver: self.env.user in approver.approval_user_ids
                )  
        self.request_status = 'approved'
        self.approved_by_id = self.env.user.id
        approver.write({'status': 'approved'})
        self.sudo()._update_next_approvers('pending', approver, only_next_approver=True)
        self.sudo().invoice_approved_date = fields.Date.today()
        self.sudo()._get_user_approval_activities(user=self.env.user).action_feedback()
        self.sudo().action_post()
    
    def action_refuse(self, approver=None):
        if not isinstance(approver, models.BaseModel):
            if self.move_type in ['in_invoice', 'in_refund']:
                approver = self.mapped('bill_approver_ids').filtered(
                    lambda approver: self.env.user in approver.approval_user_ids
                ) 
            elif self.move_type in ['out_invoice', 'out_refund']:
                approver = self.mapped('invoice_approver_ids').filtered(
                    lambda approver: self.env.user in approver.approval_user_ids
                ) 
        approver.write({'status': 'refused'})
        self.sudo()._update_next_approvers('refused', approver, only_next_approver=False, cancel_activities=True)
        self.sudo()._get_user_approval_activities(user=self.env.user).action_feedback()
        self.request_status = 'refused'

    def action_cancel(self):
        self.sudo()._get_user_approval_activities(user=self.env.user).unlink()
        if self.move_type in ['in_invoice', 'in_refund']:
            self.mapped('bill_approver_ids').write({'status': 'cancel'})
        elif self.move_type in ['out_invoice', 'out_refund']:
            self.mapped('invoice_approver_ids').write({'status': 'cancel'})
        self.request_status = 'cancel'
        self.sudo().button_cancel()

    def button_draft(self):
        """ set the submit_user_id to recompute bill_approver_ids 
            set the submit_user_id to recompute invoice_approver_ids"""
        res = super().button_draft()
        self.submit_user_id = None
        return res
    
    # generate sequence : journal from dashboard
    #                   : reverse_journal of dashboard_journal
    def _generate_journal_sequence(self):
        journal_account_id = self.journal_id.default_account_id.id
        amount_currency = self.line_ids.filtered(lambda l: l.account_id.id == journal_account_id).amount_currency
        if amount_currency > 0:
            seq_number = self.env['ir.sequence'].next_by_code('customer.payment.with.journal')
            code = self.journal_id.code
        else:
            seq_number = self.env['ir.sequence'].next_by_code('vendor.payment.with.journal')
            code = self.journal_id.payment_short_code
        name = f"{code}{seq_number}"
        return name

    def action_post(self):
        if self.name in ('draft', '/'):
            # customer credit note
            if self.move_type == 'out_refund' and self.staff_location_id:
                if self.is_internal_wrong:
                    seq_number = self.env['staff.location'].search([('id', '=', self.staff_location_id.id)]).get_seq_number('internal_credit_note')
                else:
                    seq_number = self.env['staff.location'].search([('id', '=', self.staff_location_id.id)]).get_seq_number('credit_note')
                
            # invoice
            elif self.move_type == 'out_invoice' and self.staff_location_id:
                seq_number = self.env['staff.location'].search([('id', '=', self.staff_location_id.id)]).get_seq_number('invoice')
            #vendor bill
            elif self.move_type == 'in_invoice' and self.staff_location_id:
                self.sudo().invoice_submit_date = fields.Date.today()
                self.invoice_user_id = self.env.user.id
                if self.bill_type in ['vendor_bill']:
                    seq_number = self.env['staff.location'].search([('id', '=', self.staff_location_id.id)]).get_seq_number('vendor_bill')
                elif self.bill_type in ['petty_cash']:
                    seq_number = self.env['staff.location'].search([('id', '=', self.staff_location_id.id)]).get_seq_number('petty_cash') 
                elif self.bill_type in ['petty_cash_with_ca']:
                    seq_number = self.env['staff.location'].search([('id', '=', self.staff_location_id.id)]).get_seq_number('petty_cash_with_ca')  

            # vendor credit note
            elif self.move_type == 'in_refund' and self.staff_location_id:
                if self.debit_note_type in ['debit_note']:
                    if self.is_internal_wrong:
                        seq_number = self.env['staff.location'].search([('id', '=', self.staff_location_id.id)]).get_seq_number('internal_debit_note')
                    else:
                        seq_number = self.env['staff.location'].search([('id', '=', self.staff_location_id.id)]).get_seq_number('debit_note')
                if self.debit_note_type in ['petty_cash_debit_note']:
                    seq_number = self.env['staff.location'].search([('id', '=', self.staff_location_id.id)]).get_seq_number('petty_cash_debit_note')

            # journal entry from accounting dashboard
            elif self.move_type == 'entry' and (self.statement_line_id or (self.reversed_entry_id and self.journal_id.type in ('bank', 'cash'))):
                seq_number = self._generate_journal_sequence()

            elif self.move_type == 'entry':
                self._set_next_sequence()
                seq_number = self.name
            else:
                seq_number = self.name
            self.name = seq_number
        return super().action_post()
    
    # when journal is post from actions only for reverse
    def _post(self, soft=True):
        posted_move = super(AccountMove, self)._post(soft=soft)
        for move in posted_move:
            # reverse journal from 'journal_from_dashboard'
            if move.name in ('draft', '/') and move.move_type == 'entry' and move.state == 'posted' and move.reversed_entry_id and move.journal_id.type in ('bank', 'cash'):
                name = move._generate_journal_sequence()
                move.name = name
        return posted_move
    
    #---------------------------------------------------------------------------------------
    # Methods used for one approver in invoice, remove for multi approver feature TASK: 2775
    #---------------------------------------------------------------------------------------
    # @api.onchange('invoice_user_id')
    # def onchange_invoice_user_id(self):
    #     available_approvers = self.invoice_user_id.employee_id.user_ids.filtered(lambda x: x.employee_id.department_id.id  and x.employee_id.department_id.id == self.sale_person_department_id.id)
    #     if available_approvers:
    #         self.approved_by_id = available_approvers[:1].id
    #     else:
    #         self.approved_by_id = False 

    # def _compute_enable_approve(self): 
    #     for rec in self:
    #         if rec.approved_by_id.id == self.env.uid:
    #             rec.enable_approve = True
    #         else:
    #             rec.enable_approve = False 
    # def _get_user_approval_activities(self, user):
    #     domain = [
    #         ('res_model', '=', 'account.move'),
    #         ('res_id', 'in', self.ids),
    #         ('activity_type_id', '=', self.env.ref('account_move_extends.mail_activity_data_account_kmtl').id),
    #         ('user_id', '=', user.id)
    #     ]
    #     activities = self.env['mail.activity'].search(domain)
    #     return activities 
    
    # def action_submit(self):
    #     if self.move_type == 'out_invoice':
    #         if not self.approved_by_id:
    #             raise UserError(_("Can't submit invoice without approver!"))  
            
    #         if not self.invoice_line_ids: 
    #             raise UserError(_("You need to add a line before posting.")) 

    #         self.env['invoice.approval.reason'].create({'invoice_id': self.id, 'state': 'submitted'})
    #         self.sudo().approval_state = 'submitted' 
    #         self.sudo().invoice_submit_date = fields.Date.today()
    #         self.invoice_user_id = self.env.user
    #         available_approvers = self.invoice_user_id.employee_id.user_ids.filtered(lambda x: x.employee_id.department_id.id  and x.employee_id.department_id.id == self.sale_person_department_id.id)
    #         if available_approvers:
    #             self.approved_by_id = available_approvers[:1].id
    #         if self.approved_by_id:
    #             to_approver = self.approved_by_id.id
    #             self.activity_schedule('account_move_extends.mail_activity_data_account_kmtl',
    #                                         user_id=to_approver) 
    #     else:
    #         return super().action_post()
    
    # def action_resubmit(self):
    #     self.ensure_one()
    #     self.write({'approval_state': 're-submitted'})
    #     return {
    #         'name': "Invoice Resubmit Reason",
    #         'type': 'ir.actions.act_window',
    #         'view_mode': 'form',            
    #         'res_model': 'wizard.invoice.resubmit.reason',  
    #         'views': [(False, 'form')],
    #         'view_id' : 'view_form_resubmit_reason_wizard',       
    #         'target': 'new',           
    #         'context': {'default_invoice_id': self.id, 'default_state': 're-submitted'}            
    #     }
    
    # def action_approve(self):
    #     self.approval_state = 'approved'
    #     self.env['invoice.approval.reason'].create({
    #         'invoice_id': self.id,
    #         'state': self.approval_state
    #     })
    #     self.sudo()._get_user_approval_activities(user=self.env.user).action_feedback() 
    #     return self.action_post()
    
    # def action_reject(self):
    #     self.ensure_one()
    #     return {
    #         'name': "Inovice Reject Reason",
    #         'type': 'ir.actions.act_window',
    #         'view_mode': 'form',            
    #         'res_model': 'wizard.invoice.reject.reason',  
    #         'views': [(False, 'form')],
    #         'view_id' : 'view_form_reject_reason_wizard',       
    #         'target': 'new',           
    #         'context': {'default_invoice_id': self.id, 'default_state': 'rejected'}            
    #     }
    

    @api.depends('invoice_line_ids.product_id','invoice_line_ids.price_subtotal','invoice_line_ids.tax_ids')
    def _compute_ct_amount(self): 
        for rec in self:
            total = sum(line.price_subtotal for line in rec.invoice_line_ids if line.tax_ids and not line.product_id.is_advance)
            rec.ct_total = total

    @api.depends('invoice_line_ids.product_id','invoice_line_ids.price_subtotal','invoice_line_ids.tax_ids')
    def _compute_non_ct_amount(self):
        for rec in self:
            total = sum(line.price_subtotal for line in rec.invoice_line_ids if not line.tax_ids and not line.product_id.is_advance)
            rec.non_ct_total = total
            
    @api.depends('invoice_line_ids.product_id','invoice_line_ids.price_subtotal','invoice_line_ids.tax_ids','invoice_line_ids.price_total',)
    def _compute_advance_non_ct_amount(self): 
        for rec in self:
            total = sum(line.price_subtotal for line in rec.invoice_line_ids if line.product_id.is_advance)
            rec.advance_non_ct_total = total

    @api.depends('invoice_line_ids.product_id','invoice_line_ids.price_subtotal','invoice_line_ids.tax_ids')
    def _compute_advance_non_ct_tax_total(self):
        for rec in self:
            total = sum(line.price_total - line.price_subtotal for line in rec.invoice_line_ids if line.product_id.is_advance)
            rec.advance_non_ct_tax_total = total

    @api.depends('invoice_line_ids.product_id','invoice_line_ids.price_subtotal','invoice_line_ids.tax_ids')
    def _compute_ct_tax_total(self):
        for rec in self:
            total = sum(line.price_total - line.price_subtotal for line in rec.invoice_line_ids if line.tax_ids and not line.product_id.is_advance)
            rec.ct_tax_total = total
            
    @api.model_create_multi 
    def create(self, vals_list):
        for val in vals_list:
            val['customer_invoice_format_line_ids'] = []
        result = super(AccountMove,self).create(vals_list)
        for res in result:
            if res.move_type != 'entry':
                self.create_account_customer_invoice_line(res)
        return result
    
    def write(self, vals):
        res = super().write(vals)
        if "invoice_line_ids" in vals:
            if not self.state == 'posted' and self.move_type != 'entry':
                self.customer_invoice_format_line_ids.unlink()
                self.create_account_customer_invoice_line(self)
        return res
    
    # def _prepare_customer_line_format(self,invoice_line_ids):
    #     fields = ["product_id", "name", "account_id","analytic_distribution","price_unit","product_uom_id","tax_ids","currency_id","price_subtotal","price_total","quantity"]
    #     customer_lines = self.env['account.move.line'].search_read([('id', 'in', invoice_line_ids.ids)], order="id",fields=fields)
    #     for line in customer_lines:
    #         if line['product_id']: 
    #             line['name'] = line['name']
    #             line['product_id'] = line['product_id'][0]
    #         if line['account_id']:
    #             line['account_id'] = line['account_id'][0]
    #         if line['product_uom_id']:
    #             line['product_uom_id'] = line['product_uom_id'][0]
    #         if line['currency_id']:
    #             line['currency_id'] = line['currency_id'][0]
    #     return customer_lines
    
    # def create_account_customer_invoice_line(self,res):
    #     grouper = itemgetter("product_id", "name", "account_id", "tax_ids", "product_uom_id", "price_unit")
    #     customer_lines = self._prepare_customer_line_format(res.invoice_line_ids)
    #     for key, grp in groupby(sorted(customer_lines, key = grouper), grouper):
    #         temp_dict = dict(zip(["product_id", "name", "account_id", "tax_ids", "product_uom_id", "price_unit"], key))
    #         temp_dict_grp = list(grp)
    #         temp_dict["quantity"] = sum(item["quantity"] for item in temp_dict_grp)
    #         temp_dict["price_unit"] = temp_dict_grp[0]['price_unit']
    #         temp_dict["price_subtotal"] = sum(item["price_subtotal"] for item in temp_dict_grp)
    #         temp_dict["price_total"] = sum(item["price_total"] for item in temp_dict_grp)
    #         temp_dict['move_id'] = res.id
    #         temp_dict['analytic_distribution'] = temp_dict_grp[0]['analytic_distribution']
    #         tax_list = sum([item['tax_ids'] for item in temp_dict_grp],[])
    #         temp_dict['tax_ids'] = [(6,0, tax_list)]
    #         aml_list = sum([[item['id'] for item in temp_dict_grp]],[])
    #         temp_dict['aml_ids'] = [(6,0, aml_list)]
    #         temp_dict['name'] = temp_dict_grp[0]['name']
    #         self.env['account.customer.move.line'].create(temp_dict)

    def _prepare_customer_line_format(self, invoice_line_ids):
        fields = ["product_id", "name", "account_id", "analytic_distribution", "price_unit", 
                "product_uom_id", "tax_ids", "currency_id", "price_subtotal", "price_total", "quantity"]
        
        customer_lines = self.env['account.move.line'].search_read(
            [('id', 'in', invoice_line_ids.ids)], order="id", fields=fields)

        for line in customer_lines:
            if line['product_id']:
                line['product_id'] = line['product_id'][0]
            if line['account_id']:
                line['account_id'] = line['account_id'][0]
            if line['currency_id']:
                line['currency_id'] = line['currency_id'][0]
            if line['price_subtotal']:
                line['price_subtotal'] = line['price_subtotal'] 

            # Convert quantity to the base unit of the product
            product = self.env['product.product'].browse(line['product_id'])
            uom = self.env['uom.uom'].browse(line['product_uom_id'][0])

            if product and uom:
                # Convert the quantity to the base unit of measure 
                line['product_uom_id'] = product.uom_id.id 
                line['quantity'] = uom._compute_quantity(line['quantity'], product.uom_id)
            else:
                line['quantity'] = line['quantity']
                line['product_uom_id'] = line['product_uom_id'][0]
                

        return customer_lines

    def create_account_customer_invoice_line(self, res):
        grouper = itemgetter("product_id", "name", "account_id", "tax_ids", "product_uom_id")

        customer_lines = self._prepare_customer_line_format(res.invoice_line_ids)

        for key, grp in groupby(sorted(customer_lines, key=grouper), grouper):
            temp_dict = dict(zip(["product_id", "name", "account_id", "tax_ids", "product_uom_id"], key))
            temp_dict_grp = list(grp)

            temp_dict["quantity"] = sum(item["quantity"] for item in temp_dict_grp)

            temp_dict["price_subtotal"] = sum(item["price_subtotal"] for item in temp_dict_grp)
            temp_dict["price_total"] = sum(item["price_total"] for item in temp_dict_grp)

            temp_dict["move_id"] = res.id
            temp_dict["analytic_distribution"] = temp_dict_grp[0]["analytic_distribution"] 
            temp_dict["product_uom_id"] = temp_dict_grp[0]["product_uom_id"]  

            tax_list = sum([item["tax_ids"] for item in temp_dict_grp], [])
            temp_dict["tax_ids"] = [(6, 0, tax_list)]

            aml_list = sum([[item["id"] for item in temp_dict_grp]], [])
            temp_dict["aml_ids"] = [(6, 0, aml_list)]


            self.env["account.customer.move.line"].create(temp_dict)


    def action_print_ar_invoice(self):
        return self.env.ref('account_move_extends.ar_invoice_report').report_action(self)
    
    def action_print_ap_invoice(self):
        return self.env.ref('account_move_extends.ap_invoice_report').report_action(self)  

    def _reverse_moves(self, default_values_list=None, cancel=False):
        moves = super(AccountMove, self)._reverse_moves(default_values_list, cancel)
        for move in moves:
            if move.move_type == 'out_refund' and move.state == 'posted' and move.is_internal_wrong:  
                seq_number = self.env['staff.location'].search([('id', '=', self.staff_location_id.id)]).get_seq_number('internal_credit_note')
                move.name = seq_number
        return moves
      
class account(models.Model):
    _name = 'account.customer.move.line'
    _description = 'Invoice Print Lines'
    _inherit = 'analytic.mixin'
    
    sequence = fields.Integer(string="Sequence")
    move_id = fields.Many2one('account.move', string='Invoice',
                            index=True, required=True, readonly=True, auto_join=True, ondelete="cascade",
                            help="The move of this entry line.")
    product_id = fields.Many2one('product.product',string="Product")
    name = fields.Char(string='Label')
    account_id = fields.Many2one('account.account',string='Account')
    quantity = fields.Float(string='Quantity', default=1.0, digits='Product Unit of Measure',
                            help="The optional quantity expressed by this line, eg: number of product sold. "
                                "The quantity is not a legal requirement but is very useful for some reports.")
    product_uom_id = fields.Many2one('uom.uom', string='UoM', domain="[('category_id', '=', product_uom_category_id)]")
    tax_ids = fields.Many2many(comodel_name='account.tax', string="Taxes", context={'active_test': False},
                            help="Taxes that apply on the base amount")
    price_unit = fields.Float(string='Unit Price', digits='Product Price')
    price_subtotal = fields.Monetary(string='Subtotal', store=True, readonly=False, currency_field='currency_id', help="Tax excl.")
    price_total = fields.Monetary(string='Total', store=True, readonly=False, currency_field='currency_id', help="Tax incl.")
    currency_id = fields.Many2one('res.currency', string='Currency')
    aml_ids = fields.Many2many('account.move.line', string='Move line')