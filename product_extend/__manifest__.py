# -*- coding: utf-8 -*-
{
    'name': 'Product Extends',  
    'summary': 'Product Extend Inherit',
    'license': 'LGPL-3',
    'description': """
            Inherit Product module. 
            Update Product Category Name
    """,  
    'depends': ['base', 'product', 'account'],
    'data' : [
        "views/product_view.xml",
        "views/product_category_view.xml",
]
    
    
}
