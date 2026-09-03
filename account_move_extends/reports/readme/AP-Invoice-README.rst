Business Workflow Summary (Project Handover – CZT, 25-06-2026)
-------------------------

Technical Name: account_move_extend → custom_ap_invoice

1. Overview
========================================
   | Custom AP Invoice Voucher report for Odoo

2. Key Features
========================================
   | Professional Header
   |   - Company logo and "AP INVOICE VOUCHER" title
   |
   | Detailed Voucher Information
   |   - Voucher Number
   |   - Description
   |   - Vendor Name
   |
   | Invoice Details
   |   - Vendor Invoice Number
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
   |   - Displays account code, name, invoice amount, debit, and credit for prepaid entries
   |
   | Currency Handling
   |   - Invoice Amount displayed in document currency 
   |   - Debit/Credit shown in company currency 
   |   - Exchange Rate displayed when applicable for multi-currency invoices
   |   - Totals calculated and displayed in company currency
   |
   | Approval Workflow
   |   - Prepared By (with submitter name and date)
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
   | custom_header_footer_ap_invoice
   |   - Defines the header and footer layout
   |
   | custom_ap_invoice
   |   - Main report content and data presentation
   |
   | ap_invoice_print
   |   - Container template that combines header/footer with content

4. Usage
========================================
   | Used from account.move model
   | Supported Documents:
   |   - Vendor Bill (move_type = in_invoice)
   |   - Vendor Credit Note / Vendor Refund (move_type = in_refund)

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







