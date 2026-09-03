from odoo import fields, api, models
from datetime import date, timedelta

class StockPicking(models.Model):    
    _inherit = "stock.picking"

    purchase_order_id = fields.Many2one('purchase.order',string="Purchase Order",copy=False)
    # remove in task: 6189
    # purchase_request_no = fields.Many2one('approval.request', string="Purchase Request No.", copy=False)
    prepared_by_id = fields.Many2one(string='Prepared by', comodel_name='res.users',  copy=False, store=True,)
    prepared_department_id = fields.Many2one('hr.department', string="Prepared Department", related="prepared_by_id.employee_id.department_id")
    vendor_invoice_no = fields.Char(string="Vendor Invoice No")
    receipt_by_id = fields.Many2one(string='Receipt by', comodel_name='res.users', copy=False, store=True,)
    receipt_department_id = fields.Many2one('hr.department', string="Receipt Department", related="receipt_by_id.employee_id.department_id")
    delivery_date = fields.Date(string="Delivery Date")
    is_from_po = fields.Boolean(string="Is From PO", default=False, store=True, copy=False)

    def _create_backorder_picking(self):
        vals = super()._create_backorder_picking()
        vals.update({
            'purchase_order_id': self.purchase_order_id.id,
            'is_from_po': self.is_from_po,
            'vendor_invoice_no': self.vendor_invoice_no,
            'delivery_date': self.delivery_date,
            'prepared_by_id': self.prepared_by_id.id,
            'prepared_department_id': self.prepared_department_id.id,
            'receipt_by_id': self.receipt_by_id.id,
            'receipt_department_id': self.receipt_department_id.id,
            'owner_id': self.owner_id.id,
            'picking_type_id': self.picking_type_id.id,
        })
        return vals

