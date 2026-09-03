{
    'name' : 'Dynamic Approval Management KMTL',
    'summary': 'This module allows to manage dynamic approval requests',
    'version': '0.9',
    'license': 'LGPL-3',
    'description': """
            Inherit Approval Request module. 
            Add new approval types such as purchase request,expense,cash advance,payment request and po comparison to create approval
            Add dynamic approval configuration in approval type then check and approve by realative employee in approval request
            Modified in compute approver list based on dynamic approval configuration
            Some modified changes in new PO creation feature for Create RFQ type 
            Add custom reconciled process between vendor payment and approval request 
            """,
    'depends': ['base', 'approvals', 'approvals_purchase', 'hr', 'kmtl_customization', 
                'sale_job_order', 'purchase_extends', 'account_move_extends', 'user_by_department', 'account_accountant'],
    'data': [       
        'security/ir.model.access.csv',
        'security/ir_rules.xml', 
        'data/mail_activity_type_data.xml',
        'data/ir_sequence_data.xml',
        'views/purchase_view.xml',
        'views/stock_picking_view.xml',
        'views/approval_product_line_view.xml',
        'views/cash_advance_form_view.xml',
        'views/approval_request_view.xml',
        'views/approval_category_views.xml',
        'views/approval_expense_view.xml',
        'views/account_payment_views.xml',
        'views/approval_payment_request_view.xml',
        'views/view_move_form.xml',
        'views/account_move_line_view.xml',
        'views/po_comparison.xml',
        'views/po_comparison_menu.xml',
        'views/approval_process_config_view.xml',
        'wizards/partial_payment_wizard.xml',
        'wizards/view_expense_cancel.xml',
        'wizards/view_payment_request_cancel.xml',
        'wizards/view_cash_advance_cancel.xml',
        'wizards/view_purchase_request_cancel.xml',
        'reports/cash_advance_report_template.xml',
        'reports/menu_cash_advance_report.xml',
        'reports/payment_request_report_template.xml',
        'reports/menu_payment_request_report.xml',
        'reports/menu_clear_ca_report_from_pr.xml',
        'reports/clear_ca_report_template_from_pr.xml',
        'reports/approval_expense_report_template.xml',
        'reports/menu_expense_report.xml',
        'reports/clear_ca_report_template.xml',
        'reports/menu_clear_ca_report.xml',
        'reports/po_comparison_report_template.xml',
        'reports/menu_po_comparison_report.xml',
        'reports/approval_purchase_request_template.xml',
        'reports/menu_approval_purchase_request.xml',
        'wizards/view_reconcile_wizard.xml'
    ]
}


