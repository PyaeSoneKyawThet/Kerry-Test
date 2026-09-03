{
    'name': 'Custom SQL Reports',
    'version': '2.0',
    'summary': 'Custom SQL Reports',
    'description': """
    Custom SQL Reports
    
    1. Summary Sales Team Performance By Revenue Report
    2. Sale Team Performance By Actual Quantity
    3. Sale Team Performance By KPI Quantity
    4. Activity and Productivity Report
    5. Quotation Win / Loss Analysis Report
    6. Quotation Conversion Report
    7. Detail Sales Team Performance by Revenue
    8. Qty Of Revised Quotation
    9. Quotation Validity Report
    """,
    'author': "ZettatechMM",
    'category': 'Reporting',
    'website': "http://www.zettatechmm.com",
    'license': "LGPL-3",
    'depends': [
        'sale_job_order', #<- crm_extends
    ],
    'data': [        
        'security/ir.model.access.csv',
        'reports/sale_team_performance_wizard_view.xml',
        'reports/sale_team_performance_detail_view.xml',
        'reports/st_perf_by_actual_qty_view.xml',
        'reports/st_perf_by_kpi_qty_view.xml',
        'reports/quotation_won_lost_view.xml',
        'reports/activity_n_productivity_view.xml',
        'reports/quotation_conversion_view.xml',
        'reports/qty_revised_quotation_view.xml',
        'reports/quotation_validity_view.xml',
        'reports/quotation_validity_details_view.xml',
        'reports/quotation_pipeline_view.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}