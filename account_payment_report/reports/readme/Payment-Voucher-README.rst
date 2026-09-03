Business Workflow Summary (Project Handover – CZT, 25-06-2026)
-------------------------

Technical Name: account_payment_report → payment_voucher_report

1. Overview
========================================
   | PAYMENT VOUCHER report for Odoo
   | Used to print vendor payment transactions in voucher format
   | Displays payment details, journal entries, applied invoices, tax breakdown, and approval flow

2. Key Features
========================================
   | Payment Voucher Header
   |   - Company logo
   |   - "PAYMENT VOUCHER" title

   | Payment Voucher Footer
   |   - Company name
   |   - Payment reference number
   |   - Page number
   |   - Printed datetime

   | Payment Information Section
   |   - Payment Voucher No
   |   - Vendor Name
   |   - PV/GL Date
   |   - Bank Name (Journal)
   |   - Exchange Rate
   |   - Bank Transfer No
   |   - Pay To
   |   - Currency
   |   - Payment Amount

   | Journal Entry Section
   |   - Shows accounting move lines linked to payment
   |   - Debit / Credit breakdown in company currency
   |   - Original transaction currency amount
   |   - Includes write-off and exchange difference handling

   | Applied Invoice Section
   |   - Displays related vendor invoices (AP invoices)
   |   - Shows tax breakdown and invoice totals
   |   - Supports partial payment tracking
   |   - Supports credit note (refund) integration
   |   - Shows outstanding balance per invoice
   |   - Includes write-off and refund adjustments

   | Payment Summary Section
   |   - Total Debit
   |   - Total Credit
   |   - Total Base Amount
   |   - Total Tax Amount
   |   - Total Invoice Amount
   |   - Total Balance Amount
   |   - Total Write-off Amount
   |   - Total This Payment Amount

   | Approval Section
   |   - Prepared By
   |   - Checked By
   |   - Approved By
   |   - Submission / Approval Date

   | Signature Section
   |   - Received By Name
   |   - Received Date (manual entry field)

3. Journal Entry Table Columns Explained
========================================

   | Account Code
   |   - GL account code from journal entry line
   |   - Used for accounting classification

   | Account Name
   |   - GL account name
   |   - May include distribution account details if configured

   | Amount (Original Currency)
   |   - Transaction currency amount (amount_currency)
   |   - Based on payment or invoice currency

   | Debit (MMK)
   |   - Debit amount in company currency
   |   - Used for expense/asset increase posting

   | Credit (MMK)
   |   - Credit amount in company currency
   |   - Used for liability/income posting

4. Applied Invoice Table Columns Explained
========================================

   | Vendor Invoice No
   |   - Original vendor invoice reference number

   | AP Invoice No
   |   - Internal accounting invoice number in Odoo

   | Description
   |   - Invoice description or payment reason

   | Invoice Date
   |   - Invoice's date

   | Base Amount
   |   - Untaxed invoice amount (amount_untaxed)

   | CT Amount
   |   - Tax amount (amount_tax)

   | Invoice Amount
   |   - Total invoice amount (amount_total)
   |   - Base + Tax

   | Account Balance
   |   - Remaining invoice balance after payments/refunds
   |   - Dynamically calculated from payment history

   | WHT Amount
   |   - Withholding tax amount
   |   - Deducted amount before payment settlement

   | Pay Amount
   |   - Amount paid in this current payment voucher
   |   - Does not include previous payments and write-off

5. Special Features
========================================

   | Multi-Currency Support
   |   - Original currency shown in Amount column
   |   - Company currency used for Debit/Credit (MMK)

   | Write-off Handling 
   |   - _is_show_wirte_off_value
   |   - Automatically includes write-off journal lines
   |   - Adjusts totals based on settlement logic

   | Refund / Credit Note Handling
   |   - Credit notes shown under related invoices
   |   - Refund values reduce invoice balance before payment calculation

   | Exchange Difference Handling
   |   - Supports currency exchange differences in journal lines

   | Auto Calculation
   |   - Debit and Credit totals calculated dynamically
   |   - Invoice totals and balances computed in report logic

6. Report Structure
========================================

   | custom_header_footer_payment_voucher
   |   - Header and footer layout for payment voucher

   | custom_vendor_payment_report
   |   - Main report body
   |   - Payment information section
   |   - Journal entry table
   |   - Applied invoice table
   |   - Approval section
   |   - Signature section

   | payment_voucher_report
   |   - Main container template
   |   - Handles full report rendering

7. Usage
========================================

   | Open Payment (Vendor Payment / Journal Entry)

8. Dependencies
========================================

   | Odoo Accounting module
   | Odoo Payment module
   | QWeb Reporting Engine
   | Custom module:
   |   - account_payment_report

9. Installation
========================================

   | Install custom module:
   |   - account_payment_report

   | Upgrade module after report changes

   | Print report from Payment / Journal Entry records

10. Notes
========================================

   | Monetary values use float precision with thousand separators

   | Multi-currency handled via payment and journal currency fields

   | Write-off, refund, and credit note logic is fully integrated into balance calculation

   | Account Balance is dynamically calculated, not stored in database

   | Report supports partial payments, full settlement, and multi-step payment flows
