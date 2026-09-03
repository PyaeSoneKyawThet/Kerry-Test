from odoo import api, fields, models, _
from odoo.exceptions import UserError


class Picking(models.Model):
    _inherit = 'stock.picking'

    def if_split(self, vals):
        """
        condition to check whether to split picking contrast to odoo default merge
        """
        location_id = self.env['stock.location'].sudo().search([('id', '=', vals.get('location_dest_id'))])
        # defaults = self.default_get(['name', 'picking_type_id'])
        # picking_type = self.env['stock.picking.type'].browse(vals.get('picking_type_id', defaults.get('picking_type_id')))
        if location_id.usage == 'transit':
            return True
        return False

    @api.model_create_multi
    def create(self, vals_list):
        """
        Handle batch creation with support for procurement.group splitting,
        correct move values, and picking sequence naming.
        """
        res_list = []

        for vals in vals_list:
            defaults = self.default_get(['name', 'picking_type_id'])
            picking_type_id = vals.get('picking_type_id', defaults.get('picking_type_id'))
            picking_type = self.env['stock.picking.type'].browse(picking_type_id)

            if vals.get('name', '/') == '/' and defaults.get('name', '/') == '/' and picking_type_id:
                if picking_type.sequence_id:
                    vals['name'] = picking_type.sequence_id.next_by_id()

            moves = vals.get('move_lines', []) + vals.get('move_ids', []) + vals.get('move_ids_without_package', [])
            if moves and vals.get('location_id') and vals.get('location_dest_id'):
                for move in moves:
                    if len(move) == 3 and move[0] == 0:
                        move[2]['location_id'] = vals['location_id']
                        move[2]['location_dest_id'] = vals['location_dest_id']
                        if 'picking_type_id' not in move[2] or move[2]['picking_type_id'] != picking_type.id:
                            move[2]['picking_type_id'] = picking_type.id
                            move[2]['company_id'] = picking_type.company_id.id

            scheduled_date = vals.pop('scheduled_date', False)

            # Custom split logic
            if self.if_split(vals):
                if not moves and 'location_dest_id' in vals and self.location_id != vals.get('location_dest_id'):
                    raise UserError(_('Please select product.'))
                group_id = self.env['procurement.group'].create({'name': vals['name']})
                vals['group_id'] = group_id.id
                for move in moves:
                    if len(move) == 3 and move[0] == 0:
                        move[2]['group_id'] = group_id.id

        # Now actually create all pickings
        res = super(Picking, self).create(vals_list)

        # post-processing (like scheduled_date or followers)
        for picking, vals in zip(res, vals_list):
            if vals.get('scheduled_date'):
                picking.with_context(mail_notrack=True).write({'scheduled_date': vals['scheduled_date']})

            if self.if_split(vals):
                picking = picking.with_context(default_picking_id=picking.id)

            if vals.get('partner_id') and (picking.location_id.usage == 'supplier' or picking.location_dest_id.usage == 'customer'):
                picking.message_subscribe([vals.get('partner_id')])

        return res

