from odoo import fields, models, api, Command, _
from odoo.exceptions import UserError, ValidationError
from bs4 import BeautifulSoup

class AccountPayment(models.Model):
    _name = 'account.payment'
    _inherit = ['account.payment', 'analytic.mixin']

    cash_advance_id = fields.Many2one('cash.advance.form', string='Cash Advance', copy=False)
    request_id = fields.Many2one('approval.request', string="Purchase Request Ref", tracking=True)
    purchase_order_no = fields.Char(string="Purchase Order Ref")
    fmis_job_no = fields.Char(string="FMIS Job Number")
    job_date = fields.Date(string="Job Date")
    pay_to_id = fields.Many2one('hr.employee', string="Pay To Employee", tracking=True)
    pay_to_external = fields.Char(string="Pay To External", tracking=True)
    pay_to_bank_no = fields.Char(string="Pay To Bank No", tracking=True)
    vendor_quotation_no = fields.Char(string="Vendor Quotation No", help="Vendor Quotation No From Expense,Payment Request and Cash Advance")
    vendor_invoice_no = fields.Char(string="Vendor Invoice No", help="Vendor Invoice No From Expense,Payment Request and Cash Advance")
    vendor_invoice_date = fields.Date(string="Vendor Invoice Date")
    product_id = fields.Many2one('product.product',string="Product")
    bl_no = fields.Char(string="BL No")
    reference_key = fields.Char(string="Reference Key")
    vehicle_no = fields.Char(string="Vehicle No")
    approval_payment_request_id = fields.Many2one('approval.payment.request', string='Approval Payment Request', copy=False)
    approval_expense_id = fields.Many2one('approval.expense', string='Approval Expense', copy=False)
    brand_name = fields.Char(string="Brand")
    reason = fields.Html(string="Description")
    location = fields.Char(string="Delivery Location")
    delivery_date = fields.Date(string="Est. Delivery Date")
    diff_amount = fields.Float(string="Payment Difference")
    is_cash_advance = fields.Boolean(string="From Cash Advance", copy=False)
    is_reimburse_payment = fields.Boolean(string="From reimburse", default=False, copy=False, help="Payment from cash advance's reimburse.")
    available_cash_advance_ids = fields.Many2many('cash.advance.form', string="Available Cash Advance Ids", compute="_compute_available_cash_advance_ids")
    is_cash_advance_cancel = fields.Boolean(string="Cash Advance Cancel", tracking=True , copy=False )

    # add value from vendor/customer payment to journal entry
    def action_post(self):
        res = super().action_post()
        to_write = []
        for rec in self:
            for line in rec.move_id.line_ids:
                to_write.append((1, line.id, {
                                            'bl_no': rec.bl_no,
                                            'reference_key': rec.reference_key,
                                            'analytic_distribution': rec.analytic_distribution,
                                            'fmis_job_no' : rec.fmis_job_no,
                                            'job_date' : rec.job_date,
                                            'invoice_date': rec.vendor_invoice_date,
                                            'vehicle_no': rec.vehicle_no,
                                            'brand_name': rec.brand_name
                                }))
            rec.move_id.write({'line_ids': to_write,
                            'request_id': rec.request_id,
                            'pay_to_id': rec.pay_to_id,
                            'pay_to_external': rec.pay_to_external ,
                            'vendor_quotation_no': rec.vendor_quotation_no,
                            'vendor_invoice_no': rec.vendor_invoice_no,
                            'location': rec.location,
                            'reason': rec.reason,
                            'staff_location_id': rec.staff_location_id.id
                            })
            
            # payment from expense
            if rec.approval_expense_id and rec.cash_advance_id:
                rec.cash_advance_id.action_reconcile()

            # payment from cash advance reimburse
            if rec.is_reimburse_payment:
                rec.cash_advance_id.action_reconcile()

            # payment from payment_request
            if rec.approval_payment_request_id and rec.cash_advance_id:
                if rec.approval_payment_request_id.total_amount < rec.cash_advance_id.amount:
                    rec.cash_advance_id.action_reconcile()
                else:
                    rec.approval_payment_request_id.action_reconcile()
                    rec.cash_advance_id.action_reconcile()

        return res

    @api.onchange('request_id')
    def _onchange_purchase_request(self):
        self.partner_id = self.request_id.partner_id.id
        self.staff_location_id = self.request_id.staff_location_id.id
        self.account_payment_type_id = self.request_id.payment_type_id.id
        self.pay_to_id = self.request_id.pay_to_id.id
        self.pay_to_external = self.request_id.pay_to_external
        self.vendor_quotation_no = self.request_id.reference
        self.vendor_invoice_no = self.request_id.vendor_invoice_no 
        self.location = self.request_id.location
        self.reason = self.request_id.reason
        if self.request_id.product_line_ids:
            # self.analytic_distribution = self.request_id.product_line_ids[:1].analytic_distribution 
            self.fmis_job_no = ', '.join(sorted(set(line.fmis_job_no for line in self.request_id.product_line_ids if line.fmis_job_no))) 
            self.vehicle_no = ', '.join(sorted(set(line.vehicle_no for line in self.request_id.product_line_ids if line.vehicle_no))) 
            self.bl_no = ', '.join(sorted(set(line.bl_no for line in self.request_id.product_line_ids if line.bl_no))) 
            self.reference_key = ', '.join(sorted(set(line.reference_key for line in self.request_id.product_line_ids if line.reference_key)))
            self.brand_name = ', '.join(sorted(set(line.brand_id.name for line in self.request_id.product_line_ids if line.brand_id))) 

    """ payment from cash_advance, expense and payment,
        already passed destination_account: no need to change the account
    """
    @api.depends('journal_id', 'partner_id', 'partner_type', 'is_internal_transfer', 'destination_journal_id','cash_advance_id')
    def _compute_destination_account_id(self):
        # self.destination_account_id = False
        for pay in self:
            if pay.is_internal_transfer:
                pay.destination_account_id = pay.destination_journal_id.company_id.transfer_account_id
            elif pay.partner_type == 'customer':
                # Receive money from invoice or send money to refund it.
                if pay.partner_id:
                    destination_account_id = pay.partner_id.with_company(pay.company_id).property_account_receivable_id
                    #add custom code
                    pay.destination_account_id = pay.destination_account_id if pay.destination_account_id and pay.cash_advance_id else destination_account_id.id
                else:
                    pay.destination_account_id = self.env['account.account'].search([
                        *self.env['account.account']._check_company_domain(pay.company_id),
                        ('account_type', '=', 'asset_receivable'),
                        ('deprecated', '=', False),
                    ], limit=1)
            elif pay.partner_type == 'supplier':
                # Send money to pay a bill or receive money to refund it.
                if pay.partner_id:
                    destination_account_id = pay.partner_id.with_company(pay.company_id).property_account_payable_id
                    #add custom code
                    pay.destination_account_id = pay.destination_account_id if pay.destination_account_id and pay.cash_advance_id else destination_account_id.id
                    if pay.is_cash_advance:
                        pay.destination_account_id = pay.cash_advance_id.product_id.property_account_expense_id.id
                else:
                    pay.destination_account_id = self.env['account.account'].search([
                        *self.env['account.account']._check_company_domain(pay.company_id),
                        ('account_type', '=', 'liability_payable'),
                        ('deprecated', '=', False),
                    ], limit=1)
    
    """ If user manually set cash_advance, use product expense account for that journal."""
    @api.onchange('cash_advance_id')
    def _onchange_cash_advance_id(self):
        if self.cash_advance_id:
            self.destination_account_id = self.cash_advance_id.product_id.property_account_expense_id.id
            self.request_id = self.cash_advance_id.request_id.id

    @api.depends('is_cash_advance')
    def _compute_available_cash_advance_ids(self):
        for rec in self:
            payment_ids = self.env['account.payment'].search([('is_cash_advance', '=', True)]).filtered(lambda l: l.state != 'cancel')
            rec.available_cash_advance_ids = self.env['cash.advance.form'].search([('request_status', '=', 'approved'),('id','not in',payment_ids.cash_advance_id.ids)]) 

    def action_cancel(self):
        if self.is_cash_advance and self.cash_advance_id:
            return {
                'name': "Cancel Cash Advance",
                'type': 'ir.actions.act_window',
                'view_mode': 'form',            
                'res_model': 'cash.advance.cancel.wizard',  
                'views': [(False, 'form')],
                'view_id' : 'cash_advance_cancel_wizard',       
                'target': 'new',           
                'context': {'default_payment_id': self.id, 'default_cash_advance_id': self.cash_advance_id.id}            
            }
        else:
            return super().action_cancel()
        
    def action_draft(self):
        res = super().action_draft()
        if self.is_cash_advance:
            if self.cash_advance_id.request_status in ['cancel']:
                raise ValidationError(_("You can't set to draft in Cash Advance Cancel State!"))
            else:
                self.cash_advance_id.update({'is_cash_advance_cancel': False,})
                self.update({'is_cash_advance_cancel': False})
        return res
    
    def export_data(self, fields_to_export, **kwargs):
        data = super(AccountPayment, self).export_data(fields_to_export, **kwargs)
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
    
    


            