from itertools import groupby
from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.exceptions import AccessError, UserError
from odoo.tools.mail import is_html_empty
from markupsafe import Markup
from datetime import timedelta
from bs4 import BeautifulSoup

class SaleOrder(models.Model):
    _inherit = 'sale.order'
    
    user_id = fields.Many2one(
        comodel_name='res.users',
        string="Salesperson",
        compute='_compute_user_id',
        store=True, readonly=False, precompute=True, index=True,
        tracking=2,
        domain=lambda self: "[('groups_id', '=', {}), ('share', '=', False), ('company_ids', '=', company_id)]".format(
            self.env.ref("sales_team.group_sale_salesman").id)
    )
    
    validity_date = fields.Date(
        string="Validity Date",
        compute='_compute_validity_date',
        store=True, readonly=False, copy=False, precompute=True)    
    approval_state = fields.Selection([('submitted', 'Submitted'),  
                                       ('re-submitted', 'Re-Submitted'), 
                                       ('approved', 'Approved'),
                                       ('rejected', 'Rejected')], default='', tracking=True, copy=False)        
    reject_reason = fields.Text(string="Reject Reason", tracking=True)
    attention_to = fields.Char(string="Attention To", tracking=True)
    category_ids = fields.Many2many("product.category", 'sale_id', 'categ_id', 'sale_categ_rel', string="Categories")
    category_note = fields.Html(string="Category Notes", compute="_compute_categ_note", readonly=False, store=True)
    
    revise_state = fields.Selection([('revise_requested', 'Requested'), 
                                    ('revise_approved', 'Revised'), 
                                    ('revise_rejected', 'Rejected')], default='', tracking=True, copy=False) 
    revise_reason_ids = fields.One2many('revise.reason', 'so_id', string='Revise Reason')
    revise_order_ids = fields.One2many(comodel_name='sale.order', inverse_name="original_so_id", string="Revise SO")

    approval_reason_ids = fields.One2many('approval.reason', 'so_id', string='Approval Reason')
    approval_order_ids = fields.One2many(comodel_name='sale.order', inverse_name="original_so_id", string="approval SO")
    
    is_vas = fields.Boolean(string="Is VAS Order?")
    is_vas_created = fields.Boolean(string="VAS Created?")
    is_renew_created = fields.Boolean(string="Renew Created?")
    vas_order_ids = fields.One2many(comodel_name='sale.order', inverse_name="original_so_id", string="VAS SO")
    original_so_id = fields.Many2one('sale.order', string="Original Quotation Ref", copy=False)

    prepared_by_id = fields.Many2one(string='Prepared by', comodel_name='res.users', copy=False, store=True,
                                    default=lambda self: self.env.user)        
    # approved_by_id = fields.Many2one(string='Approved by', comodel_name='res.users', copy=False, store=True,
    #                                 related="user_id.employee_id.quotation_approver_id")
    approved_by_id = fields.Many2one('res.users', string="Approved By", tracking=True) 
    enable_approve = fields.Boolean(string="Enable Approve", compute="_compute_enable_approve")
    available_approver_ids = fields.Many2many('res.users', string="Available Approvers",
                                            related="user_id.employee_id.user_ids")
    sale_person_department_id = fields.Many2one('hr.department', related="user_id.department_id", string="Department", store=True)
    address_incomplete = fields.Boolean(string="Address Incomplete", compute='_compute_address_incomplete')
    # has_access_to_request = fields.Boolean(string="Has Access To Request", compute="_compute_has_access_to_request")

    remark = fields.Html(string="Remark", readonly=False)

    @api.depends('partner_id')
    def _compute_user_id(self):
        for order in self:
            order.user_id = self.env.user
            
    
    @api.onchange('user_id')
    def onchange_user_id(self):
        self.approved_by_id = self.user_id.employee_id.quotation_approver_id

    @api.depends('partner_id')
    def _compute_address_incomplete(self):
        for order in self:
            if order.partner_id:
                order.address_incomplete = not order.partner_id.has_address()
            else:
                order.address_incomplete = False  

    @api.onchange('partner_id')
    def _onchage_partner_id(self):
        if self.partner_id:
            self.attention_to = self.partner_id.contact_person

    @api.onchange('sale_order_template_id')
    def _onchange_sale_order_template_id(self):
        """Keep existing lines and validity date; update Terms & Conditions only when template changes."""
        validity_date = self._origin.validity_date or self.validity_date
        if not self.sale_order_template_id:
            self.validity_date = validity_date
            return

        template = self.sale_order_template_id.with_context(lang=self.partner_id.lang)
        if not is_html_empty(template.note):
            self.note = template.note

        # Existing quotation lines: do not replace products/prices/qty from template.
        if self.order_line:
            self.validity_date = validity_date
            return

        res = super()._onchange_sale_order_template_id()
        self.validity_date = validity_date
        return res

    # @api.depends('approved_by_id')
    # @api.depends_context('uid')
    # def _compute_has_access_to_request(self):
    #     for request in self:
    #         request.has_access_to_request = request.approved_by_id == self.env.user
    
    #override        
    @api.depends('company_id')
    def _compute_validity_date(self):
        today = fields.Date.context_today(self)
        for order in self:
            # Keep an already filled validity date (e.g. when quotation template changes).
            if order.validity_date:
                order.validity_date = order.validity_date
                continue
            if order.is_job_order:
                days = order.company_id.quotation_validity_days
                if days > 0:
                    order.validity_date = today + timedelta(days)
                else:
                    order.validity_date = False
            else:
                order.validity_date = False
    
    @api.depends('prepared_by_id')
    def _compute_enable_approve(self):
        for rec in self:
            rec.enable_approve  = self.env.user == rec.approved_by_id and (rec.approval_state == 'submitted' or rec.revise_state == 'revise_requested')
    
    #prepare order line for new creation like revise or renew   
    def _prepare_new_order_lines(self, line):        
        l_vals = {
            'sequence': line.sequence,
            'product_id': line.product_id.id,
            'product_uom_qty': line.product_uom_qty or 1.0,
            'product_uom': line.product_uom.id,
            'tax_id': line.tax_id.ids,
            'discount': line.discount or 0.0, 
            'name': line.name,
            'price_unit': line.price_unit or 0.0, 
            'inv_currency_id': line.inv_currency_id.id if line.inv_currency_id else False,
            'categ_id': line.categ_id.id if line.categ_id else False,
            'cost': line.cost or 0.0, 
            'gross_profit': line.gross_profit,
            'display_type' : line.display_type, 
            'remark': line.remark,
            }
        return l_vals
    
    #prepare order for new creation like revise or renew   
    def _prepare_new_order(self, so_line_list):
        vals = {
                'partner_id': self.partner_id.id,
                'date_order': self.date_order,
                'warehouse_id': self.warehouse_id.id,
                'currency_id': self.currency_id.id,
                'order_line': so_line_list,  
                'original_so_id': self.id,
                'category_ids': self.category_ids.ids,
                'category_note': self.category_note,
                'note': self.note,
                'sale_order_template_id': self.sale_order_template_id.id,
                'state': 'draft',
                'opportunity_ids' : self.opportunity_ids.ids,
                'attention_to': self.attention_to,
                'validity_date': self.validity_date,
                'commodity': self.commodity,
                'payment_term_id': self.payment_term_id.id,
                'user_id': self.user_id.id,
                'approved_by_id': self.approved_by_id.id
                }
        return vals 
    
    #Revise Creation Part    
    def action_revise_request(self):
        self.ensure_one()
        return {
            'name': "Revise Request Reason",
            'type': 'ir.actions.act_window',
            'view_mode': 'form',            
            'res_model': 'wizard.revise.reason',  
            'views': [(False, 'form')],
            'view_id' : 'view_form_revise_reason_wizard',       
            'target': 'new',           
            'context': {'default_sale_order_id': self.id, 'default_state': 'revise_requested'}            
        }
        
    def action_create_new_order(self):
        self.ensure_one()
        so_line_list = []
        for line in self.order_line:
            so_line_list.append([0,0,self._prepare_new_order_lines(line)])        
        so_vals = self._prepare_new_order(so_line_list)
        # if not self.is_vas:
        #     so_vals['user_id'] = self.user_id.id
        #     so_vals['approved_by_id'] = self.user_id.employee_id.quotation_approver_id.id
        if self.is_vas:
            sequence = self.env['ir.sequence'].next_by_code('vas.sale.order')
            so_vals['name'] = "{}".format(str(sequence))
        new_order = self.env['sale.order'].create(so_vals)
        return new_order
    
    def action_revise_approve(self):
        self.ensure_one()
        self.action_create_new_order()
        self.env['revise.reason'].create({'so_id': self.id, 'state': 'revise_approved'})
        self.sudo().write({'revise_state' : 'revise_approved'})
        super(SaleOrder, self).action_lock() 
        self.sudo()._get_user_approval_activities(user=self.env.user).action_feedback()           
        
    def action_revise_reject(self):
        self.ensure_one()
        return {
            'name': "Revise Reject Reason",
            'type': 'ir.actions.act_window',
            'view_mode': 'form',            
            'res_model': 'wizard.revise.reason',  
            'views': [(False, 'form')],
            'view_id' : 'view_form_revise_reason_wizard',       
            'target': 'new',           
            'context': {'default_sale_order_id': self.id, 'default_state': 'revise_rejected'}            
        }    
   
    #VAS Creation Part
    def action_VAS_create(self):
        self.ensure_one()
        new_so_vals = {
            'partner_id': self.partner_id.id,
            'original_so_id': self.id,
            'is_vas': True,
            'state': 'draft',
            'validity_date': self.validity_date, 
            'user_id': self.user_id.id,
            'approved_by_id': self.approved_by_id.id
        }
        sequence = self.env['ir.sequence'].next_by_code('vas.sale.order')
        new_so_vals['name'] = "{}".format(str(sequence))   
        new_so = self.env['sale.order'].create(new_so_vals)
        self.is_vas_created = True
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'res_id': new_so.id, 
            'view_mode': 'form', 
            'target': 'current',
        }

    #Renew Creation Part
    def action_renew(self):
        self.ensure_one()
        so_line_list = []
        for line in self.order_line: 
            so_line_list.append([0,0,self._prepare_new_order_lines(line)]) 
        new_so_vals = self._prepare_new_order(so_line_list)    
        if self.is_vas:
            sequence = self.env['ir.sequence'].next_by_code('vas.sale.order')
            new_so_vals['name'] = "{}".format(str(sequence))
            new_so_vals['is_vas'] = True
            self.is_vas_created = True
        else:
            sequence = self.env['ir.sequence'].next_by_code('sale.order')
            new_so_vals['name'] = sequence
            new_so_vals['is_vas'] = False
        new_so = self.env['sale.order'].create(new_so_vals)
        self.is_renew_created = True
        return False
    
    @api.onchange('category_ids')
    @api.depends('category_ids')
    def _compute_categ_note(self):
        for order in self:
            categories = order.category_ids.with_context(lang=order.partner_id.lang)
            if categories:
                order.category_note = Markup('<p>').join(order.category_ids.filtered(lambda x: not is_html_empty(x.note)).mapped('note'))
            else:
                order.category_note = False
            
    def _prepare_invoice(self):
        invoice_vals = super(SaleOrder, self)._prepare_invoice()
        invoice_vals['attention_to'] = self.attention_to 
        return invoice_vals
    
    def action_draft(self):
        super().action_draft()
        self.write({'approval_state': ''})         
    
    def action_submit(self):
        self.env['approval.reason'].create({'so_id': self.id, 'state': 'submitted'})

        if self.staff_location_id and self.name in ('Draft', '/'):
            seq_number = self.env['staff.location'].search([('id', '=', self.staff_location_id.id)]).get_seq_number('job_order')
            self.name = seq_number
                
        prepared_user = self.prepared_by_id.id or self.env.uid
        self.sudo().approval_state = 'submitted' 
        self.sudo().prepared_by_id = prepared_user
        if self.prepared_by_id and self.approved_by_id:
            to_approver = self.approved_by_id.id
            self.activity_schedule('sale_extends.mail_activity_data_sale_kmtl',
                                    user_id=to_approver)
        self.user_id = self.env.user
            
    
    #2nd time add
    def _get_user_approval_activities(self, user):
        domain = [
            ('res_model', '=', 'sale.order'),
            ('res_id', 'in', self.ids),
            ('activity_type_id', '=', self.env.ref('sale_extends.mail_activity_data_sale_kmtl').id),
            ('user_id', '=', user.id)
        ]
        activities = self.env['mail.activity'].search(domain)
        return activities 

    def action_approve(self):
        self.ensure_one()
        #2nd time add
        self.env['approval.reason'].create({'so_id': self.id, 'state': 'approved'})
        self.sudo().write({'approval_state' : 'approved'})
        self.action_confirm()
        self.sudo()._get_user_approval_activities(user=self.env.user).action_feedback()     
        
    def action_reject(self):
        self.ensure_one()
        return {
            'name': "Approval Reject Reason",
            'type': 'ir.actions.act_window',
            'view_mode': 'form',            
            'res_model': 'wizard.approval.reason',  
            'views': [(False, 'form')],
            'view_id' : 'view_form_approval_reason_wizard',       
            'target': 'new',           
            'context': {'default_sale_order_id': self.id, 'default_state': 'rejected'}            
        }

    def action_resubmit(self):
        self.ensure_one()
        self.write({'approval_state': 're-submitted'})
        return {
            'name': "Approval Resubmit Reason",
            'type': 'ir.actions.act_window',
            'view_mode': 'form',            
            'res_model': 'wizard.approval.reason',  
            'views': [(False, 'form')],
            'view_id' : 'view_form_approval_reason_wizard',       
            'target': 'new',           
            'context': {'default_sale_order_id': self.id, 'default_state': 're-submitted'}            
        }

    def export_data(self, fields_to_export, **kwargs):
        data = super(SaleOrder, self).export_data(fields_to_export, **kwargs)

        category_index = fields_to_export.index('category_note') if 'category_note' in fields_to_export else None
        note_index = fields_to_export.index('note') if 'note' in fields_to_export else None
        remark_index = fields_to_export.index('order_line/remark') if 'order_line/remark' in fields_to_export else None
        order_remark_index = fields_to_export.index('remark') if 'remark' in fields_to_export else None

        if category_index is not None or note_index is not None or remark_index is not None or order_remark_index is not None:
            for record in data['datas']:
                try:
                    if category_index is not None:
                        category = record[category_index]
                        if category:
                            category_soup = BeautifulSoup(category, 'html.parser')
                            record[category_index] = category_soup.get_text()
                    if note_index is not None:
                        note = record[note_index]
                        if note:
                            note_soup = BeautifulSoup(note, 'html.parser')
                            record[note_index] = note_soup.get_text()
                    if remark_index is not None:
                        remark = record[remark_index]
                        if remark:
                            remark_soup = BeautifulSoup(remark, 'html.parser')
                            record[remark_index] = remark_soup.get_text()
                    if order_remark_index is not None:
                        order_remark = record[order_remark_index]
                        if order_remark:
                            order_remark_soup = BeautifulSoup(order_remark, 'html.parser')
                            record[order_remark_index] = order_remark_soup.get_text()
                except Exception:
                    continue

        return data

    
    # def _get_currency_invoiceable_lines(self, final=False, currency=False):
    #     """Return the invoiceable lines for order `self`."""
    #     down_payment_line_ids = []
    #     invoiceable_line_ids = []
    #     pending_section = None
    #     precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')

    #     for line in self.order_line.filtered(lambda x: x.inv_currency_id.id == currency.id):
    #         if line.display_type == 'line_section':
    #             # Only invoice the section if one of its lines is invoiceable
    #             pending_section = line
    #             continue
    #         if line.display_type != 'line_note' and float_is_zero(line.qty_to_invoice, precision_digits=precision):
    #             continue
    #         if line.qty_to_invoice > 0 or (line.qty_to_invoice < 0 and final) or line.display_type == 'line_note':
    #             if line.is_downpayment:
    #                 # Keep down payment lines separately, to put them together
    #                 # at the end of the invoice, in a specific dedicated section.
    #                 down_payment_line_ids.append(line.id)
    #                 continue
    #             if pending_section:
    #                 invoiceable_line_ids.append(pending_section.id)
    #                 pending_section = None
    #             invoiceable_line_ids.append(line.id)

    #     return self.env['sale.order.line'].browse(invoiceable_line_ids + down_payment_line_ids)
    
    # def _create_invoices(self, grouped=False, final=False, date=None):
    #     """ Create invoice(s) for the given Sales Order(s).

    #     :param bool grouped: if True, invoices are grouped by SO id.
    #         If False, invoices are grouped by keys returned by :meth:`_get_invoice_grouping_keys`
    #     :param bool final: if True, refunds will be generated if necessary
    #     :param date: unused parameter
    #     :returns: created invoices
    #     :rtype: `account.move` recordset
    #     :raises: UserError if one of the orders has no invoiceable lines.
    #     """
    #     if not self.env['account.move'].check_access_rights('create', False):
    #         try:
    #             self.check_access_rights('write')
    #             self.check_access_rule('write')
    #         except AccessError:
    #             return self.env['account.move']

    #     # 1) Create invoices.
    #     invoice_vals_list = []
    #     invoice_item_sequence = 0 # Incremental sequencing to keep the lines order on the invoice.
    #     currency_list = []
    #     for line in self.order_line:
    #         invoice_vals_list = []
    #         order = line.order_id
    #         order = order.with_company(order.company_id).with_context(lang=order.partner_invoice_id.lang)
    #         if not line.inv_currency_id:
    #             raise UserError(_("Please define currency in Sale Order Line!"))
    #         if line.inv_currency_id and line.inv_currency_id.id not in currency_list:
    #             currency_list.append(line.inv_currency_id.id)
    #             invoice_vals = order._prepare_invoice()
    #             invoice_vals.update({'currency_id': line.inv_currency_id.id})
    #             invoiceable_lines = self._get_currency_invoiceable_lines(final, line.inv_currency_id)

    #             if not any(not line.display_type for line in invoiceable_lines):
    #                 continue

    #             invoice_line_vals = []
    #             down_payment_section_added = False
    #             for line in invoiceable_lines:
    #                 if not down_payment_section_added and line.is_downpayment:
    #                     # Create a dedicated section for the down payments
    #                     # (put at the end of the invoiceable_lines)
    #                     invoice_line_vals.append(
    #                         Command.create(
    #                             order._prepare_down_payment_section_line(sequence=invoice_item_sequence)
    #                         ),
    #                     )
    #                     down_payment_section_added = True
    #                     invoice_item_sequence += 1
    #                 invoice_line_vals.append(
    #                     Command.create(
    #                         line._prepare_invoice_line(sequence=invoice_item_sequence)
    #                     ),
    #                 )
    #                 invoice_item_sequence += 1

    #             invoice_vals['invoice_line_ids'] += invoice_line_vals
    #             invoice_vals_list.append(invoice_vals)

    #             if not invoice_vals_list and self._context.get('raise_if_nothing_to_invoice', True):
    #                 raise UserError(self._nothing_to_invoice_error_message())

    #             # 2) Manage 'grouped' parameter: group by (partner_id, currency_id).
    #             if not grouped:
    #                 new_invoice_vals_list = []
    #                 invoice_grouping_keys = self._get_invoice_grouping_keys()
    #                 invoice_vals_list = sorted(
    #                     invoice_vals_list,
    #                     key=lambda x: [
    #                         x.get(grouping_key) for grouping_key in invoice_grouping_keys
    #                     ]
    #                 )
    #                 for _grouping_keys, invoices in groupby(invoice_vals_list, key=lambda x: [x.get(grouping_key) for grouping_key in invoice_grouping_keys]):
    #                     origins = set()
    #                     payment_refs = set()
    #                     refs = set()
    #                     ref_invoice_vals = None
    #                     for invoice_vals in invoices:
    #                         if not ref_invoice_vals:
    #                             ref_invoice_vals = invoice_vals
    #                         else:
    #                             ref_invoice_vals['invoice_line_ids'] += invoice_vals['invoice_line_ids']
    #                         origins.add(invoice_vals['invoice_origin'])
    #                         payment_refs.add(invoice_vals['payment_reference'])
    #                         refs.add(invoice_vals['ref'])
    #                     ref_invoice_vals.update({
    #                         'ref': ', '.join(refs)[:2000],
    #                         'invoice_origin': ', '.join(origins),
    #                         'payment_reference': len(payment_refs) == 1 and payment_refs.pop() or False,
    #                     })
    #                     new_invoice_vals_list.append(ref_invoice_vals)
    #                 invoice_vals_list = new_invoice_vals_list

    #             # 3) Create invoices.

    #             # As part of the invoice creation, we make sure the sequence of multiple SO do not interfere
    #             # in a single invoice. Example:
    #             # SO 1:
    #             # - Section A (sequence: 10)
    #             # - Product A (sequence: 11)
    #             # SO 2:
    #             # - Section B (sequence: 10)
    #             # - Product B (sequence: 11)
    #             #
    #             # If SO 1 & 2 are grouped in the same invoice, the result will be:
    #             # - Section A (sequence: 10)
    #             # - Section B (sequence: 10)
    #             # - Product A (sequence: 11)
    #             # - Product B (sequence: 11)
    #             #
    #             # Resequencing should be safe, however we resequence only if there are less invoices than
    #             # orders, meaning a grouping might have been done. This could also mean that only a part
    #             # of the selected SO are invoiceable, but resequencing in this case shouldn't be an issue.
    #             if len(invoice_vals_list) < len(self):
    #                 SaleOrderLine = self.env['sale.order.line']
    #                 for invoice in invoice_vals_list:
    #                     sequence = 1
    #                     for line in invoice['invoice_line_ids']:
    #                         line[2]['sequence'] = SaleOrderLine._get_invoice_line_sequence(new=sequence, old=line[2]['sequence'])
    #                         sequence += 1

    #             # Manage the creation of invoices in sudo because a salesperson must be able to generate an invoice from a
    #             # sale order without "billing" access rights. However, he should not be able to create an invoice from scratch.
    #             moves = self.env['account.move'].sudo().with_context(default_move_type='out_invoice').create(invoice_vals_list)

    #             # 4) Some moves might actually be refunds: convert them if the total amount is negative
    #             # We do this after the moves have been created since we need taxes, etc. to know if the total
    #             # is actually negative or not
    #             if final:
    #                 moves.sudo().filtered(lambda m: m.amount_total < 0).action_switch_move_type()
    #             for move in moves:
    #                 if final:
    #                     # Downpayment might have been determined by a fixed amount set by the user.
    #                     # This amount is tax included. This can lead to rounding issues.
    #                     # E.g. a user wants a 100€ DP on a product with 21% tax.
    #                     # 100 / 1.21 = 82.64, 82.64 * 1,21 = 99.99
    #                     # This is already corrected by adding/removing the missing cents on the DP invoice,
    #                     # but must also be accounted for on the final invoice.

    #                     delta_amount = 0
    #                     for order_line in self.order_line:
    #                         if not order_line.is_downpayment:
    #                             continue
    #                         inv_amt = order_amt = 0
    #                         for invoice_line in order_line.invoice_lines:
    #                             sign = 1 if invoice_line.move_id.is_inbound() else -1
    #                             if invoice_line.move_id == move:
    #                                 inv_amt += invoice_line.price_total * sign
    #                             elif invoice_line.move_id.state != 'cancel':  # filter out canceled dp lines
    #                                 order_amt += invoice_line.price_total * sign
    #                         if inv_amt and order_amt:
    #                             # if not inv_amt, this order line is not related to current move
    #                             # if no order_amt, dp order line was not invoiced
    #                             delta_amount += inv_amt + order_amt

    #                     if not move.currency_id.is_zero(delta_amount):
    #                         receivable_line = move.line_ids.filtered(
    #                             lambda aml: aml.account_id.account_type == 'asset_receivable')[:1]
    #                         product_lines = move.line_ids.filtered(
    #                             lambda aml: aml.display_type == 'product' and aml.is_downpayment)
    #                         tax_lines = move.line_ids.filtered(
    #                             lambda aml: aml.tax_line_id.amount_type not in (False, 'fixed'))
    #                         if tax_lines and product_lines and receivable_line:
    #                             line_commands = [Command.update(receivable_line.id, {
    #                                 'amount_currency': receivable_line.amount_currency + delta_amount,
    #                             })]
    #                             delta_sign = 1 if delta_amount > 0 else -1
    #                             for lines, attr, sign in (
    #                                 (product_lines, 'price_total', -1 if move.is_inbound() else 1),
    #                                 (tax_lines, 'amount_currency', 1),
    #                             ):
    #                                 remaining = delta_amount
    #                                 lines_len = len(lines)
    #                                 for line in lines:
    #                                     if move.currency_id.compare_amounts(remaining, 0) != delta_sign:
    #                                         break
    #                                     amt = delta_sign * max(
    #                                         move.currency_id.rounding,
    #                                         abs(move.currency_id.round(remaining / lines_len)),
    #                                     )
    #                                     remaining -= amt
    #                                     line_commands.append(Command.update(line.id, {attr: line[attr] + amt * sign}))
    #                             move.line_ids = line_commands

    #                 move.message_post_with_source(
    #                     'mail.message_origin_link',
    #                     render_values={'self': move, 'origin': move.line_ids.sale_line_ids.order_id},
    #                     subtype_xmlid='mail.mt_note',
    #                 )
    #     return moves
        
