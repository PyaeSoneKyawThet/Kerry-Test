Business Workflow Summary (Project Handover – PSM, 29-04-2026)
    Technical Name: approval_extends → Payment Request Approval

1. Request Creation
=========================================
    | User creates a Payment Request.
    | System auto-generates sequence number.
    | Vendor, invoice details, and payment lines are entered.
    | Vendor bank info auto-filled from partner.

2. Validation
=========================================
    | System checks duplicate vendor invoice numbers (normalized).
    | Prevents duplicates across active requests.

3. Data Preparation
=========================================
    | Payment lines include:
    |   - Product / expense details
    |   - Taxes, analytic distribution
    |   - Job, vehicle, BL references
    | Total amount auto-calculated (untaxed + tax).

4. Approval Configuration
=========================================
    | System selects approval workflow based on:
    |   - Amount range
    |   - Currency
    |   - Department
    | Approvers are auto-assigned by level.

5. Submit for Approval
==========================================
    | User clicks Confirm.
    | Request moves to:
    |   - To Check (multi-level)
    |   - Pending (single approver)
    | Activities created for approvers.

6. Checking Stage
=========================================
    | Checkers review and mark as Checked.
    | Moves to next checker or approver.

7. Approval Stage
=========================================
    | Approvers approve sequentially.
    | Final approval:
    |   - Request status → Approved
    |   - Vendor Bill is automatically created.

8. Vendor Bill Creation
=========================================
    | System generates Vendor Bill (account.move):
    |   - Includes all request lines
    |   - Links to Purchase Order (if any)

9. Payment Handling
=========================================
    | Two scenarios:
    |   - Direct Payment
    |   - Cash Advance Clearing
    | Payment buttons enabled based on:
    |   - Bill status
    |   - Payment status
    |   - Cash advance usage

10. Cash Advance Integration
=========================================
    | Link approved Cash Advances.
    | Clear against Vendor Bill.
    | Auto reconciliation entry created.

11. Reconciliation
=========================================
    | System allows:
    |   - Auto or manual reconciliation
    |   - Write-off handling if needed

12. Completion
=========================================
    | Payment fully processed → status updated: Paid / Partial / In Payment

13. Cancel / Refuse
=========================================
    | Request can be:
    |   - Refused by approver
    |   - Cancelled (with restrictions if bills exist)

14. Export
=========================================
    | Export removes HTML from description