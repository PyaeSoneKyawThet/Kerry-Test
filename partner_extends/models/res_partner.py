from odoo import fields, api, models , _
from odoo.exceptions import UserError, ValidationError

class ResPartner(models.Model):
    _inherit = 'res.partner'  

    contact_person = fields.Char(string="Contact Person") 
    sale_pic_ids = fields.Many2many("res.users", string="Sales PIC")
    type_id = fields.Many2one('account.payment.type',string="Type")

    property_account_receivable_id = fields.Many2one('account.account', company_dependent=True,                                                  
        string="Account Receivable", 
        domain="[('account_type', '=', 'asset_receivable'), ('deprecated', '=', False)]",
        help="This account will be used instead of the default one as the receivable account for the current partner",
        required=True, 
        default=False       
        )
    
    property_account_payable_id = fields.Many2one('account.account', company_dependent=True,
        string="Account Payable",
        domain="[('account_type', '=', 'liability_payable'), ('deprecated', '=', False)]",
        help="This account will be used instead of the default one as the payable account for the current partner",
        required=True,
        default=False )
    
    vendor_bank_info = fields.Char(string="Bank Info")
  
    @api.constrains('vat')
    def _check_unique_vat(self):  
        if self.vat:
            domain = [('vat', 'in', self.mapped('vat'))]
            groupby = ['vat']
            records = self._read_group(domain, groupby, having=[('__count', '>', 1)])            
            error_message_lines = []        
            for name in records:          
                    error_message_lines.append(_("Tax ID %s must be unique!", name[0]))
            if error_message_lines:
                raise ValidationError(_(error_message_lines))

    @api.constrains('name')
    def _check_unique_name(self):  
        if self.name:
            domain = [('name', 'in', self.mapped('name'))]
            groupby = ['name']
            records = self._read_group(domain, groupby, having=[('__count', '>', 1)])            
            error_message_lines = []        
            for name in records:          
                    error_message_lines.append(_("Name %s must be unique!", name[0]))
            if error_message_lines:
                raise ValidationError(_(error_message_lines))
    

    # create sequence number with Name
    @api.model_create_multi
    def create(self, vals):              
        for val in vals:
            if self.env.context.get('create_new_contact'):
                name = val.get('name', '').replace(" ", "")
                prefix = name[:2].upper() if name else 'XX'
                sequence = self.env['ir.sequence'].next_by_code('partner.reference.sequence')
                ref_number = "{}{}".format(prefix, str(sequence))
                val['ref'] = ref_number
        return super(ResPartner, self).create(vals)
    
    # update sequence number with name
    @api.model
    def write(self, vals):
        if self.env.context.get('create_new_contact'):
            if 'name' in vals and self.ref:
                name = vals['name'].replace(" ", "")
                prefix = name[:2].upper()
                sequence = self.ref[2:]
                vals['ref'] = "{}{}".format(prefix, str(sequence))      

        return super(ResPartner, self).write(vals)
    
   