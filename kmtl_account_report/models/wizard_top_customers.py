from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import io
import base64


class KMTLTopCustomersWizard(models.TransientModel):
    _name = 'kmtl.top.customers'
    _description = 'Top Customers Report Wizard'

    date_from = fields.Date(string='Start Date', required=True)
    date_to = fields.Date(string='End Date', required=True)
    limit = fields.Integer(string='Top', required=True, default=10)
    excel_file = fields.Binary('Excel File')
    file_name = fields.Char('File Name')

    @api.constrains('limit')
    def _check_limit(self):
        for wizard in self:
            if wizard.limit <= 0:
                raise ValidationError(_('Top must be greater than 0.'))

    def _gather_data(self):
        self.ensure_one()
        company_id = self.env.company.id

        query = (
            "SELECT aml.partner_id, SUM(aml.credit) AS credit, SUM(aml.debit) AS debit "
            "FROM account_move_line aml "
            "JOIN account_move am ON aml.move_id = am.id "
            "JOIN account_account a ON aml.account_id = a.id "
            "WHERE aml.date >= %s AND aml.date <= %s AND a.account_type = 'income' "
            "AND am.state = 'posted' AND aml.company_id = %s AND aml.partner_id IS NOT NULL "
            "GROUP BY aml.partner_id "
            "ORDER BY (SUM(aml.credit) - SUM(aml.debit)) DESC "
            "LIMIT %s"
        )
        params = (self.date_from, self.date_to, company_id, self.limit)
        self.env.cr.execute(query, params)
        rows = self.env.cr.fetchall()

        partners = self.env['res.partner'].browse([r[0] for r in rows])
        partners_by_id = {p.id: p for p in partners}

        data_rows = []
        for partner_id, credit, debit in rows:
            amount = (credit or 0.0) - (debit or 0.0)
            data_rows.append({
                'name': partners_by_id[partner_id].name or '',
                'amount': float(amount),
            })
        return data_rows

    def action_export_xlsx(self):
        self.ensure_one()
        rows = self._gather_data()

        try:
            import xlsxwriter
        except Exception:
            raise Exception(_('Missing xlsxwriter python package on the server.'))

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet('Top Customers')

        title_format = workbook.add_format({'bold': True, 'font_size': 12})
        header_format = workbook.add_format({'bold': True, 'bg_color': '#D9D9D9', 'border': 1})
        default_format = workbook.add_format({'num_format': '#,##0.00', 'border': 1})
        text_format = workbook.add_format({'border': 1})

        rowx = 0
        sheet.write(rowx, 0, self.env.company.name or '', title_format)
        rowx += 1
        sheet.write(rowx, 0, 'Top %s Customers' % self.limit, title_format)
        rowx += 1
        sheet.write(rowx, 0, 'Duration : From %s To %s' % (self.date_from, self.date_to), title_format)
        rowx += 1
        sheet.write(rowx, 0, 'Currency : %s' % (self.env.company.currency_id.name or ''), title_format)
        rowx += 2

        sheet.write(rowx, 0, 'No', header_format)
        sheet.write(rowx, 1, 'Customer Name', header_format)
        sheet.write(rowx, 2, 'Amount', header_format)
        rowx += 1

        for idx, r in enumerate(rows, start=1):
            sheet.write(rowx, 0, idx, text_format)
            sheet.write(rowx, 1, r['name'], text_format)
            sheet.write(rowx, 2, r['amount'], default_format)
            rowx += 1

        sheet.set_column(1, 1, 30)
        sheet.set_column(2, 2, 18)

        workbook.close()
        output.seek(0)
        data = output.read()

        fname = 'Top_%s_Customers_%s.xlsx' % (self.limit, fields.Date.context_today(self))
        self.write({
            'excel_file': base64.b64encode(data),
            'file_name': fname,
        })
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{self._name}/{self.id}/excel_file/{fname}?download=true',
            'target': 'new',
        }
