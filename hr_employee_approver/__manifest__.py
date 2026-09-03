{
    'name' : 'Hr Employee Extends',
    'summary': 'Approver in Hr Employee',
    'license': 'LGPL-3',
    'version': '17.0.0.3',
    'author': 'ZettatechMM',
    'website': 'https://odoo.zettatechmm.com',
    'description': """
            Inherit Hr Employee module. 
            Add custom field for employee information. 
    """,
    'depends': ['base', 'hr', 'account', 'purchase', 'sale', 'approvals'],
    'data': [     
        'security/ir.model.access.csv',   
        'views/hr_employee_views.xml',
        'views/purchase_approval_config_view.xml',
        'views/purchase_approval_config_menu.xml',
        'views/payment_approval_config_view.xml'
    ]
}


