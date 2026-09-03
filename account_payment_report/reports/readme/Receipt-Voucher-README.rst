Business Workflow Summary (Project Handover – CZT, 25-06-2026)
-------------------------

Technical Name: account_payment_report → receipt_voucher_report

1. Overview
========================================
   | RECEIPT VOUCHER report for Odoo
   | Used to print customer receipt transactions in voucher format
   | Displays receipt details, journal entries, applied invoices, credit notes, and approval information

2. Key Features
========================================

   | Receipt Voucher Header
   |   - Company logo
   |   - "RECEIPT VOUCHER" title

   | Receipt Voucher Footer
   |   - Company name
   |   - Receipt reference number
   |   - Page number
   |   - Printed datetime

   | Receipt Information Section
   |   - Description
   |   - Receipt Voucher No
   |   - Customer Code
   |   - Customer Name
   |   - GL Date
   |   - Bank Name
   |   - Exchange Rate
   |   - Receipt Type
   |   - Currency
   |   - Official Receipt No
   |   - Official Receipt Date
   |   - Received Amount

   | Journal Entry Section
   |   - Shows accounting move lines linked to receipt
   |   - Debit / Credit breakdown in company currency
   |   - Original transaction currency amount
   |   - Includes write-off and exchange difference handling

   | Applied Invoice Section
   |   - Displays related customer invoices
   |   - Shows invoice balances before payment
   |   - Supports partial payment tracking
   |   - Supports credit note display
   |   - Supports refund adjustments
   |   - Supports write-off handling

   | Payment Summary Section
   |   - Total Invoice Amount
   |   - Total Amount Balance
   |   - Total This Payment
   |   - Total Balance Due

   | Approval Section
   |   - Prepared By
   |   - Checked By
   |   - Approved By
   |   - Submission Date
   |   - Approval Date

3. Journal Entry Table Columns Explained
========================================

   | No
   |   - Running row number for each journal line

   | Account Code
   |   - General ledger account code

   | Account Name
   |   - General ledger account name

   | Amount
   |   - Transaction amount in original currency
   |   - Retrieved from amount_currency

   | Debit Amount (MMK)
   |   - Debit amount in company currency
   |   - Included in total debit calculation

   | Credit Amount (MMK)
   |   - Credit amount in company currency
   |   - Included in total credit calculation

4. Applied Invoice Table Columns Explained
========================================

   | No
   |   - Running row number for each invoice

   | Invoice Number
   |   - Customer invoice number
   |   - Credit note references are displayed under the related invoice

   | Invoice Date
   |   - Date of invoice issuance

   | Invoice Amount
   |   - Total invoice amount
   |   - Includes taxes

   | Amount Balance
   |   - Outstanding invoice balance before current receipt
   |   - Adjusted for previous receipts and credit notes

   | This Payment
   |   - Amount received from the current receipt voucher
   |   - Includes write-off amount when invoice is fully settled

   | Balance Due
   |   - Remaining balance after current receipt
   |   - Formula:
   |       Amount Balance - This Payment

5. Special Features
========================================

   | Multi-Currency Support
   |   - Original currency displayed in Amount column
   |   - Debit and Credit displayed in company currency

   | Credit Note Handling
   |   - Credit notes displayed beneath related invoices
   |   - Credit note amounts included in balance calculations

   | Write-off Handling
   |   - Automatically includes write-off journal entries
   |   - Supports full settlement scenarios

   | Exchange Difference Handling
   |   - Supports exchange gain/loss journal entries

   | Auto Total Calculation
   |   - Debit and Credit totals calculated automatically
   |   - Invoice totals and balances calculated dynamically

6. Report Structure
========================================

   | custom_header_footer_receipt_voucher
   |   - Header and footer layout for receipt voucher

   | custom_receipt_report
   |   - Main report body
   |   - Receipt information section
   |   - Journal entry table
   |   - Applied invoice table
   |   - Approval section

   | receipt_voucher_report
   |   - Main container template
   |   - Handles report rendering

7. Usage
========================================

   | Open Customer Receipt Payment
   | Print
   | Receipt Voucher

8. Dependencies
========================================

   | Odoo Accounting module
   | Odoo Payment module
   | QWeb reporting engine
   | Custom module:
   |   - account_payment_report

9. Installation
========================================

   | Install custom module:
   |   - account_payment_report

   | Upgrade module after report changes

   | Print report from customer payment records

10. Notes
========================================

   | Monetary values use float precision and thousand separators

   | Multi-currency transactions are supported

   | Credit notes are grouped with related invoices for easier tracking

   | Write-off amounts are automatically included when invoices are fully settled

   | Amount Balance is dynamically calculated from invoice payment history

   | Balance Due is calculated after applying the current receipt amount

   | Approval information is retrieved from customer payment approval records

   | Report supports partial receipts, full settlements, credit notes, refunds, and multi-payment scenarios
