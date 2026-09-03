from odoo import api, fields, models, _

class AccountPaymentRegister(models.TransientModel):
    _inherit = "account.payment.register"

    approval_expense_id = fields.Many2one('approval.expense', string="Approval Expense", copy=False, 
                                    store=True, readonly=False, compute='_compute_approval_data')
    approval_payment_request_id = fields.Many2one('approval.payment.request', string="Approval Payment Request", copy=False, 
                                    store=True, readonly=False, compute='_compute_approval_data')
    reason = fields.Html(string="Particular Description", store=True, compute="_compute_approval_data",)
    staff_location_id = fields.Many2one('staff.location', string="Doc Location", copy=False, 
                                    store=True, readonly=False, compute='_compute_approval_data')
    cash_advance_id = fields.Many2one('cash.advance.form', string='Cash Advance', 
                                    store=True, readonly=False, compute='_compute_approval_data')
    request_id = fields.Many2one('approval.request', string="Purchase Request Ref", 
                                    store=True, readonly=False, compute='_compute_approval_data')
    purchase_order_no = fields.Char(string="Purchase Order No",
                                    store=True, readonly=False, compute='_compute_approval_data')
    fmis_job_no = fields.Char(string="FMIS Job Number",
                                    store=True, readonly=False, compute='_compute_approval_data')
    job_date = fields.Date(string="Job Date",
                                    store=True, readonly=False, compute='_compute_approval_data')
    pay_to_id = fields.Many2one('hr.employee', string="Pay To Employee",
                                    store=True, readonly=False, compute='_compute_approval_data')
    pay_to_external = fields.Char(string="Pay To External",
                                    store=True, readonly=False, compute='_compute_approval_data')
    bl_no = fields.Char(string="BL No",
                                    store=True, readonly=False, compute='_compute_approval_data')
    reference_key = fields.Char(string="Reference Key",
                                    store=True, readonly=False, compute='_compute_approval_data')
    vehicle_no = fields.Char(string="Vehicle No",
                                    store=True, readonly=False, compute='_compute_approval_data')                               
    brand_name = fields.Char(string="Brand",
                                    store=True, readonly=False, compute='_compute_approval_data')
    location = fields.Char(string="Location",
                                    store=True, readonly=False, compute='_compute_approval_data')
    delivery_date = fields.Date(string="Est. Delivery Date",
                                    store=True, readonly=False, compute='_compute_approval_data')
    vendor_invoice_no = fields.Char(string="Vendor Invoice No",
                                    store=True, readonly=False, compute='_compute_approval_data')
    vendor_quotation_no = fields.Char(string="Vendor Quotation No",
                                    store=True, readonly=False, compute='_compute_approval_data')
    vendor_invoice_date = fields.Date(string="Vendor Invoice Date",
                                    store=True, readonly=False, compute='_compute_approval_data')

    @api.model
    def _get_batch_approval_expense(self, batch_result):
        expense = [line.move_id.approval_expense_id for line in batch_result['lines']][0]
        return expense

    @api.model
    def _get_batch_reason(self, batch_result):
        reason = [line.move_id.reason for line in batch_result['lines']][0]
        return reason

    @api.model
    def _get_batch_cash_advance(self, batch_result):
        cash_advance = [line.move_id.cash_advance_id for line in batch_result['lines']][0]
        return cash_advance

    @api.model
    def _get_batch_doc_location(self, batch_result):
        doc_location = [line.move_id.staff_location_id for line in batch_result['lines']][0]
        return doc_location
    
    @api.model
    def _get_batch_approval_payment_request(self, batch_result):
        payment_request = [line.move_id.approval_payment_request_id for line in batch_result['lines']][0]
        return payment_request

    @api.model
    def _get_batch_approval_request(self, batch_result):
        request_id = [line.move_id.request_id for line in batch_result['lines']][0]
        return request_id

    @api.model
    def _get_batch_purchase(self, batch_result):
        purchase = [line.move_id.purchase_order_no for line in batch_result['lines']][0]
        return purchase

    @api.model
    def _get_batch_fmis_job_no(self, batch_result):
        fmis_job_no = [line.move_id.invoice_line_ids.filtered(lambda x: x.fmis_job_no).mapped('fmis_job_no') for line in batch_result['lines']][0]
        return ', '.join(sorted(set(fmis_job_no)))

    @api.model
    def _get_batch_fmis_job_date(self, batch_result):
        fmis_job_date = [line.move_id.invoice_line_ids[0].job_date for line in batch_result['lines'] if line.move_id.invoice_line_ids][0]
        return fmis_job_date

    @api.model
    def _get_batch_pay_to_employee(self, batch_result):
        pay_to_id = [line.move_id.pay_to_id for line in batch_result['lines']][0]
        return pay_to_id

    @api.model
    def _get_batch_pay_to_ext(self, batch_result):
        pay_to_external = [line.move_id.pay_to_external for line in batch_result['lines']][0]
        return pay_to_external

    @api.model
    def _get_batch_vendor_inv(self, batch_result):
        vendor_invoice_no = [line.move_id.vendor_invoice_no for line in batch_result['lines']][0]
        return vendor_invoice_no

    @api.model
    def _get_batch_vendor_quotation_no(self, batch_result):
        vendor_quotation_no = [line.move_id.vendor_quotation_no for line in batch_result['lines']][0]
        return vendor_quotation_no

    @api.model
    def _get_batch_inv_date(self, batch_result):
        vendor_invoice_date = [line.move_id.invoice_date for line in batch_result['lines']][0]
        return vendor_invoice_date

    @api.model
    def _get_batch_vehicle_no(self, batch_result):
        vehicle_no = [line.move_id.invoice_line_ids.filtered(lambda x: x.vehicle_no).mapped('vehicle_no') for line in batch_result['lines']][0]
        return ', '.join(sorted(set(vehicle_no)))
    
    @api.model
    def _get_batch_bl_no(self, batch_result):
        bl_no = [line.move_id.invoice_line_ids.filtered(lambda x: x.bl_no).mapped('bl_no') for line in batch_result['lines']][0]
        return ', '.join(sorted(set(bl_no)))
        
    @api.model
    def _get_batch_ref_key(self, batch_result):
        reference_key = [line.move_id.invoice_line_ids.filtered(lambda x: x.reference_key).mapped('reference_key') for line in batch_result['lines']][0]
        return ', '.join(sorted(set(reference_key)))

    @api.model
    def _get_batch_brand_name(self, batch_result):
        brand = [line.move_id.invoice_line_ids.filtered(lambda x: x.brand_name).mapped('brand_name') for line in batch_result['lines']][0]
        return ', '.join(sorted(set(brand)))

    @api.model
    def _get_batch_location(self, batch_result):
        location = [line.move_id.location for line in batch_result['lines']][0]
        return location   

    @api.model
    def _get_batch_delivery_date(self, batch_result):
        delivery_date = [line.move_id.delivery_date for line in batch_result['lines']][0]
        return delivery_date      
    
    @api.depends('can_edit_wizard')
    def _compute_approval_data(self):
        for wizard in self:
            if wizard.can_edit_wizard:
                batches = wizard._get_batches()
                wizard.approval_expense_id = wizard._get_batch_approval_expense(batches[0])
                wizard.cash_advance_id = wizard._get_batch_cash_advance(batches[0])
                wizard.reason = wizard._get_batch_reason(batches[0])
                wizard.approval_payment_request_id = wizard._get_batch_approval_payment_request(batches[0])
                wizard.staff_location_id = wizard._get_batch_doc_location(batches[0])
                wizard.request_id = wizard._get_batch_approval_request(batches[0])
                wizard.purchase_order_no = wizard._get_batch_purchase(batches[0])
                wizard.fmis_job_no = wizard._get_batch_fmis_job_no(batches[0])
                wizard.job_date = wizard._get_batch_fmis_job_date(batches[0])
                wizard.pay_to_id = wizard._get_batch_pay_to_employee(batches[0])
                wizard.pay_to_external = wizard._get_batch_pay_to_ext(batches[0])
                wizard.vendor_invoice_no = wizard._get_batch_vendor_inv(batches[0])
                wizard.vendor_quotation_no = wizard._get_batch_vendor_quotation_no(batches[0])
                wizard.vendor_invoice_date = wizard._get_batch_inv_date(batches[0])
                wizard.bl_no = wizard._get_batch_bl_no(batches[0])
                wizard.vehicle_no = wizard._get_batch_vehicle_no(batches[0])
                wizard.reference_key = wizard._get_batch_ref_key(batches[0])
                wizard.brand_name = wizard._get_batch_brand_name(batches[0])
                wizard.location = wizard._get_batch_location(batches[0])
                wizard.delivery_date = wizard._get_batch_delivery_date(batches[0])
            else:
                wizard.approval_expense_id = False
                wizard.cash_advance_id = False
                wizard.reason = False
                wizard.approval_payment_request_id = False
                wizard.staff_location_id = False
                wizard.request_id = False
                wizard.purchase_order_no = False
                wizard.fmis_job_no = False
                wizard.job_date = False
                wizard.pay_to_id = False
                wizard.pay_to_external = False
                wizard.vendor_invoice_no = False
                wizard.vendor_quotation_no = False
                wizard.vendor_invoice_date = False
                wizard.bl_no = False
                wizard.vehicle_no = False
                wizard.reference_key = False
                wizard.brand_name = False
                wizard.location = False
                wizard.delivery_date = False
                                
    def _create_payment_vals_from_wizard(self, batch_result):
        res = super(AccountPaymentRegister,self)._create_payment_vals_from_wizard(batch_result)
        res['approval_expense_id'] = self.approval_expense_id.id
        res['approval_payment_request_id'] = self.approval_payment_request_id.id
        res['staff_location_id'] = self.staff_location_id.id
        res['cash_advance_id'] = self.cash_advance_id.id
        res['request_id'] = self.request_id.id
        res['reason'] = self.reason
        res['purchase_order_no'] = self.purchase_order_no
        res['fmis_job_no'] = self.fmis_job_no
        res['job_date'] = self.job_date
        res['pay_to_id'] = self.pay_to_id.id
        res['pay_to_external'] = self.pay_to_external
        res['vendor_invoice_no'] = self.vendor_invoice_no
        res['vendor_quotation_no'] = self.vendor_quotation_no
        res['vendor_invoice_date'] = self.vendor_invoice_date
        res['delivery_date'] = self.delivery_date
        res['bl_no'] = self.bl_no
        res['location'] = self.location
        res['reference_key'] = self.reference_key
        res['vehicle_no'] = self.vehicle_no
        res['brand_name'] = self.brand_name
        res['diff_amount'] = self.payment_difference
        return res

    def _create_payments(self):
        res = super()._create_payments()
        res.approval_expense_id.sudo().write({'payment_id': res.id})
        res.approval_payment_request_id.sudo().write({'payment_ids': [(4, res.id)]})
        return res