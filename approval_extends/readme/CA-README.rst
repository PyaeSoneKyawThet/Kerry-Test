Business Workflow Summary (Project Handover – PSM, 29-04-2026)
    Technical Name: approval_extends → Cash Advance Approval

1. Create Request
========================================
    | User creates Cash Advance Form
    | System auto-generates sequence (name)
    | Required fields: Category, Amount, Currency, etc.

2. Auto Configuration
========================================
    | Approval config (config_id) is determined by:
    |   - Amount range
    |   - Currency
    |   - Department
    | Approver list is auto-generated based on config

3. Submit / Confirm
=========================================
    | User clicks Confirm
    | System checks: Minimum approvers requirement
    | Status changes: new → pending / to_check
    | First approver/checker gets activity

4. Checking Stage (If Applicable)
=========================================
    | Checkers review in sequence
    | Status flow: to_check → checked
    | Once minimum checkers reached → move to approval stage

5. Approval Process
=========================================
    | Approvers approve sequentially
    | Status flow: pending → approved
    | Final approval triggers:
    |   - Creation of Account Payment
    |   - Cash Advance status → approved

6. Payment Handling
=========================================
    | Payment record created automatically
    | Payment states tracked: draft / posted / cancel
    | Priority logic: Posted → Draft → Cancel

7. Reimbursement Logic
=================================
    | Allowed only if:
    |   - Not used in Expense / Payment Request
    |   - Payment exists and not reconciled
    | Creates Reimburse Payment (inbound)

8. Reconciliation
=================================
    | Match payment with journal entries
    | Mark as Cleared

9. Cancel Process
=========================================
    | Not allowed if: Payment already posted
    | If linked Purchase Request unused: Open cancel wizard
    | Else: Direct cancel

10. Reset to Draft
=========================================
    | Allowed if Purchase Request not canceled
    | Resets:
    |   - Approvers
    |   - Status → new

11. Access Control
=========================================
    | Only request owner (with approval rights) can modify
    | User status depends on approver role

12. Lock / Unlock
=========================================
    | Manual control to prevent editing

13. Export
=========================================
    | HTML reason field converted to plain text during export