class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    inv_currency_id = fields.Many2one('res.currency', string='Inv Currency')
    price_subtotal = fields.Monetary(
                    string="Subtotal",
                    compute='_compute_amount',
                    currency_field='inv_currency_id',
                    store=True, precompute=True)
    price_total = fields.Monetary(
                    string="Total",
                    compute='_compute_amount',
                    currency_field='inv_currency_id',
                    store=True, precompute=True)
    categ_id = fields.Many2one('product.category', string="Product Category") 
    parent_categ_ids = fields.Many2many('product.category', 'line_id', 'categ_id', 'line_categ_rel', 
                                           string="Parent Categories", compute="_compute_categ_ids")   
    available_categ_ids = fields.Many2many('product.category', 'line_id', 'categ_id', 'line_categ_rel', 
                                           string="Avalilable Product Categories", compute="_compute_categ_ids")
    
    #Update(TASK-2747)
    #Show Parent Category in Job Order and Quotation
    @api.onchange('categ_id')
    @api.depends('categ_id')
    def _compute_categ_ids(self):
        for line in self:
            if line.order_id.mapped('category_ids'):
                categ_ids = line.order_id.mapped('category_ids').ids
                parent_ids = self.env['product.category'].search(['|', ('id', 'in', categ_ids), ('child_id', 'in', categ_ids), ('parent_id', '=', False)])
                line.parent_categ_ids = parent_ids.ids
                line.available_categ_ids = parent_ids.child_id.ids
            else:
                line.available_categ_ids = self.env['product.category'].search([])
                line.parent_categ_ids = self.env['product.category'].search([])
