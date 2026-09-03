from odoo import fields, models, api, _
from datetime import date, timedelta, datetime
from odoo.exceptions import UserError


class PoComparison(models.Model):
    _name = 'po.comparison'
    _description = "PO Comparison"
    _inherit = ['mail.thread', 'mail.activity.mixin'] 

    state = fields.Selection(selection=[('draft', 'Draft'), ('confirm', 'Confirmed'), ('cancel', 'Cancelled')], default='draft', tracking=True)
    
    name = fields.Char(string='Name', default="Draft")
    request_owner_id = fields.Many2one('res.users', string="Request Owner",default=lambda self: self.env.uid, copy=False, store=True, tracking=True)
    employee_id = fields.Many2one('hr.employee', string="Employee", related="request_owner_id.employee_id")
    department_id = fields.Many2one('hr.department',related="employee_id.department_id", string="Department", store=True, tracking=True) 

    category_id = fields.Many2one('approval.category',tracking=True)
    currency_id = fields.Many2one('res.currency', string="Currency", tracking=True)
    pay_to_id = fields.Many2one('hr.employee', string="Pay To ID")
    pay_to_external = fields.Char(string="Pay To External")

    staff_location_id = fields.Many2one('staff.location',string="Doc Location",tracking=True)
    est_delivery_date = fields.Date(string="Est Delivery Date")
    date = fields.Datetime(string="Date",default=datetime.now(), tracking=True)
    date_confirmed = fields.Datetime(string="Date Confirmed", copy=False, tracking=True)

    po_comparison_line_ids = fields.One2many(comodel_name='po.comparison.line', inverse_name='po_comparison_id', string="Comparison Ids",
                   store=True, readonly=False)
    
    create_rfq_no = fields.Many2one('approval.request', string="PO Comparison No.")  
    create_rfq_count = fields.Integer('Create RFQ Count', compute="_compute_create_rfq_count")
    company_id = fields.Many2one('res.company',string="Company",default=lambda self: self.env.company)
    remark = fields.Text(string="Comparison Remark")
    request_ids = fields.One2many('approval.request', 'po_comparison_id', string="RFQ", copy=False)
    pr_line_ids = fields.Many2many('approval.product.line', string="PR Line(s)", copy=False)

    #search parent department
    parent_department_id = fields.Many2one('hr.department', string="Parent Department", related="department_id.parent_id", store=True)

    #generate sequence code
    @api.model_create_multi
    def create(self, vals):              
        for val in vals:
            sequence = self.env['ir.sequence'].next_by_code('po.comparison.sequence')
            val['name'] = "{}".format(str(sequence))
        return super(PoComparison, self).create(vals)

    def action_confirm(self):
        for rec in self:
            rec.state = 'confirm'            
            rec.date_confirmed = date.today()
            approval_lines = rec.po_comparison_line_ids.mapped('purchase_request_line_id')
            approval_lines.write({'po_comparison_done': True})

    def action_cancel(self):
        if self.request_ids.filtered(lambda a: a.request_status == 'approved'): 
            raise UserError(_("You cannot cancel in RFQ Apporved State!"))        
        approval_lines = self.po_comparison_line_ids.mapped('purchase_request_line_id')
        approval_lines.write({'po_comparison_done': False}) 
        self.state = 'cancel'
        
    def unlink(self):
        if self.filtered(lambda a: a.state == 'confirm'): 
            raise UserError(_("You cannot delete in Confirmed State!"))
        approval_lines = self.po_comparison_line_ids.mapped('purchase_request_line_id')
        approval_lines.write({'po_comparison_done': False}) 
        return super().unlink()

    def action_draft(self):
        self.state = 'draft'

    def action_generate_lines(self):
        """Create PoComparisonLine records from pr_line_ids one by one"""
        for rec in self:
            if rec.pr_line_ids:
                rec.po_comparison_line_ids.unlink()  # optional: clear old lines
            lines_vals = []
            for pr_line in rec.pr_line_ids:
                
                lines_vals.append({
                    'po_comparison_id': rec.id,
                    'purchase_request_line_id': pr_line.id,
                    'product_id': pr_line.product_id.id,
                    'description': pr_line.description,
                    'brand_id': pr_line.brand_id.id,
                    'fmis_job_no': pr_line.fmis_job_no,
                    'quantity': pr_line.quantity,
                    'unit_price': pr_line.unit_price,
                    'analytic_distribution': pr_line.analytic_distribution,
                    'bl_no': pr_line.bl_no,
                    'vehicle_no': pr_line.vehicle_no,
                    'reference_key': pr_line.reference_key,
                    'product_uom_id': pr_line.product_uom_id.id
                })
            if lines_vals:
                self.env['po.comparison.line'].create(lines_vals)

    def _prepare_approval_create_rfq_vals(self): 
        """Prepare dictionary value to create CreateRFQ's"""
        for rec in self: 
            create_rfq = self.env['approval.category'].search([('approval_type', '=', 'purchase')], limit=1)
            l_vals = []
            for line in rec.po_comparison_line_ids:
                l_vals.append([0, 0, {
                    'product_id': line.product_id.id,
                    'description': line.description,
                    'brand_id': line.brand_id.id,
                    'fmis_job_no': line.fmis_job_no,
                    'vehicle_no': line.vehicle_no,
                    'bl_no': line.bl_no,
                    'reference_key': line.reference_key,
                    'analytic_distribution': line.analytic_distribution,
                    'quantity': line.quantity,
                    'product_uom_id': line.product_uom_id.id,
                    'unit_price': line.unit_price,
                    'purchase_request_line_id': line.purchase_request_line_id.id,
                    'po_comparison_line_id': line.id
                }])
                
            vals = {
                'request_owner_id' : rec.request_owner_id.id,
                'category_id': create_rfq.id,
                'po_comparison_id': rec.id,
                'currency_id' : rec.currency_id.id or False,
                'date': rec.date,
                # 'value_date' : rec.value_date,
                'est_delivery_date' : rec.est_delivery_date,
                'pay_to_id' : rec.pay_to_id.id,
                'pay_to_external' : rec.pay_to_external,
                'staff_location_id' : rec.staff_location_id.id,
                'product_line_ids' : l_vals,
            }
        return vals

    # PO Comparison -> Approval Request(CreateRFQ's)
    def action_create_new_quotation(self):
        vals = self._prepare_approval_create_rfq_vals()
        approval_create_rfq = self.env['approval.request'].create(vals)

        return {
            'name': "Approval Create RFQ",
            'view_mode': 'form',
            'res_model': 'approval.request',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'view_id': self.env.ref('approvals.approval_request_view_form').id,
            'res_id': approval_create_rfq.id,
        }
    
    def _compute_create_rfq_count(self):
        for rec in self:
            rec.create_rfq_count = self.env['approval.request'].search_count([('po_comparison_id','=',rec.id)]) or 0
    
    def action_view_approval_create_rfq(self):
        create_rfq_ids = self.env['approval.request'].search([('po_comparison_id','=',self.id)])
        result = {
                "type": "ir.actions.act_window",
                "res_model": "approval.request",
                "domain": [('id', 'in', create_rfq_ids.ids)],
                "name": ("Approval Request"),
                'view_mode': 'tree,form', 
            }
        if len(create_rfq_ids)==1:
            result.update({
                'res_id':create_rfq_ids.id,
                'view_mode':'form', 
                })
        return result 
    
    def action_print_comparison_report(self):
        return self.env.ref('approval_extends.po_comparison_report').report_action(self)
    
    def _get_report_filename(self):
        self.ensure_one()
        return 'Comparison Report-%s' % (self.name)  
    
    def _create_rfq_vals(self):
        create_rfq_ids = self.env['approval.request']
        for rec in self:
            rfqs = self.env['approval.request'].search([('po_comparison_id', '=', rec.id),('request_status','!=', 'cancel')])
            create_rfq_ids |= rfqs
        return create_rfq_ids