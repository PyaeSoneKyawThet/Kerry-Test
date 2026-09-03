from odoo import fields, models, api 

class HrEmployee(models.Model):
    _inherit = "hr.employee"    

    approver_ids = fields.One2many('approval.employee.line', 'employee_id')

    job_order_approver_id = fields.Many2one('res.users', string='Job Order Approver') 
    quotation_approver_id = fields.Many2one('res.users', string='Quotation') 
    invoice_approver_ids = fields.One2many('invoice.approver.line', 'employee_id', string="Invoice Approvers")
    bill_approver_ids = fields.One2many('bill.approver.line', 'employee_id')
    vendor_payment_approver_ids = fields.One2many('vendor.payment.approver.line', 'employee_id')
    customer_payment_approver_ids = fields.One2many('customer.payment.approver.line', 'employee_id')
    purchase_approver_ids = fields.One2many('purchase.approver.line', 'employee_id')