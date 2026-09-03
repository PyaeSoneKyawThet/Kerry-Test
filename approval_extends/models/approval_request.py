from odoo import fields,Command, models, api, _
from odoo.exceptions import UserError, ValidationError
from bs4 import BeautifulSoup
from collections import defaultdict
PAYMENT_STATE_SELECTION = [ ('draft', 'Draft'),  
                            ('posted', 'Posted'),
                            ('cancel', 'Cancel')
                            ]
PAYMENT_STATUS_SELECTION = [('not_paid', 'Not Paid'),
                            ('in_payment', 'In Payment'),
                            ('paid', 'Paid'),
                            ('partial', 'Partially Paid'),
                            ('reversed', 'Reversed'),
                            ('invoicing_legacy', 'Invoicing App Legacy'),
                            ]
APPROVAL_STATE_SELECTION = [('new', 'To Submit'),  
                            ('pending', 'Submitted'),
                            ('checked', 'Checking'),
                            ('approved', 'Approved'), 
                            ('refused', 'Refused'), 
                            ('cancel', 'Cancel')
                            ]
class ApprovalRequest(models.Model):
    _inherit = "approval.request"  

    def _get_default_payment_type(self):
        return self.env['account.payment.type'].search([('code', '=', 'Main Cash/Bank')], limit=1).id

    employee_id = fields.Many2one('hr.employee', string="Employee", related="request_owner_id.employee_id")
    department_id = fields.Many2one('hr.department',related="employee_id.department_id", string="Department", store=True)  
    currency_id = fields.Many2one('res.currency', string="Currency", default=lambda self: self.env.company.currency_id)  
    amount = fields.Float(string="Amount", compute="_compute_amount",store=True)
    total_amount = fields.Float(string="Total Amount", compute="_compute_total_amount", store=True)
    manual_amount = fields.Boolean(string="Manual Amount", default=True)    
    request_status = fields.Selection(selection_add=APPROVAL_STATE_SELECTION)
    user_status = fields.Selection(selection_add=[('to_check', 'To Checked'), ('checked', 'Checked')])
    minimal_approver =  fields.Integer(string="Minimal Approvers", default=1)
    minimal_checker =  fields.Integer(string="Minimal Checkers", compute="_compute_minimal_checker")
    cash_advance_count = fields.Integer('Cash Advance Count', compute='_compute_cash_advance_data', store=True)
    expense_count = fields.Integer('Expense Count', compute='_compute_expense_data', store=True)
    payment_request_count = fields.Integer('Payment Request Count', compute='_compute_payment_request_data', store=True)
    est_delivery_date = fields.Date(string="Est. Delivery Date")
    value_date = fields.Date(string="Value Date")
    pay_to_id = fields.Many2one('hr.employee', string="Pay To Employee")
    pay_to_external = fields.Char(string="Pay To External") 
    staff_location_id = fields.Many2one('staff.location', string="Doc Location")
    payment_type_id = fields.Many2one('account.payment.type', string="Type", default=_get_default_payment_type)
    default_journal_id = fields.Many2one('account.journal', compute="_compute_default_journal_id", store=True)
    without_PO = fields.Boolean(string="Without PO", default=False, copy=False, compute="_compute_without_po", store=True) 
    created_po = fields.Boolean(string="PO Created", compute="_compute_allowed_purchase_req")
    PR_type = fields.Selection([('cash_advance', 'Cash Advance'), ('expense', 'Expense'), 
                                ('payment_request', 'Payment without PO'),
                                ('Payment with PO', 'Payment with PO'),
                                ('long_contract', 'Payment with PO(Long Contract)')], 
                                string="PR Type",required=True, default='cash_advance')
    po_comparison_id = fields.Many2one('po.comparison', string="PO Comparison No.", copy=False)  
    request_approved_date = fields.Date(string="Request Approved Date", copy=False, help="Request's final approve date")
    request_checked_date = fields.Date(string="Request Checked Date", copy=False, help="Request's final check date")
    enable_payment_request = fields.Boolean(string="Enable Payment Request", compute="_compute_allowed_purchase_req")
    purchase_order_id = fields.Many2one('purchase.order', string="PO", compute="_compute_allowed_purchase_req") 
    has_payment_request = fields.Boolean(string="Has Payment Request", compute='_compute_payment_request_data', store=False,
                                        help="If Payment Request is in cancel state, we can create payment request again.")
    has_cash_advance = fields.Boolean(string="Has Cash Advance", compute='_compute_cash_advance_data', store=True,
                                    help="If Cash Advance is in cancel state, we can create cash advance again.")
    has_expense = fields.Boolean(string="Has Expense", compute='_compute_expense_data', store=True,
                                help="If Expense is in cancel state, we can create expense again.")
    vendor_invoice_no = fields.Char(string="Vendor Invoice No")
    vendor_quotation_date = fields.Date(string="Vendor Quotation Date")
    date = fields.Datetime(string="Date", default=fields.Datetime.now)
    #link with Cash Advance Form
    cash_advance_ids = fields.One2many('cash.advance.form', 'request_id', string="Cash Advances")
    #link with Approval Expense Form
    expense_ids = fields.One2many('approval.expense', 'request_id', string="Expenses")
    #link with Approval Payment Request Form
    payment_request_ids = fields.One2many('approval.payment.request', 'request_id', string="Payment Requests")
    #link with Purchase Order Form
    purchase_ids = fields.One2many('purchase.order', 'rfq_id', string="Purchase Orders")
    has_purchase_order = fields.Boolean(string="Has Purchase Order", compute="_compute_has_purchase_order")
    product_line_ids = fields.One2many('approval.product.line', 'approval_request_id', check_company=True, copy=True)
    fmis_petty_cash_document_no = fields.Char(string="FMIS Document No")
    #To show priority in list view purpose only
    #This part is for Cash Advance priority
    cash_advance_approved_ids = fields.Many2many('cash.advance.form', 'req_cash_adv_rel', 'request_id', 'cash_advance_id',
                                                compute="_compute_cash_advance_priority", string="CA No", store=True)
    cash_advance_state = fields.Selection(selection=APPROVAL_STATE_SELECTION, default=None, compute="_compute_cash_advance_priority", string="CA Status", store=True)
    cash_advance_payment_ids = fields.Many2many('account.payment', 'req_cash_adv_pay_rel', 'request_id', 'payment_id',
                                                compute="_compute_cash_advance_priority", string="CA Payment No", store=True)
    cash_advance_payment_state = fields.Selection(selection=PAYMENT_STATE_SELECTION, 
                                                default=None, compute="_compute_cash_advance_priority", string="CA Payment State", store=True)
    
    #This part is for Expense priority
    expense_approved_ids = fields.Many2many('approval.expense', 'req_expense_rel', 'request_id', 'expense_id',
                                            compute="_compute_expense_priority", string="PC No", store=True)
    expense_state = fields.Selection(selection=APPROVAL_STATE_SELECTION, default=None, compute="_compute_expense_priority", string="PC Status", store=True)
    expense_payment_status = fields.Selection(selection=PAYMENT_STATUS_SELECTION,
                                            default=None, compute="_compute_expense_priority", string="PC Payment Status", store=True) 
    expense_bill_state = fields.Selection(selection=PAYMENT_STATE_SELECTION, 
                                                default=None, compute="_compute_expense_priority", string="PC Bill State", store=True)
    
    #This part is for Payment Request priority
    pay_req_approved_ids = fields.Many2many('approval.payment.request', 'approval_payment_req_rel', 'request_id', 'payment_id',
                                            compute="_compute_payment_request_priority", string="PM No", store=True)
    pay_req_state = fields.Selection(selection=APPROVAL_STATE_SELECTION, default=None, 
                                    compute="_compute_payment_request_priority", string="PM Status", store=True)
    req_pay_status = fields.Selection(selection=PAYMENT_STATUS_SELECTION,default=None, 
                                    compute="_compute_payment_request_priority", string="PM Payment Status", store=True) 
    req_pay_bill_state = fields.Selection(selection=PAYMENT_STATE_SELECTION, default=None, 
                                        compute="_compute_payment_request_priority", string="PM Bill State", store=True)
    pr_done = fields.Boolean(string="PR Done", default=False)
    #search parent department
    parent_department_id = fields.Many2one('hr.department', string="Parent Department", related="department_id.parent_id", store=True)
    #Able to choose multi-PR line in RFQ TASK:6088
    pr_line_ids = fields.Many2many('approval.product.line', string="PR Line(s)", copy=False)
    approval_type = fields.Selection(related="category_id.approval_type", store=True) #add store=True for reporting purpose
    # Restrict Access for Create Payment Request 
    is_pr_expense = fields.Boolean(string="Is Expense", default=False, copy=False, store=True) 
    is_pr_payment_req = fields.Boolean(string="Is Payment without PO", default=False, copy=False, store=True) 
    is_pr_cash_advance = fields.Boolean(string="Is Cash Advance", default=False, copy=False, store=True) 

    #This part is for Cash Advance priority
    @api.depends('cash_advance_ids', 'cash_advance_ids.request_status', 'cash_advance_ids.payment_ids', 'cash_advance_ids.payment_ids.state')
    def _compute_cash_advance_priority(self):
        for rec in self:
            ca_ids = rec.cash_advance_ids
            approved = []
            others = []
            canceled = []
            # Categorize cash advances
            for ca in ca_ids:
                if ca.request_status == 'approved':
                    approved.append(ca)
                elif ca.request_status == 'cancel':
                    canceled.append(ca)
                else:
                    others.append(ca)
            # Determine state and approved_ids
            if ca_ids:
                if approved:
                    rec.cash_advance_state = 'approved'
                    rec.cash_advance_approved_ids = [(6, 0, [ca.id for ca in approved])]
                elif others:
                    rec.cash_advance_state = others[0].request_status
                    rec.cash_advance_approved_ids = [(6, 0, [ca.id for ca in others])]
                else:
                    rec.cash_advance_state = 'cancel'
                    rec.cash_advance_approved_ids = [(6, 0, [ca.id for ca in canceled])]
            else:
                rec.cash_advance_state = None
                rec.cash_advance_approved_ids = [(6, 0, [])]
            # Use in-memory mapped payments instead of searching each time
            payment_map = defaultdict(list)
            for ca in ca_ids:
                payments = ca.payment_ids.filtered(lambda x: x.is_cash_advance)
                for payment in payments:
                    payment_map[payment.state].append(payment)
            # Prioritize posted > draft > cancel
            if payment_map.get('posted'):
                rec.cash_advance_payment_state = 'posted'
                rec.cash_advance_payment_ids = [(6, 0, [p.id for p in payment_map['posted']])]
            elif payment_map.get('draft'):
                rec.cash_advance_payment_state = 'draft'
                rec.cash_advance_payment_ids = [(6, 0, [p.id for p in payment_map['draft']])]
            elif payment_map.get('cancel'):
                rec.cash_advance_payment_state = 'cancel'
                rec.cash_advance_payment_ids = [(6, 0, [p.id for p in payment_map['cancel']])]
            else:
                rec.cash_advance_payment_state = None
                rec.cash_advance_payment_ids = [(6, 0, [])]

    #This part is for Expense priority
    @api.depends('expense_ids', 'expense_ids.request_status', 'expense_ids.move_id.payment_state', 
                'expense_ids.bill_ids', 'expense_ids.bill_ids.state')
    def _compute_expense_priority(self):
        for rec in self:
            exp_ids = rec.expense_ids
            approved = []
            others = []
            canceled = []
            # Categorize Expenses
            for exp in exp_ids:
                if exp.request_status == 'approved':
                    approved.append(exp)
                elif exp.request_status == 'cancel':
                    canceled.append(exp)
                else:
                    others.append(exp)
            # Determine state and approved_ids
            if exp_ids:
                if approved:
                    rec.expense_state = 'approved'
                    rec.expense_payment_status = approved[0].move_id.payment_state
                    rec.expense_approved_ids = [(6, 0, [ca.id for ca in approved])]
                elif others:
                    rec.expense_state = others[0].request_status
                    rec.expense_payment_status = others[0].move_id.payment_state
                    rec.expense_approved_ids = [(6, 0, [ca.id for ca in others])]
                else:
                    rec.expense_state = 'cancel'
                    rec.expense_payment_status = 'not_paid'
                    rec.expense_approved_ids = [(6, 0, [ca.id for ca in canceled])]
            else:
                rec.expense_state = None
                rec.expense_payment_status = None
                rec.expense_approved_ids = [(6, 0, [])]
            # Use in-memory mapped vendor bill instead of searching each time
            bill_map = defaultdict(list)
            for exp in exp_ids:
                bills = exp.bill_ids
                for bill in bills:
                    bill_map[bill.state].append(bill)
            # Prioritize posted > draft > cancel
            if bill_map.get('posted'):
                rec.expense_bill_state = 'posted'
                
            elif bill_map.get('draft'):
                rec.expense_bill_state = 'draft'
               
            elif bill_map.get('cancel'):
                rec.expense_bill_state = 'cancel'
                
            else:
                rec.expense_bill_state = None

    #This part is for Payment Request priority
    @api.depends('payment_request_ids', 'payment_request_ids.request_status', 'payment_request_ids.move_id.payment_state', 
                'payment_request_ids.bill_ids', 'payment_request_ids.bill_ids.state')
    def _compute_payment_request_priority(self):
        for rec in self:
            pay_ids = rec.payment_request_ids
            approved = []
            others = []
            canceled = []
            # Categorize Payment Request
            for pay in pay_ids:
                if pay.request_status == 'approved':
                    approved.append(pay)
                elif pay.request_status == 'cancel':
                    canceled.append(pay)
                else:
                    others.append(pay)
            # Determine state and approved_ids
            if pay_ids:
                if approved:
                    rec.pay_req_state = 'approved'
                    rec.req_pay_status = approved[0].move_id.payment_state
                    rec.pay_req_approved_ids = [(6, 0, [ca.id for ca in approved])]
                elif others:
                    rec.pay_req_state = others[0].request_status
                    rec.req_pay_status = others[0].move_id.payment_state
                    rec.pay_req_approved_ids = [(6, 0, [ca.id for ca in others])]
                else:
                    rec.pay_req_state = 'cancel'
                    rec.req_pay_status = 'not_paid'
                    rec.pay_req_approved_ids = [(6, 0, [ca.id for ca in canceled])]
            else:
                rec.pay_req_state = None
                rec.req_pay_status = None
                rec.pay_req_approved_ids = [(6, 0, [])]
            # Use in-memory mapped vendor bill instead of searching each time
            bill_map = defaultdict(list)
            for pay in pay_ids:
                bills = pay.bill_ids
                for bill in bills:
                    bill_map[bill.state].append(bill)
            # Prioritize posted > draft > cancel
            if bill_map.get('posted'):
                rec.req_pay_bill_state = 'posted'
                
            elif bill_map.get('draft'):
                rec.req_pay_bill_state = 'draft'
               
            elif bill_map.get('cancel'):
                rec.req_pay_bill_state = 'cancel'
                
            else:
                rec.req_pay_bill_state = None

    #This part is for RFQ purpose
    #Able to choose multi-PR line in RFQ 
    def action_generate_lines(self):
        """Create RFQ Line records from RFQ product_line_ids one by one"""
        for rec in self:
            if rec.pr_line_ids:
                rec.product_line_ids.unlink()  # optional: clear old lines
            lines_vals = []
            for pr_line in rec.pr_line_ids:                
                lines_vals.append({
                    'approval_request_id': rec.id,
                    'purchase_request_line_id': pr_line.id,
                    'product_id': pr_line.product_id.id,
                    'description': pr_line.description,
                    'brand_id': pr_line.brand_id.id,
                    'fmis_job_no': pr_line.fmis_job_no,
                    'quantity': pr_line.quantity,
                    'unit_price': pr_line.unit_price,
                    'analytic_distribution': pr_line.analytic_distribution,
                    'bl_no': pr_line.bl_no,
                    'vehicle_no': pr_line.vehicle_no,
                    'reference_key': pr_line.reference_key,
                    'product_uom_id': pr_line.product_uom_id.id
                })
            if lines_vals:
                self.env['approval.product.line'].create(lines_vals)

    # override odoo's original method
    def _compute_purchase_order_count(self):
        rfq_ids = self.ids
        po_data = self.env['purchase.order'].read_group(
            [('rfq_id', 'in', rfq_ids)],
            ['rfq_id'],
            ['rfq_id']
        )
        count_map = {data['rfq_id'][0]: data['rfq_id_count'] for data in po_data}
        for request in self:
            request.purchase_order_count = count_map.get(request.id, 0)

    def _compute_has_purchase_order(self):
        rfq_ids = self.ids
        result = dict.fromkeys(rfq_ids, 0)
        if rfq_ids:
            domain = [('rfq_id', 'in', rfq_ids), ('state', '!=', 'cancel')]
            grouped_data = self.env['purchase.order'].read_group(domain, ['rfq_id'], ['rfq_id'])
            for group in grouped_data:
                rfq_id = group['rfq_id'][0]
                result[rfq_id] = group['rfq_id_count']
        for request in self:
            request.has_purchase_order = result.get(request.id, 0) > 0

    @api.onchange('partner_id')
    def _get_payment_type(self):
        default_type = self.env['account.payment.type'].search([('code', '=', 'Main Cash/Bank')], limit=1)
        if self.partner_id:
            self.payment_type_id = self.partner_id.type_id or default_type
        else:
            self.payment_type_id = default_type
    
    @api.depends('PR_type')
    @api.onchange('PR_type')
    def _compute_without_po(self):
        if self.PR_type in ('Payment with PO', 'long_contract'):
            self.without_PO = False
        else:
            self.without_PO = True


    @api.depends('purchase_order_count', 'approval_type', 'request_status', 'payment_request_ids')
    def _compute_allowed_purchase_req(self):
        self_ids = self.ids
        # Pre-fetch all purchase orders linked to rfq_id for 'purchase' type
        rfq_purchase_orders = self.env['purchase.order'].search_read(
            [('rfq_id', 'in', self_ids), ('state', 'in', ('purchase', 'done'))],
            ['id', 'rfq_id']
        )
        rfq_purchase_map = {}
        po_rfq_ids = set()
        for po in rfq_purchase_orders:
            rfq_id = po['rfq_id'][0] if po['rfq_id'] else False
            if rfq_id:
                po_rfq_ids.add(rfq_id)
                rfq_purchase_map[rfq_id] = po['id']
        for rec in self:
            rec.purchase_order_id = False
            if rec.approval_type == 'purchase':
                rec.created_po = rec.id in po_rfq_ids
                rec.enable_payment_request = rec.created_po
                rec.purchase_order_id = rfq_purchase_map.get(rec.id, False)
            else:
                rec.created_po = False
                rec.enable_payment_request = rec.request_status == 'approved'
    ##### End of RFQ part #####

    @api.depends('staff_location_id', 'staff_location_id.expense_journal_ids')
    def _compute_default_journal_id(self):
        for rec in self:
            journals = rec.staff_location_id.expense_journal_ids
            rec.default_journal_id = journals and journals[0].id or False

    @api.depends('approver_ids', 'category_id.approval_type')
    def _compute_minimal_checker(self):
        for rec in self:
            if rec.category_id.approval_type == 'purchase_req' and rec.approver_ids:
                rec.minimal_checker = max(len(rec.approver_ids) - 1, 0)
            else:
                rec.minimal_checker = 0

    @api.depends('product_line_ids')
    def _compute_total_amount(self):
        for rec in self: 
            rec.total_amount = sum(rec.product_line_ids.mapped('total')) 
            rec.manual_amount = False
                              
    @api.depends('total_amount') 
    def _compute_amount(self):
        for rec in self:    
            if rec.product_line_ids:
                rec.manual_amount = False
            if not rec.manual_amount:        
                rec.amount = rec.total_amount
            else:
                rec.amount = rec.amount            
                       
    @api.depends('approver_ids.status', 'approver_ids.required')
    def _compute_request_status(self):
        for request in self:
            if request.category_id.approval_type != 'purchase_req':
                super()._compute_request_status()
                continue

            status_lst = request.mapped('approver_ids.status')
            minimal_approver = request.minimal_approver if len(status_lst) >= request.minimal_approver else len(status_lst)
            if request.approval_type == 'purchase':
                minimal_approver = request.approval_minimum if len(status_lst) >= request.approval_minimum else len(status_lst)
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
            request.request_status = status

        self.filtered_domain([('request_status', 'in', ['approved', 'refused', 'cancel'])])._cancel_activities()

    #Multi-approver for each level feature TASK:4529
    @api.depends_context('uid')
    @api.depends('approver_ids.status', 'approver_ids.user_ids')
    def _compute_user_status(self):
        single_approver_approvals = self.env['approval.request']
        for approval in self:
            approvers = approval.approver_ids.filtered(
                lambda approver: self.env.user in approver.user_ids
            )
            if len(approvers) == 1:
                single_approver_approvals |= approval
            elif len(approvers) > 1:
                approval.user_status = approvers[0].status
            else:
                approval.user_status = False

        if single_approver_approvals:
            super(ApprovalRequest, single_approver_approvals)._compute_user_status()

    #Multi-approver for each level feature TASK:4529
    @api.constrains('approver_ids')
    def _check_approver_ids(self):
        for request in self:
            if request.category_id.approval_type != 'purchase_req':
                super()._check_approver_ids()
                continue
            pass

    @api.depends('cash_advance_ids', 'cash_advance_ids.request_status')
    def _compute_cash_advance_data(self):
        for rec in self:
            cash_advances = rec.cash_advance_ids
            rec.cash_advance_count = len(cash_advances)
            rec.has_cash_advance = any(exp.request_status != 'cancel' for exp in cash_advances)
    
    @api.depends('expense_ids', 'expense_ids.request_status')
    def _compute_expense_data(self):
        for rec in self:
            expenses = rec.expense_ids
            rec.expense_count = len(expenses)
            rec.has_expense = any(exp.request_status != 'cancel' for exp in expenses)

    @api.depends('payment_request_ids','payment_request_ids.request_status')
    def _compute_payment_request_data(self):
        for rec in self:
            payment_requests = rec.payment_request_ids
            rec.payment_request_count = len(payment_requests)
            if rec.approval_type == 'purchase':
                # rec.has_payment_request = any(pr.request_status != 'cancel' for pr in payment_requests)
                rec.has_payment_request = False
            else:
                rec.has_payment_request = False

    #Multi-approver for each level feature TASK:4529
    def action_confirm(self):
        self.ensure_one()
        status = None
        if self.category_id.approval_type == 'purchase_req':
            if len(self.approver_ids) < self.minimal_approver:
                raise UserError(_("You have to add at least %s approvers to confirm your request.", self.minimal_approver))
            if self.requirer_document == 'required' and not self.attachment_number:
                raise UserError(_("You have to attach at least one document."))
            approvers = self.approver_ids
            if not self.approver_sequence:
                raise UserError(_("Please enable approver sequence in category!"))
            approvers = approvers.filtered(lambda a: a.status in ['new', 'to_check', 'pending', 'waiting'])
            if approvers:
                status  = 'pending' if len(approvers) == 1 else 'to_check'
            approvers[1:].sudo().write({'status': 'waiting'})
            approvers = approvers[0] if approvers and approvers[0].status != 'to_check' else self.env['approval.approver']
            approvers._create_activity()
            approvers.sudo().write({'status': status})
            self.sudo().write({'date_confirmed': fields.Datetime.now()})
        else:
            super().action_confirm()
    

    #Multi-approver for each level feature TASK:4529
    def action_approve(self, approver=None):
        if self.category_id.approval_type != 'purchase_req':       
            if self.po_comparison_id:
                approved_rfq_id = self.po_comparison_id.sudo().request_ids.filtered(lambda request: request.request_status == 'approved')
                if approved_rfq_id:
                    raise UserError(_("Another RFQ is already approved!"))
                else: 
                    super().action_approve(approver)
                    rfq_ids = self.po_comparison_id.sudo().request_ids.filtered(lambda request: request.request_status != 'approved')
                    for request in rfq_ids:
                        request.action_refuse()
            super().action_approve(approver)
        else:
            self._ensure_can_approve()
            if not isinstance(approver, models.BaseModel):
                approver = self.mapped('approver_ids').filtered(
                    lambda approver: self.env.user in approver.user_ids
                )
            approver.write({'status': 'approved'})
            self.sudo().write({'request_approved_date': fields.Datetime.now()})
            self.sudo()._update_next_approvers('pending', approver, only_next_approver=True)
            self.sudo()._get_user_approval_activities(user=self.env.user).action_feedback()
            

    def action_cancel(self):
        if self.request_status == 'approved':
            if self.approval_type == 'purchase_req' and (self.cash_advance_ids.filtered(lambda x: x.request_status == 'approved') \
                or self.expense_ids.filtered(lambda x: x.request_status == 'approved') or self.payment_request_ids.filtered(lambda x: x.request_status == 'approved')):
                raise ValidationError(_('You cannot cancel in CA or Petty Cash or PR Approved state!'))
            if self.approval_type == 'purchase':
                if self.purchase_ids.filtered(lambda x: x.state in ['purchase', 'done']):
                    raise ValidationError(_('You cannot cancel in PO Approved state!'))
                if self.payment_request_ids.filtered(lambda x: x.request_status == 'approved'):
                    raise ValidationError(_('You cannot cancel in PR Approved state!'))
                
        self.cash_advance_ids.filtered(lambda x: x.request_status != 'cancel').action_cancel()
        self.expense_ids.filtered(lambda x: x.request_status != 'cancel')._action_cancel()
        self.payment_request_ids.filtered(lambda x: x.request_status != 'cancel')._action_cancel()
        self.write({'request_status': 'cancel'})
        return super().action_cancel()
            
    #-----------------------------------
    # helper methods for multi approver
    #-----------------------------------
    def _ensure_can_check(self):
        if any(approval.approver_sequence and approval.user_status == 'waiting' for approval in self):
            raise ValidationError(_('You cannot check before the previous checker.'))
        
    def _update_next_checkers(self, new_status, checker, only_next_checker, cancel_activities=False):
        checkers_updated = self.env['approval.approver']
        for approval in self.filtered('approver_sequence'):
            current_checker = approval.approver_ids & checker
            checkers_to_update = approval.approver_ids.filtered(lambda a: a.status not in ['approved', 'refused'] \
                                and (a.level > current_checker.level or (a.level == current_checker.level and a.id > current_checker.id)))
            if only_next_checker and checkers_to_update:
                checkers_to_update = checkers_to_update[0]
            checkers_updated |= checkers_to_update
        checkers_updated.sudo().status = new_status
        checkers_updated.sudo()._create_activity()
        if cancel_activities:
            checkers_updated.request_id._cancel_activities()

    #Multi-approver for each level feature TASK:4529
    def action_check(self, checker=None): 
        self._ensure_can_check()        
        if not isinstance(checker, models.BaseModel):
            checker = self.mapped('approver_ids').filtered(lambda checker: self.env.user in checker.user_ids)
        checker.status = 'checked'
        self.sudo().write({'request_checked_date': fields.Datetime.now()})
        status_lst = self.mapped('approver_ids.status')        
        if status_lst.count('checked') >= (self.minimal_checker):
            self.sudo()._update_next_checkers('pending', checker, only_next_checker=True)
        else:
            self.sudo()._update_next_checkers('to_check', checker, only_next_checker=True)
        for user in checker.user_ids:
            self.sudo()._get_user_approval_activities(user=user).action_feedback()

    @api.depends('category_id', 'request_owner_id', 'amount', 'currency_id')
    def _compute_approver_ids(self):
        for rec in self:
            if rec.category_id.approval_type != 'purchase_req':
                super()._compute_approver_ids()
                continue
            approver_id_vals = [Command.clear()]
            category = rec.category_id
            # Pre-filter configs only once
            config_ids = category.approval_process_config_ids.filtered(
                lambda x: x.from_amount <= rec.amount
                and x.to_amount >= rec.amount
                and x.currency_id == rec.currency_id
            )
            # Use department match only if present
            config = config_ids.filtered(lambda x: rec.department_id and rec.department_id.id in x.department_ids.ids)
            if not config:
                config = config_ids.filtered(lambda x: not x.department_ids)
            if len(config) > 1:
                raise ValidationError(_('Duplicate Record Found! Please Check in Approval Config'))
            config = config[0] if config else None
            if config:
                # Use search to avoid computing all employee.approver_ids unnecessarily
                approvers = rec.employee_id.approver_ids.filtered(
                    lambda a: config.from_level <= a.sequence <= config.to_level
                )
                # Sort once and use generator expression
                for approver in sorted(approvers, key=lambda a: a.sequence):
                    approver_id_vals.append(Command.create({
                        'user_ids': [(6, 0, approver.approval_user_ids.ids)],
                        'user_id': approver.approval_user_ids[:1].id if approver.approval_user_ids else False,
                        'status': 'new',
                        'required': False,
                        'level': approver.sequence
                    }))
            rec.approver_ids = approver_id_vals
                
    def _prepare_cash_advance_vals(self):
        """Prepare vals for cash advance form creation."""
        cash_advance_categ = self.env['approval.category'].search(
            [('approval_type', '=', 'cash_advance')], limit=1)
        if not cash_advance_categ:
            raise UserError(_("Cash Advance Approval Category not configured!"))
        result = []
        for rec in self:         
            approval_product_line = rec.product_line_ids[:1]
            vals = {
                'request_owner_id' : rec.request_owner_id.id,
                'category_id': cash_advance_categ.id,
                'request_id' : rec.id,
                'purchase_order_id' : rec.purchase_order_id.id,
                'currency_id' : rec.currency_id.id or False,
                'pay_to_id' : rec.pay_to_id.id,
                'pay_to_external': rec.pay_to_external,
                'partner_id' : rec.partner_id.id,
                'payment_type_id' : rec.payment_type_id.id,
                'staff_location_id': rec.staff_location_id.id,
                'vendor_quotation_no': rec.reference, #reference is named as 'Vendor Quotation No' on view
                'vendor_invoice_no': rec.vendor_invoice_no,
                'product_id' : approval_product_line.product_id.id, 
                'description' : approval_product_line.description, 
                'fmis_job_no' : approval_product_line.fmis_job_no,
                'job_date' : approval_product_line.job_date,
                'vehicle_no' : approval_product_line.vehicle_no,
                # 'analytic_distribution' : approval_product_line.analytic_distribution,
                'bl_no': approval_product_line.bl_no,
                'reference_key': approval_product_line.reference_key,
                'brand_id' : approval_product_line.brand_id.id,
                'amount': rec.amount,
                'reason': rec.reason,
                'est_delivery_date': rec.est_delivery_date,
                'location': rec.location,
            }
            result.append(vals)
        return vals
                
    def action_create_cash_advance(self): 
        self.ensure_one()
        vals = self._prepare_cash_advance_vals()
        cash_advance = self.env['cash.advance.form'].create(vals) 
        return {
            'name': "Cash Advance",
            'view_mode': 'form',
            'res_model': 'cash.advance.form',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'view_id': self.env.ref('approval_extends.cash_advance_form_view').id,
            'res_id': cash_advance.id,
        }
    
    def action_view_cash_advance_form(self):
        self.ensure_one()
        result = {
                "type": "ir.actions.act_window",
                "res_model": "cash.advance.form",
                "domain": [('id', 'in', self.cash_advance_ids.ids)],
                "name": ("Cash Advance Form"),
                'view_mode': 'tree,form', 
                }
        if len(self.cash_advance_ids) == 1:
            result.update({
                'res_id':self.cash_advance_ids.ids[0],
                'view_mode':'form', 
                })
        return result 
    
    def _prepare_expense_line_vals(self, line):
        product = line.product_id
        expense_account = product.property_account_expense_id.id or product.categ_id.property_account_expense_categ_id.id
        return {
            'product_id': product.id,
            'description': line.description,
            'brand_id': line.brand_id.id,
            'fmis_job_no': line.fmis_job_no,
            'job_date': line.job_date,
            'vehicle_no': line.vehicle_no,
            'quantity': line.quantity,
            'price_unit': line.unit_price,
            'product_uom_id': line.product_uom_id.id,
            'bl_no': line.bl_no,
            'analytic_distribution': line.analytic_distribution,
            'tax_ids': False,
            'account_id': expense_account,
        }

    def _prepare_expense_vals(self):
        self.ensure_one()
        expense_category = self.env['approval.category'].search([('approval_type', '=', 'expense')], limit=1)
        if not expense_category:
            raise UserError(_("Expense Approval Category not configured!"))
        line_vals = [(0, 0, self._prepare_expense_line_vals(line)) for line in self.product_line_ids]
        return {
            'request_owner_id': self.request_owner_id.id,
            'category_id': expense_category.id,
            'request_id': self.id,
            'purchase_order_id': self.purchase_order_id.id,
            'currency_id': self.currency_id.id,
            'staff_location_id': self.staff_location_id.id,
            'journal_id': self.default_journal_id.id,
            'partner_id': self.partner_id.id,
            'vendor_quotation_no': self.reference,
            'vendor_invoice_no': self.vendor_invoice_no,
            'pay_to_id': self.pay_to_id.id,
            'pay_to_external': self.pay_to_external,
            'delivery_date': self.est_delivery_date,
            'value_date': self.value_date,
            'payment_type_id': self.payment_type_id.id,
            'expense_line_ids': line_vals,
            'reason': self.reason,
            'location': self.location,
            'fmis_petty_cash_document_no': self.fmis_petty_cash_document_no,
        }

    def action_create_expense(self):
        self.ensure_one()
        vals = self._prepare_expense_vals()
        expense_form = self.env['approval.expense'].create(vals)
        return {
            'name': _("Expense Form"),
            'view_mode': 'form',
            'res_model': 'approval.expense',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'view_id': self.env.ref('approval_extends.approval_expense_form_view').id,
            'res_id': expense_form.id,
        }

    def action_view_expense(self):
        self.ensure_one()
        result = {
            "type": "ir.actions.act_window",
            "res_model": "approval.expense",
            "domain": [('id', 'in', self.expense_ids.ids)],
            "name": _("Expense Form"),
            "view_mode": "tree,form",
        }
        if len(self.expense_ids) == 1:
            result.update({
                "res_id": self.expense_ids.id,
                "view_mode": "form",
            })
        return result
    
    @api.model
    def _prepare_purchase_order_line_vals(self, product_id, product_qty, product_uom, company_id, supplier, po,brand_id,vehicle_no,bl_no,
                                          reference_key,analytic_distribution,price_unit,purchase_request_line_id,description):
        vals = self.env['purchase.order.line']._prepare_purchase_order_line(product_id, product_qty, product_uom, company_id, supplier, po)
        vals.update({
            'brand_id': brand_id,
            'vehicle_no': vehicle_no,
            'bl_no': bl_no,
            'reference_key': reference_key,
            'analytic_distribution': analytic_distribution,
            'price_unit': price_unit,
            'product_uom': product_uom.id,
            'product_qty': product_qty,
            'purchase_request_line_id': purchase_request_line_id.id,
            'name': description
        })
        return vals
    
    # Override odoo's original def action_create_purchase_orders
    def action_create_purchase_orders(self):
        # super(ApprovalRequest, self).action_create_purchase_orders() 
        """ Create and/or modifier Purchase Orders. """
        self.ensure_one()
        self.product_line_ids._check_products_vendor()
        for line in self.product_line_ids:
            seller = line._get_seller_id()
            vendor = seller.partner_id
            """ID:3013
            Odoo's default: when products have different vendor will split purchase order(multi vendor->multi PO)
            Customize: when approval_request have vendor, use it to create purchase order(only one PO will create)
            """
            if self.partner_id:
                vendor = self.partner_id
            po_domain = [
                ('company_id', '=', self.company_id.id),
                ('partner_id', '=', vendor.id),
                ('state', '=', 'draft'),
                ('approval_request_ids', '=', self.id),
            ]
            purchase_orders = self.env['purchase.order'].search(po_domain)
            if purchase_orders:
                # Existing RFQ found: check if we must modify an existing
                # purchase order line or create a new one.
                purchase_line = self.env['purchase.order.line'].search([
                    ('order_id', 'in', purchase_orders.ids),
                    ('product_id', '=', line.product_id.id),
                    ('product_uom', '=', line.product_uom_id.id),
                    ('price_unit', '=', line.unit_price),
                    ('brand_id', '=', line.brand_id.id),
                    ('vehicle_no', '=', line.vehicle_no),
                    ('bl_no', '=', line.bl_no),
                    ('reference_key', '=', line.reference_key),
                    ('name', '=', line.description),
                ], limit=1)
                purchase_order = self.env['purchase.order']
                if purchase_line and purchase_line.analytic_distribution == line.analytic_distribution:
                    # Compatible po line found, only update the quantity.
                    line.purchase_order_line_id = purchase_line.id
                    purchase_line.product_qty += line.quantity
                    purchase_line.price_unit = line.unit_price
                    purchase_order = purchase_line.order_id
                else:
                    # No purchase order line found, create one.
                    purchase_order = purchase_orders[0]
                    po_line_vals = self._prepare_purchase_order_line_vals(
                                        line.product_id,line.quantity,
                                        line.product_uom_id,line.company_id,
                                        seller,purchase_order,
                                        line.brand_id.id,line.vehicle_no,
                                        line.bl_no,line.reference_key,
                                        line.analytic_distribution,
                                        line.unit_price,
                                        line.purchase_request_line_id,
                                        line.description,
                                    )
                    new_po_line = self.env['purchase.order.line'].create(po_line_vals)
                    line.purchase_order_line_id = new_po_line.id
                    purchase_order.order_line = [(4, new_po_line.id)]
                # Add the request name on the purchase order `origin` field.
                new_origin = set([self.name])
                if purchase_order.origin:
                    missing_origin = new_origin - set(purchase_order.origin.split(', '))
                    if missing_origin:
                        purchase_order.write({'origin': purchase_order.origin + ', ' + ', '.join(missing_origin)})
                else:
                    purchase_order.write({'origin': ', '.join(new_origin)}) 
            else:
                # No RFQ found: create a new one.
                po_vals = line._get_purchase_order_values(vendor)
                new_purchase_order = self.env['purchase.order'].create(po_vals)
                po_line_vals = self._prepare_purchase_order_line_vals(
                                        line.product_id,line.quantity,
                                        line.product_uom_id,line.company_id,
                                        seller,new_purchase_order,
                                        line.brand_id.id,line.vehicle_no,
                                        line.bl_no,line.reference_key,
                                        line.analytic_distribution,
                                        line.unit_price,
                                        line.purchase_request_line_id,
                                        line.description
                                    )
                new_po_line = self.env['purchase.order.line'].create(po_line_vals)
                line.purchase_order_line_id = new_po_line.id
                new_purchase_order.order_line = [(4, new_po_line.id)]
        
    def _prepare_po_lines(self,name,product_qty,product_id,product_uom,price_unit,order_id,job_location_id,brand_id,vehicle_no,bl_no,reference_key,date_planned):
        return {
                'name': name,
                'product_qty': product_qty, 
                'product_id': product_id,
                'product_uom': product_uom,
                'price_unit': price_unit,
                'order_id': order_id,
                'brand_id': brand_id,
                'vehicle_no': vehicle_no,
                'bl_no': bl_no,
                'reference_key': reference_key,
                # 'job_location_id': job_location_id,
                'date_planned': date_planned,
        }
        
    def action_create_purchase(self):
        """ Always create a new Purchase Order for each product line. """
        self.ensure_one()
        for line in self.product_line_ids:                        
            if self.partner_id:
                partner = self.partner_id
            else:
                partner = self.request_owner_id.partner_id
            purchase_order = self.env['purchase.order'].search([('approval_request_ids','in', self.ids), ('partner_id', '=', partner.id), ('currency_id', '=', self.currency_id.id)])
            po_vals = line._get_purchase_order_values(partner)
            if purchase_order:
                po_line = purchase_order.order_line.filtered(lambda x: x.product_uom.id == line.product_uom_id.id and x.price_unit == line.unit_price)
                if purchase_order.order_line and po_line:
                    po_line.product_qty += line.quantity
                    po_line.price_unit = line.unit_price
                    line.purchase_order_line_id = po_line.id  
                else:
                    po_line_vals = self._prepare_po_lines(line.product_id.name, line.quantity,
                                                            line.product_id.id, line.product_uom_id.id,
                                                            line.unit_price, purchase_order.id, 
                                                            line.job_location_id,
                                                            line.brand_id,line.vehicle_no,
                                                            line.bl_no,line.reference_key,
                                                            self.est_delivery_date,
                                                            )
                    new_po_line = self.env['purchase.order.line'].create(po_line_vals)
                    line.purchase_order_line_id = new_po_line.id              
            else:
                new_purchase_order = self.env['purchase.order'].create(po_vals)                
                po_line_vals = self._prepare_po_lines(line.product_id.name,line.quantity, 
                                                      line.product_id.id,line.product_uom_id.id,
                                                      line.unit_price,new_purchase_order.id,
                                                      line.job_location_id.id,
                                                      line.brand_id.id,line.vehicle_no,
                                                      line.bl_no,line.reference_key,
                                                      self.est_delivery_date,
                                                      )                
                new_po_line = self.env['purchase.order.line'].create(po_line_vals)
                line.purchase_order_line_id = new_po_line.id                                
                new_purchase_order.order_line = [(4, new_po_line.id)]              
            
    def action_create_PO(self):
        for rec in self.filtered(lambda x: x.request_status == 'approved' and x.approval_type == 'purchase_req'):
            rec.action_create_purchase()
            
    def unlink(self):
        if self.filtered(lambda a: a.request_status == 'approved'): 
            raise UserError(_("You can't delete in approved state"))        
        request_from_comparison = self.filtered(lambda a: a.po_comparison_id)
        if request_from_comparison:
            for request in request_from_comparison:
                request_from_comparison.product_line_ids.sudo().update({
                    'po_comparison_line_id': False
                })
        return super().unlink()

    def action_view_payment_request(self):
        self.ensure_one()
        action = {
            "type": "ir.actions.act_window",
            "name": _("Payment Request Form"),
            "res_model": "approval.payment.request",
            "view_mode": "tree,form",
            "domain": [('id', 'in', self.payment_request_ids.ids)],
        }
        if len(self.payment_request_ids) == 1:
            action.update({
                'res_id': self.payment_request_ids.id,  # safe because it's one record
                'view_mode': 'form',
            })
        return action
    
    def _prepare_payment_request_vals(self):
        self.ensure_one()
        category = self.env['approval.category'].search(
            [('approval_type', '=', 'payment_request')], limit=1)
        
        def _get_grn_no(po):
            picking = next((
                p for p in po.picking_ids
                if p.picking_type_id.code == 'incoming'
            ), None)
            return picking.name if picking else ''

        lines_vals = []
        for line in self.product_line_ids:
            account_id = (
                line.product_id.property_account_expense_id.id or
                line.product_id.categ_id.property_account_expense_categ_id.id or False
            )
            lines_vals.append((0, 0, {
                'purchase_line_id': line.purchase_order_line_id.id,
                'product_id': line.product_id.id,
                'description': line.description,
                'brand_id': line.brand_id.id,
                'fmis_job_no': line.fmis_job_no,
                'job_date': line.job_date,
                'vehicle_no': line.vehicle_no,
                'quantity': line.quantity,
                'price_unit': line.unit_price,
                'product_uom_id': line.product_uom_id.id,
                'bl_no': line.bl_no,
                'analytic_distribution': line.analytic_distribution,
                'account_id': account_id,
                'reference_key': line.reference_key,
            }))

        return {
            'request_owner_id': self.request_owner_id.id,
            'category_id': category.id,
            'request_id': self.id,
            'is_purchase': self.approval_type == 'purchase',
            'purchase_order_id': self.purchase_order_id.id,
            'partner_id': self.partner_id.id,
            'vendor_bank_info': self.partner_id.vendor_bank_info,
            'currency_id': self.currency_id.id or False,
            'value_date': self.value_date,
            'pay_to_id': self.pay_to_id.id,
            'pay_to_external': self.pay_to_external,
            'staff_location_id': self.staff_location_id.id,
            'journal_id': self.default_journal_id.id,
            'payment_request_line_ids': lines_vals,
            'payment_type_id': self.payment_type_id.id,
            'reason': self.reason,
            'delivery_date': self.est_delivery_date,
            'location': self.location,
            'grn_no': _get_grn_no(self.purchase_order_id),
            'vendor_quotation_no': self.reference,
            'vendor_invoice_no': self.vendor_invoice_no,
        }
    
    def action_create_payment_request(self):
        self.ensure_one()
        vals = self._prepare_payment_request_vals()
        payment_request_form = self.env['approval.payment.request'].create(vals)
        if self.PR_type == 'payment_request':
            self.is_pr_payment_req = True
        if self.PR_type == 'expense':
            self.is_pr_expense = True   
        if self.PR_type == 'cash_advance':
            self.is_pr_cash_advance = True  
        return {
            'name': "Approval Payment Request Form",
            'view_mode': 'form',
            'res_model': 'approval.payment.request',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'view_id': self.env.ref('approval_extends.approval_payment_request_form_view').id,
            'res_id': payment_request_form.id,
        }

    def action_view_po_comparison(self):
        po_comparison_ids = self.env['po.comparison'].search([('id','=',self.po_comparison_id.id)])
        result = {
                "type": "ir.actions.act_window",
                "res_model": "po.comparison",
                "domain": [('id', 'in', po_comparison_ids.ids)],
                "name": ("PO Comparison"),
                'view_mode': 'tree,form', 
            }
        if len(po_comparison_ids)==1:
            result.update({
                'res_id':po_comparison_ids.id,
                'view_mode':'form', 
                })
        return result 
    
    def _get_report_base_filename(self):
        self.ensure_one()
        return 'PURCHASE REQUISITION-%s' % (self.name)
    
    @api.model_create_multi
    def create(self, vals_list):
        recs = super().create(vals_list)
        for rec in recs:
            if not rec.request_owner_id:
                rec.request_owner_id = self.env.uid
        return recs
    
    def action_open_purchase_orders(self):
        purchase_ids = self.env['purchase.order'].search([('rfq_id','=',self.id)]).ids
        domain = [('id', 'in', purchase_ids)]
        action = super().action_open_purchase_orders()
        action['domain'] = domain
        return action
    
    def action_print_approval_purchase_request(self):
        return self.env.ref('approval_extends.approval_purchase_request_report').report_action(self)
    
    def export_data(self, fields_to_export, **kwargs):
        data = super(ApprovalRequest, self).export_data(fields_to_export, **kwargs)
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
    
    def action_draft(self):
        res = super().action_draft()
        self.mapped('expense_ids').write({'is_request_cancel': False})
        self.mapped('payment_request_ids').write({'is_request_cancel': False})
        self.mapped('cash_advance_ids').write({'is_request_cancel': False})
        self.write({'request_status': 'new'})#without approver case
        return res