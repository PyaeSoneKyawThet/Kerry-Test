{
    'name' : 'KMTL Customization',
    'summary': 'Custom Models',
    'license': 'LGPL-3',
    'version': '0.1',
    'description': """
            
    """,
    'depends' : ['base', 'account'],
    'data': [
        'data/ir_sequence_data.xml',
        'security/ir.model.access.csv',
        'views/job_location_view.xml',
        'views/staff_location_view.xml',
        'views/brand_view.xml',
        'views/payment_type_view.xml',    
    ]
}