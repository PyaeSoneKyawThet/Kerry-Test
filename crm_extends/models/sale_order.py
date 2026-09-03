from odoo import fields, models, SUPERUSER_ID, _, api

class SaleOrder(models.Model):
    _inherit = 'sale.order'
    
    crm_ref = fields.Char(string="CRM Ref", copy=False)
    opportunity_ids = fields.Many2many('crm.lead', string="Opportunities", copy=False, domain="[('partner_id', '=', partner_id)]")
    commodity = fields.Char(string="Commodity", copy=False) 
    
    @api.depends('opportunity_ids')
    @api.onchange('opportunity_ids')
    def _onchange_opportunity_ids(self):
        for rec in self:
            commodity_ref = rec.opportunity_ids.filtered(lambda x: x.commodity != False).mapped('commodity')     
            rec.commodity = ",".join(commodity_ref)