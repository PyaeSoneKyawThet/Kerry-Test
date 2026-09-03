Business Workflow Summary (MPP, 19-05-2026)
    Technical Name: custom_sql_reports
    Main Data Source: Sales - Job Orders

1. Summary Sales Team Performance by Revenue
=======================================
    | State: must be in 'sale' status.
    | Sale Person
        | Job Order - Customer ( Contact ) - Sales & Purchases Tab - Sale Person
    | Job Month
        | job_date - Data (Show Month and Year - e.g. Jan 2024)
    | BU
        | Order Line - Product Category ( categ_id )
    | Sub BU
        | Order Line - Order Line → distribution_analytic_account_ids where plan_name = 'Sub BU'
    | Billing Amount
        | Order Line - price_total (sum of all order lines for the same sale order)
    | Currency
        | Order Line - currency_id → symbol


2. Activity and Productivity Report for Sales Team
=======================================
    | Added an Activity and Productivity Excel report with filters for Date Range and Salespersons.
    | Retrieved activity records from CRM Activity Report for active activity types related to Contacts (Res Partner), Sales Orders, or activities without a specific model.
    | Generated Activity Type columns dynamically based on configured Mail Activity Types.
    | Displayed each activity as a separate row, marking the corresponding Activity Type column with a value of 1.
    | Added a Remark column to display activity notes/comments.
    | Added total counts for each Activity Type at the bottom of the report.
    | Exported the report as an Excel (.xls) file for download.