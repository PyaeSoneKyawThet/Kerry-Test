from odoo import models, api, _


class MailActivity(models.Model):
    _inherit = 'mail.activity'
    
    @api.depends('res_model', 'res_id', 'user_id')
    def _compute_can_write(self):
        valid_records = self._filter_access_rules('write')
        activity_type_approval_id = self.env.ref('sale_extends.mail_activity_data_kmtl').id
        for record in self:
            if record.res_model == 'sale.order' and  record.activity_type_id.id == activity_type_approval_id:
                record.can_write = False
            else:
                record.can_write = record in valid_records
