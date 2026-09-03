from odoo import fields, api, models , _

class ResPartner(models.Model):
    _inherit = 'res.partner'  

    def _get_unpaid_invoices(self):
        records = self.env['account.move'].search([('id', 'in', self.unpaid_invoice_ids.ids)])
        invoice_grouped_data = {}

        for record in records:
            currency_name = record.currency_id.name
            if currency_name not in invoice_grouped_data:
                invoice_grouped_data[currency_name] = []
            invoice_grouped_data[currency_name].append(record)
        
        return invoice_grouped_data