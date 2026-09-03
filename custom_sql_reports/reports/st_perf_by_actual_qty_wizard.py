from odoo import models, fields
import io
import xlwt
import base64
from . import odoo_datetime_helper
from datetime import datetime, time, timedelta

class SaleTeamPerfActualQty(models.TransientModel):
    _name = "st.perf.actual.qty.wizard"
    _description = "Sale Team Performance By Actual Quantity Wizard"

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

    def _get_report_data(self):
        query = """
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
                        WHEN lead.date_seq1 BETWEEN DATE %(start_date)s AND DATE %(end_date)s
                        THEN 1 ELSE 0
                    END
                ), 0) AS hunting_count,

                COALESCE(SUM(
                    CASE
                        WHEN lead.date_seq3 BETWEEN DATE %(start_date)s AND DATE %(end_date)s
                        THEN 1 ELSE 0
                    END
                ), 0) AS projected_count,

                COALESCE(SUM(
                    CASE
                        WHEN lead.date_seq4 BETWEEN DATE %(start_date)s AND DATE %(end_date)s
                        THEN 1 ELSE 0
                    END
                ), 0) AS awarded_count,

                COALESCE(SUM(
                    CASE
                        WHEN lead.lost_date BETWEEN DATE %(start_date)s AND DATE %(end_date)s
                        AND lead.active = FALSE
                        AND lead.probability = 0
                        THEN 1 ELSE 0
                    END
                ), 0) AS lost_count

            FROM crm_lead lead
            LEFT JOIN user_info ui ON ui.user_id = lead.user_id
            LEFT JOIN crm_stage stage ON stage.id = lead.stage_id
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
        sheet = workbook.add_sheet("Sale Team Performance By Actual Quantity")

        header_style = xlwt.easyxf('font: bold 1; align: horiz center;')
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
        sheet.write_merge(1, 1, 0, 3, 'Sale Team Performance By Actual Quantity', cell_style_start)
        # Row 2
        sheet.write_merge(2, 2, 0, 5, header_text, cell_style_start)
        # Row 3 (printed date on right side)
        sheet.write_merge(3, 3, 3, 7, f'Printed Date - {print_date}', cell_style)

        # spacing row
        sheet.row(4).height = 20 * 20

        #Header (6 columns)
        headers = [
            "No",
            "Sale Person",
            "Hunting",
            "Projected",
            "Awarded",
            "Lost",
        ]

        row = 5
        for col, title in enumerate(headers):
            sheet.write(row, col, title, header_style)

        row += 1
        no = 1
        #Data rows
        for data in leads:
            no = no
            user_name = data.get('user_name') or ""
            hunting_count = data.get('hunting_count') or "0"
            projected_count = data.get('projected_count') or "0"
            awarded_count = data.get('awarded_count') or "0"
            lost_count = data.get('lost_count') or "0"
            

            sheet.write(row, 0, no, cell_style)
            sheet.write(row, 1, user_name, cell_style)
            sheet.write(row, 2, hunting_count, number_style)
            sheet.write(row, 3, projected_count, number_style)
            sheet.write(row, 4, awarded_count, number_style)
            sheet.write(row, 5, lost_count, number_style)
            
            row += 1
            no += 1

        #Column width
        for col in range(len(headers)):
            sheet.col(col).width = 5000

        workbook.save(output)
        output.seek(0)

        self.excel_file = base64.b64encode(output.getvalue())
        self.file_name = "Sale Team Performance By Acutal Quantity.xls"

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{self._name}/{self.id}/excel_file/{self.file_name}?download=true',
            'close': True,
        }
    
    
    # Button Actions
    def generate_xlsx(self):
        report_data = self._get_report_data()
        return self._print_sale_pipeline_xlsx(report_data)
        

    