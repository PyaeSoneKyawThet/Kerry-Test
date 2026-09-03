from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

#update staff location to document location
class DocumentLocation(models.Model):
    _name = 'staff.location'
    _description = 'Document Location'

    code = fields.Char(string="Code")
    name = fields.Char(string="Name", required=True) 
    remark = fields.Text(string="Remark")
    expense_journal_ids = fields.Many2many('account.journal', string="Expense Journal")

    document_location_line_ids = fields.One2many('document.location.line','staff_location_id',string="Document Location Lines")
    
    def get_seq_number(self,type):
        for rec in self:
            if type:
                operation_type_id = self.env['document.location.line'].search([('staff_location_id', '=', self.id), ('operation_type', '=', type)], limit=1)
                if not operation_type_id or not operation_type_id.sequence_id or not operation_type_id.staff_location_prefix:
                    raise UserError(_("Please Define Sequence IN %s", rec.name))
                
                prefix = operation_type_id.staff_location_prefix
                seq = operation_type_id.sequence_id.next_by_id()
                name = prefix + "{}".format(str(seq))
            else:
                name = ''
            return name

class DocumentLocationLine(models.Model):
    _name = 'document.location.line'
    _description = 'Document Location Lines'

    staff_location_id = fields.Many2one('staff.location')
    staff_location_prefix = fields.Char(string="Prefix")
    operation_type = fields.Selection([('job_order', 'Job Order'), 
                                       ('invoice', 'Invoice'), 
                                       ('credit_note', 'Invoice Credit Note'), 
                                       ('official_receipt', 'Official Rreceipt'),
                                       ('vendor_bill', 'Vendor Bill'),
                                       ('petty_cash', 'Petty Cash'),
                                       ('petty_cash_with_ca', 'Petty Cash With CA'),
                                       ('cash_advance', 'Cash Advance'),
                                       ('internal_credit_note', 'Internal Credit Note'),
                                       ('debit_note', 'Debit Note'),
                                       ('internal_debit_note', 'Internal Debit Note'),
                                       ('petty_cash_debit_note', 'Petty Cash Debit Note'),
                                       ('fixed_asset', 'Fixed Asset'),
                                       ],string="Operation Type", required=True)
    sequence_id = fields.Many2one('ir.sequence', string="Sequence")

