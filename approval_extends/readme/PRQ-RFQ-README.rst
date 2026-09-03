Business Workflow Summary (Project Handover – PSM, 29-04-2026)
    Technical Name: approval_extends → Purchase Request / RFQ Approval

1. Create Request
=======================================
    | User creates an Approval Request.
    | Selects PR Type (Cash Advance / Expense / Payment Request / Purchase).
    | Adds product lines and required details (amount, vendor, dates).

2. Auto Configuration
=======================================
    | System auto-fills:
    |   - Employee & Department
    |   - Currency & Amount
    |   - Default Journal & Payment Type
    | Approvers are generated based on:
    |   - Amount
    |   - Department
    |   - Approval configuration

3. Submit Request
=======================================
    | User clicks Confirm
    | System validates:
    |   - Minimum approvers
    |   - Required attachments
    | Request moves to:
    |   - To Check → if multiple levels
    |   - Pending → if single approver

4. Checking Process (Optional Layer)
=======================================
    | Assigned checkers review the request.
    | Status moves: To Check → Checked
    | After required checkers → moves to approval stage

5. Approval Process
=======================================
    | Approvers approve sequentially.
    | Final approval:
    |   - Status → Approved
    |   - Approval date recorded

6. Post-Approval Actions (Based on PR Type)
=======================================
    | Cash Advance:
    |   - Create Cash Advance Form
    |   - Track payment status
    | Expense:
    |   - Create Expense Form
    |   - Generate bills & payment tracking
    | Payment Request:
    |   - Create Payment Request Form
    |   - Link with vendor bills & payments
    | Purchase:
    |   - Generate RFQ / Purchase Order
    |   - Vendor-based PO creation

7. Document & Transaction Tracking
=======================================
    | System tracks:
    |   - Cash Advances
    |   - Expenses
    |   - Payment Requests
    |   - Purchase Orders
    | Shows status priority:
    |   - Approved → Pending → Cancelled
    |   - Payment: Posted → Draft → Cancelled

8. Restrictions & Controls
=======================================
    | Cannot cancel if:
    |   - Related documents already approved
    |   - PO already confirmed
    | Cannot delete approved requests

9. Cancellation Flow
=======================================
    | Cancels all linked documents: Cash Advance / Expense / Payment Request
    | Request status → Cancelled

10. Export
=======================================
    | Export removes HTML formatting (clean text)
