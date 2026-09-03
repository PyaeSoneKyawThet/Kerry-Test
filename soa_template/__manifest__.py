# -*- coding: utf-8 -*-
{
    'name': "SOA Template",

    'summary': """
            Print Follow-up Reports.""",

    'description': """
        Print Partner's overdue invoices by PDF format.
    """,

    'author': "Zettatech",
    'website': "",
    'version': '0.1',
    # any module necessary for this one to work correctly
    'depends': ['base','contacts' ],
    # always loaded
    'data': [
        "reports/soa_template.xml",
        "reports/menu_soa_template.xml"
    ],
    # only loaded in demonstration mode
    'license': 'LGPL-3',
}