from odoo import models, fields, _
import io
import base64


class KMTLCreditNoteListReportWizard(models.TransientModel):
    _name = 'kmtl.credit.note.list.report'
    _description = 'Credit Note List Report Wizard'

    date_from = fields.Date(string='From Date', required=True)
    date_to = fields.Date(string='To Date', required=True)
    partner_ids = fields.Many2many('res.partner', string='Customer Name')
    currency_ids = fields.Many2many('res.currency', string='Currency')
    user_ids = fields.Many2many('res.users', string='Sale PIC')
    excel_file = fields.Binary('Excel File')
    file_name = fields.Char('File Name')

    def _build_domain(self):
        self.ensure_one()
        domain = [
            ('move_type', '=', 'out_refund'),
            ('state', '=', 'posted'),
            ('invoice_date', '>=', self.date_from),
            ('invoice_date', '<=', self.date_to),
        ]
        if self.partner_ids:
            domain.append(('partner_id', 'in', self.partner_ids.ids))
        if self.user_ids:
            domain.append(('invoice_line_ids.quotation_salesperson_id', 'in', self.user_ids.ids))
        if self.currency_ids:
            domain.append(('currency_id', 'in', self.currency_ids.ids))
        return domain

    def _gather_data(self):
        self.ensure_one()
        moves = self.env['account.move'].search(self._build_domain(), order='invoice_date, name')

        if self.partner_ids:
            moves = moves.filtered(lambda move: move.partner_id.id in self.partner_ids.ids)
        if self.user_ids:
            moves = moves.filtered(
                lambda move: any(
                    line.quotation_salesperson_id.id in self.user_ids.ids
                    for line in move.invoice_line_ids
                )
            )

        if not moves:
            return [], self.currency_ids, []

        if self.currency_ids:
            currencies = self.currency_ids.sorted(key=lambda currency: currency.name)
        else:
            currency_ids = sorted(
                {move.currency_id.id for move in moves if move.currency_id},
                key=lambda cid: self.env['res.currency'].browse(cid).name,
            )
            currencies = self.env['res.currency'].browse(currency_ids)

        rows = []
        for move in moves:
            sale_pics = move.invoice_line_ids.mapped('quotation_salesperson_id')
            if self.user_ids:
                sale_pics = sale_pics.filtered(lambda user: user.id in self.user_ids.ids)
            sale_pic_names = ', '.join(sorted({user.name for user in sale_pics if user.name}))
            row = {
                'credit_note_number': move.name or move.invoice_number or '',
                'customer_name': move.partner_id.name or '',
                'sale_pic': sale_pic_names,
                'amounts': {},
            }
            for currency in currencies:
                if move.currency_id and move.currency_id.id == currency.id:
                    row['amounts'][currency.id] = float(move.amount_total_in_currency_signed or 0.0)
                else:
                    row['amounts'][currency.id] = ''
            rows.append(row)
        return moves, currencies, rows

    def action_export_xlsx(self):
        self.ensure_one()

        try:
            import xlsxwriter
        except Exception:
            raise Exception(_('Missing xlsxwriter python package on the server.'))

        moves, currencies, rows = self._gather_data()

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet('Credit Note List Report')

        title_format = workbook.add_format({'bold': True, 'font_size': 12})
        header_format = workbook.add_format({'bold': True, 'bg_color': '#D9D9D9', 'border': 1})
        default_format = workbook.add_format({'num_format': '#,##0.00', 'border': 1})
        text_format = workbook.add_format({'border': 1})

        rowx = 0
        sheet.write(rowx, 0, 'KM Terminal and Logistic Limited', title_format)
        rowx += 1
        sheet.write(rowx, 0, 'Credit Note List Report', title_format)
        rowx += 1
        sheet.write(rowx, 0, 'Duration : From %s To %s' % (self.date_from, self.date_to), title_format)
        rowx += 1
        currency_label = ','.join(c.name for c in self.currency_ids) if self.currency_ids else 'All'
        sheet.write(rowx, 0, 'Currency : %s' % currency_label, title_format)
        rowx += 2

        headers = ['No', 'Credit Note Number', 'Customer Name', 'Sale PIC']
        for currency in currencies:
            headers.append('Amount (%s)' % currency.name)

        for colx, header in enumerate(headers):
            sheet.write(rowx, colx, header, header_format)
        rowx += 1

        for idx, row in enumerate(rows, start=1):
            colx = 0
            sheet.write(rowx, colx, idx, text_format)
            colx += 1
            sheet.write(rowx, colx, row['credit_note_number'], text_format)
            colx += 1
            sheet.write(rowx, colx, row['customer_name'], text_format)
            colx += 1
            sheet.write(rowx, colx, row['sale_pic'], text_format)
            colx += 1
            for currency in currencies:
                value = row['amounts'].get(currency.id, '')
                sheet.write(rowx, colx, value, default_format if value != '' else text_format)
                colx += 1
            rowx += 1

        sheet.set_column(0, 0, 6)
        sheet.set_column(1, 1, 18)
        sheet.set_column(2, 2, 30)
        sheet.set_column(3, 3, 24)
        sheet.set_column(4, 4 + max(len(currencies) - 1, 0), 18)

        workbook.close()
        output.seek(0)
        data = output.read()

        fname = 'Credit_Note_List_Report_%s.xlsx' % fields.Date.context_today(self)
        self.write({
            'excel_file': base64.b64encode(data),
            'file_name': fname,
        })
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{self._name}/{self.id}/excel_file/{fname}?download=true',
            'target': 'new',
        }
