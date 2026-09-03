{
    'name' : 'Purchase Order Extends',
    'summary': 'Purchase Order Customize',
    'version': '0.3',
    'license': 'LGPL-3',
    'description': """Purchase Extension""",
    'depends' : ['base', 'account', 'purchase', 'kmtl_customization', 'stock', 'purchase_stock', 'hr_employee_approver'],
    'data': [  
        'data/mail_activity_type_data.xml',
        'views/purchase_view.xml',
        'views/brand_menu.xml',
        'reports/purchase_report.xml',
        'reports/custom_purchase_order.xml',
        'views/stock_picking_view.xml',
        'views/stock_move_line_view.xml',
    ]
}