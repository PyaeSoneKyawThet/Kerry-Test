Business Workflow Summary (Project Handover – CZT, 25-06-2026)
-------------------------

Technical Name: st_perf_actual_qty

1. Overview
========================================
   | Sales Team Performance By Actual Quantity report for Odoo CRM.
   | This report provides an overview of salesperson performance.

2. Key Features
========================================
   | Wizard Filters
   |   - Start Date selection
   |   - End Date selection
   |   - Multiple Salesperson selection

   | Sales Performance Analysis
   |   - Hunting opportunities count
   |   - Projected opportunities count
   |   - Awarded opportunities count
   |   - Lost opportunities count

   | Opportunity Tracking
   |   - Hunting stage based on date_seq1
   |   - Projected stage based on date_seq3
   |   - Awarded stage based on date_seq4
   |   - Lost opportunities based on lost_date and probability

   | Excel Export
   |   - Generates XLS report file
   |   - Downloadable directly from wizard
   |   - Includes company information
   |   - Includes report duration
   |   - Includes printed date and time

3. Report Layout
========================================
   | Company Name
   | Report Title:
   |   "Sale Team Performance By Actual Quantity"

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

4. Column Description
========================================

   | No
   |   - Sequential row number for each salesperson record.

   | Sale Person
   |   - Name of the salesperson assigned to the opportunity.
   |   - Data is retrieved from the opportunity's assigned user.

   | Hunting
   |   - Number of opportunities that entered the Hunting stage
   |     during the selected period.
   |   - Calculated using the opportunity field `date_seq1`.

   | Projected
   |   - Number of opportunities that entered the Projected stage
   |     during the selected period.
   |   - Calculated using the opportunity field `date_seq3`.

   | Awarded
   |   - Number of opportunities that entered the Awarded stage
   |     during the selected period.
   |   - Calculated using the opportunity field `date_seq4`.

   | Lost
   |   - Total number of opportunities marked as Lost during the selected period.
   |   - Count is based on the opportunity field `lost_date`.
   |   - Only opportunities satisfying the following conditions are counted:
   |       * Opportunity is inactive (`active = False`)
   |       * Probability is 0%
   |       * Lost date falls within the selected period

5. Business Benefits
========================================
   | Measure salesperson pipeline activities.
   | Monitor opportunity conversion progress.
   | Identify successful and unsuccessful opportunities.
   | Compare sales team performance within a period.
   | Support management decision making with actual CRM data.

6. Technical Details
========================================
   | Data Source:
   |   - CRM Opportunities (crm.lead)
   |   - Salesperson information (res.users)
   |   - Partner information (res.partner)

   | Export Format:
   |   - Microsoft Excel (.xls)

   | Timezone Support:
   |   - Printed date follows user's timezone setting.
