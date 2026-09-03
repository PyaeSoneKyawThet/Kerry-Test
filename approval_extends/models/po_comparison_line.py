
from odoo import fields, models, api


class PoComparisonLine(models.Model):
    _name = 'po.comparison.line'
    _description = "PO Comparison Line"
    _inherit = ['mail.activity.mixin', 'analytic.mixin']
    _check_company_auto = True

    name = fields.Char(string="Name")
    po_comparison_id = fields.Many2one('po.comparison', ondelete='cascade', index=True, copy=False)
    request_owner_id = fields.Many2one('res.users', related="po_comparison_id.request_owner_id", string="Request Owner", store=True) 
    department_id = fields.Many2one('hr.department', related="request_owner_id.employee_id.department_id", string="Department", store=True)  
    product_id = fields.Many2one('product.product',string="Product")
    description = fields.Char(
        "Description", required=True,
        compute="_compute_description", store=True, readonly=False, precompute=True)    
    brand_id = fields.Many2one('purchase.brand', string="Brand")
    fmis_job_no = fields.Char(string="FMIS Job Number")
    vehicle_no = fields.Char(string="Vehicle No")
    bl_no = fields.Char(string="BL No")
    reference_key = fields.Char(string="Reference Key")

    currency_id = fields.Many2one('res.currency')
    quantity = fields.Float(string="Qty")
    unit_price = fields.Float(string="Unit Price", copy=False, digits='Product Price')
    product_uom_id = fields.Many2one('uom.uom', string='UoM')
    total_amount = fields.Monetary(
        string="Total",
        currency_field='currency_id',
        compute='_compute_total_amount', store=True, readonly=False
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        string="Company",
        required=True,
        readonly=True,
        default=lambda self: self.env.company, 
    )
    purchase_request_line_id = fields.Many2one('approval.product.line') 

    @api.depends('unit_price', 'quantity')
    def _compute_total_amount(self):
        for rec in self:
            rec.total_amount = rec.unit_price * rec.quantity

    @api.depends('product_id')
    def _compute_description(self):
        for line in self:
            line.description = line.product_id.description_purchase or line.product_id.display_name

    @api.onchange('purchase_request_line_id')
    def _onchange_purchase_request_line(self):
        for rec in self:
            if rec.purchase_request_line_id:
                rec.update({
                    'product_id': rec.purchase_request_line_id.product_id.id,
                    'description': rec.purchase_request_line_id.description,
                    'brand_id': rec.purchase_request_line_id.brand_id.id,
                    'fmis_job_no': rec.purchase_request_line_id.fmis_job_no,
                    'quantity': rec.purchase_request_line_id.quantity,
                    'unit_price': rec.purchase_request_line_id.unit_price,
                    'analytic_distribution': rec.purchase_request_line_id.analytic_distribution,
                    'bl_no': rec.purchase_request_line_id.bl_no,
                    'vehicle_no': rec.purchase_request_line_id.vehicle_no,
                    'reference_key': rec.purchase_request_line_id.reference_key,
                    'product_uom_id': rec.purchase_request_line_id.product_uom_id.id
                })
