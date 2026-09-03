Business Workflow Summary (Project Handover – CZT, 25-06-2026)
-------------------------

Technical Name: approval_extends → expense_template

1. Overview
========================================
   | Custom Petty Cash Voucher report for Odoo

2. Key Features
========================================
   | Professional Header
   |   - Company logo and "PETTY CASH VOUCHER" title
   |   - Draft watermark for non-approved documents
   |
   | Voucher Information
   |   - Petty Cash Number
   |   - Cash Advance Number
   |   - Petty Cash Date
   |   - Currency
   |   - Payment Type
   |
   | Vendor and Reference Details
   |   - Vendor Code
   |   - Vendor Name
   |   - Vendor Invoice Number
   |   - FMIS Job Number
   |   - FMIS Petty Cash Document Number
   |   - Document Location
   |   - Pay To Information
   |   - PR Number
   |   - PO Number
   |
   | Expense Line Items Table
   |   - Line Number
   |   - Description
   |   - Vehicle Number
   |   - Base Amount
   |   - Tax Rate
   |   - Tax Amount
   |   - Total Amount
   |   - Account Description (Analytic Distribution)
   |
   | Distribution Information
   |   - Displays product name under each expense line
   |   - Shows analytic/account distribution data from report method
   |   - Supports multiple distribution account display
   |
   | Amount Summary
   |   - Total Amount
   |   - Cash Advance Amount
   |   - Payable To / Receivable From amount
   |
   | Remark Section
   |   - Displays expense reason and additional notes
   |
   | Approval Workflow
   |   - Prepared By    (Request Owner)
   |   - PR Approved By (Purchase Request Latest Approver)
   |   - PO Approved By (Purchase Order Approver)
   |   - PC Approved By (Latest Approver)
   |
   | Footer Information
   |   - Company name
   |   - Document reference
   |   - Page numbering
   |   - Print timestamp

3. Report Structure
========================================
   | The report consists of three main templates:
   |
   | custom_header_footer_expense_form
   |   - Defines report header and footer layout
   |   - Handles watermark display
   |
   | expense_template
   |   - Main report content and expense data presentation
   |
   | expense_form_print
   |   - Container template that combines layout and report content

4. Usage
========================================
   | Used from approval.expense model
   | Supported Documents:
   |   - Petty Cash (Approval Expense Print)

5. Dependencies
========================================
   | Odoo Approval module
   | Custom approval_extends module
   | QWeb reporting engine

6. Installation
========================================
   | Ensure the approval_extends module is installed
   | Report templates are automatically registered upon module installation
   | No additional configuration required
