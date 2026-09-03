Business Workflow Summary (Project Handover – CZT, 25-06-2026)
-------------------------

Technical Name: quotation_won_lost

1. Overview
========================================

   | Quotation Won / Lost Analysis report for Odoo CRM.
   | This report provides a detailed breakdown of quotation outcomes
   | by salesperson, including won opportunities and lost opportunities
   | categorized by loss reasons.

   | It helps businesses understand why deals are being lost and how
   | sales performance is distributed across different loss reasons.

2. Key Features
========================================

   | Wizard Filters
   |   - Start Date selection
   |   - End Date selection
   |   - Multiple Salesperson selection

   | Win / Loss Analysis
   |   - Total won quotations per salesperson
   |   - Lost quotations categorized by loss reason
   |   - Unspecified loss reason tracking

   | Dynamic Loss Reason Handling
   |   - Automatically detects all configured CRM Lost Reasons
   |   - Generates dynamic columns for each loss reason
   |   - Supports flexible reporting without code changes

   | Excel Export
   |   - Generates Microsoft Excel (.xls) report
   |   - Downloadable directly from wizard
   |   - Includes company information
   |   - Includes report duration
   |   - Includes printed date and time

3. Report Layout
========================================

   | Company Name
   | Report Title:
   |   "Quotation Win / Loss Analysis Report"

   | Report Header
   |   - Selected date range
   |   - Printed date and time

   | Report Columns
   |   - No
   |   - Sale Person
   |   - Win
   |   - Loss Reason (dynamic columns)
   |   - Unspecified Loss Reason

4. Column Description
========================================

   | No
   |   - Sequential row number for each salesperson record.

   | Sale Person
   |   - Name of the salesperson responsible for the quotation.
   |   - Retrieved from CRM opportunity’s assigned user.

   | Win
   |   - Total number of opportunities marked as Won within the selected period.
   |   - Based on:
   |       * Opportunity marked as active = True
   |       * Stage marked as `is_won = True`
   |       * Win date (`date_seq4`) within selected period

   | Loss Reason (Dynamic Columns)
   |   - Each column represents a specific CRM Lost Reason.
   |   - Shows number of lost opportunities grouped by that reason.
   |   - Based on:
   |       * Opportunity marked as lost (`active = False`)
   |       * Probability = 0
   |       * Lost date within selected period
   |       * Specific `lost_reason_id`

   | Unspecified Loss Reason
   |   - Number of lost opportunities without a defined loss reason.
   |   - Includes records where `lost_reason_id` is NULL.

5. Business Benefits
========================================

   | Identifies main reasons for lost opportunities.
   | Helps improve sales strategy and conversion rate.
   | Provides visibility into salesperson performance.
   | Enables management to reduce recurring loss patterns.
   | Supports data-driven CRM decision making.

6. Technical Details
========================================

   | Data Source:
   |   - CRM Opportunities (crm.lead)
   |   - CRM Lost Reasons (crm.lost.reason)
   |   - Salesperson information (res.users / res.partner)
   |   - CRM Stages (crm.stage)

   | Export Format:
   |   - Microsoft Excel (.xls)

   | Processing Method:
   |   - Dynamic SQL generation for loss reasons
   |   - Aggregation by salesperson and loss category
   |   - Grouped reporting using database-level computation

   | Dynamic Behavior:
   |   - Loss reason columns are auto-generated from CRM configuration
   |   - No code modification required when new loss reasons are added

   | Filtering Behavior:
   |   - If no salesperson selected, system includes all users
   |     who are linked to CRM opportunities

   | Timezone Support:
   |   - Printed date follows user timezone setting
