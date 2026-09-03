from odoo import fields, models
from bs4 import BeautifulSoup

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    payment_id = fields.Many2one('account.payment', string="Payment Reference")
    approval_request_id = fields.Many2one('approval.request', related="move_id.request_id", string="Purchase Request Ref", store=True, copy=False)
    cash_advance_id = fields.Many2one('cash.advance.form', related="move_id.cash_advance_id", string='Cash Advance', store=True)
    purchase_order_no = fields.Char(related="move_id.purchase_order_no", string="Purchase Order Ref", store=True)
    pay_to_id = fields.Many2one('hr.employee', related="move_id.pay_to_id", string="Pay To Employee", store=True)
    pay_to_external = fields.Char(string="Pay To External", related="move_id.pay_to_external", store=True)
    vendor_quotation_no = fields.Char(string="Vendor Quotation No", related="move_id.vendor_quotation_no", store=True)
    vendor_invoice_no = fields.Char(string="Vendor Invoice No", related="move_id.vendor_invoice_no", store=True)
    invoice_date = fields.Date(string="Vendor Invoice Date", related="move_id.invoice_date", store=True)
    reference_key = fields.Char(string="Reference Key")
    brand_id = fields.Many2one('purchase.brand', string="Brand ID")
    brand_name = fields.Char(string="Brand")
    reason = fields.Html(related="move_id.reason", string="Description")
    location = fields.Char(related="move_id.location", string="Delivery Location", store=True)
    account_payment_type_id = fields.Many2one('account.payment.type', related="move_id.account_payment_type_id", string="Custom Payment Type", store=True) 
    delivery_date = fields.Date(related="move_id.delivery_date", string="Est. Delivery Date", store=True)
    expense_id = fields.Many2one('approval.expense', related="move_id.expense_id", string="Write-Off PC", store=True)
    payment_request_id = fields.Many2one('approval.payment.request', related="move_id.payment_request_id", string="Write-Off PRQ", store=True)

    def export_data(self, fields_to_export, **kwargs):
        data = super(AccountMoveLine, self).export_data(fields_to_export, **kwargs)
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
