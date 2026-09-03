from odoo import api, fields, models, SUPERUSER_ID, _

class AccountMove(models.Model):
    _inherit = 'account.move'
    
    # job_order_id = fields.Many2one('sale.order', string='Job Order')
    job_order_count = fields.Integer(string='Job Order Count')

    job_order_type = fields.Selection(selection=[
                                    ("transport", "Transport"),
                                    ("warehouse", "Warehouse"),            
                                    ("dry_port", "Dry Port"),            
                                    ("freight", "Freight"),            
                                    ])
    project_name = fields.Char(string="Project Name")
    job_sub_service = fields.Char(string="Job Sub Service")

    staff_location_id = fields.Many2one('staff.location', string="Doc Location") 
    job_location_id = fields.Many2one('job.location', string="job Location")

    commodity = fields.Char(string="Commodity")
    pol = fields.Char(string="POL")
    pod = fields.Char(string="POD")    
    freight_payment_term = fields.Char(string="Freight Payment Term")

    hbl_hawb_no = fields.Char(string="HBL/HAWB No")
    mbl_mawb_no = fields.Char(string="MBL/MAWB No")
    vessel_voyage_no = fields.Char(string="Vessel & Voyage No")
    no_of_vehicle = fields.Char(string="No: of Vehicle")

    shipper = fields.Char(string="Shipper")
    consignee = fields.Char(string="Consignee")
    notify_party = fields.Char(string="Notify Party")
    current_date = fields.Date(compute="_compute_current_date", string="Current Date")

    attachment_ids = fields.Many2many('ir.attachment', string="Attachment")
    print_count = fields.Integer(string="Printed Invoice No", default=0,copy=False)
    remark = fields.Text(string="Remark")
    job_date = fields.Char(string="Job Date", readonly=False, store=True, compute="_compute_job_date")

    @api.depends('invoice_line_ids')
    def _compute_job_date(self):
        for rec in self:
            rec.job_date = ', '.join(sorted(set(line.job_date.strftime('%d/%m/%Y') for line in rec.invoice_line_ids if line.job_date)))

    @api.depends('current_date')
    def _compute_current_date(self):
        for move in self:
            move.current_date = fields.Date.today()
    
    # @api.depends('job_order_id')
    # def _compute_job_order_count(self):
    #     for move in self:
    #         move.job_order_count = len(move.job_order_id.ids) if move.job_order_id else 0
        
    def action_view_job_orders(self):
        pass
    #     formview_ref = self.env.ref('sale.view_order_form', False)        
    #     return {
    #         'name': "Job Orders",
    #         'view_mode': 'form',
    #         'view_id': False,
    #         'res_model': 'sale.order',
    #         'type': 'ir.actions.act_window',
    #         'target': 'current',
    #         'res_id': self.job_order_id.id, 
    #         'views': [(formview_ref.id, 'form')] if formview_ref else [(False, 'form')],
    #     }
        
    def _get_print_count(self):
        self.ensure_one()
        
        if self.state not in ['draft','cancel']:
            self.print_count += 1
        return self.print_count

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    job_order_id = fields.Many2one('sale.order', string='Job Order')
    fmis_job_no = fields.Char(string="FMIS Job No")
    bl_no = fields.Char(string="BL No")
    vehicle_no = fields.Char(string="Vehicle No")
    vehicle_type_id = fields.Many2one('vehicle.type', string="Vehicle Type")     

    container_no = fields.Char(string="Container No")
    container_type_id = fields.Many2one('container.type', string="Container Type")
    # job_location_id = fields.Many2one('job.location', string="job Location")
    job_date = fields.Date(string="Job Date",help="Job Date from job order/ Job Order Date from approval expense and payment request", store=True)
    attachment_ids = fields.Many2many('ir.attachment', string="Attachment", related="move_id.attachment_ids")
    inv_job_date = fields.Char(string="Job Date(Invoice)", related="move_id.job_date", store=True)
    job_order_type = fields.Selection(string="Job Order Type", related="move_id.job_order_type", store=True)
    job_sub_service = fields.Char(string="Job Sub Service", related="move_id.job_sub_service", store=True)

    """ job_date from expense and payment_request: carry date from expense_line and payment_request_line
        job_order_id is only show in invoice: carry date from job_order_line
    """
    @api.onchange('job_order_id')
    def _onchange_job_order_id(self):
        if self.job_order_id:
            self.job_date = self.sale_line_ids[:1].job_date if self.sale_line_ids and self.sale_line_ids[:1].job_date else self.job_order_id.job_date