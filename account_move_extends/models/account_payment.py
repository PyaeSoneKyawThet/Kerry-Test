from odoo import api, fields, models, _, Command
from datetime import datetime
from odoo.exceptions import UserError, ValidationError


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    @api.model
    def _read_group_request_status(self, stages, domain, order):
        request_status_list = dict(self._fields['request_status'].selection).keys()
        return request_status_list

    account_payment_type_id = fields.Many2one('account.payment.type',string="Account Payment Type", required=True)
    payment_type_available_journal_ids = fields.Many2many('account.journal',
                                        compute='_compute_payment_type_available_journal_ids')
    cheque_no = fields.Char(string="Cheque No")
    official_receipt_no = fields.Char(string="Official Receipt No", copy=False)
    official_receipt_date = fields.Date(string="Official Receipt Date", compute="_compute_official_receipt_date")

    bank_account_no = fields.Char('Bank Number', related="journal_id.bank_account_no") 
    receipt_voucher_no = fields.Char(string="Receipt Voucher No", copy=False)
    staff_location_id = fields.Many2one('staff.location',string="Doc Location")
    vendor_bill_ids = fields.Many2many('account.move', 'payment_id', 'bill_id' , 'account_payment_vendor_bill_rel' , string="Vendor Bills")
    invoice_ids = fields.Many2many('account.move','account_payment_invoice_rel' , 'payment_id', 'move_id' ,  string="Invoices", tracking=True)

    #----------------------------------------------
    # approver fields for multi approver in payemnt
    #----------------------------------------------
    request_status = fields.Selection([
                                    ('new', 'To Submit'),
                                    ('pending', 'Submitted'), 
                                    ('checked', 'Checking'),
                                    ('approved', 'Approved'),
                                    ('refused', 'Refused'),
                                    ('cancel', 'Cancel'),
                                    ], default="new", compute="_compute_request_status",
                                    store=True, index=True, tracking=True, copy=False, 
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
                                    ], compute="_compute_user_status", copy=False)
    
    submit_user_id = fields.Many2one('res.users',string="Payment Submit User",store=True,copy=False)
    vendor_payment_approver_ids = fields.One2many('vendor.payment.approver.line', 'payment_id', compute="_compute_vendor_payment_approver_ids",store=True, readonly=False)
    minimal_approver =  fields.Integer(string="Minimal Approvers", default=1)
    minimal_checker =  fields.Integer(string="Minimal Checkers", compute="_compute_minimal_checker")
    customer_payment_approver_ids = fields.One2many('customer.payment.approver.line', 'payment_id', compute="_compute_customer_payment_approver_ids",store=True, readonly=False)

    submit_date = fields.Date(string="Payment Submitted Date",help="Submit Date is used in print purpose only.")
    check_date = fields.Date(string="Payment Checked Date",help="Check Date is used in print purpose only.", default=False, copy=False)
    approve_date = fields.Date(string="Payment Approved Date",help="Approve Date is used in print purpose only.", default=False, copy=False)

    config_id = fields.Many2one('payment.approval.config', string="Config", compute="_compute_approval_config")

    @api.depends('amount','currency_id','account_payment_type_id')
    def _compute_approval_config(self):
        for rec in self:  
            domain = [
                        ('from_amount', '<=', rec.amount_total),
                        ('to_amount', '>=', rec.amount_total),
                        ('currency_id', '=', rec.currency_id.id),
                        ('account_payment_type_ids', 'in', rec.account_payment_type_id.id)
                    ]
            if rec.partner_type == 'supplier':
                domain.append(('payment_type', '=', 'supplier_pay'))
            else:
                domain.append(('payment_type', '=', 'customer_pay'))
            config = self.env['payment.approval.config'].search(domain, limit=1) 
            if config:       
                rec.config_id = config.id
            else:
                rec.config_id = False

    @api.depends('vendor_payment_approver_ids')
    def _compute_minimal_checker(self):
        for rec in self:  
            if rec.partner_type == 'supplier':
                rec.minimal_checker = len(rec.vendor_payment_approver_ids[:-1]) if rec.vendor_payment_approver_ids else 0 
            if rec.partner_type == 'customer':
                rec.minimal_checker = len(rec.customer_payment_approver_ids[:-1]) if rec.customer_payment_approver_ids else 0 

    @api.depends_context('uid')
    @api.depends('vendor_payment_approver_ids.status','customer_payment_approver_ids.status')
    def _compute_user_status(self):
        for rec in self:
            if rec.partner_type == 'supplier':
                approvers = rec.vendor_payment_approver_ids.filtered(
                    lambda approver: self.env.user in approver.approval_user_ids
                )
                rec.user_status = approvers[:1].status if approvers else False
            if rec.partner_type == 'customer':
                approvers = rec.customer_payment_approver_ids.filtered(
                    lambda approver: self.env.user in approver.approval_user_ids
                )
                rec.user_status = approvers[:1].status if approvers else False

    @api.depends('submit_user_id')
    def _compute_vendor_payment_approver_ids(self):
        for rec in self:
            if not rec.vendor_payment_approver_ids and rec.partner_type == 'supplier' and rec.submit_user_id:
                if not rec.config_id:
                    raise ValidationError(_('No Approver for current amount!'))
                
                approver_id_vals = [Command.clear()]
                if rec.config_id.need_approval:
                    approver_approvers = rec.submit_user_id.employee_id.vendor_payment_approver_ids.filtered(lambda a: a.sequence >= rec.config_id.from_level and a.sequence <= rec.config_id.to_level).sorted(key=lambda a: a.sequence)
                    for approver in approver_approvers:    
                        if approver.approval_user_ids.ids:                
                            approver_id_vals.append(Command.create({
                                'approval_user_ids': [(6, 0, approver.approval_user_ids.ids)],
                                'approval_employee_id': approver.approval_user_ids[:1].id if approver.approval_user_ids else False,
                                'status': 'new',
                                'sequence': approver.sequence,
                                'payment_id': rec.id,
                            }))
                rec.vendor_payment_approver_ids = approver_id_vals
            else:
                rec.vendor_payment_approver_ids = rec.vendor_payment_approver_ids
    
    @api.depends('submit_user_id')
    def _compute_customer_payment_approver_ids(self):
        for rec in self:
            if not rec.customer_payment_approver_ids and rec.partner_type == 'customer' and rec.submit_user_id:
                if not rec.config_id:
                    raise ValidationError(_('No Approver for current amount!'))
                
                approver_id_vals = [Command.clear()]
                if rec.config_id.need_approval:
                    approver_approvers = rec.submit_user_id.employee_id.customer_payment_approver_ids.filtered(lambda a: a.sequence >= rec.config_id.from_level and a.sequence <= rec.config_id.to_level).sorted(key=lambda a: a.sequence)
                    for approver in approver_approvers:   
                        if approver.approval_user_ids.ids:                 
                            approver_id_vals.append(Command.create({
                                'approval_user_ids': [(6, 0, approver.approval_user_ids.ids)],
                                'approval_employee_id': approver.approval_user_ids[:1].id if approver.approval_user_ids else False,
                                'status': 'new',
                                'sequence': approver.sequence,
                                'payment_id': rec.id,
                            }))
                rec.customer_payment_approver_ids = approver_id_vals
            else:
                rec.customer_payment_approver_ids = rec.customer_payment_approver_ids

    @api.depends('vendor_payment_approver_ids.status','customer_payment_approver_ids.status','state')
    def _compute_request_status(self):
        for request in self:
            if request.partner_type == 'supplier':
                status_lst = request.mapped('vendor_payment_approver_ids.status')
            if request.partner_type == 'customer':
                status_lst = request.mapped('customer_payment_approver_ids.status')
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

    def action_draft(self):
        """ set the submit_user_id to recompute vendor_payment_approver_ids 
            set the submit_user_id to recompute customer_payment_approver_ids 
        """
        self.sudo()._get_user_approval_activities(user=self.env.user).unlink()
        if self.partner_type == 'supplier':
            self.mapped('vendor_payment_approver_ids').write({'status': 'new'})
        if self.partner_type == 'customer':
            self.mapped('customer_payment_approver_ids').write({'status': 'new'})
        self.request_status = 'new'
        res = super().action_draft()
        self.submit_user_id = None
        return res
    
    #-------------------------------------------
    # helper method for payment approval feature
    #-------------------------------------------
    def _cancel_activities(self):
        approval_activity = self.env.ref('approvals.mail_activity_data_approval')
        activities = self.activity_ids.filtered(lambda a: a.activity_type_id == approval_activity)
        activities.unlink()
    
    def _get_user_approval_activities(self, user):
        domain = [
            ('res_model', '=', 'account.payment'),
            ('res_id', 'in', self.ids),
            ('activity_type_id', '=', self.env.ref('account_move_extends.mail_activity_data_account_payment_kmtl').id),
            ('user_id', '=', user.id)
        ]
        activities = self.env['mail.activity'].search(domain)
        return activities 
    
    def _ensure_can_check(self):
        if any(approval.user_status == 'waiting' for approval in self):
            raise ValidationError(_('You cannot check before the previous checker.'))

    def _update_next_checkers(self, new_status, checker, only_next_checker, cancel_activities=False):
        if self.partner_type == 'supplier':
            checkers_updated = self.env['vendor.payment.approver.line']
            for move in self:
                current_checker = move.vendor_payment_approver_ids & checker
                checkers_to_update = move.vendor_payment_approver_ids.filtered(lambda a: a.status not in ['approved', 'refused'] \
                                    and (a.sequence > current_checker.sequence \
                                    or (a.sequence == current_checker.sequence and a.id > current_checker.id)))
                
                if only_next_checker and checkers_to_update:
                    checkers_to_update = checkers_to_update[0]
                    checkers_updated |= checkers_to_update
        if self.partner_type == 'customer':
            checkers_updated = self.env['customer.payment.approver.line']
            for move in self:
                current_checker = move.customer_payment_approver_ids & checker
                checkers_to_update = move.customer_payment_approver_ids.filtered(lambda a: a.status not in ['approved', 'refused'] \
                                    and (a.sequence > current_checker.sequence \
                                    or (a.sequence == current_checker.sequence and a.id > current_checker.id)))
                if only_next_checker and checkers_to_update:
                    checkers_to_update = checkers_to_update[0]
                    checkers_updated |= checkers_to_update
        checkers_updated.sudo().status = new_status
        checkers_updated.sudo()._create_activity()
        if cancel_activities:
            checkers_updated.payment_id._cancel_activities()

    def _ensure_can_approve(self):
        if any(approval.user_status == 'waiting' for approval in self):
            raise ValidationError(_('You cannot approve before the previous approver.'))
        
    def _update_next_approvers(self, new_status, approver, only_next_approver, cancel_activities=False):
        if self.partner_type == 'supplier':
            approvers_updated = self.env['vendor.payment.approver.line'] 
        if self.partner_type == 'customer':
            approvers_updated = self.env['customer.payment.approver.line'] 

        for approval in self:
            if approval.partner_type == 'supplier':
                current_approver = approval.vendor_payment_approver_ids & approver
                approvers_to_update = approval.vendor_payment_approver_ids.filtered(lambda a: a.status not in ['approved', 'refused'] and (a.sequence > current_approver.sequence or (a.sequence == current_approver.sequence and a.id > current_approver.id)))

            if approval.partner_type == 'customer':
                current_approver = approval.customer_payment_approver_ids & approver
                approvers_to_update = approval.customer_payment_approver_ids.filtered(lambda a: a.status not in ['approved', 'refused'] and (a.sequence > current_approver.sequence or (a.sequence == current_approver.sequence and a.id > current_approver.id)))

            if only_next_approver and approvers_to_update:
                approvers_to_update = approvers_to_update[0]
            approvers_updated |= approvers_to_update

        approvers_updated.sudo().status = new_status
        if new_status == 'pending':
            approvers_updated._create_activity()
        if cancel_activities:
            approvers_updated.payment_id._cancel_activities()

    #------------------------------------------
    # main method for payment approval feature
    #------------------------------------------
    def action_submit_payment(self):
        if self.amount == 0:
            raise UserError(_("Payment Amount should be greater than zero!"))
        self.submit_user_id = self.env.user

        if self.report_amount != abs(self.move_id.amount_total_signed) and self.report_currency_id == self.company_currency_id:
            raise UserError(_("Pay Amount is not matching with Journal Entry!"))

        if self.partner_type == 'supplier':
            # if config doesn't need approver, just post the payment
            if not self.vendor_payment_approver_ids and self.config_id and not self.config_id.need_approval:
                self.action_approve_payment()
                return True

            approvers = self.vendor_payment_approver_ids
            approvers = approvers.filtered(lambda a: a.status in ['new', 'to_check', 'pending', 'waiting'])
            if not approvers:
                raise ValidationError(_("Can't submit without approver!"))
            status  = 'pending' if len(approvers) == 1 else 'to_check' 
            approvers[1:].sudo().write({'status': 'waiting'})
            approvers = approvers[0] if approvers and approvers[0].status != 'to_check' else self.env['vendor.payment.approver.line']

        if self.partner_type == 'customer':
            # if config doesn't need approver, just post the payment
            if not self.customer_payment_approver_ids and self.config_id and not self.config_id.need_approval:
                self.action_approve_payment()
                return True
            
            approvers = self.customer_payment_approver_ids
            approvers = approvers.filtered(lambda a: a.status in ['new', 'to_check', 'pending', 'waiting'])
            if not approvers:
                raise ValidationError(_("Can't submit without approver!"))
            status  = 'pending' if len(approvers) == 1 else 'to_check'
            approvers[1:].sudo().write({'status': 'waiting'})
            approvers = approvers[0] if approvers and approvers[0].status != 'to_check' else self.env['customer.payment.approver.line']

        approvers._create_activity()
        approvers.sudo().write({'status': status})
        self.sudo().submit_date = fields.Date.today()
        # self.sudo()._get_user_approval_activities(user=self.env.user).action_feedback()
        return True
    
    def action_check_payment(self, checker=None):
        self._ensure_can_check()    
        if self.partner_type == 'supplier': 
            if not isinstance(checker, models.BaseModel):
                checker = self.mapped('vendor_payment_approver_ids').filtered(
                    lambda checker: self.env.user in checker.approval_user_ids)
            checker.status = 'checked'
            status_lst = self.mapped('vendor_payment_approver_ids.status') 
            for user in checker.approval_user_ids:
                self.sudo()._get_user_approval_activities(user=user).action_feedback()

        if self.partner_type == 'customer': 
            if not isinstance(checker, models.BaseModel):
                checker = self.mapped('customer_payment_approver_ids').filtered(
                    lambda checker: self.env.user in checker.approval_user_ids)
            checker.status = 'checked'
            status_lst = self.mapped('customer_payment_approver_ids.status') 
            for user in checker.approval_user_ids:
                self.sudo()._get_user_approval_activities(user=user).action_feedback()

        if status_lst.count('checked') >= (self.minimal_checker):
            self.sudo()._update_next_checkers('pending', checker , only_next_checker=True)
        else:
            self.sudo()._update_next_checkers('to_check', checker, only_next_checker=True)
        self.sudo().check_date = fields.Date.today()

    def action_approve_payment(self, approver=None):
        self._ensure_can_approve()
        if self.report_amount != abs(self.move_id.amount_total_signed) and self.report_currency_id == self.company_currency_id:
            raise UserError(_("Pay Amount is not matching with Journal Entry!"))
        
        if not isinstance(approver, models.BaseModel):
            if self.partner_type == 'supplier':
                approver = self.mapped('vendor_payment_approver_ids').filtered(
                    lambda approver: self.env.user in approver.approval_user_ids
                )  
            if self.partner_type == 'customer':
                approver = self.mapped('customer_payment_approver_ids').filtered(
                    lambda approver: self.env.user in approver.approval_user_ids
                )       
        self.request_status = 'approved'  
        approver.write({'status': 'approved'})
        self.sudo().approve_date = fields.Date.today()
        self.sudo()._update_next_approvers('pending', approver, only_next_approver=True)
        self.sudo()._get_user_approval_activities(user=self.env.user).action_feedback()
        self.sudo().action_post()
    
    def action_refuse_payment(self, approver=None):
        if not isinstance(approver, models.BaseModel):
            if self.partner_type == 'supplier':
                approver = self.mapped('vendor_payment_approver_ids').filtered(
                    lambda approver: self.env.user in approver.approval_user_ids
                ) 
            if self.partner_type == 'customer':
                approver = self.mapped('customer_payment_approver_ids').filtered(
                    lambda approver: self.env.user in approver.approval_user_ids
                ) 
        approver.write({'status': 'refused'})
        self.sudo()._update_next_approvers('refused', approver, only_next_approver=False, cancel_activities=True)
        self.sudo()._get_user_approval_activities(user=self.env.user).action_feedback()
        self.request_status = 'refused'

    def action_cancel_payment(self):
        self.sudo()._get_user_approval_activities(user=self.env.user).unlink()
        if self.partner_type == 'supplier':
            self.mapped('vendor_payment_approver_ids').write({'status': 'cancel'})
        if self.partner_type == 'customer':
            self.mapped('customer_payment_approver_ids').write({'status': 'cancel'})
        self.request_status = 'cancel'
        return self.sudo().action_cancel()

    @api.depends('date')
    def _compute_official_receipt_date(self):
        for rec in self:
            rec.official_receipt_date = rec.date

    @api.onchange('account_payment_type_id')
    def onchange_account_payment_type(self):
        if self.account_payment_type_id.journal_ids:
            self.journal_id = self.account_payment_type_id.journal_ids.ids[0]
        elif self.available_journal_ids:
            self.journal_id = self.available_journal_ids.ids[0]
        else:
            self.journal_id = False
            
    @api.depends('account_payment_type_id')
    def _compute_payment_type_available_journal_ids(self):
        for rec in self:
            rec.payment_type_available_journal_ids = rec.account_payment_type_id.journal_ids.ids or rec.available_journal_ids.ids

    def _get_report_filename_receipt_voucher(self):
        self.ensure_one()
        return 'Receipt Voucher-%s' % (self.name)

    def _get_report_filename_official_receipt(self):
        self.ensure_one()
        return 'Official Receipt-%s' % (self.official_receipt_no)
    
    def _get_report_filename_payment_voucher(self):
        self.ensure_one()
        return 'Payment Voucher-%s' % (self.name)

    def action_print_official_receipt(self):
        for rec in self:
            if not rec.official_receipt_no:
                if rec.staff_location_id:
                    seq_number = self.env['staff.location'].search([('id', '=', self.staff_location_id.id)]).get_seq_number('official_receipt')
                    rec.official_receipt_no = seq_number
            else:
                rec.official_receipt_no = rec.official_receipt_no

        return self.env.ref('account_payment_report.account_payment_report').report_action(self)
    
    def action_print_receipt_voucher(self):
        return self.env.ref('account_payment_report.account_receipt_voucher_report').report_action(self)

    def action_print_payment_voucher(self):
        return self.env.ref('account_payment_report.account_payment_voucher_report').report_action(self)
    
    def _generate_payment_sequence(self):
        if self.paired_internal_transfer_payment_id:
            self = self.paired_internal_transfer_payment_id
        
        if self.payment_id.partner_type == 'customer':
            seq_number = self.env['ir.sequence'].next_by_code('customer.payment.with.journal')
            code = self.journal_id.code
        else:
            seq_number = self.env['ir.sequence'].next_by_code('vendor.payment.with.journal')
            code = self.journal_id.payment_short_code

        name = f"{code}{seq_number}"
        self.name = name
        self.receipt_voucher_no = name
    
    def action_post(self):
        if self.name in ('draft', '/'):
            self._generate_payment_sequence()
        res = super().action_post()
        if self.paired_internal_transfer_payment_id and self.paired_internal_transfer_payment_id.state == 'posted' and self.paired_internal_transfer_payment_id.name in ('draft', '/'):
            self._generate_payment_sequence()
        return res

    def button_open_vendor_bills(self):
        self.ensure_one()

        action = {
            'name': _("Bills"),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'context': {'create': False},
        }
        if len(self.vendor_bill_ids) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': self.vendor_bill_ids.id,
            })
        else:
            action.update({
                'view_mode': 'list,form',
                'domain': [('id', 'in', self.vendor_bill_ids.ids)],
            })
        return action
    
    def button_open_customer_invoices(self):
        self.ensure_one()

        action = {
            'name': _("Invoices"),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'context': {'create': False},
        }
        if len(self.invoice_ids) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': self.invoice_ids.id,
            })
        else:
            action.update({
                'view_mode': 'list,form',
                'domain': [('id', 'in', self.invoice_ids.ids)],
            })
        return action

            
        