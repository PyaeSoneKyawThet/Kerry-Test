from odoo import models, fields
import io
import xlwt
import base64
from . import odoo_datetime_helper
from datetime import datetime, time, timedelta
from odoo.tools.mail import html2plaintext

class ActivityProductivityWizard(models.TransientModel):
    _name = "activity.productivity.wizard"
    _description = "Activity and Productivity Wizard"

    start_date = fields.Date(string="Start Date")
    end_date = fields.Date(string="End Date")
    user_ids = fields.Many2many('res.users', string="Salesperson", domain=lambda self: self._get_sale_person_domain(), required=True)

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

    def _get_activity_type_sql(self):
        activity_types = self.env['mail.activity.type'].search([('active', '=', True), '|', ('res_model', '=', False), '|', ('res_model', '=', 'res.partner'), ('res_model', '=', 'sale.order')])
        activity_types_sql = ""

        for type in activity_types:
            activity_types_sql += f"""
                ,   CASE
                        WHEN act_rep.mail_activity_type_id = {type.id}
                        THEN 1 ELSE 0
                    END
                        AS activity_types_{type.id}
            """
        return activity_types_sql

    def _get_report_data(self):
        activity_types_sql = self._get_activity_type_sql()

        query = f"""
            SELECT 
                u.id as user_id,
                partner.name AS sale_person,
                act_rep.body AS remark

                {activity_types_sql}

            FROM crm_activity_report act_rep
            LEFT JOIN res_partner partner ON partner.id = act_rep.author_id
            LEFT JOIN res_users u ON u.partner_id = partner.id
            LEFT JOIN mail_activity_type mat ON mat.id = act_rep.mail_activity_type_id

            WHERE u.id IN %(user_ids)s
            AND act_rep.active = TRUE 
            AND mat.active = TRUE 
            AND (mat.res_model in ('res.partner', 'sale.order') OR mat.res_model IS NULL)
            AND act_rep.date BETWEEN %(start_date)s AND %(end_date)s

            GROUP BY u.id, partner.name, act_rep.body, act_rep.mail_activity_type_id
            
            ORDER BY u.id
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
    def _print_activity_productivity_xlsx(self, report_data):
        output = io.BytesIO()

        workbook = xlwt.Workbook(encoding='utf-8')
        sheet = workbook.add_sheet("Activity and Productivity Report")

        header_style = xlwt.easyxf('font: bold 1; align: horiz center, vert center, wrap on;')
        cell_style_start = xlwt.easyxf('font: bold 1; align: horiz left, vert center, wrap on;')
        cell_style = xlwt.easyxf('align: horiz center;')
        number_style = xlwt.easyxf('align: horiz center;')
        total_number_style = xlwt.easyxf('font: bold 1; align: horiz center;')

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
        sheet.write_merge(1, 1, 0, 3, 'Activity and Productivity Report', cell_style_start)
        # Row 2
        sheet.write_merge(2, 2, 0, 5, header_text, cell_style_start)
        # Row 3 (printed date on right side)
        sheet.write_merge(3, 3, 3, 7, f'Printed Date - {print_date}', cell_style)

        # spacing row
        sheet.row(4).height = 20 * 20
        sheet.row(5).height = 20 * 20
        sheet.row(6).height = 20 * 20

        #Header (2 columns)
        headers = [
            "No",
            "Sale Person",
        ]

        # Header
        row = 5
        for col, title in enumerate(headers):
            sheet.write_merge(row, row + 1, col, col, title, header_style)

        # sub header
        sub_headers = self.env['mail.activity.type'].search([('active', '=', True), '|', ('res_model', '=', False), '|', ('res_model', '=', 'res.partner'), ('res_model', '=', 'sale.order')]).mapped('name')
        sub_header_col = len(headers)
        for col, title in enumerate(sub_headers):
            col = sub_header_col + col
            sheet.write(row + 1, col, title, header_style)

        act_type_col_st = len(headers)
        act_type_col_end = len(headers) + len(sub_headers) - 1
        sheet.write_merge(row , row,  act_type_col_st, act_type_col_end, 'Activity Types' , header_style)

        remark_col_st = act_type_col_end + 1
        remark_col_end = remark_col_st + 4

        sheet.write_merge(
            row,
            row + 1,
            remark_col_st,
            remark_col_end,
            'Remark',
            header_style
        )

        row += 2
        no = 1

        activity_types = self.env['mail.activity.type'].search([('active', '=', True), '|', ('res_model', '=', False), '|', ('res_model', '=', 'res.partner'), ('res_model', '=', 'sale.order')])
        total_activity_type = {type.id: 0 for type in activity_types}

        #Data rows
        for data in leads:
            no = no
            sale_person = data.get('sale_person') or ""

            sheet.write(row, 0, no, cell_style)
            sheet.write(row, 1, sale_person, cell_style)

            col = 2

            # dynamic activity types
            for type in activity_types:
                field = f"activity_types_{type.id}"
                value = data.get(field) or 0

                total_activity_type[type.id] += value

                sheet.write(row, col, value, number_style)
                col += 1
            remark = html2plaintext(data.get('remark') or '')
            sheet.write_merge(row, row, col, col+4, remark or '', cell_style_start)

            row += 1
            no += 1

        # show total
        sheet.write_merge(row, row, 0, 1, 'Total', header_style)

        col = 2
        for type in activity_types:
            sheet.write(row, col, total_activity_type.get(type.id, 0), total_number_style)
            col += 1
            
        sheet.write_merge(row, row, col, col+4, '', cell_style_start)

        #Column width
        for col in range(len(headers) + len(sub_headers)):
            sheet.col(col).width = 5000

        workbook.save(output)
        output.seek(0)

        self.excel_file = base64.b64encode(output.getvalue())
        self.file_name = "Activity Productivity Report.xls"

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{self._name}/{self.id}/excel_file/{self.file_name}?download=true',
            'close': True,
        }
    
    
    # Button Actions
    def generate_xlsx(self):
        report_data = self._get_report_data()
        return self._print_activity_productivity_xlsx(report_data)
        

    