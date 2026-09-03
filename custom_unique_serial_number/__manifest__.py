# -*- coding: utf-8 -*-
{
    'name': 'Stock Extends',  
    'summary': 'Stock Inherit',
    'license': 'LGPL-3',
    'description': """
        Inherit Stock module to add document_location in receipt.
    """,  
    'depends': ['base', 
                'product',
                'stock',
                'purchase_extends' # <-- kmtl_customization
                ],
    'data' : [
        'data/ir_sequence.xml',
        'views/product_view.xml',
        'views/stock_picking_view.xml',
        'views/stock_move_line_view.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'custom_unique_serial_number/static/src/js/generate_serial.js',
        ],
    }
    
}