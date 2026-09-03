Business Workflow Summary (Project Handover – CZT, 25-06-2026)
-------------------------

Technical Name: account_payment_report → payment_report

1. Overview
========================================
   | OFFICIAL RECEIPT report for Odoo

2. Key Features
========================================
   | Official Receipt Header
   |   - company logo
   |   - "OFFICIAL RECEIPT" title

   | Receipt Footer
   |   - company name
   |   - receipt reference
   |   - page number
   |   - printed datetime

   | Customer Information Section
   |   - Received From
   |   - Customer Code
   |   - Address
   |   - Being Payment For

   | Receipt Information Section
   |   - Official Receipt Number
   |   - Official Receipt Date
   |   - Currency

   | Applied Invoice Table
   |   - Shows invoice payment details
   |   - Supports partial payments
   |   - Supports credit note display
   |   - Supports refund adjustments
   |   - Supports write-off handling

   | Payment Summary Section
   |   - Received Type
   |   - Cheque No
   |   - Dated
   |   - Received Amount

   | Signature Section
   |   - Collector signature line
   |   - Authorized Signature
   |   - Supports digital signature image

3. Payment Table Columns Explained
========================================

   | No
   |   - Row number for each invoice or credit note line

   | Invoice Number
   |   - Invoice number or credit note reference

   | Amount Balance
   |   - Invoice amount before current payment
   |   - Includes previous payments and refund adjustments

   | This Payment
   |   - Payment amount for invoice from current receipt
   |   - Includes write-off amount if current payment is final payment

   | Balance Due
   |   - Remaining amount after current payment
   |   - Formula:
   |       Amount Balance - This Payment

4. Special Cases
========================================

   | Credit Note Row
   |   - Credit notes display below related invoice
   |   - Credit amount is shown separately

   | Write-off
   |   - Write-off amount is added into "This Payment"
   |   - Applied when current payment closes invoice balance

   | Refund Adjustment
   |   - Refund amounts reduce invoice balance before payment calculation

5. Report Structure
========================================

   | custom_header_footer_payment_receipt
   |   - Header and footer layout for official receipt report

   | custom_payment_report
   |   - Main report body
   |   - Customer information
   |   - Receipt information
   |   - Applied invoice table
   |   - Payment summary
   |   - Signature section

   | payment_report
   |   - Main container template
   |   - Handles report rendering

6. Usage
========================================

   | Open Payment Record
   | Print
   | Official Receipt

7. Dependencies
========================================

   | Odoo Accounting module
   | Odoo Payment module
   | QWeb reporting engine
   | Custom module:
   |   - account_payment_report

8. Installation
========================================

   | Install custom module:
   |   - account_payment_report

   | Upgrade module after report changes

   | Print report from payment records

9. Notes
========================================

   | Monetary values use float precision and thousand separators

   | Multi-currency values use payment report currency fields

   | Credit notes and refunds are grouped with invoices for easier tracking

   | Write-off handling is automatically included when invoice is fully settled
