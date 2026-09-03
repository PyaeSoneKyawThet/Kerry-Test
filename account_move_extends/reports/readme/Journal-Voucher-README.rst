Business Workflow Summary (Project Handover – CZT, 25-06-2026)
-------------------------

Technical Name: account_move_extend → custom_journal_entry

1. Overview
========================================
   | Custom Journal Voucher report for Odoo

2. Key Features
========================================
   | Professional Header
   |   - Company logo and "JOURNAL VOUCHER" title
   |
   | Detailed Voucher Information
   |   - Description
   |   - Voucher Number
   |   - Exchange Rate
   |   - GL Date
   |   - Period
   |
   | Account Line Items Table
   |   - Account Code
   |   - Account Name
   |   - Original Amount
   |   - Debit and Credit amounts
   |   - Automatic totals calculation
   |
   | Distribution Information
   |   - Shows distribution account names from report data
   |   - Displays related account distribution under account name
   |
   | Currency Handling
   |   - Original Amount displayed in document currency
   |   - Debit/Credit shown in company currency
   |   - Exchange Rate displayed when applicable for multi-currency journal entries
   |   - Totals calculated and displayed in company currency
   |
   | Approval Workflow
   |   - Prepared By (creator name and submit date)
   |   - Checked By
   |   - Approved By
   |
   | Footer Information
   |   - Page numbering
   |   - Timestamp
   |   - Company footer image

3. Report Structure
========================================
   | The report consists of three main templates:
   |
   | custom_header_footer_journal_entry
   |   - Defines the header and footer layout
   |
   | custom_journal_entry
   |   - Main report content and data presentation
   |
   | journal_entry_print
   |   - Container template that combines header/footer with content

4. Usage
========================================
   | Used from account.move model
   | Supported Documents:
   |   - Journal Entries
   |   - General Ledger Vouchers
   |   - Manual Accounting Entries

5. Dependencies
========================================
   | Odoo Accounting module
   | Custom account_move_extends module
   | QWeb reporting engine

6. Installation
========================================
   | Ensure the account_move_extends module is installed
   | Report templates are automatically registered upon module installation
   | No additional configuration required
