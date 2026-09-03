from odoo import fields,Command, models, api, _
from odoo.exceptions import UserError, ValidationError
import json
 
class ApprovalRequest(models.Model):
    _inherit = "approval.request"     

    employee_id = fields.Many2one('hr.employee', string="Employee", related="request_owner_id.employee_id")
    department_id = fields.Many2one('hr.department',related="employee_id.department_id", string="Department", store=True)  
    currency_id = fields.Many2one('res.currency', string="Currency", default=lambda self: self.env.company.currency_id)  

    amount = fields.Float(string="Amount", compute="_compute_amount",store=True)
    total_amount = fields.Float(string="Total Amount", compute="_compute_total_amount", store=True)
    manual_amount = fields.Boolean(string="Manual Amount", default=True)
    
    request_status = fields.Selection(selection_add=[
                                    ('new', 'To Submit'),  
                                    ('pending', 'Submitted'),
                                    ('checked', 'Checking'),
                                    ('approved', 'Approved'), 
                                    ('refused', 'Refused'), 
                                    ('cancel', 'Cancel'),
                                    ])
    user_status = fields.Selection(selection_add=[('to_check', 'To Checked'), ('checked', 'Checked')])
    minimal_approver =  fields.Integer(string="Minimal Approvers", default=1)
    minimal_checker =  fields.Integer(string="Minimal Checkers", compute="_compute_minimal_checker")

    cash_advance_count = fields.Integer('Cash Advance Count',compute='_compute_cash_advance_count')
    expense_count = fields.Integer('Expense Count',compute='_compute_expense_count')

    est_delivery_date = fields.Date(string="Est. Delivery Date")
    value_date = fields.Date(string="Value Date")
    pay_to_id = fields.Many2one('hr.employee',string="Pay To Employee")
    pay_to_external = fields.Char(string="Pay To External") 
    staff_location_id = fields.Many2one('staff.location',string="Doc Location")
    payment_type_id = fields.Many2one('account.payment.type',string="Type")
    default_journal_id = fields.Many2one('account.journal',compute="_compute_default_journal_id")
    without_PO = fields.Boolean(string="Without PO", default=False, copy=False)
    purchase_request_no = fields.Many2one('approval.request', string="Purchase Request No.")   
    payment_request_count = fields.Integer('Payment Request Count', compute='_compute_payment_request_count')
    allowed_purchase_req_ids = fields.Many2many('approval.request', compute='_compute_allowed_purchase_req')    
    created_po = fields.Boolean(string="PO Created", compute="_compute_allowed_purchase_req")
    PR_type = fields.Selection([('cash_advance', 'Cash Advance'), ('expense', 'Expense'), ('payment_request', 'Payment without PO'),('Payment with PO', 'Payment with PO')], string="PR Type",required=True, default='cash_advance')

    po_comparison_id = fields.Many2one('po.comparison', string="PO Comparison No.", copy=False)  
    # po_comparison_count = fields.Integer('PO Comparison Count', compute="_compute_po_comparison_count") 
    request_approved_date = fields.Date(string="Request Approved Date",copy=False ,help="Request's final approve date")
    request_checked_date = fields.Date(string="Request Checked Date",copy=False, help="Request's final check date")
    enable_payment_request = fields.Boolean(string="Enable Payment Request", compute="_compute_allowed_purchase_req")
    purchase_order_id = fields.Many2one('purchase.order', string="PO", compute="_compute_allowed_purchase_req") 

    has_payment_request = fields.Boolean(string="Payment Request",compute='_compute_has_payment_request',help="If Payment Request is in cancel state, we can create payment request again.")
    has_cash_advance = fields.Boolean(string="Payment Request",compute='_compute_has_cash_advance',help="If Cash Advance is in cancel state, we can create cash advance again.")
    has_expense = fields.Boolean(string="Payment Request",compute='_compute_has_expense',help="If Expense is in cancel state, we can create expense again.")
    vendor_invoice_no = fields.Char(string="Vendor Invoice No")
    vendor_quotation_date = fields.Date(string="Vendor Quotation Date")
    date = fields.Datetime(string="Date",default=fields.Datetime.now)

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

    # override odoo's original method
    def _compute_purchase_order_count(self):
        for request in self:
            request.purchase_order_count = self.env['purchase.order'].search_count([('rfq_id','=',request.id)]) or 0

    def _compute_has_purchase_order(self):
        for request in self:
            request.has_purchase_order = self.env['purchase.order'].search_count([('rfq_id','=',request.id),('state','!=','cancel')]) or 0

    @api.onchange('partner_id')
    def _get_payment_type(self):
        self.payment_type_id = self.partner_id.type_id

    @api.depends('purchase_order_count')                           
    def _compute_allowed_purchase_req(self): 
        for rec in self:
            rec.purchase_order_id = False   
            if rec.approval_type == 'purchase':
                rec.created_po = rec.purchase_order_count > 0 
                purchase = self.env['purchase.order'].search([('rfq_id','=',rec.id)]).filtered(lambda x: x.state in ('purchase','done'))
                rec.enable_payment_request = True if purchase else False

                rec.purchase_order_id = purchase[0].id if purchase else False
            elif rec.approval_type == 'purchase_req':
                purchase_order_count = self.env['approval.request'].search([('approval_type', '=', 'purchase'), 
                                                                            ('request_status', '=', 'approved'),
                                                                            ('purchase_request_no', '=', rec.id)])
                rec.created_po = len(purchase_order_count) > 0
                rec.enable_payment_request = True if rec.request_status == 'approved' else False
            else:
                rec.created_po = False
                rec.enable_payment_request = False
            purchase_req = self.env['approval.request'].search([('approval_type', '=', 'purchase_req'),
                                                                ('request_status', '=', 'approved')])
            purchase_order = self.env['purchase.order'].search([('purchase_request_no', 'in', purchase_req.ids), ('state', '!=', 'cancel')])            
            rec.allowed_purchase_req_ids = purchase_req.filtered(lambda x: x.id not in purchase_order.mapped('purchase_request_no').ids)
                
    @api.depends('staff_location_id')
    def _compute_default_journal_id(self):
        for rec in self: 
            if rec.staff_location_id:
                available_journal_ids = rec.staff_location_id.expense_journal_ids
                rec.default_journal_id = available_journal_ids[:1].id
            else:
                rec.default_journal_id = False

    @api.depends('approver_ids')
    def _compute_minimal_checker(self): 
        for rec in self: 
            rec.minimal_checker = 0
            if rec.category_id.approval_type == 'purchase_req':   
                rec.minimal_checker = len(rec.approver_ids[:-1]) if rec.approver_ids else 0      

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
            status_lst = request.mapped('approver_ids.status')
            required_approved = all(a.status == 'approved' for a in request.approver_ids.filtered('required'))
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
        
    def action_confirm(self):
        self.ensure_one()
        status = None
        if self.category_id.approval_type == 'purchase_req':
            if len(self.approver_ids) < self.minimal_approver:
                raise UserError(_("You have to add at least %s approvers to confirm your request.", self.minimal_approver))
            if self.requirer_document == 'required' and not self.attachment_number:
                raise UserError(_("You have to attach at least one document."))
            approvers = self.approver_ids
            if self.approver_sequence:
                approvers = approvers.filtered(lambda a: a.status in ['new', 'to_check', 'pending', 'waiting'])
                if approvers:
                    status  = 'pending' if len(approvers) == 1 else 'to_check'
                approvers[1:].sudo().write({'status': 'waiting'})
                approvers = approvers[0] if approvers and approvers[0].status != 'to_check' else self.env['approval.approver']
            else:
                approvers = approvers.filtered(lambda a: a.status == 'new')

            approvers._create_activity()
            approvers.sudo().write({'status': status})
            self.sudo().write({'date_confirmed': fields.Datetime.now()})
            self.sudo()._get_user_approval_activities(user=self.env.user).action_feedback()
        else:
            super().action_confirm()
    
    def action_approve(self):
        if self.po_comparison_id:
            approved_rfq_id = self.po_comparison_id.sudo().request_ids.filtered(lambda request: request.request_status == 'approved')

            if approved_rfq_id:
                raise UserError(_("Another RFQ is already approved!"))
            else: 
                super().action_approve()
                rfq_ids = self.po_comparison_id.sudo().request_ids.filtered(lambda request: request.request_status != 'approved')
                for request in rfq_ids:
                    request.action_refuse()
        else:
            super().action_approve()

        self.sudo().write({'request_approved_date': fields.Datetime.now()})

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
                
        self.cash_advance_ids.action_cancel()
        self.expense_ids.filtered(lambda x: x.request_status != 'cancel').action_cancel()
        self.payment_request_ids.action_cancel()
        return super().action_cancel()
            
    def _ensure_can_check(self):
        if any(approval.approver_sequence and approval.user_status == 'waiting' for approval in self):
            raise ValidationError(_('You cannot check before the previous checker.'))
        
    def _update_next_checkers(self, new_status, checker, only_next_checker, cancel_activities=False):
        checkers_updated = self.env['approval.approver']
        for approval in self.filtered('approver_sequence'):
            current_checker = approval.approver_ids & checker
            approval_type = 'checker' if new_status == 'to_check' else 'approver'
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
        
    def action_check(self, checker=None): 
        self._ensure_can_check()        
        if not isinstance(checker, models.BaseModel):
            checker = self.mapped('approver_ids').filtered(
                lambda checker: checker.user_id == self.env.user
            )
        checker.status = 'checked'
        self.sudo().write({'request_checked_date': fields.Datetime.now()})
        status_lst = self.mapped('approver_ids.status')        
        if status_lst.count('checked') >= (self.minimal_checker):
            self.sudo()._update_next_checkers('pending', checker , only_next_checker=True)
        else:
            self.sudo()._update_next_checkers('to_check', checker, only_next_checker=True)
        self.sudo()._get_user_approval_activities(user=self.env.user).action_feedback()

    @api.depends('category_id', 'request_owner_id', 'amount', 'currency_id') 
    def _compute_approver_ids(self):
        for rec in self:
            if rec.category_id.approval_type == 'purchase_req': 
                approver_id_vals = [Command.clear()]               
                config_ids = rec.category_id.approval_process_config_ids.filtered(lambda x: x.from_amount <= rec.amount \
                        and x.to_amount >= rec.amount and x.currency_id.id == rec.currency_id.id)
                dept_config = config_ids.filtered(lambda x: x.department_ids and rec.department_id.id in x.department_ids.ids)
                not_dept_config = config_ids.filtered(lambda x: not x.department_ids)               
                config = dept_config if dept_config else not_dept_config
                if len(config) > 1:
                    raise ValidationError(_('Duplicate Record Found! Please Check in Approval Config'))
                approver_approvers = rec.employee_id.approver_ids.filtered(lambda a: a.sequence >= config.from_level and a.sequence <= config.to_level).sorted(key=lambda a: a.sequence)
                for approver in approver_approvers:
                    approver_id_vals.append(Command.create({
                        'user_id': approver.approval_employee_id.id,
                        'status': 'new',
                        'required': False,
                        'level': approver.sequence 
                    }))
                rec.write({'approver_ids': approver_id_vals})
            else: 
                super()._compute_approver_ids()
                
    def _prepare_cash_advance_vals(self):
        for rec in self:
            cash_advance = self.env['approval.category'].search([('approval_type', '=', 'cash_advance')], limit=1)

            approval_product_line = rec.product_line_ids[:1]
            vals = {
                'request_owner_id' : rec.request_owner_id.id,
                'category_id': cash_advance.id,
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
                'analytic_distribution' : approval_product_line.analytic_distribution,
                'bl_no': approval_product_line.bl_no,
                'reference_key': approval_product_line.reference_key,
                'brand_id' : approval_product_line.brand_id.id,
                'amount': rec.amount,
                'reason': rec.reason,
                'est_delivery_date': rec.est_delivery_date,
                'location': rec.location,
            }
        return vals
                
    def action_create_cash_advance(self): 
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

    def _compute_cash_advance_count(self):
        for rec in self:
            rec.cash_advance_count = self.env['cash.advance.form'].search_count([('request_id','=',rec.id)]) or 0
    
    def action_view_cash_advance_form(self):
        advance_ids = self.env['cash.advance.form'].search([('request_id','=',self.id)])
        result = {
                "type": "ir.actions.act_window",
                "res_model": "cash.advance.form",
                "domain": [('id', 'in', advance_ids.ids)],
                "name": ("Cash Advance Form"),
                'view_mode': 'tree,form', 
            }
        if len(advance_ids)==1:
            result.update({
                'res_id':advance_ids.id,
                'view_mode':'form', 
                })
        return result 
    
    def _prepare_expense_vals(self):
        for rec in self:
            expense_form = self.env['approval.category'].search([('approval_type', '=', 'expense')], limit=1)
            l_vals = []
            for line in rec.product_line_ids:
                l_vals.append([0,0,{
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
                            'tax_ids': False,
                            'account_id': line.product_id.property_account_expense_id.id or line.product_id.categ_id.property_account_expense_categ_id.id
                        }])
                 
            vals = {
                'request_owner_id' : rec.request_owner_id.id, 
                'category_id': expense_form.id,
                'request_id' : rec.id,
                'purchase_order_id' : rec.purchase_order_id.id,
                'currency_id' : rec.currency_id.id or False,
                'staff_location_id' : rec.staff_location_id.id,
                'journal_id' : rec.default_journal_id.id,
                'partner_id' : rec.partner_id.id,
                'vendor_quotation_no' : rec.reference, #reference is named as 'Vendor Invoice No' on view
                'vendor_invoice_no' : rec.vendor_invoice_no,
                'pay_to_id' : rec.pay_to_id.id,
                'pay_to_external' : rec.pay_to_external,
                'staff_location_id' : rec.staff_location_id.id,
                'delivery_date' : rec.est_delivery_date,
                'value_date' : rec.value_date,
                'payment_type_id' : rec.payment_type_id.id,
                'expense_line_ids' : l_vals,
                'reason' : rec.reason,
                'delivery_date': rec.est_delivery_date,
                'location': rec.location,
                'fmis_petty_cash_document_no':rec.fmis_petty_cash_document_no,
            }
        return vals
    
    def action_create_expense(self):
        vals = self._prepare_expense_vals()
        expense_form = self.env['approval.expense'].create(vals)

        return {
            'name': "Expense Form",
            'view_mode': 'form',
            'res_model': 'approval.expense',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'view_id': self.env.ref('approval_extends.approval_expense_form_view').id,
            'res_id': expense_form.id,
        }
    
    def _compute_expense_count(self):
        for rec in self:
            rec.expense_count = self.env['approval.expense'].search_count([('request_id','=',rec.id)]) or 0
    
    def _compute_has_payment_request(self):
        for rec in self:
            #if approval type is create_rfq, allow to create only one payment request since 'payment vendor bill' is connected with 'purchase vendor bill'
            if rec.approval_type == 'purchase':
                rec.has_payment_request = self.env['approval.payment.request'].search_count([('request_id','=',rec.id),('request_status','!=','cancel')]) or 0
            else:
                rec.has_payment_request = False
    
    def _compute_has_cash_advance(self):
        for rec in self:
            rec.has_cash_advance = self.env['cash.advance.form'].search_count([('request_id','=',rec.id),('request_status','!=','cancel')]) or 0

    def _compute_has_expense(self):
        for rec in self:
            rec.has_expense = self.env['approval.expense'].search_count([('request_id','=',rec.id),('request_status','!=','cancel')]) or 0

    def action_view_expense(self):
        expense_ids = self.env['approval.expense'].search([('request_id','=',self.id)])
        result = {
                "type": "ir.actions.act_window",
                "res_model": "approval.expense",
                "domain": [('id', 'in', expense_ids.ids)],
                "name": ("Expense Form"),
                'view_mode': 'tree,form', 
            }
        if len(expense_ids)==1:
            result.update({
                'res_id':expense_ids.id,
                'view_mode':'form', 
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

        # duplicate_rfq = self.env['approval.request'].search([('approval_type', '=', 'purchase'), ('purchase_request_no', '=', self.purchase_request_no.id), 
        #                                                     ('request_status', 'not in', ['cancel', 'refuse']), ('purchase_order_count', '=', 0), ('id', '!=', self.id)])
        
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

    def _compute_payment_request_count(self):
        for rec in self:
            rec.payment_request_count = self.env['approval.payment.request'].search_count([('request_id','=',rec.id)]) or 0 

    def action_view_payment_request(self):
        payment_request_ids = self.env['approval.payment.request'].search([('request_id','=',self.id)])
        result = {
                "type": "ir.actions.act_window",
                "res_model": "approval.payment.request",
                "domain": [('id', 'in', payment_request_ids.ids)], 
                "name": ("Payment Request Form"),
                'view_mode': 'tree,form', 
            }
        if len(payment_request_ids)==1:
            result.update({
                'res_id':payment_request_ids.id,
                'view_mode':'form', 
                })
        return result 
    
    def _prepare_payment_request_vals(self): 
        for rec in self: 
            payment_request_form = self.env['approval.category'].search([('approval_type', '=', 'payment_request')], limit=1)
            l_vals = []
            for line in rec.product_line_ids:
                l_vals.append([0,0,{
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
                            'account_id': line.product_id.property_account_expense_id.id or line.product_id.categ_id.property_account_expense_categ_id.id or False,
                            'reference_key': line.reference_key,
                            'product_uom_id': line.product_uom_id.id,
                        }])
            """ID:3013
            GRN No: purchase_order > receipt > name
            """
            grn_no = ''
            if rec.purchase_order_id:
                incoming_picking = next((
                    picking for picking in rec.purchase_order_id.picking_ids
                    if picking.picking_type_id.code == 'incoming'
                ), None)
                grn_no = incoming_picking.name if incoming_picking else ""

            vals = {
                'request_owner_id' : rec.request_owner_id.id, 
                'category_id': payment_request_form.id,
                'request_id' : rec.id,
                'is_purchase': True if rec.approval_type == 'purchase' else False,
                'purchase_order_id' : rec.purchase_order_id.id,
                'partner_id' : rec.partner_id.id,
                'currency_id' : rec.currency_id.id or False,
                'value_date' : rec.value_date,
                'pay_to_id' : rec.pay_to_id.id,
                'pay_to_external' : rec.pay_to_external,
                'staff_location_id' : rec.staff_location_id.id,
                'journal_id' : rec.default_journal_id.id,
                'payment_request_line_ids' : l_vals,
                'payment_type_id' : rec.payment_type_id.id,
                'reason' : rec.reason,
                'delivery_date': rec.est_delivery_date,
                'location': rec.location,
                'grn_no': grn_no,
                'vendor_quotation_no': rec.reference, #reference is named as 'Vendor Invoice No' on view
                'vendor_invoice_no': rec.vendor_invoice_no,
            }
        return vals
    
    def action_create_payment_request(self):
        vals = self._prepare_payment_request_vals()
        payment_request_form = self.env['approval.payment.request'].create(vals)

        return {
            'name': "Approval Payment Request Form",
            'view_mode': 'form',
            'res_model': 'approval.payment.request',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'view_id': self.env.ref('approval_extends.approval_payment_request_form_view').id,
            'res_id': payment_request_form.id,
        }
    
    # def _compute_po_comparison_count(self):
    #     for rec in self:
    #         rec.po_comparison_count = self.env['po.comparison'].search_count([('id','=',rec.po_comparison_no.id)]) or 0

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
    