{
    'name' : 'CRM Extends',
    'summary': 'CRM Lead Customization',
    'license': 'LGPL-3',
    'version': '0.2',
    'description': """
            Inherit CRM Lead module. 
            Add custom field 'currency_id' to adjust the 'expected_revenue'.
            Generate Sequence for CRM Ref
    """,
    'depends' : ['base', 'mail', 'crm', 'sale_crm', 'partner_extends', 'crm_iap_mine'],
    'data': [
        'security/ir.model.access.csv',
        'security/ir_rules.xml',
        'data/ir_sequence_data.xml',
        'data/ir_cron.xml',
        'views/mail_activity_type_view.xml',
        'views/res_company_view.xml',
        'views/crm_stage_view.xml',
        'views/customer_forecast_revenue_view.xml',
        'views/crm_lead_view.xml',
        'views/crm_industry_view.xml',
        'views/crm_unit_view.xml',
        'wizard/select_partner_wiz.xml',
        'wizard/sale_forecast_report_wizard_view.xml',
        'views/crm_menu_view.xml',
        'views/sale_order_view.xml',
        'reports/crm_report_view.xml',
        'reports/sale_pipeline_wizard.xml',
    ]
}


