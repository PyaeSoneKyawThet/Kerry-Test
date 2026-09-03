from odoo import fields, api, models , _

class ResCompany(models.Model): 
    _inherit = 'res.company'  

    company_footer = fields.Binary(string="Company Footer") 
    company_footer_text = fields.Text(string="Company Footer Text") 
    invoice_footer = fields.Binary(string="Invoice Footer") 
    

  