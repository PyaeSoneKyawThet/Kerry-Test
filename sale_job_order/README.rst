Business Workflow Summary (Project Handover – PSM, 04-05-2026)
    Technical Name: sale_extends

1. Create Sale / Job Order
=======================================
    | User creates a quotation or job order.
    | If marked as Job Order, system sets default name as Draft and assigns approver based on employee.
    | Customer must match the selected original quotation (validation applied).

2. Fill Job Details
=======================================
    | Enter job-related information (Project Name, Job Date, POL/POD, Vessel, Shipper, etc.).
    | Attach supporting documents if required.
    | System auto-generates Amount in Words.

3. Quotation Reference Linking
=======================================
    | User can link related quotations (VAS / Quotation Ref).
    | Easy navigation to linked quotations via smart button.
    
4. Confirmation
=======================================
    | On confirmation:
    |   - Order status changes to confirmed.
    |   - Confirmed Date is recorded automatically.

5. Invoice Generation
=======================================
    | Invoice is created from Sale Order.
    | All job-related fields are transferred to invoice (job date, logistics info, attachments, etc.).

6. Invoice Status Tracking
=======================================
    | System tracks invoice status:
    |   - To Invoice → No posted invoice
    |   - Invoiced → At least one posted invoice

7. Reversal Handling
=======================================
    | If credit note exists for posted invoice: Order is marked as Reversed

8. User & Approval Logic
=======================================
    | Changing salesperson updates approver (for Job Orders only).
    | Requester is automatically tracked.

9. Attachment Handling
=======================================
    | Attachments are linked to Sale Order and copied to related records when needed.

10. For Additional Request & Change Request - MPP
=======================================
    | New Menu for "Job Order for Sale" 
    |    | Number, Date, Customer, Revenue, Sale PIC, Status Columns
    |    |   | Number - order reference ( name )
    |    |   | Date - Job Date (job_date)
    |    |   | Customer - customer ( partner_id )
    |    |   | Revenue - Total ( amount_total )
    |    |   | Sale PIC - sale_pic_id of partner_id 
    |    |   | Status - invoiced_state
    |
    | To set Quotation Ref Expired Date with Job Order Date[TASK:6401]
    |   | Validate Quotation Expiry (Validity Date) against the selected Job Order Date instead of Today's Date
    |   | Set Job Date default value to Today's Date
    |   | Support backdated Job Orders while maintaining quotation validity checks
    |
    | Add Remark Field on Header and Detail Line in Job Order [TASK:6734]
    | Add Remark field in the Other Info tab of the Job Order Form
    |   | Display Remark as a column in the Job Order List View
    |   | Add Remark column to Job Order Lines
    |   | Support rich text formatting (e.g., bold and multi-line) similar to the Quotation Detail Line Remark field