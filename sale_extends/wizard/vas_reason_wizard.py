from odoo import fields, api, models, _

class VASReason(models.TransientModel):
    _name = 'wizard.vas.reason'   
    _description ="Wizard VAS Reason"

    sale_order_id = fields.Many2one('sale.order', string='Sale order', required=True)
    state = fields.Selection([('vas_requested', 'Requested'), 
                            ('vas_approved', 'Approved'), 
                            ('vas_rejected', 'Rejected')], default='') 
    reason = fields.Text(string="Reason")    
        
    def _prepare_new_order_lines(self, line):
        l_vals = {
                'sequence':line.sequence,
                'product_id':line.product_id.id,
                'product_uom_qty':line.product_uom_qty,
                'product_uom':line.product_uom.id,
                'tax_id':line.tax_id.ids,
                'discount':line.discount,
                'name':line.name,
                'price_unit': line.price_unit,
                'inv_currency_id': line.inv_currency_id.id,
                'categ_id': line.categ_id.id,
                }
        return l_vals
    
    def _prepare_new_order(self, order_id, so_line_list):
        vals = {
                'partner_id': order_id.partner_id.id,
                'date_order': order_id.date_order,
                'warehouse_id': order_id.warehouse_id.id,
                'currency_id': order_id.currency_id.id,
                'order_line': so_line_list,
                'original_so_id': order_id.id,
                'category_ids': order_id.category_ids.ids,
                'category_note': order_id.category_note,
                'note': order_id.note,
                'sale_order_template_id': order_id.sale_order_template_id.id,
                'state': 'draft'
                }
        return vals        
        
    def action_create_new_order(self):
        self.ensure_one()
        so_line_list = []
        for line in self.sale_order_id.order_line:
            so_line_list.append([0,0,self._prepare_new_order_lines(line)])        
        so_vals = self._prepare_new_order(self.sale_order_id, so_line_list)  
        sequence = self.env['ir.sequence'].next_by_code('vas.sale.order')
        so_vals['name'] = "{}".format(str(sequence))   
        return self.env['sale.order'].create(so_vals)
        
    def action_confirm(self):
        self.sale_order_id.vas_state = self.state
        self.env['vas.reason'].create({
            'so_id': self.sale_order_id.id,
            'reason': self.reason,
            'state': self.state
        })
        if self.state == 'vas_approved':
            new_so = self.action_create_new_order() 
            # self.sale_order_id.VAS_count += 1
            # if len(str(self.sale_order_id.VAS_count)) > 1:
            #     new_so.name = "{}/{}{}".format(new_so.name,'RV', self.sale_order_id.VAS_count)  
            # else:
            #     new_so.name = "{}/{}{}{}".format(new_so.name, 'RV', str(0), self.sale_order_id.VAS_count)  
                