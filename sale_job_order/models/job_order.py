
from itertools import groupby
from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.exceptions import UserError, ValidationError,AccessError
from odoo.fields import Command
from odoo.tools import float_is_zero 

INVOICED_STATE = [
    ('to_invoice', 'To Invoice'),
    ('invoiced', 'Invoiced'),
]

class SaleOrder(models.Model):
    _inherit = 'sale.order'
    
    company_currency_id = fields.Many2one(comodel_name='res.currency', string='Company currency', related='company_id.currency_id')
    job_order_type = fields.Selection(selection=[
                                    ("transport", "Transport"),
                                    ("warehouse", "Warehouse"),            
                                    ("dry_port", "Dry Port"),            
                                    ("freight", "Freight"),            
                                    ])

    is_job_order = fields.Boolean(string="Is Job Order?", default=False)
    project_name = fields.Char(string="Project Name")
    job_date = fields.Date(string="Job Date", default=fields.Date.context_today)
    receipt_date = fields.Date(string="Receipt Date")
    fmis_inv_number = fields.Char(string="FMIS Invoice Number") 
    job_sub_service = fields.Char(string="Job Sub Service") 
    staff_location_id = fields.Many2one('staff.location', string="Doc Location")
 
    pol = fields.Char(string="POL")
    pod = fields.Char(string="POD")
    vas_ref_ids = fields.Many2many('sale.order', 'sale_order_vas_rel', 'sale_order_id', 'vas_id', string='VAS Ref')
    freight_payment_term = fields.Char(string="Freight Payment Term")
    shipper = fields.Char(string="Shipper")
    consignee = fields.Char(string="Consignee")
    notify_party = fields.Char(string="Notify Party")
    no_of_vehicle = fields.Char(string="No: of Vehicle")
    hbl_hawb_no = fields.Char(string="HBL/HAWB No")
    mbl_mawb_no = fields.Char(string="MBL/MAWB No")
    vessel_voyage_no = fields.Char(string="Vessel & Voyage No")

    amount_total_words = fields.Char(
        string="Amount total in words",
        compute="_compute_amount_total_words",
    )
    job_categ_ids = fields.Many2many('product.category', 'line_id', 'categ_id', 'line_categ_rel', 
                                           string="Job Product Categories", compute="_compute_job_categ_ids")
    
    attachment_ids = fields.Many2many('ir.attachment', 'so_attachment_rel', 'sale_id', 'attachment_id', string="Attachment", copy=False)
    received_customer_id = fields.Many2one('res.partner', string="Received Customer")
    print_count = fields.Integer(string="Printed Sale/Job Order Count", default=0, copy=False)
    requester_id = fields.Many2one('res.users', related="user_id", string="Requester", store=True, readonly=True) # To Show Requester in Job Order List View [TASK-3706]
    confirmed_date = fields.Datetime(string="Confirmed Date")
    is_reversed = fields.Boolean(
        string="Reversed",
        compute="_compute_is_reversed",
        store=True,
        default=False
    )
    quotation_ref_ids = fields.Many2many('sale.order', 'order_id', 'related_id', 'sale_order_rel',  string="Quotation Refs")

    invoiced_state = fields.Selection(
        selection=INVOICED_STATE,
        string="Invoiced State",
        compute='_compute_invoiced_state',
        store=True,
        copy=False)
    
    # For Job Order for Sale
    sale_pic_ids = fields.Many2many("res.users", string="Sales PIC", related="partner_id.sale_pic_ids", readonly=True)
    
    @api.depends('invoice_ids.state')
    def _compute_invoiced_state(self):
        """
        Compute the custom invoice status of a SO.
        - to invioce. no posted invoice
        - invoiced. a least one posted invoice
        """
        for rec in self:
            if any(invoice.state == 'posted' for invoice in rec.invoice_ids):
                rec.invoiced_state = "invoiced"
            else:
                rec.invoiced_state = "to_invoice"

    @api.depends('invoice_ids.move_type','invoice_ids.state')
    def _compute_is_reversed(self):
        for order in self:
            invoices = order.invoice_ids.filtered(lambda m: m.state == 'posted')

            if not invoices:
                order.is_reversed = False
                continue

            # Find credit notes linked to invoices
            credit_notes = invoices.filtered(lambda m: m.move_type == 'out_refund')

            if not credit_notes:
                order.is_reversed = False       
            else:
                order.is_reversed = True
                

    def _prepare_confirmation_values(self):
        res = super()._prepare_confirmation_values()
        res.update({'date_order': self.date_order})
        return res
    
    @api.onchange('so_id')
    @api.depends('so_id')
    def _compute_job_categ_ids(self):
        for rec in self:
            rec.job_categ_ids = self.env['product.category'].search([]).ids

    @api.depends('amount_total', 'currency_id')
    def _compute_amount_total_words(self):
        for order in self:
            amount_total_words = order.currency_id.amount_to_text(order.amount_total).replace(',', '')
            order.amount_total_words = amount_total_words + " Only" if amount_total_words else ""
            
    @api.depends('opportunity_ids', 'so_id')
    @api.onchange('opportunity_ids', 'so_id')
    def _onchange_opportunity_ids(self):
            super()._onchange_opportunity_ids()
            for rec in self:
                if rec.is_job_order:
                    rec.commodity = rec.so_id.commodity

    def button_open_quotation_ref_ids(self):
        self.ensure_one()

        action = {
            'name': _("Quotation Ref"),
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'context': {'create': False},
        }
        if len(self.quotation_ref_ids) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': self.quotation_ref_ids.id,
            })
        else:
            action.update({
                'view_mode': 'list,form',
                'domain': [('id', 'in', self.quotation_ref_ids.ids)],
            })
        return action

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'company_id' in vals:
                self = self.with_company(vals['company_id'])
            if self._context.get('default_is_job_order'):
                vals['name'] = _("Draft")
                if 'user_id' in vals and vals['user_id']:
                    user = self.env['res.users'].browse(vals['user_id'])
                else:                
                    user = self.env.user
                job_order_approver = user.employee_id.job_order_approver_id
                vals['approved_by_id'] = job_order_approver.id if job_order_approver else False
            if vals.get('so_id'):
                quotation_partner = self.env['sale.order'].browse(vals['so_id']).partner_id
                if quotation_partner and quotation_partner.id == vals['partner_id']:
                    continue
                else:
                    raise UserError(_("Customer is not matched with Original Quotation!"))
        recs = super().create(vals_list)
        #This part is temporary solution for odoo bug(attachment many2many field)[TASK:3428]
        for rec in recs:    
            if rec.attachment_ids and not self.attachment_ids:
                rec.attachment_ids.update({
                'res_model': self._name,
                'res_id': rec.id,
                })            
            if not rec.attachment_ids and self.attachment_ids:
                new_attachments = self.env['ir.attachment']
                for att in self.attachment_ids:
                    new_att = att.copy({'res_id': rec.id})
                    new_attachments |= new_att
                rec.attachment_ids = new_attachments
        ####[TASK:3428]####
        return recs
    
    def write(self, values):
        if 'partner_id' in values:
            partner_id = values['partner_id']
        else:
            partner_id = self.partner_id
        if 'so_id' in values:
            quotation_partner = self.env['sale.order'].browse(values['so_id']).partner_id
            if quotation_partner and quotation_partner.id != partner_id.id:
                raise UserError(_("Customer is not matched with Original Quotation!"))
        
        return super().write(values)
    
    @api.onchange('user_id')
    def onchange_user_id(self):
        if self.is_job_order:
            self.approved_by_id = self.user_id.employee_id.job_order_approver_id
        else:
            super().onchange_user_id()

    def action_confirm(self):
        res = super().action_confirm()
        for order in self:
            order.confirmed_date = fields.Datetime.now()
        return res
    
    def _prepare_invoice(self):
        res = super()._prepare_invoice()
        job_date = ', '.join(sorted(set(line.job_date.strftime('%d/%m/%Y') for line in self.order_line if line.job_date)))
        res.update({'job_date': job_date,
                    'currency_id': self.currency_id.id,
                    'job_order_type': self.job_order_type,
                    'project_name': self.project_name,
                    'job_sub_service': self.job_sub_service,
                    'staff_location_id': self.staff_location_id.id,
                    'commodity': self.commodity, 
                    'pol': self.pol,
                    'pod': self.pod,
                    'freight_payment_term': self.freight_payment_term,
                    'hbl_hawb_no': self.hbl_hawb_no,
                    'mbl_mawb_no': self.mbl_mawb_no,
                    'vessel_voyage_no': self.vessel_voyage_no,
                    'no_of_vehicle': self.no_of_vehicle,
                    'shipper': self.shipper,
                    'consignee': self.consignee,
                    'notify_party': self.notify_party,
                    'attachment_ids': self.attachment_ids.ids,
                    'approved_by_id': self.approved_by_id.id
                    })
        return res    
    
    def job_order_report(self):
        return self.env.ref('sale_job_order.job_order_report').report_action(self)   
    
    def _get_print_count(self):
        self.ensure_one()
        
        if self.state in ['sale']:
            self.print_count += 1
        return self.print_count
    
class JobOrderLine(models.Model):
    _inherit = "sale.order.line"

    fmis_job_no = fields.Char(string="FMIS Job No")
    job_date = fields.Date(string="Job Date") 
    bl_no = fields.Char(string="BL No")
    vehicle_no = fields.Char(string="Vehicle No")
    vehicle_type_id = fields.Many2one("vehicle.type", string="Vehicle Type") 
    container_no = fields.Char(string="Container No")
    container_type_id = fields.Many2one("container.type", string="Container Type") 


    def _prepare_invoice_line(self, **optional_values):
        res = super()._prepare_invoice_line(**optional_values)
        res.update({'job_order_id': self.order_id.id,
                    'fmis_job_no': self.fmis_job_no,
                    'job_date': self.job_date or self.order_id.job_date,
                    'bl_no': self.bl_no,
                    'vehicle_no': self.vehicle_no,
                    'vehicle_type_id': self.vehicle_type_id.id,
                    'container_no': self.container_no,
                    'container_type_id': self.container_type_id.id,
                    })
        return res  