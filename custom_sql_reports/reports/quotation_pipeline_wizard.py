from odoo import models, fields
import io
import xlwt
import base64
from . import odoo_datetime_helper
from datetime import datetime, time, timedelta

class QuotationPipelineWizard(models.TransientModel):
    _name = "quotation.pipeline.wizard"
    _description = "Quotation Pipeline Report"

    start_date = fields.Date(string="Start Date")
    end_date = fields.Date(string="End Date")

    print_date = fields.Datetime(default=fields.Datetime.now)
    excel_file = fields.Binary('Excel File')
    file_name = fields.Char('File Name')

    user_ids = fields.Many2many('res.users', string="Salesperson", domain=lambda self: self._get_sale_person_domain(), required=True)
    
    def _get_sale_person_domain(self):
        current_user = self.env.user

        if current_user.has_group('sales_team.group_sale_manager'):
            partners = self.env['res.partner'].search([])
            users = partners.mapped('user_id')
            return [('id', 'in', users.ids)]

        return [('id', '=', current_user.id)]

    def _get_report_data(self):
        query = """
            WITH 
            user_info AS (
                SELECT 
                    u.id AS user_id,
                    p.name AS user_name
                FROM res_users u
                LEFT JOIN res_partner p ON p.id = u.partner_id
            ),

            crm_lost AS (
                SELECT DISTINCT rel.crm_lead_id, rel.sale_order_id
                FROM crm_lead_sale_order_rel rel
                JOIN crm_lead cl ON cl.id = rel.crm_lead_id
                WHERE cl.won_status = 'lost'
            )

            SELECT
                ui.user_name AS sale_person,
                so.user_id AS user_id,

                COUNT(*) FILTER (
                    WHERE so.state = 'draft'
                    AND COALESCE(so.approval_state, '') <> 'rejected'
                ) AS draft_quotation,

                COUNT(*) FILTER (
                    WHERE so.state = 'sale'
                ) AS approved_quotation,

                COUNT(*) FILTER (
                    WHERE so.state = 'sale'
                    AND EXISTS (
                        SELECT 1
                        FROM crm_lead_sale_order_rel rel
                        JOIN crm_lead cl ON cl.id = rel.crm_lead_id
                        JOIN crm_stage cs ON cs.id = cl.stage_id
                        WHERE rel.sale_order_id = so.id
                        AND cs.is_won = TRUE
                    )
                    AND COALESCE(so.revise_state, '') <> 'revise_approved'
                ) AS accepted_quotation,

                COUNT(DISTINCT crm_lost.crm_lead_id) FILTER (
                    WHERE so.state = 'sale'
                    AND crm_lost.crm_lead_id IS NOT NULL
                    AND COALESCE(so.revise_state, '') <> 'revise_approved'
                ) AS lost_quotation

            FROM sale_order so 
                LEFT JOIN res_partner partner ON partner.id = so.partner_id
                LEFT JOIN user_info ui ON ui.user_id = so.user_id
                LEFT JOIN crm_lost ON crm_lost.sale_order_id = so.id

            WHERE so.create_date >= %(start_date)s
                AND so.create_date <= %(end_date)s
                AND so.user_id IN %(user_ids)s
                AND so.is_job_order = FALSE

            GROUP BY
                ui.user_name,
                so.user_id
            ORDER BY
                ui.user_name
        """

        user_ids = tuple(self.user_ids.ids)

        params = {
            "start_date": datetime.combine(self.start_date, time.min),
            "end_date": datetime.combine(self.end_date, time.max),
            "user_ids": user_ids,
        }


        if not user_ids:
            params["user_ids"] = tuple(self.env['res.users'].search([]).ids)
        
        self.env.cr.execute(query, params)
        data = self.env.cr.dictfetchall()
        return data
    
    # # excel print format
    def _print_quotation_pipeline(self, report_data):
        output = io.BytesIO()

        workbook = xlwt.Workbook(encoding='utf-8')
        sheet = workbook.add_sheet("Quotation Pipeline Report")

        header_style = xlwt.easyxf('font: bold 1; align: horiz center, vert center;')
        cell_style_start = xlwt.easyxf('font: bold 1; align: horiz left, vert center, wrap on;')
        cell_style_end = xlwt.easyxf('font: bold 1; align: horiz right, vert center, wrap on;')
        cell_style = xlwt.easyxf('align: horiz left;')
        cell_style_center = xlwt.easyxf('align: horiz center, vert center;')
        number_style = xlwt.easyxf('align: horiz right;')

        print_date = odoo_datetime_helper.local_time(
            self.print_date,
            self.env.user.tz or 'Asia/Yangon'
        )

        start_date = self.start_date.strftime('%d.%m.%Y') if self.start_date else ""
        end_date = self.end_date.strftime('%d.%m.%Y') if self.end_date else ""
        company_name = self.env.company.name
        performance_data = report_data
        saleperson_names = ', '.join(user_name for user_name in self.user_ids.mapped('name') if user_name).strip(', ')
        if saleperson_names:
            saleperson_names = f'Sale Persons: {saleperson_names}'
        else:
            saleperson_names = 'Sale Persons: All'
        
        # header
        header_text = f'Duration : {start_date} to {end_date}'

        # Row 0
        sheet.write_merge(0, 0, 0, 2, company_name, cell_style_start)
        # Row 1
        sheet.write_merge(1, 1, 0, 2, 'Quotation Pipeline Report', cell_style_start)
        # Row 2
        sheet.write_merge(2, 3, 0, 2, header_text, cell_style_start)

        # Row 1 (printed date on right side)
        sheet.write_merge(1, 1, 3, 5, f'Printed Date - {print_date}', cell_style_end)

        sheet.write_merge(2, 3, 3, 5, f'{saleperson_names}', cell_style_end)

        headers = [
            "No",
            "Sale PIC",
        ]

        sub_headers = [
            "Draft Quotation",
            "Approved Quotation",
            "Accepted Quotation",
            "Lost",
        ]

        row = 5

        # Main headers
        for i, title in enumerate(headers):
            sheet.write_merge(row, row + 1, i, i, title, header_style)

        # Group header
        start_col = len(headers)      
        end_col = start_col + len(sub_headers) - 1

        sheet.write_merge(row, row, start_col, end_col, "Status", header_style,)

        # Sub headers
        for i, title in enumerate(sub_headers):
            sheet.write(row + 1, start_col + i, title, header_style,)

        row += 2
        index = 1

        total_quotation = 0
        total_accepted_quotation = 0
        total_draft_quotation = 0
        total_approved_quotation = 0
        total_lost_quotation = 0

        #Data rows
        for data in performance_data:
            sale_person = data.get('sale_person') or ""
            quotation = float(data.get('quotation') or 0)
            accepted_quotation = float(data.get('accepted_quotation') or 0)
            draft_quotation = float(data.get('draft_quotation') or 0)
            approved_quotation = float(data.get('approved_quotation') or 0)
            lost_quotation = float(data.get('lost_quotation') or 0)

            sheet.write(row, 0, index, cell_style_center)
            sheet.write(row, 1, sale_person, cell_style)
            sheet.write(row, 2, draft_quotation, number_style)
            sheet.write(row, 3, approved_quotation, number_style)
            sheet.write(row, 4, accepted_quotation, number_style)
            sheet.write(row, 5, lost_quotation, number_style)
            row += 1
            index += 1

            total_quotation += quotation
            total_accepted_quotation += accepted_quotation
            total_draft_quotation += draft_quotation
            total_approved_quotation += approved_quotation
            total_lost_quotation += lost_quotation
        # show total
        # total_conversion_rate = (f"{(total_accepted_quotation / total_quotation * 100):.2f} %"
        #                             if total_quotation else "0.00 %")
        
        sheet.write_merge(row, row, 0, 1, 'Total', header_style)
        sheet.write(row, 2, total_draft_quotation, number_style)
        sheet.write(row, 3, total_approved_quotation, number_style)
        sheet.write(row, 4, total_accepted_quotation, number_style)
        sheet.write(row, 5, total_lost_quotation, number_style)

        #Column width
        sheet.col(0).width = 3000
        sheet.col(1).width = 10000
        sheet.col(2).width = 6000
        sheet.col(3).width = 6000
        sheet.col(4).width = 6000
        sheet.col(5).width = 6000

        #Row Height
        # for row in range(100):
        #     sheet.row(row).height = 50

        # spacing row
        sheet.row(1).height = 30 * 30
        sheet.row(2).height = 30 * 30
        sheet.row(3).height = 30 * 30
        sheet.row(4).height = 30 * 30
        sheet.row(5).height = 30 * 30
        sheet.row(6).height = 30 * 30

        workbook.save(output)
        output.seek(0)

        self.excel_file = base64.b64encode(output.getvalue())
        self.file_name = "Quotation Pipeline Report.xls"

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{self._name}/{self.id}/excel_file/{self.file_name}?download=true',
            'close': True,
        }
    
    
    # Button Actions
    def generate_xlsx(self):
        pass
        report_data = self._get_report_data()
        return self._print_quotation_pipeline(report_data)
        

    