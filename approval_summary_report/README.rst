Business Workflow Summary (Project Handover – PSM, 29-04-2026)
    Technical Name: approval_summary_report

Pulls data from approved Purchase Requests (PR) only

1. Aggregates related documents
=======================================
    | - Purchase Requests (PR)
    | - RFQs and Vendor Quotations
    | - Purchase Orders (PO)
    | - Comparison records
    | - Payment Requests (PR & RFQ)
    | - Expense Requests
    | - Cash Advances

2. Groups and summarizes
======================================
    |  - Vendor (partner)
    | - Department and Parent Department
    | - Request Owner
    | - Document numbers (PR, RFQ, PO, Comparison)
    | - Financial data (amount, currency)
    | - Request type (Cash Advance / Expense / Payment With PO / Without PO)
    | - Status (Approved only)

3. Combines multiple related records into single rows using aggregation (STRING_AGG)
=======================================
    | - Shows all linked document numbers in one field
    | - Provides a comprehensive view of the approval history for each request

4. Displays consolidated approval tracking view
=======================================
    | - Procurement
    | - Finance
    | - Audit reporting


5. For Additional Request & Change Request - MPP
    ================================================
    | Dept Access Right in Approval Summary Menu [TASK:6392]
    |   | Display only transactions belonging to the user's assigned department
    |   | Restrict Approval Summary records based on the user's department mapping
    |   | Improve data visibility and access control by department