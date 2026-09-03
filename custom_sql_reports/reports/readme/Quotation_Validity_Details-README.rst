Business Workflow Summary (Project Handover – MPP, 26-06-2026)
    Technical Name: custom_sql_reports

1. Overview
    ========================================
    | Quotation Validity Details report for Sales quotations.
    | Displays quotations that are approaching their validity
    | (expiry) date based on a selected report date.
    | Supports exporting the report to Excel.

2. Key Features
    ========================================
    | Wizard Filters
    | - Report Date
    | - Before Expire (Days)
    | - Multiple Salesperson selection
    | - Multiple Currency selection

    | Quotation Analysis
    | - Salesperson-wise quotation listing
    | - Customer information
    | - Quotation number
    | - Expiry date tracking
    | - Remaining days before expiry

    | Data Source
    | - Sales Quotations only
    | - Excludes Job Orders
    | - Includes confirmed quotations only
    | - Excludes revised approved quotations

    | Excel Export
    | - Generates Microsoft Excel (.xls)
    | - Includes company information
    | - Includes report date
    | - Includes expiry duration
    | - Includes printed date
    | - Includes currency summary

3. Report Layout
    ========================================
    | Company Name
    | Report Title:
    | "Quotation Validity Details"

    | Report Header
    | - Report Date
    | - Before Expire Duration
    | - Currency Summary
    | - Printed Date & Time

    | Report Columns
    | - No
    | - Sale PIC
    | - Customer Name
    | - Quotation Number
    | - Expired Date
    | - Expired In Day

4. Column Description
    ========================================
    | No
    | - Sequential row number.

    | Sale PIC
    | - Salesperson responsible for the quotation.

    | Customer Name
    | - Customer linked to the quotation.

    | Quotation Number
    | - Sales quotation reference.

    | Expired Date
    | - Quotation validity date.

    | Expired In Day
    | - Number of days remaining before quotation expiry.

5. Business Benefits
    ========================================
    | Monitors quotations nearing expiry.
    | Helps sales teams follow up with customers.
    | Improves quotation conversion opportunities.
    | Provides quick visibility of expiring quotations.
    | Supports Excel reporting for management.

6. Technical Details
    ========================================
    | Data Source:
    | - Sales Orders (sale_order)
    | - Users (res.users)
    | - Partners (res.partner)
    | - Currency (res.currency)

    | Export Format:
    | - Microsoft Excel (.xls)

    | Filtering Behavior:
    | - Salesperson selection is required.
    | - If no currency is selected, all currencies are included.
    | - Retrieves quotations within the selected expiry period.

    | Timezone Support:
    | - Printed date follows the user's timezone.