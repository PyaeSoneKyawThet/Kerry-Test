# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools, _
from odoo.osv import expression

class AssetReport(models.Model):
    _name = "asset.report"
    _inherit = 'analytic.mixin'
    _description = 'Asset Report'
    _auto = False

    # From Asset Form
    asset_name = fields.Char(string="Asset Name")
    depreciation_date = fields.Date(string="Depreciation Date", readonly=True)
    fixed_asset_account_id = fields.Many2one('account.account',string="Fixed Asset Account", readonly=True)
    depreciation_account_id = fields.Many2one('account.account',string="Depreciation Account", readonly=True)
    depreciation_expense_account_id = fields.Many2one('account.account',string="Expense Account", readonly=True)
    model_id = fields.Many2one('account.asset',string="Asset Category", readonly=True)
    asset_method = fields.Selection(
                        selection=[
                            ('linear', 'Straight Line'),
                            ('degressive', 'Declining'),
                            ('degressive_then_linear', 'Declining then Straight Line')
                        ],
                        string='Depreciation Method',
                        default='linear',
                        readonly=True
                    )
    method_period = fields.Selection([('1', 'Months'), ('12', 'Years')], string='Year or Month', default='12',help="Unit of duration.",readonly=True)
    staff_location_id = fields.Many2one('staff.location',string="Doc Location", readonly=True)
    employee_id = fields.Many2one('hr.employee',string="Asset User Name", readonly=True)
    department_id = fields.Many2one('hr.department',string="Department", readonly=True)
    prorata_date = fields.Date(string="Date In Service", readonly=True)

    model_serial_no = fields.Char(string="Model Serial No", readonly=True)
    lot_name = fields.Char(string="Fixed Asset (FA) Tag", readonly=True)
    old_fixe_asset = fields.Char(string="Old Fixed Asset", readonly=True)

    reference_seq = fields.Char(string="Asset Code Tagging", readonly=True)
    original_value = fields.Float(string="Original Cost",readonly=True, help="Asset form's original value as Original Cost.")
    duration = fields.Float(string="Duration",readonly=True)
    useful_life = fields.Float(string="Useful life(year)",readonly=True, help="Duration into year")
    depreciation_rate = fields.Float(string="Depreciation Rate", readonly=True) # 1/ useful_life * 100

    # From Bill Line
    account_move_line_id = fields.Many2one('account.move.line', string="Bill Line", readonly=True)
    move_id = fields.Many2one('account.move', string="AP Invoice Voucher No",readonly=True, help="Vendor bill no.")
    product_id = fields.Many2one('product.product',readonly=True,help="Vendor bill line's product.")
    description = fields.Char(string="Description", readonly=True)
    brand_id = fields.Many2one('purchase.brand', string="Brand Name", readonly=True)
    price_unit = fields.Float(string="Orginal Value",readonly=True, help="Vendor bill line unit_price.")

    # From Bill Form
    partner_id = fields.Many2one('res.partner',string="Vendor Name", readonly=True)
    bill_date = fields.Date(string="Vendor Invoice Date",readonly=True, help="Bill Date on vendor bill.")
    vendor_invoice_no = fields.Char(string="Vendor Invoice No", readonly=True)
    currency_rate = fields.Float(string="Currency Rate",readonly=True, help="Bill's currency rate")
    currency_id = fields.Many2one('res.currency', string="Currency",readonly=True)
    
    # From Journal
    depreciation_value = fields.Float(string="Depreciation", readonly=True)
    asset_remaining_value = fields.Float(string="Net Book Value",readonly=True, help="Journal's Depreciable Value")
    asset_depreciated_value = fields.Float(string="Accumulated Depreciation",readonly=True, help="Journal's Cumulative Depreciation")
    state = fields.Char(string="State",readonly=True)
    year_to_date = fields.Float(string="Year to Date") #calculation
    
    # Default
    quantity = fields.Float(string="Quantity", default=1, readonly=True)

    def init(self):
        tools.drop_view_if_exists(self._cr, 'asset_report')
        self._cr.execute("""
            CREATE or REPLACE view asset_report AS (
                SELECT   
                    am.id AS id,
                    asset.name AS asset_name,
                    am.date AS depreciation_date,
                    asset.account_asset_id AS fixed_asset_account_id,
                    asset.account_depreciation_id AS depreciation_account_id,
                    asset.account_depreciation_expense_id AS depreciation_expense_account_id,
                    asset.model_id AS model_id,
                    asset.method AS asset_method,
                    asset.staff_location_id AS staff_location_id,
                    asset.employee_id AS employee_id,
                    asset.department_id AS department_id,
                    asset.prorata_date AS prorata_date,
                    asset.model_serial_no AS model_serial_no,
                    asset.lot_name AS lot_name,
                    asset.old_fixe_asset AS old_fixe_asset,
                    asset.reference_seq AS reference_seq,
                    asset.analytic_distribution AS analytic_distribution,
                    asset.original_value AS original_value,
                    asset.method_number AS duration,
                    asset.method_period AS method_period,
                    
                    CASE
                        WHEN asset.method_period = '1' THEN CAST(asset.method_number AS float) / 12
                        WHEN asset.method_period = '12' THEN CAST(asset.method_number AS float)
                    END AS useful_life,
                    CASE
                        WHEN asset.method_period = '1' THEN  (1 / (CAST(asset.method_number AS float) / 12)) * 100 
                        WHEN asset.method_period = '12' THEN (1 / (CAST(asset.method_number AS float))) * 100 
                    END AS depreciation_rate,
                        
                    bill.id AS move_id,
                    bill.partner_id AS partner_id,
                    bill.vendor_invoice_no AS vendor_invoice_no,
                    bill.currency_rate AS currency_rate,
                    bill.date AS bill_date,
                    bill.currency_id AS currency_id,
                        
                    am.state AS state,
                    am.depreciation_value AS depreciation_value,
                    am.new_asset_remaining_value AS asset_remaining_value,
                    am.new_asset_depreciated_value AS asset_depreciated_value,
                    am.year_to_date AS year_to_date,
                    
                    aml.product_id AS product_id,
                    aml.name AS description,
                    aml.brand_id AS brand_id,
                    aml.price_unit AS price_unit,
                    1 AS quantity
                FROM account_move am
                JOIN account_asset asset on am.asset_id = asset.id
                LEFT JOIN account_move_line aml on asset.account_move_line_id = aml.id 
                LEFT JOIN account_move bill on aml.move_id = bill.id
            );
        """)

    def export_data(self, fields_to_export, **kwargs):
        data = super(AssetReport, self).export_data(fields_to_export, **kwargs)
        if 'analytic_distribution' in fields_to_export:
            field_index = fields_to_export.index('analytic_distribution')
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

   

        