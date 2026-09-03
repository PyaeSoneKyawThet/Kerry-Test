# -*- coding: utf-8 -*-
{
    'name': 'Stock Extends',  
    'summary': 'Stock Inherit',
    'license': 'LGPL-3',
    'description': """
        Inherit Stock module to add document_location in scrap.
    """,  
    'depends': ['base', 
                'stock',
                'kmtl_customization'
                ],
    'data' : [
        'views/stock_scrap_view.xml',
    ],
    
}