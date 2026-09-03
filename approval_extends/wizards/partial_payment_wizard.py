from odoo import api, fields, models, _

class PartialPayment(models.TransientModel):
    _name = 'partial.payment.wizard'
    _description = "Partial Payment Wizard"

    amount = fields.Float(string="Amount")
    date = fields.Date(string="Payment Request Date", default=fields.Date.today(), required=True)
    communication = fields.Char(string="Memo", required=True)
    journal_id = fields.Many2one('account.journal', string="Journal")
    currency_id = fields.Many2one('res.currency', string="Currency")
    payment_request_id = fields.Many2one('approval.payment.request', string="Payment Request")
    vendor_invoice_date = fields.Date(string="Vendor Invoice Date")

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        res_id = self._context.get('active_id')
        res_model = self._context.get('active_model')
        if res_model == 'approval.payment.request' and res_id:
            payment_request = self.env['approval.payment.request'].browse(res_id)
            res['amount'] = payment_request.amount_residual
            res['currency_id'] = payment_request.currency_id.id
            res['journal_id'] = payment_request.journal_id.id
            res['vendor_invoice_date'] = payment_request.vendor_invoice_date
        return res


    def _prepare_partial_payment_vals(self):
        payment_method = self.env['account.payment.method'].search([('payment_type', '=', 'inbound'),('name', '=', 'Manual')])[:1]
        payment_type = 'outbound'
        partner_type = 'supplier'
        amount = self.amount
        # use journal from payment type TASK: 3668
        journal_id = False
        if self.payment_request_id.payment_type_id.journal_ids:
            journal_id = self.payment_request_id.payment_type_id.journal_ids.ids[0]

        vals = {'partner_id': self.payment_request_id.partner_id.id or self.payment_request_id.request_owner_id.partner_id.id,
                'cash_advance_id': self.payment_request_id.cash_advance_ids[0].id if self.payment_request_id.cash_advance_ids else False,
                'date': self.date,
                'amount': amount,
                'currency_id': self.currency_id.id,
                'payment_type': payment_type,
                'partner_type': partner_type,
                'journal_id': journal_id,
                'payment_method_id': payment_method.id,
                'company_id': self.payment_request_id.company_id.id,
                'ref': self.communication,
                'approval_payment_request_id': self.payment_request_id.id,
                'state': 'draft',
                'request_id': self.payment_request_id.request_id.id, 
                'purchase_order_no': self.payment_request_id.purchase_order_id.name,
                'pay_to_id': self.payment_request_id.pay_to_id.id, 
                'pay_to_external': self.payment_request_id.pay_to_external, 
                'vendor_invoice_no': self.payment_request_id.vendor_invoice_no, 
                'vendor_quotation_no': self.payment_request_id.vendor_quotation_no,  
                'vendor_invoice_date': self.vendor_invoice_date,  
                'staff_location_id': self.payment_request_id.staff_location_id.id, 
                'account_payment_type_id': self.payment_request_id.payment_type_id.id,
                'reason': self.payment_request_id.reason,
                'delivery_date': self.payment_request_id.delivery_date,
                } 
        return vals

    def action_create_partial_payment(self):
        payment_vals = self._prepare_partial_payment_vals()
        payment = self.env['account.payment'].sudo().create(payment_vals)
        self.payment_request_id.sudo().write({'enable_direct_payment': False})