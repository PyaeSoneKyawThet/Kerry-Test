from odoo import fields, api, models , _
from odoo.exceptions import ValidationError

class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    def _prepare_picking(self):
        vals = super(PurchaseOrder, self)._prepare_picking()
        vals['staff_location_id'] = self.staff_location_id.id
        return vals


