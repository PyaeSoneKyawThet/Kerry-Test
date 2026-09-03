
from odoo import fields, api, models , _

class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.model
    def has_address(self):
        for partner in self:
            address_fields = ('street', 'state_id')
            return all(partner[field] for field in address_fields)