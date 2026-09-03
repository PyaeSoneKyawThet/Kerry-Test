from odoo import models, fields, _
import io
import base64


class KMTLReceiveHistoryReportWizard(models.TransientModel):
    _name = 'kmtl.receive.history.report'
    _description = 'Receive History Report Wizard'

    date_from = fields.Date(string='Start Date', required=True)
    date_to = fields.Date(string='End Date', required=True)
    partner_ids = fields.Many2many('res.partner', string='Customer')
    currency_ids = fields.Many2many('res.currency', string='Currency')
    report_currency_ids = fields.Many2many(
        'res.currency',
        'kmtl_receive_history_report_currency_rel',
        'wizard_id',
        'currency_id',
        string='Pay Currency',
    )
    account_payment_type_ids = fields.Many2many('account.payment.type', string='Receive Type')
    journal_ids = fields.Many2many('account.journal', string='Company Bank Name')
    staff_location_ids = fields.Many2many('staff.location', string='Location')
    excel_file = fields.Binary('Excel File')
    file_name = fields.Char('File Name')

    def _build_domain(self):
        self.ensure_one()
        domain = [
            ('payment_type', '=', 'inbound'),
            ('partner_type', '=', 'customer'),
            ('state', '=', 'posted'),
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
            ('company_id', '=', self.env.company.id),
        ]
        if self.partner_ids:
            domain.append(('partner_id', 'in', self.partner_ids.ids))
        if self.currency_ids:
            domain.append(('currency_id', 'in', self.currency_ids.ids))
        if self.report_currency_ids:
            domain.append(('report_currency_id', 'in', self.report_currency_ids.ids))
        if self.account_payment_type_ids:
            domain.append(('account_payment_type_id', 'in', self.account_payment_type_ids.ids))
        if self.journal_ids:
            domain.append(('journal_id', 'in', self.journal_ids.ids))
        if self.staff_location_ids:
            domain.append(('staff_location_id', 'in', self.staff_location_ids.ids))
        return domain

    def _gather_data(self):
        self.ensure_one()
        payments = self.env['account.payment'].search(
            self._build_domain(),
            order='date, receipt_voucher_no, id',
        )
        company_currency = self.env.company.currency_id
        rows = []
        for payment in payments:
            amount_in_currency = float(payment.amount or 0.0)
            currency_rate = float(payment.currency_rate or 1.0)
            amount = amount_in_currency * currency_rate
            invoice_numbers = ', '.join(
                sorted({invoice.name for invoice in payment.invoice_ids if invoice.name})
            )
            rows.append({
                'gl_date': payment.move_id.date or payment.date,
                'receive_date': payment.official_receipt_date or payment.date,
                'receive_voucher_no': payment.receipt_voucher_no or payment.name or '',
                'official_receipt_no': payment.official_receipt_no or '',
                'customer_code': payment.partner_id.ref or '',
                'customer_name': payment.partner_id.name or '',
                'invoice_number': invoice_numbers,
                'description': payment.ref or '',
                'receive_type': payment.account_payment_type_id.name or '',
                'company_bank_name': payment.journal_id.name or '',
                'amount_in_currency': amount_in_currency,
                'currency': payment.currency_id.name or '',
                'currency_rate': currency_rate,
                'amount': amount,
                'pay_currency': payment.report_currency_id.name or '',
                'pay_amount': float(payment.report_amount or 0.0),
            })
        return rows, company_currency

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

        rows, company_currency = self._gather_data()

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet('Receive History Report')

        title_format = workbook.add_format({'bold': True, 'font_size': 12})
        header_format = workbook.add_format({'bold': True, 'bg_color': '#D9D9D9', 'border': 1, 'align': 'center'})
        default_format = workbook.add_format({'num_format': '#,##0.00', 'border': 1})
        rate_format = workbook.add_format({'num_format': '#,##0.0000', 'border': 1})
        text_format = workbook.add_format({'border': 1})
        date_format = workbook.add_format({'num_format': 'yyyy-mm-dd', 'border': 1})

        rowx = 0
        sheet.write(rowx, 0, self.env.company.name or 'KM TERMINAL & LOGISTICS LIMITED', title_format)
        rowx += 1
        sheet.write(rowx, 0, 'Receive History Report', title_format)
        rowx += 1
        sheet.write(
            rowx,
            0,
            'Location - %s' % self._filter_label(self.staff_location_ids),
            title_format,
        )
        rowx += 1
        sheet.write(rowx, 0, 'Period - From %s To %s' % (self.date_from, self.date_to), title_format)
        rowx += 2

        headers = [
            'No',
            'GL Date',
            'Receive Date',
            'Receive Voucher No',
            'Official Receipt No',
            'Customer Code',
            'Customer Name',
            'Invoice Number',
            'Description',
            'Receive Type',
            'Company Bank Name',
            'Amount In Currency',
            'Currency',
            'Exchange Rate',
            'Amount (%s)' % (company_currency.name or 'MMK'),
            'Pay Currency',
            'Pay Amount',
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
            sheet.write(rowx, colx, row['receive_date'], date_format)
            colx += 1
            sheet.write(rowx, colx, row['receive_voucher_no'], text_format)
            colx += 1
            sheet.write(rowx, colx, row['official_receipt_no'], text_format)
            colx += 1
            sheet.write(rowx, colx, row['customer_code'], text_format)
            colx += 1
            sheet.write(rowx, colx, row['customer_name'], text_format)
            colx += 1
            sheet.write(rowx, colx, row['invoice_number'], text_format)
            colx += 1
            sheet.write(rowx, colx, row['description'], text_format)
            colx += 1
            sheet.write(rowx, colx, row['receive_type'], text_format)
            colx += 1
            sheet.write(rowx, colx, row['company_bank_name'], text_format)
            colx += 1
            sheet.write(rowx, colx, row['amount_in_currency'], default_format)
            colx += 1
            sheet.write(rowx, colx, row['currency'], text_format)
            colx += 1
            sheet.write(rowx, colx, row['currency_rate'], rate_format)
            colx += 1
            sheet.write(rowx, colx, row['amount'], default_format)
            colx += 1
            sheet.write(rowx, colx, row['pay_currency'], text_format)
            colx += 1
            sheet.write(rowx, colx, row['pay_amount'], default_format)
            rowx += 1

        sheet.set_column(0, 0, 6)
        sheet.set_column(1, 2, 12)
        sheet.set_column(3, 4, 18)
        sheet.set_column(5, 5, 14)
        sheet.set_column(6, 6, 28)
        sheet.set_column(7, 8, 22)
        sheet.set_column(9, 10, 18)
        sheet.set_column(11, 11, 16)
        sheet.set_column(12, 12, 10)
        sheet.set_column(13, 13, 12)
        sheet.set_column(14, 16, 16)

        workbook.close()
        output.seek(0)
        data = output.read()

        fname = 'Receive_History_Report_%s.xlsx' % fields.Date.context_today(self)
        self.write({
            'excel_file': base64.b64encode(data),
            'file_name': fname,
        })
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{self._name}/{self.id}/excel_file/{fname}?download=true',
            'target': 'new',
        }
