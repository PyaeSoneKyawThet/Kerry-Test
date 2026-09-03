{
    'name' : 'Account Payment Extends',
    'summary': 'Approval Payment Customization',
    'license': 'LGPL-3',
    'description': """
            Print payment
    """,
    'depends': ['base', 'account', 'kmtl_customization', 'account_move_extends'],
    'data': [      
       "data/ir_sequence_data.xml",
       "reports/menu_payment_report.xml",
       "reports/menu_receipt_voucher.xml",
       "reports/menu_payment_voucher.xml",
       "reports/payment_report.xml",
       "reports/receipt_voucher.xml",
       "reports/payment_voucher.xml",
       "views/account_payment_view.xml",
    ]
}


