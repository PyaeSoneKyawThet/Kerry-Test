from odoo import fields, api, models, _

class VASConfirmWizard(models.TransientModel):
    _name = 'wizard.vas.confirm'   
    _description ="Wizard Confirm VAS"

    sale_order_id = fields.Many2one('sale.order', string="Sale Order", required=True)

    def action_confirm(self):
        self.ensure_one()
        sale_order = self.sale_order_id
        is_vas = True
        new_so_vals = {
            'partner_id': sale_order.partner_id.id,
            'original_so_id': sale_order.id,
            'is_vas': is_vas,
            'state': 'draft',   
        }
        sequence = self.env['ir.sequence'].next_by_code('vas.sale.order')
        new_so_vals['name'] = "{}".format(str(sequence))   
        new_so = self.env['sale.order'].create(new_so_vals)
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'res_id': new_so.id, 
            'view_mode': 'form',
            'target': 'current',
        }

    def action_cancel(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'res_id': self.sale_order_id.id, 
            'view_mode': 'form',
            'target': 'current',
        }