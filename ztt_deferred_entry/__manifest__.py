{
    'name' : 'Deferred Entries Extend',
    'summary': 'Custom Models',
    'version': '0.1',
    'license': 'LGPL-3',
    'description': """
        1.This module allows to create 'Deferred Entries'
        with the custom deferred account 
        in bill and invoice line.
        2.Show deferred and depreciated value as columns in Invoice/Bill Line by multi currency
    """,
    'depends' : ['base', 
                 'account',
                 'account_accountant',
                 'approval_extends' #<-- account_move_extends
                 ],
    'data': [
        'views/account_move_view.xml'
    ]
}