from odoo import models, fields
import io
import xlwt
import base64
from . import odoo_datetime_helper
from datetime import datetime, time, timedelta

class QuotationWonLostWizard(models.TransientModel):
    _name = "quotation.won.lost.wizard"
    _description = "Quotation Won Lost Wizard"

    start_date = fields.Date(string="Start Date")
    end_date = fields.Date(string="End Date")
    user_ids = fields.Many2many('res.users', string="Salesperson", domain=lambda self: self._get_sale_person_domain(), required=True)
    # parent_categ_ids = fields.Many2many('product.category', domain= "[('parent_id', '=', False), ('show_in_quotation', '!=', False)]", string='BU')

    print_date = fields.Datetime(default=fields.Datetime.now)
    excel_file = fields.Binary('Excel File')
    file_name = fields.Char('File Name')

    def _get_sale_person_domain(self):
        current_user = self.env.user

        if current_user.has_group('sales_team.group_sale_manager'):
            partners = self.env['res.partner'].search([])
            users = partners.mapped('user_id')
            return [('id', 'in', users.ids)]

        return [('id', '=', current_user.id)]
    
    def _get_lost_reason_sql(self):
        lost_reasons = self.env['crm.lost.reason'].search([])
        lost_reason_sql = ""

        for reason in lost_reasons:
            lost_reason_sql += f"""
                , COALESCE(SUM(
                    CASE
                        WHEN lead.lost_reason_id = {reason.id}
                        AND lead.lost_date BETWEEN DATE %(start_date)s AND DATE %(end_date)s
                        AND lead.active = FALSE
                        AND lead.probability = 0
                        THEN 1 ELSE 0
                    END
                ), 0) AS lost_reason_{reason.id}
            """
        return lost_reason_sql

    def _get_report_data(self):
        lost_reason_sql = self._get_lost_reason_sql()
        
        query = f"""
            WITH user_info AS (
                SELECT 
                    u.id AS user_id,
                    p.name AS user_name
                FROM res_users u
                LEFT JOIN res_partner p ON p.id = u.partner_id
            )
            SELECT 
                ui.user_id AS id,
                ui.user_name AS user_name,

                COALESCE(SUM(
                    CASE
                        WHEN lead.date_seq4 BETWEEN DATE %(start_date)s AND DATE %(end_date)s
                        AND lead.active = TRUE
                        AND stage.is_won = TRUE
                        THEN 1 ELSE 0
                    END
                ), 0) AS awarded_count,

                COALESCE(SUM(
                    CASE
                        WHEN lead.lost_date BETWEEN DATE %(start_date)s AND DATE %(end_date)s
                        AND lead.active = FALSE
                        AND lead.probability = 0
                        AND lead.lost_reason_id IS NULL
                        THEN 1 ELSE 0
                    END
                ), 0) AS lost_reason_empty

                {lost_reason_sql}

            FROM crm_lead lead
            LEFT JOIN user_info ui ON ui.user_id = lead.user_id
            LEFT JOIN crm_stage stage ON stage.id = lead.stage_id
            LEFT JOIN crm_lost_reason lost_reason ON lost_reason.id = lead.lost_reason_id
            WHERE lead.type = 'opportunity'
            AND lead.user_id IN %(user_ids)s
            GROUP BY ui.user_id, ui.user_name
            ORDER BY ui.user_name
        """

        start_dt = datetime.combine(self.start_date, time.min)   # 00:00:00
        end_dt = datetime.combine(self.end_date, time.max)       # 23:59:59.999999
        user_ids = tuple(self.user_ids.ids)

        params = {
            "start_date": start_dt,
            "end_date": end_dt,
            "user_ids": user_ids,
        }

        if not user_ids:
            params["user_ids"] = tuple(self.env['res.users'].search([]).ids)
        

        self.env.cr.execute(query, params)
        data = self.env.cr.dictfetchall()
        return data
    
    # excel print format
    def _print_sale_pipeline_xlsx(self, report_data):
        output = io.BytesIO()

        workbook = xlwt.Workbook(encoding='utf-8')
        sheet = workbook.add_sheet("Quotation Won / Lost Analysis")

        header_style = xlwt.easyxf('font: bold 1; align: horiz center, vert center, wrap on;')
        cell_style_start = xlwt.easyxf('font: bold 1; align: horiz left, vert center, wrap on;')
        cell_style = xlwt.easyxf('align: horiz center;')
        number_style = xlwt.easyxf('align: horiz center;')

        print_date = odoo_datetime_helper.local_time(
            self.print_date,
            self.env.user.tz or 'Asia/Yangon'
        )

        start_date = self.start_date.strftime('%d.%m.%Y') if self.start_date else ""
        end_date = self.end_date.strftime('%d.%m.%Y') if self.end_date else ""
        company_id = self.env.company
        company_name = company_id.name
        leads = report_data

        # header
        header_text = f'Duration : {start_date} to {end_date}'
        # Row 0
        sheet.write_merge(0, 0, 0, 3, company_name, cell_style_start)
        # Row 1
        sheet.write_merge(1, 1, 0, 3, 'Quotation Win / Loss Analysis Report', cell_style_start)
        # Row 2
        sheet.write_merge(2, 2, 0, 5, header_text, cell_style_start)
        # Row 3 (printed date on right side)
        sheet.write_merge(3, 3, 3, 7, f'Printed Date - {print_date}', cell_style)

        # spacing row
        sheet.row(4).height = 20 * 20
        sheet.row(5).height = 20 * 20
        sheet.row(6).height = 20 * 20

        #Header (3 columns)
        headers = [
            "No",
            "Sale Person",
            "Win",
        ]

        # Header
        row = 5
        for col, title in enumerate(headers):
            sheet.write_merge(row, row + 1, col, col, title, header_style)

        # sub header
        sub_headers = self.env['crm.lost.reason'].search([]).mapped('name')
        sub_header_col = len(headers)
        for col, title in enumerate(sub_headers):
            col = sub_header_col + col
            sheet.write(row + 1, col, title, header_style)

        reason_col_st = len(headers)
        reason_col_end = len(headers) + len(sub_headers)
        sheet.write_merge(row , row,  reason_col_st, reason_col_end, 'Loss Reason' , header_style)

        row += 2
        no = 1

        lost_reasons = self.env['crm.lost.reason'].search([])
        total_awarded = 0
        total_lost_empty = 0
        total_lost_by_reason = {reason.id: 0 for reason in lost_reasons}

        #Data rows
        for data in leads:
            no = no
            user_name = data.get('user_name') or ""
            awarded_count = data.get('awarded_count') or 0

            total_awarded += awarded_count

            sheet.write(row, 0, no, cell_style)
            sheet.write(row, 1, user_name, cell_style)
            sheet.write(row, 2, awarded_count, number_style)

            col = 3

            # dynamic lost reasons
            for reason in lost_reasons:
                field = f"lost_reason_{reason.id}"
                value = data.get(field) or 0

                total_lost_by_reason[reason.id] += value

                sheet.write(row, col, value, number_style)
                col += 1

            # empty reason last
            lost_reason_empty = data.get('lost_reason_empty')
            total_lost_empty += lost_reason_empty

            sheet.write(row, col, lost_reason_empty or '', number_style)

            row += 1
            no += 1

        # show total
        sheet.write_merge(row, row, 0, 1, 'Total', header_style)
        sheet.write(row, 2, total_awarded, number_style)

        col = 3
        for reason in lost_reasons:
            sheet.write(row, col, total_lost_by_reason.get(reason.id, 0), number_style)
            col += 1
        sheet.write(row, col, total_lost_empty or '', number_style)

        #Column width
        for col in range(len(headers) + len(sub_headers)):
            sheet.col(col).width = 5000

        workbook.save(output)
        output.seek(0)

        self.excel_file = base64.b64encode(output.getvalue())
        self.file_name = "Quotation Won Lost Analysis Report.xls"

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{self._name}/{self.id}/excel_file/{self.file_name}?download=true',
            'close': True,
        }
    
    
    # Button Actions
    def generate_xlsx(self):
        report_data = self._get_report_data()
        return self._print_sale_pipeline_xlsx(report_data)
        

    