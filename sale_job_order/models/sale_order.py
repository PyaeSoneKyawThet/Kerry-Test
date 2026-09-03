from itertools import groupby
from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.fields import Command
from odoo.tools import float_is_zero

class SaleOrder(models.Model):
    _inherit = 'sale.order'
    
    available_partner_ids = fields.Many2many('res.partner',compute="_compute_available_partner_ids")
    job_order_id = fields.Many2one('sale.order', domain="[('is_job_order', '=', True)]")

    @api.depends('is_job_order')
    def _compute_available_partner_ids(self):
        for rec in self:
            if rec.is_job_order:
                rec.available_partner_ids = self.env['res.partner'].search([]).ids
            else:
                rec.available_partner_ids = self.env['res.partner'].search(['|',('sale_pic_ids', '=', False), ('sale_pic_ids', 'in', self.env.user.id)]).ids

    so_id = fields.Many2one('sale.order', string="Quotation Ref")
    currency_id = fields.Many2one(
        comodel_name='res.currency',
        compute='_compute_currency_id',
        store=True,
        precompute=False,
        readonly=False,
        ondelete='restrict', default=lambda self: self.env.user.company_id.currency_id)
    
    @api.depends('pricelist_id', 'company_id')
    def _compute_currency_id(self):
        for order in self:
            if order.is_job_order:
                order.currency_id = order.currency_id.id or False         
            else:
                super()._compute_currency_id()

    def action_cancel(self):
        if any(rec.state == 'sale' and rec.invoice_ids.filtered(lambda x: x.state == 'posted') for rec in self):
            raise UserError(_("You cannot cancel in invoice posted state!"))
        if any(rec.state == 'sale' and rec.approved_by_id and rec.approved_by_id != self.env.user for rec in self):
            raise AccessError(_('You are not allowed to cancel!'))
        return super().action_cancel()

    def _action_cancel(self):
        if any(rec.state == 'sale' and rec.invoice_ids.filtered(lambda x: x.state == 'posted') for rec in self):
            raise UserError(_("You cannot cancel in invoice posted state!"))
        if any(rec.state == 'sale' and rec.approved_by_id and rec.approved_by_id != self.env.user for rec in self):
            raise AccessError(_('You are not allowed to cancel!'))
        return super()._action_cancel()
    
    def _prepare_job_order_lines(self, line):
        l_vals = {
                    'sequence':line.sequence,
                    'product_id':line.product_id.id,
                    'product_uom_qty':line.product_uom_qty,
                    'product_uom':line.product_uom.id,
                    'tax_id':line.tax_id.ids,
                    'discount':line.discount,
                    'name':line.name,
                    'price_unit': line.price_unit,
                    'inv_currency_id': line.inv_currency_id.id,
                    'categ_id': line.categ_id.id
                    }
        return l_vals
    
    def _prepare_job_order(self, jo_line_list, currency_id):
        vals = {
        'name': 'Draft',
        'partner_id':self.partner_id.id,
        'date_order': self.date_order,
        'warehouse_id': self.warehouse_id.id,
        'currency_id': currency_id,
        'order_line':jo_line_list,
        'so_id':self.id,
        'is_job_order': True,
        'approval_state': 'approved'
        }
        return vals        
        
    def action_create_job_order(self):
        self.ensure_one()
        currency_list = list(set(self.order_line.mapped('inv_currency_id').ids))
        for currency in currency_list:
            jo_line_list = []
            for line in self.order_line:
                if line.inv_currency_id and line.inv_currency_id.id == currency:
                    jo_line_list.append([0,0,self._prepare_job_order_lines(line)])
            
            jo_vals = self._prepare_job_order(jo_line_list, currency)     
            so = self.env['sale.order'].create(jo_vals)
        
    #action view job orders      
    # def action_view_job_orders(self):
    #     formview_ref = self.env.ref('sale.view_order_form', False)
    #     treeview_ref = self.env.ref('sale.view_order_tree', False)
    #     return {
    #         'name': ("Job Orders"),
    #         'view_mode': 'tree, form',
    #         'view_id': False,
    #         'res_model': 'sale.order',
    #         'type': 'ir.actions.act_window',
    #         'target': 'current',
    #         'domain': [('so_id', 'in', self.ids)],
    #         'views': [(treeview_ref and treeview_ref.id or False, 'tree'), (formview_ref and formview_ref.id or False, 'form')],
    #         'context': {'default_so_id': self.id}
    #     }    