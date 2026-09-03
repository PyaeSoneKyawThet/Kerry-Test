from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError

class PurchaseOrder(models.Model):
    _inherit = "purchase.order" 

    approval_request_ids = fields.Many2many('approval.request', 'purchase_id', 'approval_request_id', 'purchase_approval_request_rel', string='Approval Request')
    rfq_id = fields.Many2one('approval.request', string="RFQ No.", domain=[('approval_type','=','purchase'), ('request_status', '=', 'approved')])    
    pay_to_id = fields.Many2one('hr.employee', string="Pay To Employee")
    pay_to_external = fields.Char(string="Pay To External")
    value_date = fields.Date(string="Value Date")
    purchase_request_no = fields.Many2one('approval.request', string="Purchase Request No.", 
                                        domain=[('approval_type', '=', 'purchase_req'),('request_status', '=', 'approved')]) 
    original_purchase_order_id = fields.Many2one('purchase.order', string="Original PO")
    revised_po_count = fields.Integer(string="No of Revised PO", compute="_compute_revised_po_count")

    @api.depends('original_purchase_order_id')
    def _compute_revised_po_count(self):
        for rec in self:
            rec.revised_po_count = self.env['purchase.order'].search_count([('original_purchase_order_id','=',rec.id)]) or 0

    def _prepare_revise_po_vals(self):
        """prepare dictionary value to create revise purchase order"""
        l_vals = []      
        for line in self.order_line: 
            l_vals.append([0,0,{
                        'purchase_request_line_id': line.purchase_request_line_id.id,
                        'product_id' : line.product_id.id,
                        'name' : line.name,
                        'brand_id': line.brand_id.id,
                        'vehicle_no': line.vehicle_no,
                        'bl_no': line.bl_no,
                        'reference_key': line.reference_key,
                        'product_qty': line.product_qty,
                        'product_packaging_qty': line.product_packaging_qty,
                        'product_packaging_id': line.product_packaging_id.id,
                        'price_unit': line.price_unit,
                        'taxes_id': line.taxes_id.ids,
                        }])
            
        vals = { 'original_purchase_order_id' : self.id,
                 'partner_id': self.partner_id.id,
                 'vendor_quotation_no': self.vendor_quotation_no,
                 'vendor_invoice_no': self.vendor_invoice_no,
                 'rfq_id': self.rfq_id.id,
                 'currency_id': self.currency_id.id,
                 'prepared_department_id': self.prepared_department_id.id,
                 'staff_location_id': self.staff_location_id.id,
                 'vendor_quotation_date': self.vendor_quotation_date,
                 'payment_term_id': self.payment_term_id.id,
                 'date_planned': self.date_planned,
                 'picking_type_id': self.picking_type_id.id,
                 'value_date': self.value_date,
                 'pay_to_id': self.pay_to_id.id,
                 'pay_to_external': self.pay_to_external,
                 'order_line' : l_vals,
                } 
        return vals
    
    def action_view_revised_po(self):
        revised_purchase_ids = self.env['purchase.order'].search([('original_purchase_order_id','=',self.id)])
        result = {
                "type": "ir.actions.act_window",
                "res_model": "purchase.order",
                "domain": [('id', 'in', revised_purchase_ids.ids)],
                "name": ("Purchase Order"),
                'view_mode': 'tree,form', 
            }
        if len(revised_purchase_ids)==1:
            result.update({
                'res_id':revised_purchase_ids.id,
                'view_mode':'form', 
                })
        return result 

    def action_revise(self):
        # Get all approval lines linked to the current PO lines
        approval_line_map = {}
        for line in self.order_line:
            linked_approvals = self.env['approval.product.line'].search([
                ('purchase_order_line_id', '=', line.id)
            ])
            if linked_approvals:
                approval_line_map[line.product_id.id] = linked_approvals

        # Cancel the old PO
        self.button_cancel()
        self.env['approval.payment.request'].search([('purchase_order_id','=',self.id)]).action_cancel()

        # Create new PO
        vals = self._prepare_revise_po_vals()
        revised_purchase_order = self.env['purchase.order'].create(vals)

        # Re-link approval lines to new PO lines
        for new_line in revised_purchase_order.order_line:
            linked_approvals = approval_line_map.get(new_line.product_id.id)
            if linked_approvals:
                for approval_line in linked_approvals:
                    approval_line.purchase_order_line_id = new_line.id

        return {
            'type': 'ir.actions.act_window',
            'name': _('Revised Purchase Order'),
            'res_model': 'purchase.order',
            'view_mode': 'form',
            'res_id': revised_purchase_order.id,
            'target': 'current',
        }

    
    def action_view_revised_po(self):
        revised_purchase_ids = self.env['purchase.order'].search([('original_purchase_order_id','=',self.id)])
        result = {
                "type": "ir.actions.act_window",
                "res_model": "purchase.order",
                "domain": [('id', 'in', revised_purchase_ids.ids)],
                "name": ("Purchase Order"),
                'view_mode': 'tree,form', 
            }
        if len(revised_purchase_ids)==1:
            result.update({
                'res_id':revised_purchase_ids.id,
                'view_mode':'form', 
                })
        return result 