from odoo import models
 
class SaleOrder(models.Model):
    _inherit = "sale.order"
 
    def export_data(self, fields_to_export, **kwargs):
        data = super(SaleOrder, self).export_data(fields_to_export, **kwargs)
        if 'order_line/analytic_distribution' in fields_to_export:
            field_index = fields_to_export.index('order_line/analytic_distribution')
            for record in data['datas']:
                analytic_dist = record[field_index]
                if analytic_dist:
                    try:
                        analytic_dist_dict = eval(analytic_dist)
                        analytic_ids = [int(k) for key in analytic_dist_dict.keys() for k in key.split(',')]
                        analytic_accounts = self.env['account.analytic.account'].browse(analytic_ids)
                        analytic_names = analytic_accounts.mapped('name')
 
                        record[field_index] = analytic_names
                    except Exception:
                        record[field_index] = analytic_dist
        return data