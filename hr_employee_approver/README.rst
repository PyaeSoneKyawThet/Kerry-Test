Business Workflow Summary (Project Handover - MPP, 26-06-2026)
Technical Name: **hr_employee_approver**

Employee records maintain approver configurations for different business documents.
Approval rules are assigned based on sequence, approval type, and amount configuration.

1. Employee Approval Configuration
   ==============================================
   | Configure approvers for each employee
   | Support multiple approvers per level
   | Maintain approval sequence
   | Support Approver and Checker roles
   | Automatically set default approver from selected users

2. Approval Line Management
   ==============================================
   | Separate approval lines for each document type
   | Invoice Approval
   | Vendor Bill Approval
   | Purchase Order Approval
   | Vendor Payment Approval
   | Customer Payment Approval
   | General Approval Request
   | Each line tracks approval status throughout the workflow

3. Approval Workflow
   ==============================================
   | Sequential approval process
   | Status flow:
   | New
   | → To Check
   | → Checked
   | → To Approve
   | → Waiting
   | → Approved / Refused / Cancel
   | Supports multiple approvers for each approval level

4. Approval Configuration
   ==============================================
   | Configure approval rules by:
   | Amount Range
   | Currency
   | Approval Level (From → To)
   | Payment Type
   | Purchase Type
   | Enable or disable approval requirement

5. Payment Approval Configuration
   ==============================================
   | Configure Vendor Payment approvals
   | Configure Customer Payment approvals
   | Different approval levels based on payment amount
   | Filter by Payment Type
   | Multi-currency support

6. Purchase Approval Configuration
   ==============================================
   | Configure Purchase Order approval levels
   | Approval based on purchase amount
   | Multi-currency support
   | Define approval sequence and required levels

7. Activity & Notification
   ==============================================
   | Automatically create activities for assigned approvers
   | Notify all configured approval users
   | Activities linked to:
   | Invoice
   | Vendor Bill
   | Purchase Order
   | Vendor Payment
   | Customer Payment

8. Overall Flow
   ================================================
   Configure Employee Approvers
   → Configure Approval Rules
   → Create Business Document
   → Assign Approvers by Configuration
   → Sequential Approval Process
   → Notify Next Approver
   → Final Approval / Refusal / Cancellation
