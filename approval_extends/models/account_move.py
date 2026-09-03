from odoo import fields, models, api ,_
from odoo.exceptions import UserError, ValidationError
from bs4 import BeautifulSoup

class VendorBill(models.Model):
    _inherit = "account.move"    

    approval_expense_id = fields.Many2one('approval.expense', string='PC No')
    approval_payment_request_id = fields.Many2one('approval.payment.request',string="PRQ No")
    cash_advance_id = fields.Many2one('cash.advance.form', string='Cash Advance')
    request_id = fields.Many2one('approval.request', string="PR No")
    approval_payment_request_date = fields.Date(string="PRQ Date") 
    delivery_date = fields.Date(string="Est. Delivery Date")
    receive_date = fields.Date(string="Receive Date")
    value_date = fields.Date(string="Value Date")
    vendor_invoice_date = fields.Date(string="Vendor Invioce Date")

    pay_to_id = fields.Many2one('hr.employee',string="Pay To Employee")
    pay_to_external = fields.Char(string="Pay To External", readonly=False, store=True)
    grn_no = fields.Char(string="GRN No")
    vendor_bank_info = fields.Char(string="Vendor Bank Info")
    reason = fields.Html(string="Particular Description")
    auto_reconciled = fields.Boolean(string="Auto Reconcile?")
    reconcile_entry_id = fields.Many2one('account.move', string="Reconcile Journal Entry")
    # fmis_job_no = fields.Char(string="FMIS Job Number")
    vehicle_no = fields.Char(string="Vehicle No")
    location = fields.Char(string="Location")
    purchase_order_no = fields.Char(string="Purchase Order Ref")
    #This part is write off to link with expense and payment request 
    expense_id = fields.Many2one('approval.expense', string='Write-Off PC')
    payment_request_id = fields.Many2one('approval.payment.request', string="Write-Off PRQ")
    fmis_petty_cash_document_no = fields.Char(string="FIMS Document No")
    is_expense_cancel = fields.Boolean(string="Expense Cancel", tracking=True , copy=False )
    is_payment_request_cancel = fields.Boolean(string="Payment Request Cancel", tracking=True , copy=False)

    @api.onchange('partner_id')
    def _onchange_partner_id_for_bank_info(self):
        if self.partner_id:
            self.vendor_bank_info = self.partner_id.vendor_bank_info

    def action_post(self):
        res = super().action_post()
        # If Invoice is from approval expense(with is_cash_advance on), draft journal entry will create when invoice is posted
        if self.move_type == 'in_invoice' and self.approval_expense_id.is_cash_advance:
            if self.approval_expense_id.cash_advance_ids and not self.approval_expense_id.cash_advance_ids[0].product_id.property_account_expense_id:
                raise UserError(_("You have to add Advance COA on cash advance product!")) 
            reconcile_vals = self.approval_expense_id._prepare_reconcile_move_vals()
            move_entry = self.env['account.move'].sudo().create(reconcile_vals)
            self.approval_expense_id.reconcile_entry_id = move_entry.id
            self.reconcile_entry_id = move_entry.id

        # If VendorBill is from approval payment request, draft journal entry will create when bill is posted
        if self.move_type == 'in_invoice' and self.approval_payment_request_id.is_cash_advance:
            if self.approval_payment_request_id.cash_advance_ids and not self.approval_payment_request_id.cash_advance_ids[0].product_id.property_account_expense_id:
                raise UserError(_("You have to add Advance COA on cash advance product!")) 
            reconcile_vals = self.approval_payment_request_id._prepare_reconcile_move_vals()
            move_entry = self.env['account.move'].sudo().create(reconcile_vals)
            self.approval_payment_request_id.reconcile_entry_id = move_entry.id
            self.reconcile_entry_id = move_entry.id
        return res

    def button_draft(self):
        res = super().button_draft()
        if any(rec.reconcile_entry_id and rec.reconcile_entry_id.state == 'posted' for rec in self):
            raise ValidationError(_('You cannot cancel in journal entry posted state!'))
        self.reconcile_entry_id.button_cancel()

        if self.approval_expense_id:
            if self.approval_expense_id.request_status in ['cancel']:
                raise ValidationError(_("You can't set to draft in Expense Cancel State!"))
            else:
                self.approval_expense_id.update({'is_expense_cancel': False,})
                self.update({'is_expense_cancel': False})
        
        if self.approval_payment_request_id:
            if self.approval_payment_request_id.request_status in ['cancel']:
                raise ValidationError(_("You can't set to draft in Payment Request Cancel State!"))
            else:
                self.approval_payment_request_id.update({'is_payment_request_cancel': False,})
                self.update({'is_payment_request_cancel': False})
        return res
    
    def action_cancel(self):
        self.ensure_one()
        if self.approval_expense_id:
            return {
                'name': "Cancel Expense",
                'type': 'ir.actions.act_window',
                'view_mode': 'form',            
                'res_model': 'expense.cancel.wizard',  
                'views': [(False, 'form')],
                'view_id' : 'expense_cancel_wizard',       
                'target': 'new',           
                'context': {'default_move_id': self.id, 'default_approval_expense_id': self.approval_expense_id.id}            
            }
        if self.approval_payment_request_id:
            return {
                'name': "Cancel Payment Request",
                'type': 'ir.actions.act_window',
                'view_mode': 'form',            
                'res_model': 'payment.request.cancel.wizard',  
                'views': [(False, 'form')],
                'view_id' : 'payment_request_cancel_wizard',       
                'target': 'new',           
                'context': {'default_move_id': self.id, 'default_approval_payment_request_id': self.approval_payment_request_id.id}            
            }
        else:
            return super().action_cancel()

    def export_data(self, fields_to_export, **kwargs):
        data = super(VendorBill, self).export_data(fields_to_export, **kwargs)
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
