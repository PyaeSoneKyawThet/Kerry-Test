# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools, _
from odoo.osv import expression

class ApprovalSummary(models.Model):
    _name = "approval.summary.report"
    _description = 'Approval Report'
    _auto = False
    _order = "date DESC"
    
    request_name = fields.Char(string="PR No", readonly=True)
    date = fields.Date(string="Date", readonly=True)
    comparison = fields.Char(string="Comparison No", readonly=True)
    rfq_no = fields.Char(string="RFQ No", readonly=True)
    purchase = fields.Char(string="PO No", readonly=True)
    request_pay = fields.Char(string="PR's Payment Request No", readonly=True)
    rfq_pay = fields.Char(string="RFQ's Payment Request No", readonly=True)
    request_exp = fields.Char(string="Expense No", readonly=True)
    cash_advance = fields.Char(string="Cash Advance No", readonly=True)
    pr_type = fields.Char(string="PR Type", readonly=True)
    partner_id = fields.Many2one("res.partner", string="Vendor", readonly=True)
    doc_location_id = fields.Many2one("staff.location", string="Doc Location", readonly=True)
    payment_type_id = fields.Many2one("account.payment.type", string="Type", readonly=True)
    currency_id = fields.Many2one("res.currency", string="Currency", readonly=True)
    amount = fields.Float(string="Amount", readonly=True)
    request_status = fields.Char(string="Request Status", readonly=True)
    location = fields.Char(string="Delivery Location", readonly=True)
    request_owner_id = fields.Many2one("res.users", string="Request Owner", readonly=True)
    department_id = fields.Many2one("hr.department", string="Department", readonly=True)
    reference = fields.Char(string="Vendor Quotation No", readonly=True)
    vendor_invoice_no = fields.Char(string="Vendor Invoice No", readonly=True)
    without_PO = fields.Boolean(string="Without PO", readonly=True)
    est_delivery_date = fields.Date(string="Est. Delivery Date", readonly=True)
    value_date = fields.Date(string="Value Date", readonly=True)
    pay_to_id = fields.Many2one("hr.employee", string="Pay To Employee", readonly=True)
    pay_to_external = fields.Char(string="Pay To External", readonly=True)
    request_approved_date = fields.Date(string="Request Approved Date", readonly=True)

    #search parent department
    parent_department_id = fields.Many2one('hr.department', string="Parent Department", readonly=True)

    def init(self):
        tools.drop_view_if_exists(self._cr, 'approval_summary_report')

        self._cr.execute("""
            CREATE or REPLACE view approval_summary_report as (
                SELECT request.id,request.name request_name,(request.date AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Yangon') AS date,request.request_owner_id,request.department_id, request.parent_department_id,
                    STRING_AGG(DISTINCT com.name, ', ')::CHARACTER VARYING comparison,
                    STRING_AGG(DISTINCT rfq.name, ', ')::CHARACTER VARYING rfq_no,
                    STRING_AGG(DISTINCT po.name, ', ')::CHARACTER VARYING purchase,
                    STRING_AGG(DISTINCT req_pay.name, ', ')::CHARACTER VARYING request_pay,
                    STRING_AGG(DISTINCT rfq_pay.name, ', ')::CHARACTER VARYING rfq_pay,
                    STRING_AGG(DISTINCT req_exp.name, ', ')::CHARACTER VARYING request_exp,
                    STRING_AGG(DISTINCT cash.name, ', ')::CHARACTER VARYING cash_advance,
                    CASE WHEN LOWER(request."PR_type")='cash_advance' THEN 'Cash Advance'
						WHEN LOWER(request."PR_type")='expense' THEN 'Expense'
						WHEN LOWER(request."PR_type")='payment_request' THEN 'Payment Without PO'
						WHEN LOWER(request."PR_type")='payment with po' THEN 'Payment With PO' ELSE '' END pr_type,
                    request.partner_id,request.staff_location_id doc_location_id,request.location,request.reference,
                    request.vendor_invoice_no,request."without_PO",request.est_delivery_date,request.request_approved_date,request.value_date,request.pay_to_id,
                    request.pay_to_external,request.payment_type_id,request.currency_id,SUM(request.amount) amount,
                    CASE WHEN LOWER(request.request_status)='approved' THEN 'Approved' ELSE '' END request_status
                    FROM approval_request request JOIN approval_category cat 
                    ON cat.id=request.category_id AND cat.approval_type='purchase_req'
                    JOIN approval_product_line line ON request.id=line.approval_request_id
                    LEFT JOIN po_comparison_line cline ON line.id=cline.purchase_request_line_id
                    LEFT JOIN po_comparison com ON cline.po_comparison_id=com.id AND com.state='confirm'
                    LEFT JOIN approval_product_line rfq_line ON rfq_line.purchase_request_line_id=line.id
                    LEFT JOIN approval_request rfq ON rfq.id=rfq_line.approval_request_id AND rfq.approval_type='purchase' AND rfq.request_status='approved'
                    LEFT JOIN purchase_order_line pol ON line.id=pol.purchase_request_line_id
                    LEFT JOIN purchase_order po ON pol.order_id=po.id AND po.state in ('purchase', 'done')
                    LEFT JOIN approval_payment_request req_pay ON req_pay.request_id=request.id AND req_pay.request_status='approved'
                    LEFT JOIN approval_payment_request rfq_pay ON rfq_pay.request_id=rfq.id AND rfq_pay.request_status='approved'
                    LEFT JOIN approval_expense req_exp ON req_exp.request_id=request.id AND req_exp.request_status='approved'
                    LEFT JOIN cash_advance_form cash ON cash.request_id=request.id AND cash.request_status='approved'
                    WHERE request.request_status='approved'
                    GROUP BY request.id,request.name,request.date,request."PR_type",request.partner_id,request.staff_location_id,
                        request.request_owner_id,request.department_id, request.parent_department_id, request.payment_type_id,request.currency_id,request."request_status",
                        request.vendor_invoice_no,request."without_PO",request.est_delivery_date,request.request_approved_date,request.value_date,request.pay_to_id,
                        request.location,request.reference,request.pay_to_external
            );
        """)