{
    'name': 'KMTL Account Report',
    'summary': 'Custom left-aligned statement header for Profit & Loss / Balance Sheet (PDF & Excel).',
    'license': 'LGPL-3',
    'description': """
        Adds a "Custom Report Type" option (Profit & Loss / Balance Sheet /
        Standard Header) on account.report, so that Profit and Loss and
        Balance Sheet each get a left-aligned statement header on their PDF
        and Excel exports instead of the default Odoo report header:

        - Profit & Loss: STATEMENT OF INCOME DETAIL / FOR THE MONTH END <date>
        - Balance Sheet: STATEMENTS OF FINANCIAL POSITION - DETAIL / AS AT <date>

        The option is available on any account.report record (Accounting >
        Configuration > Accounting Reports, in developer mode), so other
        reports can opt into the same header style.
    """,
    'depends': ['account_reports', 'account', 'sale_job_order', 'kmtl_account_report_BU'],
    'data': [
        'security/ir.model.access.csv',
        'views/kmtl_reports_menu.xml',
        'views/report_templates.xml',
        'views/wizard_revenue_by_customer_views.xml',
        'views/wizard_received_money_by_customer_views.xml',
        'views/wizard_top_customers_views.xml',
        'views/wizard_yearly_revenue_comparison_views.xml',
        'views/wizard_quarterly_revenue_comparison_views.xml',
        'views/wizard_revenue_by_customer_bu_views.xml',
        'views/wizard_invoice_qty_by_bu_views.xml',
        'views/wizard_invoice_list_report_views.xml',
        'views/wizard_invoice_qty_by_customer_views.xml',
        'views/wizard_credit_note_list_report_views.xml',
        'views/wizard_receive_history_report_views.xml',
        'data/ar_invoice_tracking_state_data.xml',
        'views/wizard_ar_invoice_tracking_report_views.xml',
        'data/ap_invoice_tracking_state_data.xml',
        'views/wizard_ap_invoice_tracking_report_views.xml',
        # 'data/account_report_data.xml',
    ],
}
