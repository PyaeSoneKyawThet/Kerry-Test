from odoo import models, fields
import io
import xlwt
import base64
from . import odoo_datetime_helper
from datetime import datetime, time, timedelta

class QuotationValidityDetailsWizard(models.TransientModel):
    _name = "quotation.validity.details.wizard"
    _description = "Quotation Validity Details Report"

    report_date = fields.Date(string="Report Date", default=fields.Date.today())
    before_expire = fields.Integer(string="Before expire")
    user_ids = fields.Many2many('res.users', string="Salesperson", domain=lambda self: self._get_sale_person_domain(), required=True)
    currency_ids = fields.Many2many('res.currency', string="Currency")

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
            WITH 
            user_info AS (
                SELECT 
                    u.id AS user_id,
                    p.name AS user_name
                FROM res_users u
                LEFT JOIN res_partner p ON p.id = u.partner_id
            )

            SELECT
                ui.user_name AS sale_person,
                so.user_id AS user_id,
                partner.name AS customer_name,
                so.name AS quotation_no,
                so.validity_date AS expired_date,
                DATE(so.validity_date) - DATE(CURRENT_TIMESTAMP) AS expired_in_day

            FROM sale_order so 
                LEFT JOIN res_partner partner ON partner.id = so.partner_id
                LEFT JOIN user_info ui ON ui.user_id = so.user_id

            WHERE so.validity_date >= %(start_date)s
                AND so.validity_date <= %(end_date)s
                AND so.user_id IN %(user_ids)s
                AND so.currency_id IN %(currency_ids)s
                AND so.is_job_order = FALSE
                AND so.state = 'sale'
                AND COALESCE(so.revise_state, '') != 'revise_approved'

            GROUP BY
                so.user_id,
                ui.user_name,
                partner.name,
                so.name,
                so.validity_date

            ORDER BY
                ui.user_name
        """

        user_ids = tuple(self.user_ids.ids)
        currency_ids = tuple(self.currency_ids.ids)

        params = {
            "start_date": datetime.combine(self.report_date, time.min),
            "end_date": datetime.combine(self.report_date + timedelta(self.before_expire), time.max),
            "user_ids": user_ids,
            "currency_ids": currency_ids,
        }
        
        if not currency_ids:
            params["currency_ids"] = tuple(self.env['res.currency'].search([]).ids)


        self.env.cr.execute(query, params)
        data = self.env.cr.dictfetchall()
        return data
    
    # # excel print format
    def _print_quotation_validity(self, report_data):
        output = io.BytesIO()

        workbook = xlwt.Workbook(encoding='utf-8')
        sheet = workbook.add_sheet("Quotation Validity Report")

        header_style = xlwt.easyxf('font: bold 1; align: horiz center, vert center;')
        cell_style_start = xlwt.easyxf('font: bold 1; align: horiz left, vert center, wrap on;')
        cell_style_end = xlwt.easyxf('font: bold 1; align: horiz right, vert center, wrap on;')
        cell_style = xlwt.easyxf('align: horiz left;')
        cell_style_center = xlwt.easyxf('align: horiz center;')
        number_style = xlwt.easyxf('align: horiz right;')

        print_date = odoo_datetime_helper.local_time(
            self.print_date,
            self.env.user.tz or 'Asia/Yangon'
        )

        report_date = self.report_date.strftime('%Y-%m-%d') if self.report_date else ""
        
        company_name = self.env.company.name

        # header
        report_date_text = f'Report Date: {report_date}'
        expired_duration_text = f'Expired Duration : Before expire {self.before_expire} days'
        currency_names = ', '.join(currency for currency in self.currency_ids.mapped('name') if currency).strip(', ')
        currency_names = f'Currency: {currency_names}'
        
        # Row 0
        sheet.write_merge(0, 0, 0, 2, company_name, cell_style_start)
        # Row 1
        sheet.write_merge(1, 1, 0, 2, 'Quotation Validity Details', cell_style_start)
        # Row 2
        sheet.write_merge(2, 3, 0, 1, expired_duration_text, cell_style_start)
        sheet.write_merge(2, 3, 2, 3, report_date_text, cell_style_end)
        sheet.write_merge(2, 3, 4, 5, currency_names, cell_style_end)
        
        # Row 0 (printed date on right side)
        sheet.write_merge(0, 0, 3, 5, f'Printed Date: {print_date}', cell_style_end)

        # spacing row
        sheet.row(0).height = 20 * 20
        sheet.row(1).height = 20 * 20
        sheet.row(2).height = 20 * 20

        row = 3

        #Header (6 columns)
        headers = [
            "No",
            "Sale PIC",
            "Customer Name",
            "Quotation Number",
            "Expired Date",
            "Expired In Day"
        ]

        row = 5
        for col, title in enumerate(headers):
            sheet.write(row, col, title, header_style)

        row += 1

        index = 1

        #Data rows
        for data in report_data:
            sale_person = data.get('sale_person') or ""
            customer_name = data.get('customer_name') or ""
            quotation_no = data.get('quotation_no') or ""
            expired_date = data.get('expired_date').strftime('%Y-%m-%d') if data.get('expired_date') else ""
            expired_in_day = float(data.get('expired_in_day') or 0)

            sheet.write(row, 0, index,          cell_style_center)
            sheet.write(row, 1, sale_person,    cell_style)
            sheet.write(row, 2, customer_name, cell_style)
            sheet.write(row, 3, quotation_no,  cell_style)
            sheet.write(row, 4, expired_date,  cell_style)
            sheet.write(row, 5, expired_in_day,  number_style)
            row += 1
            index += 1

        #Column width
        sheet.col(0).width = 3000
        sheet.col(1).width = 6000
        sheet.col(2).width = 10500
        sheet.col(3).width = 6000
        sheet.col(4).width = 4000
        sheet.col(5).width = 4000

        workbook.save(output)
        output.seek(0)

        self.excel_file = base64.b64encode(output.getvalue())
        self.file_name = "Quotation Validity Details Report.xls"

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{self._name}/{self.id}/excel_file/{self.file_name}?download=true',
            'close': True,
        }
    
    
    # Button Actions
    def generate_xlsx(self):
        pass
        report_data = self._get_report_data()
        return self._print_quotation_validity(report_data)
        

    