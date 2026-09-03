from odoo import models, fields
import io
import xlwt
import base64
from . import odoo_datetime_helper
from datetime import datetime, time, timedelta

class SaleTeamPerformanceReport(models.TransientModel):
    _name = "sale.team.performance.wizard"
    _description = "Summary Sales Team Performance By Revenue Report"

    start_date = fields.Date(string="Start Date")
    end_date = fields.Date(string="End Date")
    # user_ids = fields.Many2many('res.users', string="Salesperson")

    print_date = fields.Datetime(default=fields.Datetime.now)
    excel_file = fields.Binary('Excel File')
    file_name = fields.Char('File Name')

    user_ids = fields.Many2many('res.users', string="Salesperson", domain=lambda self: self._get_sale_person_domain(), required=True)

    currency_ids = fields.Many2many('res.currency', string="Currency")
    parent_categ_ids = fields.Many2many('product.category', domain= "[('parent_id', '=', False), ('show_in_quotation', '!=', False)]", string='BU')
    
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

            analytic_info AS (
                SELECT
                    aaa.id AS analytic_id,
                    aaa.name AS sub_bu
                FROM account_analytic_account aaa
                LEFT JOIN account_analytic_plan aap ON aap.id = aaa.plan_id
                WHERE REPLACE(
                    LOWER(aap.name->>'en_US'),
                    ' ',
                    ''
                ) LIKE '%%subbu%%'
            ),

            sale_line_analytic AS (
                SELECT
                    sol.id AS sale_order_line_id,

                    (
                        regexp_matches(
                            jsonb_object_keys(sol.analytic_distribution),
                            '\d+',
                            'g'
                        )
                    )[1]::int AS analytic_account_id

                FROM sale_order_line sol
                WHERE sol.analytic_distribution IS NOT NULL
            )

            SELECT
                ui.user_id as user_id,
                ui.user_name AS sale_person,
                TO_CHAR(DATE_TRUNC('month', so.job_date), 'Mon YYYY') AS job_month,
                category.name AS bu,
                ai.sub_bu AS sub_bu,
                SUM(sol.price_total) AS billing_amount,
                currency.symbol AS currency_symbol,
                currency.name AS currency_name

            FROM sale_order_line sol
                 LEFT JOIN sale_order so ON so.id = sol.order_id
                 LEFT JOIN res_partner partner ON partner.id = so.partner_id
                 LEFT JOIN user_info ui ON ui.user_id = partner.user_id
                 LEFT JOIN res_currency currency ON currency.id = sol.currency_id
                 LEFT JOIN product_product pp ON pp.id = sol.product_id
                 LEFT JOIN product_template pt ON pt.id = pp.product_tmpl_id
                 LEFT JOIN product_category category ON category.id = pt.categ_id
                 LEFT JOIN sale_line_analytic sla ON sla.sale_order_line_id = sol.id
                 INNER JOIN analytic_info ai ON ai.analytic_id = sla.analytic_account_id

            WHERE so.is_job_order = TRUE
                  AND so.state IN ('sale', 'done')
                  AND so.job_date >= %(start_date)s
                  AND so.job_date <= %(end_date)s
                  AND partner.user_id IN %(user_ids)s
                  AND so.currency_id IN %(currency_ids)s
                  AND category.id IN %(parent_categ_ids)s

            GROUP BY
                ui.user_id,
                ui.user_name,
                DATE_TRUNC('month', so.job_date),
                category.name,
                ai.sub_bu,
                currency.id

            ORDER BY
                DATE_TRUNC('month', so.job_date),
                ui.user_name,
                category.name,
                ai.sub_bu
        """

        user_ids = tuple(self.user_ids.ids)
        currency_ids = tuple(self.currency_ids.ids)
        parent_categ_ids = tuple(self.parent_categ_ids.ids)

        params = {
            "start_date": self.start_date,
            "end_date": self.end_date,
            "user_ids": user_ids,
            "currency_ids": currency_ids,
            "parent_categ_ids": parent_categ_ids,
        }


        if not user_ids:
            params["user_ids"] = tuple(self.env['res.users'].search([]).ids)
        
        if not currency_ids:
            params["currency_ids"] = tuple(self.env['res.currency'].search([]).ids)

        if not parent_categ_ids:
            params["parent_categ_ids"] = tuple(self.env['product.category'].search([]).ids)


        self.env.cr.execute(query, params)
        data = self.env.cr.dictfetchall()
        return data
    
    # excel print format
    def _print_sale_team_performance_xlsx(self, report_data):
        output = io.BytesIO()

        workbook = xlwt.Workbook(encoding='utf-8')
        sheet = workbook.add_sheet("Summary Sales Team Performance By Revenue")

        header_style = xlwt.easyxf('font: bold 1; align: horiz center;')
        cell_style_start = xlwt.easyxf('font: bold 1; align: horiz left, vert center, wrap on;')
        cell_style = xlwt.easyxf('align: horiz left;')
        number_style = xlwt.easyxf('align: horiz right;')
        currency_style = xlwt.easyxf('align: horiz right;', num_format_str='#,##0.00')
        date_style = xlwt.easyxf('align: horiz right;', num_format_str='DD/MM/YYYY')

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

        currency_names = ", ".join(
                            list(set(
                                data.get('currency_name')
                                for data in performance_data
                                if data.get('currency_name')
                            ))
                        )
        currency_names = f'Currency: {currency_names}'
        
        # Row 0
        sheet.write_merge(0, 0, 0, 3, company_name, cell_style_start)
        # Row 1
        sheet.write_merge(1, 1, 0, 3, 'Summary Sales Team Performance By Revenue', cell_style_start)
        # Row 2
        sheet.write_merge(2, 3, 0, 3, header_text, cell_style_start)
        sheet.write_merge(2, 3, 5, 6, currency_names, cell_style_start)

        # Row 3 (printed date on right side)
        sheet.write_merge(1, 1, 5, 6, f'Printed Date - {print_date}', cell_style)

        # spacing row
        sheet.row(4).height = 20 * 20

        #Header (11 columns)
        headers = [
            "No",
            "Sale Person",
            "Job Month",
            "BU",
            "SubBU",
            "Total Amount"
        ]

        row = 5
        for col, title in enumerate(headers):
            sheet.write(row, col, title, header_style)

        row += 1

        index = 1

        #Data rows
        for data in performance_data:
            job_month = data.get('job_month') or ""
            sale_person = data.get('sale_person') or ""
            bu = data.get('bu') or ""
            sub_bu = data.get('sub_bu') or ""
            if isinstance(sub_bu, dict):
                sub_bu = sub_bu.get('en_US', '')
            billing_amount = data.get('billing_amount') or ""
            currency_symbol = data.get('currency_symbol') or ""

            sheet.write(row, 0, index, cell_style)
            sheet.write(row, 1, sale_person, cell_style)
            sheet.write(row, 2, job_month, cell_style)
            sheet.write(row, 3, bu, cell_style)
            sheet.write(row, 4, sub_bu, cell_style)
            sheet.write(row, 5, billing_amount, currency_style)
            sheet.write(row, 6, currency_symbol, cell_style)
            row += 1
            index += 1

        #Column width
        for col in range(11):
            sheet.col(col).width = 5000

        workbook.save(output)
        output.seek(0)

        self.excel_file = base64.b64encode(output.getvalue())
        self.file_name = "Summary Sales Team Performance By Revenue Report.xls"

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{self._name}/{self.id}/excel_file/{self.file_name}?download=true',
            'close': True,
        }
    
    
    # Button Actions
    def generate_xlsx(self):
        report_data = self._get_report_data()
        return self._print_sale_team_performance_xlsx(report_data)
        

    