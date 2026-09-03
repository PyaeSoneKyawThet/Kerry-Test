{
    'name': 'Approval Summary Report',
    'version': '0.2',
    'summary': 'Tracking Approval Summary Report',
    'depends': ['sale',
                'approval_extends' #<-- kmtl_customization
                ],
    'data': [
        "security/ir.model.access.csv",     
        "security/ir_rules.xml",     
        "views/approval_summary_report_view.xml" ,
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',   
}
