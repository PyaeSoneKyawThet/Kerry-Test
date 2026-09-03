Business Workflow Summary (Project Handover – CZT, 25-06-2026)
-------------------------

Technical Name: st_perf_kpi_qty

1. Overview
========================================

   | Sales Team Performance By KPI Quantity report for Odoo CRM.
   | This report evaluates salesperson KPI achievement based on
   | opportunity progression through the sales pipeline during
   | a selected period.

2. Key Features
========================================

   | Wizard Filters
   |   - Start Date selection
   |   - End Date selection
   |   - Multiple Salesperson selection

   | KPI Performance Analysis
   |   - Hunting opportunity quantity
   |   - Projected opportunity quantity
   |   - Awarded opportunity quantity
   |   - Lost opportunity quantity
   |   - Conversion rate calculation

   | Opportunity Conversion Tracking
   |   - Tracks opportunities entering Hunting stage
   |   - Tracks opportunities entering Projected stage
   |   - Measures successful conversion into Awarded opportunities
   |   - Calculates unsuccessful projected opportunities

   | Excel Export
   |   - Generates Microsoft Excel (.xls) report
   |   - Downloadable directly from the wizard
   |   - Includes company information
   |   - Includes report duration
   |   - Includes printed date and time

3. Report Layout
========================================

   | Company Name
   | Report Title:
   |   "Sale Team Performance By KPI Quantity"

   | Report Header
   |   - Selected date range
   |   - Printed date and time

   | Report Columns
   |   - No
   |   - Sale Person
   |   - Hunting
   |   - Projected
   |   - Awarded
   |   - Lost
   |   - Conversion Rate (%)

4. Column Description
========================================

   | No
   |   - Sequential row number for each salesperson record.

   | Sale Person
   |   - Name of the salesperson responsible for the opportunities.

   | Hunting
   |   - Number of opportunities that entered the Hunting stage
   |     during the selected period.
   |   - Calculated using the opportunity field `date_seq1`.

   | Projected
   |   - Number of opportunities that entered the Projected stage
   |     during the selected period.
   |   - Calculated using the opportunity field `date_seq3`.

   | Awarded
   |   - Number of projected opportunities that were eventually
   |     converted into awarded opportunities.
   |   - Opportunities are counted when:
   |       * `date_seq3` falls within the selected period.
   |       * `date_seq4` contains a value.

   | Lost
   |   - Number of projected opportunities that were not awarded.
   |   - Calculated as:
   |
   |       Lost = Projected - Awarded

   | Conversion Rate (%)
   |   - Percentage of projected opportunities that did not convert
   |     into awarded opportunities.
   |   - Calculated as:
   |
   |       Conversion Rate (%) =
   |       ((Projected - Awarded) / Projected) × 100
   |
   |   - If Projected quantity is zero, the conversion rate
   |     will be displayed as 0%.

5. Business Benefits
========================================

   | Monitor salesperson KPI achievement.
   | Measure opportunity conversion effectiveness.
   | Identify weak points in the sales pipeline.
   | Compare conversion performance between salespersons.
   | Support management decision making using KPI metrics.

6. Technical Details
========================================

   | Data Source:
   |   - CRM Opportunities (crm.lead)
   |   - Salesperson information (res.users)
   |   - Partner information (res.partner)

   | Export Format:
   |   - Microsoft Excel (.xls)

   | Timezone Support:
   |   - Printed date follows the user's timezone setting.
