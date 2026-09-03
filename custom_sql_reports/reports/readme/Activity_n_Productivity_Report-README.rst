Business Workflow Summary (Project Handover – MPP, 26-06-2026)
    Technical Name: custom_sql_reports

1. Overview
    ========================================
    | Activity and Productivity report for Sales users.
    | Displays activities performed by each salesperson
    | within a selected date range.
    | Supports exporting the report to Excel.

2. Key Features
    ========================================
    | Wizard Filters
    |   - Start Date
    |   - End Date
    |   - Multiple Salesperson selection

    | Activity Analysis
    |   - Salesperson-wise activity summary
    |   - Dynamic activity type columns
    |   - Activity remarks
    |   - Total count for each activity type

    | Data Source
    |   - CRM Activity Report
    |   - Active Mail Activity Types
    |   - Activities for Customers and Sales Orders only

    | Excel Export
    |   - Generates Microsoft Excel (.xls)
    |   - Includes company information
    |   - Includes report duration
    |   - Includes printed date
    |   - Displays activity totals

3. Report Layout
    ========================================
    | Company Name
    | Report Title:
    |   "Activity and Productivity Report"

    | Report Header
    |   - Selected date range
    |   - Printed date & time

    | Report Columns
    |   - No
    |   - Sale Person
    |   - Dynamic Activity Types
    |   - Remark

4. Column Description
    ========================================
    | No
    |   - Sequential row number.

    | Sale Person
    |   - Salesperson who performed the activity.

    | Activity Types
    |   - One column for each active activity type.
    |   - Shows activity count (0 or 1) for each record.

    | Remark
    |   - Activity note converted to plain text.

5. Business Benefits
    ========================================
    | Tracks salesperson productivity.
    | Measures activity performance by type.
    | Provides activity remarks for review.
    | Supports management reporting.
    | Easy Excel export for analysis.

6. Technical Details
    ========================================
    | Data Source:
    | - CRM Activity Report (`crm_activity_report`)
    | - Mail Activity Types (`mail.activity.type`)
    | - Users (`res.users`)
    | - Partners (`res.partner`)

    | Export Format:
    | - Microsoft Excel (.xls)

    | Filtering Behavior:
    | - If no salesperson is selected, all salespersons are included.

    | Timezone Support:
    | - Printed date follows the user's timezone.
