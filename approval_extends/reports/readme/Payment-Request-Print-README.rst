Business Workflow Summary (Project Handover – CZT, 25-06-2026)
-------------------------

Technical Name: approval_extends → payment_request_template

1. Overview
========================================
   | Custom Payment Request report for Odoo

2. Key Features
========================================
   | Professional Header
   |   - Company logo and "PAYMENT REQUEST" title
   |   - Draft watermark for non-approved documents
   |
   | Payment Request Information
   |   - Payment Request Number
   |   - Payment Request Date
   |   - Value Date
   |   - Currency
   |   - Vendor Invoice Number
   |
   | Vendor and Reference Details
   |   - Vendor Code
   |   - Vendor Name
   |   - PR Number
   |   - PO Number
   |   - GRN Number
   |   - Pay To Information
   |
   | Approval Workflow Information
   |   - Prepared By
   |   - PO Approved By
   |   - PR Approved By
   |   - PRQ Approved By
   |
   | Payment Request Line Table
   |   - Description
   |   - Quantity
   |   - Unit Price
   |   - Base Amount
   |   - Tax Rate
   |   - Tax Amount
   |   - Total Amount
   |   - Account Description (Analytic Distribution)
   |
   | Grouped Payment Line Processing
   |   - Supports grouped line display using custom grouping method
   |   - Consolidates payment request lines for reporting
   |
   | Payment Information Section
   |   - Advance Paid records
   |   - Payment history display
   |   - Payment references
   |   - Payment dates
   |   - Payment amount tracking
   |
   | Financial Summary
   |   - Total Amount calculation
   |   - Currency display
   |   - Amount In Words
   |
   | Additional Information
   |   - Note section
   |   - Remark section
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
   | custom_header_footer_payment_request_form
   |   - Defines report header and footer layout
   |   - Handles company branding and watermark display
   |
   | payment_request_template
   |   - Main report content and payment request data presentation
   |
   | payment_request_print
   |   - Container template that combines layout and report content

4. Usage
========================================
   | Used from payment request and vendor payment workflow
   |
   | Supported Processes:
   |   - Vendor payment request reporting
   |   - Purchase request and purchase order tracking
   |   - Payment approval workflow
   |   - Advance payment tracking
   |   - Payment history reporting
   |   - Analytic distribution reporting

5. Dependencies
========================================
   | Odoo Approval module
   | Odoo Accounting module
   | Custom approval_extends module
   | QWeb reporting engine

6. Installation
========================================
   | Ensure the approval_extends module is installed
   | Report templates are automatically registered upon module installation
   | No additional configuration required
