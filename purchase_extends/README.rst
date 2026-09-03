Business Workflow Summary (Project Handover – PSM, 04-05-2026)
    Technical Name: purchase_extends

1. PO Creation
=================================
    | User creates Purchase Order with vendor and product details.
    | System auto-fills related info (department, contact person, etc.).
    
2. Submit PO
=================================
    | User clicks Submit.
    | System determines approval configuration based on PO amount.
    | Approvers are automatically assigned.

3. Approval Flow Initialization
=================================
    | First approver/checker is notified.
    | Remaining approvers are set to Waiting.

4. Checking Stage (if applicable)
=================================
    | Assigned checker reviews PO.
    | Sequential checking enforced (no skipping).
    | After minimum checkers, flow moves to approval stage.

5. Approval Stage
=================================
    | Approvers review in sequence.
    | Minimum required approvals must be reached.
    | Each approval triggers next approver notification.

6. Final Approval
=================================
    | PO is automatically confirmed.
    | System records:
    |   - Approved By
    |   - Approval Date

7. Refusal Handling
=================================
    | Any approver can refuse.
    | PO status becomes Refused.
    | Approval process stops.

8. Cancellation
=================================
    | PO can be cancelled.
    | All approval activities are cleared.

9. PO Completion Tracking
=================================
    | System tracks received quantities.
    | PO marked as Done when fully received.
    
10. Additional Features
=================================
    | Due date auto-calculated from payment terms.
    | Amount displayed in words.
    | Vendor invoice/quotation tracking.
    | Print count tracking.