from odoo import api, fields,Command, models, _
from odoo.exceptions import UserError, ValidationError
from datetime import date
from bs4 import BeautifulSoup
import re

import logging
_logger = logging.getLogger(__name__)

class ApprovalPaymentRequest(models.Model): 
    _name = 'approval.payment.request'
    _description = "Approval Payment Request"
    _inherit = ['mail.thread', 'mail.activity.mixin'] 
    _order = 'name'
    _mail_post_access = 'read'

    @api.model
    def _read_group_request_status(self, stages, domain, order):
        request_status_list = dict(self._fields['request_status'].selection).keys()
        return request_status_list

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

    name = fields.Char(string="Name")
    date = fields.Date(string="PRQ Date", default=date.today())
    request_id = fields.Many2one('approval.request', string="Purchase Request Ref") 
    purchase_order_id = fields.Many2one('purchase.order',string="Purchase Order No.", tracking=True, copy=False)
    partner_id = fields.Many2one('res.partner', string="Vendor",tracking=True)

    delivery_date = fields.Date(string="Est. Delivery Date", default=date.today())
    receive_date = fields.Date(string="Receive Date", default=date.today())
    grn_no = fields.Char(string="GRN No")
    currency_id = fields.Many2one('res.currency', string="Currency", default=lambda self: self.env.company.currency_id) 
    value_date = fields.Date(string="Value Date")

    vendor_invoice_date = fields.Date(string="Vendor Invioce Date")
    vendor_quotation_no = fields.Char(string="Vendor Quotation No", help="Approval Request's reference")
    vendor_invoice_no = fields.Char(string="Vendor Invoice No")
    pay_to_id = fields.Many2one('hr.employee',string="Pay To Employee")
    pay_to_external = fields.Char(string="Pay To External") 
    vendor_bank_info = fields.Char(string="Vendor Bank Info") 

    staff_location_id = fields.Many2one('staff.location',string="Doc Location",tracking=True)
    available_journal_ids = fields.Many2many('account.journal', string="Available Journals", compute="_compute_available_journal_ids")
    journal_id = fields.Many2one('account.journal',string="Expense Journal",
                                domain="[('id', 'in', available_journal_ids)]", tracking=True)
    payment_request_line_ids = fields.One2many(comodel_name="payment.request.lines", inverse_name="payment_request_id", string="Payment Request Lines")
    company_id = fields.Many2one('res.company', related="request_id.company_id", string="Company")
    category_id = fields.Many2one('approval.category', string="Category", required=True)

    # approver fields
    approver_ids = fields.One2many(comodel_name='approval.payment.request.approver', inverse_name='approval_payment_request_id', string="Approvers", check_company=True,
                   compute='_compute_approver_ids', store=True, readonly=False)
    request_owner_id = fields.Many2one('res.users', string="Request Owner", tracking=True)
    employee_id = fields.Many2one('hr.employee', string="Employee", related="request_owner_id.employee_id")
    department_id = fields.Many2one('hr.department', related="employee_id.department_id", string="Department", store=True)
    partial_payment = fields.Boolean(string="Partial Payment", default=False)
    is_locked = fields.Boolean(string="Is Locked", default=False)

    #search parent department
    parent_department_id = fields.Many2one('hr.department', string="Parent Department", related="department_id.parent_id", store=True)

    @api.onchange('partner_id')
    def _onchange_partner_id_for_bank_info(self):
        if self.partner_id:
            self.vendor_bank_info = self.partner_id.vendor_bank_info

    @api.model
    def _normalize_invoice(self, invoice):
        """Normalize vendor invoice: remove spaces, special chars, lowercase"""
        if not invoice:
            return ''
        invoice = re.sub(r'\s+', '', invoice)         # remove spaces/tabs
        invoice = invoice.lower()                     # lowercase
        invoice = re.sub(r'[-_/\.]', '', invoice)    # remove - _ / .
        return invoice

    @api.model
    def _split_invoices(self, invoice_str):
        """Split comma-separated invoices"""
        if not invoice_str:
            return []
        return [x.strip() for x in invoice_str.split(',') if x.strip()]

    @api.constrains('vendor_invoice_no', 'request_status', 'partner_id')
    def _check_duplicate_invoice(self):
        for rec in self:
            if rec.request_status in ['new', 'cancel', 'refused']:
                continue
                # Split and normalize current record invoices
            invoices = rec._split_invoices(rec.vendor_invoice_no)
            normalized_list = [rec._normalize_invoice(inv) for inv in invoices]
            normalized_list = list(filter(None, normalized_list))
            if not normalized_list:
                continue

            # Search for other Payment Requests (exclude canceled/refused)
            other_records = self.search([
                ('id', '!=', rec.id),
                ('partner_id', '=', rec.partner_id.id),
                ('request_status', 'not in', ['new', 'cancel', 'refused']),
                ('vendor_invoice_no', '!=', False),
            ])

            for other in other_records:
                other_invoices = rec._split_invoices(other.vendor_invoice_no)
                other_normalized = [rec._normalize_invoice(inv) for inv in other_invoices]
                
                # Check intersection
                if set(normalized_list) & set(other_normalized):
                    raise ValidationError(
                        "Vendor Invoice Number already exists in another Payment Request."
                    )

    def _get_grouped_payment_lines(self):
        self.ensure_one()
        lines = self.payment_request_line_ids
        grouped = {}

        for line in lines:
            key = (
                line.description,
                line.brand_id.id,
                tuple(sorted(line.analytic_distribution.items())) if line.analytic_distribution else (),
                line.fmis_job_no,
                str(line.job_date),
                line.vehicle_no,
                line.bl_no,
                line.product_uom_id.id,
                line.price_unit,
                tuple(sorted(line.tax_ids.ids)),
            )

            if key not in grouped:
                analytic_names = []
                if line.analytic_distribution:
                    for account_id_str in line.analytic_distribution.keys():
                        account_ids = str(account_id_str).split(",")
                        for account_id in account_ids:
                            account_id_clean = account_id.strip()
                            if account_id_clean.isdigit():
                                account = self.env['account.analytic.account'].browse(int(account_id_clean))
                                if account.exists() and account.name:
                                    analytic_names.append(account.name)

                grouped[key] = {
                    'description': line.description,
                    'brand_name': line.brand_id.name,
                    'analytic_distribution': ', '.join(analytic_names) if analytic_names else '',
                    'fmis_job_no': line.fmis_job_no,
                    'job_date': line.job_date,
                    'vehicle_no': line.vehicle_no,
                    'bl_no': line.bl_no,
                    'uom_name': line.product_uom_id.name,
                    'unit_price': line.price_unit,
                    'tax_names': [tax.name for tax in line.tax_ids],
                    'quantity': 0,
                    'base_amount': 0,
                    'tax_amount': 0,
                    'total_amount': 0,
                    'total_included_amount_currency': 0.0,
                    'total_amount_currency': 0.0,
                }
            grouped[key]['quantity'] += line.quantity
            grouped[key]['base_amount'] += line.price_unit * line.quantity
            grouped[key]['tax_amount'] += line.tax_amount
            grouped[key]['total_included_amount_currency'] += line.total_included_amount_currency
            grouped[key]['total_amount_currency'] += line.total_amount_currency
        return list(grouped.values())
    
    def action_lock(self):
        self.ensure_one()
        self.is_locked = True

    def action_unlock(self):
        self.ensure_one()
        self.is_locked = False

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
    
    has_access_to_request = fields.Boolean(string="Has Access To Request", compute="_compute_has_access_to_request")
    change_request_owner = fields.Boolean(string='Can Change Request Owner', compute='_compute_has_access_to_request')
    minimal_approver =  fields.Integer(string="Minimal Approvers", default=1)
    minimal_checker =  fields.Integer(string="Minimal Checkers", compute="_compute_minimal_checker")

    # === Account fields === #
    move_id = fields.Many2one('account.move',string="Vendor Bill", copy=False)
    payment_state = fields.Selection(
        selection=lambda self: self.env["account.move"]._fields["payment_state"]._description_selection(self.env),
        string="Payment Status",
        compute='_compute_from_account_move_ids', store=True, readonly=True,
        copy=False,
        tracking=True,
    )
    bill_state = fields.Selection(
        selection=lambda self: self.env["account.move"]._fields["state"]._description_selection(self.env),
        string="Bill State",
        compute='_compute_from_bill_state', store=True, readonly=True,
        copy=False,
        tracking=True,
    )

    payment_type_id = fields.Many2one('account.payment.type', string="Type", tracking=True) 
    payment_ids = fields.One2many('account.payment', 'approval_payment_request_id', string="Payment")
    reconcile_entry_id = fields.Many2one('account.move', string="Journal Entry", copy=False)

    # === Amount fields === #
    total_amount = fields.Monetary(
        string="Total",
        currency_field='currency_id',
        compute='_compute_total_amount', store=True, readonly=True,
        tracking=True,
    )
    untaxed_amount = fields.Monetary(
        string="Untaxed Amount",
        currency_field='currency_id',
        compute='_compute_total_amount', store=True, readonly=True,
    )
    total_tax_amount = fields.Monetary(
        string="Taxes",
        currency_field='currency_id',
        compute='_compute_total_amount', store=True, readonly=True,
    )
    amount_residual = fields.Monetary(
        string="Amount Due",
        currency_field='currency_id',
        compute='_compute_from_account_move_ids', store=True, readonly=True,
    )
    currency_id = fields.Many2one(
        comodel_name='res.currency',
        string="Currency",
        compute='_compute_currency_id', store=True, readonly=False,
    )

    amount= fields.Float(string="Total Amount", compute="_compute_total_amount", store=True)
    amount_in_words = fields.Char(
        string="Amount In Words",
        compute="_compute_amount_in_words",
    )
    description = fields.Text(string="Approval Payment Description")
    narration = fields.Text(string="Approval Payment Note", default="Please provide detailed information for above each item to enable the payment to be made properly.")
    show_is_cash_advance = fields.Boolean(string="Show Is Cash Advance",default=True,compute="_compute_show_is_cash_advance")  
    is_cash_advance = fields.Boolean(string="Is Cash Advance", default=False, tracking=True)

    available_cash_advance_ids = fields.Many2many('cash.advance.form',compute="_compute_available_cash_advance_ids")
    cash_advance_ids = fields.Many2many(
        'cash.advance.form', 
        string="Cash Advance No",
        tracking=True,
    )
    cash_advance_amount = fields.Float(string="Cash Advance Amount", compute="_compute_cash_advance_amount")
    sub_total = fields.Float(string="Sub Total", compute="_compute_sub_total")
    clear_cash_advance = fields.Boolean(string="Clear Cash Advance", compute="_compute_enable_payment")
    enable_cash_advance = fields.Boolean(string="Enable Cash Advance", compute="_compute_enable_payment")
    enable_direct_payment = fields.Boolean(string="Enable Direct Payment", compute="_compute_enable_payment")
    reimburse_amount = fields.Float(string="Reimburse Amount", compute="_compute_reimburse_amount", help="Payment amount of the bill)")
    is_purchase = fields.Boolean(string="Is Purchase", default=False)
    reason = fields.Html(string="Particular Description") 
    cash_advance_requested = fields.Boolean(string="Cash Advance Requested?")
    enable_cash_advance_approve = fields.Boolean(string="Enable Clear CA Approve?")
    location = fields.Char(string="Location")
    config_id = fields.Many2one('approval.process.config', string="Config", compute="_compute_approval_config", store=True)
    need_approval = fields.Boolean(related="config_id.need_approval", string="Need Approval", store=True)
    write_off_ids = fields.One2many('account.move', 'payment_request_id', string="Write Off")
    clearance_date = fields.Date(string="Clearance Date", copy=False)

    is_payment_request_cancel = fields.Boolean(string="Payment Request Cancel", tracking=True, copy=False)
    is_request_cancel = fields.Boolean(string="Purchase Request Cancel", tracking=True, copy=False)

    # for purchase_request auto cancel
    bill_ids = fields.One2many('account.move', 'approval_payment_request_id', string="Bills")
    apply_credit_note = fields.Boolean(string="Vendor Credit Note", default=False)

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

    @api.depends('request_id')
    def _compute_show_is_cash_advance(self):
        for rec in self:
            approval_expense = self.env['approval.expense'].search([('request_id','=',rec.request_id.id), ('request_status', '=', 'approved')], limit=1) if rec.request_id else False
            if approval_expense and approval_expense.is_cash_advance:
                rec.show_is_cash_advance = False
            else:
                rec.show_is_cash_advance = True

    @api.depends('total_amount', 'currency_id')
    def _compute_amount_in_words(self):
        for order in self:
            amount_in_words = order.currency_id.amount_to_text(order.total_amount).replace(',', '')
            order.amount_in_words = amount_in_words + " Only" if amount_in_words else ""

    #generate sequence code
    @api.model_create_multi
    def create(self, vals):              
        for val in vals:
            sequence = self.env['ir.sequence'].next_by_code('approval.payment.request.sequence')
            val['name'] = "{}".format(str(sequence))
            if not 'request_owner_id' in val:
                val['request_owner_id'] = self.env.uid
        return super(ApprovalPaymentRequest, self).create(vals)
    
    def unlink(self):
        if self.filtered(lambda a: a.request_status == 'approved'): 
            raise UserError(_("You can't delete in Approved State!"))
        return super().unlink()

    # @api.depends('request_owner_id')
    # def _compute_employee_id(self):
    #     for request in self:
    #         request.employee_id = request.request_owner_id.employee_id

    # Amount compute #
    @api.depends('payment_request_line_ids.total_amount', 'payment_request_line_ids.tax_amount')
    def _compute_total_amount(self):
        for rec in self:
            rec.untaxed_amount = sum(rec.payment_request_line_ids.mapped('total_amount'))
            rec.total_tax_amount = sum(rec.payment_request_line_ids.mapped('tax_amount'))
            rec.total_amount = rec.untaxed_amount + rec.total_tax_amount
            rec.amount = rec.total_amount
        
    @api.depends('staff_location_id')
    def _compute_available_journal_ids(self):
        for rec in self:
            if rec.staff_location_id:
                rec.available_journal_ids = rec.staff_location_id.expense_journal_ids.ids
            else:
                rec.available_journal_ids = self.env['account.journal'].search([])

    # compute approver list based on approval type
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
                        'approval_payment_request_id': self.id or self.ids[0],
                    }))

            rec.sudo().write({'approver_ids': approver_id_vals})

    @api.depends('move_id.payment_state', 'move_id.amount_residual')
    def _compute_from_account_move_ids(self):
        for rec in self:
            # Only one move is created when the expenses are paid by the employee
            if rec.move_id:
                rec.amount_residual = sum(rec.move_id.mapped('amount_residual'))
                rec.payment_state = rec.move_id[:1].payment_state
            else:
                rec.amount_residual = 0.0
                rec.payment_state = 'not_paid'

    @api.depends('request_status', 'move_id.state')
    def _compute_from_bill_state(self):
        for sheet in self:
            # Only one move is created when the expenses are paid by the employee
            if sheet.move_id:
                sheet.bill_state = sheet.move_id[:1].state
            else:
                sheet.bill_state = '' 

    def _cancel_activities(self):
        approval_activity = self.env.ref('approval_extends.mail_activity_data_approval_payment_request_kmtl')
        activities = self.activity_ids.filtered(lambda a: a.activity_type_id == approval_activity)
        activities.unlink()

    @api.depends('approver_ids.status', 'approver_ids.required')
    def _compute_request_status(self):
        for request in self:
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
            request.request_status = status

        self.filtered_domain([('request_status', 'in', ['approved', 'refused', 'cancel'])])._cancel_activities()

    @api.depends_context('uid')
    @api.depends('approver_ids.status')
    def _compute_user_status(self):
        for approval in self:
            approvers = approval.approver_ids.filtered(
                lambda approver: self.env.user in approver.user_ids
            )
            approval.user_status = approvers[:1].status if approvers else False

    @api.depends('request_owner_id')
    @api.depends_context('uid')
    def _compute_has_access_to_request(self):
        is_approval_user = self.env.user.has_group('approvals.group_approval_user')
        self.change_request_owner = is_approval_user
        for request in self:
            request.has_access_to_request = request.request_owner_id == self.env.user and is_approval_user 

    @api.depends('approver_ids')
    def _compute_minimal_checker(self):
        for rec in self: 
            rec.minimal_checker = 0
            if rec.category_id.approval_type == 'payment_request':   
                rec.minimal_checker = len(rec.approver_ids[:-1]) if rec.approver_ids else 0

    @api.depends('is_cash_advance')
    def _compute_available_cash_advance_ids(self):
        for rec in self:
            cash_advance_ids = False
            if rec.request_id.category_id.approval_type == 'purchase':
                request_ids = self.request_id.product_line_ids.mapped('purchase_request_line_id').mapped('approval_request_id').ids
                cash_advance_ids = self.env['cash.advance.form'].search([('request_id', 'in', request_ids), ('request_status', '=', 'approved'),('is_clear','!=', True),('is_reimburse','!=', True)])
                cash_advance_ids = cash_advance_ids.ids
            else:
                cash_advance_ids = self.env['cash.advance.form'].search([('request_id', '=', rec.request_id.id), ('request_status', '=', 'approved'),('is_clear','!=', True),('is_reimburse','!=', True)]).ids
            rec.available_cash_advance_ids = cash_advance_ids

    @api.depends('cash_advance_ids')
    def _compute_cash_advance_amount(self):
        for rec in self:
            total_amount = 0.0
            if rec.cash_advance_ids:
                total_amount = sum(rec.cash_advance_ids.mapped('total_amount'))
            rec.cash_advance_amount = total_amount or False
    
    @api.depends('payment_ids')
    def _compute_reimburse_amount(self):
        for rec in self:
            if rec.payment_ids and rec.payment_ids.filtered(lambda x: x.state == 'posted'):
                rec.reimburse_amount = sum(rec.payment_ids.filtered(lambda x: x.state == 'posted' and x.payment_type == 'outbound').mapped('amount')) * (-1) + \
                                        sum(rec.payment_ids.filtered(lambda x: x.state == 'posted' and x.payment_type == 'inbound').mapped('amount'))
            else:
                rec.reimburse_amount = 0

    @api.depends('amount','cash_advance_amount' , 'reimburse_amount')
    def _compute_sub_total(self):
        for rec in self:
            total = write_off_amt = diff_amount = 0.0
            if rec.amount:
                diff_amount = sum(rec.payment_ids.filtered(lambda x: x.state == 'posted').mapped('diff_amount'))
                if self.cash_advance_ids:
                    reconcile_account_id = self.cash_advance_ids[0].product_id.property_account_expense_id.id
                    lines = rec.write_off_ids.mapped('line_ids').filtered(
                        lambda l: l.account_id.id == reconcile_account_id and l.parent_state == 'posted'
                    )
                    if rec.currency_id == self.env.company.currency_id:
                        write_off_amt = sum(lines.mapped('balance'))
                    else:
                        write_off_amt = sum(lines.mapped('amount_currency'))
                        
                total = (rec.amount + rec.reimburse_amount) - (rec.cash_advance_amount + diff_amount) - write_off_amt
            rec.sub_total = total 

    """if vendor_bill is approved
        : enable_direct payment: 
        : if no cash_advance, able to register vendor_bill until the remaining amount become 0

        : clear_cash_advance
        : if vendor_bill is not fully pay, able to reconcile with cash_advance
    """
    @api.depends('is_cash_advance', 'clear_cash_advance', 'request_status', 'bill_state', 'payment_state')
    def _compute_enable_payment(self):    
        for rec in self:
            rec.clear_cash_advance = True if rec.is_cash_advance and rec.payment_state in ('partial', 'in_payment', 'paid') else False            
            if rec.request_status in ('approved') and rec.bill_state and rec.bill_state in ('posted') and rec.payment_state not in ('in_payment', 'paid'):
                if not rec.is_cash_advance:
                    rec.enable_cash_advance = False
                    if not rec.clear_cash_advance:                        
                        rec.enable_direct_payment = True
                    else:
                        rec.enable_direct_payment = False
                else:                
                    if not rec.clear_cash_advance:
                        rec.enable_cash_advance = True
                        rec.enable_direct_payment = False
                    else:
                        rec.enable_cash_advance = False
                        rec.enable_direct_payment = rec.sub_total != 0
            else:
                rec.enable_cash_advance = False
                if rec.bill_state and rec.bill_state in ('posted') and rec.sub_total < 0 and rec.clear_cash_advance:
                    rec.enable_direct_payment = True
                else:
                    rec.enable_direct_payment = False
            if rec.clear_cash_advance:
                rec.cash_advance_ids.write({'is_clear': True})

    #Purchase Order Lines -> Approval Payment request lines#
    @api.onchange('purchase_order_id')
    def onchange_purchase_order_id(self):
        if self.purchase_order_id:
            self.partner_id = self.purchase_order_id.partner_id.id
            request_line_ids = [Command.clear()]
            purchase_order_lines = self.purchase_order_id.order_line
            for order_line in purchase_order_lines:
                request_line_ids.append(Command.create({
                        'product_id': order_line.product_id.id,
                        'description': order_line.name,
                        'brand_id': order_line.brand_id.id,
                        # 'analytic_distribution': order_line.analytic_distribution,
                        'vehicle_no': order_line.vehicle_no,
                        'bl_no': order_line.bl_no,
                        'reference_key': order_line.reference_key,
                        'price_unit': order_line.price_unit,
                        'product_uom_id': order_line.product_uom.id,
                        'quantity': order_line.product_qty,
                        'tax_ids': order_line.taxes_id.ids,
                        'purchase_line_id': order_line.id,
                        'account_id': order_line.product_id.property_account_expense_id.id or order_line.product_id.categ_id.property_account_expense_categ_id.id or False,
                    }))
            self.write({'payment_request_line_ids': request_line_ids})

    def _get_user_approval_activities(self, user):
        domain = [
            ('res_model', '=', 'approval.payment.request'),
            ('res_id', 'in', self.ids),
            ('activity_type_id', '=', self.env.ref('approval_extends.mail_activity_data_approval_payment_request_kmtl').id),
            ('user_id', '=', user.id)
        ]
        activities = self.env['mail.activity'].search(domain)
        return activities
    
    def _ensure_can_approve(self):
        if any(approval.user_status == 'waiting' for approval in self):
            raise ValidationError(_('You cannot approve before the previous approver.'))
        
    def _update_next_approvers(self, new_status, approver, only_next_approver, cancel_activities=False):
        approvers_updated = self.env['approval.payment.request.approver']
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

    def _update_next_checkers(self, new_status, checker, only_next_checker, cancel_activities=False):
        checkers_updated = self.env['approval.payment.request.approver']
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

    def _get_purchase_journal(self):
        journal = self.env['account.journal'].search([('type', '=', 'purchase')], limit=1)   
        return journal
    
    #Payment Request Approved -> Vendor Bill
    def _prepare_account_move_vals(self):
        """prepare dictionary value to create vendor bill once payment request form is approved"""
        l_vals = [] 
        purchase_journal = self._get_purchase_journal()
        if not purchase_journal: 
            UserError(_("Please define vendor bills journal", self.journal_id.name))      
        for line in self.payment_request_line_ids: 
            l_vals.append([0,0,{
                        'product_id':line.product_id.id,
                        'name':line.description,
                        'account_id':line.account_id.id,
                        'quantity': line.quantity,
                        'product_uom_id':line.product_uom_id.id,
                        'price_unit': line.price_unit,
                        'vehicle_no': line.vehicle_no,
                        'fmis_job_no': line.fmis_job_no, 
                        'job_date': line.job_date, 
                        'bl_no': line.bl_no,
                        'brand_id': line.brand_id.id,
                        # 'analytic_distribution': line.analytic_distribution,
                        'tax_ids': line.tax_ids.ids,
                        'purchase_line_id': line.purchase_line_id.id,
                        'reference_key': line.reference_key
                        }])
        partner = self.partner_id or self.request_owner_id.partner_id
        vals = {'partner_id': partner.id,
                'date': self.date,
                'invoice_date': self.date,
                'journal_id': purchase_journal.id,
                'company_id': self.company_id.id,
                'currency_id': self.currency_id.id,
                'state': 'draft',
                'move_type': 'in_refund' if self.apply_credit_note else 'in_invoice',
                'invoice_line_ids': l_vals,
                'approval_payment_request_id': self.id,
                'account_payment_type_id': self.payment_type_id.id,
                'staff_location_id': self.staff_location_id.id,
                'date': date.today(),
                'request_id': self.request_id.id,
                'purchase_order_no': self.purchase_order_id.name,
                'approval_payment_request_date': self.date,
                'delivery_date': self.delivery_date,
                'receive_date': self.receive_date,
                'value_date': self.value_date,
                'pay_to_id': self.pay_to_id.id,
                'pay_to_external': self.pay_to_external,
                'grn_no': self.grn_no,
                'vendor_bank_info': self.vendor_bank_info,
                'vendor_quotation_no': self.vendor_quotation_no,
                'vendor_invoice_no': self.vendor_invoice_no,
                'vendor_invoice_date': self.vendor_invoice_date,
                'narration': self.description,
                'reason': self.reason,
                'location': self.location,
                'cash_advance_id': self.cash_advance_ids[0].id if self.cash_advance_ids else False
                } 
        return vals
    
    def action_confirm(self):
        self.ensure_one()
        
        posted_payments = self.env['account.payment'].search(['&',('cash_advance_id','in',self.cash_advance_ids.ids),('state','=','posted')])
        if self.cash_advance_ids and not posted_payments:
            raise UserError(_("Can't submit: some related payments are not approved."))
        
        status = None
        if self.category_id.approval_type == 'payment_request':
            if self.config_id.need_approval:
                if self.journal_id and not self.journal_id.default_account_id and self.payment_request_line_ids:
                    raise UserError(_("Please define COA for expense journal!"))
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
                # self.sudo()._get_user_approval_activities(user=self.env.user).action_feedback()
            else:
                self.action_approve()

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
    
    def action_view_journal(self):
        return {
            'type': 'ir.actions.act_window', 
            'name': _('Journal Entry'),
            'res_model': 'account.move',
            'view_mode': 'tree,form',
            'domain': [('approval_payment_request_id', 'in', self.ids), ('move_type', '=', 'entry'), ('auto_reconciled', '=', True)], 
        }

    def action_view_write_off(self):
        return {
            'type': 'ir.actions.act_window', 
            'name': _('Write-Off Entery'),
            'res_model': 'account.move',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.write_off_ids.ids)], 
        }

    def _get_reconcile_journal(self):
        journal = self.env['account.journal'].search([('type', '=', 'general')], limit=1)   
        return journal  
    
    #cash advance auto reconcile journal
    def _prepare_reconcile_move_vals(self):
        """prepare dictionary value to create move entry once payment request form is approved
        debit line will use payable account from partner of vendor bill
        credit line will use expense account(as cash advance account) from product 
        """
        l_vals = []  
        if not self._get_reconcile_journal():  
            raise UserError(_("Miscellaneous Journal not found!")) 
        vehicle_no = ', '.join(sorted(set(line.vehicle_no for line in self.payment_request_line_ids if line.vehicle_no)))  
        fmis_job_no = ', '.join(sorted(set(line.fmis_job_no for line in self.payment_request_line_ids if line.fmis_job_no)))  
        bl_no = ', '.join(sorted(set(line.bl_no for line in self.payment_request_line_ids if line.bl_no))) 
        reference_key = ', '.join(sorted(set(line.reference_key for line in self.payment_request_line_ids if line.reference_key)))     
        brand_name = ', '.join(sorted(set(line.brand_id.name for line in self.payment_request_line_ids if line.brand_id))) 
        liquidity_amount_currency = self.cash_advance_amount if self.sub_total > 0 else self.amount 
        liquidity_balance = self.currency_id._convert(
                liquidity_amount_currency,
                self.company_id.currency_id,
                self.company_id,
                self.date,
            )
        counterpart_amount_currency = -liquidity_amount_currency
        counterpart_balance = -liquidity_balance
        currency_id = self.currency_id.id
        l_vals = [
            # Debit Line(Payable)
            {
                'name': self.partner_id.name,
                'date_maturity': self.date,
                'amount_currency': liquidity_amount_currency,
                'currency_id': currency_id,
                'debit': liquidity_balance if liquidity_balance > 0.0 else 0.0,
                'credit': -liquidity_balance if liquidity_balance < 0.0 else 0.0,
                'partner_id': self.partner_id.id,
                'account_id': self.partner_id.property_account_payable_id.id,
                'vehicle_no': vehicle_no,
                'fmis_job_no': fmis_job_no,
                'job_date': self.payment_request_line_ids[0].job_date if self.payment_request_line_ids else False,
                'bl_no': bl_no,
                'reference_key': reference_key,
                'brand_name': brand_name
            },
            # Credit Line(Cash Advance).
            {
                'name': self.partner_id.name,
                'date_maturity': self.date,
                'amount_currency': counterpart_amount_currency,
                'currency_id': currency_id,
                'debit': counterpart_balance if counterpart_balance > 0.0 else 0.0,
                'credit': -counterpart_balance if counterpart_balance < 0.0 else 0.0,
                'partner_id': self.partner_id.id,
                'account_id': self.cash_advance_ids[0].product_id.property_account_expense_id.id,
                'vehicle_no': vehicle_no,
                'fmis_job_no': fmis_job_no,
                'job_date': self.payment_request_line_ids[0].job_date if self.payment_request_line_ids else False,
                'bl_no': bl_no,
                'reference_key': reference_key,
                'brand_name': brand_name
            },
        ]
        vals = {'partner_id': self.partner_id.id,
                'date': self.date,
                'vendor_quotation_no': self.vendor_quotation_no,
                'vendor_invoice_no': self.vendor_invoice_no,
                'invoice_date': self.date,
                'journal_id': self._get_reconcile_journal().id,
                'company_id': self.company_id.id,
                'currency_id': self.currency_id.id,
                'state': 'draft',
                'move_type': 'entry',
                'line_ids': [Command.create(line) for line in l_vals],
                'approval_payment_request_id': self.id,
                'account_payment_type_id': self.payment_type_id.id,
                'staff_location_id': self.staff_location_id.id,
                'request_id': self.request_id.id,
                'purchase_order_no': self.purchase_order_id.name,
                'reason': self.reason,
                'auto_reconciled': True,
                'pay_to_id': self.pay_to_id.id,
                'pay_to_external': self.pay_to_external, 
                'vehicle_no': vehicle_no,
                'location': self.location,
                'job_date': self.payment_request_line_ids[0].job_date if self.payment_request_line_ids else False,
                'cash_advance_id': self.cash_advance_ids[0].id if self.cash_advance_ids else False,
                'delivery_date': self.delivery_date,
                } 
        return vals

    def action_approve(self, approver=None):
        self._ensure_can_approve()

        if not isinstance(approver, models.BaseModel):
            approver = self.mapped('approver_ids').filtered(
                    lambda approver: self.env.user in approver.user_ids
                )       
        bill_vals = self._prepare_account_move_vals()
        bill = self.env['account.move'].sudo().create(bill_vals)
        self.move_id = bill.id 
        payable_line  = bill.line_ids.filtered(lambda x: x.account_id.account_type == 'liability_payable')
        payable_line.sudo().write({'name': self.partner_id.id,
                                    'fmis_job_no': ', '.join(sorted(set(self.payment_request_line_ids.filtered(lambda x: x.fmis_job_no).mapped('fmis_job_no')))),
                                    'job_date': self.payment_request_line_ids[0].job_date if self.payment_request_line_ids else False,
                                    'vehicle_no': ', '.join(sorted(set(self.payment_request_line_ids.filtered(lambda x: x.vehicle_no).mapped('vehicle_no')))),
                                    'bl_no': ', '.join(sorted(set(self.payment_request_line_ids.filtered(lambda x: x.bl_no).mapped('bl_no')))),
                                    'reference_key': ', '.join(sorted(set(self.payment_request_line_ids.filtered(lambda x: x.reference_key).mapped('reference_key')))),
                                    'brand_name': ', '.join(sorted(set(self.payment_request_line_ids.filtered(lambda x: x.brand_id).mapped('brand_id').mapped('name')))),
                                    })  
        if self.purchase_order_id:
            self.purchase_order_id.sudo().write({'invoice_ids': [(4, bill.id)], })
        self.request_status = 'approved'
        approver.write({'status': 'approved'})
        self.sudo()._update_next_approvers('pending', approver, only_next_approver=True)
        self.sudo()._get_user_approval_activities(user=self.env.user).action_feedback()

    def action_draft(self):
        if self.request_id and self.request_id.request_status == 'cancel':
            raise ValidationError(_("You can't set to draft in Purchase Request Cancel state!"))
        self.mapped('approver_ids').write({'status': 'new'})
        self.mapped('bill_ids').write({'is_payment_request_cancel': False})
        self.write({'request_status': 'new',
                    'is_payment_request_cancel': False,
                    })
    def _action_cancel(self):
        self.sudo()._get_user_approval_activities(user=self.env.user).unlink()
        self.bill_ids.filtered(lambda x: x.state not in ['cancel']).button_cancel()
        self.reconcile_entry_id.filtered(lambda x: x.state not in ['cancel']).button_cancel()
        self.mapped('approver_ids').write({'status': 'cancel'})
        self.request_status = 'cancel'

    def action_cancel(self):
        if any(rec.request_status == 'approved' and any(bill.request_status in ['checked', 'approved'] for bill in rec.bill_ids) for rec in self):
            raise ValidationError(_('You cannot cancel in vendor bill checking and approved state!'))
        
        # check if purchase_request have cash advance or expense
        request_ids = self.mapped('request_id').filtered(
            lambda r: not r.cash_advance_ids and not r.expense_ids
        )
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
                'context': {'default_approval_payment_request_ids': self.ids, 'default_request_ids': unused_request_ids.ids}            
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

    def action_view_bill(self):
        return {
            'type': 'ir.actions.act_window', 
            'name': _('Vendor Bills'),
            'res_model': 'account.move',
            'view_mode': 'tree,form',
            'domain': [('approval_payment_request_id', 'in', self.ids), ('move_type', '=', 'in_invoice')],
        }

    def action_view_credit_note(self):
        return {
            'type': 'ir.actions.act_window', 
            'name': _('Vendor Credit Notes'),
            'res_model': 'account.move',
            'view_mode': 'tree,form',
            'domain': [('approval_payment_request_id', 'in', self.ids), ('move_type', 'in', ['in_refund'])], 
        }

    def _get_report_base_filename(self):
        self.ensure_one()
        return 'Payment Request-%s' % (self.name)
    
    def _prepare_account_payment_vals(self):
        payment_method = self.env['account.payment.method'].search([('payment_type', '=', 'inbound'),('name', '=', 'Manual')])[:1]
        journal_id = False
        if self.payment_type_id.journal_ids:
            journal_id = self.payment_type_id.journal_ids.ids[0]
        payment_type = 'inbound'
        partner_type = 'supplier'
        amount = self.sub_total * -1
        vals = {'partner_id': self.partner_id.id or self.request_owner_id.partner_id.id,
                'cash_advance_id': self.cash_advance_ids[0].id if self.cash_advance_ids else False,
                'date': self.date,
                'amount': amount,
                'currency_id': self.currency_id.id,
                'payment_type': payment_type,
                'partner_type': partner_type,
                'journal_id': journal_id,
                'payment_method_id': payment_method.id,
                'company_id': self.company_id.id,
                'ref': self.description,
                'approval_payment_request_id': self.id,
                'state': 'draft',
                'request_id': self.request_id.id, 
                'purchase_order_no': self.purchase_order_id.name,
                'pay_to_id': self.pay_to_id.id, 
                'pay_to_external': self.pay_to_external, 
                'vendor_quotation_no': self.vendor_quotation_no,  
                'vendor_invoice_no': self.vendor_invoice_no,  
                'vendor_invoice_date': self.vendor_invoice_date,  
                'staff_location_id': self.staff_location_id.id, 
                'account_payment_type_id': self.payment_type_id.id,
                'reason': self.reason,
                'delivery_date': self.delivery_date,
                'destination_account_id': self.cash_advance_ids[0].product_id.property_account_expense_id.id,
                } 
        return vals
    
    def action_create_vendor_payment(self):
        payment_vals = self._prepare_account_payment_vals()
        payment = self.env['account.payment'].sudo().create(payment_vals)
        payment.sudo().write({'approval_payment_request_id': self.id})
        self.sudo().write({'enable_direct_payment': False})

    def action_register_partial_payment(self):
        self.ensure_one()
        return {
            'name': "Partial Payment",
            'type': 'ir.actions.act_window',
            'view_mode': 'form',            
            'res_model': 'partial.payment.wizard',  
            'views': [(False, 'form')],
            'view_id' : 'approval_partial_payment_wizard',       
            'target': 'new',           
            'context': {'default_payment_request_id': self.id}            
        }

    def action_register_payment(self):
        return self.action_create_vendor_payment()

    # when "Clear Cash Advance Request" button is clicked, it will ask for approve
    # def action_clear_ca_request(self):
    #     self.sudo().write({'cash_advance_requested': True})  
    #     approver = self.approver_ids.filtered(lambda x: x.status == 'approved')
    #     approver._create_activity()
    
    def action_clear_cash_advance(self):
        # for payment in self.cash_advance_ids.mapped('payment_id').filtered(lambda x: x.state == 'posted'):
        #     if self.move_id.is_invoice():
        #         move_lines = payment.line_ids.filtered(lambda line: line.account_type in ('asset_receivable', 'liability_payable') and not line.reconciled)
        #         for line in move_lines:
        #             self.move_id.js_assign_outstanding_line(line.id)
        # self.sudo().write({'clear_cash_advance': True})  
        posted_payments = self.env['account.payment'].search(['&',('cash_advance_id','in',self.cash_advance_ids.ids),('state','=','posted')])
        if self.cash_advance_ids and not posted_payments:
            raise UserError(_("Can't clear cash advance: some related payments are not approved."))

        # vendor bill will reconcile with the journal(which is created when bill is posted)
        if self.move_id.is_invoice():
            move_lines = self.reconcile_entry_id.line_ids.filtered(lambda line: line.account_type in ('asset_current', 'liability_payable') and not line.reconciled)
            for line in move_lines:
                self.move_id.js_assign_outstanding_line(line.id)
        self.sudo().write({'clear_cash_advance': True, 
                        'clearance_date': fields.Date.today()})
    
    def action_view_payment(self):
        return {
            'type': 'ir.actions.act_window', 
            'name': _('Payment'),
            'res_model': 'account.payment',
            'view_mode': 'tree,form',
            'domain': [('approval_payment_request_id', 'in', self.ids)],
        }
    
    def action_print_clear_cash_advance(self):
        return self.env.ref('approval_extends.clear_ca_report_from_pr').report_action(self)

    def _get_report_clear_cash_filename(self):
        self.ensure_one()
        return 'CLEAR CASH ADVANCE-%s' % (self.name) 
    
    def action_reconcile(self):
        unreconcile_lines = self.env['account.move.line'].sudo().search([
                            ('partner_id','=', self.partner_id.id),
                            ('display_type', 'not in', ('line_section', 'line_note')), 
                            ('account_id.reconcile', '=', True), 
                            ('parent_state', '=', 'posted'), 
                            ('full_reconcile_id', '=', False),
                            ('approval_request_id','=',self.request_id.id),
                            ('reconciled','=', False),
                            ('account_id','!=',self.cash_advance_ids[:1].product_id.property_account_expense_id.id)
                            ])
        
        wizard = self.env['account.reconcile.wizard'].with_context(
            active_model='account.move.line',
            active_ids=unreconcile_lines.ids,
        ).new({})
        return wizard._action_open_wizard() if (wizard.is_write_off_required or wizard.force_partials) else wizard.reconcile()
    
    def export_data(self, fields_to_export, **kwargs):
        data = super(ApprovalPaymentRequest, self).export_data(fields_to_export, **kwargs)
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

