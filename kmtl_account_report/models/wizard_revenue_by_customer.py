from odoo import models, fields, api, _
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta
import io
import base64


class KMTLRevenueByCustomerWizard(models.TransientModel):
    _name = 'kmtl.revenue.by.customer'
    _description = 'Revenue by Customer Report Wizard'

    date_from = fields.Date(string='Start Date', required=True)
    date_to = fields.Date(string='End Date', required=True)
    partner_ids = fields.Many2many('res.partner', string='Customers')
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
        current = start_date
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
            # quarters as Q1..Q4 with numbering starting at 1 per year
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
            # ISO-like weeks starting from start_date
            cur = start_date
            week_no = 1
            while cur <= end_date:
                s = cur
                e = min(cur + timedelta(days=6), end_date)
                label = f"W{week_no}-{s.year}"
                periods.append((label, s, e))
                cur = e + timedelta(days=1)
                week_no += 1
        else:  # day
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
        company_id = self.env.company.id

        partner_domain = []
        if self.partner_ids:
            partner_ids = tuple(self.partner_ids.ids)
            partner_filter_sql = 'AND aml.partner_id IN %s'
            partner_params = (partner_ids,)
        else:
            partner_filter_sql = ''
            partner_params = ()

        # Build partner list: if partners selected, use them; else we'll collect from SQL results
        partners_map = {}
        has_no_customer = False
        results = {}

        for label, pstart, pend in periods:
            params = (pstart, pend, company_id)
            params = params + partner_params
            query = (
                "SELECT aml.partner_id, SUM(aml.credit) AS credit, SUM(aml.debit) AS debit "
                "FROM account_move_line aml "
                "JOIN account_move am ON aml.move_id = am.id "
                "JOIN account_account a ON aml.account_id = a.id "
                "WHERE aml.date >= %s AND aml.date <= %s AND a.account_type = 'income' "
                "AND am.state = 'posted' AND aml.company_id = %s " + partner_filter_sql +
                " GROUP BY aml.partner_id"
            )
            self.env.cr.execute(query, params)
            rows = self.env.cr.fetchall()
            period_map = {}
            for partner_id, credit, debit in rows:
                amt = (credit or 0.0) - (debit or 0.0)
                period_map[partner_id] = float(amt)
                if partner_id:
                    if partner_id not in partners_map:
                        partners_map[partner_id] = None
                else:
                    has_no_customer = True
            results[label] = period_map

        # If no partners selected, fetch partner records for ids we gathered
        if self.partner_ids:
            partners = self.partner_ids
        else:
            partners = self.env['res.partner'].browse(list(partners_map.keys())) if partners_map else self.env['res.partner']

        # Build rows: for each partner, amounts per period
        data_rows = []
        for partner in partners:
            row = {'name': partner.name or '', 'periods': [], 'total': 0.0}
            for label, pstart, pend in periods:
                amt = results.get(label, {}).get(partner.id, 0.0)
                row['periods'].append(amt)
                row['total'] += amt
            data_rows.append(row)

        if has_no_customer:
            row = {'name': _('None'), 'periods': [], 'total': 0.0}
            for label, pstart, pend in periods:
                amt = results.get(label, {}).get(None, 0.0)
                row['periods'].append(amt)
                row['total'] += amt
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
        sheet = workbook.add_worksheet('Revenue By Customer')

        # Formats
        title_format = workbook.add_format({'bold': True, 'font_size': 12})
        header_format = workbook.add_format({'bold': True, 'bg_color': '#D9D9D9', 'border': 1})
        default_format = workbook.add_format({'num_format': '#,##0.00', 'border': 1})
        text_format = workbook.add_format({'border': 1})

        rowx = 0
        # Header lines
        sheet.write(rowx, 0, self.env.company.name or '', title_format)
        rowx += 1
        sheet.write(rowx, 0, 'Revenue by Customer', title_format)
        rowx += 1
        sheet.write(rowx, 0, f"Duration : From {self.date_from} To {self.date_to}", title_format)
        rowx += 1
        sheet.write(rowx, 0, 'Currency : %s' % (self.currency_id.name or ''), title_format)
        rowx += 2

        # Column headers
        colx = 0
        sheet.write(rowx, colx, 'No', header_format)
        colx += 1
        sheet.write(rowx, colx, 'Customer Name', header_format)
        colx += 1
        for label, _, _ in periods:
            sheet.write(rowx, colx, label, header_format)
            colx += 1
        sheet.write(rowx, colx, 'Total', header_format)
        rowx += 1

        # Data rows
        for idx, r in enumerate(rows, start=1):
            colx = 0
            sheet.write(rowx, colx, idx, text_format)
            colx += 1
            sheet.write(rowx, colx, r['name'], text_format)
            colx += 1
            for amt in r['periods']:
                sheet.write(rowx, colx, amt, default_format)
                colx += 1
            sheet.write(rowx, colx, r['total'], default_format)
            rowx += 1

        # Totals row
        sheet.write(rowx, 0, '', header_format)
        sheet.write(rowx, 1, 'Total', header_format)
        col = 2
        for p_index in range(len(periods)):
            col_sum = sum(r['periods'][p_index] for r in rows)
            sheet.write(rowx, col, col_sum, header_format)
            col += 1
        sheet.write(rowx, col, sum(r['total'] for r in rows), header_format)

        workbook.close()
        output.seek(0)
        data = output.read()

        fname = 'Revenue_by_Customer_%s.xlsx' % (fields.Date.context_today(self))
        self.write({
            'excel_file': base64.b64encode(data),
            'file_name': fname,
        })
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{self._name}/{self.id}/excel_file/{fname}?download=true',
            'target': 'new',
        }
