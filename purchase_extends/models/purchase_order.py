from odoo import fields, api, models, _, Command
from datetime import date, timedelta
from odoo.exceptions import UserError, ValidationError

class PurchaseOrder(models.Model):    
    _inherit = "purchase.order"

    amount_total_words = fields.Char(
        string="Amount total in words",
        compute="_compute_amount_total_words", 
    )

    vendor_contact_person = fields.Char(string="Contact Person")
    due_date = fields.Date(string="Due Date",compute="_compute_due_date")
    staff_location_id = fields.Many2one('staff.location', string="Document Location")
    prepared_department_id = fields.Many2one('hr.department',related="user_id.employee_id.department_id")
    vendor_quotation_no = fields.Char(string=" Vendor Quotation No")
    vendor_invoice_no = fields.Char(string=" Vendor Invoice No")
    vendor_quotation_date = fields.Date(string="Vendor Quotation Date")
    approved_by_id = fields.Many2one('res.users',string="Approved By") 
    po_approved_date = fields.Date(string="PO Approved Date")
    config_id = fields.Many2one('purchase.approval.config', string="Config", compute="_compute_approval_config")

    # approver fields
    request_status = fields.Selection([
                                    ('new', 'To Submit'),
                                    ('pending', 'Submitted'), 
                                    ('checked', 'Checking'), 
                                    ('approved', 'Approved'),
                                    ('refused', 'Refused'),
                                    ('cancel', 'Cancel'),
                                    ], default="new", compute="_compute_request_status",
                                    store=True, index=True, tracking=True, string="Request Status")
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
    
    purchase_approver_ids = fields.One2many('purchase.approver.line', 'purchase_id', compute="_compute_purchase_approver_ids",store=True, readonly=False)
    minimal_approver =  fields.Integer(string="Minimal Approvers", default=1)
    minimal_checker =  fields.Integer(string="Minimal Checkers", compute="_compute_minimal_checker")
    submit_user_id = fields.Many2one('res.users',string="Submit User", copy=False)
    po_done_state = fields.Boolean(string="PO Done", compute="compute_po_status", readonly=False, store=True, copy=False)
    print_count = fields.Integer(string="Printed Purchase No", default=0,copy=False)

    @api.onchange('partner_id')
    def get_vendor_contact_person(self):
            self.vendor_contact_person = self.partner_id.contact_person

    def _get_print_count(self):
        self.ensure_one()
        if self.state not in ['draft','sent','to approve']:
            self.print_count += 1
        return self.print_count

    @api.depends('state', 'order_line.qty_received', 'order_line.product_qty')
    def compute_po_status(self):
        for rec in self:
            if rec.state in ('purchase', 'done'):
                po_done = rec.order_line.mapped('qty_received') == rec.order_line.mapped('product_qty')
                rec.po_done_state = True if po_done else False
            else:       
                rec.po_done_state = False


    # def _auto_check_po_done(self):
    #     for order in self:
    #         if order.state == 'purchase' and not order.po_done:
    #             all_received = all(
    #                 line.qty_received >= line.product_qty
    #                 for line in order.order_line
    #                 if line.product_qty > 0
    #             )
    #             if all_received:
    #                 order.update({'po_done': True})
    
    # def write(self, vals):
    #     res = super().write(vals)
    #     self._auto_check_po_done()
    #     return res

    @api.depends('purchase_approver_ids')
    def _compute_minimal_checker(self):
        for rec in self:  
            rec.minimal_checker = len(rec.purchase_approver_ids[:-1]) if rec.purchase_approver_ids else 0 

    @api.depends_context('uid')
    @api.depends('purchase_approver_ids.status')
    def _compute_user_status(self):
        for rec in self:
            approvers = rec.purchase_approver_ids.filtered(
                lambda approver: self.env.user in approver.approval_user_ids
            )
            rec.user_status = approvers[:1].status if approvers else False

    @api.depends('submit_user_id')
    def _compute_purchase_approver_ids(self):
        for rec in self:
            approver_id_vals = [Command.clear()]  
            config = self.env['purchase.approval.config'].search([
                                ('from_amount', '<=', rec.amount_total),
                                ('to_amount', '>=', rec.amount_total),
                                ('currency_id', '=', rec.currency_id.id),
                            ],limit=1)
            if not config:
                raise ValidationError(_('No Approver for current amount!'))
            if config.need_approval:
                approver_approvers = rec.submit_user_id.employee_id.purchase_approver_ids.filtered(lambda a: a.sequence >= config.from_level and a.sequence <= config.to_level).sorted(key=lambda a: a.sequence)
                
                for approver in approver_approvers:    
                    if approver.approval_employee_id.id:                
                        approver_id_vals.append(Command.create({
                            'approval_user_ids': [(6, 0, approver.approval_user_ids.ids)],
                            'approval_employee_id': approver.approval_user_ids[:1].id if approver.approval_user_ids else False,
                            'status': 'new',
                            'sequence': approver.sequence,
                            'purchase_id': rec.id if rec.id else False,
                        }))
            rec.purchase_approver_ids = approver_id_vals
    
    @api.depends('amount_total')
    def _compute_approval_config(self):
        for rec in self:  
            config = self.env['purchase.approval.config'].search([
                                ('from_amount', '<=', rec.amount_total),
                                ('to_amount', '>=', rec.amount_total),
                                ('currency_id', '=', rec.currency_id.id),
                            ],limit=1) 
            if config:       
                rec.config_id = config.id
            else:
                rec.config_id = False

    @api.depends('purchase_approver_ids.status')
    def _compute_request_status(self):
        for request in self:
            status_lst = request.mapped('purchase_approver_ids.status')
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


    @api.depends('amount_total', 'currency_id')
    def _compute_amount_total_words(self):
        for move in self:
            amount_total_words = move.currency_id.amount_to_text(move.amount_total).replace(',', '')
            move.amount_total_words = amount_total_words + " Only" if amount_total_words and move.amount_total else ""

    @api.depends('date_order', 'payment_term_id')
    def _compute_due_date(self):
        for order in self:
            if order.date_order and order.payment_term_id:
                payment_term = order.payment_term_id._compute_terms(
                        date_ref=order.date_order or fields.Date.context_today(order),
                        currency=order.currency_id,
                        tax_amount_currency=0.0,
                        tax_amount=order.amount_total,
                        untaxed_amount_currency=0.0,
                        untaxed_amount=order.amount_untaxed,
                        company=order.company_id,
                        cash_rounding=False,
                        sign=1
                    )

                order.due_date = max(
                (k['date'] for k in payment_term['line_ids'] if k), 
                default=False,
            )
            else: 
                order.due_date = False
    # -------------------------------------------------
    # helper method for purchase order approval feature
    # -------------------------------------------------
    def _cancel_activities(self):
        approval_activity = self.env.ref('purchase_extends.mail_activity_data_purchase_kmtl')
        activities = self.activity_ids.filtered(lambda a: a.activity_type_id == approval_activity)
        activities.unlink()
    
    def _get_user_approval_activities(self, user):
        domain = [
            ('res_model', '=', 'purchase.order'),
            ('res_id', 'in', self.ids),
            ('activity_type_id', '=', self.env.ref('purchase_extends.mail_activity_data_purchase_kmtl').id),
            ('user_id', '=', user.id)
        ]
        activities = self.env['mail.activity'].search(domain)
        return activities 
    
    def _ensure_can_check(self):
        if any(approval.user_status == 'waiting' for approval in self):
            raise ValidationError(_('You cannot check before the previous checker.'))

    def _update_next_checkers(self, new_status, checker, only_next_checker, cancel_activities=False):
        checkers_updated = self.env['purchase.approver.line']
        for move in self:
            current_checker = move.purchase_approver_ids & checker
            checkers_to_update = move.purchase_approver_ids.filtered(lambda a: a.status not in ['approved', 'refused'] \
                                and (a.sequence > current_checker.sequence \
                                or (a.sequence == current_checker.sequence and a.id > current_checker.id)))

        if only_next_checker and checkers_to_update:
            checkers_to_update = checkers_to_update[0]
        checkers_updated |= checkers_to_update

        checkers_updated.sudo().status = new_status
        checkers_updated.sudo()._create_activity()
        if cancel_activities:
            checkers_updated.purchase_id._cancel_activities()

    def _ensure_can_approve(self):
        if any(approval.user_status == 'waiting' for approval in self):
            raise ValidationError(_('You cannot approve before the previous approver.'))
        
    def _update_next_approvers(self, new_status, approver, only_next_approver, cancel_activities=False):
        approvers_updated = self.env['purchase.approver.line'] 

        for approval in self:
            current_approver = approval.purchase_approver_ids & approver
            approvers_to_update = approval.purchase_approver_ids.filtered(lambda a: a.status not in ['approved', 'refused'] and (a.sequence > current_approver.sequence or (a.sequence == current_approver.sequence and a.id > current_approver.id)))
            
            if only_next_approver and approvers_to_update:
                approvers_to_update = approvers_to_update[0]
            approvers_updated |= approvers_to_update

        approvers_updated.sudo().status = new_status
        if new_status == 'pending':
            approvers_updated._create_activity()
        if cancel_activities:
            approvers_updated.purchase_id._cancel_activities()

    def _prepare_picking(self):
        vals = super(PurchaseOrder, self)._prepare_picking()
        vals['purchase_order_id'] = self.id
        # vals['purchase_request_no'] = self.purchase_request_no.id
        vals['prepared_by_id'] = self.submit_user_id.id
        vals['delivery_date'] = self.date_planned
        vals['vendor_invoice_no'] = self.vendor_invoice_no
        vals['is_from_po'] = True
        return vals
    
    # -----------------------------------------------
    # main method for purchase order approval feature
    # -----------------------------------------------
    def action_submit_purchase_order(self):
        self.submit_user_id = self.env.user

        if self.config_id and not self.config_id.need_approval:
            self.sudo().action_approve_purchase_order()
            return True
            
        approvers = self.purchase_approver_ids
        approvers = approvers.filtered(lambda a: a.status in ['new', 'to_check', 'pending', 'waiting'])
        if approvers:
            status  = 'pending' if len(approvers) == 1 else 'to_check'
        approvers[1:].sudo().write({'status': 'waiting'})
        approvers = approvers[0] if approvers and approvers[0].status != 'to_check' else self.env['purchase.approver.line']    
  
        approvers._create_activity()
        approvers.sudo().write({'status': status})
        # self.sudo()._get_user_approval_activities(user=self.env.user).action_feedback()
        return True
    
    def action_check_purchase_order(self,checker=None):
        self._ensure_can_check()    
        if not isinstance(checker, models.BaseModel):
            checker = self.mapped('purchase_approver_ids').filtered(
                lambda checker: self.env.user in checker.approval_user_ids)
        checker.status = 'checked'
        status_lst = self.mapped('purchase_approver_ids.status') 

        if status_lst.count('checked') >= (self.minimal_checker):
            self.sudo()._update_next_checkers('pending', checker, only_next_checker=True)
        else:
            self.sudo()._update_next_checkers('to_check', checker, only_next_checker=True)
        
        for user in checker.approval_user_ids:
            self.sudo()._get_user_approval_activities(user=user).action_feedback()

    def action_approve_purchase_order(self,approver=None):
        self._ensure_can_approve()
        if not isinstance(approver, models.BaseModel):
            approver = self.mapped('purchase_approver_ids').filtered(
                    lambda approver: self.env.user in approver.approval_user_ids
                ) 
             
        self.request_status = 'approved'  
        approver.write({'status': 'approved'})
        self.sudo()._update_next_approvers('pending', approver, only_next_approver=True)
        self.sudo()._get_user_approval_activities(user=self.env.user).action_feedback()
        self.sudo().button_confirm()
        self.write({'approved_by_id': self.env.user.id, 'po_approved_date': fields.Datetime.now() })
    
    def action_refuse_purchase_order(self,approver=None):
        if not isinstance(approver, models.BaseModel):
            approver = self.mapped('purchase_approver_ids').filtered(
                    lambda approver: self.env.user in approver.approval_user_ids
                )
                
        approver.write({'status': 'refused'})
        self.sudo()._update_next_approvers('refused', approver, only_next_approver=False, cancel_activities=True)
        self.sudo()._get_user_approval_activities(user=self.env.user).action_feedback()
        self.request_status = 'refused'

    def action_cancel_purchase_order(self):
        self.sudo()._get_user_approval_activities(user=self.env.user).unlink()
        self.mapped('purchase_approver_ids').write({'status': 'cancel'})
        self.request_status = 'cancel'
        self.sudo().button_cancel()

    def button_draft(self):
        """ set the submit_user_id to recompute purchase_approver_ids """
        res = super().button_draft()
        self.submit_user_id = self.submit_user_id
        return res

    def _prepare_invoice(self):
        vals = super(PurchaseOrder, self)._prepare_invoice()
        vals['vendor_invoice_no'] = self.vendor_invoice_no
        return vals
        
    