class ApprovalPaymentRequestLines(models.Model):
    _name = 'payment.request.lines'
    _description = 'Approval Payment Request Detail Lines'
    _inherit = ['mail.activity.mixin', 'analytic.mixin']
    _check_company_auto = True

    name = fields.Char(string="Name")
    category_id = fields.Many2one('product.category',string="Payment Request Product Category")
    product_id = fields.Many2one('product.product',string="Payment Request Product")
    description = fields.Char(string="Label")
    account_id = fields.Many2one('account.account', string="Account")
    brand_id = fields.Many2one('purchase.brand', string="Brand Name")

    fmis_job_no = fields.Char(string="FMIS Job No")
    job_date = fields.Date(string="Job Date")
    vehicle_no = fields.Char(string="Vehicle No")
    bl_no = fields.Char(string="BL No")
    reference_key = fields.Char(string="Reference Key")
    product_uom_category_id = fields.Many2one(
        comodel_name='uom.category',
        related='product_id.uom_id.category_id',
    )
    product_uom_id = fields.Many2one('uom.uom', string='UoM',domain="[('category_id', '=', product_uom_category_id)]")

    quantity = fields.Float(string="Quantity", default=1)
    payment_request_id = fields.Many2one('approval.payment.request', ondelete='cascade', index=True, copy=False)
    request_owner_id = fields.Many2one('res.users', related="payment_request_id.request_owner_id", string="Request Owner", store=True)
    department_id = fields.Many2one('hr.department', related="request_owner_id.employee_id.department_id", string="Department", store=True)
    date = fields.Date(related="payment_request_id.date")
    purchase_line_id = fields.Many2one('purchase.order.line', 'Purchase Order Line')

    company_id = fields.Many2one(
        comodel_name='res.company',
        string="Company",
        required=True,
        readonly=True,
        default=lambda self: self.env.company,
    )

    # Amount fields
    tax_ids = fields.Many2many(
        comodel_name='account.tax',
        relation='payment_request_line_tax',
        column1='payment_request_id',
        column2='tax_id',
        string="Taxes",
        compute='_compute_tax_ids', precompute=True, store=True, readonly=False,
        domain="[('type_tax_use', '=', 'purchase')]",
        check_company=True,
        help="Both price-included and price-excluded taxes will behave as price-included taxes for expenses.",
    )
    tax_amount_currency = fields.Monetary(
        string="Tax amount in Currency",
        currency_field='currency_id',
        compute='_compute_tax_amount_currency', precompute=True, store=True,
        help="Tax amount in currency",
    )
    tax_amount = fields.Monetary(
        string="Tax amount",
        currency_field='currency_id',
        compute='_compute_tax_amount', precompute=True, store=True,
        help="Tax amount in company currency",
    )
    total_amount_currency = fields.Monetary(
        string="Total In Currency (Tax incl)",
        currency_field='currency_id',
        compute='_compute_total_amount_currency', precompute=True, store=True, readonly=False
    )
    untaxed_amount_currency = fields.Monetary(
        string="Total Untaxed Amount In Currency",
        currency_field='currency_id',
        compute='_compute_tax_amount_currency', precompute=True, store=True,
    )
    total_amount = fields.Monetary(
        string="Total",
        currency_field='currency_id',
        compute='_compute_total_amount', precompute=True, store=True, readonly=True
    )
    price_unit = fields.Float(string="Unit Price", copy=False, digits='Product Price')
    currency_id = fields.Many2one(
        comodel_name='res.currency',
        string="Currency",
        compute='_compute_currency_id', precompute=True, store=True, readonly=False,
        required=True,
    )

    total_included_amount_currency = fields.Monetary(
        string="Total In Currency (Tax incl)",
        currency_field='currency_id',
        compute='_compute_total_amount_currency', precompute=True, store=True, readonly=False
    )

    @api.depends('product_id', 'company_id')
    def _compute_tax_ids(self):
        for line in self:
            pr = line.with_company(line.company_id)
            # taxes only from the same company
            pr.tax_ids = pr.product_id.supplier_taxes_id.filtered_domain(self.env['account.tax']._check_company_domain(pr.company_id))
    
    @api.depends('quantity', 'price_unit', 'tax_ids')
    def _compute_total_amount_currency(self):
        for line in self:
            # base_lines = [pr._convert_to_tax_base_line_dict(price_unit=pr.price_unit, quantity=pr.quantity)]
            # taxes_totals = self.env['account.tax']._compute_taxes(base_lines)['totals'][pr.currency_id]
            # pr.total_amount_currency = taxes_totals['amount_untaxed'] + taxes_totals['amount_tax']
            if line.tax_ids:
                taxes_res = line.tax_ids.compute_all(
                    line.price_unit,
                    quantity=line.quantity,
                    currency=line.payment_request_id.currency_id
                )
                line.total_amount_currency = taxes_res['total_excluded']
                line.total_included_amount_currency = taxes_res['total_included']
            else:
                line.total_amount_currency = line.quantity * line.price_unit

    @api.depends('payment_request_id')
    def _compute_currency_id(self):
        for line in self:
            line.currency_id = line.payment_request_id.currency_id.id
            
    @api.depends('total_amount', 'total_amount_currency')
    def _compute_price_unit(self):
        """
           The price_unit is the unit price of the product if no product is set and no attachment overrides it.
           Otherwise it is always computed from the total_amount and the quantity else it would break the vendor bill
           when edited after creation.
        """
        for line in self:
            product_id = line.product_id
            if product_id:
                line.price_unit = product_id._price_compute(
                    'standard_price',
                    uom=line.product_uom_id,
                    company=line.company_id,
                )[product_id.id]
            else:
                line.price_unit = 0
                
    @api.depends('date', 'company_id', 'currency_id',
        'total_amount_currency', 'product_id', 'quantity')
    def _compute_total_amount(self):
        for pr in self:
            pr.total_amount = pr.total_amount_currency 
            
    # @api.depends('total_amount_currency', 'tax_ids')
    # def _compute_tax_amount_currency(self):
    #     """
    #          Note: as total_amount_currency can be set directly by the user (for product without cost)
    #          or needs to be computed (for product with cost), `untaxed_amount_currency` can't be computed in the same method as `total_amount_currency`.
    #     """
    #     for pr in self:
    #         base_lines = [pr._convert_to_tax_base_line_dict(price_unit=pr.total_amount_currency)]
    #         taxes_totals = self.env['account.tax']._compute_taxes(base_lines)['totals'][pr.currency_id]
    #         pr.tax_amount_currency = taxes_totals['amount_tax']
    #         pr.untaxed_amount_currency = taxes_totals['amount_untaxed']
    @api.depends('price_unit', 'quantity', 'tax_ids')
    def _compute_tax_amount_currency(self):
        for line in self:
            taxes = line.tax_ids.compute_all(
                line.price_unit,
                quantity=line.quantity,
                currency=line.payment_request_id.currency_id
            )
            line.tax_amount_currency = sum(t['amount'] for t in taxes['taxes'])
            
    @api.depends('total_amount', 'tax_ids')
    def _compute_tax_amount(self):
        for pr in self:            
            pr.tax_amount = pr.tax_amount_currency
            
    def _convert_to_tax_base_line_dict(self, base_line=None, currency=None, price_unit=None, quantity=None):
        self.ensure_one()
        return self.env['account.tax']._convert_to_tax_base_line_dict(
            base_line,
            currency=currency or self.currency_id,
            product=self.product_id,
            taxes=self.tax_ids,
            price_unit=price_unit or self.total_amount,
            quantity=quantity if quantity is not None else 1,
            account=self.account_id,
            analytic_distribution=self.analytic_distribution,
            extra_context={'force_price_include': True},
        )
    
    # remove recomputing price_unit in task:2649         
    # def _inverse_total_amount(self):
    #     """ Allows to set a custom rate on the pr, and avoid the override when it makes no sense """
    #     for pr in self:
    #         pr.total_amount_currency = pr.total_amount
    #         pr.tax_amount = pr.tax_amount_currency
    #         pr.price_unit = pr.total_amount / pr.quantity if pr.quantity else pr.total_amount
 

    @api.onchange('product_id','category_id')
    def onchange_product_id(self):
        for line in self:
            line.account_id = line.product_id.property_account_expense_id or line.product_id.categ_id.property_account_expense_categ_id or False
            line.product_uom_id = line.product_id.uom_id.id or False
            line.price_unit = line.product_id.lst_price
            line.description = line.product_id.display_name

    def _get_report_data(self):
        result = []
        for line in self:
            if line.analytic_distribution:
                for key, percentage in line.analytic_distribution.items():
                    analytic_ids = [int(analytic_id) for analytic_id in key.split(',')]
                    analytic_accounts = self.env['account.analytic.account'].browse(analytic_ids)
                    for analytic_account in analytic_accounts:
                        account_name = analytic_account.name
                        plan_name = analytic_account.plan_id.name

                        if analytic_account.partner_id:
                            account_name = f"{analytic_account.name} - {analytic_account.partner_id.name}"
                        if analytic_account.plan_id.name == 'Job Location':
                            plan_name = 'Job Loc'
                        if analytic_account.plan_id.name == 'Job Department':
                            plan_name = 'Dept'
                        if not analytic_account.plan_id.name == 'Projects':
                            result.append({
                                'plan_name': plan_name,
                                'account_name': account_name
                            })
        return result
    