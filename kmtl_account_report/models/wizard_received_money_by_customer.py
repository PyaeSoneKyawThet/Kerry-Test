from odoo import models, fields, api, _
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
import io
import base64


class KMTLReceivedMoneyByCustomerWizard(models.TransientModel):
    _name = 'kmtl.received.money.by.customer'
    _description = 'Received Money by Customer Report Wizard'

    date_from = fields.Date(string='Start Date', required=True)
    date_to = fields.Date(string='End Date', required=True)
    partner_ids = fields.Many2many('res.partner', string='Customers')
    user_ids = fields.Many2many('res.users', string='Created Users')
    group_by = fields.Selection([
        ('year', 'Year'),
        ('quarter', 'Quarter'),
        ('month', 'Month'),
        ('week', 'Week'),
        ('day', 'Day'),
    ], string='Date Group By', required=True, default='month')
    currency_id = fields.Many2one('res.currency', string='Currency', required=True,
                                  default=lambda self: self.env.company.currency_id)
    excel_file = fields.Binary('Excel File')
    file_name = fields.Char('File Name')

    def _periods_between(self, start_date, end_date, group_by):
        periods = []
        if group_by == 'year':
            y = start_date.year
            while y <= end_date.year:
                s = date(y, 1, 1)
                e = date(y, 12, 31)
                if e < start_date:
                    y += 1
                    continue
                if s > end_date:
                    break
                periods.append((str(y), max(s, start_date), min(e, end_date)))
                y += 1
        elif group_by == 'quarter':
            cur = date(start_date.year, ((start_date.month - 1) // 3) * 3 + 1, 1)
            while cur <= end_date:
                q = ((cur.month - 1) // 3) + 1
                s = cur
                e = (s + relativedelta(months=3)) - timedelta(days=1)
                label = f"Q{q}-{s.year}"
                periods.append((label, max(s, start_date), min(e, end_date)))
                cur = cur + relativedelta(months=3)
        elif group_by == 'month':
            cur = date(start_date.year, start_date.month, 1)
            while cur <= end_date:
                s = cur
                e = (s + relativedelta(months=1)) - timedelta(days=1)
                label = s.strftime('%b-%y')
                periods.append((label, max(s, start_date), min(e, end_date)))
                cur = cur + relativedelta(months=1)
        elif group_by == 'week':
            cur = start_date
            week_no = 1
            while cur <= end_date:
                s = cur
                e = min(cur + timedelta(days=6), end_date)
                label = f"W{week_no}-{s.year}"
                periods.append((label, s, e))
                cur = e + timedelta(days=1)
                week_no += 1
        else:
            cur = start_date
            while cur <= end_date:
                periods.append((cur.strftime('%Y-%m-%d'), cur, cur))
                cur = cur + timedelta(days=1)
        return periods

    def _gather_data(self):
        self.ensure_one()
        start = self.date_from
        stop = self.date_to
        periods = self._periods_between(start, stop, self.group_by)
        company = self.env.company

        payments_obj = self.env['account.payment']

        partner_filter = []
        if self.partner_ids:
            partner_filter = [('partner_id', 'in', self.partner_ids.ids)]

        user_filter = []
        if self.user_ids:
            user_filter = [('create_uid', 'in', self.user_ids.ids)]

        results = {}
        partners_map = {}
        has_no_customer = False

        for label, pstart, pend in periods:
            domain = [
                ('date', '>=', pstart),
                ('date', '<=', pend),
                ('state', '=', 'posted'),
                ('payment_type', '=', 'inbound'),
                ('company_id', '=', company.id),
                ('partner_type', '=', 'customer'),
                ('report_currency_id', '=', self.currency_id.id),
            ] + partner_filter + user_filter

            payments = payments_obj.search(domain)
            period_map = {}
            for p in payments:
                partner_id = p.partner_id.id if p.partner_id else None
                amt = p.report_currency_id._convert(p.report_amount, self.currency_id, company, p.date)
                entry = period_map.setdefault(partner_id, {'amount': 0.0, 'qty': 0})
                entry['amount'] += float(amt or 0.0)
                entry['qty'] += 1
                if partner_id:
                    partners_map[partner_id] = None
                else:
                    has_no_customer = True

            results[label] = period_map

        if self.partner_ids:
            partners = self.partner_ids
        else:
            partners = self.env['res.partner'].browse(list(partners_map.keys())) if partners_map else self.env['res.partner']

        data_rows = []
        for partner in partners:
            row = {'name': partner.name or '', 'periods': [], 'total': 0.0, 'total_qty': 0}
            for label, pstart, pend in periods:
                period_data = results.get(label, {}).get(partner.id, {'amount': 0.0, 'qty': 0})
                row['periods'].append(period_data)
                row['total'] += period_data['amount']
                row['total_qty'] += period_data['qty']
            data_rows.append(row)

        if has_no_customer:
            row = {'name': _('None'), 'periods': [], 'total': 0.0, 'total_qty': 0}
            for label, pstart, pend in periods:
                period_data = results.get(label, {}).get(None, {'amount': 0.0, 'qty': 0})
                row['periods'].append(period_data)
                row['total'] += period_data['amount']
                row['total_qty'] += period_data['qty']
            data_rows.append(row)

        return periods, data_rows

    def action_export_xlsx(self):
        self.ensure_one()
        periods, rows = self._gather_data()

        try:
            import xlsxwriter
        except Exception:
            raise Exception(_('Missing xlsxwriter python package on the server.'))

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet('Received Money By Customer')

        title_format = workbook.add_format({'bold': True, 'font_size': 12, 'align': 'center'})
        header_format = workbook.add_format({'bold': True, 'bg_color': '#D9D9D9', 'border': 1, 'align': 'center'})
        default_format = workbook.add_format({'num_format': '#,##0.00', 'border': 1})
        text_format = workbook.add_format({'border': 1})
        integer_format = workbook.add_format({'num_format': '0', 'border': 1})

        rowx = 0
        sheet.write(rowx, 0, self.env.company.name or '', title_format)
        rowx += 1
        sheet.write(rowx, 0, 'Received money by Customer', title_format)
        rowx += 1
        sheet.write(rowx, 0, f"Duration : From {self.date_from} To {self.date_to}", title_format)
        rowx += 1
        sheet.write(rowx, 0, 'Currency : %s' % (self.currency_id.name or ''), title_format)
        rowx += 2

        colx = 0
        sheet.merge_range(rowx, colx, rowx + 1, colx, 'No', header_format)
        colx += 1
        sheet.merge_range(rowx, colx, rowx + 1, colx, 'Customer Name', header_format)
        colx += 1
        for label, _, _ in periods:
            sheet.merge_range(rowx, colx, rowx, colx + 1, label, header_format)
            colx += 2
        rowx += 1

        colx = 2
        for _ in periods:
            sheet.write(rowx, colx, 'Qty', header_format)
            colx += 1
            sheet.write(rowx, colx, 'Amount', header_format)
            colx += 1
        rowx += 1

        for idx, r in enumerate(rows, start=1):
            colx = 0
            sheet.write(rowx, colx, idx, text_format)
            colx += 1
            sheet.write(rowx, colx, r['name'], text_format)
            colx += 1
            for period_data in r['periods']:
                sheet.write(rowx, colx, period_data['qty'], integer_format)
                colx += 1
                sheet.write(rowx, colx, period_data['amount'], default_format)
                colx += 1
            rowx += 1

        workbook.close()
        output.seek(0)
        data = output.read()

        fname = 'Received_money_by_Customer_%s.xlsx' % (fields.Date.context_today(self))
        self.write({
            'excel_file': base64.b64encode(data),
            'file_name': fname,
        })
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{self._name}/{self.id}/excel_file/{fname}?download=true',
            'target': 'new',
        }
