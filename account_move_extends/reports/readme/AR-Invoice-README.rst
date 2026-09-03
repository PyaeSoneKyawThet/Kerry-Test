Business Workflow Summary (Project Handover – CZT, 25-06-2026)
-------------------------

Technical Name: account_move_extend → custom_ar_invoice

1. Overview
========================================
   | Custom AR Invoice Voucher report for Odoo

2. Key Features
========================================
   | Professional Header
   |   - Company logo and "AR INVOICE VOUCHER" title
   |
   | Detailed Voucher Information
   |   - Invoice Number
   |   - Customer Code
   |   - Customer Name
   |
   | Invoice Details
   |   - Payment Terms
   |   - Currency and Exchange Rate
   |   - Invoice Date, Due Date, and GL Date
   |
   | Account Line Items Table
   |   - Account Code
   |   - Account Name
   |   - Invoice Amount
   |   - Debit and Credit amounts
   |   - Automatic totals calculation(company currency sign)
   |
   | Distribution Information
   |   - Shows distribution account names from report data
   |   - Displays related account distribution under account name
   |
   | Applied Prepaid Section
   |   - Separate table for deferred/prepaid account entries (when applicable)
   |   - Automatically detects lines with deferred accounts
   |   - Shows "Applied Prepaid:" header when present
   |   - Displays deferred account code, name, invoice amount, debit, and credit
   |
   | Currency Handling
   |   - Invoice Amount displayed in document currency
   |   - Debit/Credit shown in company currency
   |   - Exchange Rate displayed when applicable for multi-currency invoices
   |   - Totals calculated and displayed in company currency
   |
   | Approval Workflow
   |   - Prepared By (submitter name and date)
   |   - Checked By  (latest checker or approver)
   |   - Approved By (latest approver)
   |
   | Footer Information
   |   - Company name
   |   - Document reference
   |   - Page numbering
   |   - Timestamp

3. Report Structure
========================================
   | The report consists of three main templates:
   |
   | custom_header_footer_ar_invoice
   |   - Defines the header and footer layout
   |
   | custom_ar_invoice
   |   - Main report content and data presentation
   |
   | ar_invoice_print
   |   - Container template that combines header/footer with content

4. Usage
========================================
   | Used from account.move model
   | Supported Documents:
   |   - Customer Invoice (move_type = out_invoice)
   |   - Customer Credit Note / Customer Refund (move_type = out_refund)

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
