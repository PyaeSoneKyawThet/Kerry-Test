Business Workflow Summary (Project Handover – CZT, 25-06-2026)
-------------------------

Technical Name: qty_revised_quotation_report

1. Overview
========================================

   | Qty of Revised Quotation report for Odoo Sales.
   | This report provides analysis of how many times quotations
   | have been revised before reaching a final confirmed state.

   | It helps businesses track quotation revision behavior and
   | understand how frequently sales quotations are updated before
   | final approval.

2. Key Features
========================================

   | Wizard Filters
   |   - Start Date selection
   |   - End Date selection
   |   - Multiple Salesperson selection
   |   - Multiple Customer selection
   |   - Multiple Currency selection

   | Revision Analysis
   |   - Tracks final confirmed quotations
   |   - Counts number of revisions per quotation chain
   |   - Shows revision depth per customer and salesperson

   | Business Rules
   |   - Only confirmed quotations are considered (`state = sale`)
   |   - Only quotations with original revision chain are included
   |   - Excludes VAS quotations (`is_vas = False`)
   |   - Excludes renewal-linked quotations (`is_renew_created = False`)

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
   |   "Qty of Revised Quotation"

   | Report Header
   |   - Selected date range
   |   - Printed date and time
   |   - Currency filter summary
   |   - Status: Quotation Revised

   | Report Columns
   |   - No
   |   - Sale PIC
   |   - Customer Name
   |   - Final Quotation Number
   |   - Revised Time

4. Column Description
========================================

   | No
   |   - Sequential row number for each record.

   | Sale PIC
   |   - Salesperson responsible for the quotation chain.
   |   - Retrieved from customer’s assigned salesperson.

   | Customer Name
   |   - Name of the customer linked to the quotation.

   | Final Quotation Number
   |   - The last quotation in the revision chain.
   |   - Represents the final approved quotation in the workflow.
   |   - If the quotation originates from a renew flow (`is_renew_created = True`),
   |     that renew quotation is treated as the original root source of the chain.
   |   - The final quotation is always the latest successful record in the
   |     chain regardless of whether it started from a standard quotation or a renew process.

   | Revised Time
   |   - Number of times the quotation was revised.
   |   - Calculated from the recursive quotation chain depth.
   |   - Includes revisions starting from either:
   |       * Original quotation, or
   |       * Renew-created quotation (treated as root when applicable)
   |   - The revision count reflects the full chain until the final quotation.

5. Business Benefits
========================================

   | Helps identify how often quotations are revised before approval.
   | Improves understanding of customer negotiation behavior.
   | Assists in reducing unnecessary quotation revisions.
   | Supports sales efficiency optimization.
   | Provides insight into quotation approval complexity.

6. Technical Details
========================================

   | Data Source:
   |   - Sales Orders (sale_order)
   |   - Customers (res.partner)
   |   - Salesperson information (res.users / res.partner)

   | Export Format:
   |   - Microsoft Excel (.xls)

   | Processing Method:
   |   - Recursive SQL query to trace quotation revision chains
   |   - Aggregation based on final quotation nodes
   |   - Filters applied for currency, customer, and salesperson

   | Filtering Behavior:
   |   - If no salesperson selected, system includes all users
   |   - If no customer selected, system includes all customers
   |   - If no currency selected, system includes all currencies

   | Business Logic:
   |   - Only finalized quotations are considered (`state = sale`)
   |   - Only quotations with revision history are included
   |   - VAS and renewal quotations are excluded

   | Timezone Support:
   |   - Printed date follows user timezone setting
