# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class ApprovalCategory(models.Model):
    _inherit = 'approval.category'
    
    approval_type = fields.Selection(selection_add=[('purchase_req', 'Purchase Request'),
                                                    ('cash_advance', 'Cash Advance'),
                                                    ('expense', 'Expense'),
                                                    ('payment_request', 'Payment Request'),
                                                    ('po_comparison', 'PO Comparison')
                                                    ])
    
    approval_process_config_ids = fields.One2many('approval.process.config','approval_categ_id')
    visible_in_kanban = fields.Boolean(string="Visible in Kanban", default=False)
    
    @api.constrains('approval_type')
    def _check_unique_type(self):  
        if self.approval_type:
            domain = [('approval_type', 'in', ['purchase_req', 'cash_advance', 'expense'])]
            groupby = ['approval_type']
            records = self._read_group(domain, groupby, having=[('__count', '>', 1)])            
            error_message_lines = []        
            for name in records: 
                if name[0] == 'purchase_req':      
                    error_message_lines.append(_("%s Approval Type must be unique!", 'Purchase Request'))
                if name[0] == 'cash_advance':      
                    error_message_lines.append(_("%s Approval Type must be unique!", 'Cash Advance'))
                if name[0] == 'expense':      
                    error_message_lines.append(_("%s Approval Type must be unique!", 'Expense'))
            if error_message_lines:
                raise ValidationError(_(error_message_lines))