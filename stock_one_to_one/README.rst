Business Workflow Summary (Project Handover – PSM, 04-05-2026)
    Technical Name: stock_one_to_one

1. System creates stock picking records (single or batch creation supported).

2. Picking type is identified and sequence number is generated if not provided.

3. Stock move lines are automatically updated
========================================
    | Source location
    | Destination location
    | Picking type and company information

4. Scheduled date is captured and applied after record creation.

5. Split Handling Rule
========================================
   | If destination location is Transit, system triggers split logic.
   | A new procurement group is created.
   | Stock moves are linked to this procurement group for traceability.
   | Validation ensures product lines exist before proceeding.

6. Stock picking is created using standard Odoo processing.

7. Post-Creation Processing
========================================
   | Scheduled date is updated.
   | Context is adjusted for split pickings when applicable.
   | Partner is subscribed to chatter for supplier/customer related operations.

8. Final output ensures
========================================
   | Proper grouping of stock operations
   | Accurate stock movement tracking
   | Clear traceability between pickings and procurement groups