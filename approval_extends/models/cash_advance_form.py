from odoo import fields,Command, models, api, _
from odoo.exceptions import UserError,ValidationError
from datetime import date
from collections import defaultdict
from bs4 import BeautifulSoup

class CashAdvanceForm(models.Model):
    _name = 'cash.advance.form'
    _description = 'Cash Advance Form'
    _inherit = ['mail.thread', 'mail.activity.mixin','analytic.mixin'] 
    _order = 'name'
    _mail_post_access = 'read' 
     
    @api.model
    def _read_group_request_status(self, stages, domain, order):
        request_status_list = dict(self._fields['request_status'].selection).keys()
        return request_status_list

    name = fields.Char(string='Name')
    date = fields.Date(string='Date', default=date.today(), tracking=True)
    request_status = fields.Selection([
                                    ('new', 'To Submit'),
                                    ('pending', 'Submitted'),
                                    ('checked', 'Checking'),
                                    ('approved', 'Approved'),
                                    ('refused', 'Refused'),
                                    ('cancel', 'Cancel'),
                                    ], default="new", compute="_compute_request_status", 
                                    store=True, index=True, tracking=True,
                                    group_expand='_read_group_request_status')
    request_owner_id = fields.Many2one('res.users',string="Request Owner", tracking=True) 
    employee_id = fields.Many2one('hr.employee', string="Employee", related="request_owner_id.employee_id")
    department_id = fields.Many2one('hr.department',related="employee_id.department_id", string="Department", store=True)  
    category_id = fields.Many2one('approval.category', string="Category", required=True)
    cash_advance_no = fields.Char(string="Cash Advance No")
    request_id = fields.Many2one('approval.request', string="Purchase Request Ref", tracking=True)
    purchase_order_id = fields.Many2one('purchase.order', string="Purchase Order Ref", copy=False)
    currency_id = fields.Many2one('res.currency', string="Currency", tracking=True)
    partner_id = fields.Many2one('res.partner', string="Vendor")
    payment_type_id = fields.Many2one('account.payment.type', string="Type") 
    vehicle_no = fields.Char(string="Vehicle No")
    amount = fields.Float(string="Amount") 
    tax_ids = fields.Many2many('account.tax',string="Taxs")
    tax_amount = fields.Float(string="Tax amount", compute="_compute_tax_amount")
    total_amount = fields.Float(string="Total amount", compute="_compute_total_amount")
    reason = fields.Html(string="Account Description")
    company_id = fields.Many2one(string='Company', related='category_id.company_id',
                                store=True, readonly=True, index=True)
    approval_type = fields.Selection(related="category_id.approval_type")
    
    approver_ids = fields.One2many('cash.advance.approver', 'cash_advance_id', string="Approvers", 
                   compute='_compute_approver_ids', store=True, readonly=False)
    
    fmis_job_no = fields.Char(string="FMIS Job Number")
    job_date = fields.Date(string="Job Date")
    staff_location_id = fields.Many2one('staff.location',string="Doc Location")
    minimal_approver =  fields.Integer(string="Minimal Approvers", default=1)
    minimal_checker =  fields.Integer(string="Minimal Checkers", compute="_compute_minimal_checker")
    user_status = fields.Selection([
        ('new', 'New'),
        ('to_check', 'To Checked'), 
        ('checked', 'Checked'),
        ('pending', 'To Approve'),
        ('waiting', 'Waiting'),
        ('approved', 'Approved'),
        ('refused', 'Refused'),
        ('cancel', 'Cancel')], compute="_compute_user_status")
    has_access_to_request = fields.Boolean(string="Has Access To Request", compute="_compute_has_access_to_request")
    change_request_owner = fields.Boolean(string='Can Change Request Owner', compute='_compute_has_access_to_request')
    date_confirmed = fields.Datetime(string="Date Confirmed")
    payment_id = fields.Many2one('account.payment', string="Current Payment")
    payment_ids = fields.One2many('account.payment', 'cash_advance_id', string="Payments")
    payment_state = fields.Selection(
        selection=lambda self: self.env["account.payment"]._fields["state"]._description_selection(self.env),
        string="Current Payment Status",
        compute='_compute_from_account_payment', store=True, readonly=True,
        copy=False,
        tracking=True,
    )
    # journal_id = fields.Many2one('account.journal', string="Journal") 
    available_journal_ids = fields.Many2many( comodel_name='account.journal',
                                        compute='_compute_available_journal_ids')
    
    pay_to_id = fields.Many2one('hr.employee',string="Pay To Employee",tracking=True)
    pay_to_external = fields.Char(string="Pay To External", tracking=True)
    product_id = fields.Many2one('product.product',string="Product")
    description = fields.Char(string="Description")
    vendor_quotation_no = fields.Char(string="Vendor Quotation No", help="Approval Request's reference")
    vendor_invoice_no = fields.Char(string="Vendor Invoice No")
    config_id = fields.Many2one('approval.process.config', string="Config", compute="_compute_approval_config")
    bl_no = fields.Char(string="BL No")
    brand_id = fields.Many2one('purchase.brand', string="Brand")
    reference_key = fields.Char(string="Reference Key")
    location = fields.Char(string="Delivery Location")
    est_delivery_date = fields.Date(string="Est. Delivery Date")
    is_clear = fields.Boolean(string="Is Clear")
    is_locked = fields.Boolean(string="Is Locked", default=False)
    able_to_reimburse = fields.Boolean(string="Able to reimburse", help="Define we can click reimburse or not.", default=True, compute="_compute_able_to_reimburse")
    is_reimburse = fields.Boolean(string="Reimburse", help="If cash advance is not used in expense or payment, we can reimburse cash advance.")
    is_cash_advance_cancel = fields.Boolean(string="Cash Advance Cancel", tracking=True , copy=False)
    is_request_cancel = fields.Boolean(string="Purchase Request Cancel", tracking=True , copy=False) 
    #To show priority in list view purpose only
    #This part is for Payment priority
    payment_approved_ids = fields.Many2many('account.payment', string="Payment No", compute="_compute_payment_priority", store=True, copy=False)
    account_payment_state = fields.Selection([('draft', 'Draft'),  
                                            ('posted', 'Posted'),
                                            ('cancel', 'Cancel')],
                                        default=None, compute="_compute_payment_priority", string="Payment State", store=True, copy=False)
    
    purchase_request_status = fields.Selection(string="Purchase Request Status", related="request_id.request_status", copy=False, store=True)

    #search parent department
    parent_department_id = fields.Many2one('hr.department', string="Parent Department", related="department_id.parent_id", store=True)

    @api.depends('payment_ids', 'payment_ids.state')
    def _compute_payment_priority(self):
        for ca in self:
            payment_map = defaultdict(list)
            payments = ca.payment_ids.filtered(lambda x: x.is_cash_advance)
            for payment in payments:
                payment_map[payment.state].append(payment)
            # Prioritize posted > draft > cancel
            if payment_map.get('posted'):
                ca.account_payment_state = 'posted'
                ca.payment_approved_ids = [(6, 0, [p.id for p in payment_map['posted']])]
            elif payment_map.get('draft'):
                ca.account_payment_state = 'draft'
                ca.payment_approved_ids = [(6, 0, [p.id for p in payment_map['draft']])]
            elif payment_map.get('cancel'):
                ca.account_payment_state = 'cancel'
                ca.payment_approved_ids = [(6, 0, [p.id for p in payment_map['cancel']])]
            else:
                ca.account_payment_state = None
                ca.payment_approved_ids = [(6, 0, [])]
    
    def action_lock(self):
        self.ensure_one()
        self.is_locked = True

    def action_unlock(self):
        self.ensure_one()
        self.is_locked = False

    def _compute_able_to_reimburse(self):
        for rec in self:
            used_in_expense = self.env['approval.expense'].search([('cash_advance_ids','in', rec.id),('request_status','!=', 'cancel')])
            used_in_payment_request = self.env['approval.payment.request'].search([('cash_advance_ids','in', rec.id),('request_status','!=', 'cancel')])

            payment_approved = self.env['account.payment'].search([
                                    ('cash_advance_id','=', rec.id),
                                    ('is_cash_advance','=', True),
                                    ('state','=', 'posted'),
                                    ('is_reconciled', '!=', True)
                                ])
            
            reimburse_payment = self.env['account.payment'].search([
                                    ('cash_advance_id','=', rec.id),
                                    ('is_cash_advance','=', True),
                                    ('is_reimburse_payment','=',True),
                                    ('state','!=', 'cancel'),
                                ])

            if used_in_expense or used_in_payment_request or rec.request_status != 'approved' or reimburse_payment or not payment_approved:
                rec.able_to_reimburse = False
            else:
                rec.able_to_reimburse = True
                rec.is_clear = False

    @api.depends('request_status', 'payment_id.state')
    def _compute_from_account_payment(self):
        for rec in self:
            # Only one move is created when the expenses are paid by the employee
            if rec.payment_id:
                rec.payment_state = rec.payment_id[:1].state
            else:
                rec.payment_state = ''
    
    @api.depends('payment_type_id')
    def _compute_available_journal_ids(self):
        for rec in self:
            if rec.payment_type_id:
                rec.available_journal_ids = rec.payment_type_id.journal_ids.ids
            else:
                rec.available_journal_ids = self.env['account.journal'].search([('type', 'in', ['cash', 'bank'])])
    
    @api.depends('request_owner_id')
    @api.depends_context('uid')
    def _compute_has_access_to_request(self):
        is_approval_user = self.env.user.has_group('approvals.group_approval_user')
        self.change_request_owner = is_approval_user
        for request in self:
            request.has_access_to_request = request.request_owner_id == self.env.user and is_approval_user    
    
    @api.depends_context('uid')
    @api.depends('approver_ids.status')
    def _compute_user_status(self):
        for approval in self:
            approvers = approval.approver_ids.filtered(
                lambda approver: self.env.user in approver.user_ids
            )
            approval.user_status = approvers[:1].status if approvers else False
    
    @api.depends('approver_ids')
    def _compute_minimal_checker(self):
        for rec in self: 
            rec.minimal_checker = 0
            if rec.category_id.approval_type == 'cash_advance':   
                rec.minimal_checker = len(rec.approver_ids[:-1]) if rec.approver_ids else 0  
                
    @api.depends('category_id', 'amount', 'currency_id')
    def _compute_approval_config(self):
        for approval in self:  
            config_ids = approval.category_id.approval_process_config_ids.filtered(lambda x: x.from_amount <= approval.amount \
                    and x.to_amount >= approval.amount and x.currency_id.id == approval.currency_id.id)  
            dept_config = config_ids.filtered(lambda x: x.department_ids and approval.department_id.id in x.department_ids.ids)
            not_dept_config = config_ids.filtered(lambda x: not x.department_ids)               
            config = dept_config if dept_config else not_dept_config 
            if config:       
                approval.config_id = config[0].id
            else:
                approval.config_id = False

    #generate sequence code
    @api.model_create_multi
    def create(self, vals):              
        for val in vals:
            sequence = self.env['ir.sequence'].next_by_code('cash.advance.sequence')
            val['name'] = "{}".format(str(sequence))
        return super(CashAdvanceForm, self).create(vals)
    
    def unlink(self):
        if self.filtered(lambda a: a.request_status == 'approved'): 
            raise UserError(_("You can't delete in Approved State!"))
        return super().unlink()
    
    @api.depends('amount','tax_ids')
    def _compute_tax_amount(self):
        for record in self:
            tax_amount = 0.0
            if record.tax_ids:
                taxes = record.tax_ids.compute_all(record.amount, currency= record.currency_id, quantity=1.0)['taxes']
                tax_amount = sum(tax['amount'] for tax in taxes)
            record.tax_amount = tax_amount
            
    @api.depends('amount','tax_amount')
    def _compute_total_amount(self):
        for record in self:
            record.total_amount = record.amount + record.tax_amount
            
    def _cancel_activities(self):
        approval_activity = self.env.ref('approval_extends.mail_activity_data_cash_advance_kmtl')
        activities = self.activity_ids.filtered(lambda a: a.activity_type_id == approval_activity)
        activities.unlink()
    
    def action_confirm(self):
        self.ensure_one()
        status = None
        if self.category_id.approval_type == 'cash_advance':
            if self.config_id.need_approval:
                if len(self.approver_ids) < self.minimal_approver:
                    raise UserError(_("You have to add at least %s approvers to confirm your request.", self.minimal_approver))
                approvers = self.approver_ids
                approvers = approvers.filtered(lambda a: a.status in ['new', 'to_check', 'pending', 'waiting'])
                if approvers:
                    status  = 'pending' if len(approvers) == 1 else 'to_check'
                approvers[1:].sudo().write({'status': 'waiting'})
                approvers = approvers[0] if approvers and approvers[0].status != 'to_check' else self.env['cash.advance.approver']

                approvers._create_activity()
                approvers.sudo().write({'status': status})
                self.sudo()._get_user_approval_activities(user=self.env.user).action_feedback()
            else:
                self.action_approve()
            self.sudo().write({'date_confirmed': fields.Datetime.now()}) 
            
    def _update_next_checkers(self, new_status, checker, only_next_checker, cancel_activities=False):
        checkers_updated = self.env['cash.advance.approver']
        for approval in self:
            current_checker = approval.approver_ids & checker
            checkers_to_update = approval.approver_ids.filtered(lambda a: a.status not in ['approved', 'refused'] \
                                and (a.level > current_checker.level \
                                or (a.level == current_checker.level and a.id > current_checker.id)))

            if only_next_checker and checkers_to_update:
                checkers_to_update = checkers_to_update[0]
            checkers_updated |= checkers_to_update

        checkers_updated.sudo().status = new_status
        checkers_updated.sudo()._create_activity()
        if cancel_activities:
            checkers_updated.request_id._cancel_activities()
            
    def _ensure_can_check(self):
        if any(approval.user_status == 'waiting' for approval in self):
            raise ValidationError(_('You cannot check before the previous checker.'))

    def action_check(self, checker=None):
        self._ensure_can_check()        
        if not isinstance(checker, models.BaseModel):
            checker = self.mapped('approver_ids').filtered(
                lambda checker: self.env.user in checker.user_ids)
        checker.status = 'checked'
        status_lst = self.mapped('approver_ids.status')        
        if status_lst.count('checked') >= (self.minimal_checker):
            self.sudo()._update_next_checkers('pending', checker, only_next_checker=True)
        else:
            self.sudo()._update_next_checkers('to_check', checker, only_next_checker=True)
        for user in checker.user_ids:
            self.sudo()._get_user_approval_activities(user=user).action_feedback()
            
    def _ensure_can_approve(self):
        if any(approval.user_status == 'waiting' for approval in self):
            raise ValidationError(_('You cannot approve before the previous approver.'))
        
    def _update_next_approvers(self, new_status, approver, only_next_approver, cancel_activities=False):
        approvers_updated = self.env['cash.advance.approver']
        for approval in self:
            current_approver = approval.approver_ids & approver
            approvers_to_update = approval.approver_ids.filtered(lambda a: a.status not in ['approved', 'refused'] and (a.sequence > current_approver.sequence or (a.sequence == current_approver.sequence and a.id > current_approver.id)))

            if only_next_approver and approvers_to_update:
                approvers_to_update = approvers_to_update[0]
            approvers_updated |= approvers_to_update

        approvers_updated.sudo().status = new_status
        if new_status == 'pending':
            approvers_updated._create_activity()
        if cancel_activities:
            approvers_updated.request_id._cancel_activities()
            
    def _prepare_account_payment_vals(self):
        # payment_method = self.env['account.payment.method'].search([('payment_type', '=', 'outbound')])
        # payment_method_line = self.env['account.payment.method.line'].search([('journal_id', '=', self.journal_id.id), ('payment_method_id', '=', payment_method.id)])
        payment_type = 'outbound'
        partner_type = 'supplier'
        journal_id = False
        if self.payment_type_id.journal_ids:
            journal_id = self.payment_type_id.journal_ids.ids[0]      
        vals = {'partner_id': self.partner_id.id or self.request_owner_id.partner_id.id, 
                'date': self.date,
                'amount': self.amount,
                'payment_type': payment_type,
                'partner_type': partner_type,
                'journal_id': journal_id,
                'company_id': self.company_id.id,
                'ref': self.description,
                'cash_advance_id': self.id,
                'state': 'draft',
                'request_id': self.request_id.id, 
                'purchase_order_no': self.purchase_order_id.name,
                'fmis_job_no': self.fmis_job_no, 
                'job_date': self.job_date, 
                'pay_to_id': self.pay_to_id.id, 
                'pay_to_external': self.pay_to_external, 
                'vendor_quotation_no': self.vendor_quotation_no,  
                'vendor_invoice_no': self.vendor_invoice_no,  
                'vendor_invoice_date': self.date,  
                'product_id': self.product_id.id,
                'staff_location_id': self.staff_location_id.id, 
                'account_payment_type_id': self.payment_type_id.id,
                'currency_id': self.currency_id.id,
                'vehicle_no': self.vehicle_no,
                'bl_no': self.bl_no,
                'reference_key': self.reference_key,
                # 'analytic_distribution': self.analytic_distribution,
                'reason': self.reason,
                'destination_account_id': self.product_id.property_account_expense_id.id,
                'brand_name': self.brand_id.name,
                'location': self.location,
                'delivery_date': self.est_delivery_date,
                'is_cash_advance': True,
                } 
        return vals

    def action_approve(self, approver=None):
        self._ensure_can_approve()

        if not isinstance(approver, models.BaseModel):
            approver = self.mapped('approver_ids').filtered(
                    lambda approver: self.env.user in approver.user_ids
                )
        if not self.product_id.property_account_expense_id:
            raise UserError(_("You have to add Advance COA on product!"))
        payment_vals = self._prepare_account_payment_vals()
        payment = self.env['account.payment'].sudo().create(payment_vals)
        self.payment_id = payment.id
        approver.write({'status': 'approved'})
        self.sudo()._update_next_approvers('pending', approver, only_next_approver=True)
        self.sudo()._get_user_approval_activities(user=self.env.user).action_feedback()
        self.write({'request_status': 'approved'})
    
    def action_draft(self):
        if self.request_id and self.request_id.request_status == 'cancel':
            raise ValidationError(_("You can't set to draft in Purchase Request Cancel state!"))
        self.mapped('approver_ids').write({'status': 'new'})
        self.mapped('payment_ids').write({'is_cash_advance_cancel': False})
        self.write({'request_status': 'new', 'is_cash_advance_cancel': False})
    
    def _action_cancel(self):
        self.sudo()._get_user_approval_activities(user=self.env.user).unlink()
        self.mapped('approver_ids').write({'status': 'cancel'})
        self.write({'request_status': 'cancel','is_clear': False, 'is_reimburse': False})
        for payment in self.mapped('payment_ids').filtered(lambda p: p.is_cash_advance and p.state == 'draft'):
            if payment.move_id:
                payment.move_id.button_cancel()

    def action_cancel(self):
        if any(rec.request_status == 'approved' and any(payment.is_cash_advance and payment.state == 'posted' for payment in rec.payment_ids) for rec in self):
            raise ValidationError(_('You cannot cancel in payment posted state!'))
        
        # check if purchase_request have cash_advance or expense or payment_request
        request_ids = self.mapped('request_id').filtered(
                        lambda r: not r.expense_ids and not r.payment_request_ids )

        # check if purchase_request is used in RFQ
        used_line_ids = self.env['approval.product.line'].search([
            ('purchase_request_line_id', 'in', request_ids.mapped('product_line_ids').ids)
        ]).mapped('purchase_request_line_id')
        # remove request that is uesed in RFQ
        unused_request_ids = request_ids.filtered(
            lambda r: not any(line.id in used_line_ids.ids for line in r.product_line_ids)
        )

        if unused_request_ids:
            return {
                'name': "Cancel Purchase Request",
                'type': 'ir.actions.act_window',
                'view_mode': 'form',            
                'res_model': 'purchase.request.cancel.wizard',  
                'views': [(False, 'form')],
                'view_id' : 'purchase_request_cancel_wizard',       
                'target': 'new',           
                'context': {'default_cash_advance_ids': self.ids, 'default_request_ids': unused_request_ids.ids}            
            }
        else:
            self._action_cancel()

        
        
    def action_refuse(self, approver=None):
        if not isinstance(approver, models.BaseModel):
            approver = self.mapped('approver_ids').filtered(
                lambda approver: self.env.user in approver.user_ids)
        approver.write({'status': 'refused'})
        self.sudo()._update_next_approvers('refused', approver, only_next_approver=False, cancel_activities=True)
        self.sudo()._get_user_approval_activities(user=self.env.user).action_feedback()
        
    def _get_user_approval_activities(self, user):
        domain = [
            ('res_model', '=', 'cash.advance.form'),
            ('res_id', 'in', self.ids),
            ('activity_type_id', '=', self.env.ref('approval_extends.mail_activity_data_cash_advance_kmtl').id),
            ('user_id', '=', user.id)
        ]
        activities = self.env['mail.activity'].search(domain)
        return activities
            
    @api.depends('approver_ids.status', 'approver_ids.required')
    def _compute_request_status(self):
        for request in self:
            if request.approver_ids:
                status_lst = request.mapped('approver_ids.status')
                required_approved = all(a.status == 'approved' for a in request.approver_ids.filtered('required'))
                minimal_approver = request.minimal_approver if len(status_lst) >= request.minimal_approver else len(status_lst)
                minimal_checker = request.minimal_checker if len(status_lst) >= request.minimal_checker else len(status_lst)
                if status_lst:
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
                else:
                    status = 'new'
            else:
                status = request.request_status
            request.request_status = status

        self.filtered_domain([('request_status', 'in', ['approved', 'refused', 'cancel'])])._cancel_activities()
    
    #compute approver list based on approval type
    @api.depends('category_id', 'request_owner_id', 'amount', 'currency_id')
    def _compute_approver_ids(self):
        for rec in self:
            approver_id_vals = [Command.clear()]               
            config_ids = rec.category_id.approval_process_config_ids.filtered(lambda x: x.from_amount <= rec.amount \
                        and x.to_amount >= rec.amount and x.currency_id.id == rec.currency_id.id)
            dept_config = config_ids.filtered(lambda x: x.department_ids and rec.department_id.id in x.department_ids.ids)
            not_dept_config = config_ids.filtered(lambda x: not x.department_ids)               
            config = dept_config if dept_config else not_dept_config
            if len(config) > 1:
                raise ValidationError(_('Duplicate Record Found! Please Check in Approval Config'))          
            if config.need_approval:
                approver_approvers = rec.employee_id.approver_ids.filtered(lambda a: a.sequence >= config.from_level and a.sequence <= config.to_level).sorted(key=lambda a: a.sequence)
                
                for approver in approver_approvers:
                    approver_id_vals.append(Command.create({
                        'user_ids': [(6, 0, approver.approval_user_ids.ids)],
                        'user_id': approver.approval_user_ids[:1].id if approver.approval_user_ids else False,
                        'status': 'new',
                        'required': False,
                        'level': approver.sequence,
                        'request_id': self.request_id.id,
                        # 'company_id': self.request_id.company_id.id,
                        'cash_advance_id': self.id or self.ids[0],
                    }))

            rec.sudo().write({'approver_ids': approver_id_vals})
            
    def action_view_payment(self):
        return {
            'type': 'ir.actions.act_window', 
            'name': _('Payment'),
            'res_model': 'account.payment',
            'view_mode': 'tree,form',
            'domain': [('cash_advance_id', 'in', self.ids), ('is_cash_advance', '=', True)],
        }
    
    def _get_report_base_filename(self):
        self.ensure_one()
        return 'Cash Advance-%s' % (self.name)
    
    def action_reconcile(self):
        unreconcile_lines = self.env['account.move.line'].sudo().search([
                            ('partner_id','=', self.partner_id.id),
                            ('display_type', 'not in', ('line_section', 'line_note')), 
                            ('account_id.reconcile', '=', True), 
                            ('parent_state', '=', 'posted'), 
                            ('full_reconcile_id', '=', False),
                            ('approval_request_id','=',self.request_id.id),
                            ('account_id','=',self.product_id.property_account_expense_id.id)
                            ])
        if unreconcile_lines and not any(aml.reconciled for aml in unreconcile_lines):
            unreconcile_lines.action_reconcile()
            self.is_clear = True

    def _prepare_reimburse_payment_vals(self):
        payment_type = 'inbound'
        partner_type = 'customer'
        journal_id = False
        if self.payment_type_id.journal_ids:
            journal_id = self.payment_type_id.journal_ids.ids[0]      
        vals = {'partner_id': self.partner_id.id or self.request_owner_id.partner_id.id, 
                'date': self.date,
                'amount': self.amount,
                'payment_type': payment_type,
                'partner_type': partner_type,
                'journal_id': journal_id,
                'company_id': self.company_id.id,
                'ref': self.description,
                'cash_advance_id': self.id,
                'state': 'draft',
                'request_id': self.request_id.id, 
                'purchase_order_no': self.purchase_order_id.name,
                'fmis_job_no': self.fmis_job_no, 
                'job_date': self.job_date, 
                'pay_to_id': self.pay_to_id.id, 
                'pay_to_external': self.pay_to_external, 
                'vendor_quotation_no': self.vendor_quotation_no,  
                'vendor_invoice_no': self.vendor_invoice_no,  
                'vendor_invoice_date': self.date,  
                'product_id': self.product_id.id,
                'staff_location_id': self.staff_location_id.id, 
                'account_payment_type_id': self.payment_type_id.id,
                'currency_id': self.currency_id.id,
                'vehicle_no': self.vehicle_no,
                'bl_no': self.bl_no,
                'reference_key': self.reference_key,
                # 'analytic_distribution': self.analytic_distribution,
                'reason': self.reason,
                'destination_account_id': self.product_id.property_account_expense_id.id,
                'brand_name': self.brand_id.name,
                'location': self.location,
                'delivery_date': self.est_delivery_date,
                'is_cash_advance': True,
                'is_reimburse_payment': True,
                } 
        return vals

    def action_reimburse(self):
        payment_vals = self._prepare_reimburse_payment_vals()
        payment = self.env['account.payment'].sudo().create(payment_vals)
        return payment

    def action_reconcile_reimburse(self):
        reconcilable_payment = self.env['account.payment'].search([
                                        ('cash_advance_id','=',self.id),
                                        ('is_cash_advance','=', 'true'),
                                        ('state','=','posted')
                                        ])
        if reconcilable_payment:
            unreconcile_line = reconcilable_payment.move_id.line_ids
            unreconcile_line.action_reconcile()
        self.is_clear = True

    def export_data(self, fields_to_export, **kwargs):
        data = super(CashAdvanceForm, self).export_data(fields_to_export, **kwargs)
        if 'reason' in fields_to_export:
            field_index = fields_to_export.index('reason')
            for record in data['datas']:
                reason = record[field_index]
                if reason:
                    try:
                        soup = BeautifulSoup(reason)           
                        description = soup.get_text()
                        record[field_index] = description
                    except Exception:
                        record[field_index] = reason
        return data
        
        


        
        
        

        