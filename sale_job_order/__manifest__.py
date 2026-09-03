{
    'name' : 'Job Order',
    'summary': 'Job Order Creation',
    'license': 'LGPL-3',
    'description': """
            Add new Job Order after SO creation.
    """,
    'depends' : [ 'base', 'sale', 'sale_extends', 'sale_stock', 'crm_extends', 'kmtl_customization', 'account', 'partner_extends', 
                'user_by_department'],
    'data': [
        'data/ir_sequence_data.xml',
        'security/ir_rules.xml',
        'views/job_order_view.xml',
        'views/job_order_menu.xml',  
        'views/sale_order_view.xml',
        'views/sale_order_menu_views.xml',
        'views/view_move_form.xml',
        'reports/custom_job_order_report.xml',
        'reports/job_order_report.xml',
        'reports/custom_report_invoice.xml',      
        'reports/account_report.xml',
    ]
}
