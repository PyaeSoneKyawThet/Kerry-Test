from odoo import models, fields
import io
import xlwt
import base64
from . import odoo_datetime_helper
from datetime import datetime, time, timedelta

class QuotationConversionWizard(models.TransientModel):
    _name = "quotation.conversion.wizard"
    _description = "Quotation Conversion Report"

    start_date = fields.Date(string="Start Date")
    end_date = fields.Date(string="End Date")

    print_date = fields.Datetime(default=fields.Datetime.now)
    excel_file = fields.Binary('Excel File')
    file_name = fields.Char('File Name')

    user_ids = fields.Many2many('res.users', string="Salesperson", domain=lambda self: self._get_sale_person_domain(), required=True)

    currency_ids = fields.Many2many('res.currency', string="Currency")
    # parent_categ_ids = fields.Many2many('product.category', domain= "[('parent_id', '=', False), ('show_in_quotation', '!=', False)]", string='BU')
    
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

                COUNT(*) AS quotation,

                COUNT(*) FILTER (
                    WHERE so.state = 'sale'
                    AND COALESCE(so.revise_state, '') != 'revise_approved'
                ) AS accepted_quotation

            FROM sale_order so 
                LEFT JOIN res_partner partner ON partner.id = so.partner_id
                LEFT JOIN user_info ui ON ui.user_id = so.user_id

            WHERE so.create_date >= %(start_date)s
                AND so.create_date <= %(end_date)s
                AND so.user_id IN %(user_ids)s
                AND so.currency_id IN %(currency_ids)s
                AND so.is_job_order = FALSE

            GROUP BY
                ui.user_name,
                so.user_id
            ORDER BY
                ui.user_name
        """

        user_ids = tuple(self.user_ids.ids)
        currency_ids = tuple(self.currency_ids.ids)

        params = {
            "start_date": datetime.combine(self.start_date, time.min),
            "end_date": datetime.combine(self.end_date, time.max),
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
    def _print_quotation_conversion(self, report_data):
        output = io.BytesIO()

        workbook = xlwt.Workbook(encoding='utf-8')
        sheet = workbook.add_sheet("Quotation Conversion Report")

        header_style = xlwt.easyxf('font: bold 1; align: horiz center;')
        cell_style_start = xlwt.easyxf('font: bold 1; align: horiz left, vert center, wrap on;')
        cell_style = xlwt.easyxf('align: horiz left;')
        cell_style_center = xlwt.easyxf('align: horiz center;')
        number_style = xlwt.easyxf('align: horiz right;')
        currency_style = xlwt.easyxf('align: horiz right;', num_format_str='#,##0.00')

        print_date = odoo_datetime_helper.local_time(
            self.print_date,
            self.env.user.tz or 'Asia/Yangon'
        )

        start_date = self.start_date.strftime('%d.%m.%Y') if self.start_date else ""
        end_date = self.end_date.strftime('%d.%m.%Y') if self.end_date else ""
        company_name = self.env.company.name
        performance_data = report_data

        # header
        header_text = f'Duration : {start_date} to {end_date} Report'

        if self.currency_ids:
            currencies = self.currency_ids
        else:
            sale_orders = self.env['sale.order'].search([
                ('create_date', '>=', self.start_date),
                ('create_date', '<=', self.end_date),
            ])
            currencies = sale_orders.mapped('currency_id')

        currency_names = ", ".join(sorted(set(currencies.mapped('name'))))
        currency_names = f'Currency: {currency_names}'
        
        # Row 0
        sheet.write_merge(0, 0, 0, 2, company_name, cell_style_start)
        # Row 1
        sheet.write_merge(1, 1, 0, 2, 'Quotation Conversion Report', cell_style_start)
        # Row 2
        sheet.write_merge(2, 3, 0, 2, header_text, cell_style_start)

        # Row 1 (printed date on right side)
        sheet.write_merge(1, 1, 3, 5, f'Printed Date - {print_date}', cell_style_start)

        sheet.write_merge(2, 3, 3, 5, currency_names, cell_style_start)

        # spacing row
        sheet.row(4).height = 20 * 20

        #Header (5 columns)
        headers = [
            "No",
            "Sale Rep",
            "Total Quotations",
            "Accepted Quotations",
            "Conversion Rate"
        ]

        row = 5
        for col, title in enumerate(headers):
            sheet.write(row, col, title, header_style)

        row += 1
        index = 1

        total_quotation = 0
        total_accepted_quotation = 0

        #Data rows
        for data in performance_data:
            sale_person = data.get('sale_person') or ""
            quotation = float(data.get('quotation') or 0)
            accepted_quotation = float(data.get('accepted_quotation') or 0)

            conversion_rate = (
                f"{(accepted_quotation / quotation * 100):.2f} %"
                if quotation else "0.00 %"
            )
            

            sheet.write(row, 0, index, cell_style_center)
            sheet.write(row, 1, sale_person, cell_style)
            sheet.write(row, 2, quotation, number_style)
            sheet.write(row, 3, accepted_quotation, number_style)
            sheet.write(row, 4, conversion_rate, number_style)
            row += 1
            index += 1

            total_quotation += quotation
            total_accepted_quotation += accepted_quotation
        
        # show total
        total_conversion_rate = (f"{(total_accepted_quotation / total_quotation * 100):.2f} %"
                                    if total_quotation else "0.00 %")
        
        sheet.write_merge(row, row, 0, 1, 'Total', header_style)
        sheet.write(row, 2, total_quotation, number_style)
        sheet.write(row, 3, total_accepted_quotation, number_style)
        sheet.write(row, 4, total_conversion_rate, number_style)

        #Column width
        for col in range(11):
            sheet.col(col).width = 5000

        workbook.save(output)
        output.seek(0)

        self.excel_file = base64.b64encode(output.getvalue())
        self.file_name = "Quotation Conversion Report.xls"

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{self._name}/{self.id}/excel_file/{self.file_name}?download=true',
            'close': True,
        }
    
    
    # Button Actions
    def generate_xlsx(self):
        pass
        report_data = self._get_report_data()
        return self._print_quotation_conversion(report_data)
        

    