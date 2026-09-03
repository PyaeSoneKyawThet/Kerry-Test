Business Workflow Summary (Project Handover – CZT, 25-06-2026)
-------------------------

Technical Name: quotation_validity_report

1. Overview
========================================

   | Quotation Validity Report for Odoo Sales.
   | This report provides analysis of quotation lifecycle based on
   | validity period, helping sales teams understand how quickly
   | quotations are approaching expiration.

   | It categorizes quotations based on how close they are to expiry
   | (15 days, 7 days, and 3 days before validity date).

2. Key Features
========================================

   | Wizard Filters
   |   - Report Date selection
   |   - Multiple Salesperson selection
   |   - Multiple Currency selection

   | Validity Analysis
   |   - Quotations expiring within 15 days
   |   - Quotations expiring within 7 days
   |   - Quotations expiring within 3 days
   |   - Salesperson-wise breakdown

   | Business Rules
   |   - Only confirmed sale orders are considered
   |   - Excludes job orders (`is_job_order = False`)
   |   - Excludes revised quotations (`revise_state != 'revise_approved'`)

   | Excel Export
   |   - Generates Microsoft Excel (.xls) report
   |   - Downloadable directly from wizard
   |   - Includes company information
   |   - Includes report date and printed date

3. Report Layout
========================================

   | Company Name
   | Report Title:
   |   "Quotation Validity Report"

   | Report Header
   |   - Report date
   |   - Printed date and time

   | Report Columns
   |   - No
   |   - Sale PIC
   |   - Before 15 Days
   |   - Before 7 Days
   |   - Before 3 Days

4. Column Description
========================================

   | No
   |   - Sequential row number for each salesperson record.

   | Sale PIC
   |   - Salesperson responsible for the quotation.
   |   - Retrieved from the quotation’s assigned user.

   | Before 15 Days
   |   - Number of quotations whose validity date is within
   |     15 days from the report date.

   | Before 7 Days
   |   - Number of quotations whose validity date is within
   |     7 days from the report date.

   | Before 3 Days
   |   - Number of quotations whose validity date is within
   |     3 days from the report date.

5. Business Benefits
========================================

   | Helps sales teams track quotation expiry risks.
   | Improves follow-up efficiency on near-expiry quotations.
   | Increases conversion rate by timely action.
   | Provides visibility into sales urgency by salesperson.
   | Supports proactive sales management decisions.

6. Technical Details
========================================

   | Data Source:
   |   - Sales Orders (sale_order)
   |   - Salesperson information (res.users / res.partner)
   |   - Currency (res.currency)

   | Export Format:
   |   - Microsoft Excel (.xls)

   | Processing Method:
   |   - SQL aggregation using filtered COUNT conditions
   |   - Grouped by Salesperson

   | Filtering Behavior:
   |   - If no salesperson selected, system includes all available users
   |   - If no currency selected, system includes all currencies

   | Business Logic:
   |   - Only confirmed sale orders (`state = 'sale'`) are included
   |   - Excludes job orders and revised quotations
   |   - Based on `validity_date` comparison with report date

   | Timezone Support:
   |   - Printed date follows user timezone setting
