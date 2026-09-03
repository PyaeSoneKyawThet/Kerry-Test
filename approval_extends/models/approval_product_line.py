# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare, float_is_zero, float_round


class ApprovalProductLine(models.Model):
    _name = 'approval.product.line'
    _inherit = ['approval.product.line', 'analytic.mixin']
    _rec_name = "approval_request_id"
     
    unit_price = fields.Float(string="Unit Price")
    total = fields.Float(string="Total",compute="_compute_total")
    description = fields.Char(
        "Label", required=True,
        compute="_compute_description", store=True, readonly=False, precompute=True)
    category_id = fields.Many2one('product.category',string="Product Category")
    job_location_id = fields.Many2one('job.location', string="Job Location")
    brand_id = fields.Many2one('purchase.brand', string="Brand")
    fmis_job_no = fields.Char(string="FMIS Job No")
    vehicle_no = fields.Char(string="Vehicle No")
    bl_no = fields.Char(string="BL No")
    reference_key = fields.Char(string="Reference Key")
    request_owner_id = fields.Many2one('res.users', related="approval_request_id.request_owner_id", string="Request Owner", store=True)
    department_id = fields.Many2one('hr.department', related="request_owner_id.employee_id.department_id", string="Department", store=True)
    request_category_id = fields.Many2one('approval.category', related="approval_request_id.category_id", string="Approval Category", store=True)
    request_status = request_status = fields.Selection(related="approval_request_id.request_status",
        store=True, index=True, group_expand=True)

    purchase_request_no = fields.Many2one('approval.request', string="Purchase Request No.")  
    purchase_request_line_id = fields.Many2one('approval.product.line', string="Purchase Request Line")  
    without_PO = fields.Boolean(related="approval_request_id.without_PO", string="Without PO", store=True)
    po_comparison_done = fields.Boolean(default=False, string="PO Comparison Done") 
    pr_done = fields.Boolean(related="approval_request_id.pr_done", string="PR Done", store=True)
    approval_type = fields.Selection(related="request_category_id.approval_type")
    job_date = fields.Date(string="Job Date")
    created_po = fields.Boolean(default=False, string="PO Created")
    po_comparison_line_id = fields.Many2one('po.comparison.line', string="Comparison line", copy=False)

    #search parent department
    parent_department_id = fields.Many2one('hr.department', string="Parent Department", related="department_id.parent_id", store=True)
    
    def unlink(self):
        if self.filtered(lambda a: a.request_status == 'approved'): 
            raise UserError(_("You can't delete in Approved State!"))
        
        if self.filtered(lambda a: a.po_comparison_line_id): 
            raise UserError(_("You can't delete line from comparison!"))
        return super().unlink()

    @api.depends('unit_price', 'quantity')
    def _compute_total(self):
        precision = self.env['decimal.precision'].precision_get('Product Price')
        for line in self:
            if line.unit_price and line.quantity:
                rounded_price = float_round(
                    line.unit_price,
                    precision_digits=precision
                )
                line.total = rounded_price * line.quantity
            else:
                line.total = 0.0
    
    @api.onchange('purchase_request_line_id')
    def _onchange_purchase_request_line(self):
        for rec in self:
            if rec.purchase_request_line_id:
                rec.update({
                    'product_id': rec.purchase_request_line_id.product_id,
                    'description': rec.purchase_request_line_id.description,
                    'brand_id': rec.purchase_request_line_id.brand_id,
                    'fmis_job_no': rec.purchase_request_line_id.fmis_job_no,
                    'quantity': rec.purchase_request_line_id.quantity,
                    'unit_price': rec.purchase_request_line_id.unit_price,
                    'analytic_distribution': rec.purchase_request_line_id.analytic_distribution,
                    'bl_no': rec.purchase_request_line_id.bl_no,
                    'vehicle_no': rec.purchase_request_line_id.vehicle_no,
                    'reference_key': rec.purchase_request_line_id.reference_key,
                    'product_uom_id': rec.purchase_request_line_id.product_uom_id
                })
                 
    def _get_purchase_order_values(self, partner):
        res = super()._get_purchase_order_values(partner)
        res.update({'approval_request_ids': self.approval_request_id.ids,
                    'currency_id': self.approval_request_id.currency_id.id,
                    'date_planned': self.approval_request_id.est_delivery_date,
                    'pay_to_id': self.approval_request_id.pay_to_id.id,
                    'pay_to_external': self.approval_request_id.pay_to_external,
                    'rfq_id': self.approval_request_id.id,
                    'value_date': self.approval_request_id.value_date,
                    'staff_location_id': self.approval_request_id.staff_location_id.id,
                    'vendor_quotation_date': self.approval_request_id.vendor_quotation_date,
                    'vendor_quotation_no': self.approval_request_id.reference,
                    'vendor_invoice_no': self.approval_request_id.vendor_invoice_no})
        return res
                   
    def action_create_po_comparison(self): 
        l_vals = []
        vals = {}
        approval_type = self.env['approval.category'].search([('approval_type', '=', 'po_comparison')], limit=1)
        for line in self:
            l_vals.append([0,0,{
                        'product_id': line.product_id.id,
                        'brand_id': line.brand_id.id,
                        'fmis_job_no': line.fmis_job_no,
                        'vehicle_no': line.vehicle_no,
                        'quantity': line.quantity,
                        'unit_price': line.unit_price,
                        'product_uom_id': line.product_uom_id.id,
                        'bl_no': line.bl_no,
                        'analytic_distribution': line.analytic_distribution,
                        # 'account_id': rec.default_journal_id.default_account_id.id, 
                        'reference_key': line.reference_key,
                        # 'purchase_request_id': line.approval_request_id.id,
                        'purchase_request_line_id': line.id,
                    }])
        if not vals:
            vals = {
                    'request_owner_id' : self.env.user.id, 
                    'category_id': approval_type.id,
                    # 'request_id' : self.approval_request_id.id,
                    # 'partner_id' : self.approval_request_id.partner_id.id,
                    # 'currency_id' : self.approval_request_id.currency_id.id or False,
                    # 'value_date' : self.approval_request_id.value_date,
                    # 'reference' : rec.reference,
                    # 'pay_to_id' : self.approval_request_id.pay_to_id.id,
                    # 'pay_to_external' : self.approval_request_id.pay_to_external,
                    # 'staff_location_id' : self.approval_request_id.staff_location_id.id,
                    # 'journal_id' : rec.default_journal_id.id,
                    'po_comparison_line_ids' : l_vals,
                }
        self.env['po.comparison'].create(vals)
    
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
                            plan_name = 'Loc'
                        if analytic_account.plan_id.name == 'Job Department':
                            plan_name = 'Utilize Dept'
                        if not analytic_account.plan_id.name == 'Projects':
                            result.append({
                                'plan_name': plan_name,
                                'account_name': account_name
                            })
        return result

