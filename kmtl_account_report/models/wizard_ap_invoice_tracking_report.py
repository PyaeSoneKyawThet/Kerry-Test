import io
import base64

from odoo import models, fields, _


class KMTLAPInvoiceTrackingState(models.Model):
    _name = 'kmtl.ap.tracking.state'
    _description = 'AP Invoice Tracking Report State'
    _order = 'sequence, id'

    name = fields.Char(required=True)
    code = fields.Char(required=True)
    sequence = fields.Integer(default=10)


class KMTLAPInvoiceTrackingReportWizard(models.TransientModel):
    _name = 'kmtl.ap.invoice.tracking.report'
    _description = 'AP Invoice Tracking Report Wizard'

    date_from = fields.Date(string='Start Date', required=True)
    date_to = fields.Date(string='End Date', required=True)
    staff_location_ids = fields.Many2many('staff.location', string='Document Location')
    partner_ids = fields.Many2many('res.partner', string='Vendor')
    payment_term_ids = fields.Many2many('account.payment.term', string='Payment Term')
    state_ids = fields.Many2many(
        'kmtl.ap.tracking.state',
        string='Status',
    )
    currency_ids = fields.Many2many('res.currency', string='Currency')
    account_ids = fields.Many2many('account.account', string='Account')
    excel_file = fields.Binary('Excel File')
    file_name = fields.Char('File Name')

    def _build_line_domain(self):
        self.ensure_one()
        domain = [
            ('move_id.move_type', '=', 'in_invoice'),
            ('move_id.company_id', '=', self.env.company.id),
            ('account_id.account_type', 'not in', ('asset_receivable', 'liability_payable')),
            ('move_id.invoice_date', '>=', self.date_from),
            ('move_id.invoice_date', '<=', self.date_to),
        ]
        if self.staff_location_ids:
            domain.append(('move_id.staff_location_id', 'in', self.staff_location_ids.ids))
        if self.partner_ids:
            domain.append(('partner_id', 'in', self.partner_ids.ids))
        if self.payment_term_ids:
            domain.append(('move_id.invoice_payment_term_id', 'in', self.payment_term_ids.ids))
        if self.state_ids:
            domain.append(('move_id.state', 'in', self.state_ids.mapped('code')))
        if self.currency_ids:
            domain.append(('currency_id', 'in', self.currency_ids.ids))
        if self.account_ids:
            domain.append(('account_id', 'in', self.account_ids.ids))
        return domain

    def _parse_analytic_account_ids(self, line):
        if not line.analytic_distribution:
            return []
        account_ids = set()
        for key in line.analytic_distribution.keys():
            for account_id in str(key).split(','):
                account_id = account_id.strip()
                if account_id.isdigit():
                    account_ids.add(int(account_id))
        return list(account_ids)

    def _format_analytic(self, line):
        account_ids = self._parse_analytic_account_ids(line)
        if not account_ids:
            return ''
        accounts = self.env['account.analytic.account'].browse(account_ids).sorted(key=lambda rec: rec.name or '')
        return ' * '.join(account.name for account in accounts if account.name)

    def _move_status_label(self, move):
        return {
            'draft': 'Draft',
            'posted': 'Posted',
            'cancel': 'Cancelled',
        }.get(move.state, move.state or '')

    def _get_exchange_rate(self, move):
        return float(getattr(move, 'currency_rate', None) or 1.0)

    def _line_amount_in_currency(self, line):
        amount_currency = float(line.amount_currency or 0.0)
        if amount_currency:
            return amount_currency
        return float(line.balance or 0.0)

    def _gather_data(self):
        self.ensure_one()
        lines = self.env['account.move.line'].search(
            self._build_line_domain(),
            order='move_id, account_id, id',
        )

        rows = []
        for line in lines:
            move = line.move_id
            exchange_rate = self._get_exchange_rate(move)
            amount_in_currency = self._line_amount_in_currency(line)
            rows.append({
                'gl_date': move.date,
                'invoice_date': move.invoice_date,
                'due_date': move.invoice_date_due,
                'invoice_voucher_no': move.name or '',
                'vendor_code': line.partner_id.ref or '',
                'vendor_name': line.partner_id.name or '',
                'vendor_invoice_number': move.ref or '',
                'payment_term': move.invoice_payment_term_id.name or '',
                'label': line.name if line.name else '',
                'description': move.reason,
                'acc_code': line.account_id.code or '',
                'acc_name': line.account_id.name or '',
                'analytic': self._format_analytic(line),
                'currency': line.currency_id.name or '',
                'amount_in_currency': amount_in_currency,
                'exchange_rate': exchange_rate,
                'amount_mmk': amount_in_currency * exchange_rate,
                'status': self._move_status_label(move),
            })

        rows.sort(key=lambda row: (
            row['invoice_date'] or fields.Date.today(),
            row['invoice_voucher_no'],
            row['acc_code'],
            row['analytic'],
        ))
        return rows

    def _filter_label(self, records, all_label='All'):
        if records:
            return ', '.join(records.mapped('name'))
        return all_label

    def action_export_xlsx(self):
        self.ensure_one()

        try:
            import xlsxwriter
        except Exception:
            raise Exception(_('Missing xlsxwriter python package on the server.'))

        rows = self._gather_data()
        company_currency = self.env.company.currency_id

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet('AP Invoice Tracking Report')

        title_format = workbook.add_format({'bold': True, 'font_size': 12})
        header_format = workbook.add_format({'bold': True, 'bg_color': '#D9D9D9', 'border': 1, 'align': 'center'})
        default_format = workbook.add_format({'num_format': '#,##0.00', 'border': 1})
        rate_format = workbook.add_format({'num_format': '#,##0.0000', 'border': 1})
        text_format = workbook.add_format({'border': 1})
        date_format = workbook.add_format({'num_format': 'yyyy-mm-dd', 'border': 1})

        rowx = 0
        sheet.write(rowx, 0, self.env.company.name or 'KM TERMINAL & LOGISTICS LIMITED', title_format)
        rowx += 1
        sheet.write(rowx, 0, 'AP Invoice Tracking Report', title_format)
        rowx += 1
        sheet.write(
            rowx,
            0,
            'Doc Location - %s' % self._filter_label(self.staff_location_ids),
            title_format,
        )
        rowx += 1
        sheet.write(rowx, 0, 'Period - From %s To %s' % (self.date_from, self.date_to), title_format)
        rowx += 2

        headers = [
            'No',
            'GL Date',
            'Vendor Invoice Date',
            'Due Date',
            'AP Invoice Voucher No',
            'Vendor Code',
            'Vendor Name',
            'Vendor Invoice Number',
            'Payment Term',
            'Label',
            'Description',
            'Acc Code',
            'Acc Name',
            'Analytic',
            'Currency',
            'Amount In Currency',
            'Exchange Rate',
            'Amount (%s)' % (company_currency.name or 'MMK'),
            'Status',
        ]
        for colx, header in enumerate(headers):
            sheet.write(rowx, colx, header, header_format)
        rowx += 1

        for idx, row in enumerate(rows, start=1):
            colx = 0
            sheet.write(rowx, colx, idx, text_format)
            colx += 1
            sheet.write(rowx, colx, row['gl_date'], date_format)
            colx += 1
            sheet.write(rowx, colx, row['invoice_date'], date_format)
            colx += 1
            sheet.write(rowx, colx, row['due_date'], date_format)
            colx += 1
            sheet.write(rowx, colx, row['invoice_voucher_no'], text_format)
            colx += 1
            sheet.write(rowx, colx, row['vendor_code'], text_format)
            colx += 1
            sheet.write(rowx, colx, row['vendor_name'], text_format)
            colx += 1
            sheet.write(rowx, colx, row['vendor_invoice_number'], text_format)
            colx += 1
            sheet.write(rowx, colx, row['payment_term'], text_format)
            colx += 1
            sheet.write(rowx, colx, row['label'], text_format)
            colx += 1
            sheet.write(rowx, colx, row['description'], text_format)
            colx += 1
            sheet.write(rowx, colx, row['acc_code'], text_format)
            colx += 1
            sheet.write(rowx, colx, row['acc_name'], text_format)
            colx += 1
            sheet.write(rowx, colx, row['analytic'], text_format)
            colx += 1
            sheet.write(rowx, colx, row['currency'], text_format)
            colx += 1
            sheet.write(rowx, colx, row['amount_in_currency'], default_format)
            colx += 1
            sheet.write(rowx, colx, row['exchange_rate'], rate_format)
            colx += 1
            sheet.write(rowx, colx, row['amount_mmk'], default_format)
            colx += 1
            sheet.write(rowx, colx, row['status'], text_format)
            rowx += 1

        sheet.set_column(0, 0, 6)
        sheet.set_column(1, 3, 12)
        sheet.set_column(4, 4, 20)
        sheet.set_column(5, 5, 14)
        sheet.set_column(6, 6, 28)
        sheet.set_column(7, 7, 20)
        sheet.set_column(8, 8, 16)
        sheet.set_column(9, 10, 18)
        sheet.set_column(11, 12, 18)
        sheet.set_column(13, 13, 24)
        sheet.set_column(14, 14, 10)
        sheet.set_column(15, 17, 16)
        sheet.set_column(18, 18, 12)

        workbook.close()
        output.seek(0)
        data = output.read()

        fname = 'AP_Invoice_Tracking_Report_%s.xlsx' % fields.Date.context_today(self)
        self.write({
            'excel_file': base64.b64encode(data),
            'file_name': fname,
        })
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{self._name}/{self.id}/excel_file/{fname}?download=true',
            'target': 'new',
        }
