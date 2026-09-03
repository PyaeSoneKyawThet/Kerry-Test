{
    'name' : 'Sale Extends',
    'summary': 'Sale Customization',
    'license': 'LGPL-3',
    "version": "0.2",
    'description': """
            Inherit Sale module. 
            Add custom field on report.
    """,
    'depends' : ['base', 'hr', 'sale', 
                 'account_move_extends', # <-product_extend
                 'account', 'sale_management',
                 'crm_extends','web','product', ],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'data/mail_activity_type_data.xml',
        # 'views/product_category_view.xml',
        'views/view_employee_form.xml',
        'views/sale_order_template_view.xml',
        'wizard/reject_reason_wizard.xml', 
        'wizard/revise_reason_wizard.xml',
        'wizard/approval_reason_wizard.xml',
        'views/sale_order_views_inherit.xml',
        'reports/custom_sale_order_report.xml',
        'reports/sale_report.xml',                      
    ],
    "assets": {
        "web.assets_backend": [
            "sale_extends/static/src/**/*",
        ],
    },
}