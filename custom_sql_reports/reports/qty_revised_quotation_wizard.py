from odoo import models, fields
import io
import xlwt
import base64
from . import odoo_datetime_helper
from datetime import datetime, time, timedelta

class QtyRevisedQuotation(models.TransientModel):
    _name = "qty.revised.quotation.wizard"
    _description = "Qty Of Revised Quotation"

    start_date = fields.Date(string="Start Date")
    end_date = fields.Date(string="End Date")

    print_date = fields.Datetime(default=fields.Datetime.now)
    excel_file = fields.Binary('Excel File')
    file_name = fields.Char('File Name')

    user_ids = fields.Many2many('res.users', string="Salesperson", domain=lambda self: self._get_sale_person_domain(), required=True)
    partner_ids = fields.Many2many('res.partner', string="Customers")

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
                WITH RECURSIVE 

                user_info AS (
                        SELECT 
                            u.id AS user_id,
                            p.name AS user_name
                        FROM res_users u
                        LEFT JOIN res_partner p ON p.id = u.partner_id
                    ),    
                
                revise_chain AS (
                    -- final quotations
                    SELECT
                        so.partner_id,
                        so.id,
                        so.name,
                        so.original_so_id,
                        so.id AS final_so_id,
                        so.name AS final_quotation,
                        0 AS revise_count
                    FROM sale_order so
                    WHERE so.state = 'sale'
                    AND so.original_so_id IS NOT NULL
                    AND COALESCE(so.is_vas, FALSE) = FALSE
                    AND (
                        NOT EXISTS (
                            SELECT 1
                            FROM sale_order child
                            WHERE child.original_so_id = so.id
                            AND child.state = 'sale'
                        )
                        OR so.is_renew_created = TRUE
                    )
                    AND so.create_date >= %(start_date)s
                    AND so.create_date <= %(end_date)s
                    AND so.currency_id IN %(currency_ids)s
                    AND so.partner_id IN %(partner_ids)s

                    UNION ALL

                    -- walk back to parent
                    SELECT
                        rc.partner_id,
                        parent.id,
                        parent.name,
                        parent.original_so_id,
                        rc.final_so_id,
                        rc.final_quotation,
                        rc.revise_count + 1
                    FROM sale_order parent
                    JOIN revise_chain rc
                        ON rc.original_so_id = parent.id
                    WHERE COALESCE(parent.is_renew_created, FALSE) = FALSE
                )
                SELECT
                    rc.partner_id,
                    rp.name AS partner_name,
                    ui.user_name AS sale_person,
                    rc.final_so_id,
                    rc.final_quotation,
                    MAX(rc.revise_count) AS revise_count
                FROM revise_chain rc
                LEFT JOIN res_partner rp ON rp.id = rc.partner_id
                LEFT JOIN user_info ui ON ui.user_id = rp.user_id
                WHERE
                (
                    rp.user_id IN %(user_ids)s
                )
                OR
                (
                    %(include_null_user)s = TRUE
                    AND rp.user_id IS NULL
                )
                GROUP BY
                    rc.final_so_id,
                    rc.final_quotation,
                    rc.partner_id,
                    rp.name,
                    ui.user_name
                HAVING MAX(rc.revise_count) > 0
                ORDER BY final_so_id DESC;
                """

        user_ids = tuple(self.user_ids.ids)
        currency_ids = tuple(self.currency_ids.ids)
        partner_ids = tuple(self.partner_ids.ids)

        params = {
            "start_date": datetime.combine(self.start_date, time.min),
            "end_date": datetime.combine(self.end_date, time.max),
            "user_ids": user_ids,
            "currency_ids": currency_ids,
            "partner_ids": partner_ids,
        }

        if not user_ids:
            params["user_ids"] = tuple(self.env['res.users'].search([]).ids)
            params["include_null_user"] = True
        else:
            params["include_null_user"] = False

        if not partner_ids:
            params["partner_ids"] = tuple(self.env['res.partner'].search([]).ids)
        
        if not currency_ids:
            params["currency_ids"] = tuple(self.env['res.currency'].search([]).ids)
        
        if not partner_ids:
            params["partner_ids"] = tuple(self.env['res.partner'].search([]).ids)


        self.env.cr.execute(query, params)
        data = self.env.cr.dictfetchall()
        return data
    
    # # excel print format
    def _print_qty_revised_quotation(self, report_data):
        output = io.BytesIO()

        workbook = xlwt.Workbook(encoding='utf-8')
        sheet = workbook.add_sheet("Qty Of Revised Quotation")

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

        # header
        header_text = f'Duration : {start_date} to {end_date}'

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
        sheet.write_merge(1, 1, 0, 2, 'Qty of Revised Quotation', cell_style_start)
        # Row 2
        sheet.write_merge(2, 3, 0, 2, header_text, cell_style_start)

        # Row 1 (printed date on right side)
        sheet.write_merge(1, 1, 3, 5, f'Printed Date - {print_date}', cell_style_start)

        sheet.write_merge(2, 3, 3, 5, currency_names, cell_style_start)

        sheet.write_merge(4, 4, 0, 2, 'Status: Quotation Revised', cell_style_start)

        # spacing row
        sheet.row(5).height = 20 * 20

        #Header (5 columns)
        headers = [
            "No",
            "Sale PIC",
            "Customer Name",
            "Final Quotation Number",
            "Revised Time",
        ]

        row = 6
        for col, title in enumerate(headers):
            sheet.write(row, col, title, header_style)
        sheet.row(row).height = 20 * 20

        row += 1
        index = 1

        #Data rows
        for data in report_data:
            partner_name = data.get('partner_name') or ""
            sale_person = data.get('sale_person') or ""
            final_quotation = data.get('final_quotation') or ""
            revise_count = data.get('revise_count') or ""

            sheet.write(row, 0, index, cell_style_center)
            sheet.write(row, 1, sale_person, cell_style)
            sheet.write(row, 2, partner_name, cell_style)
            sheet.write(row, 3, final_quotation, cell_style)
            sheet.write(row, 4, revise_count, number_style)
            row += 1
            index += 1


        #Column width
        for col in range(11):
            sheet.col(col).width = 5000

        workbook.save(output)
        output.seek(0)

        self.excel_file = base64.b64encode(output.getvalue())
        self.file_name = "Qty Of Revised Quotation.xls"

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{self._name}/{self.id}/excel_file/{self.file_name}?download=true',
            'close': True,
        }
    
    
    # Button Actions
    def generate_xlsx(self):
        pass
        report_data = self._get_report_data()
        return self._print_qty_revised_quotation(report_data)
        

    