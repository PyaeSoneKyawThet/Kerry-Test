# Copyright 2019 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Account Asset Extend",
    "summary": """
            Add: model_serial_no in PO
            To: receipt, detail operation asset form
        """,
    'category': 'account',
    "version": "0.1",
    "license": "AGPL-3",
    "author": "zettatech",
    "depends": ['base', 'account', 'analytic', 'account_asset', 'stock', 'hr', 'kmtl_customization','purchase'],
    "data": [
        "security/ir.model.access.csv",     
        "reports/asset_report_view.xml",
        "views/account_asset.xml",
        "views/product_view.xml",
        "views/stock_move_line_view.xml",
        "views/purchase_view.xml",
        "views/stock_picking_view.xml",
    ],
    "installable": True,
    "auto_install": False, 
}
