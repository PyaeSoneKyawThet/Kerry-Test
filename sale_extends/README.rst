Business Workflow Summary (Project Handover – PSM, 04-05-2026)
    Technical Name: sale_extends

1. Quotation Creation
======================================
    | Salesperson creates a quotation.
    | Default salesperson and approver are assigned.
    | Customer details (e.g., Attention To, Address) are auto-filled.

2. Submission for Approval
======================================
    | User clicks Submit.
    | Approval request is logged with reason.
    | Activity is assigned to the designated approver.
    | Status → Submitted

3. Approval Process
======================================
    | Approver reviews the quotation.
    | Can:
    |   - Approve → Order is confirmed automatically.
    |   - Reject → Reject reason is required.
    |   - Status → Approved / Rejected

4. Resubmission
======================================
    | Rejected orders can be edited and Resubmitted.
    | Reason for resubmission is recorded.
    | Status → Re-Submitted

5. Revision Workflow
======================================
    | User requests revision with reason.
    | Approver can:
    |   - Approve Revision → New revised quotation is created.
    |   - Reject Revision → Reason is recorded.
    | Original order is locked after revision.

6. VAS (Value-Added Service) Order
======================================
    | User can create a VAS Order linked to original quotation.
    | Separate sequence and tracking applied.

7. Renewal Process
======================================
    | User can renew an order.
    | New quotation is created with copied lines and details.
    | Tracks renewal status.

8. Tracking & Audit
======================================
    | All approval, rejection, and revision reasons are logged.
    | Activities are tracked per user.
    | Prepared By and Approved By are recorded.

9. Validation Controls
======================================
    | Address completeness is checked.
    | Approval button enabled only for authorized approver.

10. Reporting & Export
======================================
    | Notes and remarks are cleaned (HTML removed) during export.
    | Category notes are auto-generated based on selected categories.

11. For Additional Request & Change Request - MPP
=======================================
    | Allow to choose approver in Job Order [TASK:6738] 
    |    | Allow users to manually select the approver in the Job Order Form
    |    | Display all users in the approver selection list
    |    | Enable the selected user to perform the approval process