{
    'name' : 'KMTL Account Report By BU',
    'summary': 'Trial Balance Report with group by analytic distribution.',
    'license': 'LGPL-3',
    'description': """
            Inherit Account module. 
    """,
    'depends' : ['base', 'account', 'account_reports', 'analytic'],
    'data': [ 
        'security/ir.model.access.csv',
        'data/trial_balance_business_name.xml',
        'data/account_report_actions.xml',
        'data/menuitems.xml',
        'views/account_move_form.xml',
    ]
}