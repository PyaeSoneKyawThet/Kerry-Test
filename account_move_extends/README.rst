Business Workflow Summary (Project Handover – PSM, 07-05-2026)
    Technical Name: account_move_extends

1. Added multi-level approval workflow for Customer Invoices, Vendor Bills, Credit Notes, and Debit Notes with submit, check, approve, refuse, and cancel processes.

2. Implemented dynamic approver/checker assignment based on employee approval configuration and sequence order.

3. Added user activity notifications and approval task management for each approval stage.

4. Customized invoice and bill status tracking with request status and user-specific approval status.

5. Added custom document numbering and sequence generation based on document type, branch/location, and transaction category.

6. Implemented separate sequence handling for invoices, vendor bills, petty cash, debit notes, credit notes, and journal entries.

7. Added reporting support fields including CT Total, Non-CT Total, Advance Amounts, Tax Totals, and internal references.

8. Created summarized invoice print lines by grouping invoice lines with quantity conversion to product base UoM.

9. Added AR/AP invoice print actions and customized invoice reporting support.

10. Added analytic distribution reporting helper methods for invoice and accounting reports.

11. Extended journal posting and reverse entry logic with automatic sequence handling and exchange difference references.

12. Added additional accounting and reporting fields such as payment references, attention to, staff location, and write-off indicators

13. Added multi-level approval workflow for Customer and Vendor Payments with submit, check, approve, refuse, and cancel processes.

14. Implemented payment approval configuration based on payment amount, currency, payment type, and partner type.

15. Added automatic approver assignment and sequential approval flow for payment processing.

16. Added payment activity notifications and approval task management for approvers and checkers.

17. Implemented validation controls for payment amount matching and approval sequence restrictions.

18. Added custom payment sequence generation for customer payments, vendor payments, receipt vouchers, and official receipts.

19. Added payment reporting features including Payment Voucher, Receipt Voucher, and Official Receipt printing.

20. Added journal enhancements with bank account information, payment short codes, and WHT Tax indicators.

21. Added payment type and journal integration with dynamic journal filtering and auto-selection.

22. Extended payment registration and reconciliation process with analytic distribution and write-off handling.

23. Added validation to prevent posting or reversing journal entries linked with payments.

24. Added reversal enhancements for debit notes, petty cash debit notes, and internal wrong transaction handling.