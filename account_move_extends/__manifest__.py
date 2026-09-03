{
    'name' : 'Account Move Extends',
    'summary': 'Invoice Report Customize',
    'license': 'LGPL-3',
    'version': '0.8',
    'description': """
            Inherit Account module. 
            Add custom field on report.
    """,
    'depends' : ['base', 'account', 'sale' , 'base_extends', 'partner_extends', 
                'product_extend', 'hr_employee_extend', 'analytic', 'hr_employee_approver','account_batch_payment', 'account_accountant'],
    'data': [ 
        'security/ir.model.access.csv',
        'data/mail_activity_type_data.xml',
        'data/ir_sequence_data.xml',
        'wizard/view_account_reconcile_wizard.xml',
        'wizard/account_payment_register_view.xml',  
        'views/account_move_view.xml', 
        'views/account_journal_view.xml',
        'views/account_payment_veiw.xml',  
        'views/account_account_view.xml',
        'views/ar_invoice_detail_line_view.xml',
        'views/bank_rec_widget_view.xml',
        'wizard/account_move_reversal_view.xml', 
        'reports/ar_invoice_template.xml',
        'reports/menu_ar_invoice.xml',
        'reports/ap_invoice_template.xml',
        'reports/menu_ap_invoice.xml',
        'reports/journal_entry_template.xml',
        'reports/menu_journal_entry.xml'
    ]
}