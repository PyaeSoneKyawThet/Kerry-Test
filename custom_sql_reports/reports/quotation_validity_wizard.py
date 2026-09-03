from odoo import models, fields
import io
import xlwt
import base64
from . import odoo_datetime_helper
from datetime import datetime, time, timedelta

class QuotationValidityWizard(models.TransientModel):
    _name = "quotation.validity.wizard"
    _description = "Quotation Validity Report"

    report_date = fields.Date(string="Report Date", default=fields.Date.today())

    print_date = fields.Datetime(default=fields.Datetime.now)
    excel_file = fields.Binary('Excel File')
    file_name = fields.Char('File Name')

    user_ids = fields.Many2many('res.users', string="Salesperson", domain=lambda self: self._get_sale_person_domain(), required=True)

    currency_ids = fields.Many2many('res.currency', string="Currency")
    
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
                COUNT(*) FILTER (
                    WHERE so.validity_date >= %(start_date)s
                    AND so.validity_date <= %(start_date)s + INTERVAL '15 days'
                ) AS before_15_days,

                COUNT(*) FILTER (
                    WHERE so.validity_date >= %(start_date)s
                    AND so.validity_date <= %(start_date)s + INTERVAL '7 days'
                ) AS before_7_days,

                COUNT(*) FILTER (
                    WHERE so.validity_date >= %(start_date)s
                    AND so.validity_date <= %(start_date)s + INTERVAL '3 days'
                ) AS before_3_days

            FROM sale_order so 
                LEFT JOIN res_partner partner ON partner.id = so.partner_id
                LEFT JOIN user_info ui ON ui.user_id = so.user_id

            WHERE so.validity_date >= %(start_date)s
                AND so.validity_date <= %(start_date)s + INTERVAL '15 days'
                AND so.user_id IN %(user_ids)s
                AND so.currency_id IN %(currency_ids)s
                AND so.is_job_order = FALSE
                AND so.state = 'sale'
                AND COALESCE(so.revise_state, '') != 'revise_approved'

            GROUP BY
                so.user_id,
                ui.user_name
            ORDER BY
                ui.user_name
        """

        user_ids = tuple(self.user_ids.ids)
        currency_ids = tuple(self.currency_ids.ids)

        params = {
            "start_date": datetime.combine(self.report_date, time.min),
            "user_ids": user_ids,
            "currency_ids": currency_ids,
        }


        if not user_ids:
            params["user_ids"] = tuple(self.env['res.users'].search([]).ids)
        
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
        cell_style = xlwt.easyxf('align: horiz left;')
        cell_style_center = xlwt.easyxf('align: horiz center;')
        number_style = xlwt.easyxf('align: horiz right;')

        print_date = odoo_datetime_helper.local_time(
            self.print_date,
            self.env.user.tz or 'Asia/Yangon'
        )

        report_date = self.report_date.strftime('%d.%m.%Y') if self.report_date else ""
        
        company_name = self.env.company.name

        # if self.currency_ids:
        #     currencies = self.currency_ids
        # else:
        #     sale_orders = self.env['sale.order'].search([
        #         ('create_date', '>=', datetime.combine(self.report_date, time.min)),
        #         ('create_date', '<=', datetime.combine(self.report_date, time.max)),
        #     ])
        #     currencies = sale_orders.mapped('currency_id')

        # currency_names = ", ".join(sorted(set(currencies.mapped('name'))))
        # currency_names = f'Currency: {currency_names}'

        # header
        header_text = f'Report date: {report_date}'
        
        # Row 0
        sheet.write_merge(0, 0, 0, 2, company_name, cell_style_start)
        # Row 1
        sheet.write_merge(1, 1, 0, 2, 'Quotation Validity Report', cell_style_start)
        # Row 1
        sheet.write_merge(1, 1, 3, 5, header_text, cell_style_start)

        # Row 0 (printed date on right side)
        sheet.write_merge(0, 0, 3, 5, f'Printed Date: {print_date}', cell_style_start)

        # sheet.write_merge(2, 3, 3, 5, currency_names, cell_style_start)

        # spacing row
        sheet.row(2).height = 20 * 20

        row = 3

        #Header (3 columns)
        sheet.write_merge(row, row + 1, 0, 0, "No", header_style)
        sheet.write_merge(row, row + 1, 1, 1, "Sale PIC", header_style)

        sheet.write_merge(row, row, 2, 4, "Validity Status (Qty)", header_style)
        row += 1

        sheet.write(row, 2, "Before 15 days", header_style)
        sheet.write(row, 3, "Before 7 days",  header_style)
        sheet.write(row, 4, "Before 3 days",  header_style)

        row += 1
        index = 1
        total_before_15_days = 0
        total_before_7_days = 0
        total_before_3_days = 0

        #Data rows
        for data in report_data:
            sale_person = data.get('sale_person') or ""
            before_15_days = float(data.get('before_15_days') or 0)
            before_7_days = float(data.get('before_7_days') or 0)
            before_3_days = float(data.get('before_3_days') or 0)

            sheet.write(row, 0, index,          cell_style_center)
            sheet.write(row, 1, sale_person,    cell_style)
            sheet.write(row, 2, before_15_days, number_style)
            sheet.write(row, 3, before_7_days,  number_style)
            sheet.write(row, 4, before_3_days,  number_style)
            row += 1
            index += 1

            total_before_15_days += before_15_days
            total_before_7_days += before_7_days
            total_before_3_days += before_3_days
        
        # show total
        sheet.write_merge(row, row, 0, 1, 'Total', header_style)
        sheet.write(row, 2, total_before_15_days, number_style)
        sheet.write(row, 3, total_before_7_days, number_style)
        sheet.write(row, 4, total_before_3_days, number_style)

        #Column width
        for col in range(11):
            sheet.col(col).width = 5000

        workbook.save(output)
        output.seek(0)

        self.excel_file = base64.b64encode(output.getvalue())
        self.file_name = "Quotation Validity Report.xls"

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
        

    