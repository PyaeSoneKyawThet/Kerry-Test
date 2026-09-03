Business Workflow Summary (Project Handover – PSM, 29-04-2026)
    Technical Name: approval_extends → PO Comparison Feature

1. Create PO Comparison
=========================================
    | User creates a po.comparison record (Draft state)
    | System auto-generates sequence number

2. Select PR Lines
=========================================
    | User selects approval.product.line records
    | Lines are linked via pr_line_ids

3. Generate Comparison Lines
==========================================
    | System creates po.comparison.line records
    | Copies product, qty, price, analytic, and reference data from PR lines

4. Review & Validate Data
=========================================
    | User verifies comparison details (price, quantity, vendor-related info, etc.)

5. Confirm PO Comparison
==========================================
    | State changes to Confirmed
    | Marks related PR lines as po_comparison_done = True
    | Confirmation date is stored

6. Create RFQ (Approval Request)
==========================================
    | System generates an approval.request (RFQ)
    | Links all comparison lines into approval product lines
    | RFQ is created under purchase approval category

7. Track RFQ Status
==========================================
    | Multiple RFQs can be created and linked
    | User can view RFQ list or open single RFQ directly
    | RFQ count is displayed on PO Comparison

8. Cancel Flow
==========================================
    | Cannot cancel if RFQ is already approved
    | On cancel, PR lines are reset (po_comparison_done = False)
    | State changes to Cancelled

9. Reset to Draft
==========================================
    | Allows rework of comparison before confirmation

10. Deletion Restriction
==========================================
    | Cannot delete confirmed records
    | Ensures data integrity with RFQ linkage