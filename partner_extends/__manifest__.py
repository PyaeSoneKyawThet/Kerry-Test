# -*- coding: utf-8 -*-
{
    'name': 'Partner Extends',  
    'summary': 'Partner Extend Inherit',
    'license': 'LGPL-3',
    'version': '0.2',
    'description': """
            Inherit Partner Extend module. 
            Validate Unique Tax ID.
    """,  
    'depends': [        
        'base', 'contacts', 'account', 'kmtl_customization',
    ],
    'data' : [
        # 'data/ir_sequence_data.xml',
        'views/res_partner_views.xml',
        'security/ir_rules.xml',
    ]
    
    
}
