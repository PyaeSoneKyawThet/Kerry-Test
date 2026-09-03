Business Workflow Summary (Project Handover – CZT, 25-06-2026)
-------------------------

Technical Name: quotation_conversion_report

1. Overview
========================================

   | Quotation Conversion Report for Odoo Sales.
   | This report analyzes how effectively quotations are converted
   | into confirmed sales orders within a selected period.
   | It helps evaluate salesperson performance based on conversion
   | efficiency and overall quotation handling success.

2. Key Features
========================================

   | Wizard Filters
   |   - Start Date selection
   |   - End Date selection
   |   - Multiple Salesperson selection
   |   - Multiple Currency selection

   | Conversion Analysis
   |   - Total quotations created per salesperson
   |   - Accepted (confirmed) quotations
   |   - Conversion rate calculation

   | Business Rules
   |   - Only non-job quotations are considered (`is_job_order = False`)
   |   - Only quotations within selected date range are included
   |   - Excludes revised quotations (`revise_approved` state excluded)
   |   - Only confirmed sales orders are counted as accepted

   | Excel Export
   |   - Generates Microsoft Excel (.xls) report
   |   - Downloadable directly from wizard
   |   - Includes company information
   |   - Includes report duration
   |   - Includes printed date and currency summary

3. Report Layout
========================================

   | Company Name
   | Report Title:
   |   "Quotation Conversion Report"

   | Report Header
   |   - Selected date range
   |   - Printed date and time
   |   - Currency filter summary

   | Report Columns
   |   - No
   |   - Sale Rep
   |   - Total Quotations
   |   - Accepted Quotations
   |   - Conversion Rate

4. Column Description
========================================

   | No
   |   - Sequential row number for each salesperson record.

   | Sale Rep
   |   - Name of the salesperson responsible for quotations.
   |   - Retrieved from CRM/Salesperson assignment on the order.

   | Total Quotations
   |   - Total number of quotations created by the salesperson
   |   - Based on `sale_order` records within the selected period.

   | Accepted Quotations
   |   - Number of quotations successfully converted into sales orders.
   |   - Only includes quotations where:
   |       * `state = 'sale'`
   |       * Not in revised approval state (`revise_approved` excluded)

   | Conversion Rate
   |   - Percentage of quotations converted into sales.
   |   - Calculated as:
   |
   |       Conversion Rate = (Accepted Quotations / Total Quotations) × 100
   |
   |   - If Total Quotations is zero, the value is shown as 0.00%.

5. Business Benefits
========================================

   | Measures sales team conversion efficiency.
   | Identifies high-performing and low-performing sales reps.
   | Helps improve quotation follow-up strategy.
   | Supports sales forecasting and performance tracking.
   | Provides clear KPI visibility for management.

6. Technical Details
========================================

   | Data Source:
   |   - Sales Orders (sale.order)
   |   - Salesperson information (res.users / res.partner)
   |   - Currency (res.currency)

   | Export Format:
   |   - Microsoft Excel (.xls)

   | Processing Method:
   |   - SQL aggregation grouped by salesperson
   |   - Conversion rate calculated at Python level

   | Filtering Behavior:
   |   - If no salesperson selected, system includes all users
   |   - If no currency selected, system includes all currencies
   |   - Only non-job quotations are considered

   | Timezone Support:
   |   - Printed date follows user timezone setting
