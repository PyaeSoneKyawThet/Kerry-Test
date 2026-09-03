{
    'name' : 'Reverse Journal',
    'summary': 'Custom Models',
    'version': '0.1',
    'license': 'LGPL-3',
    'description': """
        1.This module automatically revise "Journal" base on reverse_date.
    """,
    'depends' : ['base', 
                 'account',
                 ],
    'data': [
        'data/ir_cron_data.xml',
        'views/account_move_view.xml',
    ]
}