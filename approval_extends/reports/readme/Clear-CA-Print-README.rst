Business Workflow Summary (Project Handover – CZT, 25-06-2026)
-------------------------

Technical Name: approval_extends → clear_cash_advance_template

1. Overview
========================================
   | Custom Clear Cash Advance report for Odoo

2. Key Features
========================================
   | Professional Header
   |   - Company logo and "CLEAR CASH ADVANCE" title
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
   |   - Displays product information under expense lines
   |   - Shows analytic/account distribution details
   |   - Supports multiple account distribution display
   |
   | Amount Summary
   |   - Total Amount
   |   - Cash Advance Amount
   |   - Payable To / Receivable From calculation
   |   - Negative balance displayed with bracket format
   |
   | Approval Workflow
   |   - Prepared By
   |   - PR Approved By
   |   - PO Approved By
   |   - Clear CA Approved By
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
   | custom_header_footer_clear_cash_advance
   |   - Defines report header and footer layout
   |   - Handles watermark display
   |
   | clear_cash_advance_template
   |   - Main report content and settlement data presentation
   |
   | clear_ca_print
   |   - Container template that combines layout and report content

4. Usage
========================================
   | Used from approval.expense model
   | Supported Documents:
   |   - Clear Cash Advance (Clear CA Print)

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
