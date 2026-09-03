Business Workflow Summary (Project Handover – PSM, 29-04-2026)
    Technical Name: approval_extends → Expense Approval

1. Create Expense Request
========================================
    | User creates Approval Expense with expense lines, vendor, and details.
    | System auto-generates sequence and default values (product, account, price).

2. Cash Advance Selection (Optional)
=========================================
    | User selects available cash advances (if any).
    | System validates usage (not cleared/reimbursed).

3. Submit Request
=========================================
    | User clicks Confirm.
    | System checks:
    |   - Required approvers exist
    |   - Cash advance payments are posted
    | Status → Pending / To Check

4. Approval Workflow
==========================================
    | Multi-level approvers process sequentially:
    |   - Checker → Checked
    |   - Approver → Approved
    | Status updates automatically based on approver actions.

5. Expense Approval(Petty Cash)
==========================================
    | On final approval:
    |   - Vendor Bill is automatically created.
    |   - Linked to Purchase Order (if exists).
    |   - Status → Approved

6. Billing & Accounting
==========================================
    | Vendor bill moves through: Draft → Posted
    | Payment state tracked (Not Paid / In Payment / Paid).

7. Payment Processing
==========================================
    | Two scenarios:
    |   - Direct Payment → Register vendor payment
    |   - Cash Advance Clearing → Reconcile with advance
    | System controls available actions based on state.

8. Cash Advance Clearance (If Applicable)
===========================================
    | System reconciles journal entries with vendor bill.
    | Marks cash advance as cleared.
    | Updates clearance date.

9. Write-off / Adjustment
===========================================
    | System handles differences (over/under payment).
    | Creates write-off entries if needed.

10. Cancellation / Refusal
===========================================
    | Request can be:
    |   - Refused by approver
    |   - Cancelled (with validation rules)
    | Related bills and entries are reversed if required.

11. Reporting & Tracking
===========================================
    | User can view:
    |   - Vendor Bills
    |   - Payments
    |   - Journal Entries
    |   - Write-offs
    | Export supported (HTML cleaned to text).

12. Closure
===========================================
    | Process completes when:
    |   - Payment fully settled
    |   - Cash advance cleared (if any)
    | Final state: Approved & Paid