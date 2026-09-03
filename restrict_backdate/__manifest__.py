{
    'name': "Sale, Purchase, Invoice Backdate",
    'summary': """Restrice backdate in Sale, Purchase, Invoice""",
    'description': """""",
    'author': "Zettatech Co.Ltd",
    'website': "http://www.zettatechmm.com",
    'category': 'Extra Tools',
    'version': '0.1',
    'depends': ['base', 'sale', 'purchase', 'account'],
    'data': [
        "views/res_config_settings_view.xml",
        "views/res_groups_view.xml",
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
}