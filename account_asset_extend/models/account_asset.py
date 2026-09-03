from odoo import fields, models, api

class AccountAsset(models.Model):
    _inherit = 'account.asset'

    reference_seq = fields.Char(string="Reference")
    code = fields.Char(string="Code", copy=False)
    reference_sequence_id = fields.Many2one('ir.sequence', 'Reference Sequence', copy=False)
    employee_id = fields.Many2one('hr.employee', string='Employee', copy=False)
    department_id = fields.Many2one('hr.department', string='Department', copy=False)
    old_fixe_asset = fields.Char(string="Old Fixed Asset")
    picking_id = fields.Many2one('stock.picking', string='Receipt No', copy=False)
    product_id = fields.Many2one('product.product', string='Product', copy=False)
    location_dest_id = fields.Many2one('stock.location', string='Dest Location', copy=False)
    staff_location_id = fields.Many2one('staff.location', string='Doc Location', copy=False,)
    account_move_line_id = fields.Many2one('account.move.line', string='Bill No', copy=False)
    bill_date = fields.Date(string='Bill Date', copy=False)
    partner_id = fields.Many2one('res.partner', string='Partner', copy=False)
    available_bill_ids = fields.Many2many('account.move.line', string='Available Bills', compute='_compute_available_bill_ids')
    picking_id = fields.Many2one('stock.picking', string='Receipt No', copy=False)
    lot_name = fields.Char('Lot Name')
    model_serial_no = fields.Char(string="Model Serial No")

    def _get_disposal_moves(self, invoice_lines_list, disposal_date):
        move_ids = super()._get_disposal_moves(invoice_lines_list, disposal_date)
        for asset in self:
            related_moves = self.env['account.move'].search([
                ('asset_id', '=', asset.id),
                ('id', 'in', move_ids),
            ])
            for move in related_moves:
                move.staff_location_id = asset.staff_location_id.id
        return move_ids

    @api.onchange('picking_id')
    def _onchange_stock_picking(self):
        for rec in self:
            rec.location_dest_id = rec.picking_id.location_dest_id.id
            rec.staff_location_id = rec.picking_id.staff_location_id.id

    @api.onchange('employee_id')
    def _onchange_employee(self):
        for rec in self:
            rec.department_id = rec.employee_id.department_id.id

    @api.onchange('account_move_line_id')
    def _onchange_bill(self):
        for rec in self:
            rec.bill_date = rec.account_move_line_id.move_id.invoice_date
            rec.partner_id = rec.account_move_line_id.move_id.partner_id.id

    @api.depends('picking_id')
    def _compute_available_bill_ids(self):
        for rec in self:
            if rec.picking_id:
                # rec.available_bill_ids = self.env['account.move'].search([('id', 'in', rec.picking_id.purchase_order_id.invoice_ids.ids), ('state', '!=', 'cancel')]).ids
                invoice_ids = rec.picking_id.purchase_order_id.invoice_ids.filtered(lambda inv: inv.state != 'cancel')
                rec.available_bill_ids = self.env['account.move.line'].search([('move_id', 'in', invoice_ids.ids), ('display_type', '=', 'product')])
            else:
                bill_obj = self.env['account.move.line'].search([('move_id.move_type', '=', 'in_invoice'), ('move_id.state', '!=', 'cancel')])
                rec.available_bill_ids = bill_obj.ids
                

    def create_reference_sequence(self):
        asset_model_name = self.model_id.name
        asset_model_code = self.model_id.code or ""

        ir_sequence = self.env['ir.sequence'].create({
        'name': f'Sequence for {asset_model_name}',
        'code': f'sequence.asset.model.{asset_model_name}',
        'prefix': f'FFA-{asset_model_code}-%(y)s%(month)s',
        'padding': 3, 
        })
        self.model_id.reference_sequence_id = ir_sequence.id
    
    
    @api.model_create_multi
    def create(self, vals_list):
        recs = super().create(vals_list)
        for rec in recs:
            reference_seq = ""
            if rec.model_id:
                if not rec.model_id.reference_sequence_id:
                    rec.create_reference_sequence()
                reference_seq = rec.model_id.reference_sequence_id.next_by_id()

            rec.reference_seq = reference_seq 
        return recs

    def write(self, vals):
        res = super().write(vals)
        if 'model_id' in vals:
            for rec in self:
                reference_seq = rec.reference_seq
                if rec.model_id and not reference_seq:
                    if not rec.model_id.reference_sequence_id:
                        rec.create_reference_sequence()
                    reference_seq = rec.model_id.reference_sequence_id.next_by_id()
                rec.reference_seq = reference_seq
        return res