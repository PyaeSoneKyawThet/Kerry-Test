from odoo import fields, api, models, _

class PartnerSelect(models.TransientModel):
    _name = 'wizard.select.partner'   
    _description ="Wizard Partner Select"

    crm_ids = fields.Many2many('crm.lead', string='CRM', required=True)
    partner_id = fields.Many2one('res.partner',string="Customer")    
        
    def action_confirm(self):
        self.crm_ids._create_order_quotation(self.partner_id.id)