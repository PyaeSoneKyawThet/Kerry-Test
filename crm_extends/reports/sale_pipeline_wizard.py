from odoo import models, fields
import io
import xlwt
import base64
from . import odoo_datetime_helper
from datetime import datetime, time, timedelta

class SalePipeLineReport(models.TransientModel):
    _name = "sale.pipeline.wizard"
    _description = "Sale Pipe Line Report"

    start_date = fields.Date(string="Start Date")
    end_date = fields.Date(string="End Date")
    user_ids = fields.Many2many('res.users', string="Salesperson", domain=lambda self: self._get_sale_person_domain(), required=True)
    parent_categ_ids = fields.Many2many('product.category', domain= "[('parent_id', '=', False), ('show_in_quotation', '!=', False)]", string='BU')

    print_date = fields.Datetime(default=fields.Datetime.now)
    excel_file = fields.Binary('Excel File')
    file_name = fields.Char('File Name')

    def _get_sale_person_domain(self):
        current_user = self.env.user

        if current_user.has_group('sales_team.group_sale_manager'):
            partners = self.env['res.partner'].search([])
            users = partners.mapped('sale_pic_ids')
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
            ),

            category_info AS (
                SELECT 
                    pc.id AS category_id,
                    pc.name AS sub_bu,
                    parent_pc.name AS bu,
                    parent_pc.id AS bu_id
                FROM product_category pc
                LEFT JOIN product_category parent_pc ON parent_pc.id = pc.parent_id
            )

            SELECT 
                lead.id AS id,
                lead.crm_ref AS crm_ref,
                lead.create_date AS create_date,
                lead.currency_id AS currency_id,
                lead.volume AS volume,
                lead.commodity AS commodity,
                lead.expected_revenue AS expected_revenue,
                lead.probability AS probability,
                lead.date_deadline AS date_deadline,
                stage.name AS stage_name,
                ui.user_name AS user_name,
                partner.name AS customer,
                currency.name AS currency_name,
                ci.bu,
                ci.sub_bu

            FROM crm_lead lead
            LEFT JOIN user_info ui ON ui.user_id = lead.user_id
            LEFT JOIN res_partner partner ON partner.id = lead.partner_id
            LEFT JOIN crm_stage stage ON stage.id = lead.stage_id
            LEFT JOIN res_currency currency ON currency.id = lead.currency_id
            LEFT JOIN category_info ci ON ci.category_id = lead.category_id
            WHERE lead.create_date >= %(start_date)s
            AND lead.create_date <= %(end_date)s
            AND lead.type = 'opportunity'
            AND lead.active = TRUE
        """

        start_dt = datetime.combine(self.start_date, time.min)   # 00:00:00
        end_dt = datetime.combine(self.end_date, time.max)       # 23:59:59.999999
        user_ids = tuple(self.user_ids.ids)
        parent_categ_ids = tuple(self.parent_categ_ids.ids)

        params = {
            "start_date": start_dt,
            "end_date": end_dt,
        }

        if user_ids:
            query += "AND ui.user_id IN %(user_ids)s"
            params["user_ids"] = user_ids
        
        if parent_categ_ids:
            query += "AND ci.bu_id IN %(parent_categ_ids)s"
            params["parent_categ_ids"] = parent_categ_ids

        self.env.cr.execute(query, params)
        data = self.env.cr.dictfetchall()
        return data
    
    # excel print format
    def _print_sale_pipeline_xlsx(self, report_data):
        output = io.BytesIO()

        workbook = xlwt.Workbook(encoding='utf-8')
        sheet = workbook.add_sheet("Sale Pipeline Report")

        header_style = xlwt.easyxf('font: bold 1; align: horiz center;')
        cell_style_start = xlwt.easyxf('font: bold 1; align: horiz left, vert center, wrap on;')
        cell_style = xlwt.easyxf('align: horiz left;')
        cell_style_right = xlwt.easyxf('align: horiz right;')
        number_style = xlwt.easyxf('align: horiz right;')
        currency_style = xlwt.easyxf('align: horiz right;', num_format_str='#,##0.00')
        date_style = xlwt.easyxf('align: horiz right;', num_format_str='DD/MM/YYYY')

        print_date = odoo_datetime_helper.local_time(
            self.print_date,
            self.env.user.tz or 'Asia/Yangon'
        )

        start_date = self.start_date.strftime('%d.%m.%Y') if self.start_date else ""
        end_date = self.end_date.strftime('%d.%m.%Y') if self.end_date else ""
        company_id = self.env.company
        company_name = company_id.name
        company_currency_id = company_id.currency_id
        leads = report_data

        # header
        header_text = f'Duration : {start_date} to {end_date}'
        # Row 0
        sheet.write_merge(0, 0, 0, 3, company_name, cell_style_start)
        # Row 1
        sheet.write_merge(1, 1, 0, 3, 'Sale Pipeline Report', cell_style_start)
        # Row 2
        sheet.write_merge(2, 2, 0, 5, header_text, cell_style_start)
        # Row 3 (printed date on right side)
        sheet.write_merge(3, 3, 8, 10, f'Printed Date - {print_date}', cell_style)

        # spacing row
        sheet.row(4).height = 20 * 20

        #Header (12 columns)
        headers = [
            "CRM No",
            "Sale Person",
            "Created Date",
            "Customer Name",
            "Expected Volume",
            "Commodity",
            "Expected Revenue",
            "Currency",
            "Possibility %",
            "Expected Closing Date ",
            "BU",
            "Sub BU",
            "CRM Stage"
        ]

        row = 5
        for col, title in enumerate(headers):
            sheet.write(row, col, title, header_style)

        row += 1

        #Data rows
        for data in leads:
            crm_ref = data.get('crm_ref') or ""
            create_date = data.get('create_date') or ""
            volume = data.get('volume') or ""
            commodity = data.get('commodity') or ""

            expected_revenue = data.get('expected_revenue') or 0.0
            currency_name = data.get('currency_name') or company_currency_id.name


            probability = data.get('probability') or ""
            date_deadline = data.get('date_deadline') or ""
            user_name = data.get('user_name') or ""
            customer = data.get('customer') or ""
            bu = data.get('bu') or ""
            sub_bu = data.get('sub_bu') or ""
            stage_name = data.get('stage_name') or {}
            stage_name_value = stage_name.get('en_US') or next(iter(stage_name.values()), False)
            

            sheet.write(row, 0, crm_ref, cell_style)
            sheet.write(row, 1, user_name, cell_style)
            sheet.write(row, 2, create_date, date_style)
            sheet.write(row, 3, customer, cell_style)
            sheet.write(row, 4, volume, number_style)
            sheet.write(row, 5, commodity, number_style)
            sheet.write(row, 6, expected_revenue, currency_style)
            sheet.write(row, 7, currency_name, cell_style_right)
            sheet.write(row, 8, probability, number_style)
            sheet.write(row, 9, date_deadline, date_style)
            sheet.write(row, 10, bu, cell_style)
            sheet.write(row, 11, sub_bu, cell_style)
            sheet.write(row, 12, stage_name_value, cell_style)
            row += 1

        #Column width
        for col in range(len(headers)):
            sheet.col(col).width = 5000

        workbook.save(output)
        output.seek(0)

        self.excel_file = base64.b64encode(output.getvalue())
        self.file_name = "sale_pipeline_report.xls"

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{self._name}/{self.id}/excel_file/{self.file_name}?download=true',
            'close': True,
        }
    
    
    # Button Actions
    def generate_xlsx(self):
        report_data = self._get_report_data()
        return self._print_sale_pipeline_xlsx(report_data)
        

    